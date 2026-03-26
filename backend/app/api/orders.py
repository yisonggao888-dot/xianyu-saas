"""
订单API路由
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.services.order_service import OrderService
from app.models.models import OrderStatus

router = APIRouter()


# ========== 请求/响应模型 ==========

class CreateOrderRequest(BaseModel):
    conversation_id: str
    xianyu_order_id: str = Field(..., min_length=1)
    buyer_id: str = Field(..., min_length=1)
    item_title: str = Field(..., min_length=1)
    sold_price: float = Field(..., gt=0)
    cost_price: float = Field(..., gt=0)


class UpdateStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|paid|shipped|completed|cancelled)$")
    tracking_number: Optional[str] = None


class UpdateSourceRequest(BaseModel):
    source_platform: str = Field(..., pattern="^(pdd|1688)$")
    source_order_id: str = Field(..., min_length=1)


class OrderResponse(BaseModel):
    id: str
    conversation_id: str
    xianyu_order_id: str
    buyer_id: str
    item_title: str
    sold_price: float
    cost_price: float
    profit: float
    status: str
    source_platform: Optional[str]
    source_order_id: Optional[str]
    tracking_number: Optional[str]
    created_at: str
    paid_at: Optional[str]
    shipped_at: Optional[str]
    completed_at: Optional[str]


class OrderStatsResponse(BaseModel):
    total_orders: int
    pending_count: int
    completed_count: int
    total_sales: float
    total_profit: float
    avg_margin_percent: float
    status_distribution: dict


class DailyStatsItem(BaseModel):
    date: str
    orders: int
    sales: float
    profit: float


# ========== API端点 ==========

@router.post("/", response_model=OrderResponse)
async def create_order(
    data: CreateOrderRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """创建订单"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = OrderService(db)
    
    order = await service.create_from_conversation(
        tenant_id=tenant_id,
        conversation_id=data.conversation_id,
        xianyu_order_id=data.xianyu_order_id,
        buyer_id=data.buyer_id,
        item_title=data.item_title,
        sold_price=data.sold_price,
        cost_price=data.cost_price,
    )
    
    return {
        "id": order.id,
        "conversation_id": order.conversation_id,
        "xianyu_order_id": order.xianyu_order_id,
        "buyer_id": order.buyer_id,
        "item_title": order.item_title,
        "sold_price": order.sold_price,
        "cost_price": order.cost_price,
        "profit": order.profit,
        "status": order.status.value,
        "source_platform": order.source_platform,
        "source_order_id": order.source_order_id,
        "tracking_number": order.tracking_number,
        "created_at": order.created_at.isoformat(),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
    }


@router.get("/", response_model=List[OrderResponse])
async def get_order_list(
    status: Optional[str] = Query(None, regex="^(pending|paid|shipped|completed|cancelled)$"),
    days: Optional[int] = Query(None, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取订单列表"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = OrderService(db)
    
    status_enum = None
    if status:
        status_enum = OrderStatus(status)
    
    orders = await service.get_order_list(tenant_id, status_enum, days)
    
    return [
        {
            "id": o.id,
            "conversation_id": o.conversation_id,
            "xianyu_order_id": o.xianyu_order_id,
            "buyer_id": o.buyer_id,
            "item_title": o.item_title,
            "sold_price": o.sold_price,
            "cost_price": o.cost_price,
            "profit": o.profit,
            "status": o.status.value,
            "source_platform": o.source_platform,
            "source_order_id": o.source_order_id,
            "tracking_number": o.tracking_number,
            "created_at": o.created_at.isoformat(),
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            "shipped_at": o.shipped_at.isoformat() if o.shipped_at else None,
            "completed_at": o.completed_at.isoformat() if o.completed_at else None,
        }
        for o in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取订单详情"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = OrderService(db)
    order = await service.get_order(tenant_id, order_id)
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    return {
        "id": order.id,
        "conversation_id": order.conversation_id,
        "xianyu_order_id": order.xianyu_order_id,
        "buyer_id": order.buyer_id,
        "item_title": order.item_title,
        "sold_price": order.sold_price,
        "cost_price": order.cost_price,
        "profit": order.profit,
        "status": order.status.value,
        "source_platform": order.source_platform,
        "source_order_id": order.source_order_id,
        "tracking_number": order.tracking_number,
        "created_at": order.created_at.isoformat(),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "shipped_at": o.shipped_at.isoformat() if o.shipped_at else None,
        "completed_at": o.completed_at.isoformat() if o.completed_at else None,
    }


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    data: UpdateStatusRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """更新订单状态"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = OrderService(db)
    
    status_enum = OrderStatus(data.status)
    
    success = await service.update_status(
        tenant_id, order_id, status_enum,
        tracking_number=data.tracking_number
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    # 返回更新后的订单
    order = await service.get_order(tenant_id, order_id)
    
    return {
        "id": order.id,
        "conversation_id": order.conversation_id,
        "xianyu_order_id": order.xianyu_order_id,
        "buyer_id": order.buyer_id,
        "item_title": order.item_title,
        "sold_price": order.sold_price,
        "cost_price": order.cost_price,
        "profit": order.profit,
        "status": order.status.value,
        "source_platform": order.source_platform,
        "source_order_id": order.source_order_id,
        "tracking_number": order.tracking_number,
        "created_at": order.created_at.isoformat(),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
    }


@router.put("/{order_id}/source", response_model=OrderResponse)
async def update_source_info(
    order_id: str,
    data: UpdateSourceRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """更新货源信息"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = OrderService(db)
    
    success = await service.update_source_info(
        tenant_id, order_id,
        data.source_platform, data.source_order_id
    )
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    order = await service.get_order(tenant_id, order_id)
    
    return {
        "id": order.id,
        "conversation_id": order.conversation_id,
        "xianyu_order_id": order.xianyu_order_id,
        "buyer_id": order.buyer_id,
        "item_title": order.item_title,
        "sold_price": order.sold_price,
        "cost_price": order.cost_price,
        "profit": order.profit,
        "status": order.status.value,
        "source_platform": order.source_platform,
        "source_order_id": order.source_order_id,
        "tracking_number": order.tracking_number,
        "created_at": order.created_at.isoformat(),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
    }


@router.post("/{order_id}/purchase")
async def auto_purchase(
    order_id: str,
    product_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """自动采购（到拼多多/1688下单）"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = OrderService(db)
    result = await service.auto_purchase(tenant_id, order_id, product_id)
    
    if not result['success']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get('error'))
    
    return result


@router.get("/stats/summary", response_model=OrderStatsResponse)
async def get_order_stats(
    days: int = Query(30, ge=1, le=365),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取订单统计"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = OrderService(db)
    stats = await service.get_stats(tenant_id, days)
    
    return OrderStatsResponse(**stats)


@router.get("/stats/daily", response_model=List[DailyStatsItem])
async def get_daily_stats(
    days: int = Query(7, ge=1, le=30),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取每日统计"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = OrderService(db)
    stats = await service.get_daily_stats(tenant_id, days)
    
    return stats
