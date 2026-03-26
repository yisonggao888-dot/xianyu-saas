"""
采购服务 - 拼多多/1688自动下单
"""
import asyncio
import re
import json
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from loguru import logger

from app.services.purchase_queue import PurchaseTask, PurchaseStatus


@dataclass
class PurchaseResult:
    """采购结果"""
    success: bool
    source_order_id: Optional[str] = None
    total_price: Optional[float] = None
    error_msg: Optional[str] = None
    screenshot_path: Optional[str] = None


class PDDPurchase:
    """拼多多采购"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def init_browser(self, headless: bool = True):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        self.page = await self.context.new_page()
    
    async def login(self, username: str, password: str) -> bool:
        """登录拼多多"""
        if not self.page:
            await self.init_browser(headless=False)  # 登录需要可视化
        
        try:
            await self.page.goto('https://mobile.yangkeduo.com/login.html')
            
            # 等待登录页面加载
            await self.page.wait_for_selector('.phone-login', timeout=10000)
            
            # 点击账号密码登录
            await self.page.click('.phone-login')
            
            # 输入账号密码
            await self.page.fill('input[name="username"]', username)
            await self.page.fill('input[name="password"]', password)
            
            # 点击登录
            await self.page.click('.login-button')
            
            # 等待登录成功（可能需要滑块验证）
            try:
                await self.page.wait_for_selector('.user-avatar', timeout=30000)
                logger.info("拼多多登录成功")
                return True
            except:
                logger.warning("拼多多登录可能需要人工验证")
                # 等待用户手动完成验证
                await asyncio.sleep(30)
                return True
        
        except Exception as e:
            logger.error(f"拼多多登录失败: {e}")
            return False
    
    async def purchase(self, task: PurchaseTask, cookies: Optional[str] = None) -> PurchaseResult:
        """
        执行采购
        
        流程:
        1. 打开商品页面
        2. 选择规格
        3. 立即购买
        4. 填写地址
        5. 提交订单
        6. 获取订单号
        """
        if not self.page:
            await self.init_browser()
        
        # 如果有cookies，先设置
        if cookies:
            try:
                cookies_list = json.loads(cookies)
                await self.context.add_cookies(cookies_list)
            except:
                logger.warning("Cookies解析失败")
        
        try:
            # 1. 打开商品页面
            logger.info(f"打开商品页面: {task.source_url}")
            await self.page.goto(task.source_url, wait_until='networkidle')
            await asyncio.sleep(2)
            
            # 2. 选择规格（如果有）
            if task.sku_spec:
                await self._select_sku(task.sku_spec)
            
            # 3. 点击立即购买
            buy_button = await self.page.query_selector('.buy-now, [data-testid="buy-now"], .pdd-btn-buy')
            if not buy_button:
                return PurchaseResult(
                    success=False,
                    error_msg="未找到购买按钮"
                )
            
            await buy_button.click()
            await asyncio.sleep(2)
            
            # 4. 填写地址（如果是新地址）
            await self._fill_address(
                task.buyer_name,
                task.buyer_phone,
                task.buyer_address
            )
            
            # 5. 提交订单
            submit_button = await self.page.query_selector('.submit-order, [data-testid="submit-order"]')
            if not submit_button:
                return PurchaseResult(
                    success=False,
                    error_msg="未找到提交订单按钮"
                )
            
            # 获取订单金额
            price_element = await self.page.query_selector('.total-price, .order-total')
            total_price = None
            if price_element:
                price_text = await price_element.text_content()
                price_match = re.search(r'[\d.]+', price_text)
                if price_match:
                    total_price = float(price_match.group())
            
            # 点击提交
            await submit_button.click()
            await asyncio.sleep(3)
            
            # 6. 获取订单号
            # 等待支付页面或订单详情页
            await self.page.wait_for_load_state('networkidle')
            
            # 尝试获取订单号
            order_id = await self._extract_order_id()
            
            if order_id:
                logger.info(f"拼多多下单成功: {order_id}")
                return PurchaseResult(
                    success=True,
                    source_order_id=order_id,
                    total_price=total_price
                )
            else:
                # 保存截图用于调试
                screenshot_path = f"/tmp/pdd_purchase_{task.id}.png"
                await self.page.screenshot(path=screenshot_path)
                
                return PurchaseResult(
                    success=False,
                    error_msg="未获取到订单号，可能需要人工确认",
                    screenshot_path=screenshot_path
                )
        
        except Exception as e:
            logger.error(f"拼多多采购失败: {e}")
            return PurchaseResult(
                success=False,
                error_msg=str(e)
            )
    
    async def _select_sku(self, sku_spec: str):
        """选择商品规格"""
        # TODO: 实现规格选择逻辑
        # 根据规格文本找到对应的SKU按钮并点击
        sku_buttons = await self.page.query_selector_all('.sku-item, .pdd-sku-item')
        
        for button in sku_buttons:
            text = await button.text_content()
            if sku_spec in text:
                await button.click()
                await asyncio.sleep(0.5)
                break
    
    async def _fill_address(self, name: str, phone: str, address: str):
        """填写收货地址"""
        # 检查是否需要填写地址
        address_form = await self.page.query_selector('.address-form, .new-address')
        
        if address_form:
            # 填写姓名
            await self.page.fill('input[placeholder*="姓名"], input[name="name"]', name)
            
            # 填写电话
            await self.page.fill('input[placeholder*="电话"], input[name="phone"]', phone)
            
            # 填写地址
            await self.page.fill('input[placeholder*="地址"], input[name="address"]', address)
    
    async def _extract_order_id(self) -> Optional[str]:
        """提取订单号"""
        # 尝试多种方式获取订单号
        
        # 1. 从URL获取
        url = self.page.url
        order_match = re.search(r'order[_-]?id[=/]([\w-]+)', url, re.I)
        if order_match:
            return order_match.group(1)
        
        # 2. 从页面元素获取
        selectors = [
            '.order-id',
            '.order-number',
            '[data-testid="order-id"]',
            '.pdd-order-id',
        ]
        
        for selector in selectors:
            element = await self.page.query_selector(selector)
            if element:
                text = await element.text_content()
                order_match = re.search(r'[\d\w-]{10,}', text)
                if order_match:
                    return order_match.group()
        
        return None
    
    async def get_order_status(self, order_id: str) -> Dict:
        """获取订单状态"""
        try:
            # 打开订单详情页
            await self.page.goto(f'https://mobile.yangkeduo.com/order_detail.html?order_id={order_id}')
            await asyncio.sleep(2)
            
            # 获取状态
            status_element = await self.page.query_selector('.order-status, .pdd-order-status')
            status = await status_element.text_content() if status_element else 'unknown'
            
            # 获取物流信息
            tracking_element = await self.page.query_selector('.tracking-number, .logistics-num')
            tracking_number = await tracking_element.text_content() if tracking_element else None
            
            return {
                'order_id': order_id,
                'status': status,
                'tracking_number': tracking_number,
            }
        
        except Exception as e:
            logger.error(f"获取订单状态失败: {e}")
            return {'error': str(e)}
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


class Ali1688Purchase:
    """1688采购"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def init_browser(self, headless: bool = True):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        self.page = await self.context.new_page()
    
    async def purchase(self, task: PurchaseTask, cookies: Optional[str] = None) -> PurchaseResult:
        """执行1688采购"""
        if not self.page:
            await self.init_browser()
        
        if cookies:
            try:
                cookies_list = json.loads(cookies)
                await self.context.add_cookies(cookies_list)
            except:
                pass
        
        try:
            # 1. 打开商品页面
            logger.info(f"打开1688商品页面: {task.source_url}")
            await self.page.goto(task.source_url, wait_until='networkidle')
            await asyncio.sleep(2)
            
            # 2. 选择规格
            if task.sku_spec:
                await self._select_sku(task.sku_spec)
            
            # 3. 设置数量
            quantity_input = await self.page.query_selector('.amount-input, input[name="amount"]')
            if quantity_input:
                await quantity_input.fill(str(task.quantity))
            
            # 4. 立即订购
            buy_button = await self.page.query_selector('.order-btn, .buy-now')
            if not buy_button:
                return PurchaseResult(
                    success=False,
                    error_msg="未找到订购按钮"
                )
            
            await buy_button.click()
            await asyncio.sleep(3)
            
            # 5. 确认订单页面
            # 选择或填写地址
            await self._ensure_address(
                task.buyer_name,
                task.buyer_phone,
                task.buyer_address
            )
            
            # 6. 提交订单
            submit_button = await self.page.query_selector('.submit-order, .order-submit')
            if submit_button:
                await submit_button.click()
                await asyncio.sleep(3)
            
            # 7. 获取订单号
            order_id = await self._extract_order_id()
            
            if order_id:
                logger.info(f"1688下单成功: {order_id}")
                return PurchaseResult(
                    success=True,
                    source_order_id=order_id
                )
            else:
                return PurchaseResult(
                    success=False,
                    error_msg="未获取到订单号"
                )
        
        except Exception as e:
            logger.error(f"1688采购失败: {e}")
            return PurchaseResult(
                success=False,
                error_msg=str(e)
            )
    
    async def _select_sku(self, sku_spec: str):
        """选择规格"""
        sku_items = await self.page.query_selector_all('.sku-item, .prop-item')
        
        for item in sku_items:
            text = await item.text_content()
            if sku_spec in text:
                await item.click()
                await asyncio.sleep(0.5)
                break
    
    async def _ensure_address(self, name: str, phone: str, address: str):
        """确保地址已填写"""
        # 检查是否有默认地址
        address_selected = await self.page.query_selector('.address-selected, .selected-address')
        
        if not address_selected:
            # 点击添加地址
            add_btn = await self.page.query_selector('.add-address, .new-address')
            if add_btn:
                await add_btn.click()
                await asyncio.sleep(1)
                
                # 填写地址信息
                await self.page.fill('input[placeholder*="姓名"]', name)
                await self.page.fill('input[placeholder*="手机"], input[placeholder*="电话"]', phone)
                await self.page.fill('textarea[placeholder*="地址"], input[placeholder*="地址"]', address)
                
                # 保存地址
                save_btn = await self.page.query_selector('.save-address, .confirm-btn')
                if save_btn:
                    await save_btn.click()
                    await asyncio.sleep(1)
    
    async def _extract_order_id(self) -> Optional[str]:
        """提取订单号"""
        url = self.page.url
        order_match = re.search(r'order[_-]?id[=/]([\w-]+)', url, re.I)
        if order_match:
            return order_match.group(1)
        
        # 从页面获取
        selectors = ['.order-id', '.order-number', '.order-code']
        for selector in selectors:
            element = await self.page.query_selector(selector)
            if element:
                text = await element.text_content()
                match = re.search(r'[\d\w-]{10,}', text)
                if match:
                    return match.group()
        
        return None
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


class PurchaseService:
    """采购服务"""
    
    async def purchase(self, task: PurchaseTask) -> Dict:
        """
        执行采购任务
        
        Returns:
            {
                'success': bool,
                'order_id': str,  # 源平台订单号
                'total_price': float,
                'error': str,
            }
        """
        # 根据平台选择采购器
        if task.source == 'pdd':
            purchaser = PDDPurchase()
        elif task.source == '1688':
            purchaser = Ali1688Purchase()
        else:
            return {
                'success': False,
                'error': f'不支持的平台: {task.source}'
            }
        
        try:
            # TODO: 从数据库获取平台的cookies
            cookies = None
            
            result = await purchaser.purchase(task, cookies)
            
            return {
                'success': result.success,
                'order_id': result.source_order_id,
                'total_price': result.total_price,
                'error': result.error_msg,
                'screenshot': result.screenshot_path,
            }
        
        finally:
            await purchaser.close()
