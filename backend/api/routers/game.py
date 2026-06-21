"""游戏管理API路由"""
import re
from fastapi import APIRouter, HTTPException, Depends, Request
from api.schemas import (
    GameInitRequest,
    GameInitData,
    GameInitApiResponse,
    GameInputRequest,
    GameInputData,
    GameInputApiResponse,
    CheckEndingData,
    CheckEndingApiResponse,
    TriggerEndingRequest,
    TriggerEndingData,
    TriggerEndingApiResponse,
)
from api.services.game_service import GameService
from api.dependencies import get_game_service
from api.utils.network import get_client_ip
from api.utils.guest_limit import (
    ensure_guest_ending_allowed,
    is_guest_ending_ip_whitelisted,
    is_guest_request,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/game", tags=["游戏管理"])


@router.get("/guest-ending-status")
async def guest_ending_status(request: Request):
    """查询当前访问者的游客结局额度状态，不做 403 拦截。"""
    client_ip = get_client_ip(request)
    is_guest = is_guest_request(request)
    whitelisted = is_guest_ending_ip_whitelisted(client_ip) if is_guest else False

    status = GameService.get_guest_ending_status(client_ip)
    if not is_guest or whitelisted:
        status["limited"] = False

    status.update({
        "is_guest": is_guest,
        "whitelisted": whitelisted,
        "has_record": bool(status.get("thread_id")),
        "client_ip_source": "X-Forwarded-For > X-Real-IP > request.client.host",
    })
    return {"code": 200, "message": "ok", "data": status}


@router.post("/init", response_model=GameInitApiResponse)
async def init_game(
    body: GameInitRequest,
    request: Request,
    game_service: GameService = Depends(get_game_service)
):
    """初始化游戏"""
    ensure_guest_ending_allowed(request)

    try:
        logger.info(f"收到初始化请求: user_id={body.user_id}, character_id={body.character_id}, game_mode={body.game_mode}")

        character_id = None
        if body.character_id:
            character_id = int(body.character_id)
        else:
            logger.error("character_id is required")
            raise HTTPException(status_code=400, detail="character_id is required")

        logger.info("开始初始化游戏会话...")
        result = game_service.init_game(
            user_id=body.user_id,
            character_id=character_id,
            game_mode=body.game_mode
        )

        logger.info(f"游戏初始化成功: thread_id={result.get('thread_id')}, user_id={result.get('user_id')}")
        return {"code": 200, "message": "ok", "data": result}
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")


@router.post("/input", response_model=GameInputApiResponse)
async def process_input(
    body: GameInputRequest,
    http_request: Request,
    game_service: GameService = Depends(get_game_service)
):
    """处理玩家输入"""
    try:
        ensure_guest_ending_allowed(http_request)

        # 尝试从user_input中解析option_id（仅接受严格格式: option:<number>）
        option_id = None
        user_input = (body.user_input or "").strip()

        option_match = re.fullmatch(r"option:(\d+)", user_input, flags=re.IGNORECASE)
        if option_match:
            option_id = int(option_match.group(1)) - 1  # 转换为0-based索引
            user_input = ""  # 清空user_input，使用选项
        elif user_input.lower().startswith("option:"):
            raise HTTPException(status_code=400, detail="无效的选项格式，应为 option:<number>")

        async def _process_with_session_lock(target_thread_id: str, input_text: str, input_option_id):
            target_session = game_service.session_manager.get_session(target_thread_id)
            if target_session and hasattr(target_session, "lock"):
                target_session.lock.acquire()
                try:
                    return await game_service.process_input(
                        thread_id=target_thread_id,
                        user_input=input_text,
                        option_id=input_option_id
                    )
                finally:
                    target_session.lock.release()
            return await game_service.process_input(
                thread_id=target_thread_id,
                user_input=input_text,
                option_id=input_option_id
            )

        try:
            result = await _process_with_session_lock(
                target_thread_id=body.thread_id,
                input_text=user_input,
                input_option_id=option_id
            )
        except ValueError as e:
            # 如果会话不存在，尝试自动恢复
            if "not found" in str(e).lower() and body.character_id:
                try:
                    # 重新初始化游戏会话
                    character_id_int = int(body.character_id)
                    init_result = game_service.init_game(
                        user_id=body.user_id,
                        character_id=character_id_int,
                        game_mode='solo'
                    )
                    new_thread_id = init_result['thread_id']

                    # 初始化故事
                    restored_story = await game_service.initialize_story(new_thread_id, character_id_int)

                    # 关键修复：旧会话的选项不重放到新会话，避免"选了A却执行新会话的A"错配
                    if option_id is not None:
                        restored_story['thread_id'] = new_thread_id
                        restored_story['session_restored'] = True
                        restored_story['need_reselect_option'] = True
                        restored_story['restored_from_thread_id'] = body.thread_id
                        return {
                            "code": 200,
                            "message": "会话已恢复，请重新选择选项",
                            "data": restored_story
                        }

                    # 非选项输入可在新会话中继续处理
                    result = await _process_with_session_lock(
                        target_thread_id=new_thread_id,
                        input_text=user_input,
                        input_option_id=option_id
                    )

                    # 在响应中返回新的thread_id，让前端更新
                    result['thread_id'] = new_thread_id
                    result['session_restored'] = True
                except Exception as restore_error:
                    raise HTTPException(
                        status_code=400,
                        detail=f"会话已过期且无法恢复: {str(e)}。请重新开始游戏。"
                    )
            else:
                raise

        # ── 游客结局记录 ──
        if result.get("is_game_finished"):
            if is_guest_request(http_request):
                client_ip = get_client_ip(http_request)
                if not is_guest_ending_ip_whitelisted(client_ip):
                    game_service.log_guest_ending(
                        client_ip=client_ip,
                        thread_id=result.get("thread_id", body.thread_id),
                        ending_type=result.get("ending_type"),
                    )

        return {"code": 200, "message": "ok", "data": result}
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"参数错误: {str(e)}")


@router.get("/check-ending/{thread_id}", response_model=CheckEndingApiResponse)
async def check_ending(
    thread_id: str,
    game_service: GameService = Depends(get_game_service)
):
    """检查是否满足结局条件"""
    try:
        result = game_service.check_ending(thread_id)
        return {"code": 200, "message": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/trigger-ending", response_model=TriggerEndingApiResponse)
async def trigger_ending(
    request: TriggerEndingRequest,
    game_service: GameService = Depends(get_game_service)
):
    """触发结局"""
    try:
        result = game_service.trigger_ending(request.thread_id)
        return {"code": 200, "message": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

