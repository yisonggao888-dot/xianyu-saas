"""
选品中心API路由
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.security import get_current_user_id
from app.db.database import get_db
from app.services.sourcing_analyzer import SourcingAnalyzer, HotProductCriteria
from app.services.product_publish import ProductPublishService, PublishConfig
from app.services.polish_service import PolishService, PolishConfig

router = APIRouter()


# ========== 请求/响应模型 ==========

class HotProductFilter(BaseModel):
    """爆款筛选条件"""
    min_monthly_sales: int = Field(default=100, ge=0)
    min_profit_margin: float = Field(default=30.0, ge=0)
    max_competition: float = Field(default=0.8, ge=0, le=1)
    min_rating: float = Field(default=4.0, ge=0, le=5)
    price_min: float = Field(default=10.0, ge=0)
    price_max: float = Field(default=500.0, ge=0)


class AddToCenterRequest(BaseModel):
    """添加到商品中心请求"""
    sourcing_product_id: str
    price_markup: float = Field(default=1.5, ge=1.0)
    add_watermark: bool = True
    watermark_text: str = "闲鱼优品"
    optimize_title: bool = True
    compress_images: bool = True
    remove_duplicates: bool = True


class BatchPublishRequest(BaseModel):
    """批量发布请求"""
    name: str = Field(..., min_length=1, max_length=100)
    sourcing_product_ids: List[str]
    target_account_ids: List[str]
    price_markup: float = Field(default=1.5, ge=1.0)
    add_watermark: bool = True
    optimize_title: bool = True
    scheduled_at: Optional[datetime] = None


class CreatePolishScheduleRequest(BaseModel):
    """创建擦亮计划请求"""
    name: str = Field(..., min_length=1, max_length=100)
    account_id: str
    schedule_type: str = Field(default="interval", pattern="^(interval|cron)$")
    interval_minutes: int = Field(default=60, ge=5)
    cron_expression: Optional[str] = None
    max_items_per_run: int = Field(default=50, ge=1, le=100)
    only_work_hours: bool = True


class ManualPolishRequest(BaseModel):
    """手动擦亮请求"""
    account_id: str
    item_ids: List[str]


class TitleOptimizeRequest(BaseModel):
    """标题优化请求"""
    title: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = None


class SearchProductsRequest(BaseModel):
    """搜索商品请求"""
    keyword: str = Field(..., min_length=1)
    sources: Optional[List[str]] = Field(default=['pdd', '1688'])
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_sales: Optional[int] = None
    sort: str = Field(default='default')


# ========== API端点 ==========

@router.post("/search")
async def search_products(
    data: SearchProductsRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    搜索商品（拼多多、1688）
    """
    from app.services.scraper import ProductScraper
    
    scraper = ProductScraper()
    
    # 调试日志
    logger.info(f"搜索请求 - keyword: {data.keyword!r}, sources: {data.sources}")
    
    try:
        # 转换排序参数
        sort_map = {
            'default': 'default',
            'price_asc': 'price_asc',
            'price_desc': 'price_desc',
            'sales_desc': 'sales',
        }
        sort = sort_map.get(data.sort, 'default')
        
        # 执行搜索
        results = await scraper.search_all(
            keyword=data.keyword,
            sources=data.sources,
            sort=sort,
            min_price=int(data.min_price) if data.min_price else None,
            max_price=int(data.max_price) if data.max_price else None,
        )
        
        # 统计结果
        total = sum(len(products) for products in results.values())
        logger.info(f"搜索完成 - 共找到 {total} 件商品")
        
        # 转换结果格式
        formatted_results = {}
        for source, products in results.items():
            formatted_results[source] = [
                {
                    'source_id': p.source_id,
                    'title': p.title,
                    'price': p.price,
                    'original_price': p.original_price,
                    'main_image': p.main_image,
                    'images': p.images,
                    'sales_count': p.sales_count,
                    'shop_name': p.shop_name,
                    'shop_rating': p.shop_rating,
                    'detail_url': p.detail_url,
                    'category': p.category,
                }
                for p in products
            ]
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"搜索商品失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}",
        )
    finally:
        await scraper.close()


@router.get("/hot-products")
async def get_hot_products(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    filter: HotProductFilter = Depends(),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取爆款商品列表
    """
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    analyzer = SourcingAnalyzer(db)
    
    # 构建筛选条件
    criteria = HotProductCriteria(
        min_monthly_sales=filter.min_monthly_sales,
        min_profit_margin=filter.min_profit_margin,
        max_competition=filter.max_competition,
        min_rating=filter.min_rating,
        price_range=(filter.price_min, filter.price_max),
    )
    
    products = await analyzer.get_hot_products(
        tenant_id=tenant_id,
        criteria=criteria,
        limit=limit,
    )
    
    return {
        "total": len(products),
        "products": products,
    }


@router.get("/analysis/category")
async def get_category_analysis(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取分类分析报告
    """
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    analyzer = SourcingAnalyzer(db)
    analysis = await analyzer.get_category_analysis(tenant_id)
    
    return {
        "categories": analysis,
    }


@router.get("/analysis/price")
async def get_price_analysis(
    category: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取价格带分析
    """
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    analyzer = SourcingAnalyzer(db)
    analysis = await analyzer.get_price_analysis(tenant_id, category)
    
    return analysis


@router.post("/analyze")
async def analyze_products(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    分析商品数据（更新评分）
    """
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    analyzer = SourcingAnalyzer(db)
    await analyzer.update_product_scores(tenant_id)
    
    return {"message": "分析完成"}


@router.post("/add-to-center")
async def add_to_product_center(
    data: AddToCenterRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    一键上架到商品中心
    """
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = ProductPublishService(db)
    
    config = PublishConfig(
        price_markup=data.price_markup,
        add_watermark=data.add_watermark,
        watermark_text=data.watermark_text,
        optimize_title=data.optimize_title,
        compress_images=data.compress_images,
        remove_duplicates=data.remove_duplicates,
    )
    
    product = await service.add_to_product_center(
        tenant_id=tenant_id,
        sourcing_product_id=data.sourcing_product_id,
        config=config,
    )
    
    await service.close()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="上架失败",
        )
    
    return {
        "success": True,
        "product_id": product.id,
        "title": product.title,
        "sale_price": product.sale_price,
    }


@router.post("/batch-publish")
async def create_batch_publish_task(
    data: BatchPublishRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    创建批量发布任务
    """
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = ProductPublishService(db)
    
    config = PublishConfig(
        price_markup=data.price_markup,
        add_watermark=data.add_watermark,
        optimize_title=data.optimize_title,
    )
    
    task = await service.create_batch_publish_task(
        tenant_id=tenant_id,
        user_id=current_user_id,
        name=data.name,
        sourcing_product_ids=data.sourcing_product_ids,
        target_account_ids=data.target_account_ids,
        config=config,
        scheduled_at=data.scheduled_at,
    )
    
    await service.close()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建任务失败",
        )
    
    # 如果是立即执行，添加到后台任务
    if not data.scheduled_at:
        background_tasks.add_task(execute_publish_task_async, task.id)
    
    return {
        "success": True,
        "task_id": task.id,
        "status": task.status.value,
        "total_count": task.total_count,
    }


async def execute_publish_task_async(task_id: str):
    """异步执行发布任务"""
    from app.db.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        service = ProductPublishService(db)
        await service.execute_publish_task(task_id)
        await service.close()


@router.get("/publish-tasks")
async def get_publish_tasks(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取发布任务列表
    """
    from sqlalchemy import select
    from app.models.product_models import PublishTask
    from app.api.users import get_current_tenant_id
    
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(PublishTask).where(
            PublishTask.tenant_id == tenant_id
        ).order_by(PublishTask.created_at.desc())
    )
    tasks = result.scalars().all()
    
    return {
        "tasks": [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status.value,
                "total_count": t.total_count,
                "success_count": t.success_count,
                "failed_count": t.failed_count,
                "progress": round(
                    (t.success_count + t.failed_count) / t.total_count * 100, 1
                ) if t.total_count > 0 else 0,
                "created_at": t.created_at.isoformat(),
                "scheduled_at": t.scheduled_at.isoformat() if t.scheduled_at else None,
            }
            for t in tasks
        ]
    }


@router.get("/publish-tasks/{task_id}")
async def get_publish_task_detail(
    task_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取发布任务详情
    """
    service = ProductPublishService(db)
    progress = await service.get_task_progress(task_id)
    await service.close()
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在",
        )
    
    return progress


@router.post("/publish-tasks/{task_id}/cancel")
async def cancel_publish_task(
    task_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    取消发布任务
    """
    service = ProductPublishService(db)
    success = await service.cancel_task(task_id)
    await service.close()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="取消任务失败",
        )
    
    return {"success": True}


@router.post("/optimize-title")
async def optimize_title(
    data: TitleOptimizeRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    AI优化标题
    """
    from app.services.title_optimizer import TitleOptimizer
    
    optimizer = TitleOptimizer()
    result = await optimizer.optimize_title(
        data.title,
        data.category,
    )
    
    return {
        "original_title": result.original_title,
        "optimized_title": result.optimized_title,
        "keywords": result.keywords,
        "score": result.score,
        "improvements": result.improvements,
    }


@router.post("/polish-schedules")
async def create_polish_schedule(
    data: CreatePolishScheduleRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    创建定时擦亮计划
    """
    from app.api.users import get_current_tenant_id
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    service = PolishService(db)
    
    config = PolishConfig(
        interval_minutes=data.interval_minutes,
        cron_expression=data.cron_expression,
        max_items_per_run=data.max_items_per_run,
        only_work_hours=data.only_work_hours,
    )
    
    schedule = await service.create_schedule(
        tenant_id=tenant_id,
        account_id=data.account_id,
        name=data.name,
        config=config,
    )
    
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建计划失败",
        )
    
    return {
        "success": True,
        "schedule_id": schedule.id,
        "name": schedule.name,
        "status": schedule.status.value,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
    }


@router.get("/polish-schedules")
async def get_polish_schedules(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取擦亮计划列表
    """
    from sqlalchemy import select
    from app.models.product_models import PolishSchedule
    from app.api.users import get_current_tenant_id
    
    tenant_id = await get_current_tenant_id(current_user_id, db)
    
    result = await db.execute(
        select(PolishSchedule).where(
            PolishSchedule.tenant_id == tenant_id
        ).order_by(PolishSchedule.created_at.desc())
    )
    schedules = result.scalars().all()
    
    return {
        "schedules": [
            {
                "id": s.id,
                "name": s.name,
                "status": s.status.value,
                "schedule_type": s.schedule_type,
                "total_runs": s.total_runs,
                "success_runs": s.success_runs,
                "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            }
            for s in schedules
        ]
    }


@router.get("/polish-schedules/{schedule_id}")
async def get_polish_schedule_detail(
    schedule_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取擦亮计划详情
    """
    service = PolishService(db)
    stats = await service.get_schedule_stats(schedule_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="计划不存在",
        )
    
    return stats


@router.post("/polish-schedules/{schedule_id}/pause")
async def pause_polish_schedule(
    schedule_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    暂停擦亮计划
    """
    service = PolishService(db)
    success = await service.pause_schedule(schedule_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="暂停失败",
        )
    
    return {"success": True}


@router.post("/polish-schedules/{schedule_id}/resume")
async def resume_polish_schedule(
    schedule_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    恢复擦亮计划
    """
    service = PolishService(db)
    success = await service.resume_schedule(schedule_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="恢复失败",
        )
    
    return {"success": True}


@router.delete("/polish-schedules/{schedule_id}")
async def delete_polish_schedule(
    schedule_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    删除擦亮计划
    """
    service = PolishService(db)
    success = await service.delete_schedule(schedule_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="删除失败",
        )
    
    return {"success": True}


@router.post("/manual-polish")
async def manual_polish(
    data: ManualPolishRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    手动擦亮商品
    """
    service = PolishService(db)
    result = await service.manual_polish(
        account_id=data.account_id,
        item_ids=data.item_ids,
    )
    
    return result
