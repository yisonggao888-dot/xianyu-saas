"""
商品爬虫服务 - 拼多多/1688数据采集
注：由于平台反爬机制，当前使用演示数据模式
"""
import re
import json
import urllib.parse
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from loguru import logger


@dataclass
class ProductItem:
    """商品数据模型"""
    source: str  # pdd / 1688
    source_id: str
    title: str
    price: float
    original_price: Optional[float]
    main_image: str
    images: List[str]
    sales_count: int
    shop_name: str
    shop_rating: float
    detail_url: str
    category: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


class PDDScraper:
    """拼多多爬虫"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            },
            timeout=30.0
        )
    
    def _generate_demo_data(self, keyword: str) -> List[ProductItem]:
        """生成拼多多演示数据"""
        titles = [
            f"{keyword} 正品官方旗舰店 限时特价",
            f"{keyword} 网红同款 热销爆款",
            f"{keyword} 工厂直销 品质保证",
            f"{keyword} 新款上市 买一送一",
            f"{keyword} 品牌特价 万人团购",
            f"{keyword} 学生党必备 超实惠",
            f"{keyword} 家用必备 耐用款",
            f"{keyword} 明星同款 火爆全网",
            f"{keyword} 原装正品 售后无忧",
            f"{keyword} 限时秒杀 手慢无"
        ]
        
        shops = ["百亿补贴旗舰店", "品牌直营店", "官方授权店", "优品专营店", "精选好物店",
                 "天天特价店", "品质生活馆", "爆款集中营", "网红同款店", "工厂直营店"]
        
        products = []
        for i in range(10):
            base_price = 9.9 + (i * 8.5)
            products.append(ProductItem(
                source='pdd',
                source_id=f'pdd_{abs(hash(keyword + str(i))) % 100000000}',
                title=titles[i],
                price=round(base_price, 2),
                original_price=round(base_price * 2.5, 2),
                main_image=f'https://picsum.photos/seed/pdd{i}{abs(hash(keyword)) % 1000}/300/300',
                images=[f'https://picsum.photos/seed/pdd{i}{abs(hash(keyword)) % 1000}/300/300'],
                sales_count=5000 + (i * 1200),
                shop_name=shops[i],
                shop_rating=round(4.0 + (i % 10) * 0.08, 1),
                detail_url=f'https://mobile.yangkeduo.com/goods.html?goods_id={abs(hash(keyword + str(i))) % 100000000}',
                category=keyword,
            ))
        return products
    
    async def search(
        self,
        keyword: str,
        page: int = 1,
        sort: str = "default",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
    ) -> List[ProductItem]:
        """搜索商品（演示模式）"""
        keyword = str(keyword).strip()
        logger.info(f"PDD搜索: {keyword}")
        
        # 返回演示数据
        products = self._generate_demo_data(keyword)
        
        # 价格筛选
        if min_price is not None:
            products = [p for p in products if p.price >= min_price]
        if max_price is not None:
            products = [p for p in products if p.price <= max_price]
        
        logger.info(f"PDD返回 {len(products)} 条演示数据")
        return products
    
    async def close(self):
        await self.client.aclose()


class Ali1688Scraper:
    """1688爬虫"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            },
            timeout=30.0
        )
    
    def _generate_demo_data(self, keyword: str) -> List[ProductItem]:
        """生成1688演示数据"""
        titles = [
            f"{keyword} 厂家直销 一件代发",
            f"{keyword} 批发定制 量大从优",
            f"{keyword} 源头工厂 品质保障",
            f"{keyword} 现货批发 快速发货",
            f"{keyword} 跨境电商专供",
            f"{keyword} 1688严选 品质好货",
            f"{keyword} 实力工厂 OEM定制",
            f"{keyword} 阿里巴巴认证供应商",
            f"{keyword} 批发价 零售品质",
            f"{keyword} 新品上市 抢先订购"
        ]
        
        shops = ["源头实力工厂", "阿里巴巴认证", "金牌供应商", "品质工厂店", "批发专营店",
                 "OEM定制厂", "跨境电商基地", "1688严选店", "工厂直营店", "批发总部"]
        
        products = []
        for i in range(10):
            base_price = 5.5 + (i * 3.2)
            products.append(ProductItem(
                source='1688',
                source_id=f'1688_{abs(hash(keyword + str(i))) % 100000000}',
                title=titles[i],
                price=round(base_price, 2),
                original_price=None,
                main_image=f'https://picsum.photos/seed/1688{i}{abs(hash(keyword)) % 1000}/300/300',
                images=[f'https://picsum.photos/seed/1688{i}{abs(hash(keyword)) % 1000}/300/300'],
                sales_count=3000 + (i * 800),
                shop_name=shops[i],
                shop_rating=round(4.2 + (i % 8) * 0.09, 1),
                detail_url=f'https://detail.1688.com/offer/{abs(hash(keyword + str(i))) % 100000000}.html',
                category=keyword,
            ))
        return products
    
    async def search(
        self,
        keyword: str,
        page: int = 1,
        sort: str = "default",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
    ) -> List[ProductItem]:
        """搜索商品（演示模式）"""
        keyword = str(keyword).strip()
        logger.info(f"1688搜索: {keyword}")
        
        # 返回演示数据
        products = self._generate_demo_data(keyword)
        
        # 价格筛选
        if min_price is not None:
            products = [p for p in products if p.price >= min_price]
        if max_price is not None:
            products = [p for p in products if p.price <= max_price]
        
        logger.info(f"1688返回 {len(products)} 条演示数据")
        return products
    
    async def close(self):
        await self.client.aclose()


class ProductScraper:
    """统一商品抓取器"""
    
    def __init__(self):
        self.pdd_scraper = PDDScraper()
        self.ali1688_scraper = Ali1688Scraper()
    
    async def search_all(
        self,
        keyword: str,
        sources: List[str] = None,
        **kwargs
    ) -> Dict[str, List[ProductItem]]:
        """
        多平台搜索
        
        Returns:
            {'pdd': [...], '1688': [...]}
        """
        sources = sources or ['pdd', '1688']
        results = {}
        
        if 'pdd' in sources:
            try:
                results['pdd'] = await self.pdd_scraper.search(keyword, **kwargs)
            except Exception as e:
                logger.error(f"PDD搜索失败: {e}")
                results['pdd'] = []
        
        if '1688' in sources:
            try:
                results['1688'] = await self.ali1688_scraper.search(keyword, **kwargs)
            except Exception as e:
                logger.error(f"1688搜索失败: {e}")
                results['1688'] = []
        
        return results
    
    async def close(self):
        await self.pdd_scraper.close()
        await self.ali1688_scraper.close()
