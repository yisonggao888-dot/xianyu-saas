"""
订单服务
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.models import Order, OrderStatus, Conversation, Product


class OrderService:
    """订单服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_from_conversation(
        self,
        tenant_id: str,
        conversation_id: str,
        xianyu_order_id: str,
        buyer_id: str,
        item_title: str,
        sold_price: float,
        cost_price: float,
    ) -> Order:
        """从对话创建订单"""
        profit = sold_price - cost_price
        
        order = Order(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            xianyu_order_id=xianyu_order_id,
            buyer_id=buyer_id,
            item_title=item_title,
            sold_price=sold_price,
            cost_price=cost_price,
            profit=profit,
            status=OrderStatus.PENDING,
        )
        
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        
        logger.info(f"创建订单成功: {order.id}")
        
        return order
    
    async def get_order_list(
        self,
        tenant_id: str,
        status: Optional[OrderStatus] = None,
        days: Optional[int] = None,
    ) -> List[Order]:
        """获取订单列表"""
        query = select(Order).where(Order.tenant_id == tenant_id)
        
        if status:
            query = query.where(Order.status == status)
        
        if days:
            start_date = datetime.now() - timedelta(days=days)
            query = query.where(Order.created_at >= start_date)
        
        query = query.order_by(desc(Order.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_order(self, tenant_id: str, order_id: str) -> Optional[Order]:
        """获取订单详情"""
        result = await self.db.execute(
            select(Order).where(
                and_(
                    Order.id == order_id,
                    Order.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        tenant_id: str,
        order_id: str,
        status: OrderStatus,
        **kwargs
    ) -> bool:
        """更新订单状态"""
        order = await self.get_order(tenant_id, order_id)
        if not order:
            return False
        
        order.status = status
        
        # 根据状态更新时间戳
        now = datetime.now()
        if status == OrderStatus.PAID:
            order.paid_at = now
        elif status == OrderStatus.SHIPPED:
            order.shipped_at = now
        elif status == OrderStatus.COMPLETED:
            order.completed_at = now
        
        # 更新其他字段
        for field, value in kwargs.items():
            if hasattr(order, field) and value is not None:
                setattr(order, field, value)
        
        order.updated_at = now
        await self.db.commit()
        
        logger.info(f"订单状态更新: {order_id} -> {status.value}")
        
        return True
    
    async def update_source_info(
        self,
        tenant_id: str,
        order_id: str,
        source_platform: str,
        source_order_id: str,
    ) -> bool:
        """更新货源信息"""
        order = await self.get_order(tenant_id, order_id)
        if not order:
            return False
        
        order.source_platform = source_platform
        order.source_order_id = source_order_id
        order.updated_at = datetime.now()
        
        await self.db.commit()
        
        return True
    
    async def update_tracking(
        self,
        tenant_id: str,
        order_id: str,
        tracking_number: str,
    ) -> bool:
        """更新物流单号"""
        return await self.update_status(
            tenant_id, order_id, OrderStatus.SHIPPED,
            tracking_number=tracking_number
        )
    
    async def get_stats(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> Dict:
        """获取订单统计"""
        start_date = datetime.now() - timedelta(days=days)
        
        # 总订单数
        result = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.created_at >= start_date,
                )
            )
        )
        total_orders = result.scalar() or 0
        
        # 各状态订单数
        status_counts = {}
        for status in OrderStatus:
            result = await self.db.execute(
                select(func.count(Order.id)).where(
                    and_(
                        Order.tenant_id == tenant_id,
                        Order.status == status,
                        Order.created_at >= start_date,
                    )
                )
            )
            status_counts[status.value] = result.scalar() or 0
        
        # 总销售额
        result = await self.db.execute(
            select(func.sum(Order.sold_price)).where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED]),
                    Order.created_at >= start_date,
                )
            )
        )
        total_sales = result.scalar() or 0
        
        # 总利润
        result = await self.db.execute(
            select(func.sum(Order.profit)).where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED]),
                    Order.created_at >= start_date,
                )
            )
        )
        total_profit = result.scalar() or 0
        
        # 平均利润率
        avg_margin = 0
        if total_sales > 0:
            avg_margin = round((total_profit / total_sales) * 100, 1)
        
        # 待处理订单
        pending_count = (
            status_counts.get(OrderStatus.PENDING.value, 0) +
            status_counts.get(OrderStatus.PAID.value, 0)
        )
        
        return {
            'total_orders': total_orders,
            'pending_count': pending_count,
            'completed_count': status_counts.get(OrderStatus.COMPLETED.value, 0),
            'total_sales': round(total_sales, 2),
            'total_profit': round(total_profit, 2),
            'avg_margin_percent': avg_margin,
            'status_distribution': status_counts,
        }
    
    async def get_daily_stats(
        self,
        tenant_id: str,
        days: int = 7,
    ) -> List[Dict]:
        """获取每日统计（用于图表）"""
        results = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            # 该日订单数
            result = await self.db.execute(
                select(func.count(Order.id)).where(
                    and_(
                        Order.tenant_id == tenant_id,
                        Order.created_at >= start_of_day,
                        Order.created_at < end_of_day,
                    )
                )
            )
            order_count = result.scalar() or 0
            
            # 该日销售额
            result = await self.db.execute(
                select(func.sum(Order.sold_price)).where(
                    and_(
                        Order.tenant_id == tenant_id,
                        Order.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED]),
                        Order.created_at >= start_of_day,
                        Order.created_at < end_of_day,
                    )
                )
            )
            sales = result.scalar() or 0
            
            # 该日利润
            result = await self.db.execute(
                select(func.sum(Order.profit)).where(
                    and_(
                        Order.tenant_id == tenant_id,
                        Order.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED]),
                        Order.created_at >= start_of_day,
                        Order.created_at < end_of_day,
                    )
                )
            )
            profit = result.scalar() or 0
            
            results.append({
                'date': start_of_day.strftime('%Y-%m-%d'),
                'orders': order_count,
                'sales': round(sales, 2),
                'profit': round(profit, 2),
            })
        
        # 反转，按日期正序
        results.reverse()
        
        return results
    
    async def auto_purchase(
        self,
        tenant_id: str,
        order_id: str,
        product_id: str,
    ) -> Dict:
        """
        自动到货源平台采购
        
        TODO: 实现拼多多/1688自动下单
        """
        order = await self.get_order(tenant_id, order_id)
        if not order:
            return {'success': False, 'error': '订单不存在'}
        
        # TODO: 获取商品详情，调用采购API
        # 1. 获取商品链接
        # 2. 调用Playwright模拟下单
        # 3. 获取货源订单号
        # 4. 更新订单状态
        
        logger.info(f"自动采购订单: {order_id}, 商品: {product_id}")
        
        return {
            'success': True,
            'message': '采购任务已创建',
            'order_id': order_id,
        }
