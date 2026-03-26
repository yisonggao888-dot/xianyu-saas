"""
认证API路由
"""
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token, verify_password,
    get_password_hash, decode_token
)
from app.db.database import get_db
from app.models.models import User, Tenant, UserRole, TenantPlan

router = APIRouter()
security = HTTPBearer()


# ========== 请求/响应模型 ==========

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    tenant_name: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@example.com",
                "password": "123456",
                "tenant_name": "我的店铺"
            }
        }


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    id: str
    email: str
    name: Optional[str]
    role: str
    tenant: dict


# ========== API端点 ==========

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建租户
    tenant = Tenant(
        name=data.tenant_name,
        plan=TenantPlan.FREE,
        max_accounts=settings.FREE_PLAN_MAX_ACCOUNTS,
        max_messages_per_month=settings.FREE_PLAN_MAX_MESSAGES,
    )
    db.add(tenant)
    await db.flush()  # 获取tenant.id
    
    # 创建用户
    user = User(
        tenant_id=tenant.id,
        email=data.email,
        password_hash=get_password_hash(data.password),
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    
    # 生成Token
    access_token = create_access_token({"sub": user.id, "tenant_id": tenant.id})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    # 查询用户
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )
    
    # 生成Token
    access_token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """刷新访问令牌"""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )
    
    # 生成新Token
    access_token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id})
    new_refresh_token = create_refresh_token({"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserInfo)
async def get_me(
    user_id: str = Depends(lambda: None),  # TODO: 实现JWT依赖
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户信息"""
    # TODO: 从JWT获取user_id
    # result = await db.execute(
    #     select(User, Tenant).join(Tenant).where(User.id == user_id)
    # )
    # user, tenant = result.first()
    
    # Mock数据
    return UserInfo(
        id="mock-user-id",
        email="admin@example.com",
        name="管理员",
        role="admin",
        tenant={
            "id": "mock-tenant-id",
            "name": "我的店铺",
            "plan": "free"
        }
    )
