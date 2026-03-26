"""
采购API路由
"""
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.services.purchase_queue import PurchaseTask, PurchaseStatus, get_purchase_queue
from app.services.order_service import OrderService
from app.models.models import Order

router = APIRouter()


# ========== 请求/响应模型 ==========

class CreatePurchaseRequest(BaseModel):
    order_id: str
    source: str = Field(..., pattern="^(pdd|1688)$")
    source_id: str
    source_url: str
    sku_spec: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    buyer_name: str = Field(..., min_length=1)
    buyer_phone: str = Field(..., min_length=11, max_length=11)
    buyer_address: str = Field(..., min_length=1)


class PurchaseResponse(BaseModel):
    task_id: str
    status: str
    message: str


class PurchaseTaskResponse(BaseModel):
    id: str
    order_id: str
    status: str
    source: str
    result: Optional[dict]
    error_msg: Optional[str]
    created_at: str
    completed_at: Optional[str]


# ========== API端点 ==========

@router.post("/create", response_model=PurchaseResponse)
async def create_purchase(
    data: CreatePurchaseRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    创建采购任务
    
    提交后会异步执行采购流程
    """
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    # 验证订单存在
    order_service = OrderService(db)
    order = await order_service.get_order(tenant_id, data.order_id)
    
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    
    if order.status.value not in ['pending', 'paid']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订单状态不允许采购")
    
    # 创建任务
    task = PurchaseTask(
        id=str(uuid4()),
        order_id=data.order_id,
        tenant_id=tenant_id,
        source=data.source,
        source_id=data.source_id,
        source_url=data.source_url,
        sku_spec=data.sku_spec,
        quantity=data.quantity,
        buyer_name=data.buyer_name,
        buyer_phone=data.buyer_phone,
        buyer_address=data.buyer_address,
    )
    
    # 定义完成回调
    async def on_complete(task: PurchaseTask):
        """任务完成回调"""
        if task.status == PurchaseStatus.SUCCESS and task.result:
            # 更新订单的货源信息
            await order_service.update_source_info(
                tenant_id=tenant_id,
                order_id=task.order_id,
                source_platform=task.source,
                source_order_id=task.result.get('order_id')
            )
    
    # 提交到队列
    queue = get_purchase_queue()
    task_id = await queue.submit(task, callback=on_complete)
    
    return PurchaseResponse(
        task_id=task_id,
        status=task.status.value,
        message="采购任务已提交，正在处理中"
    )


@router.get("/task/{task_id}", response_model=PurchaseTaskResponse)
async def get_task_status(
    task_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """获取采购任务状态"""
    queue = get_purchase_queue()
    task = queue.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    
    return PurchaseTaskResponse(
        id=task.id,
        order_id=task.order_id,
        status=task.status.value,
        source=task.source,
        result=task.result,
        error_msg=task.error_msg,
        created_at=task.created_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


@router.get("/order/{order_id}/tasks")
async def get_order_tasks(
    order_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """获取订单的所有采购任务"""
    queue = get_purchase_queue()
    tasks = queue.get_tasks_by_order(order_id)
    
    return [
        {
            'id': t.id,
            'status': t.status.value,
            'source': t.source,
            'result': t.result,
            'error_msg': t.error_msg,
            'created_at': t.created_at.isoformat(),
        }
        for t in tasks
    ]


@router.post("/task/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """取消采购任务"""
    queue = get_purchase_queue()
    success = queue.cancel_task(task_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务不存在或无法取消"
        )
    
    return {"message": "任务已取消"}


@router.get("/stats")
async def get_queue_stats(
    current_user_id: str = Depends(get_current_user_id),
):
    """获取采购队列统计"""
    queue = get_purchase_queue()
    stats = queue.get_stats()
    
    return stats
