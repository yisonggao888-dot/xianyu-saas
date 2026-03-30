"""
定时擦亮服务 - 自动刷新商品曝光
"""
import json
import asyncio
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.models.product_models import (
    PolishSchedule, PolishScheduleStatus, PolishLog
)
from app.services.xianyu_api import XianyuAPI


@dataclass
class PolishConfig:
    """擦亮配置"""
    # 执行时间配置
    interval_minutes: int = 60  # 默认每小时
    cron_expression: Optional[str] = None  # Cron表达式，如 "0 9,15 * * *"
    
    # 擦亮范围
    polish_all: bool = True  # 是否擦亮全部商品
    item_ids: List[str] = None  # 指定商品ID列表
    
    # 限制
    max_items_per_run: int = 50  # 每次最多擦亮数量
    min_interval_between_items: int = 5  # 商品间最小间隔（秒）
    
    # 时间窗口
    only_work_hours: bool = True  # 仅工作时间
    work_hours_start: int = 9  # 工作开始时间
    work_hours_end: int = 22  # 工作结束时间


class PolishService:
    """
    定时擦亮服务
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scheduler = AsyncIOScheduler()
        self._scheduled_jobs = {}  # job_id -> {schedule_id, job}
    
    async def create_schedule(
        self,
        tenant_id: str,
        account_id: str,
        name: str,
        config: PolishConfig,
    ) -> Optional[PolishSchedule]:
        """
        创建定时擦亮计划
        """
        try:
            # 计算下次执行时间
            next_run = self._calc_next_run(config)
            
            schedule = PolishSchedule(
                tenant_id=tenant_id,
                account_id=account_id,
                name=name,
                schedule_type="interval" if not config.cron_expression else "cron",
                interval_minutes=config.interval_minutes,
                cron_expression=config.cron_expression,
                item_filter=json.dumps({
                    'polish_all': config.polish_all,
                    'item_ids': config.item_ids or [],
                }),
                max_items_per_run=config.max_items_per_run,
                status=PolishScheduleStatus.ACTIVE,
                next_run_at=next_run,
            )
            
            self.db.add(schedule)
            await self.db.commit()
            await self.db.refresh(schedule)
            
            # 添加到调度器
            await self._schedule_job(schedule)
            
            logger.info(f"Polish schedule created: {schedule.id}")
            return schedule
            
        except Exception as e:
            logger.error(f"Create schedule error: {e}")
            await self.db.rollback()
            return None
    
    def _calc_next_run(self, config: PolishConfig) -> datetime:
        """计算下次执行时间"""
        now = datetime.now()
        
        if config.cron_expression:
            # Cron表达式，使用APScheduler解析
            trigger = CronTrigger.from_crontab(config.cron_expression)
            return trigger.get_next_fire_time(None, now)
        else:
            # 间隔模式
            return now + timedelta(minutes=config.interval_minutes)
    
    async def _schedule_job(self, schedule: PolishSchedule):
        """将计划添加到调度器"""
        job_id = f"polish_{schedule.id}"
        
        # 移除已存在的任务
        if job_id in self._scheduled_jobs:
            old_job = self._scheduled_jobs[job_id].get('job')
            if old_job:
                old_job.remove()
        
        # 创建触发器
        if schedule.cron_expression:
            trigger = CronTrigger.from_crontab(schedule.cron_expression)
        else:
            trigger = IntervalTrigger(minutes=schedule.interval_minutes or 60)
        
        # 添加任务
        job = self.scheduler.add_job(
            func=self._execute_polish_job,
            trigger=trigger,
            id=job_id,
            args=[schedule.id],
            replace_existing=True,
        )
        
        self._scheduled_jobs[job_id] = {
            'schedule_id': schedule.id,
            'job': job,
        }
        
        logger.info(f"Job scheduled: {job_id}")
    
    async def _execute_polish_job(self, schedule_id: str):
        """执行擦亮任务（由调度器调用）"""
        logger.info(f"Executing polish job: {schedule_id}")
        
        # 创建新的数据库会话
        from app.db.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            service = PolishService(db)
            await service.execute_polish(schedule_id)
    
    async def execute_polish(self, schedule_id: str) -> bool:
        """
        执行擦亮操作
        """
        schedule = await self.db.get(PolishSchedule, schedule_id)
        if not schedule or schedule.status != PolishScheduleStatus.ACTIVE:
            return False
        
        # 检查是否在允许的时间窗口
        config = self._parse_config(schedule)
        if config.only_work_hours:
            now = datetime.now()
            if not (config.work_hours_start <= now.hour < config.work_hours_end):
                logger.info(f"Skip polish for {schedule_id}: outside work hours")
                return False
        
        # 更新执行时间
        schedule.last_run_at = datetime.now()
        schedule.total_runs += 1
        await self.db.commit()
        
        try:
            # 获取要擦亮的商品列表
            items = await self._get_items_to_polish(schedule, config)
            
            if not items:
                logger.info(f"No items to polish for schedule {schedule_id}")
                return True
            
            # 逐个擦亮
            success_count = 0
            failed_count = 0
            details = []
            
            for item_id in items:
                result = await self._polish_single_item(
                    schedule.account_id,
                    item_id,
                )
                
                if result['success']:
                    success_count += 1
                else:
                    failed_count += 1
                
                details.append(result)
                
                # 间隔等待
                if config.min_interval_between_items > 0:
                    await asyncio.sleep(config.min_interval_between_items)
            
            # 更新统计
            schedule.success_runs += 1 if success_count > 0 else 0
            schedule.failed_runs += 1 if failed_count > 0 else 0
            
            # 计算下次执行时间
            schedule.next_run_at = self._calc_next_run(config)
            await self.db.commit()
            
            # 记录日志
            await self._save_polish_log(
                schedule_id=schedule_id,
                account_id=schedule.account_id,
                status='success' if failed_count == 0 else 'partial',
                items_polished=success_count,
                items_failed=failed_count,
                details=details,
            )
            
            logger.info(
                f"Polish completed for {schedule_id}: "
                f"success={success_count}, failed={failed_count}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Execute polish error: {e}")
            schedule.failed_runs += 1
            await self.db.commit()
            
            await self._save_polish_log(
                schedule_id=schedule_id,
                account_id=schedule.account_id,
                status='failed',
                items_polished=0,
                items_failed=0,
                error_message=str(e),
            )
            return False
    
    def _parse_config(self, schedule: PolishSchedule) -> PolishConfig:
        """解析配置"""
        try:
            item_filter = json.loads(schedule.item_filter or '{}')
        except:
            item_filter = {}
        
        return PolishConfig(
            interval_minutes=schedule.interval_minutes or 60,
            cron_expression=schedule.cron_expression,
            max_items_per_run=schedule.max_items_per_run,
            polish_all=item_filter.get('polish_all', True),
            item_ids=item_filter.get('item_ids', []),
        )
    
    async def _get_items_to_polish(
        self,
        schedule: PolishSchedule,
        config: PolishConfig,
    ) -> List[str]:
        """获取要擦亮的商品列表"""
        # TODO: 从闲鱼API获取商品列表
        # 目前返回模拟数据
        
        if config.polish_all:
            # 获取账号下的所有在售商品
            # items = await self._fetch_account_items(schedule.account_id)
            # return items[:config.max_items_per_run]
            return [f"item_{i}" for i in range(min(10, config.max_items_per_run))]
        else:
            return config.item_ids[:config.max_items_per_run] if config.item_ids else []
    
    async def _polish_single_item(
        self,
        account_id: str,
        item_id: str,
    ) -> Dict:
        """擦亮单个商品"""
        try:
            # TODO: 调用闲鱼擦亮API
            # api = XianyuAPI()
            # result = await api.polish_item(account_id, item_id)
            
            # 模拟成功
            await asyncio.sleep(0.5)
            
            return {
                'item_id': item_id,
                'success': True,
                'message': '擦亮成功',
                'polished_at': datetime.now().isoformat(),
            }
            
        except Exception as e:
            return {
                'item_id': item_id,
                'success': False,
                'message': str(e),
            }
    
    async def _save_polish_log(
        self,
        schedule_id: str,
        account_id: str,
        status: str,
        items_polished: int,
        items_failed: int,
        details: List[Dict] = None,
        error_message: str = None,
    ):
        """保存擦亮日志"""
        log = PolishLog(
            schedule_id=schedule_id,
            account_id=account_id,
            status=status,
            items_polished=items_polished,
            items_failed=items_failed,
            error_message=error_message,
            details=json.dumps(details) if details else None,
        )
        self.db.add(log)
        await self.db.commit()
    
    async def pause_schedule(self, schedule_id: str) -> bool:
        """暂停计划"""
        schedule = await self.db.get(PolishSchedule, schedule_id)
        if not schedule:
            return False
        
        schedule.status = PolishScheduleStatus.PAUSED
        await self.db.commit()
        
        # 暂停调度器中的任务
        job_id = f"polish_{schedule_id}"
        if job_id in self._scheduled_jobs:
            job = self._scheduled_jobs[job_id].get('job')
            if job:
                job.pause()
        
        return True
    
    async def resume_schedule(self, schedule_id: str) -> bool:
        """恢复计划"""
        schedule = await self.db.get(PolishSchedule, schedule_id)
        if not schedule:
            return False
        
        schedule.status = PolishScheduleStatus.ACTIVE
        await self.db.commit()
        
        # 恢复调度器中的任务
        job_id = f"polish_{schedule_id}"
        if job_id in self._scheduled_jobs:
            job = self._scheduled_jobs[job_id].get('job')
            if job:
                job.resume()
        else:
            # 重新调度
            await self._schedule_job(schedule)
        
        return True
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """删除计划"""
        schedule = await self.db.get(PolishSchedule, schedule_id)
        if not schedule:
            return False
        
        # 从调度器移除
        job_id = f"polish_{schedule_id}"
        if job_id in self._scheduled_jobs:
            job = self._scheduled_jobs[job_id].get('job')
            if job:
                job.remove()
            del self._scheduled_jobs[job_id]
        
        await self.db.delete(schedule)
        await self.db.commit()
        
        return True
    
    async def get_schedule_stats(self, schedule_id: str) -> Dict:
        """获取计划统计"""
        schedule = await self.db.get(PolishSchedule, schedule_id)
        if not schedule:
            return {}
        
        # 获取最近日志
        result = await self.db.execute(
            select(PolishLog).where(
                PolishLog.schedule_id == schedule_id
            ).order_by(PolishLog.executed_at.desc()).limit(10)
        )
        recent_logs = result.scalars().all()
        
        return {
            'schedule_id': schedule.id,
            'name': schedule.name,
            'status': schedule.status.value,
            'total_runs': schedule.total_runs,
            'success_runs': schedule.success_runs,
            'failed_runs': schedule.failed_runs,
            'success_rate': round(
                schedule.success_runs / schedule.total_runs * 100, 1
            ) if schedule.total_runs > 0 else 0,
            'last_run_at': schedule.last_run_at.isoformat() if schedule.last_run_at else None,
            'next_run_at': schedule.next_run_at.isoformat() if schedule.next_run_at else None,
            'recent_logs': [
                {
                    'executed_at': log.executed_at.isoformat(),
                    'status': log.status,
                    'items_polished': log.items_polished,
                }
                for log in recent_logs
            ],
        }
    
    async def manual_polish(
        self,
        account_id: str,
        item_ids: List[str],
    ) -> Dict:
        """
        手动擦亮商品
        """
        results = []
        success_count = 0
        
        for item_id in item_ids:
            result = await self._polish_single_item(account_id, item_id)
            results.append(result)
            if result['success']:
                success_count += 1
            await asyncio.sleep(1)  # 手动擦亮间隔
        
        return {
            'total': len(item_ids),
            'success': success_count,
            'failed': len(item_ids) - success_count,
            'results': results,
        }
    
    async def start_scheduler(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Polish scheduler started")
    
    async def stop_scheduler(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Polish scheduler stopped")
    
    async def load_active_schedules(self):
        """加载所有活动的计划"""
        result = await self.db.execute(
            select(PolishSchedule).where(
                PolishSchedule.status == PolishScheduleStatus.ACTIVE
            )
        )
        schedules = result.scalars().all()
        
        for schedule in schedules:
            await self._schedule_job(schedule)
        
        logger.info(f"Loaded {len(schedules)} active schedules")
