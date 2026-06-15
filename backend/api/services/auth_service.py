"""认证服务：处理用户认证、token管理、密码哈希等"""
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, and_
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from api.schemas.auth import (
    GuestRequest, RegisterRequest, LoginRequest, 
    RefreshTokenRequest, LogoutRequest, TokenResponse,
    UserResponse, GuestUpgradeRequest, PasswordChangeRequest
)
from database.db_manager import DatabaseManager
from utils.logger import get_logger
import os

logger = get_logger(__name__)

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# 用户类型常量
USER_TYPE_GUEST = "guest"
USER_TYPE_REGISTERED = "registered"


class AuthService:
    """认证服务类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        # 注意：这里需要导入实际的SQLAlchemy模型，暂时用字典模拟
        # 实际实现时需要创建User、UserToken、GamePlay等模型
        self._users = {}  # 临时存储，实际应使用数据库
        self._tokens = {}  # 临时存储，实际应使用数据库
    
    def _generate_user_id(self) -> str:
        """生成用户ID"""
        return str(uuid.uuid4())
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def _create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def _create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def _hash_token(self, token: str) -> str:
        """哈希token（用于存储）"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _generate_guest_username(self) -> str:
        """生成游客用户名"""
        return f"guest_{secrets.token_hex(4)}"
    
    async def create_guest(self, request: GuestRequest) -> TokenResponse:
        """
        创建游客用户
        返回访问token和刷新token
        """
        try:
            user_id = self._generate_user_id()
            guest_username = self._generate_guest_username()
            
            # 创建用户记录（实际应存入数据库）
            user_data = {
                "user_id": user_id,
                "user_type": USER_TYPE_GUEST,
                "username": guest_username,
                "email": None,
                "password_hash": None,
                "created_at": datetime.utcnow(),
                "last_login_at": datetime.utcnow(),
                "free_plays_remaining": 1,  # 游客初始免费次数
                "device_fingerprint": request.device_fingerprint,
                "ip_address": request.ip_address
            }
            self._users[user_id] = user_data
            
            # 创建token
            access_token = self._create_access_token({"sub": user_id, "user_type": USER_TYPE_GUEST})
            refresh_token = self._create_refresh_token({"sub": user_id, "user_type": USER_TYPE_GUEST})
            
            # 存储token哈希（实际应存入数据库）
            token_hash = self._hash_token(refresh_token)
            self._tokens[token_hash] = {
                "user_id": user_id,
                "token_hash": token_hash,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                "is_revoked": False
            }
            
            logger.info(f"创建游客用户: {user_id}")
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user_id=user_id,
                user_type=USER_TYPE_GUEST
            )
            
        except Exception as e:
            logger.error(f"创建游客用户失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建游客用户失败"
            )
    
    async def register_user(self, request: RegisterRequest) -> TokenResponse:
        """
        注册新用户
        可选：升级游客账户
        """
        try:
            # 检查邮箱是否已注册
            # 实际应查询数据库
            for user in self._users.values():
                if user.get("email") == request.email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="邮箱已被注册"
                    )
            
            # 检查用户名是否已存在
            for user in self._users.values():
                if user.get("username") == request.username:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="用户名已被使用"
                    )
            
            # 如果有游客token，尝试升级
            guest_user_id = None
            if request.guest_token:
                try:
                    payload = jwt.decode(request.guest_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                    if payload.get("user_type") == USER_TYPE_GUEST:
                        guest_user_id = payload.get("sub")
                except JWTError:
                    pass  # 无效的游客token，忽略
            
            user_id = guest_user_id or self._generate_user_id()
            password_hash = self._hash_password(request.password)
            
            # 创建或更新用户记录
            user_data = {
                "user_id": user_id,
                "user_type": USER_TYPE_REGISTERED,
                "username": request.username,
                "email": request.email,
                "password_hash": password_hash,
                "created_at": datetime.utcnow(),
                "last_login_at": datetime.utcnow(),
                "free_plays_remaining": 3,  # 注册用户初始免费次数
                "device_fingerprint": None,
                "ip_address": None
            }
            self._users[user_id] = user_data
            
            # 创建token
            access_token = self._create_access_token({"sub": user_id, "user_type": USER_TYPE_REGISTERED})
            refresh_token = self._create_refresh_token({"sub": user_id, "user_type": USER_TYPE_REGISTERED})
            
            # 存储token哈希
            token_hash = self._hash_token(refresh_token)
            self._tokens[token_hash] = {
                "user_id": user_id,
                "token_hash": token_hash,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                "is_revoked": False
            }
            
            logger.info(f"注册用户: {user_id} ({request.username})")
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user_id=user_id,
                user_type=USER_TYPE_REGISTERED
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"注册用户失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="注册用户失败"
            )
    
    async def login_user(self, request: LoginRequest) -> TokenResponse:
        """用户登录"""
        try:
            # 查找用户（实际应查询数据库）
            user = None
            for u in self._users.values():
                if u.get("email") == request.email:
                    user = u
                    break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="邮箱或密码错误"
                )
            
            # 验证密码
            if not user.get("password_hash") or not self._verify_password(request.password, user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="邮箱或密码错误"
                )
            
            # 更新最后登录时间
            user["last_login_at"] = datetime.utcnow()
            
            # 创建token
            access_token = self._create_access_token({"sub": user["user_id"], "user_type": user["user_type"]})
            refresh_token = self._create_refresh_token({"sub": user["user_id"], "user_type": user["user_type"]})
            
            # 存储token哈希
            token_hash = self._hash_token(refresh_token)
            self._tokens[token_hash] = {
                "user_id": user["user_id"],
                "token_hash": token_hash,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                "is_revoked": False
            }
            
            logger.info(f"用户登录: {user['user_id']} ({user.get('username')})")
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user_id=user["user_id"],
                user_type=user["user_type"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"用户登录失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="用户登录失败"
            )
    
    async def refresh_token(self, request: RefreshTokenRequest) -> TokenResponse:
        """刷新token"""
        try:
            # 解码刷新token
            payload = jwt.decode(request.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的刷新token"
                )
            
            user_id = payload.get("sub")
            user_type = payload.get("user_type")
            
            # 检查token是否被吊销（实际应查询数据库）
            token_hash = self._hash_token(request.refresh_token)
            token_data = self._tokens.get(token_hash)
            if not token_data or token_data.get("is_revoked"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="刷新token已失效"
                )
            
            # 吊销旧token
            token_data["is_revoked"] = True
            
            # 创建新token
            new_access_token = self._create_access_token({"sub": user_id, "user_type": user_type})
            new_refresh_token = self._create_refresh_token({"sub": user_id, "user_type": user_type})
            
            # 存储新token哈希
            new_token_hash = self._hash_token(new_refresh_token)
            self._tokens[new_token_hash] = {
                "user_id": user_id,
                "token_hash": new_token_hash,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                "is_revoked": False
            }
            
            logger.info(f"刷新token: {user_id}")
            
            return TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user_id=user_id,
                user_type=user_type
            )
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新token"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"刷新token失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="刷新token失败"
            )
    
    async def logout_user(self, request: LogoutRequest) -> Dict[str, str]:
        """用户登出，吊销token"""
        try:
            # 吊销访问token（如果提供）
            if request.access_token:
                try:
                    payload = jwt.decode(request.access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                    # 访问token通常是无状态的，这里只是记录日志
                    logger.info(f"用户登出（访问token）: {payload.get('sub')}")
                except JWTError:
                    pass  # 无效的访问token，忽略
            
            # 吊销刷新token（如果提供）
            if request.refresh_token:
                token_hash = self._hash_token(request.refresh_token)
                token_data = self._tokens.get(token_hash)
                if token_data:
                    token_data["is_revoked"] = True
                    logger.info(f"吊销刷新token: {token_data.get('user_id')}")
            
            return {"message": "登出成功"}
            
        except Exception as e:
            logger.error(f"用户登出失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="用户登出失败"
            )
    
    async def get_current_user(self, token: str) -> UserResponse:
        """获取当前用户信息（用于中间件）"""
        try:
            # 解码访问token
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的访问token"
                )
            
            user_id = payload.get("sub")
            user_type = payload.get("user_type")
            
            # 获取用户信息（实际应查询数据库）
            user_data = self._users.get(user_id)
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户不存在"
                )
            
            return UserResponse(
                user_id=user_data["user_id"],
                user_type=user_data["user_type"],
                username=user_data.get("username"),
                email=user_data.get("email"),
                created_at=user_data["created_at"],
                last_login_at=user_data.get("last_login_at"),
                free_plays_remaining=user_data.get("free_plays_remaining", 0)
            )
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的访问token"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取用户信息失败"
            )
    
    async def upgrade_guest(self, request: GuestUpgradeRequest, current_user: UserResponse) -> TokenResponse:
        """游客升级为注册用户"""
        try:
            if current_user.user_type != USER_TYPE_GUEST:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="只有游客账户可以升级"
                )
            
            # 检查邮箱是否已被注册
            for user in self._users.values():
                if user.get("email") == request.email and user["user_id"] != current_user.user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="邮箱已被注册"
                    )
            
            # 检查用户名是否已被使用
            for user in self._users.values():
                if user.get("username") == request.username and user["user_id"] != current_user.user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="用户名已被使用"
                    )
            
            # 更新用户信息
            user_data = self._users[current_user.user_id]
            user_data["user_type"] = USER_TYPE_REGISTERED
            user_data["username"] = request.username
            user_data["email"] = request.email
            user_data["password_hash"] = self._hash_password(request.password)
            user_data["free_plays_remaining"] = 3  # 升级后给予注册用户的免费次数
            
            # 创建新token
            access_token = self._create_access_token({"sub": current_user.user_id, "user_type": USER_TYPE_REGISTERED})
            refresh_token = self._create_refresh_token({"sub": current_user.user_id, "user_type": USER_TYPE_REGISTERED})
            
            # 存储token哈希
            token_hash = self._hash_token(refresh_token)
            self._tokens[token_hash] = {
                "user_id": current_user.user_id,
                "token_hash": token_hash,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                "is_revoked": False
            }
            
            logger.info(f"游客升级: {current_user.user_id} -> {request.username}")
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user_id=current_user.user_id,
                user_type=USER_TYPE_REGISTERED
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"游客升级失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="游客升级失败"
            )
    
    async def change_password(self, request: PasswordChangeRequest, current_user: UserResponse) -> Dict[str, str]:
        """修改密码"""
        try:
            if current_user.user_type != USER_TYPE_REGISTERED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="只有注册用户可以修改密码"
                )
            
            user_data = self._users.get(current_user.user_id)
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="用户不存在"
                )
            
            # 验证当前密码
            if not user_data.get("password_hash") or not self._verify_password(request.current_password, user_data["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="当前密码错误"
                )
            
            # 更新密码
            user_data["password_hash"] = self._hash_password(request.new_password)
            
            logger.info(f"用户修改密码: {current_user.user_id}")
            
            return {"message": "密码修改成功"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"修改密码失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="修改密码失败"
            )