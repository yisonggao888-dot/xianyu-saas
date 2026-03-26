"""
发布API路由
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.services.publish_service import PublishService

router = APIRouter()


# ========== 请求/响应模型 ==========

class PublishRequest(BaseModel):
    product_id: str
    account_id: str
    sale_price: Optional[float] = None


class BatchPublishRequest(BaseModel):
    product_ids: List[str]
    account_id: str
    interval: int = Field(default=60, ge=30, le=300)


class PublishResponse(BaseModel):
    success: bool
    item_id: Optional[str]
    url: Optional[str]
    error: Optional[str]


# ========== API端点 ==========

@router.post("/publish", response_model=PublishResponse)
async def publish_product(
    data: PublishRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """发布单个商品到闲鱼"""
    service = PublishService()
    
    result = await service.publish_product(
        product_id=data.product_id,
        account_id=data.account_id,
        sale_price=data.sale_price,
        db=db,
    )
    
    return PublishResponse(**result)


@router.post("/batch-publish")
async def batch_publish(
    data: BatchPublishRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """批量发布商品"""
    if len(data.product_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单次最多发布10个商品"
        )
    
    service = PublishService()
    
    results = await service.batch_publish(
        product_ids=data.product_ids,
        account_id=data.account_id,
        interval=data.interval,
    )
    
    success_count = sum(1 for r in results if r['success'])
    
    return {
        'total': len(data.product_ids),
        'success': success_count,
        'failed': len(data.product_ids) - success_count,
        'results': results,
    }


@router.get("/categories")
async def get_categories(
    current_user_id: str = Depends(get_current_user_id),
):
    """获取闲鱼分类列表"""
    # TODO: 从数据库或闲鱼API获取分类
    categories = [
        {'id': '1', 'name': '数码', 'children': [
            {'id': '1-1', 'name': '手机'},
            {'id': '1-2', 'name': '电脑'},
        ]},
        {'id': '2', 'name': '服装', 'children': [
            {'id': '2-1', 'name': '男装'},
            {'id': '2-2', 'name': '女装'},
        ]},
        {'id': '3', 'name': '家居', 'children': [
            {'id': '3-1', 'name': '家具'},
            {'id': '3-2', 'name': '家纺'},
        ]},
    ]
    
    return categories
