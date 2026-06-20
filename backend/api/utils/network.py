"""网络工具函数"""
from fastapi import Request


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP 地址

    优先级：X-Forwarded-For > X-Real-IP > request.client.host
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"
