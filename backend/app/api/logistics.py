"""
物流API路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.services.logistics_service import LogisticsService
from app.services.order_service import OrderService

router = APIRouter()


# ========== 请求/响应模型 ==========

class SyncLogisticsRequest(BaseModel):
    order_id: str


class FillLogisticsRequest(BaseModel):
    order_id: str
    tracking_number: str = Field(..., min_length=5)
    carrier: str = Field(..., min_length=1)


class LogisticsResponse(BaseModel):
    success: bool
    tracking_number: Optional[str]
    carrier: Optional[str]
    status: Optional[str]
    details: Optional[list]
    error: Optional[str]


# ========== API端点 ==========

@router.post("/sync", response_model=LogisticsResponse)
async def sync_logistics(
    data: SyncLogisticsRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """同步货源物流信息"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    # 获取订单
    order_service = OrderService(db)
    order = await order_service.get_order(tenant_id, data.order_id)
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    if not order.source_platform or not order.source_order_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订单无货源信息")
    
    # 同步物流
    service = LogisticsService()
    
    # TODO: 从数据库获取cookies
    cookies = None
    
    result = await service.sync_from_source(
        order.source_platform,
        order.source_order_id,
        cookies
    )
    
    # 如果同步成功且有物流单号，更新订单
    if result['success'] and result.get('tracking_number'):
        await order_service.update_status(
            tenant_id, data.order_id, order.status,  # 保持原状态
            tracking_number=result['tracking_number']
        )
    
    return LogisticsResponse(**result)


@router.post("/fill-to-xianyu")
async def fill_to_xianyu(
    data: FillLogisticsRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """回填物流到闲鱼"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    # 获取订单
    order_service = OrderService(db)
    order = await order_service.get_order(tenant_id, data.order_id)
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    # 回填物流
    service = LogisticsService()
    
    # TODO: 获取账号cookies
    cookies = None
    
    success = await service.fill_to_xianyu(
        order.xianyu_order_id,
        data.tracking_number,
        data.carrier,
        cookies
    )
    
    if success:
        # 更新订单状态为已发货
        await order_service.update_status(
            tenant_id, data.order_id, order.status,
            tracking_number=data.tracking_number
        )
    
    return {"success": success}


@router.post("/auto-sync-all")
async def auto_sync_all(
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """触发批量同步（后台执行）"""
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    async def sync_task():
        """同步任务"""
        service = LogisticsService()
        # TODO: 查询所有待发货订单，逐个同步
        pass
    
    background_tasks.add_task(sync_task)
    
    return {"message": "同步任务已启动"}
