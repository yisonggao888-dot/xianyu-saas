"""
图片处理服务 - 水印、压缩、去重、格式转换
"""
import io
import os
import hashlib
import base64
from typing import List, Optional, Tuple, BinaryIO
from dataclasses import dataclass
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import httpx
from loguru import logger


class WatermarkPosition(str, Enum):
    """水印位置"""
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"
    TILE = "tile"  # 平铺


@dataclass
class WatermarkConfig:
    """水印配置"""
    text: str = "闲鱼优品"  # 水印文字
    font_size: int = 24
    color: Tuple[int, int, int, int] = (255, 255, 255, 128)  # RGBA
    position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT
    opacity: float = 0.5  # 透明度
    angle: int = 0  # 旋转角度


@dataclass
class CompressConfig:
    """压缩配置"""
    quality: int = 85  # JPEG质量
    max_width: Optional[int] = 1200  # 最大宽度
    max_height: Optional[int] = 1200  # 最大高度
    format: str = "JPEG"  # 输出格式


@dataclass
class ProcessResult:
    """处理结果"""
    success: bool
    data: Optional[bytes] = None
    format: Optional[str] = None
    size: Optional[int] = None  # 处理后大小
    original_size: Optional[int] = None  # 原始大小
    error_message: Optional[str] = None
    hash: Optional[str] = None  # 图片指纹


class ImageProcessor:
    """
    图片处理器
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._font_cache = {}
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """下载图片"""
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Download failed: {url}, status: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Download error: {url}, error: {e}")
            return None
    
    async def process_from_url(
        self,
        url: str,
        watermark: Optional[WatermarkConfig] = None,
        compress: Optional[CompressConfig] = None,
    ) -> ProcessResult:
        """
        从URL下载并处理图片
        """
        # 下载图片
        image_data = await self.download_image(url)
        if not image_data:
            return ProcessResult(success=False, error_message="下载图片失败")
        
        return await self.process_image(image_data, watermark, compress)
    
    async def process_image(
        self,
        image_data: bytes,
        watermark: Optional[WatermarkConfig] = None,
        compress: Optional[CompressConfig] = None,
    ) -> ProcessResult:
        """
        处理图片（添加水印、压缩）
        """
        try:
            original_size = len(image_data)
            
            # 在线程池中处理图片（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._process_image_sync,
                image_data,
                watermark,
                compress,
            )
            
            if result.success:
                result.original_size = original_size
                result.hash = self._calc_image_hash(result.data)
            
            return result
            
        except Exception as e:
            logger.error(f"Process image error: {e}")
            return ProcessResult(success=False, error_message=str(e))
    
    def _process_image_sync(
        self,
        image_data: bytes,
        watermark: Optional[WatermarkConfig],
        compress: Optional[CompressConfig],
    ) -> ProcessResult:
        """同步处理图片（在线程池中运行）"""
        try:
            # 打开图片
            img = Image.open(io.BytesIO(image_data))
            
            # 转换为RGB模式（处理PNG等透明图片）
            if img.mode in ('RGBA', 'P'):
                # 透明背景转白色
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 压缩处理
            if compress:
                img = self._resize_image(img, compress)
            
            # 添加水印
            if watermark:
                img = self._add_watermark(img, watermark)
            
            # 保存为字节
            output_format = compress.format if compress else 'JPEG'
            output = io.BytesIO()
            
            save_kwargs = {'format': output_format}
            if output_format == 'JPEG':
                save_kwargs['quality'] = compress.quality if compress else 85
                save_kwargs['optimize'] = True
            elif output_format == 'PNG':
                save_kwargs['optimize'] = True
            
            img.save(output, **save_kwargs)
            processed_data = output.getvalue()
            
            return ProcessResult(
                success=True,
                data=processed_data,
                format=output_format,
                size=len(processed_data),
            )
            
        except Exception as e:
            logger.error(f"Process image sync error: {e}")
            return ProcessResult(success=False, error_message=str(e))
    
    def _resize_image(self, img: Image.Image, config: CompressConfig) -> Image.Image:
        """调整图片尺寸"""
        width, height = img.size
        
        # 计算缩放比例
        scale = 1.0
        if config.max_width and width > config.max_width:
            scale = min(scale, config.max_width / width)
        if config.max_height and height > config.max_height:
            scale = min(scale, config.max_height / height)
        
        if scale < 1.0:
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return img
    
    def _add_watermark(
        self, 
        img: Image.Image, 
        config: WatermarkConfig
    ) -> Image.Image:
        """添加水印"""
        # 创建透明图层
        watermark_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark_layer)
        
        # 获取字体
        font = self._get_font(config.font_size)
        
        # 计算文字尺寸
        bbox = draw.textbbox((0, 0), config.text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 计算位置
        img_width, img_height = img.size
        padding = 20
        
        if config.position == WatermarkPosition.TOP_LEFT:
            x, y = padding, padding
        elif config.position == WatermarkPosition.TOP_RIGHT:
            x, y = img_width - text_width - padding, padding
        elif config.position == WatermarkPosition.BOTTOM_LEFT:
            x, y = padding, img_height - text_height - padding
        elif config.position == WatermarkPosition.BOTTOM_RIGHT:
            x, y = img_width - text_width - padding, img_height - text_height - padding
        elif config.position == WatermarkPosition.CENTER:
            x, y = (img_width - text_width) // 2, (img_height - text_height) // 2
        elif config.position == WatermarkPosition.TILE:
            # 平铺模式
            return self._add_tile_watermark(img, config)
        else:
            x, y = img_width - text_width - padding, img_height - text_height - padding
        
        # 绘制文字
        draw.text((x, y), config.text, font=font, fill=config.color)
        
        # 旋转
        if config.angle:
            watermark_layer = watermark_layer.rotate(
                config.angle, 
                expand=False,
                fillcolor=(255, 255, 255, 0)
            )
        
        # 调整透明度
        alpha = watermark_layer.split()[-1]
        alpha = alpha.point(lambda p: int(p * config.opacity))
        watermark_layer.putalpha(alpha)
        
        # 合并图层
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, watermark_layer)
        
        return img.convert('RGB')
    
    def _add_tile_watermark(
        self, 
        img: Image.Image, 
        config: WatermarkConfig
    ) -> Image.Image:
        """添加平铺水印"""
        # 创建一个小水印图案
        font = self._get_font(config.font_size)
        temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1), (0, 0, 0, 0)))
        bbox = temp_draw.textbbox((0, 0), config.text, font=font)
        text_width = bbox[2] - bbox[0] + 40  # 间距
        text_height = bbox[3] - bbox[1] + 40
        
        # 创建图案
        pattern = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(pattern)
        draw.text((20, 20), config.text, font=font, fill=config.color)
        
        # 旋转图案
        pattern = pattern.rotate(config.angle, expand=True, fillcolor=(255, 255, 255, 0))
        
        # 平铺
        img = img.convert('RGBA')
        pattern_width, pattern_height = pattern.size
        
        for y in range(0, img.height, pattern_height):
            for x in range(0, img.width, pattern_width):
                img.paste(pattern, (x, y), pattern)
        
        return img.convert('RGB')
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """获取字体（带缓存）"""
        cache_key = f"default_{size}"
        if cache_key not in self._font_cache:
            # 尝试常见字体路径
            font_paths = [
                "C:/Windows/Fonts/simhei.ttf",  # 黑体
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Linux
                "/System/Library/Fonts/PingFang.ttc",  # macOS
            ]
            
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    try:
                        font = ImageFont.truetype(path, size)
                        break
                    except:
                        continue
            
            if font is None:
                font = ImageFont.load_default()
            
            self._font_cache[cache_key] = font
        
        return self._font_cache[cache_key]
    
    def _calc_image_hash(self, image_data: bytes) -> str:
        """计算图片指纹（用于去重）"""
        return hashlib.md5(image_data).hexdigest()[:16]
    
    async def calc_perceptual_hash(self, image_data: bytes) -> Optional[str]:
        """
        计算感知哈希（pHash）- 用于相似图片检测
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self._calc_phash_sync,
                image_data
            )
        except Exception as e:
            logger.error(f"Calc phash error: {e}")
            return None
    
    def _calc_phash_sync(self, image_data: bytes) -> str:
        """同步计算感知哈希"""
        img = Image.open(io.BytesIO(image_data))
        img = img.convert('L')  # 转为灰度
        img = img.resize((32, 32), Image.Resampling.LANCZOS)
        
        # 计算DCT（简化版，使用平均值代替）
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        
        # 生成哈希
        hash_bits = ''.join('1' if p >= avg else '0' for p in pixels[:64])
        return hex(int(hash_bits, 2))[2:].zfill(16)
    
    def calc_hash_similarity(self, hash1: str, hash2: str) -> float:
        """
        计算两个哈希的相似度
        
        Returns:
            相似度 (0-1)，1表示完全相同
        """
        if len(hash1) != len(hash2):
            return 0.0
        
        # 计算汉明距离
        distance = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        max_distance = len(hash1)
        
        return 1 - (distance / max_distance)
    
    async def batch_process(
        self,
        images: List[bytes],
        watermark: Optional[WatermarkConfig] = None,
        compress: Optional[CompressConfig] = None,
    ) -> List[ProcessResult]:
        """
        批量处理图片
        """
        tasks = [
            self.process_image(img, watermark, compress)
            for img in images
        ]
        return await asyncio.gather(*tasks)
    
    async def remove_similar_images(
        self,
        images: List[bytes],
        threshold: float = 0.9,
    ) -> Tuple[List[bytes], List[int]]:
        """
        去除相似图片
        
        Args:
            images: 图片数据列表
            threshold: 相似度阈值，超过此值认为是重复图片
        
        Returns:
            (去重后的图片列表, 被移除的索引列表)
        """
        # 计算所有图片的哈希
        hashes = await asyncio.gather(*[
            self.calc_perceptual_hash(img)
            for img in images
        ])
        
        unique_images = []
        unique_hashes = []
        removed_indices = []
        
        for i, (img, hash_val) in enumerate(zip(images, hashes)):
            if hash_val is None:
                removed_indices.append(i)
                continue
            
            # 检查是否与已有图片相似
            is_duplicate = False
            for unique_hash in unique_hashes:
                similarity = self.calc_hash_similarity(hash_val, unique_hash)
                if similarity >= threshold:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                removed_indices.append(i)
            else:
                unique_images.append(img)
                unique_hashes.append(hash_val)
        
        return unique_images, removed_indices
    
    async def enhance_image(
        self,
        image_data: bytes,
        brightness: float = 1.0,
        contrast: float = 1.0,
        sharpness: float = 1.0,
    ) -> ProcessResult:
        """
        图片增强
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self._enhance_image_sync,
                image_data,
                brightness,
                contrast,
                sharpness,
            )
        except Exception as e:
            return ProcessResult(success=False, error_message=str(e))
    
    def _enhance_image_sync(
        self,
        image_data: bytes,
        brightness: float,
        contrast: float,
        sharpness: float,
    ) -> ProcessResult:
        """同步图片增强"""
        img = Image.open(io.BytesIO(image_data))
        
        # 亮度
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
        
        # 对比度
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)
        
        # 锐度
        if sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(sharpness)
        
        # 保存
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=90)
        
        return ProcessResult(
            success=True,
            data=output.getvalue(),
            format='JPEG',
            size=len(output.getvalue()),
            original_size=len(image_data),
        )
    
    async def close(self):
        """关闭资源"""
        await self.client.aclose()
        self.executor.shutdown(wait=True)
