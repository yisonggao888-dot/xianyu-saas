"""
选品分析服务 - 爆款筛选、数据分析
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import math

from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.product_models import SourcingProduct, ProductSource


@dataclass
class HotProductCriteria:
    """爆款筛选条件"""
    min_monthly_sales: int = 100  # 最低月销量
    min_profit_margin: float = 30.0  # 最低利润率(%)
    max_competition: float = 0.8  # 最大竞争指数(0-1)
    min_rating: float = 4.0  # 最低评分
    price_range: Tuple[float, float] = (10.0, 500.0)  # 价格范围
    
    # 权重配置（用于计算综合得分）
    sales_weight: float = 0.3
    profit_weight: float = 0.3
    rating_weight: float = 0.2
    competition_weight: float = 0.2


@dataclass
class ProductScore:
    """商品评分结果"""
    product_id: str
    hot_score: float  # 热度分 (0-100)
    profit_score: float  # 盈利分 (0-100)
    competition_score: float  # 竞争分 (0-100，越高竞争越小)
    comprehensive_score: float  # 综合得分
    
    # 各项指标
    sales_rank: int  # 销量排名
    profit_potential: float  # 盈利潜力
    market_saturation: float  # 市场饱和度


class SourcingAnalyzer:
    """
    选品分析器 - 分析商品数据，筛选爆款
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def analyze_products(
        self,
        tenant_id: str,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        source: Optional[ProductSource] = None,
    ) -> List[Dict]:
        """
        分析商品数据，计算各项指标
        
        Returns:
            分析后的商品列表，包含热度分、盈利潜力等
        """
        # 构建查询
        query = select(SourcingProduct).where(
            SourcingProduct.tenant_id == tenant_id
        )
        
        if keyword:
            query = query.where(SourcingProduct.title.contains(keyword))
        if category:
            query = query.where(SourcingProduct.category == category)
        if source:
            query = query.where(SourcingProduct.source == source)
        
        # 只分析最近30天的数据
        thirty_days_ago = datetime.now() - timedelta(days=30)
        query = query.where(SourcingProduct.crawled_at >= thirty_days_ago)
        
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        if not products:
            return []
        
        # 计算统计数据（用于标准化）
        stats = self._calculate_stats(products)
        
        # 分析每个商品
        analyzed_products = []
        for product in products:
            analysis = self._analyze_single_product(product, stats)
            analyzed_products.append(analysis)
        
        # 按综合得分排序
        analyzed_products.sort(key=lambda x: x['comprehensive_score'], reverse=True)
        
        return analyzed_products
    
    def _calculate_stats(self, products: List[SourcingProduct]) -> Dict:
        """计算统计数据用于标准化"""
        sales_list = [p.monthly_sales or 0 for p in products]
        price_list = [p.cost_price for p in products]
        rating_list = [p.rating or 0 for p in products if p.rating]
        
        return {
            'max_sales': max(sales_list) if sales_list else 1,
            'min_sales': min(sales_list) if sales_list else 0,
            'avg_price': sum(price_list) / len(price_list) if price_list else 0,
            'max_rating': max(rating_list) if rating_list else 5,
            'total_count': len(products),
        }
    
    def _analyze_single_product(
        self, 
        product: SourcingProduct, 
        stats: Dict
    ) -> Dict:
        """分析单个商品"""
        # 计算热度分（基于销量）
        sales_score = self._calc_sales_score(product.monthly_sales or 0, stats)
        
        # 计算盈利潜力（基于价格差和市场空间）
        profit_score = self._calc_profit_score(product)
        
        # 计算竞争指数（基于同类商品数量和市场饱和度）
        competition_score = self._calc_competition_score(product, stats)
        
        # 计算综合得分
        comprehensive_score = (
            sales_score * 0.3 +
            profit_score * 0.4 +
            competition_score * 0.3
        )
        
        return {
            'id': product.id,
            'source': product.source.value,
            'source_id': product.source_id,
            'title': product.title,
            'main_image': product.main_image,
            'cost_price': product.cost_price,
            'original_price': product.original_price,
            'monthly_sales': product.monthly_sales,
            'total_sales': product.total_sales,
            'rating': product.rating,
            'review_count': product.review_count,
            'shop_name': product.shop_name,
            'category': product.category,
            'source_url': product.source_url,
            
            # 分析指标
            'hot_score': round(sales_score, 1),
            'profit_score': round(profit_score, 1),
            'competition_score': round(competition_score, 1),
            'comprehensive_score': round(comprehensive_score, 1),
            
            # 建议售价和利润
            'suggested_price': round(product.cost_price * 1.5, 2),
            'estimated_profit': round(product.cost_price * 0.5, 2),
            'profit_margin': 50.0,
        }
    
    def _calc_sales_score(self, monthly_sales: int, stats: Dict) -> float:
        """计算销量得分（0-100）"""
        if stats['max_sales'] == stats['min_sales']:
            return 50.0
        
        # 使用对数标准化，避免极端值影响
        log_sales = math.log1p(monthly_sales)
        log_max = math.log1p(stats['max_sales'])
        
        score = (log_sales / log_max) * 100 if log_max > 0 else 0
        return min(100, max(0, score))
    
    def _calc_profit_score(self, product: SourcingProduct) -> float:
        """计算盈利潜力得分（0-100）"""
        score = 0.0
        
        # 价格区间得分（适中价格更好卖）
        price = product.cost_price
        if 20 <= price <= 100:
            score += 30  # 最佳价格区间
        elif 10 <= price < 20 or 100 < price <= 200:
            score += 20
        else:
            score += 10
        
        # 折扣力度得分（原价vs现价）
        if product.original_price and product.original_price > product.cost_price:
            discount = (product.original_price - product.cost_price) / product.original_price
            score += min(30, discount * 100)
        else:
            score += 15
        
        # 销量增长潜力（基于现有销量和市场空间）
        if product.monthly_sales:
            if product.monthly_sales >= 1000:
                score += 25  # 已验证的市场
            elif product.monthly_sales >= 100:
                score += 35  # 增长潜力大
            else:
                score += 20
        else:
            score += 10
        
        # 评分加成
        if product.rating:
            score += (product.rating / 5) * 15
        else:
            score += 7.5
        
        return min(100, score)
    
    def _calc_competition_score(self, product: SourcingProduct, stats: Dict) -> float:
        """
        计算竞争指数（0-100，越高表示竞争越小，机会越大）
        """
        score = 50.0  # 基础分
        
        # 基于销量的竞争度（销量过高可能竞争激烈）
        if product.monthly_sales:
            if product.monthly_sales > 10000:
                score -= 20  # 竞争可能很激烈
            elif product.monthly_sales > 5000:
                score -= 10
            elif product.monthly_sales > 1000:
                score += 10  # 有一定市场且竞争适中
            else:
                score += 20  # 小众市场，竞争小
        
        # 店铺评分加成（好店铺的商品竞争质量高）
        if product.shop_rating:
            if product.shop_rating >= 4.8:
                score -= 10  # 优质店铺，竞争激烈
            elif product.shop_rating >= 4.0:
                score += 5
            else:
                score += 15  # 店铺一般，有机会做得比它好
        
        # 评价数分析
        if product.review_count:
            if product.review_count > 10000:
                score -= 15
            elif product.review_count < 100:
                score += 15  # 评价少，竞争小
        
        return min(100, max(0, score))
    
    async def get_hot_products(
        self,
        tenant_id: str,
        criteria: Optional[HotProductCriteria] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        获取爆款商品列表
        
        Args:
            tenant_id: 租户ID
            criteria: 筛选条件
            limit: 返回数量限制
        """
        criteria = criteria or HotProductCriteria()
        
        # 先获取所有分析结果
        all_products = await self.analyze_products(tenant_id)
        
        # 按条件筛选
        filtered = []
        for p in all_products:
            # 销量筛选
            if (p['monthly_sales'] or 0) < criteria.min_monthly_sales:
                continue
            
            # 利润率筛选
            if p['profit_margin'] < criteria.min_profit_margin:
                continue
            
            # 竞争度筛选
            if p['competition_score'] < (1 - criteria.max_competition) * 100:
                continue
            
            # 评分筛选
            if (p['rating'] or 0) < criteria.min_rating:
                continue
            
            # 价格筛选
            if not (criteria.price_range[0] <= p['cost_price'] <= criteria.price_range[1]):
                continue
            
            filtered.append(p)
        
        # 按综合得分排序并限制数量
        filtered.sort(key=lambda x: x['comprehensive_score'], reverse=True)
        return filtered[:limit]
    
    async def get_category_analysis(self, tenant_id: str) -> List[Dict]:
        """
        获取分类分析报告
        
        Returns:
            各分类的热度和竞争分析
        """
        query = select(
            SourcingProduct.category,
            func.count(SourcingProduct.id).label('product_count'),
            func.avg(SourcingProduct.monthly_sales).label('avg_sales'),
            func.avg(SourcingProduct.cost_price).label('avg_price'),
            func.avg(SourcingProduct.rating).label('avg_rating'),
        ).where(
            and_(
                SourcingProduct.tenant_id == tenant_id,
                SourcingProduct.category.isnot(None)
            )
        ).group_by(SourcingProduct.category)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        category_stats = []
        for row in rows:
            category_stats.append({
                'category': row.category,
                'product_count': row.product_count,
                'avg_monthly_sales': round(row.avg_sales or 0, 0),
                'avg_price': round(row.avg_price or 0, 2),
                'avg_rating': round(row.avg_rating or 0, 2),
                'market_size': self._estimate_market_size(row.avg_sales, row.product_count),
            })
        
        # 按市场规模排序
        category_stats.sort(key=lambda x: x['market_size'], reverse=True)
        return category_stats
    
    def _estimate_market_size(self, avg_sales: float, product_count: int) -> int:
        """估算市场规模"""
        if not avg_sales:
            return 0
        # 简化的估算：平均销量 * 商品数 * 平均单价
        return int(avg_sales * product_count * 50)  # 假设平均单价50元
    
    async def get_price_analysis(
        self, 
        tenant_id: str,
        category: Optional[str] = None,
    ) -> Dict:
        """
        价格带分析
        
        Returns:
            各价格区间的商品分布和销售情况
        """
        query = select(SourcingProduct).where(
            SourcingProduct.tenant_id == tenant_id
        )
        
        if category:
            query = query.where(SourcingProduct.category == category)
        
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        # 定义价格区间
        price_ranges = [
            (0, 10, '0-10元'),
            (10, 30, '10-30元'),
            (30, 50, '30-50元'),
            (50, 100, '50-100元'),
            (100, 200, '100-200元'),
            (200, 500, '200-500元'),
            (500, float('inf'), '500元以上'),
        ]
        
        range_stats = []
        for min_price, max_price, label in price_ranges:
            range_products = [
                p for p in products 
                if min_price <= p.cost_price < max_price
            ]
            
            if range_products:
                avg_sales = sum(p.monthly_sales or 0 for p in range_products) / len(range_products)
                avg_rating = sum(p.rating or 0 for p in range_products) / len(range_products)
            else:
                avg_sales = 0
                avg_rating = 0
            
            range_stats.append({
                'range': label,
                'count': len(range_products),
                'avg_monthly_sales': round(avg_sales, 0),
                'avg_rating': round(avg_rating, 2),
                'percentage': round(len(range_products) / len(products) * 100, 1) if products else 0,
            })
        
        return {
            'category': category or '全部',
            'price_distribution': range_stats,
            'optimal_price_range': self._find_optimal_price_range(range_stats),
        }
    
    def _find_optimal_price_range(self, range_stats: List[Dict]) -> str:
        """找出最优价格区间"""
        # 综合考虑销量和竞争度
        best_range = None
        best_score = 0
        
        for stat in range_stats:
            if stat['count'] == 0:
                continue
            # 得分 = 销量 / 商品数（表示平均每个商品的销量）
            score = stat['avg_monthly_sales'] / (stat['count'] + 1)
            if score > best_score:
                best_score = score
                best_range = stat['range']
        
        return best_range or '暂无数据'
    
    async def update_product_scores(self, tenant_id: str):
        """
        更新数据库中商品的评分
        """
        analyzed = await self.analyze_products(tenant_id)
        
        for item in analyzed:
            product = await self.db.get(SourcingProduct, item['id'])
            if product:
                product.hot_score = item['hot_score']
                product.profit_potential = item['profit_score']
                product.competition_index = item['competition_score']
        
        await self.db.commit()
        logger.info(f"Updated scores for {len(analyzed)} products")
