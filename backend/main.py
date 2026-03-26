"""
FastAPI主应用
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.db.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    logger.info("Database initialized")
    
    # 启动活跃账号
    await init_active_accounts()
    
    yield
    
    # 关闭时
    from app.services.account_manager import get_account_manager
    manager = get_account_manager()
    await manager.stop_all()
    
    await close_db()
    logger.info("Database connection closed")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="星昌云·闲鱼无货源SaaS平台",
    lifespan=lifespan,
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


# 根路由
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


# 注册API路由
from app.api import auth, users, accounts, conversations, products, orders

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["闲鱼账号"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["对话"])
app.include_router(products.router, prefix="/api/v1/products", tags=["选品"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["订单"])


# ========== 启动时初始化 ==========

async def init_active_accounts():
    """启动时连接所有启用的账号"""
    from sqlalchemy import select
    from app.db.database import AsyncSessionLocal
    from app.models.models import Account, AccountStatus
    from app.core.security import decrypt_cookie
    from app.services.account_manager import get_account_manager
    
    logger.info("初始化活跃账号连接...")
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Account).where(Account.status == AccountStatus.ACTIVE)
        )
        accounts = result.scalars().all()
        
        manager = get_account_manager()
        
        for account in accounts:
            try:
                cookies = decrypt_cookie(account.cookies)
                await manager.start_account(account.id, cookies)
                logger.info(f"账号 {account.id} 已启动")
            except Exception as e:
                logger.error(f"启动账号 {account.id} 失败: {e}")
    
    logger.info(f"已启动 {len(accounts)} 个账号")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
