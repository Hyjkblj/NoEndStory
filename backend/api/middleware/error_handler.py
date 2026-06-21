"""统一异常处理中间件"""
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from api.exceptions import ServiceException
import logging

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    """将 FastAPI HTTPException 转为统一 {code, message, data:null} 格式"""
    logger.warning(
        f"HTTP异常: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    detail = exc.detail
    content = {
        "code": exc.status_code,
        "message": str(detail),
        "data": None,
    }

    if isinstance(detail, dict):
        message = detail.get("message")
        content["message"] = message if isinstance(message, str) else str(detail)
        content["detail"] = detail

        business_code = detail.get("code")
        if isinstance(business_code, str):
            content["error_code"] = business_code

        if "hint" in detail:
            content["hint"] = detail.get("hint")

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


async def service_exception_handler(request: Request, exc: ServiceException):
    """处理ServiceException异常 — 统一 {code, message, data:null} 格式"""
    logger.error(
        f"Service异常: {exc.message}",
        extra={
            "code": exc.code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常 — 统一 {code, message, data:null} 格式"""
    logger.exception(
        f"未处理的异常: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": str(exc) if logger.level == logging.DEBUG else "服务器内部错误",
            "data": None
        }
    )
