"""WebSocket 游戏端点 — W13: 实时流式对话"""
import json
import asyncio
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
    - 服务端返回: {"type": "dialogue", "content": "角色台词片段"}  (流式)
                  {"type": "options", "options": [...]}
                  {"type": "end", "summary": "结束信息"}
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

                # 使用 Agent 引擎处理（同步调用在线程池）
                try:
                    from api.services.game_service import GameService
                    result = await _process_via_agent(thread_id, user_input)

                    # 逐段推送对话（模拟流式）
                    dialogue = result.get("character_dialogue", "")
                    if dialogue:
                        # 分段发送，模拟逐 token 流式
                        segments = _split_for_streaming(dialogue)
                        for seg in segments:
                            await websocket.send_json({"type": "dialogue_chunk", "content": seg})
                            await asyncio.sleep(0.03)

                        await websocket.send_json({"type": "dialogue_complete"})

                    # 发送选项
                    options = result.get("player_options", [])
                    await websocket.send_json({"type": "options", "options": options})

                    # 发送状态更新
                    await websocket.send_json({
                        "type": "state",
                        "current_states": result.get("current_states", {}),
                        "scene": result.get("scene", ""),
                        "elapsed_minutes": result.get("elapsed_minutes", 0),
                    })

                    # 检查游戏结束
                    if result.get("is_game_finished"):
                        await websocket.send_json({
                            "type": "end",
                            "summary": dialogue,
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


async def _process_via_agent(thread_id: str, user_input: str) -> dict:
    """通过 Agent 引擎处理输入"""
    import os
    if os.getenv("USE_NOS_AGENT_ENGINE", "false").lower() == "true":
        from api.services.game_service import _get_agent_orchestrator
        orch = _get_agent_orchestrator()
        if orch:
            return await orch.process_input(user_input)

    # 回退：返回简单响应
    return {
        "character_dialogue": "WebSocket模式已连接，即将支持。",
        "player_options": [
            {"id": 1, "text": "继续", "type": "continue"},
            {"id": 2, "text": "换个话题", "type": "change_topic"},
        ],
        "scene": "classroom",
        "current_states": {},
        "elapsed_minutes": 0,
        "is_game_finished": False,
    }


def _split_for_streaming(text: str, chunk_size: int = 3) -> list:
    """将文本分割为流式片段"""
    result = []
    for i in range(0, len(text), chunk_size):
        result.append(text[i:i + chunk_size])
    return result
