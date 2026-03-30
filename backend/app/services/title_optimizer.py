"""
AI标题优化服务 - 使用AI优化商品标题
"""
import json
import re
from typing import List, Optional, Dict
from dataclasses import dataclass

from openai import AsyncOpenAI
from loguru import logger

from app.core.config import settings


@dataclass
class OptimizeResult:
    """优化结果"""
    original_title: str
    optimized_title: str
    keywords: List[str]  # 提取的关键词
    score: float  # 优化得分
    improvements: List[str]  # 改进点说明


class TitleOptimizer:
    """
    AI标题优化器
    """
    
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL or None,
            )
        
        # 闲鱼热门关键词库（可以定期更新）
        self.hot_keywords = {
            '通用': ['全新', '正品', '包邮', '现货', '限量', '网红', '爆款', 'ins风', '少女心'],
            '数码': ['原装', '国行', '未拆封', '二手', '99新', '无拆修', '有发票'],
            '服饰': ['潮牌', '设计师', '韩版', '日系', '复古', '百搭', '显瘦'],
            '美妆': ['专柜', '小样', '正装', '明星同款', '好用', '回购'],
            '家居': ['北欧', '简约', '收纳', '神器', '实用', '高颜值'],
            '母婴': ['进口', '安全', '可啃咬', '益智', '成长'],
        }
    
    async def optimize_title(
        self,
        original_title: str,
        category: Optional[str] = None,
        platform: str = "xianyu",
    ) -> Optional[OptimizeResult]:
        """
        优化商品标题
        
        Args:
            original_title: 原标题
            category: 商品分类
            platform: 目标平台（xianyu/taobao等）
        """
        if not self.client:
            logger.warning("AI client not initialized, using rule-based optimization")
            return self._rule_optimize(original_title, category)
        
        try:
            # 构建提示词
            prompt = self._build_optimize_prompt(original_title, category, platform)
            
            response = await self.client.chat.completions.create(
                model=settings.AI_MODEL or "gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的电商标题优化专家，擅长为闲鱼、淘宝等平台优化商品标题。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500,
            )
            
            content = response.choices[0].message.content
            return self._parse_optimize_result(original_title, content)
            
        except Exception as e:
            logger.error(f"AI optimize error: {e}")
            # 降级到规则优化
            return self._rule_optimize(original_title, category)
    
    def _build_optimize_prompt(
        self,
        title: str,
        category: Optional[str],
        platform: str,
    ) -> str:
        """构建优化提示词"""
        category_hint = f"，商品分类是{category}" if category else ""
        
        hot_words = []
        if category and category in self.hot_keywords:
            hot_words = self.hot_keywords[category]
        hot_words_str = "、".join(hot_words[:10]) if hot_words else "全新、正品、包邮等"
        
        prompt = f"""请优化以下{platform}商品标题{category_hint}：

原标题：{title}

要求：
1. 标题长度控制在30字以内（闲鱼限制）
2. 突出商品卖点和优势
3. 包含热搜关键词，如：{hot_words_str}
4. 避免违禁词和敏感词
5. 吸引买家点击

请以JSON格式返回：
{{
    "optimized_title": "优化后的标题",
    "keywords": ["关键词1", "关键词2"],
    "score": 85,
    "improvements": ["改进点1", "改进点2"]
}}
"""
        return prompt
    
    def _parse_optimize_result(
        self,
        original_title: str,
        content: str,
    ) -> OptimizeResult:
        """解析AI返回的优化结果"""
        try:
            # 提取JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return OptimizeResult(
                    original_title=original_title,
                    optimized_title=data.get('optimized_title', original_title),
                    keywords=data.get('keywords', []),
                    score=float(data.get('score', 70)),
                    improvements=data.get('improvements', []),
                )
        except Exception as e:
            logger.error(f"Parse optimize result error: {e}")
        
        # 解析失败时返回原始标题
        return OptimizeResult(
            original_title=original_title,
            optimized_title=original_title,
            keywords=[],
            score=50,
            improvements=["AI解析失败，使用原标题"],
        )
    
    def _rule_optimize(
        self,
        title: str,
        category: Optional[str],
    ) -> OptimizeResult:
        """
        基于规则的标题优化（AI不可用时降级使用）
        """
        improvements = []
        keywords = []
        
        optimized = title
        
        # 规则1：去除多余空格
        if '  ' in optimized:
            optimized = re.sub(r'\s+', ' ', optimized)
            improvements.append("去除多余空格")
        
        # 规则2：添加通用热词（如果不存在）
        hot_words = self.hot_keywords.get(category, self.hot_keywords['通用'])
        added_words = []
        for word in hot_words[:3]:
            if word not in optimized and len(optimized) + len(word) + 1 <= 30:
                optimized = word + optimized
                added_words.append(word)
                keywords.append(word)
        if added_words:
            improvements.append(f"添加热搜词：{', '.join(added_words)}")
        
        # 规则3：去除无意义的词
        useless_words = ['的', '了', '一个', '这个']
        removed = []
        for word in useless_words:
            if word in optimized:
                optimized = optimized.replace(word, '')
                removed.append(word)
        if removed:
            improvements.append(f"去除冗余词：{', '.join(removed)}")
        
        # 规则4：添加表情符号增加吸引力（控制数量）
        if '🔥' not in optimized and len(optimized) < 28:
            optimized = '🔥' + optimized
            improvements.append("添加热度标识")
        
        # 计算得分
        score = self._calc_title_score(optimized)
        
        # 提取关键词
        if not keywords:
            keywords = self._extract_keywords(optimized)
        
        return OptimizeResult(
            original_title=title,
            optimized_title=optimized,
            keywords=keywords,
            score=score,
            improvements=improvements if improvements else ["规则优化完成"],
        )
    
    def _calc_title_score(self, title: str) -> float:
        """计算标题质量得分"""
        score = 60  # 基础分
        
        # 长度得分（15-25字最佳）
        length = len(title)
        if 15 <= length <= 25:
            score += 15
        elif 10 <= length < 15 or 25 < length <= 30:
            score += 10
        else:
            score += 5
        
        # 包含数字加分
        if re.search(r'\d', title):
            score += 5
        
        # 包含热词加分
        all_hot_words = []
        for words in self.hot_keywords.values():
            all_hot_words.extend(words)
        
        hot_word_count = sum(1 for word in all_hot_words if word in title)
        score += min(15, hot_word_count * 3)
        
        # 包含特殊符号（emoji）加分
        if any(ord(c) > 127 for c in title):
            score += 5
        
        return min(100, score)
    
    def _extract_keywords(self, title: str) -> List[str]:
        """从标题中提取关键词"""
        # 简单的关键词提取：去除停用词后的名词
        stop_words = {'的', '了', '是', '在', '有', '和', '与', '或', '等', '及'}
        
        words = []
        for word in re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+|\d+', title):
            if word not in stop_words and len(word) >= 2:
                words.append(word)
        
        return words[:5]  # 返回前5个关键词
    
    async def batch_optimize(
        self,
        titles: List[Dict[str, str]],
    ) -> List[OptimizeResult]:
        """
        批量优化标题
        
        Args:
            titles: [{"title": "...", "category": "..."}, ...]
        """
        tasks = [
            self.optimize_title(
                t['title'],
                t.get('category'),
                t.get('platform', 'xianyu')
            )
            for t in titles
        ]
        
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]
    
    async def generate_description(
        self,
        title: str,
        features: List[str],
        category: Optional[str] = None,
    ) -> str:
        """
        生成商品描述
        """
        if not self.client:
            # 使用模板生成
            return self._generate_template_description(title, features, category)
        
        try:
            features_str = "\n".join(f"- {f}" for f in features)
            
            prompt = f"""请为以下商品生成闲鱼商品描述：

标题：{title}
商品特点：
{features_str}

要求：
1. 描述简洁明了，100-200字
2. 突出商品卖点
3. 语气亲切自然
4. 适当使用emoji
5. 包含"非质量问题不退换"等必要声明

请直接返回描述内容：
"""
            
            response = await self.client.chat.completions.create(
                model=settings.AI_MODEL or "gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个闲鱼卖家，擅长写吸引人的商品描述。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_tokens=500,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Generate description error: {e}")
            return self._generate_template_description(title, features, category)
    
    def _generate_template_description(
        self,
        title: str,
        features: List[str],
        category: Optional[str],
    ) -> str:
        """使用模板生成描述"""
        lines = [
            f"✨ {title}",
            "",
            "📦 商品详情：",
        ]
        
        for feature in features[:5]:
            lines.append(f"• {feature}")
        
        lines.extend([
            "",
            "💡 温馨提示：",
            "• 实物拍摄，所见即所得",
            "• 非质量问题不退换",
            "• 48小时内发货",
            "",
            "🎁 喜欢就带走吧~",
        ])
        
        return "\n".join(lines)
    
    async def analyze_keywords(
        self,
        category: str,
        top_n: int = 20,
    ) -> List[Dict]:
        """
        分析分类下的热门关键词
        
        Returns:
            [{"keyword": "...", "search_volume": 1000, "competition": "high"}, ...]
        """
        # 这里可以接入实际的关键词API
        # 目前返回预设的热词
        keywords = self.hot_keywords.get(category, self.hot_keywords['通用'])
        
        return [
            {
                "keyword": kw,
                "search_volume": 10000 - i * 500,  # 模拟数据
                "competition": "medium" if i < 5 else "low",
            }
            for i, kw in enumerate(keywords[:top_n])
        ]


import asyncio  # noqa: E402
