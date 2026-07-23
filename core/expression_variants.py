"""
表达变体库(ExpressionVariants)

核心职责:
- 对常见表达建立多个变体（如"震惊"→[愕然、瞳孔微缩、倒吸一口凉气...])
- 每次生成时随机选择变体，避免重复
- 重复检测器：统计最近N章中每个词汇的使用频率，超标则强制替换

工作流程:
加载变体数据 → 获取变体 → 检查重复 → 建议替换

设计思路:
- 使用JSON文件存储变体数据
- 支持动态添加新变体
- 统计最近N章的词汇使用频率
- 超过阈值则建议替换

输出格式:
{
    "variant": 选择的变体,
    "alternatives": [其他可选变体],
    "usage_count": 使用次数
}
"""

import json
import os
import sys
import random
from typing import Dict, List, Any, Optional
from collections import Counter
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class ExpressionVariants:
    """
    表达变体库类
    
    核心功能:
    1. 变体管理：加载、保存、添加变体
    2. 变体获取：随机选择一个变体
    3. 重复检测：统计词汇使用频率
    4. 替换建议：超标时建议替换
    
    使用场景:
    - 写手生成章节时，获取表达变体
    - 审计员检查重复度
    - 避免词汇过度使用
    
    使用流程:
    1. 初始化时加载变体数据
    2. 调用get_variant(base_expression)获取变体
    3. 调用check_repetition(recent_chapters)检查重复
    4. 调用suggest_replacement()获取替换建议
    """
    
    # 默认变体数据（如果JSON文件不存在）
    DEFAULT_VARIANTS = {
        "震惊": ["愕然", "瞳孔微缩", "倒吸一口凉气", "目瞪口呆", "大吃一惊", "惊愕", "震撼"],
        "高兴": ["欣喜", "愉悦", "欢喜", "喜出望外", "心花怒放", "欢天喜地", "乐不可支"],
        "生气": ["愤怒", "恼火", "怒火中烧", "勃然大怒", "气急败坏", "怒发冲冠", "火冒三丈"],
        "悲伤": ["哀伤", "悲痛", "伤心欲绝", "泪如雨下", "悲痛欲绝", "肝肠寸断", "痛不欲生"],
        "害怕": ["恐惧", "惊恐", "胆战心惊", "毛骨悚然", "惶恐不安", "心惊胆战", "战战兢兢"],
        "思考": ["沉思", "思索", "深思熟虑", "冥思苦想", "绞尽脑汁", "苦思冥想", "反复琢磨"],
        "快速": ["迅速", "飞快", "疾速", "风驰电掣", "闪电般", "瞬息之间", "转瞬即逝"],
        "慢慢": ["缓缓", "徐徐", "逐渐", "渐渐", "一步一步", "慢条斯理", "不紧不慢"],
        "大声": ["高声", "扬声", "震耳欲聋", "声如洪钟", "响彻云霄", "放声", "高亢"],
        "小声": ["低声", "轻声", "细声细气", "呢喃", "窃窃私语", "压低声音", "轻声细语"],
        "美丽": ["漂亮", "绝美", "惊艳", "倾国倾城", "貌美如花", "楚楚动人", "美轮美奂"],
        "丑陋": ["难看", "丑陋不堪", "面目可憎", "奇丑无比", "丑陋至极", "不堪入目", "惨不忍睹"],
        "强大": ["强悍", "无敌", "所向披靡", "势不可挡", "无人能敌", "傲视群雄", "独霸天下"],
        "弱小": ["脆弱", "不堪一击", "弱不禁风", "手无缚鸡之力", "微不足道", "渺小", "卑微"],
        "聪明": ["智慧", "睿智", "机智过人", "聪慧异常", "才智超群", "足智多谋", "精明能干"],
        "愚蠢": ["笨拙", "愚昧", "愚不可及", "愚蠢至极", "脑子进水", "糊涂透顶", "愚钝"]
    }
    
    def __init__(self):
        """
        初始化表达变体库
        
        初始化流程:
        1. 加载变体数据（从JSON文件或默认数据）
        2. 初始化使用统计
        """
        self.variants = self._load_variants()
        self.usage_stats = {}  # 词汇累计使用次数（基础表达 -> 次数）
        self.usage_history = {}  # 词汇使用历史（基础表达 -> [已使用的变体列表]），用于去重选择
    
    def _load_variants(self) -> Dict[str, List[str]]:
        """
        加载变体数据
        
        实现逻辑:
        1. 检查JSON文件是否存在
        2. 存在则加载，不存在则使用默认数据
        
        Returns:
            变体字典
        """
        variants_file = os.path.join(config.DATA_DIR, "expression_variants.json")
        
        if os.path.exists(variants_file):
            try:
                with open(variants_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载变体数据失败: {e}")
                return self.DEFAULT_VARIANTS.copy()
        else:
            # 创建默认数据文件
            self._save_variants(self.DEFAULT_VARIANTS)
            return self.DEFAULT_VARIANTS.copy()
    
    def _save_variants(self, variants: Dict[str, List[str]]):
        """
        保存变体数据到JSON文件
        
        Args:
            variants: 变体字典
        """
        variants_file = os.path.join(config.DATA_DIR, "expression_variants.json")
        os.makedirs(os.path.dirname(variants_file), exist_ok=True)
        
        try:
            with open(variants_file, 'w', encoding='utf-8') as f:
                json.dump(variants, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存变体数据失败: {e}")
    
    def get_variant(self, base_expression: str) -> Dict[str, Any]:
        """
        获取表达变体

        实现逻辑:
        1. 查找基础表达的变体列表
        2. 优先选择本轮会话中尚未使用过的变体（避免重复）
        3. 若所有变体均已使用，则回退到随机选择
        4. 更新使用统计

        Args:
            base_expression: 基础表达（如"震惊"）

        Returns:
            变体结果字典，结构如下:
            {
                "base": 基础表达,
                "variant": 选中的变体,
                "alternatives": 其他可选变体列表,
                "usage_count": 该基础表达在本会话中的累计使用次数
            }
        """
        variants_list = self.variants.get(base_expression, [base_expression])

        if not variants_list:
            selected_variant = base_expression
        else:
            # 找出本轮会话中尚未使用过的变体，优先挑选以降低重复率
            used_variants = set(self.usage_history.get(base_expression, []))
            unused_variants = [v for v in variants_list if v not in used_variants]
            if unused_variants:
                selected_variant = random.choice(unused_variants)
            else:
                # 所有变体都已使用过，回退到随机选择
                selected_variant = random.choice(variants_list)

        # 更新使用统计（累计次数）
        self.usage_stats[base_expression] = self.usage_stats.get(base_expression, 0) + 1

        # 记录使用历史，供后续 get_variant 去重参考
        if base_expression not in self.usage_history:
            self.usage_history[base_expression] = []
        self.usage_history[base_expression].append(selected_variant)

        return {
            "base": base_expression,
            "variant": selected_variant,
            "alternatives": [v for v in variants_list if v != selected_variant],
            "usage_count": self.usage_stats[base_expression]
        }
    
    def check_repetition(self, recent_chapters: List[str],
                        window_size: int = None) -> Dict[str, Any]:
        """
        检查重复度（统计最近N章的词汇使用频率）
        
        实现逻辑:
        1. 统计最近N章中每个词汇的使用频率
        2. 超过阈值则标记为重复
        
        Args:
            recent_chapters: 最近章节内容列表
            window_size: 统计窗口大小（默认使用config.VARIETY_WINDOW_SIZE）
        
        Returns:
            重复检测结果字典
        """
        if window_size is None:
            window_size = config.VARIETY_WINDOW_SIZE
        
        # 只统计最近window_size章
        recent_chapters = recent_chapters[-window_size:]
        
        # 统计词汇频率
        word_counts = Counter()
        for chapter in recent_chapters:
            # 简单分词（实际应该使用jieba等分词工具）
            words = self._simple_tokenize(chapter)
            word_counts.update(words)
        
        # 检查超过阈值的词汇
        overused_words = []
        for word, count in word_counts.items():
            if count > config.EXPRESSION_REPEAT_THRESHOLD:
                overused_words.append({
                    "word": word,
                    "count": count,
                    "threshold": config.EXPRESSION_REPEAT_THRESHOLD
                })
        
        return {
            "is_overused": len(overused_words) > 0,
            "overused_words": overused_words,
            "window_size": window_size,
            "total_chapters": len(recent_chapters)
        }
    
    def _simple_tokenize(self, text: str) -> List[str]:
        """
        简单分词（启发式方法）
        
        实现逻辑:
        1. 提取中文词汇（2-4字）
        2. 过滤停用词
        
        Args:
            text: 输入文本
        
        Returns:
            词汇列表
        """
        import re
        # 提取2-4字的中文词汇
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
        
        # 过滤停用词
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一"}
        words = [w for w in words if w not in stop_words]
        
        return words
    
    def suggest_replacement(self, word: str) -> Dict[str, Any]:
        """
        建议替换（当词汇过度使用时）
        
        实现逻辑:
        1. 查找该词的变体
        2. 返回未使用过的变体
        
        Args:
            word: 需要替换的词汇
        
        Returns:
            替换建议字典
        """
        variants_list = self.variants.get(word, [])
        
        if not variants_list:
            return {
                "word": word,
                "suggestion": word,
                "alternatives": [],
                "note": "无可用变体"
            }
        
        # 随机选择一个变体
        suggestion = random.choice(variants_list)
        alternatives = [v for v in variants_list if v != suggestion]
        
        return {
            "word": word,
            "suggestion": suggestion,
            "alternatives": alternatives,
            "note": f"建议将'{word}'替换为'{suggestion}'"
        }
    
    def add_variant(self, base_expression: str, new_variant: str) -> bool:
        """
        添加新变体
        
        Args:
            base_expression: 基础表达
            new_variant: 新变体
        
        Returns:
            是否添加成功
        """
        if base_expression not in self.variants:
            self.variants[base_expression] = []
        
        if new_variant not in self.variants[base_expression]:
            self.variants[base_expression].append(new_variant)
            self._save_variants(self.variants)
            return True
        
        return False
    
    def get_all_variants(self) -> Dict[str, List[str]]:
        """
        获取所有变体
        
        Returns:
            变体字典
        """
        return self.variants.copy()
    
    def reset_usage_stats(self):
        """
        重置使用统计和使用历史

        使用场景:
        - 新章节开始生成前，清空上一轮的变体选择记录
        - 使 get_variant 重新从"未使用"变体中挑选
        """
        self.usage_stats.clear()
        self.usage_history.clear()


# 全局实例
_expression_variants = None


def get_expression_variants() -> ExpressionVariants:
    """获取全局表达变体库实例（单例模式）"""
    global _expression_variants
    if _expression_variants is None:
        _expression_variants = ExpressionVariants()
    return _expression_variants
