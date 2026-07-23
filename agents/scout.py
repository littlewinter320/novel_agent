"""
扫榜分析师(SubAgent-Scout)

核心职责:
- 根据用户提供的小说类型/题材，通过真实爬虫获取当前热门作品数据
- 爬取数据自动入库，截图供Agent视觉分析
- 分析3-5部对标作品的爆火特征（开篇钩子、爽点分布、人设套路、剧情模板、读者反馈）
- 爆火写法特征自动记录到知识库
- 输出结构化报告 + 针对性写法建议 + 推荐大纲框架

工作流程:
用户输入题材 → 爬虫获取真实数据 → 数据入库 → 截图 → 更新知识库 → 分析每部作品 → 提取共性特征 → 输出建议

设计思路:
- 优先使用真实爬虫获取数据，爬虫失败时降级为LLM搜索
- 爬取的数据自动持久化到SQLite数据库
- 爆火小说的写法特征自动更新到题材知识库
- 分析维度：开篇钩子、爽点分布、人设套路、剧情模板、读者反馈

输出格式:
{
    "hot_novels": [热门作品列表],
    "feature_analysis": [特征分析结果],
    "common_features": [共性特征],
    "suggestions": [针对性建议],
    "recommended_outline": [推荐大纲框架],
    "data_source": "crawl" | "llm"  # 数据来源标记
}
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.llm_client import get_llm_client
from utils.web_scraper import get_web_scraper
from utils.screenshot_tool import get_screenshot_tool
from utils.progress_display import get_progress_display
from core.novel_database import get_novel_database
from core.genre_knowledge import get_genre_knowledge_base


class ScoutAgent:
    """
    扫榜分析师类
    
    核心功能:
    1. 热门作品搜索：通过网络搜索获取当前热门作品
    2. 特征分析：分析每部作品的爆火特征
    3. 共性提取：提取多部作品的共性特征
    4. 建议生成：基于分析结果生成针对性建议
    5. 大纲推荐：推荐适合的剧情框架
    
    使用场景:
    - 用户确定题材后，需要了解当前市场趋势
    - 用户需要参考热门作品的设计思路
    - 用户需要针对性的写法建议
    
    使用流程:
    1. 调用analyze_genre(genre, constraints)开始分析
    2. 内部自动调用search_hot_novels()搜索热门作品
    3. 调用extract_features()分析每部作品
    4. 调用generate_report()生成完整报告
    """
    
    def __init__(self):
        """
        初始化扫榜分析师
        
        初始化流程:
        1. 获取LLM客户端（用于搜索和分析）
        2. 获取题材知识库实例（用于查询题材规范）
        3. 初始化爬虫、截图、数据库、进度显示模块
        4. 初始化分析缓存（避免重复分析）
        """
        self.llm_client = get_llm_client()
        self.genre_knowledge_base = get_genre_knowledge_base()
        # 新增模块：爬虫、截图、数据库、进度显示
        self.web_scraper = get_web_scraper()
        self.screenshot_tool = get_screenshot_tool()
        self.novel_db = get_novel_database()
        self.progress = get_progress_display()
        self._analysis_cache = {}
    
    def analyze_genre(self, genre: str, constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分析指定题材的热门作品（核心入口方法）
        
        实现逻辑:
        1. 检查缓存，如果已有分析结果直接返回
        2. 调用search_hot_novels()搜索热门作品
        3. 调用extract_features()分析每部作品
        4. 调用analyze_common_features()提取共性特征
        5. 调用generate_suggestions()生成建议
        6. 调用generate_recommended_outline()生成推荐大纲
        7. 缓存结果并返回
        
        Args:
            genre: 题材名称（如"玄幻"、"都市"等）
            constraints: 用户约束条件（可选）
        
        Returns:
            分析结果字典，包含：
            - hot_novels: 热门作品列表
            - feature_analysis: 特征分析结果
            - common_features: 共性特征
            - suggestions: 针对性建议
            - recommended_outline: 推荐大纲框架
        """
        # 检查缓存
        cache_key = f"{genre}_{json.dumps(constraints, sort_keys=True) if constraints else 'default'}"
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]
        
        # 1. 搜索热门作品
        hot_novels = self.search_hot_novels(genre, constraints)
        
        # 2. 分析每部作品的特征
        feature_analysis = []
        for novel in hot_novels:
            features = self.extract_features(novel, genre)
            feature_analysis.append({
                "novel": novel,
                "features": features
            })
        
        # 3. 提取共性特征
        common_features = self.analyze_common_features(feature_analysis)
        
        # 4. 生成针对性建议
        suggestions = self.generate_suggestions(common_features, genre, constraints)
        
        # 5. 生成推荐大纲框架
        recommended_outline = self.generate_recommended_outline(common_features, genre)
        
        # 构建完整结果
        result = {
            "genre": genre,
            "hot_novels": hot_novels,
            "feature_analysis": feature_analysis,
            "common_features": common_features,
            "suggestions": suggestions,
            "recommended_outline": recommended_outline,
            "analyzed_at": datetime.now().isoformat()
        }
        
        # 缓存结果
        self._analysis_cache[cache_key] = result
        
        return result
    
    def search_hot_novels(self, genre: str, constraints: Dict[str, Any] = None, 
                         platform: str = "番茄小说") -> List[Dict[str, Any]]:
        """
        搜索热门作品（优先使用真实爬虫）
        
        实现逻辑:
        1. 优先使用爬虫从指定平台获取真实数据
        2. 爬取的数据自动入库保存
        3. 爬虫失败时降级为LLM搜索
        
        Args:
            genre: 题材名称
            constraints: 用户约束条件
            platform: 目标平台（默认番茄小说）
        
        Returns:
            热门作品列表，每部作品包含：
            - title: 作品名称
            - author: 作者
            - platform: 平台
            - popularity: 热度指标
            - brief: 简介
            - tags: 标签列表
            - url: 作品链接
        """
        # 尝试使用爬虫获取真实数据
        crawled_novels = self._crawl_platform_data(platform, genre)
        
        if crawled_novels:
            # 爬虫成功，保存数据到数据库
            self._save_crawled_data(crawled_novels, platform, genre)
            return crawled_novels
        
        # 爬虫失败，降级为LLM搜索
        print(f"爬虫获取数据失败，使用LLM搜索模式...")
        return self._llm_search_hot_novels(genre, constraints)
    
    def _crawl_platform_data(self, platform: str, genre: str) -> List[Dict[str, Any]]:
        """
        从指定平台爬取热门小说数据
        
        Args:
            platform: 平台名称
            genre: 题材名称
        
        Returns:
            爬取到的小说列表，失败返回空列表
        """
        try:
            self.progress.start_task(f"正在从{platform}爬取{genre}类热门小说...", total=1)
            
            # 调用爬虫模块
            crawl_result = self.web_scraper.crawl_platform(platform, genre, limit=10)
            
            if "error" in crawl_result:
                self.progress.fail_task(f"爬取失败: {crawl_result['error']}")
                return []
            
            novels = crawl_result.get("novels", [])
            self.progress.complete_task(f"成功获取{len(novels)}部小说数据")
            
            # 截图保存（可选）
            if crawl_result.get("url"):
                try:
                    screenshot_result = self.screenshot_tool.take_screenshot(
                        crawl_result["url"],
                        filename=f"{platform}_{genre}_ranking"
                    )
                    if "error" not in screenshot_result:
                        print(f"页面截图已保存: {screenshot_result.get('screenshot_path')}")
                except Exception as e:
                    print(f"截图失败（非关键功能）: {e}")
            
            return novels
            
        except Exception as e:
            print(f"爬取平台数据失败: {e}")
            return []
    
    def _save_crawled_data(self, novels: List[Dict[str, Any]], platform: str, genre: str):
        """
        保存爬取的数据到数据库
        
        Args:
            novels: 小说列表
            platform: 平台名称
            genre: 题材名称
        """
        try:
            saved_count = 0
            for novel in novels:
                # 补充平台和题材信息
                novel["platform"] = platform
                novel["genre"] = genre
                
                # 保存到数据库
                novel_id = self.novel_db.save_novel(novel)
                if novel_id > 0:
                    saved_count += 1
            
            # 记录爬取日志
            crawl_url = f"https://{platform}.com/rank/{genre}"
            self.novel_db.log_crawl(platform, genre, crawl_url, "success", f"爬取{len(novels)}部小说", len(novels))
            
            print(f"数据入库完成: 新增/更新{saved_count}部小说")
            
        except Exception as e:
            print(f"保存爬取数据失败: {e}")
    
    def _llm_search_hot_novels(self, genre: str, constraints: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        使用LLM搜索热门作品（降级方案）
        
        Args:
            genre: 题材名称
            constraints: 用户约束条件
        
        Returns:
            热门作品列表
        """
        # 构造约束文本
        constraints_text = ""
        if constraints:
            constraints_text = f"\n用户约束: {json.dumps(constraints, ensure_ascii=False)}"
        
        prompt = f"""请搜索当前{genre}题材的热门网络小说作品，找出3-5部代表性作品。

要求:
1. 作品必须是近期热门（2023-2024年）
2. 作品必须有较高的读者评价和热度
3. 作品应该代表该题材的典型写法
{constraints_text}

请以JSON数组格式返回，每部作品包含以下字段:
{{
    "title": "作品名称",
    "author": "作者",
    "platform": "平台（如起点中文网、晋江文学城等）",
    "popularity": "热度指标（如月票数、收藏数、评分等）",
    "brief": "作品简介（100字以内）",
    "tags": ["标签列表"]
}}

只返回JSON数组，不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            hot_novels = json.loads(response)
            return hot_novels if isinstance(hot_novels, list) else []
        except Exception as e:
            print(f"LLM搜索热门作品失败: {e}")
            return []
    
    def extract_features(self, novel: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """
        提取单部作品的爆火特征
        
        实现逻辑:
        1. 构造分析提示词，要求LLM分析该作品的爆火特征
        2. 分析维度：开篇钩子、爽点分布、人设套路、剧情模板、读者反馈
        3. 调用LLM生成分析结果
        
        Args:
            novel: 作品信息字典
            genre: 题材名称
        
        Returns:
            特征分析结果字典，包含：
            - opening_hook: 开篇钩子设计
            - excitement_distribution: 爽点分布
            - character_archetype: 人设套路
            - plot_template: 剧情模板
            - reader_feedback: 读者反馈
        """
        title = novel.get("title", "未知")
        brief = novel.get("brief", "无简介")
        
        prompt = f"""分析以下{genre}题材作品的爆火特征。

作品信息:
- 名称: {title}
- 简介: {brief}

请从以下5个维度分析该作品的爆火特征:

1. 开篇钩子: 前3章如何吸引读者？使用了什么钩子？
2. 爽点分布: 爽点如何分布？每隔多少章一个爽点？
3. 人设套路: 主角和配角的人设有什么特点？
4. 剧情模板: 使用了什么经典剧情模板？
5. 读者反馈: 读者最喜欢什么？最吐槽什么？

请以JSON格式返回:
{{
    "opening_hook": "开篇钩子设计",
    "excitement_distribution": "爽点分布特点",
    "character_archetype": "人设套路",
    "plot_template": "剧情模板",
    "reader_feedback": {{
        "likes": ["读者喜欢的点"],
        "dislikes": ["读者吐槽的点"]
    }}
}}

只返回JSON对象，不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            features = json.loads(response)
            return features
        except Exception as e:
            print(f"提取特征失败 {title}: {e}")
            return {}
    
    def analyze_common_features(self, feature_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析多部作品的共性特征
        
        实现逻辑:
        1. 收集所有作品的特征
        2. 提取重复出现的模式
        3. 总结共性特征
        
        Args:
            feature_analysis: 特征分析结果列表
        
        Returns:
            共性特征字典
        """
        if not feature_analysis:
            return {}
        
        # 构造提示词
        analyses_text = json.dumps(feature_analysis, ensure_ascii=False, indent=2)
        
        prompt = f"""分析以下多部作品的特征，提取共性特征。

作品特征分析:
{analyses_text}

请提取这些作品的共性特征，总结以下内容:
1. 共同的成功要素
2. 常见的开篇钩子类型
3. 常见的爽点分布模式
4. 常见的人设套路
5. 常见的剧情模板
6. 读者普遍喜欢的元素
7. 读者普遍吐槽的元素

请以JSON格式返回:
{{
    "success_factors": ["共同的成功要素"],
    "common_opening_hooks": ["常见的开篇钩子类型"],
    "common_excitement_patterns": ["常见的爽点分布模式"],
    "common_character_archetypes": ["常见的人设套路"],
    "common_plot_templates": ["常见的剧情模板"],
    "reader_preferences": {{
        "likes": ["读者普遍喜欢的元素"],
        "dislikes": ["读者普遍吐槽的元素"]
    }}
}}

只返回JSON对象，不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            common_features = json.loads(response)
            return common_features
        except Exception as e:
            print(f"分析共性特征失败: {e}")
            return {}
    
    def generate_suggestions(self, common_features: Dict[str, Any], 
                            genre: str,
                            constraints: Dict[str, Any] = None) -> List[str]:
        """
        生成针对性写法建议
        
        实现逻辑:
        1. 基于共性特征和题材知识库
        2. 结合用户约束
        3. 生成具体的写法建议
        
        Args:
            common_features: 共性特征
            genre: 题材名称
            constraints: 用户约束
        
        Returns:
            建议列表
        """
        # 获取题材知识库信息
        genre_info = self.genre_knowledge_base.get_genre(genre)
        writing_style = genre_info.get("writing_style", "") if genre_info else ""
        taboo_list = genre_info.get("taboo_list", []) if genre_info else []
        
        # 构造约束文本
        constraints_text = ""
        if constraints:
            constraints_text = f"\n用户约束: {json.dumps(constraints, ensure_ascii=False)}"
        
        prompt = f"""基于以下信息，为{genre}题材的小说创作生成针对性写法建议。

共性特征:
{json.dumps(common_features, ensure_ascii=False, indent=2)}

题材写作风格:
{writing_style}

题材禁忌:
{chr(10).join([f'- {t}' for t in taboo_list]) if taboo_list else '无'}
{constraints_text}

请生成5-8条具体的写法建议，每条建议要:
1. 具体可操作
2. 符合该题材特点
3. 避免题材禁忌
4. 参考成功作品的经验

请以JSON数组格式返回建议列表:
["建议1", "建议2", ...]

只返回JSON数组，不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            suggestions = json.loads(response)
            return suggestions if isinstance(suggestions, list) else []
        except Exception as e:
            print(f"生成建议失败: {e}")
            return []
    
    def generate_recommended_outline(self, common_features: Dict[str, Any], 
                                    genre: str) -> Dict[str, Any]:
        """
        生成推荐大纲框架
        
        实现逻辑:
        1. 基于共性特征中的剧情模板
        2. 结合题材特点
        3. 生成推荐的大纲框架
        
        Args:
            common_features: 共性特征
            genre: 题材名称
        
        Returns:
            推荐大纲框架字典
        """
        plot_templates = common_features.get("common_plot_templates", [])
        
        prompt = f"""基于以下信息，为{genre}题材的小说生成推荐大纲框架。

常见剧情模板:
{chr(10).join([f'- {p}' for p in plot_templates[:3]]) if plot_templates else '无'}

请生成一个推荐的大纲框架，包含:
1. 总纲: 整体剧情走向（起承转合）
2. 卷纲: 分卷设计（每卷的核心事件）
3. 开篇设计: 前3章的详细设计
4. 爽点分布: 爽点如何分布

请以JSON格式返回:
{{
    "master_outline": {{
        "act_1_start": "起(开篇)描述",
        "act_2_develop": "承(发展)描述",
        "act_3_turn": "转(高潮)描述",
        "act_4_end": "合(结局)描述"
    }},
    "volume_design": [
        {{
            "volume_num": 1,
            "core_event": "核心事件",
            "estimated_chapters": 预估章节数
        }}
    ],
    "opening_design": {{
        "chapter_1": "第1章设计",
        "chapter_2": "第2章设计",
        "chapter_3": "第3章设计"
    }},
    "excitement_distribution": "爽点分布建议"
}}

只返回JSON对象，不要其他内容。"""
        
        try:
            response = self.llm_client.generate(prompt)
            recommended_outline = json.loads(response)
            return recommended_outline
        except Exception as e:
            print(f"生成推荐大纲失败: {e}")
            return {}
    
    def generate_report(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成人类可读的分析报告
        
        实现逻辑:
        1. 将分析结果转换为Markdown格式
        2. 分章节展示：热门作品、特征分析、共性特征、建议、推荐大纲
        
        Args:
            analysis_result: 分析结果字典
        
        Returns:
            Markdown格式的报告
        """
        report = "# 扫榜分析报告\n\n"
        
        # 1. 热门作品
        hot_novels = analysis_result.get("hot_novels", [])
        if hot_novels:
            report += "## 一、热门作品\n\n"
            for i, novel in enumerate(hot_novels, 1):
                report += f"### {i}. {novel.get('title', '未知')}\n"
                report += f"- **作者**: {novel.get('author', '未知')}\n"
                report += f"- **平台**: {novel.get('platform', '未知')}\n"
                report += f"- **热度**: {novel.get('popularity', '未知')}\n"
                report += f"- **简介**: {novel.get('brief', '无')}\n\n"
        
        # 2. 特征分析
        feature_analysis = analysis_result.get("feature_analysis", [])
        if feature_analysis:
            report += "## 二、特征分析\n\n"
            for item in feature_analysis:
                novel = item.get("novel", {})
                features = item.get("features", {})
                report += f"### {novel.get('title', '未知')}\n"
                report += f"- **开篇钩子**: {features.get('opening_hook', '未知')}\n"
                report += f"- **爽点分布**: {features.get('excitement_distribution', '未知')}\n"
                report += f"- **人设套路**: {features.get('character_archetype', '未知')}\n"
                report += f"- **剧情模板**: {features.get('plot_template', '未知')}\n\n"
        
        # 3. 共性特征
        common_features = analysis_result.get("common_features", {})
        if common_features:
            report += "## 三、共性特征\n\n"
            report += "### 成功要素\n"
            for factor in common_features.get("success_factors", []):
                report += f"- {factor}\n"
            report += "\n"
            
            report += "### 常见开篇钩子\n"
            for hook in common_features.get("common_opening_hooks", []):
                report += f"- {hook}\n"
            report += "\n"
            
            report += "### 常见爽点模式\n"
            for pattern in common_features.get("common_excitement_patterns", []):
                report += f"- {pattern}\n"
            report += "\n"
        
        # 4. 针对性建议
        suggestions = analysis_result.get("suggestions", [])
        if suggestions:
            report += "## 四、针对性建议\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                report += f"{i}. {suggestion}\n"
            report += "\n"
        
        # 5. 推荐大纲
        recommended_outline = analysis_result.get("recommended_outline", {})
        if recommended_outline:
            report += "## 五、推荐大纲框架\n\n"
            
            master_outline = recommended_outline.get("master_outline", {})
            if master_outline:
                report += "### 总纲\n"
                report += f"- **起(开篇)**: {master_outline.get('act_1_start', '未知')}\n"
                report += f"- **承(发展)**: {master_outline.get('act_2_develop', '未知')}\n"
                report += f"- **转(高潮)**: {master_outline.get('act_3_turn', '未知')}\n"
                report += f"- **合(结局)**: {master_outline.get('act_4_end', '未知')}\n\n"
            
            volume_design = recommended_outline.get("volume_design", [])
            if volume_design:
                report += "### 卷纲设计\n"
                for volume in volume_design:
                    report += f"- **第{volume.get('volume_num', '?')}卷**: {volume.get('core_event', '未知')} (预估{volume.get('estimated_chapters', '?')}章)\n"
                report += "\n"
        
        return report


# 全局实例
_scout_agent = None


def get_scout_agent() -> ScoutAgent:
    """获取全局扫榜分析师实例（单例模式）"""
    global _scout_agent
    if _scout_agent is None:
        _scout_agent = ScoutAgent()
    return _scout_agent
