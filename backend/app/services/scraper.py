"""
拼多多/1688 商品爬虫
"""
import asyncio
import re
import json
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime

import httpx
from playwright.async_api import async_playwright, Page
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
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class PDDScraper:
    """拼多多爬虫"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://mobile.yangkeduo.com/',
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)
    
    async def search(
        self,
        keyword: str,
        page: int = 1,
        sort: str = "default",  # default, price_asc, price_desc, sales
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
    ) -> List[ProductItem]:
        """搜索商品"""
        try:
            # 拼多多搜索API
            url = 'https://mobile.yangkeduo.com/proxy/api/search'
            params = {
                'page': page,
                'size': 20,
                'q': keyword,
                'sort': self._get_sort_type(sort),
                'requery': '0',
            }
            
            if min_price:
                params['filter'] = f"price,{min_price},{max_price or 999999}"
            
            response = await self.client.get(url, params=params)
            data = response.json()
            
            items = data.get('items', [])
            products = []
            
            for item in items:
                try:
                    product = ProductItem(
                        source='pdd',
                        source_id=str(item.get('goods_id', '')),
                        title=item.get('goods_name', ''),
                        price=float(item.get('min_on_sale_group_price', 0)) / 100,
                        original_price=float(item.get('min_group_price', 0)) / 100 if item.get('min_group_price') else None,
                        main_image=item.get('thumb_url', ''),
                        images=[item.get('thumb_url', '')],
                        sales_count=self._parse_sales(item.get('sales', '0')),
                        shop_name=item.get('mall_name', ''),
                        shop_rating=float(item.get('mall_cps', 0)) / 100,
                        detail_url=f"https://mobile.yangkeduo.com/goods.html?goods_id={item.get('goods_id')}",
                        category=item.get('opt_name'),
                    )
                    products.append(product)
                except Exception as e:
                    logger.error(f"解析商品失败: {e}")
                    continue
            
            logger.info(f"拼多多搜索 '{keyword}' 返回 {len(products)} 条结果")
            return products
            
        except Exception as e:
            logger.error(f"拼多多搜索失败: {e}")
            return []
    
    def _get_sort_type(self, sort: str) -> str:
        """排序类型映射"""
        sort_map = {
            'default': '0',
            'price_asc': '2',
            'price_desc': '3',
            'sales': '6',
        }
        return sort_map.get(sort, '0')
    
    def _parse_sales(self, sales_str: str) -> int:
        """解析销量"""
        if not sales_str:
            return 0
        
        # 处理 "已拼1.2万件" 格式
        match = re.search(r'[\d.]+', sales_str)
        if not match:
            return 0
        
        num = float(match.group())
        
        if '万' in sales_str:
            return int(num * 10000)
        elif '千' in sales_str:
            return int(num * 1000)
        else:
            return int(num)
    
    async def get_detail(self, goods_id: str) -> Optional[ProductItem]:
        """获取商品详情"""
        # TODO: 使用Playwright获取详情
        pass
    
    async def close(self):
        await self.client.aclose()


class Ali1688Scraper:
    """1688爬虫"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://s.1688.com/',
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)
    
    async def search(
        self,
        keyword: str,
        page: int = 1,
        sort: str = "default",
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
    ) -> List[ProductItem]:
        """搜索商品"""
        try:
            url = 'https://s.1688.com/selloffer/offer_search.htm'
            params = {
                'keywords': keyword,
                'n': 'y',
                'netType': '1',
                'beginPage': page,
                'pageSize': '60',
            }
            
            response = await self.client.get(url, params=params)
            html = response.text
            
            # 解析数据
            products = self._parse_search_result(html, keyword)
            
            logger.info(f"1688搜索 '{keyword}' 返回 {len(products)} 条结果")
            return products
            
        except Exception as e:
            logger.error(f"1688搜索失败: {e}")
            return []
    
    def _parse_search_result(self, html: str, keyword: str) -> List[ProductItem]:
        """解析搜索结果"""
        products = []
        
        try:
            # 尝试从JSON数据中提取
            # 1688的数据通常在 window.__INITIAL_STATE__ 或 iDetailData 中
            json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html)
            
            if json_match:
                data = json.loads(json_match.group(1))
                offers = data.get('data', {}).get('data', {}).get('offerList', [])
                
                for offer in offers:
                    try:
                        product = ProductItem(
                            source='1688',
                            source_id=str(offer.get('id', '')),
                            title=offer.get('title', ''),
                            price=float(offer.get('price', 0)),
                            original_price=None,
                            main_image=offer.get('imageUrl', ''),
                            images=[offer.get('imageUrl', '')],
                            sales_count=offer.get('saleQuantity', 0),
                            shop_name=offer.get('company', {}).get('name', ''),
                            shop_rating=0.0,
                            detail_url=offer.get('detailUrl', ''),
                            category=keyword,
                        )
                        products.append(product)
                    except Exception as e:
                        logger.error(f"解析1688商品失败: {e}")
                        continue
            
            # 如果JSON解析失败，使用正则提取
            if not products:
                products = self._parse_with_regex(html, keyword)
                
        except Exception as e:
            logger.error(f"解析1688搜索结果失败: {e}")
        
        return products
    
    def _parse_with_regex(self, html: str, keyword: str) -> List[ProductItem]:
        """使用正则解析商品"""
        products = []
        
        # 查找商品卡片
        # 这是一个简化的示例，实际1688的HTML结构复杂
        item_pattern = r'data-offer-id="(\d+)"[^>]*>[\s\S]*?<img[^>]*src="([^"]+)"[^>]*>[\s\S]*?<a[^>]*>([^<]+)</a>[\s\S]*?<span[^>]*>¥([\d.]+)</span>'
        
        for match in re.finditer(item_pattern, html):
            try:
                product = ProductItem(
                    source='1688',
                    source_id=match.group(1),
                    title=match.group(3).strip(),
                    price=float(match.group(4)),
                    original_price=None,
                    main_image=match.group(2),
                    images=[match.group(2)],
                    sales_count=0,
                    shop_name='',
                    shop_rating=0.0,
                    detail_url=f"https://detail.1688.com/offer/{match.group(1)}.html",
                    category=keyword,
                )
                products.append(product)
            except Exception:
                continue
        
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
        sources: List[str] = None,  # ['pdd', '1688']
        **kwargs
    ) -> Dict[str, List[ProductItem]]:
        """
        多平台搜索
        
        Returns:
            {'pdd': [...], '1688': [...]}
        """
        sources = sources or ['pdd', '1688']
        results = {}
        
        tasks = []
        
        if 'pdd' in sources:
            tasks.append(('pdd', self.pdd_scraper.search(keyword, **kwargs)))
        
        if '1688' in sources:
            tasks.append(('1688', self.ali1688_scraper.search(keyword, **kwargs)))
        
        for source, task in tasks:
            try:
                results[source] = await task
            except Exception as e:
                logger.error(f"{source}搜索失败: {e}")
                results[source] = []
        
        return results
    
    async def close(self):
        await self.pdd_scraper.close()
        await self.ali1688_scraper.close()


class PlaywrightScraper:
    """
    Playwright爬虫（用于需要JS渲染的页面）
    """
    
    def __init__(self):
        self.browser = None
        self.context = None
    
    async def init(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
    
    async def get_product_detail(self, url: str) -> Optional[Dict]:
        """获取商品详情页数据"""
        if not self.context:
            await self.init()
        
        page = await self.context.new_page()
        
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待页面加载
            await page.wait_for_load_state('networkidle')
            
            # 获取页面内容
            content = await page.content()
            
            # TODO: 根据URL判断平台，解析详情
            if 'pinduoduo' in url or 'yangkeduo' in url:
                return await self._parse_pdd_detail(page, content)
            elif '1688' in url:
                return await self._parse_1688_detail(page, content)
            
            return None
            
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return None
        finally:
            await page.close()
    
    async def _parse_pdd_detail(self, page: Page, content: str) -> Dict:
        """解析拼多多详情"""
        # 提取商品信息
        title = await page.locator('[data-testid="pdd-modal-goods-title"]').first.text_content()
        price = await page.locator('[data-testid="pdd-modal-goods-price"]').first.text_content()
        
        return {
            'title': title,
            'price': price,
            'raw_content': content[:5000],  # 限制大小
        }
    
    async def _parse_1688_detail(self, page: Page, content: str) -> Dict:
        """解析1688详情"""
        title = await page.locator('.offer-title').first.text_content()
        price = await page.locator('.price-now').first.text_content()
        
        return {
            'title': title,
            'price': price,
            'raw_content': content[:5000],
        }
    
    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
