"""
多样性统计报告(DiversityReport)

核心职责:
- 统计词汇使用频率、句式分布、梗使用分布、结构分布
- 定期输出报告，提醒"过度使用"的元素

工作流程:
收集章节数据 → 统计分析 → 检测过度使用 → 生成报告

设计思路:
- 使用统计分析方法
- 检测重复和过度使用
- 生成可读的报告

输出格式:
{
    "vocabulary_stats": 词汇统计,
    "sentence_stats": 句式统计,
    "meme_stats": 梗统计,
    "structure_stats": 结构统计,
    "overuse_warnings": [过度使用警告],
    "report": 报告文本
}
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from collections import Counter
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class DiversityReport:
    """
    多样性统计报告类
    
    核心功能:
    1. 词汇统计：统计词汇使用频率
    2. 句式统计：统计句式分布
    3. 梗统计：统计梗使用情况
    4. 结构统计：统计章节结构分布
    5. 过度使用检测：检测重复元素
    
    使用场景:
    - 定期生成多样性报告
    - 检测过度使用的元素
    - 优化创作多样性
    
    使用流程:
    1. 调用generate_statistics(recent_chapters)生成统计
    2. 调用check_overuse()检测过度使用
    3. 调用generate_report()生成报告
    """
    
    def __init__(self):
        """
        初始化多样性报告
        
        初始化流程:
        1. 初始化统计数据存储
        """
        self.statistics = {}
    
    def generate_statistics(self, recent_chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成统计数据（核心方法）
        
        实现逻辑:
        1. 收集所有章节的文本数据
        2. 统计词汇使用频率
        3. 统计句式分布
        4. 统计梗使用情况
        5. 统计结构分布
        
        Args:
            recent_chapters: 最近章节数据列表
        
        Returns:
            统计数据字典
        """
        if not recent_chapters:
            return {}
        
        # 收集所有文本
        all_text = ""
        for chapter in recent_chapters:
            content = chapter.get("chapter_content", "")
            all_text += content + " "
        
        # 1. 词汇统计
        vocabulary_stats = self._analyze_vocabulary(all_text)
        
        # 2. 句式统计
        sentence_stats = self._analyze_sentences(all_text)
        
        # 3. 梗统计
        meme_stats = self._analyze_memes(recent_chapters)
        
        # 4. 结构统计
        structure_stats = self._analyze_structures(recent_chapters)
        
        self.statistics = {
            "vocabulary_stats": vocabulary_stats,
            "sentence_stats": sentence_stats,
            "meme_stats": meme_stats,
            "structure_stats": structure_stats,
            "chapter_count": len(recent_chapters),
            "total_words": len(all_text),
            "generated_at": datetime.now().isoformat()
        }
        
        return self.statistics
    
    def _analyze_vocabulary(self, text: str) -> Dict[str, Any]:
        """分析词汇使用"""
        # 简单的词汇统计（实际应该使用分词库）
        words = text.split()
        word_counts = Counter(words)
        
        # 获取最常见的词汇
        most_common = word_counts.most_common(20)
        
        return {
            "total_words": len(words),
            "unique_words": len(word_counts),
            "most_common": most_common
        }
    
    def _analyze_sentences(self, text: str) -> Dict[str, Any]:
        """分析句式分布"""
        # 按句号、问号、感叹号分割句子
        sentences = []
        for delimiter in ['。', '？', '！']:
            sentences.extend(text.split(delimiter))
        
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 统计句子长度分布
        sentence_lengths = [len(s) for s in sentences]
        
        if sentence_lengths:
            avg_length = sum(sentence_lengths) / len(sentence_lengths)
            max_length = max(sentence_lengths)
            min_length = min(sentence_lengths)
        else:
            avg_length = max_length = min_length = 0
        
        return {
            "total_sentences": len(sentences),
            "avg_length": round(avg_length, 2),
            "max_length": max_length,
            "min_length": min_length
        }
    
    def _analyze_memes(self, chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析梗使用情况"""
        # 简化实现：统计特定关键词
        meme_keywords = ["打脸", "升级", "逆袭", "奇遇", "突破"]
        meme_counts = {}
        
        for keyword in meme_keywords:
            count = 0
            for chapter in chapters:
                content = chapter.get("chapter_content", "")
                count += content.count(keyword)
            meme_counts[keyword] = count
        
        return {
            "meme_counts": meme_counts,
            "total_memes": sum(meme_counts.values())
        }
    
    def _analyze_structures(self, chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析结构分布"""
        # 简化实现：统计章节长度分布
        chapter_lengths = [len(chapter.get("chapter_content", "")) for chapter in chapters]
        
        if chapter_lengths:
            avg_length = sum(chapter_lengths) / len(chapter_lengths)
            max_length = max(chapter_lengths)
            min_length = min(chapter_lengths)
        else:
            avg_length = max_length = min_length = 0
        
        return {
            "chapter_count": len(chapters),
            "avg_chapter_length": round(avg_length, 2),
            "max_chapter_length": max_length,
            "min_chapter_length": min_length
        }
    
    def check_overuse(self) -> Dict[str, Any]:
        """
        检测过度使用
        
        实现逻辑:
        1. 检查词汇使用频率
        2. 检查梗使用频率
        3. 生成警告
        
        Returns:
            过度使用检测结果字典
        """
        warnings = []
        
        if not self.statistics:
            return {"has_overuse": False, "warnings": []}
        
        # 检查词汇过度使用
        vocab_stats = self.statistics.get("vocabulary_stats", {})
        most_common = vocab_stats.get("most_common", [])
        
        for word, count in most_common[:5]:
            if count > config.DIVERSITY_WORD_THRESHOLD:
                warnings.append(f"词汇'{word}'使用过于频繁({count}次)")
        
        # 检查梗过度使用
        meme_stats = self.statistics.get("meme_stats", {})
        meme_counts = meme_stats.get("meme_counts", {})
        
        for meme, count in meme_counts.items():
            if count > config.DIVERSITY_MEME_THRESHOLD:
                warnings.append(f"梗'{meme}'使用过于频繁({count}次)")
        
        return {
            "has_overuse": len(warnings) > 0,
            "warnings": warnings
        }
    
    def generate_report(self) -> str:
        """
        生成多样性报告
        
        Returns:
            Markdown格式的报告
        """
        if not self.statistics:
            return "无统计数据"
        
        report = "# 多样性统计报告\n\n"
        report += f"统计章节数: {self.statistics.get('chapter_count', 0)}\n"
        report += f"总字数: {self.statistics.get('total_words', 0)}\n"
        report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 词汇统计
        report += "## 词汇统计\n\n"
        vocab_stats = self.statistics.get("vocabulary_stats", {})
        report += f"- 总词汇数: {vocab_stats.get('total_words', 0)}\n"
        report += f"- 不重复词汇数: {vocab_stats.get('unique_words', 0)}\n"
        
        most_common = vocab_stats.get("most_common", [])
        if most_common:
            report += "\n**最常见词汇:**\n"
            for word, count in most_common[:10]:
                report += f"- {word}: {count}次\n"
        
        report += "\n"
        
        # 句式统计
        report += "## 句式统计\n\n"
        sentence_stats = self.statistics.get("sentence_stats", {})
        report += f"- 总句子数: {sentence_stats.get('total_sentences', 0)}\n"
        report += f"- 平均句长: {sentence_stats.get('avg_length', 0)}字\n"
        report += f"- 最长句子: {sentence_stats.get('max_length', 0)}字\n"
        report += f"- 最短句子: {sentence_stats.get('min_length', 0)}字\n\n"
        
        # 梗统计
        report += "## 梗使用统计\n\n"
        meme_stats = self.statistics.get("meme_stats", {})
        meme_counts = meme_stats.get("meme_counts", {})
        
        for meme, count in meme_counts.items():
            report += f"- {meme}: {count}次\n"
        
        report += "\n"
        
        # 过度使用警告
        overuse = self.check_overuse()
        if overuse.get("has_overuse"):
            report += "## ⚠️ 过度使用警告\n\n"
            for warning in overuse.get("warnings", []):
                report += f"- {warning}\n"
            report += "\n"
        
        return report


# 全局实例
_diversity_report = None


def get_diversity_report() -> DiversityReport:
    """获取全局多样性报告实例（单例模式）"""
    global _diversity_report
    if _diversity_report is None:
        _diversity_report = DiversityReport()
    return _diversity_report
