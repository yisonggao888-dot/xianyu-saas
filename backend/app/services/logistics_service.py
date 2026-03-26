"""
物流服务 - 同步货源物流信息
"""
import asyncio
import re
import json
from typing import Dict, Optional, List
from datetime import datetime

from playwright.async_api import async_playwright
from loguru import logger


class LogisticsService:
    """物流服务"""
    
    async def sync_from_source(
        self,
        source: str,
        source_order_id: str,
        cookies: Optional[str] = None
    ) -> Dict:
        """
        从货源平台同步物流信息
        
        Returns:
            {
                'success': bool,
                'tracking_number': str,
                'carrier': str,
                'status': str,
                'details': List[dict],
            }
        """
        if source == 'pdd':
            return await self._sync_pdd(source_order_id, cookies)
        elif source == '1688':
            return await self._sync_1688(source_order_id, cookies)
        else:
            return {'success': False, 'error': f'不支持的平台: {source}'}
    
    async def _sync_pdd(self, order_id: str, cookies: Optional[str]) -> Dict:
        """同步拼多多物流"""
        playwright = await async_playwright().start()
        
        try:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080},
            )
            
            # 设置cookies
            if cookies:
                try:
                    cookies_list = json.loads(cookies)
                    await context.add_cookies(cookies_list)
                except:
                    pass
            
            page = await context.new_page()
            
            # 打开订单详情
            await page.goto(f'https://mobile.yangkeduo.com/order_detail.html?order_id={order_id}')
            await asyncio.sleep(2)
            
            # 获取物流信息
            logistics_info = await self._extract_pdd_logistics(page)
            
            await browser.close()
            
            return {
                'success': True,
                **logistics_info
            }
        
        except Exception as e:
            logger.error(f"同步拼多多物流失败: {e}")
            return {'success': False, 'error': str(e)}
        
        finally:
            await playwright.stop()
    
    async def _extract_pdd_logistics(self, page) -> Dict:
        """提取拼多多物流信息"""
        result = {
            'tracking_number': None,
            'carrier': None,
            'status': 'unknown',
            'details': [],
        }
        
        try:
            # 获取物流状态
            status_selectors = [
                '.logistics-status',
                '.delivery-status',
                '.order-status',
            ]
            
            for selector in status_selectors:
                element = await page.query_selector(selector)
                if element:
                    result['status'] = await element.text_content()
                    break
            
            # 获取快递单号
            tracking_selectors = [
                '.tracking-number',
                '.logistics-num',
                '.express-no',
            ]
            
            for selector in tracking_selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    match = re.search(r'[\dA-Z]{10,}', text)
                    if match:
                        result['tracking_number'] = match.group()
                        break
            
            # 获取快递公司
            carrier_selectors = [
                '.carrier-name',
                '.express-company',
                '.logistics-company',
            ]
            
            for selector in carrier_selectors:
                element = await page.query_selector(selector)
                if element:
                    result['carrier'] = await element.text_content()
                    break
            
            # 获取物流详情
            detail_selectors = [
                '.logistics-item',
                '.tracking-item',
                '.express-detail',
            ]
            
            for selector in detail_selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items:
                        time_elem = await item.query_selector('.time, .date')
                        content_elem = await item.query_selector('.content, .desc')
                        
                        if time_elem and content_elem:
                            result['details'].append({
                                'time': await time_elem.text_content(),
                                'content': await content_elem.text_content(),
                            })
                    break
        
        except Exception as e:
            logger.error(f"提取物流信息失败: {e}")
        
        return result
    
    async def _sync_1688(self, order_id: str, cookies: Optional[str]) -> Dict:
        """同步1688物流"""
        playwright = await async_playwright().start()
        
        try:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            )
            
            if cookies:
                try:
                    cookies_list = json.loads(cookies)
                    await context.add_cookies(cookies_list)
                except:
                    pass
            
            page = await context.new_page()
            
            # 打开订单详情
            await page.goto(f'https://trade.1688.com/order/order_detail.htm?orderId={order_id}')
            await asyncio.sleep(2)
            
            # 获取物流信息
            logistics_info = await self._extract_1688_logistics(page)
            
            await browser.close()
            
            return {
                'success': True,
                **logistics_info
            }
        
        except Exception as e:
            logger.error(f"同步1688物流失败: {e}")
            return {'success': False, 'error': str(e)}
        
        finally:
            await playwright.stop()
    
    async def _extract_1688_logistics(self, page) -> Dict:
        """提取1688物流信息"""
        result = {
            'tracking_number': None,
            'carrier': None,
            'status': 'unknown',
            'details': [],
        }
        
        try:
            # 获取物流状态
            status_elem = await page.query_selector('.order-status, .logistics-status')
            if status_elem:
                result['status'] = await status_elem.text_content()
            
            # 获取快递单号
            tracking_elem = await page.query_selector('.tracking-no, .logistics-number')
            if tracking_elem:
                text = await tracking_elem.text_content()
                match = re.search(r'[\dA-Z]{10,}', text)
                if match:
                    result['tracking_number'] = match.group()
            
            # 获取快递公司
            carrier_elem = await page.query_selector('.carrier, .express-company')
            if carrier_elem:
                result['carrier'] = await carrier_elem.text_content()
            
            # 获取物流详情
            detail_items = await page.query_selector_all('.logistics-detail-item')
            for item in detail_items:
                time_elem = await item.query_selector('.time')
                content_elem = await item.query_selector('.content')
                
                if time_elem and content_elem:
                    result['details'].append({
                        'time': await time_elem.text_content(),
                        'content': await content_elem.text_content(),
                    })
        
        except Exception as e:
            logger.error(f"提取1688物流信息失败: {e}")
        
        return result
    
    async def fill_to_xianyu(
        self,
        xianyu_order_id: str,
        tracking_number: str,
        carrier: str,
        cookies: str
    ) -> bool:
        """
        回填物流单号到闲鱼
        
        TODO: 实现闲鱼发货逻辑
        """
        logger.info(f"回填物流到闲鱼: {xianyu_order_id}, {tracking_number}, {carrier}")
        
        # TODO: 使用Playwright登录闲鱼，找到订单，填写物流信息
        # 1. 登录闲鱼
        # 2. 打开订单详情
        # 3. 点击发货
        # 4. 填写物流公司和单号
        # 5. 确认发货
        
        return True
    
    def get_carrier_code(self, carrier_name: str) -> str:
        """
        获取快递公司编码
        
        拼多多/1688的快递公司名称 -> 闲鱼的快递公司编码
        """
        carrier_map = {
            '顺丰': 'sf',
            '顺丰速运': 'sf',
            '中通': 'zt',
            '中通快递': 'zt',
            '圆通': 'yt',
            '圆通速递': 'yt',
            '韵达': 'yd',
            '韵达快递': 'yd',
            '申通': 'st',
            '申通快递': 'st',
            '百世': 'bs',
            '百世快递': 'bs',
            'EMS': 'ems',
            '邮政EMS': 'ems',
            '京东': 'jd',
            '京东物流': 'jd',
            '德邦': 'db',
            '德邦快递': 'db',
        }
        
        for key, code in carrier_map.items():
            if key in carrier_name:
                return code
        
        return 'other'


class AutoSyncTask:
    """自动同步任务"""
    
    def __init__(self):
        self.running = False
        self.interval = 300  # 5分钟
    
    async def start(self):
        """启动自动同步"""
        self.running = True
        
        while self.running:
            try:
                await self._sync_all()
            except Exception as e:
                logger.error(f"自动同步异常: {e}")
            
            await asyncio.sleep(self.interval)
    
    async def _sync_all(self):
        """同步所有待发货订单"""
        # TODO: 从数据库查询所有已采购但未发货的订单
        # 逐个同步物流信息
        # 如果已发货，自动回填到闲鱼
        pass
    
    def stop(self):
        """停止同步"""
        self.running = False
