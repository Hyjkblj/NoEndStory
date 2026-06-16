"""WebSocket 游戏端点 — W13: 实时流式对话"""
import json
import asyncio
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 活跃连接池
_active_connections: dict[str, WebSocket] = {}


@router.websocket("/v1/ws/game/{thread_id}")
async def ws_game_endpoint(websocket: WebSocket, thread_id: str):
    """WebSocket 游戏端点

    协议:
    - 客户端发送: {"type": "input", "content": "玩家输入文本"}
    - 服务端返回: {"type": "dialogue_chunk", "content": "token片段"}  (流式)
                  {"type": "dialogue_complete"}
                  {"type": "options", "options": [...]}
                  {"type": "state", ...}
                  {"type": "end", ...}
    """
    await websocket.accept()
    _active_connections[thread_id] = websocket
    logger.info(f"WS连接已建立: thread_id={thread_id}")

    try:
        # 发送连接确认
        await websocket.send_json({
            "type": "connected",
            "thread_id": thread_id,
            "message": "WebSocket连接已建立"
        })

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "input":
                user_input = data.get("content", "")
                logger.debug(f"WS接收: thread_id={thread_id}, input={user_input[:30]}...")

                try:
                    result = await _process_with_streaming(thread_id, user_input, websocket)

                    # 发送选项
                    options = result.get("player_options", [])
                    await websocket.send_json({"type": "options", "options": options})

                    # 发送状态更新
                    await websocket.send_json({
                        "type": "state",
                        "current_states": result.get("current_states", {}),
                        "scene": result.get("scene", ""),
                        "scene_image_url": result.get("scene_image_url"),
                        "audio_url": result.get("audio_url"),
                        "audio_duration": result.get("audio_duration", 0.0),
                        "elapsed_minutes": result.get("elapsed_minutes", 0),
                    })

                    # 检查游戏结束
                    if result.get("is_game_finished"):
                        await websocket.send_json({
                            "type": "end",
                            "summary": result.get("character_dialogue", ""),
                            "emotion_tags": result.get("emotion_tags", ""),
                        })
                        break

                except Exception as e:
                    logger.error(f"WS处理失败: {e}", exc_info=True)
                    await websocket.send_json({"type": "error", "message": "服务器处理失败"})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({"type": "error", "message": f"未知消息类型: {msg_type}"})

    except WebSocketDisconnect:
        logger.info(f"WS断开: thread_id={thread_id}")
    except Exception as e:
        logger.error(f"WS异常: thread_id={thread_id}, error={e}", exc_info=True)
    finally:
        _active_connections.pop(thread_id, None)


async def _process_with_streaming(thread_id: str, user_input: str, websocket: WebSocket) -> dict:
    """处理输入并通过 WebSocket 流式推送对话 token"""
    use_agent = os.getenv("USE_NOS_AGENT_ENGINE", "false").lower() == "true"

    if use_agent:
        from api.services.game_service import _get_agent_orchestrator
        orch = _get_agent_orchestrator()
        if orch:
            # 定义 token 回调：每个 token 立即推送到客户端
            async def on_token(chunk: str):
                try:
                    await websocket.send_json({"type": "dialogue_chunk", "content": chunk})
                except Exception:
                    pass  # 连接可能已断开

            result = await orch.process_input_stream(user_input, thread_id=thread_id, on_token=on_token)

            # 流式完成，发送完成标记
            await websocket.send_json({"type": "dialogue_complete"})
            return result

    # 回退：非 Agent 模式，使用 StoryEngine + 模拟流式
    from api.services.game_service import GameService
    from api.dependencies import get_game_service
    game_service = get_game_service()
    result = await game_service.process_input(thread_id, user_input)

    # 模拟流式推送
    dialogue = result.get("character_dialogue", "")
    if dialogue:
        for i in range(0, len(dialogue), 3):
            await websocket.send_json({"type": "dialogue_chunk", "content": dialogue[i:i + 3]})
            await asyncio.sleep(0.03)
    await websocket.send_json({"type": "dialogue_complete"})

    return result
