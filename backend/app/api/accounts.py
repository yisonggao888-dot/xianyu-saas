"""
闲鱼账号API路由
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, encrypt_cookie, decrypt_cookie
from app.db.database import get_db
from app.models.models import Account, AccountStatus, User

router = APIRouter()


# ========== 请求/响应模型 ==========

class AccountCreate(BaseModel):
    name: str
    cookies: str


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    cookies: Optional[str] = None
    ai_enabled: Optional[bool] = None
    status: Optional[AccountStatus] = None


class AccountResponse(BaseModel):
    id: str
    name: str
    xianyu_nickname: Optional[str]
    status: str
    last_online_at: Optional[str]
    message_count_this_month: int
    ai_enabled: bool
    created_at: str


# ========== 辅助函数 ==========

async def get_current_tenant_id(user_id: str, db: AsyncSession) -> str:
    """获取当前用户的租户ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user.tenant_id


# ========== API端点 ==========

@router.get("/", response_model=List[AccountResponse])
async def list_accounts(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取账号列表"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(Account).where(Account.tenant_id == tenant_id)
    )
    accounts = result.scalars().all()
    
    return [
        {
            "id": acc.id,
            "name": acc.name,
            "xianyu_nickname": acc.xianyu_nickname,
            "status": acc.status.value,
            "last_online_at": acc.last_online_at.isoformat() if acc.last_online_at else None,
            "message_count_this_month": acc.message_count_this_month,
            "ai_enabled": acc.ai_enabled,
            "created_at": acc.created_at.isoformat(),
        }
        for acc in accounts
    ]


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: AccountCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """创建闲鱼账号"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    # TODO: 检查租户账号数量限制
    
    # 加密Cookie
    encrypted_cookies = encrypt_cookie(data.cookies)
    
    account = Account(
        tenant_id=tenant_id,
        name=data.name,
        cookies=encrypted_cookies,
        status=AccountStatus.PAUSED,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    return {
        "id": account.id,
        "name": account.name,
        "xianyu_nickname": account.xianyu_nickname,
        "status": account.status.value,
        "last_online_at": None,
        "message_count_this_month": 0,
        "ai_enabled": account.ai_enabled,
        "created_at": account.created_at.isoformat(),
    }


@router.get("/{account_id}")
async def get_account(
    account_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取账号详情"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(Account).where(and_(Account.id == account_id, Account.tenant_id == tenant_id))
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    
    return {
        "id": account.id,
        "name": account.name,
        "xianyu_nickname": account.xianyu_nickname,
        "status": account.status.value,
        "ai_enabled": account.ai_enabled,
        "ai_model": account.ai_model,
        # 不返回cookies
    }


@router.put("/{account_id}")
async def update_account(
    account_id: str,
    data: AccountUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """更新账号"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(Account).where(and_(Account.id == account_id, Account.tenant_id == tenant_id))
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    
    # 更新字段
    if data.name is not None:
        account.name = data.name
    if data.cookies is not None:
        account.cookies = encrypt_cookie(data.cookies)
    if data.ai_enabled is not None:
        account.ai_enabled = data.ai_enabled
    if data.status is not None:
        account.status = data.status
    
    await db.commit()
    await db.refresh(account)
    
    return {"message": "更新成功"}


@router.delete("/{account_id}")
async def delete_account(
    account_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """删除账号"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(Account).where(and_(Account.id == account_id, Account.tenant_id == tenant_id))
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    
    await db.delete(account)
    await db.commit()
    
    return {"message": "删除成功"}
