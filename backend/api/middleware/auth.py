"""JWT认证中间件"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from jose import JWTError, jwt
from api.services.auth_service import AuthService, JWT_SECRET, JWT_ALGORITHM
from api.schemas.auth import UserResponse
from database.db_manager import DatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer认证方案
security = HTTPBearer()


async def get_auth_service() -> AuthService:
    """获取认证服务实例"""
    db_manager = DatabaseManager()
    return AuthService(db_manager)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    获取当前认证用户
    从Authorization头中提取JWT token并验证
    """
    try:
        token = credentials.credentials
        user = await auth_service.get_current_user(token)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"认证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[UserResponse]:
    """
    获取当前认证用户（可选）
    如果提供了token则验证，否则返回None
    用于可选认证的端点
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user = await auth_service.get_current_user(token)
        return user
    except HTTPException:
        return None
    except Exception as e:
        logger.warning(f"可选认证失败: {e}")
        return None


async def get_current_guest_or_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    获取当前用户（游客或注册用户）
    如果没有token，创建一个新的游客用户
    """
    if not credentials:
        # 没有token，创建游客用户
        from api.schemas.auth import GuestRequest
        guest_request = GuestRequest()
        token_response = await auth_service.create_guest(guest_request)
        # 获取刚创建的用户信息
        user = await auth_service.get_current_user(token_response.access_token)
        return user
    
    try:
        token = credentials.credentials
        user = await auth_service.get_current_user(token)
        return user
    except HTTPException:
        # token无效，创建新的游客用户
        from api.schemas.auth import GuestRequest
        guest_request = GuestRequest()
        token_response = await auth_service.create_guest(guest_request)
        user = await auth_service.get_current_user(token_response.access_token)
        return user
    except Exception as e:
        logger.warning(f"获取用户失败，创建游客: {e}")
        from api.schemas.auth import GuestRequest
        guest_request = GuestRequest()
        token_response = await auth_service.create_guest(guest_request)
        user = await auth_service.get_current_user(token_response.access_token)
        return user


async def require_registered_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    要求注册用户
    游客用户会被拒绝访问
    """
    if current_user.user_type != "registered":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此功能仅限注册用户使用"
        )
    return current_user


async def require_admin_user(
    current_user: UserResponse = Depends(require_registered_user)
) -> UserResponse:
    """
    要求管理员用户
    需要额外的管理员权限检查
    """
    # TODO: 实现管理员权限检查
    # 暂时允许所有注册用户访问管理功能
    return current_user