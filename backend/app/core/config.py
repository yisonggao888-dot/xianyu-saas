"""
应用配置
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用信息
    APP_NAME: str = "XianyuSaaS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://xianyu:xianyu2026@localhost:5432/xianyu_saas"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # 安全
    SECRET_KEY: str = "your-secret-key-change-this"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 43200  # 30天
    
    # 密码加密
    PASSWORD_ALGORITHM: str = "bcrypt"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    # 初始管理员
    FIRST_ADMIN_EMAIL: Optional[str] = None
    FIRST_ADMIN_PASSWORD: Optional[str] = None
    
    # 支付宝支付
    ALIPAY_APP_ID: Optional[str] = None
    ALIPAY_APP_PRIVATE_KEY: Optional[str] = None
    ALIPAY_PUBLIC_KEY: Optional[str] = None
    ALIPAY_GATEWAY: str = "https://openapi.alipaydev.com/gateway.do"
    
    # LLM API
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen-turbo"
    
    # 闲鱼相关
    XIANYU_WEBSOCKET_URL: str = "wss://wss-goofish.dingtalk.com/"
    XIANYU_HEARTBEAT_INTERVAL: int = 15
    XIANYU_TOKEN_REFRESH_INTERVAL: int = 3600
    
    # 套餐限制
    FREE_PLAN_MAX_ACCOUNTS: int = 1
    FREE_PLAN_MAX_MESSAGES: int = 500
    STANDARD_PLAN_MAX_ACCOUNTS: int = 3
    STANDARD_PLAN_MAX_MESSAGES: int = 5000
    PRO_PLAN_MAX_ACCOUNTS: int = 10
    PRO_PLAN_MAX_MESSAGES: int = 50000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
