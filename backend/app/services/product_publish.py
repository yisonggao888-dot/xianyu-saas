"""
商品上架和批量发布服务
"""
import json
import asyncio
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.product_models import (
    SourcingProduct, ProductOptimizeRecord, PublishTask,
    PublishTaskItem, PublishStatus, PublishTaskStatus
)
from app.models.models import Product, ProductStatus
from app.services.image_processor import ImageProcessor, WatermarkConfig, CompressConfig
from app.services.title_optimizer import TitleOptimizer


@dataclass
class PublishConfig:
    """发布配置"""
    # 价格配置
    price_markup: float = 1.5  # 加价比例
    min_price: float = 1.0  # 最低价格
    max_price: float = 10000.0  # 最高价格
    
    # 图片配置
    add_watermark: bool = True
    watermark_text: str = "闲鱼优品"
    compress_images: bool = True
    remove_duplicates: bool = True
    
    # 标题配置
    optimize_title: bool = True
    append_keywords: List[str] = None
    
    # 描述配置
    generate_description: bool = True


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    product_id: Optional[str] = None
    xianyu_item_id: Optional[str] = None
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None


class ProductPublishService:
    """
    商品发布服务
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.image_processor = ImageProcessor()
        self.title_optimizer = TitleOptimizer()
    
    async def add_to_product_center(
        self,
        tenant_id: str,
        sourcing_product_id: str,
        config: Optional[PublishConfig] = None,
    ) -> Optional[Product]:
        """
        将选品库商品添加到商品中心（一键上架）
        
        Args:
            tenant_id: 租户ID
            sourcing_product_id: 选品库商品ID
            config: 发布配置
        """
        config = config or PublishConfig()
        
        # 获取选品库商品
        result = await self.db.execute(
            select(SourcingProduct).where(
                and_(
                    SourcingProduct.id == sourcing_product_id,
                    SourcingProduct.tenant_id == tenant_id,
                )
            )
        )
        sourcing = result.scalar_one_or_none()
        
        if not sourcing:
            logger.error(f"Sourcing product not found: {sourcing_product_id}")
            return None
        
        try:
            # 处理图片
            processed_images = await self._process_images(
                sourcing.images,
                config,
                tenant_id,
                sourcing.id,
            )
            
            # 优化标题
            if config.optimize_title:
                optimize_result = await self.title_optimizer.optimize_title(
                    sourcing.title,
                    sourcing.category,
                )
                final_title = optimize_result.optimized_title
                
                # 保存优化记录
                await self._save_optimize_record(
                    tenant_id, sourcing.id, "title",
                    sourcing.title, final_title
                )
            else:
                final_title = sourcing.title
            
            # 生成描述
            if config.generate_description:
                description = await self.title_optimizer.generate_description(
                    final_title,
                    [sourcing.description] if sourcing.description else [],
                    sourcing.category,
                )
            else:
                description = sourcing.description or ""
            
            # 计算售价
            sale_price = self._calc_sale_price(
                sourcing.cost_price,
                config.price_markup,
                config.min_price,
                config.max_price,
            )
            
            # 创建商品中心记录
            product = Product(
                tenant_id=tenant_id,
                source=sourcing.source.value,
                source_id=sourcing.source_id,
                source_url=sourcing.source_url,
                title=final_title,
                description=description,
                images=json.dumps(processed_images),
                main_image=processed_images[0] if processed_images else sourcing.main_image,
                cost_price=sourcing.cost_price,
                sale_price=sale_price,
                detail_url=sourcing.source_url,
                status=ProductStatus.ACTIVE,
            )
            
            self.db.add(product)
            
            # 标记选品已上架
            sourcing.is_selected = True
            
            await self.db.commit()
            await self.db.refresh(product)
            
            logger.info(f"Product added to center: {product.id}")
            return product
            
        except Exception as e:
            logger.error(f"Add to product center error: {e}")
            await self.db.rollback()
            return None
    
    async def _process_images(
        self,
        images_json: str,
        config: PublishConfig,
        tenant_id: str,
        product_id: str,
    ) -> List[str]:
        """处理商品图片"""
        try:
            images = json.loads(images_json) if images_json else []
        except:
            images = []
        
        if not images:
            return []
        
        # 下载图片
        image_data_list = []
        for url in images[:9]:  # 最多9张
            data = await self.image_processor.download_image(url)
            if data:
                image_data_list.append(data)
        
        if not image_data_list:
            return images[:9]
        
        # 去重
        if config.remove_duplicates:
            image_data_list, _ = await self.image_processor.remove_similar_images(
                image_data_list,
                threshold=0.9,
            )
        
        # 配置处理选项
        watermark = None
        if config.add_watermark:
            watermark = WatermarkConfig(
                text=config.watermark_text,
                position="bottom_right",
                opacity=0.5,
            )
        
        compress = None
        if config.compress_images:
            compress = CompressConfig(
                quality=85,
                max_width=1200,
                max_height=1200,
            )
        
        # 批量处理
        results = await self.image_processor.batch_process(
            image_data_list,
            watermark=watermark,
            compress=compress,
        )
        
        # 收集处理后的图片
        processed_urls = []
        for i, result in enumerate(results):
            if result.success and result.data:
                # TODO: 上传到云存储，返回URL
                # 目前返回处理后的base64（实际应该上传到OSS/S3）
                processed_urls.append(f"data:image/jpeg;base64,{result.data[:100]}...")
                
                # 保存处理记录
                await self._save_image_record(
                    tenant_id, product_id, "compress",
                    images[i] if i < len(images) else "",
                    processed_urls[-1],
                    result,
                )
            else:
                # 处理失败，使用原图
                if i < len(images):
                    processed_urls.append(images[i])
        
        return processed_urls if processed_urls else images[:9]
    
    async def _save_optimize_record(
        self,
        tenant_id: str,
        product_id: str,
        optimize_type: str,
        original: str,
        optimized: str,
    ):
        """保存优化记录"""
        record = ProductOptimizeRecord(
            tenant_id=tenant_id,
            product_id=product_id,
            optimize_type=optimize_type,
            original_value=original,
            optimized_value=optimized,
        )
        self.db.add(record)
    
    async def _save_image_record(
        self,
        tenant_id: str,
        product_id: str,
        process_type: str,
        original_url: str,
        processed_url: str,
        result,
    ):
        """保存图片处理记录"""
        from app.models.product_models import ImageProcessRecord
        
        record = ImageProcessRecord(
            tenant_id=tenant_id,
            product_id=product_id,
            process_type=process_type,
            original_url=original_url,
            processed_url=processed_url,
            original_size=result.original_size,
            processed_size=result.size,
        )
        self.db.add(record)
    
    def _calc_sale_price(
        self,
        cost_price: float,
        markup: float,
        min_price: float,
        max_price: float,
    ) -> float:
        """计算售价"""
        price = cost_price * markup
        price = max(min_price, min(max_price, price))
        # 取整到0.9或0.99
        return round(price - 0.1, 1)
    
    async def create_batch_publish_task(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        sourcing_product_ids: List[str],
        target_account_ids: List[str],
        config: Optional[PublishConfig] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> Optional[PublishTask]:
        """
        创建批量发布任务
        """
        config = config or PublishConfig()
        
        try:
            # 创建任务
            task = PublishTask(
                tenant_id=tenant_id,
                user_id=user_id,
                name=name,
                description=f"批量发布 {len(sourcing_product_ids)} 个商品",
                target_accounts=json.dumps(target_account_ids),
                publish_settings=json.dumps({
                    'price_markup': config.price_markup,
                    'add_watermark': config.add_watermark,
                    'optimize_title': config.optimize_title,
                }),
                status=PublishTaskStatus.PENDING,
                total_count=len(sourcing_product_ids) * len(target_account_ids),
                scheduled_at=scheduled_at,
            )
            
            self.db.add(task)
            await self.db.flush()  # 获取task.id
            
            # 创建任务项
            for product_id in sourcing_product_ids:
                for account_id in target_account_ids:
                    task_item = PublishTaskItem(
                        task_id=task.id,
                        product_id=product_id,
                        title="",  # 稍后填充
                        images="[]",
                        price=0,
                        status=PublishStatus.PENDING,
                    )
                    self.db.add(task_item)
            
            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(f"Batch publish task created: {task.id}")
            return task
            
        except Exception as e:
            logger.error(f"Create batch task error: {e}")
            await self.db.rollback()
            return None
    
    async def execute_publish_task(self, task_id: str) -> bool:
        """
        执行发布任务
        """
        # 获取任务
        task = await self.db.get(PublishTask, task_id)
        if not task or task.status != PublishTaskStatus.PENDING:
            return False
        
        # 更新状态为执行中
        task.status = PublishTaskStatus.RUNNING
        task.started_at = datetime.now()
        await self.db.commit()
        
        try:
            # 获取任务项
            result = await self.db.execute(
                select(PublishTaskItem).where(
                    PublishTaskItem.task_id == task_id
                )
            )
            task_items = result.scalars().all()
            
            # 逐个执行
            for item in task_items:
                result = await self._publish_single_item(item, task)
                
                if result.success:
                    task.success_count += 1
                    item.status = PublishStatus.PUBLISHED
                    item.xianyu_item_id = result.xianyu_item_id
                    item.published_at = datetime.now()
                else:
                    task.failed_count += 1
                    item.status = PublishStatus.FAILED
                    item.error_message = result.error_message
                
                await self.db.commit()
            
            # 更新任务状态
            task.status = PublishTaskStatus.COMPLETED
            task.completed_at = datetime.now()
            await self.db.commit()
            
            logger.info(f"Publish task completed: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Execute publish task error: {e}")
            task.status = PublishTaskStatus.FAILED
            await self.db.commit()
            return False
    
    async def _publish_single_item(
        self,
        item: PublishTaskItem,
        task: PublishTask,
    ) -> PublishResult:
        """发布单个商品"""
        try:
            # 获取源商品
            sourcing = await self.db.get(SourcingProduct, item.product_id)
            if not sourcing:
                return PublishResult(
                    success=False,
                    error_message="源商品不存在",
                )
            
            # 获取发布配置
            settings = json.loads(task.publish_settings)
            config = PublishConfig(
                price_markup=settings.get('price_markup', 1.5),
                add_watermark=settings.get('add_watermark', True),
                optimize_title=settings.get('optimize_title', True),
            )
            
            # 先添加到商品中心
            product = await self.add_to_product_center(
                task.tenant_id,
                sourcing.id,
                config,
            )
            
            if not product:
                return PublishResult(
                    success=False,
                    error_message="添加到商品中心失败",
                )
            
            # 更新任务项
            item.title = product.title
            item.description = product.description
            item.images = product.images
            item.price = product.sale_price
            
            # TODO: 调用闲鱼API发布商品
            # xianyu_item_id = await self._publish_to_xianyu(product, account_id)
            xianyu_item_id = f"mock_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            return PublishResult(
                success=True,
                product_id=product.id,
                xianyu_item_id=xianyu_item_id,
                published_at=datetime.now(),
            )
            
        except Exception as e:
            logger.error(f"Publish single item error: {e}")
            return PublishResult(
                success=False,
                error_message=str(e),
            )
    
    async def get_task_progress(self, task_id: str) -> Dict:
        """获取任务进度"""
        task = await self.db.get(PublishTask, task_id)
        if not task:
            return {}
        
        total = task.total_count
        completed = task.success_count + task.failed_count
        
        return {
            'task_id': task.id,
            'status': task.status.value,
            'total': total,
            'completed': completed,
            'success': task.success_count,
            'failed': task.failed_count,
            'progress': round(completed / total * 100, 1) if total > 0 else 0,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = await self.db.get(PublishTask, task_id)
        if not task or task.status not in (PublishTaskStatus.PENDING, PublishTaskStatus.RUNNING):
            return False
        
        task.status = PublishTaskStatus.CANCELLED
        await self.db.commit()
        return True
    
    async def close(self):
        """关闭资源"""
        await self.image_processor.close()
