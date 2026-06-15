"""认证API路由"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
from api.schemas.auth import (
    GuestRequest, RegisterRequest, LoginRequest, 
    RefreshTokenRequest, LogoutRequest, TokenResponse,
    UserResponse, GuestUpgradeRequest, PasswordChangeRequest,
    PasswordResetRequest, PasswordResetConfirmRequest
)
from api.services.auth_service import AuthService
from api.middleware.auth import (
    get_current_user, get_current_user_optional, 
    get_current_guest_or_user, require_registered_user,
    get_auth_service
)
from api.response import success_response, error_response
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["认证管理"])


@router.post("/guest", response_model=Dict[str, Any])
async def create_guest(
    request: GuestRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    创建游客用户
    - 自动生成游客用户名
    - 签发JWT访问token和刷新token
    - 返回用户信息和token
    """
    try:
        token_response = await auth_service.create_guest(request)
        return success_response(
            data={
                "user_id": token_response.user_id,
                "user_type": token_response.user_type,
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "expires_in": token_response.expires_in
            },
            message="游客用户创建成功"
        )
    except HTTPException as e:
        return error_response(code=e.status_code, message=e.detail)
    except Exception as e:
        logger.error(f"创建游客用户失败: {e}")
        return error_response(code=500, message="创建游客用户失败")


@router.post("/register", response_model=Dict[str, Any])
async def register_user(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户注册
    - 邮箱注册（可升级游客）
    - 密码哈希存储
    - 签发JWT访问token和刷新token
    """
    try:
        token_response = await auth_service.register_user(request)
        return success_response(
            data={
                "user_id": token_response.user_id,
                "user_type": token_response.user_type,
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "expires_in": token_response.expires_in
            },
            message="用户注册成功"
        )
    except HTTPException as e:
        return error_response(code=e.status_code, message=e.detail)
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        return error_response(code=500, message="用户注册失败")


@router.post("/login", response_model=Dict[str, Any])
async def login_user(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户登录
    - 邮箱+密码登录
    - bcrypt密码验证
    - 签发JWT访问token和刷新token
    """
    try:
        token_response = await auth_service.login_user(request)
        return success_response(
            data={
                "user_id": token_response.user_id,
                "user_type": token_response.user_type,
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "expires_in": token_response.expires_in
            },
            message="登录成功"
        )
    except HTTPException as e:
        return error_response(code=e.status_code, message=e.detail)
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        return error_response(code=500, message="用户登录失败")


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    刷新token
    - 使用刷新token获取新的访问token
    - 刷新token轮换（旧token失效）
    """
    try:
        token_response = await auth_service.refresh_token(request)
        return success_response(
            data={
                "user_id": token_response.user_id,
                "user_type": token_response.user_type,
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "expires_in": token_response.expires_in
            },
            message="token刷新成功"
        )
    except HTTPException as e:
        return error_response(code=e.status_code, message=e.detail)
    except Exception as e:
        logger.error(f"刷新token失败: {e}")
        return error_response(code=500, message="刷新token失败")


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    获取当前用户信息
    - 需要有效的访问token
    - 返回用户基本信息
    """
    try:
        return success_response(
            data={
                "user_id": current_user.user_id,
                "user_type": current_user.user_type,
                "username": current_user.username,
                "email": current_user.email,
                "created_at": current_user.created_at.isoformat(),
                "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
                "free_plays_remaining": current_user.free_plays_remaining
            },
            message="获取用户信息成功"
        )
    except HTTPException as e:
        return error_response(code=e.status_code, message=e.detail)
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return error_response(code=500, message="获取用户信息失败")


@router.post("/logout", response_model=Dict[str, Any])
async def logout_user(
    request: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户登出
    - 吊销刷新token
    - 访问token通常是无状态的，不需要吊销
    """
    try:
        result = await auth_service.logout_user(request)
        return success_response(
            data=result,
            message="登出成功"
        )
    except HTTPException as e:
        return error_response(code=e.status_code, message=e.detail)
    except Exception as e:
        logger.error(f"用户登出失败: {e}")
        return error_response(code=500, message="用户登出失败")


@router.post("/upgrade", response_model=Dict[str, Any])
async def upgrade_guest(
    request: GuestUpgradeRequest,
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    游客升级为注册用户
    - 保留游戏记录
    - 升级为注册用户
    """
    try:
        token_response = await auth_service.upgrade_guest(request, current_user)
        return success_response(
            data={
                "user_id": token_response.user_id,
                "user_type": token_response.user_type,
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "expires_in": token_response.expires_in
            },
            message="游客升级成功"
        )
    except HTTPException as e:
        return error_response(code=e.status_code, message=e.detail)
    except Exception as e:
        logger.error(f"游客升级失败: {e}")
        return error_response(code=500, message="游客升级失败")


@router.post("/change-password", response_model=Dict[str, Any])
async def change_password(
    request: PasswordChangeRequest,
    current_user: UserResponse = Depends(require_registered_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    修改密码
    - 仅限注册用户
    - 验证当前密码
    - 更新为新密码
    """
    try:
        result = await auth_service.change_password(request, current_user)
        return success_response(
            data=result,
            message="密码修改成功"
        )
    except HTTPException as e:
        return error_response(code=e.status_code, message=e.detail)
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return error_response(code=500, message="修改密码失败")


@router.post("/reset-password", response_model=Dict[str, Any])
async def reset_password(
    request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    请求密码重置
    - 发送重置邮件（TODO: 实现邮件发送）
    - 生成重置token
    """
    try:
        # TODO: 实现密码重置邮件发送
        # 暂时返回成功，实际需要发送邮件
        return success_response(
            data={"message": "如果邮箱存在，重置邮件已发送"},
            message="密码重置请求已处理"
        )
    except Exception as e:
        logger.error(f"密码重置请求失败: {e}")
        return error_response(code=500, message="密码重置请求失败")


@router.post("/reset-password/confirm", response_model=Dict[str, Any])
async def confirm_reset_password(
    request: PasswordResetConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    确认密码重置
    - 使用重置token
    - 设置新密码
    """
    try:
        # TODO: 实现密码重置确认
        # 暂时返回成功，实际需要验证token并更新密码
        return success_response(
            data={"message": "密码重置成功"},
            message="密码重置成功"
        )
    except Exception as e:
        logger.error(f"密码重置确认失败: {e}")
        return error_response(code=500, message="密码重置确认失败")