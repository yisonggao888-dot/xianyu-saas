"""
选品服务
"""
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.models import Product, ProductStatus, OrderStatus, Order
from app.services.scraper import ProductScraper, ProductItem


class ProductService:
    """选品服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scraper = ProductScraper()
    
    async def search_products(
        self,
        tenant_id: str,
        keyword: str,
        sources: List[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_sales: Optional[int] = None,
        sort: str = "default",
    ) -> Dict[str, List[Dict]]:
        """
        搜索商品
        
        Returns:
            {
                'pdd': [{'id': ..., 'title': ..., ...}, ...],
                '1688': [...]
            }
        """
        sources = sources or ['pdd', '1688']
        
        # 抓取商品
        results = await self.scraper.search_all(
            keyword=keyword,
            sources=sources,
            sort=sort,
            min_price=int(min_price * 100) if min_price else None,
            max_price=int(max_price * 100) if max_price else None,
        )
        
        # 转换为可序列化的字典
        formatted_results = {}
        
        for source, products in results.items():
            formatted_products = []
            
            for p in products:
                # 过滤
                if min_sales and p.sales_count < min_sales:
                    continue
                
                formatted_products.append({
                    'source': p.source,
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
                    'profit_margin': self._calc_margin(p.price),
                })
            
            formatted_results[source] = formatted_products
        
        await self.scraper.close()
        
        return formatted_results
    
    def _calc_margin(self, cost_price: float) -> Dict:
        """计算建议售价和利润率"""
        # 建议售价 = 成本价 * 1.4 (40%利润)
        suggested_price = round(cost_price * 1.4, 2)
        profit = round(suggested_price - cost_price, 2)
        margin_percent = round((profit / cost_price) * 100, 1)
        
        return {
            'suggested_price': suggested_price,
            'profit': profit,
            'margin_percent': margin_percent,
        }
    
    async def add_to_list(
        self,
        tenant_id: str,
        source: str,
        source_id: str,
        title: str,
        cost_price: float,
        sale_price: float,
        main_image: str,
        detail_url: str,
        description: Optional[str] = None,
    ) -> Product:
        """添加商品到选品列表"""
        # 检查是否已存在
        result = await self.db.execute(
            select(Product).where(
                and_(
                    Product.tenant_id == tenant_id,
                    Product.source == source,
                    Product.source_id == source_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"商品已存在: {existing.id}")
            return existing
        
        # 创建商品
        product = Product(
            tenant_id=tenant_id,
            source=source,
            source_id=source_id,
            title=title,
            cost_price=cost_price,
            sale_price=sale_price,
            main_image=main_image,
            detail_url=detail_url,
            description=description,
            status=ProductStatus.ACTIVE,
        )
        
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        
        logger.info(f"添加商品成功: {product.id}")
        
        return product
    
    async def get_product_list(
        self,
        tenant_id: str,
        status: Optional[str] = None,
    ) -> List[Product]:
        """获取选品列表"""
        query = select(Product).where(Product.tenant_id == tenant_id)
        
        if status:
            query = query.where(Product.status == status)
        
        query = query.order_by(desc(Product.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_product(self, tenant_id: str, product_id: str) -> Optional[Product]:
        """获取商品详情"""
        result = await self.db.execute(
            select(Product).where(
                and_(
                    Product.id == product_id,
                    Product.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_product(
        self,
        tenant_id: str,
        product_id: str,
        **kwargs
    ) -> bool:
        """更新商品"""
        product = await self.get_product(tenant_id, product_id)
        if not product:
            return False
        
        allowed_fields = [
            'title', 'sale_price', 'main_image', 'description', 'status'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(product, field):
                setattr(product, field, value)
        
        product.updated_at = datetime.now()
        await self.db.commit()
        
        return True
    
    async def delete_product(self, tenant_id: str, product_id: str) -> bool:
        """删除商品"""
        product = await self.get_product(tenant_id, product_id)
        if not product:
            return False
        
        product.status = ProductStatus.DELETED
        await self.db.commit()
        
        return True
    
    async def get_stats(self, tenant_id: str) -> Dict:
        """获取选品统计"""
        # 商品总数
        result = await self.db.execute(
            select(Product).where(
                and_(
                    Product.tenant_id == tenant_id,
                    Product.status != ProductStatus.DELETED,
                )
            )
        )
        total_products = len(result.scalars().all())
        
        # 已上架数量
        result = await self.db.execute(
            select(Product).where(
                and_(
                    Product.tenant_id == tenant_id,
                    Product.status == ProductStatus.ACTIVE,
                )
            )
        )
        active_products = len(result.scalars().all())
        
        # 已售出订单数
        result = await self.db.execute(
            select(Order).where(
                and_(
                    Order.tenant_id == tenant_id,
                    Order.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED]),
                )
            )
        )
        orders = result.scalars().all()
        total_orders = len(orders)
        
        # 总销售额
        total_sales = sum(o.sale_price for o in orders)
        
        # 总利润
        total_profit = sum((o.sale_price - o.cost_price) for o in orders)
        
        return {
            'total_products': total_products,
            'active_products': active_products,
            'total_orders': total_orders,
            'total_sales': round(total_sales, 2),
            'total_profit': round(total_profit, 2),
        }
