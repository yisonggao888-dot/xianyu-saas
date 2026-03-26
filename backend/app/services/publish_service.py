"""
发布服务 - 一键发布选品到闲鱼
"""
import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime

from playwright.async_api import async_playwright, Page
from loguru import logger


class XianyuPublisher:
    """闲鱼发布器"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
    
    async def init_browser(self, headless: bool = True):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            viewport={'width': 375, 'height': 812},
        )
        self.page = await self.context.new_page()
    
    async def publish(
        self,
        title: str,
        description: str,
        price: float,
        images: List[str],
        category: Optional[str] = None,
        location: str = '北京',
        cookies: Optional[str] = None,
    ) -> Dict:
        """
        发布商品到闲鱼
        
        Args:
            title: 商品标题
            description: 商品描述
            price: 售价
            images: 图片URL列表
            category: 分类
            location: 发货地
            cookies: 登录cookies
        
        Returns:
            {
                'success': bool,
                'item_id': str,
                'url': str,
                'error': str,
            }
        """
        if not self.page:
            await self.init_browser(headless=False)  # 发布需要可视化
        
        # 设置cookies
        if cookies:
            try:
                cookies_list = json.loads(cookies)
                await self.context.add_cookies(cookies_list)
            except:
                logger.warning("Cookies解析失败")
        
        try:
            # 1. 打开发布页面
            logger.info("打开发布页面")
            await self.page.goto('https://www.goofish.com/publish')
            await asyncio.sleep(3)
            
            # 2. 上传图片
            logger.info(f"上传 {len(images)} 张图片")
            await self._upload_images(images)
            
            # 3. 填写标题
            logger.info("填写标题")
            await self._fill_title(title)
            
            # 4. 填写描述
            logger.info("填写描述")
            await self._fill_description(description)
            
            # 5. 设置价格
            logger.info("设置价格")
            await self._set_price(price)
            
            # 6. 选择分类
            if category:
                logger.info("选择分类")
                await self._select_category(category)
            
            # 7. 设置发货地
            logger.info("设置发货地")
            await self._set_location(location)
            
            # 8. 点击发布
            logger.info("点击发布")
            result = await self._submit()
            
            return result
        
        except Exception as e:
            logger.error(f"发布失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _upload_images(self, images: List[str]):
        """上传图片"""
        # 等待上传按钮
        upload_input = await self.page.wait_for_selector('input[type="file"]', timeout=10000)
        
        # 下载并上传图片（最多9张）
        for i, image_url in enumerate(images[:9]):
            try:
                # 下载图片到临时文件
                import httpx
                import tempfile
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url)
                    
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                        f.write(response.content)
                        temp_path = f.name
                
                # 上传
                await upload_input.set_input_files(temp_path)
                await asyncio.sleep(1)
                
                # 删除临时文件
                import os
                os.unlink(temp_path)
                
            except Exception as e:
                logger.error(f"上传图片失败: {e}")
    
    async def _fill_title(self, title: str):
        """填写标题"""
        # 找到标题输入框
        title_input = await self.page.wait_for_selector(
            'input[placeholder*="标题"], textarea[placeholder*="标题"], .title-input',
            timeout=5000
        )
        
        # 限制30字
        title = title[:30]
        
        await title_input.fill(title)
        await asyncio.sleep(0.5)
    
    async def _fill_description(self, description: str):
        """填写描述"""
        desc_input = await self.page.wait_for_selector(
            'textarea[placeholder*="描述"], .desc-input, .description-input',
            timeout=5000
        )
        
        await desc_input.fill(description)
        await asyncio.sleep(0.5)
    
    async def _set_price(self, price: float):
        """设置价格"""
        price_input = await self.page.wait_for_selector(
            'input[placeholder*="价格"], input[name="price"], .price-input',
            timeout=5000
        )
        
        await price_input.fill(str(price))
        await asyncio.sleep(0.5)
    
    async def _select_category(self, category: str):
        """选择分类"""
        try:
            # 点击分类选择
            category_btn = await self.page.query_selector('.category-selector, .category-btn')
            if category_btn:
                await category_btn.click()
                await asyncio.sleep(1)
                
                # 搜索分类
                search_input = await self.page.query_selector('.category-search, input[placeholder*="分类"]')
                if search_input:
                    await search_input.fill(category)
                    await asyncio.sleep(1)
                    
                    # 选择第一个结果
                    result = await self.page.query_selector('.category-item, .category-result')
                    if result:
                        await result.click()
                        await asyncio.sleep(0.5)
        
        except Exception as e:
            logger.warning(f"选择分类失败: {e}")
    
    async def _set_location(self, location: str):
        """设置发货地"""
        try:
            location_btn = await self.page.query_selector('.location-selector, .location-btn')
            if location_btn:
                await location_btn.click()
                await asyncio.sleep(1)
                
                # 搜索城市
                search_input = await self.page.query_selector('.location-search')
                if search_input:
                    await search_input.fill(location)
                    await asyncio.sleep(1)
                    
                    # 选择
                    result = await self.page.query_selector('.location-item')
                    if result:
                        await result.click()
        
        except Exception as e:
            logger.warning(f"设置发货地失败: {e}")
    
    async def _submit(self) -> Dict:
        """提交发布"""
        submit_btn = await self.page.wait_for_selector(
            '.submit-btn, .publish-btn, button:has-text("发布")',
            timeout=5000
        )
        
        await submit_btn.click()
        
        # 等待发布结果
        await asyncio.sleep(3)
        
        # 获取商品ID
        url = self.page.url
        
        # 检查是否发布成功
        if '/item/' in url or 'itemId=' in url:
            # 提取商品ID
            import re
            item_match = re.search(r'item[/=]([\w-]+)', url)
            item_id = item_match.group(1) if item_match else None
            
            return {
                'success': True,
                'item_id': item_id,
                'url': url,
            }
        else:
            # 检查错误信息
            error_elem = await self.page.query_selector('.error-msg, .toast, .error-message')
            error_msg = await error_elem.text_content() if error_elem else '发布失败'
            
            return {
                'success': False,
                'error': error_msg,
            }
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


class PublishService:
    """发布服务"""
    
    async def publish_product(
        self,
        product_id: str,
        account_id: str,
        sale_price: Optional[float] = None,
        db = None,
    ) -> Dict:
        """
        发布商品
        
        Args:
            product_id: 选品ID
            account_id: 闲鱼账号ID
            sale_price: 自定义售价
        
        Returns:
            {
                'success': bool,
                'item_id': str,
                'url': str,
                'error': str,
            }
        """
        # TODO: 从数据库获取商品信息和账号cookies
        
        publisher = XianyuPublisher()
        
        try:
            # 示例调用
            result = await publisher.publish(
                title="示例商品",
                description="这是商品描述",
                price=sale_price or 99.0,
                images=["https://example.com/image.jpg"],
            )
            
            if result['success']:
                # TODO: 更新数据库，记录已发布
                logger.info(f"发布成功: {result['item_id']}")
            
            return result
        
        finally:
            await publisher.close()
    
    async def batch_publish(
        self,
        product_ids: List[str],
        account_id: str,
        interval: int = 60,
    ) -> List[Dict]:
        """
        批量发布
        
        Args:
            product_ids: 商品ID列表
            account_id: 账号ID
            interval: 发布间隔(秒)
        
        Returns:
            发布结果列表
        """
        results = []
        
        for product_id in product_ids:
            result = await self.publish_product(product_id, account_id)
            results.append(result)
            
            if not result['success']:
                logger.error(f"发布失败: {product_id} - {result.get('error')}")
            
            # 间隔等待
            await asyncio.sleep(interval)
        
        return results
