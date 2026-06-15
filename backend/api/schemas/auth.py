"""认证相关Pydantic数据模型"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class GuestRequest(BaseModel):
    """游客创建请求"""
    device_fingerprint: Optional[str] = Field(None, description="设备指纹（可选，用于限制游客滥用）")
    ip_address: Optional[str] = Field(None, description="客户端IP（可选，由中间件自动填充）")


class RegisterRequest(BaseModel):
    """用户注册请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    username: str = Field(..., min_length=3, max_length=50, description="用户名（3-50字符）")
    password: str = Field(..., min_length=8, max_length=128, description="密码（8-128字符）")
    guest_token: Optional[str] = Field(None, description="游客token（用于升级游客账户）")


class LoginRequest(BaseModel):
    """用户登录请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class RefreshTokenRequest(BaseModel):
    """刷新token请求"""
    refresh_token: str = Field(..., description="刷新token")


class LogoutRequest(BaseModel):
    """登出请求"""
    access_token: Optional[str] = Field(None, description="访问token（可选，用于吊销）")
    refresh_token: Optional[str] = Field(None, description="刷新token（可选，用于吊销）")


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str = Field(..., description="访问token")
    refresh_token: str = Field(..., description="刷新token")
    token_type: str = Field(default="bearer", description="token类型")
    expires_in: int = Field(..., description="访问token过期时间（秒）")
    user_id: str = Field(..., description="用户ID")
    user_type: str = Field(..., description="用户类型：guest | registered")


class UserResponse(BaseModel):
    """用户信息响应"""
    user_id: str = Field(..., description="用户ID")
    user_type: str = Field(..., description="用户类型：guest | registered")
    username: Optional[str] = Field(None, description="用户名（游客为空）")
    email: Optional[str] = Field(None, description="邮箱（游客为空）")
    created_at: datetime = Field(..., description="创建时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    free_plays_remaining: int = Field(..., description="剩余免费游玩次数")


class GuestUpgradeRequest(BaseModel):
    """游客升级为注册用户请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    username: str = Field(..., min_length=3, max_length=50, description="用户名（3-50字符）")
    password: str = Field(..., min_length=8, max_length=128, description="密码（8-128字符）")


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码（8-128字符）")


class PasswordResetRequest(BaseModel):
    """密码重置请求"""
    email: EmailStr = Field(..., description="邮箱地址")


class PasswordResetConfirmRequest(BaseModel):
    """密码重置确认请求"""
    token: str = Field(..., description="重置token")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码（8-128字符）")