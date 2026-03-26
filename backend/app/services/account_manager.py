"""
多账号连接管理器
"""
import asyncio
from typing import Dict, Optional, Callable
from datetime import datetime

from loguru import logger

from app.services.ws_connection import XianyuWebSocketConnection
from app.services.ai_engine import AIReplyEngine
from app.services.conversation_service import ConversationService


class AccountManager:
    """多账号管理器"""
    
    def __init__(
        self,
        db_session_factory,
        ai_engine: Optional[AIReplyEngine] = None,
    ):
        self.db_session_factory = db_session_factory
        self.ai_engine = ai_engine or AIReplyEngine()
        
        # 账号连接池
        self.connections: Dict[str, XianyuWebSocketConnection] = {}
        
        # 运行状态
        self.running = False
    
    async def start_account(self, account_id: str, cookies: str):
        """启动单个账号"""
        if account_id in self.connections:
            logger.warning(f"账号 {account_id} 已在运行")
            return
        
        # 创建连接
        conn = XianyuWebSocketConnection(
            account_id=account_id,
            cookies=cookies,
            message_callback=self._on_message,
            ai_engine=self.ai_engine,
        )
        
        self.connections[account_id] = conn
        
        # 启动连接
        asyncio.create_task(conn.start())
        
        logger.info(f"账号 {account_id} 启动中...")
    
    async def stop_account(self, account_id: str):
        """停止单个账号"""
        conn = self.connections.get(account_id)
        if not conn:
            return
        
        await conn.stop()
        del self.connections[account_id]
        
        logger.info(f"账号 {account_id} 已停止")
    
    async def stop_all(self):
        """停止所有账号"""
        logger.info("停止所有账号...")
        
        tasks = []
        for account_id, conn in list(self.connections.items()):
            tasks.append(conn.stop())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.connections.clear()
    
    async def send_message(self, account_id: str, chat_id: str, to_id: str, text: str):
        """发送消息"""
        conn = self.connections.get(account_id)
        if not conn:
            raise Exception(f"账号 {account_id} 未在线")
        
        await conn.send_message(chat_id, to_id, text)
    
    def get_account_status(self, account_id: str) -> dict:
        """获取账号状态"""
        conn = self.connections.get(account_id)
        if not conn:
            return {
                'online': False,
                'message_count': 0,
            }
        
        return {
            'online': conn.connected,
            'message_count': conn.message_count,
            'last_message_at': conn.last_message_at.isoformat() if conn.last_message_at else None,
        }
    
    async def _on_message(
        self,
        account_id: str,
        chat_id: str,
        sender_id: str,
        content: str,
        raw_data: dict,
    ):
        """收到消息回调"""
        logger.info(f"[Account {account_id}] 收到消息: {content[:100]}")
        
        # 使用ConversationService处理消息
        async with self.db_session_factory() as db:
            service = ConversationService(db, self.ai_engine)
            
            reply = await service.handle_incoming_message(
                account_id=account_id,
                chat_id=chat_id,
                sender_id=sender_id,
                content=content,
            )
            
            if reply:
                # 发送回复
                try:
                    await self.send_message(account_id, chat_id, sender_id, reply)
                except Exception as e:
                    logger.error(f"发送回复失败: {e}")


# 全局管理器实例
_account_manager: Optional[AccountManager] = None


def get_account_manager() -> AccountManager:
    """获取账号管理器实例"""
    global _account_manager
    if _account_manager is None:
        from app.db.database import AsyncSessionLocal
        _account_manager = AccountManager(AsyncSessionLocal)
    return _account_manager
