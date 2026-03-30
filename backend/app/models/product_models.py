"""
选品中心扩展模型
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, ForeignKey, 
    Enum, func, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.models import Base


# ========== 枚举类型 ==========

class PublishStatus(str, PyEnum):
    """发布状态"""
    PENDING = "pending"      # 待发布
    PROCESSING = "processing" # 处理中
    PUBLISHED = "published"  # 已发布
    FAILED = "failed"        # 发布失败


class PublishTaskStatus(str, PyEnum):
    """发布任务状态"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


class PolishScheduleStatus(str, PyEnum):
    """定时擦亮状态"""
    ACTIVE = "active"        # 启用
    PAUSED = "paused"        # 暂停
    COMPLETED = "completed"  # 已完成


# ========== 选品库模型 ==========

class ProductSource(str, PyEnum):
    """商品来源"""
    PDD = "pdd"
    ALI1688 = "1688"
    TAOBAO = "taobao"
    JD = "jd"
    OTHER = "other"


class SourcingProduct(Base):
    """
    选品库商品 - 从各平台抓取的原始商品数据
    """
    __tablename__ = "sourcing_products"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    
    # 来源信息
    source: Mapped[ProductSource] = mapped_column(Enum(ProductSource), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    shop_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shop_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 商品信息
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    main_image: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[str] = mapped_column(Text, default="[]")  # JSON数组
    
    # 价格信息
    cost_price: Mapped[float] = mapped_column(Float, nullable=False)  # 成本价（元）
    original_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 原价
    
    # 销量数据
    monthly_sales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_sales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 评分数据
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 爆款指标（用于筛选）
    hot_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 热度分
    profit_potential: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 盈利潜力
    competition_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 竞争指数
    
    # 分类信息
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 状态
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已选入商品中心
    is_optimized: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已优化
    
    # 抓取时间
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # 原始数据（保留完整数据用于分析）
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProductOptimizeRecord(Base):
    """
    商品优化记录 - 记录标题、图片等优化历史
    """
    __tablename__ = "product_optimize_records"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("sourcing_products.id"), nullable=False)
    
    # 优化类型
    optimize_type: Mapped[str] = mapped_column(String(20), nullable=False)  # title/image/price/description
    
    # 优化前后对比
    original_value: Mapped[str] = mapped_column(Text, nullable=False)
    optimized_value: Mapped[str] = mapped_column(Text, nullable=False)
    
    # AI优化参数
    ai_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    prompt_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 优化效果
    improvement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ========== 发布任务模型 ==========

class PublishTask(Base):
    """
    批量发布任务
    """
    __tablename__ = "publish_tasks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # 任务信息
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 发布配置
    target_accounts: Mapped[str] = mapped_column(Text, nullable=False)  # JSON数组，目标账号ID列表
    publish_settings: Mapped[str] = mapped_column(Text, default="{}")  # JSON，发布设置
    
    # 任务状态
    status: Mapped[PublishTaskStatus] = mapped_column(Enum(PublishTaskStatus), default=PublishTaskStatus.PENDING)
    
    # 进度统计
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # 时间
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 计划执行时间
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class PublishTaskItem(Base):
    """
    发布任务项 - 单个商品的发布记录
    """
    __tablename__ = "publish_task_items"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(ForeignKey("publish_tasks.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("sourcing_products.id"), nullable=False)
    
    # 发布配置（快照）
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    images: Mapped[str] = mapped_column(Text, nullable=False)  # JSON数组
    price: Mapped[float] = mapped_column(Float, nullable=False)
    
    # 发布状态
    status: Mapped[PublishStatus] = mapped_column(Enum(PublishStatus), default=PublishStatus.PENDING)
    
    # 发布结果
    xianyu_item_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 闲鱼商品ID
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 发布时间
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ========== 定时擦亮模型 ==========

class PolishSchedule(Base):
    """
    定时擦亮计划
    """
    __tablename__ = "polish_schedules"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    
    # 擦亮配置
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # 执行时间配置（Cron表达式或固定时间）
    schedule_type: Mapped[str] = mapped_column(String(20), default="interval")  # interval/cron/once
    interval_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 间隔分钟
    cron_expression: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Cron表达式
    specific_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 指定时间
    
    # 擦亮范围
    item_filter: Mapped[str] = mapped_column(Text, default="{}")  # JSON，商品筛选条件
    max_items_per_run: Mapped[int] = mapped_column(Integer, default=50)
    
    # 状态
    status: Mapped[PolishScheduleStatus] = mapped_column(Enum(PolishScheduleStatus), default=PolishScheduleStatus.ACTIVE)
    
    # 统计
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    success_runs: Mapped[int] = mapped_column(Integer, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class PolishLog(Base):
    """
    擦亮执行日志
    """
    __tablename__ = "polish_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    schedule_id: Mapped[str] = mapped_column(ForeignKey("polish_schedules.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    
    # 执行结果
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success/failed
    items_polished: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 执行详情
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON，详细信息
    
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ========== 图片处理记录 ==========

class ImageProcessRecord(Base):
    """
    图片处理记录
    """
    __tablename__ = "image_process_records"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("sourcing_products.id"), nullable=False)
    
    # 处理类型
    process_type: Mapped[str] = mapped_column(String(50), nullable=False)  # watermark/compress/resize/remove_bg
    
    # 图片信息
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    processed_url: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 处理参数
    process_params: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    
    # 效果统计
    original_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 原始大小（字节）
    processed_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 处理后大小
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
