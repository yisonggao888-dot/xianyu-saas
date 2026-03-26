"""
数据库模型定义
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, ForeignKey, 
    Enum, func, select, and_
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    """基础模型类"""
    pass


# ========== 枚举类型 ==========

class UserRole(str, PyEnum):
    ADMIN = "admin"
    MEMBER = "member"


class TenantPlan(str, PyEnum):
    FREE = "free"
    STANDARD = "standard"
    PRO = "pro"


class AccountStatus(str, PyEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class ConversationStatus(str, PyEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    MANUAL = "manual"  # 人工接管


# ========== 租户模型 ==========

class Tenant(Base):
    __tablename__ = "tenants"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    plan: Mapped[TenantPlan] = mapped_column(Enum(TenantPlan), default=TenantPlan.FREE)
    
    # 套餐限制
    max_accounts: Mapped[int] = mapped_column(Integer, default=1)
    max_messages_per_month: Mapped[int] = mapped_column(Integer, default=1000)
    max_products: Mapped[int] = mapped_column(Integer, default=100)
    
    # 订阅信息
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关联
    users: Mapped[List["User"]] = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    accounts: Mapped[List["Account"]] = relationship("Account", back_populates="tenant", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="tenant")


# ========== 用户模型 ==========

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.MEMBER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关联
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")


# ========== 闲鱼账号模型 ==========

class Account(Base):
    __tablename__ = "accounts"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # 账号别名
    cookies: Mapped[str] = mapped_column(Text, nullable=False)  # 加密存储
    
    # 闲鱼用户信息
    xianyu_user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    xianyu_nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    xianyu_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[AccountStatus] = mapped_column(Enum(AccountStatus), default=AccountStatus.PAUSED)
    
    # AI配置
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_model: Mapped[str] = mapped_column(String(50), default="qwen-turbo")
    classify_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tech_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 统计
    last_online_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    message_count_this_month: Mapped[int] = mapped_column(Integer, default=0)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关联
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="accounts")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="account")


# ========== 对话模型 ==========

class Conversation(Base):
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    
    # 闲鱼信息
    xianyu_chat_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    buyer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    buyer_nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 商品信息
    item_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    item_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    item_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    status: Mapped[ConversationStatus] = mapped_column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE)
    
    # 议价统计
    bargain_count: Mapped[int] = mapped_column(Integer, default=0)
    last_bargain_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 关联
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="conversations")
    account: Mapped["Account"] = relationship("Account", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


# ========== 消息模型 ==========

class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user/assistant/system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 元数据
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # 关联
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")


# ========== 商品模型 (选品中心) ==========

class Product(Base):
    __tablename__ = "products"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    
    # 来源信息
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # pdd/1688
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)  # 源平台商品ID
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 商品信息
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    images: Mapped[str] = mapped_column(Text, default="[]")  # JSON数组
    
    # 价格
    cost_price: Mapped[float] = mapped_column(Float, nullable=False)  # 成本价
    suggested_price: Mapped[float] = mapped_column(Float, nullable=False)  # 建议售价
    profit_margin: Mapped[float] = mapped_column(Float, nullable=False)  # 利润率
    
    # 销量数据
    monthly_sales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 状态
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


# ========== 订单模型 ==========

class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    
    # 闲鱼订单信息
    xianyu_order_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    buyer_id: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # 商品信息
    item_title: Mapped[str] = mapped_column(String(200), nullable=False)
    sold_price: Mapped[float] = mapped_column(Float, nullable=False)
    cost_price: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[float] = mapped_column(Float, nullable=False)
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/paid/shipped/completed/cancelled
    
    # 货源信息
    source_platform: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
