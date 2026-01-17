"""API响应工具"""
from typing import Any, Optional, Dict
from fastapi.responses import JSONResponse
from api.schemas import ApiResponse


def success_response(data: Any = None, message: str = "success") -> JSONResponse:
    """成功响应"""
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": message,
            "data": data
        }
    )


def error_response(
    code: int = 400,
    message: str = "error",
    data: Any = None,
    error: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """错误响应"""
    content = {
        "code": code,
        "message": message,
        "data": data
    }
    if error:
        content["error"] = error
    
    return JSONResponse(
        status_code=code,
        content=content
    )


def not_found_response(message: str = "资源不存在") -> JSONResponse:
    """404响应"""
    return error_response(code=404, message=message)


def unauthorized_response(message: str = "未授权") -> JSONResponse:
    """401响应"""
    return error_response(code=401, message=message)


def forbidden_response(message: str = "没有权限访问") -> JSONResponse:
    """403响应"""
    return error_response(code=403, message=message)


def server_error_response(message: str = "服务器错误") -> JSONResponse:
    """500响应"""
    return error_response(code=500, message=message)

