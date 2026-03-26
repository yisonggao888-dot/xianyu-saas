"""
采购任务队列 - 异步处理下单
"""
import asyncio
import json
from typing import Dict, Optional, Callable
from datetime import datetime
from enum import Enum as PyEnum
from dataclasses import dataclass, asdict

from loguru import logger


class PurchaseStatus(str, PyEnum):
    """采购任务状态"""
    PENDING = "pending"           # 待处理
    PROCESSING = "processing"     # 处理中
    NEED_LOGIN = "need_login"     # 需要登录
    NEED_CAPTCHA = "need_captcha" # 需要验证码
    SUCCESS = "success"           # 成功
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消


@dataclass
class PurchaseTask:
    """采购任务"""
    id: str                       # 任务ID
    order_id: str                 # 订单ID
    tenant_id: str                # 租户ID
    
    # 商品信息
    source: str                   # pdd / 1688
    source_id: str                # 源平台商品ID
    source_url: str               # 商品链接
    
    # 采购信息
    sku_spec: Optional[str]       # 规格选择
    quantity: int                 # 数量
    buyer_name: str               # 买家姓名
    buyer_phone: str              # 买家电话
    buyer_address: str            # 买家地址
    
    # 任务状态
    status: PurchaseStatus = PurchaseStatus.PENDING
    result: Optional[Dict] = None # 结果
    error_msg: Optional[str] = None
    
    # 时间戳
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class PurchaseQueue:
    """
    采购任务队列
    
    内存队列，后续可替换为Redis/RabbitMQ
    """
    
    def __init__(self):
        self._queue: asyncio.Queue[PurchaseTask] = asyncio.Queue()
        self._tasks: Dict[str, PurchaseTask] = {}  # 所有任务存储
        self._callbacks: Dict[str, Callable] = {}   # 完成回调
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动队列处理器"""
        if self._running:
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("采购队列已启动")
    
    async def stop(self):
        """停止队列处理器"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("采购队列已停止")
    
    async def _worker(self):
        """队列工作线程"""
        while self._running:
            try:
                # 获取任务
                task = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                
                # 处理任务
                await self._process_task(task)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"队列处理异常: {e}")
    
    async def _process_task(self, task: PurchaseTask):
        """处理单个任务"""
        from app.services.purchase_service import PurchaseService
        
        task.status = PurchaseStatus.PROCESSING
        task.started_at = datetime.now()
        
        logger.info(f"开始处理采购任务: {task.id}")
        
        try:
            service = PurchaseService()
            result = await service.purchase(task)
            
            if result['success']:
                task.status = PurchaseStatus.SUCCESS
                task.result = result
                logger.info(f"采购任务成功: {task.id}")
            else:
                task.status = PurchaseStatus.FAILED
                task.error_msg = result.get('error', '未知错误')
                logger.error(f"采购任务失败: {task.id} - {task.error_msg}")
        
        except Exception as e:
            task.status = PurchaseStatus.FAILED
            task.error_msg = str(e)
            logger.error(f"采购任务异常: {task.id} - {e}")
        
        finally:
            task.completed_at = datetime.now()
            
            # 调用回调
            if task.id in self._callbacks:
                try:
                    callback = self._callbacks[task.id]
                    await callback(task)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
    
    async def submit(self, task: PurchaseTask, callback: Optional[Callable] = None) -> str:
        """提交任务"""
        self._tasks[task.id] = task
        
        if callback:
            self._callbacks[task.id] = callback
        
        await self._queue.put(task)
        
        logger.info(f"采购任务已提交: {task.id}")
        
        return task.id
    
    def get_task(self, task_id: str) -> Optional[PurchaseTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_tasks_by_order(self, order_id: str) -> list:
        """获取订单的所有任务"""
        return [
            t for t in self._tasks.values()
            if t.order_id == order_id
        ]
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [PurchaseStatus.PENDING]:
            task.status = PurchaseStatus.CANCELLED
            return True
        
        return False
    
    def get_stats(self) -> Dict:
        """获取队列统计"""
        stats = {
            'pending': 0,
            'processing': 0,
            'success': 0,
            'failed': 0,
            'total': len(self._tasks),
        }
        
        for task in self._tasks.values():
            if task.status == PurchaseStatus.PENDING:
                stats['pending'] += 1
            elif task.status == PurchaseStatus.PROCESSING:
                stats['processing'] += 1
            elif task.status == PurchaseStatus.SUCCESS:
                stats['success'] += 1
            elif task.status == PurchaseStatus.FAILED:
                stats['failed'] += 1
        
        return stats


# 全局队列实例
_purchase_queue: Optional[PurchaseQueue] = None


def get_purchase_queue() -> PurchaseQueue:
    """获取采购队列实例"""
    global _purchase_queue
    if _purchase_queue is None:
        _purchase_queue = PurchaseQueue()
    return _purchase_queue
