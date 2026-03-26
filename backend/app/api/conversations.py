"""
对话API路由
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.models.models import Conversation, Message, ConversationStatus, Account, User

router = APIRouter()


# ========== 请求/响应模型 ==========

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    is_ai_generated: bool
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    buyer_id: str
    buyer_nickname: Optional[str]
    item_title: Optional[str]
    item_price: Optional[float]
    status: str
    bargain_count: int
    last_message_at: Optional[str]
    message_count: int
    unread_count: int = 0


class ConversationDetail(BaseModel):
    id: str
    buyer_id: str
    buyer_nickname: Optional[str]
    item_title: Optional[str]
    item_price: Optional[float]
    status: str
    messages: List[MessageResponse]


class SendMessageRequest(BaseModel):
    content: str


class ToggleManualRequest(BaseModel):
    manual: bool


# ========== 辅助函数 ==========

async def get_current_tenant_id(user_id: str, db: AsyncSession) -> str:
    """获取当前用户的租户ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user.tenant_id


# ========== API端点 ==========

@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取对话列表"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    # 构建查询
    query = select(Conversation).where(Conversation.tenant_id == tenant_id)
    
    if account_id:
        query = query.where(Conversation.account_id == account_id)
    
    if status:
        query = query.where(Conversation.status == status)
    
    query = query.order_by(desc(Conversation.last_message_at))
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    return [
        {
            "id": conv.id,
            "buyer_id": conv.buyer_id,
            "buyer_nickname": conv.buyer_nickname,
            "item_title": conv.item_title,
            "item_price": conv.item_price,
            "status": conv.status.value,
            "bargain_count": conv.bargain_count,
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            "message_count": len(conv.messages) if conv.messages else 0,
        }
        for conv in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取对话详情"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id
            )
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    
    # 获取消息
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = messages_result.scalars().all()
    
    return {
        "id": conversation.id,
        "buyer_id": conversation.buyer_id,
        "buyer_nickname": conversation.buyer_nickname,
        "item_title": conversation.item_title,
        "item_price": conversation.item_price,
        "status": conversation.status.value,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "is_ai_generated": msg.is_ai_generated,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    data: SendMessageRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """发送人工回复"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id
            )
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    
    # 保存消息
    message = Message(
        conversation_id=conversation_id,
        role='assistant',
        content=data.content,
        is_ai_generated=False,
    )
    db.add(message)
    
    from datetime import datetime
    conversation.last_message_at = datetime.now()
    
    await db.commit()
    await db.refresh(message)
    
    # TODO: 调用AccountManager发送消息到闲鱼
    
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "is_ai_generated": message.is_ai_generated,
        "created_at": message.created_at.isoformat(),
    }


@router.post("/{conversation_id}/toggle-manual")
async def toggle_manual(
    conversation_id: str,
    data: ToggleManualRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """切换人工接管模式"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id
            )
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    
    conversation.status = (
        ConversationStatus.MANUAL if data.manual else ConversationStatus.ACTIVE
    )
    await db.commit()
    
    return {"message": "已切换到人工接管模式" if data.manual else "已切换到AI模式"}


@router.post("/{conversation_id}/close")
async def close_conversation(
    conversation_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """关闭对话"""
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id
            )
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    
    conversation.status = ConversationStatus.CLOSED
    await db.commit()
    
    return {"message": "对话已关闭"}
