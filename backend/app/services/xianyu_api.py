"""
闲鱼API封装 (基于XianyuAutoAgent)
"""
import time
import re
import json
from typing import Optional, Dict, Any

import httpx
from loguru import logger


class XianyuAPI:
    """闲鱼Web API封装"""
    
    def __init__(self, cookies: str):
        self.cookies_str = cookies
        self.cookies = self._parse_cookies(cookies)
        self.user_id = self.cookies.get('unb', '')
        
        # HTTP客户端
        self.client = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Referer': 'https://www.goofish.com/',
            },
            cookies=self.cookies,
            timeout=30.0,
        )
    
    def _parse_cookies(self, cookies_str: str) -> Dict[str, str]:
        """解析Cookie字符串"""
        cookies = {}
        for cookie in cookies_str.split('; '):
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies[key] = value
        return cookies
    
    async def check_login(self) -> bool:
        """检查登录状态"""
        try:
            url = 'https://passport.goofish.com/newlogin/hasLogin.do'
            params = {'appName': 'xianyu', 'fromSite': '77'}
            
            response = await self.client.post(url, params=params)
            data = response.json()
            
            return data.get('content', {}).get('success', False)
        except Exception as e:
            logger.error(f"登录检查失败: {e}")
            return False
    
    async def get_token(self, device_id: str) -> Optional[str]:
        """获取WebSocket Token"""
        try:
            url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/'
            
            # 构建请求参数
            t = str(int(time.time() * 1000))
            data = json.dumps({"deviceId": device_id})
            
            response = await self.client.post(url, data={
                'data': data,
                't': t,
            })
            
            result = response.json()
            if 'data' in result and 'accessToken' in result['data']:
                return result['data']['accessToken']
            
            logger.error(f"获取Token失败: {result}")
            return None
            
        except Exception as e:
            logger.error(f"获取Token异常: {e}")
            return None
    
    async def get_user_info(self) -> Optional[Dict]:
        """获取用户信息"""
        try:
            url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.getUserInfo/1.0/'
            
            response = await self.client.post(url)
            result = response.json()
            
            if result.get('data'):
                return result['data']
            return None
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# ========== 工具函数 ==========

def generate_device_id(user_id: str) -> str:
    """生成设备ID"""
    import random
    import uuid
    
    # 基于user_id生成一致的device_id
    random.seed(user_id)
    return str(uuid.uuid4())


def generate_mid() -> str:
    """生成消息ID"""
    import random
    random_part = int(1000 * random.random())
    timestamp = int(time.time() * 1000)
    return f"{random_part}{timestamp} 0"


def generate_uuid() -> str:
    """生成UUID"""
    timestamp = int(time.time() * 1000)
    return f"-{timestamp}1"


# ========== WebSocket消息构建 ==========

def build_ws_init_message(token: str, device_id: str) -> dict:
    """构建WebSocket初始化消息"""
    return {
        "lwp": "/reg",
        "headers": {
            "cache-header": "app-key token ua wv",
            "app-key": "444e9908a51d1cb236a27862abc769c9",
            "token": token,
            "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "dt": "j",
            "wv": "im:3,au:3,sy:6",
            "sync": "0,0;0;0;",
            "did": device_id,
            "mid": generate_mid()
        }
    }


def build_ws_send_message(cid: str, toid: str, text: str, myid: str) -> dict:
    """构建发送消息"""
    import base64
    
    content = {
        "contentType": 1,
        "text": {"text": text}
    }
    content_base64 = base64.b64encode(json.dumps(content).encode()).decode()
    
    return {
        "lwp": "/r/MessageSend/sendByReceiverScope",
        "headers": {"mid": generate_mid()},
        "body": [
            {
                "uuid": generate_uuid(),
                "cid": f"{cid}@goofish",
                "conversationType": 1,
                "content": {
                    "contentType": 101,
                    "custom": {
                        "type": 1,
                        "data": content_base64
                    }
                },
                "redPointPolicy": 0,
                "extension": {"extJson": "{}"},
                "ctx": {"appVersion": "1.0", "platform": "web"},
                "mtags": {},
                "msgReadStatusSetting": 1
            },
            {
                "actualReceivers": [
                    f"{toid}@goofish",
                    f"{myid}@goofish"
                ]
            }
        ]
    }
