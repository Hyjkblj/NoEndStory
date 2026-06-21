"""Guest ending limit helpers."""
import ipaddress
import os
from functools import lru_cache

from fastapi import HTTPException, Request

from api.services.game_service import GameService
from api.utils.network import get_client_ip
from utils.logger import get_logger

logger = get_logger(__name__)

GUEST_ENDING_LIMIT_CODE = "GUEST_ENDING_LIMIT"
GUEST_ENDING_LIMIT_MESSAGE = "这次游客体验已经完成，24小时后可再次开启。注册账号可解锁无限旅程。"


@lru_cache(maxsize=1)
def _guest_ending_whitelist() -> tuple[str, ...]:
    raw = os.getenv("GUEST_ENDING_IP_WHITELIST", "127.0.0.1,::1")
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def is_guest_request(request: Request) -> bool:
    """无 Authorization header 的请求按游客处理。"""
    return not request.headers.get("Authorization")


def is_guest_ending_ip_whitelisted(client_ip: str) -> bool:
    """检查 IP 是否在游客结局限制白名单中，支持精确 IP 与 CIDR。"""
    for item in _guest_ending_whitelist():
        if item == client_ip:
            return True

        if "/" not in item:
            continue

        try:
            if ipaddress.ip_address(client_ip) in ipaddress.ip_network(item, strict=False):
                return True
        except ValueError:
            logger.warning("游客结局白名单配置无效: %s", item)

    return False


def guest_ending_limit_exception() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "code": GUEST_ENDING_LIMIT_CODE,
            "message": GUEST_ENDING_LIMIT_MESSAGE,
            "hint": "register",
        },
    )


def ensure_guest_ending_allowed(request: Request) -> None:
    """若游客过去 24 小时内已完成结局，则阻止新的成本动作。"""
    if not is_guest_request(request):
        return

    client_ip = get_client_ip(request)
    if is_guest_ending_ip_whitelisted(client_ip):
        return

    if GameService.has_guest_ended_today(client_ip):
        logger.info("游客结局额度拦截: ip=%s path=%s", client_ip, request.url.path)
        raise guest_ending_limit_exception()
