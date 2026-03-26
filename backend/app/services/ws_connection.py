"""
WebSocket连接管理器
"""
import asyncio
import json
import base64
from typing import Optional, Callable, Dict, Any
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosed
from loguru import logger

from app.services.xianyu_api import (
    XianyuAPI, generate_device_id, build_ws_init_message,
    build_ws_send_message, generate_mid
)
from app.services.ai_engine import AIReplyEngine


class XianyuWebSocketConnection:
    """单个闲鱼账号的WebSocket连接"""
    
    def __init__(
        self,
        account_id: str,
        cookies: str,
        message_callback: Optional[Callable] = None,
        ai_engine: Optional[AIReplyEngine] = None,
    ):
        self.account_id = account_id
        self.cookies = cookies
        self.message_callback = message_callback
        self.ai_engine = ai_engine
        
        # API客户端
        self.api = XianyuAPI(cookies)
        self.user_id = self.api.user_id
        self.device_id = generate_device_id(self.user_id)
        
        # WebSocket
        self.ws = None
        self.ws_url = 'wss://wss-goofish.dingtalk.com/'
        
        # Token管理
        self.token = None
        self.token_refresh_task = None
        
        # 心跳
        self.heartbeat_task = None
        self.heartbeat_interval = 15  # 秒
        
        # 运行状态
        self.running = False
        self.connected = False
        
        # 统计
        self.message_count = 0
        self.last_message_at = None
    
    async def start(self):
        """启动连接"""
        logger.info(f"[Account {self.account_id}] 启动WebSocket连接")
        
        # 检查登录
        if not await self.api.check_login():
            logger.error(f"[Account {self.account_id}] Cookie已失效")
            return False
        
        self.running = True
        
        # 启动主循环
        while self.running:
            try:
                await self._connect()
                await self._handle_messages()
            except ConnectionClosed:
                logger.warning(f"[Account {self.account_id}] 连接断开，5秒后重连...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"[Account {self.account_id}] 异常: {e}")
                await asyncio.sleep(5)
        
        return True
    
    async def stop(self):
        """停止连接"""
        logger.info(f"[Account {self.account_id}] 停止连接")
        self.running = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        if self.ws:
            await self.ws.close()
        
        await self.api.close()
    
    async def _connect(self):
        """建立WebSocket连接"""
        # 获取Token
        self.token = await self.api.get_token(self.device_id)
        if not self.token:
            raise Exception("获取Token失败")
        
        # 连接WebSocket
        self.ws = await websockets.connect(self.ws_url)
        
        # 发送初始化消息
        init_msg = build_ws_init_message(self.token, self.device_id)
        await self.ws.send(json.dumps(init_msg))
        
        # 发送同步消息
        sync_msg = {
            "lwp": "/r/SyncStatus/ackDiff",
            "headers": {"mid": generate_mid()},
            "body": [{
                "pipeline": "sync",
                "tooLong2Tag": "PNM,1",
                "channel": "sync",
                "topic": "sync",
                "highPts": 0,
                "pts": int(asyncio.get_event_loop().time() * 1000) * 1000,
                "seq": 0,
                "timestamp": int(asyncio.get_event_loop().time() * 1000)
            }]
        }
        await self.ws.send(json.dumps(sync_msg))
        
        # 启动心跳
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        self.connected = True
        logger.info(f"[Account {self.account_id}] WebSocket连接成功")
    
    async def _handle_messages(self):
        """处理消息循环"""
        async for message in self.ws:
            try:
                await self._process_message(message)
            except Exception as e:
                logger.error(f"[Account {self.account_id}] 处理消息失败: {e}")
    
    async def _process_message(self, message: str):
        """处理单条消息"""
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return
        
        # 检查是否为聊天消息
        if not self._is_chat_message(data):
            return
        
        # 提取消息内容
        chat_data = self._extract_chat_data(data)
        if not chat_data:
            return
        
        # 更新统计
        self.message_count += 1
        self.last_message_at = datetime.now()
        
        # 回调
        if self.message_callback:
            await self.message_callback(
                account_id=self.account_id,
                **chat_data
            )
    
    def _is_chat_message(self, data: dict) -> bool:
        """检查是否为聊天消息"""
        # 简化判断：检查包含特定字段
        if not isinstance(data, dict):
            return False
        
        # 检查body字段
        body = data.get('body', {})
        if not isinstance(body, dict):
            return False
        
        # 检查是否有syncPushPackage
        sync_data = body.get('syncPushPackage', {}).get('data', [])
        if sync_data:
            return True
        
        return False
    
    def _extract_chat_data(self, data: dict) -> Optional[Dict]:
        """提取聊天数据"""
        try:
            body = data.get('body', {})
            sync_data = body.get('syncPushPackage', {}).get('data', [])
            
            if not sync_data:
                return None
            
            # 解析第一条消息
            msg = sync_data[0]
            
            # 提取cid和发送者
            cid = msg.get('1', {}).get('1', '')
            sender = msg.get('1', {}).get('10', {}).get('reminderContent', [])
            
            if not cid or not sender:
                return None
            
            # 解析消息内容
            content = msg.get('1', {}).get('10', {}).get('1', [])
            if not content:
                return None
            
            text_content = content[0].get('1', '') if content else ''
            
            return {
                'chat_id': cid,
                'sender_id': sender[0].get('1', '').replace('@goofish', '') if sender else '',
                'content': text_content,
                'raw_data': msg,
            }
            
        except Exception as e:
            logger.error(f"提取聊天数据失败: {e}")
            return None
    
    async def send_message(self, chat_id: str, to_id: str, text: str):
        """发送消息"""
        if not self.ws or not self.connected:
            raise Exception("WebSocket未连接")
        
        msg = build_ws_send_message(chat_id, to_id, text, self.user_id)
        await self.ws.send(json.dumps(msg))
        
        logger.info(f"[Account {self.account_id}] 发送消息: {text[:50]}...")
    
    async def _heartbeat_loop(self):
        """心跳保活"""
        while self.running:
            try:
                # 发送ping
                await self.ws.send('{"lwp": "/ping"}')
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"[Account {self.account_id}] 心跳失败: {e}")
                break
