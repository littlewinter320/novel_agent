"""
热点刷新器(TrendRefresher)

核心职责:
- 触发条件：每生成5-25章、进入新篇章/新卷、用户主动要求、检测到梗/词汇超过20章未更新
- 重新搜索当前题材的热门内容
- 与现有梗库和表达变体库合并（去重、标记新鲜度）
- 超过20章未使用的梗标记为"过时"

工作流程:
检查触发条件 → 搜索热点内容 → 合并到梗库/变体库 → 生成更新报告

设计思路:
- 采用"定时检查 + 主动触发"的策略
- 使用LLM搜索当前热门内容
- 与现有数据合并时去重
- 标记新鲜度和过时内容

输出格式:
{
    "refreshed": bool,
    "new_memes": [新梗列表],
    "new_variants": [新变体列表],
    "stale_memes": [过时梗列表],
    "report": 更新报告
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
from core.meme_library import get_meme_library
from core.expression_variants import get_expression_variants


class TrendRefresher:
    """
    热点刷新器类
    
    核心功能:
    1. 触发条件检查：判断是否需要刷新
    2. 热点搜索：搜索当前热门内容
    3. 数据合并：与梗库和变体库合并
    4. 过时标记：标记长期未使用的梗
    5. 生成报告：生成热点更新报告
    
    使用场景:
    - 定期刷新热点内容
    - 保持梗库和变体库的时效性
    - 避免使用过时的梗
    
    使用流程:
    1. 调用check_trigger(current_chapter, last_refresh)检查触发条件
    2. 如果需要刷新，调用refresh(genre)执行刷新
    3. 调用merge_results()合并数据
    4. 生成更新报告
    """
    
    def __init__(self):
        """
        初始化热点刷新器
        
        初始化流程:
        1. 获取LLM客户端
        2. 获取梗库和变体库实例
        """
        self.llm_client = get_llm_client()
        self.meme_library = get_meme_library()
        self.expression_variants = get_expression_variants()
    
    def check_trigger(self, current_chapter: int,
                     last_refresh_chapter: int = 0,
                     user_requested: bool = False,
                     new_volume: bool = False) -> Dict[str, Any]:
        """
        检查触发条件
        
        实现逻辑:
        1. 检查章节间隔（5-25章）
        2. 检查是否进入新卷
        3. 检查用户是否主动要求
        4. 检查梗/词汇是否超过20章未更新
        
        Args:
            current_chapter: 当前章节号
            last_refresh_chapter: 上次刷新的章节号
            user_requested: 用户是否主动要求
            new_volume: 是否进入新卷
        
        Returns:
            触发条件检查结果字典
        """
        should_refresh = False
        reasons = []
        
        # 1. 检查章节间隔
        chapter_interval = current_chapter - last_refresh_chapter
        if chapter_interval >= config.TREND_REFRESH_MIN_INTERVAL:
            should_refresh = True
            reasons.append(f"章节间隔达到{chapter_interval}章（最小间隔{config.TREND_REFRESH_MIN_INTERVAL}章）")
        
        # 2. 检查是否进入新卷
        if new_volume:
            should_refresh = True
            reasons.append("进入新卷")
        
        # 3. 检查用户是否主动要求
        if user_requested:
            should_refresh = True
            reasons.append("用户主动要求")
        
        # 4. 检查梗/词汇是否过时
        stale_check = self._check_stale_content(current_chapter)
        if stale_check.get("has_stale"):
            should_refresh = True
            reasons.append(f"发现{len(stale_check.get('stale_memes', []))}个过时梗")
        
        return {
            "should_refresh": should_refresh,
            "reasons": reasons,
            "chapter_interval": chapter_interval,
            "stale_check": stale_check
        }
    
    def _check_stale_content(self, current_chapter: int) -> Dict[str, Any]:
        """
        检查过时内容
        
        实现逻辑:
        1. 检查梗库中超过20章未使用的梗
        2. 检查变体库中超过20章未使用的变体
        
        Args:
            current_chapter: 当前章节号
        
        Returns:
            过时内容检查结果字典
        """
        stale_memes = []
        
        # 检查梗库
        all_memes = self.meme_library.get_all_memes()
        for category, memes_list in all_memes.items():
            for meme in memes_list:
                usage_record = self.meme_library.usage_records.get(meme, {})
                last_used = usage_record.get("last_used_chapter", 0)
                
                if last_used > 0 and (current_chapter - last_used) > config.MEME_STALE_THRESHOLD:
                    stale_memes.append({
                        "category": category,
                        "meme": meme,
                        "last_used_chapter": last_used,
                        "chapters_since_use": current_chapter - last_used
                    })
        
        return {
            "has_stale": len(stale_memes) > 0,
            "stale_memes": stale_memes,
            "stale_count": len(stale_memes)
        }
    
    def refresh(self, genre: str, current_chapter: int) -> Dict[str, Any]:
        """
        执行热点刷新
        
        实现逻辑:
        1. 搜索当前题材的热门内容
        2. 提取新梗和新变体
        3. 合并到梗库和变体库
        4. 标记过时内容
        5. 生成更新报告
        
        Args:
            genre: 题材名称
            current_chapter: 当前章节号
        
        Returns:
            刷新结果字典
        """
        # 1. 搜索热点内容
        hot_content = self._search_hot_content(genre)
        
        # 2. 提取新梗和新变体
        new_memes = hot_content.get("new_memes", [])
        new_variants = hot_content.get("new_variants", [])
        
        # 3. 合并到梗库和变体库
        merged_memes_count = self._merge_memes(new_memes)
        merged_variants_count = self._merge_variants(new_variants)
        
        # 4. 标记过时内容
        stale_check = self._check_stale_content(current_chapter)
        
        # 5. 生成更新报告
        report = self.generate_refresh_report(
            genre=genre,
            new_memes_count=merged_memes_count,
            new_variants_count=merged_variants_count,
            stale_memes=stale_check.get("stale_memes", []),
            current_chapter=current_chapter
        )
        
        return {
            "refreshed": True,
            "genre": genre,
            "new_memes_count": merged_memes_count,
            "new_variants_count": merged_variants_count,
            "stale_memes": stale_check.get("stale_memes", []),
            "report": report,
            "refreshed_at": datetime.now().isoformat()
        }
    
    def _search_hot_content(self, genre: str) -> Dict[str, Any]:
        """
        搜索当前题材的热门内容
        
        实现逻辑:
        1. 使用LLM搜索当前热门的该题材内容
        2. 提取新梗和新变体
        
        Args:
            genre: 题材名称
        
        Returns:
            热门内容字典
        """
        prompt = f"""搜索当前{genre}题材的热门网络小说中的新梗和流行表达。

请提供：
1. 5-10个新的梗（每类梗一句话描述）
2. 5-10个新的表达变体（常见情感词的新表达）

以JSON格式返回:
{{
    "new_memes": [
        {{"category": "梗类别", "meme": "梗内容"}}
    ],
    "new_variants": [
        {{"base": "基础表达", "variant": "新变体"}}
    ]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            hot_content = json.loads(response)
            return hot_content
        except Exception as e:
            print(f"搜索热点内容失败: {e}")
            return {"new_memes": [], "new_variants": []}
    
    def _merge_memes(self, new_memes: List[Dict[str, str]]) -> int:
        """
        合并新梗到梗库
        
        Args:
            new_memes: 新梗列表
        
        Returns:
            合并的梗数量
        """
        merged_count = 0
        
        for meme_info in new_memes:
            category = meme_info.get("category", "")
            meme = meme_info.get("meme", "")
            
            if category and meme:
                if self.meme_library.add_meme(category, meme):
                    merged_count += 1
        
        return merged_count
    
    def _merge_variants(self, new_variants: List[Dict[str, str]]) -> int:
        """
        合并新变体到变体库
        
        Args:
            new_variants: 新变体列表
        
        Returns:
            合并的变体数量
        """
        merged_count = 0
        
        for variant_info in new_variants:
            base = variant_info.get("base", "")
            variant = variant_info.get("variant", "")
            
            if base and variant:
                if self.expression_variants.add_variant(base, variant):
                    merged_count += 1
        
        return merged_count
    
    def generate_refresh_report(self, genre: str,
                               new_memes_count: int,
                               new_variants_count: int,
                               stale_memes: List[Dict[str, Any]],
                               current_chapter: int) -> str:
        """
        生成热点更新报告
        
        Args:
            genre: 题材名称
            new_memes_count: 新梗数量
            new_variants_count: 新变体数量
            stale_memes: 过时梗列表
            current_chapter: 当前章节号
        
        Returns:
            Markdown格式的报告
        """
        report = f"# 热点更新报告\n\n"
        report += f"**题材**: {genre}\n"
        report += f"**当前章节**: 第{current_chapter}章\n"
        report += f"**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 新增内容
        report += "## 新增内容\n\n"
        report += f"- 新增梗: {new_memes_count}个\n"
        report += f"- 新增表达变体: {new_variants_count}个\n\n"
        
        # 过时内容
        if stale_memes:
            report += "## 过时内容\n\n"
            report += f"发现{len(stale_memes)}个超过{config.MEME_STALE_THRESHOLD}章未使用的梗:\n\n"
            for stale in stale_memes[:5]:  # 只显示前5个
                report += f"- [{stale.get('category', '未知')}] {stale.get('meme', '未知')} "
                report += f"(上次使用: 第{stale.get('last_used_chapter', '?')}章, "
                report += f"已过{stale.get('chapters_since_use', '?')}章)\n"
            if len(stale_memes) > 5:
                report += f"- ... 还有{len(stale_memes) - 5}个过时梗\n"
            report += "\n"
        
        # 建议
        report += "## 建议\n\n"
        if stale_memes:
            report += "- 建议避免使用过时梗，或为其注入新元素\n"
        if new_memes_count > 0:
            report += "- 新梗已添加到梗库，可以在后续章节中使用\n"
        if new_variants_count > 0:
            report += "- 新表达变体已添加到变体库，可以丰富表达方式\n"
        
        return report


# 全局实例
_trend_refresher = None


def get_trend_refresher() -> TrendRefresher:
    """获取全局热点刷新器实例（单例模式）"""
    global _trend_refresher
    if _trend_refresher is None:
        _trend_refresher = TrendRefresher()
    return _trend_refresher
