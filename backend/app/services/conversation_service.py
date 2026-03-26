"""
对话服务
"""
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.models import (
    Conversation, ConversationStatus, Message, Account,
    AccountStatus
)
from app.services.ai_engine import AIReplyEngine


class ConversationService:
    """对话服务"""
    
    def __init__(self, db: AsyncSession, ai_engine: AIReplyEngine):
        self.db = db
        self.ai_engine = ai_engine
    
    async def handle_incoming_message(
        self,
        account_id: str,
        chat_id: str,
        sender_id: str,
        content: str,
    ) -> Optional[str]:
        """
        处理收到的消息
        
        Returns:
            AI回复内容，如果无需回复则返回None
        """
        # 获取或创建对话
        conversation = await self._get_or_create_conversation(
            account_id=account_id,
            chat_id=chat_id,
            sender_id=sender_id,
        )
        
        # 检查是否人工接管
        if conversation.status == ConversationStatus.MANUAL:
            logger.info(f"对话 {conversation.id} 处于人工接管模式，跳过AI回复")
            return None
        
        # 检查AI是否启用
        account = await self.db.get(Account, account_id)
        if not account or not account.ai_enabled:
            return None
        
        # 保存用户消息
        user_message = Message(
            conversation_id=conversation.id,
            role='user',
            content=content,
        )
        self.db.add(user_message)
        
        # 更新对话时间
        conversation.last_message_at = datetime.now()
        await self.db.commit()
        
        # 获取对话历史
        history = await self._get_conversation_history(conversation.id)
        
        # 构建商品描述
        item_desc = self._build_item_description(conversation)
        
        # 生成AI回复
        reply = await self.ai_engine.generate_reply(
            user_msg=content,
            item_desc=item_desc,
            conversation_history=history,
            bargain_count=conversation.bargain_count,
        )
        
        if not reply:
            return None
        
        # 保存AI回复
        ai_message = Message(
            conversation_id=conversation.id,
            role='assistant',
            content=reply,
            is_ai_generated=True,
            ai_model=account.ai_model,
        )
        self.db.add(ai_message)
        
        # 更新账号消息计数
        account.message_count_this_month += 1
        
        await self.db.commit()
        
        logger.info(f"对话 {conversation.id} AI回复: {reply[:100]}...")
        
        return reply
    
    async def _get_or_create_conversation(
        self,
        account_id: str,
        chat_id: str,
        sender_id: str,
    ) -> Conversation:
        """获取或创建对话"""
        # 查找现有对话
        result = await self.db.execute(
            select(Conversation).where(
                and_(
                    Conversation.account_id == account_id,
                    Conversation.xianyu_chat_id == chat_id,
                    Conversation.status != ConversationStatus.CLOSED,
                )
            )
        )
        conversation = result.scalar_one_or_none()
        
        if conversation:
            return conversation
        
        # 获取账号信息
        account = await self.db.get(Account, account_id)
        
        # 创建新对话
        conversation = Conversation(
            tenant_id=account.tenant_id,
            account_id=account_id,
            xianyu_chat_id=chat_id,
            buyer_id=sender_id,
            status=ConversationStatus.ACTIVE,
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        
        logger.info(f"创建新对话: {conversation.id}")
        
        return conversation
    
    async def _get_conversation_history(self, conversation_id: str) -> List[dict]:
        """获取对话历史"""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(20)
        )
        messages = result.scalars().all()
        
        # 反转顺序，最旧的在前
        messages = list(reversed(messages))
        
        return [
            {
                'role': msg.role,
                'content': msg.content,
            }
            for msg in messages
        ]
    
    def _build_item_description(self, conversation: Conversation) -> str:
        """构建商品描述"""
        parts = []
        
        if conversation.item_title:
            parts.append(f"商品名称: {conversation.item_title}")
        
        if conversation.item_price:
            parts.append(f"售价: {conversation.item_price}元")
        
        if not parts:
            return "商品信息暂无"
        
        return " | ".join(parts)
    
    async def toggle_manual_mode(
        self,
        conversation_id: str,
        manual: bool,
    ) -> bool:
        """切换人工接管模式"""
        conversation = await self.db.get(Conversation, conversation_id)
        if not conversation:
            return False
        
        conversation.status = (
            ConversationStatus.MANUAL if manual else ConversationStatus.ACTIVE
        )
        await self.db.commit()
        
        return True
    
    async def send_manual_reply(
        self,
        conversation_id: str,
        content: str,
    ) -> bool:
        """发送人工回复"""
        conversation = await self.db.get(Conversation, conversation_id)
        if not conversation:
            return False
        
        # 保存消息
        message = Message(
            conversation_id=conversation_id,
            role='assistant',
            content=content,
            is_ai_generated=False,
        )
        self.db.add(message)
        
        conversation.last_message_at = datetime.now()
        await self.db.commit()
        
        return True
