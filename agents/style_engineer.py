"""
文风工程师(SubAgent-StyleEngineer)

核心职责:
- 分析用户提供的参考文本
- 提取"文笔指纹"（句式长度分布、对话占比、心理描写占比、常用词汇、叙事视角等）
- 生成"风格指南"文件（JSON格式）

工作流程:
接收参考文本 → 提取文笔指纹 → 分析风格特征 → 生成风格指南

设计思路:
- 采用"统计分析 + LLM辅助"的策略
- 统计分析：句式长度、对话占比、心理描写占比等
- LLM辅助：叙事视角、情感表达风格等

关键算法:
- 句式长度分布：统计句子长度，计算平均值、中位数、标准差
- 对话占比：统计对话文本占总文本的比例
- 心理描写占比：统计心理描写文本占总文本的比例
- 常用词汇：统计高频词汇（排除停用词）
- 叙事视角：识别第一人称/第三人称/全知视角

输出格式:
{
    "fingerprint": 文笔指纹,
    "style_guide": 风格指南
}
"""

import json
import os
import re
import sys
from typing import Dict, List, Any, Optional
from collections import Counter
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.llm_client import get_llm_client


class StyleEngineerAgent:
    """
    文风工程师类
    
    核心功能:
    1. 文笔指纹提取：分析文本的统计特征
    2. 风格指南生成：基于指纹生成风格指南
    3. 风格对比：可以对比多个文本的风格差异
    
    使用场景:
    - 用户提供参考文本，需要学习其风格
    - 需要生成风格指南，指导后续创作
    - 需要分析用户写作习惯
    
    使用流程:
    1. 调用analyze_writing_style(reference_text)
    2. 内部自动提取文笔指纹
    3. 生成风格指南
    4. 返回指纹和指南
    """
    
    # 中文停用词（简化版）
    STOP_WORDS = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
        "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
        "自己", "这", "他", "她", "它", "们", "那", "些", "什么", "怎么", "为什么"
    }
    
    def __init__(self):
        """
        初始化文风工程师
        
        初始化流程:
        1. 获取LLM客户端
        """
        self.llm_client = get_llm_client()
    
    def analyze_writing_style(self, reference_text: str) -> Dict[str, Any]:
        """
        分析写作风格（核心方法）
        
        实现逻辑:
        1. 提取文笔指纹（统计特征）
        2. 使用LLM分析风格特征（叙事视角、情感表达等）
        3. 生成风格指南
        
        Args:
            reference_text: 参考文本
        
        Returns:
            分析结果字典，包含：
            - fingerprint: 文笔指纹
            - style_guide: 风格指南
        """
        # 1. 提取文笔指纹
        fingerprint = self.extract_fingerprint(reference_text)
        
        # 2. 使用LLM分析风格特征
        style_analysis = self._analyze_style_with_llm(reference_text)
        
        # 3. 生成风格指南
        style_guide = self.generate_style_guide(fingerprint, style_analysis)
        
        return {
            "fingerprint": fingerprint,
            "style_guide": style_guide,
            "analyzed_at": datetime.now().isoformat()
        }
    
    def extract_fingerprint(self, text: str) -> Dict[str, Any]:
        """
        提取文笔指纹（统计特征）
        
        实现逻辑:
        1. 句式长度分布：统计句子长度
        2. 对话占比：统计对话文本比例
        3. 心理描写占比：统计心理描写比例
        4. 常用词汇：统计高频词汇
        5. 段落长度分布：统计段落长度
        
        Args:
            text: 输入文本
        
        Returns:
            文笔指纹字典
        """
        # 1. 句式长度分布
        sentences = re.split(r'[。！？!?\n]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_lengths = [len(s) for s in sentences]
        
        avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
        median_sentence_length = sorted(sentence_lengths)[len(sentence_lengths) // 2] if sentence_lengths else 0
        
        # 2. 对话占比
        dialogue_pattern = r'[""](.*?)[""]'
        dialogues = re.findall(dialogue_pattern, text)
        dialogue_length = sum(len(d) for d in dialogues)
        dialogue_ratio = dialogue_length / len(text) if len(text) > 0 else 0
        
        # 3. 心理描写占比（简单启发式：包含"想"、"觉得"、"感到"等的句子）
        psychology_pattern = r'[^。！？]*?(想|觉得|感到|心想|思考|意识到)[^。！？]*?[。！？]'
        psychology_matches = re.findall(psychology_pattern, text)
        psychology_length = sum(len(m) for m in psychology_matches)
        psychology_ratio = psychology_length / len(text) if len(text) > 0 else 0
        
        # 4. 常用词汇（排除停用词）
        words = re.findall(r'[\u4e00-\u9fa5]+', text)  # 提取中文词汇
        words = [w for w in words if w not in self.STOP_WORDS and len(w) > 1]
        word_freq = Counter(words)
        top_words = word_freq.most_common(20)  # 前20个高频词
        
        # 5. 段落长度分布
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        paragraph_lengths = [len(p) for p in paragraphs]
        avg_paragraph_length = sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0
        
        return {
            "sentence_length": {
                "average": round(avg_sentence_length, 2),
                "median": median_sentence_length,
                "min": min(sentence_lengths) if sentence_lengths else 0,
                "max": max(sentence_lengths) if sentence_lengths else 0
            },
            "dialogue_ratio": round(dialogue_ratio, 3),
            "psychology_ratio": round(psychology_ratio, 3),
            "top_words": [{"word": w, "count": c} for w, c in top_words],
            "paragraph_length": {
                "average": round(avg_paragraph_length, 2),
                "total_paragraphs": len(paragraphs)
            },
            "total_characters": len(text),
            "total_sentences": len(sentences)
        }
    
    def _analyze_style_with_llm(self, text: str) -> Dict[str, Any]:
        """
        使用LLM分析风格特征
        
        实现逻辑:
        1. 构造提示词，要求LLM分析叙事视角、情感表达等
        2. 调用LLM生成分析结果
        
        Args:
            text: 输入文本
        
        Returns:
            风格分析结果字典
        """
        prompt = f"""分析以下文本的写作风格特征。

文本内容:
{text[:3000]}...

请从以下维度分析:
1. 叙事视角: 第一人称/第三人称/全知视角/限知视角
2. 情感表达: 直接表达/含蓄表达/混合
3. 语言风格: 简洁/华丽/幽默/严肃
4. 节奏特点: 快节奏/慢节奏/混合
5. 描写特点: 重对话/重心理/重环境/重动作
6. 文风特点: 其他显著特点

请以JSON格式返回:
{{
    "narrative_pov": "叙事视角",
    "emotion_expression": "情感表达方式",
    "language_style": "语言风格",
    "pacing": "节奏特点",
    "description_focus": "描写重点",
    "other_features": ["其他特点"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            style_analysis = json.loads(response)
            return style_analysis
        except Exception as e:
            print(f"LLM风格分析失败: {e}")
            return {}
    
    def generate_style_guide(self, fingerprint: Dict[str, Any],
                           style_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成风格指南
        
        实现逻辑:
        1. 基于文笔指纹和风格分析
        2. 生成"必须做"和"禁止做"清单
        3. 生成风格参数
        
        Args:
            fingerprint: 文笔指纹
            style_analysis: 风格分析结果
        
        Returns:
            风格指南字典
        """
        # 生成"必须做"清单
        must_do = []
        
        # 基于句式长度
        avg_sent_len = fingerprint.get("sentence_length", {}).get("average", 20)
        if avg_sent_len < 15:
            must_do.append("保持简洁的句式，平均句长控制在15字以内")
        elif avg_sent_len < 25:
            must_do.append("保持适中的句式长度，平均句长控制在15-25字")
        else:
            must_do.append("可以使用较长的句式，但要注意断句")
        
        # 基于对话占比
        dialogue_ratio = fingerprint.get("dialogue_ratio", 0)
        if dialogue_ratio > 0.3:
            must_do.append("保持较高的对话占比（30%以上）")
        elif dialogue_ratio > 0.15:
            must_do.append("保持适中的对话占比（15-30%）")
        else:
            must_do.append("对话占比较低，注意增加对话")
        
        # 基于叙事视角
        pov = style_analysis.get("narrative_pov", "未知")
        must_do.append(f"保持{pov}叙事视角")
        
        # 基于语言风格
        lang_style = style_analysis.get("language_style", "未知")
        must_do.append(f"保持{lang_style}的语言风格")
        
        # 生成"禁止做"清单
        forbidden = []
        
        # 基于高频词
        top_words = fingerprint.get("top_words", [])
        if top_words:
            overused_words = [w["word"] for w in top_words[:5]]
            forbidden.append(f"避免过度使用以下词汇: {', '.join(overused_words)}")
        
        # 通用禁止
        forbidden.append("避免使用AI常用句式（首先、其次、最后等）")
        forbidden.append("避免过度使用排比句")
        forbidden.append("避免突然切换叙事视角")
        
        # 生成风格参数
        style_params = {
            "target_sentence_length": {
                "min": 10,
                "max": 30,
                "average": avg_sent_len
            },
            "target_dialogue_ratio": {
                "min": 0.1,
                "max": 0.4,
                "target": dialogue_ratio
            },
            "target_psychology_ratio": {
                "min": 0.05,
                "max": 0.2,
                "target": fingerprint.get("psychology_ratio", 0.1)
            }
        }
        
        return {
            "tone": style_analysis.get("language_style", "未知"),
            "pov": style_analysis.get("narrative_pov", "未知"),
            "must_do": must_do,
            "forbidden_patterns": forbidden,
            "style_params": style_params,
            "other_features": style_analysis.get("other_features", [])
        }
    
    def generate_style_report(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成人类可读的风格分析报告
        
        Args:
            analysis_result: 分析结果字典
        
        Returns:
            Markdown格式的报告
        """
        report = "# 文风分析报告\n\n"
        
        # 1. 文笔指纹
        fingerprint = analysis_result.get("fingerprint", {})
        if fingerprint:
            report += "## 一、文笔指纹\n\n"
            
            # 句式长度
            sent_len = fingerprint.get("sentence_length", {})
            report += "### 句式长度\n"
            report += f"- 平均句长: {sent_len.get('average', 0)}字\n"
            report += f"- 中位数: {sent_len.get('median', 0)}字\n"
            report += f"- 最短: {sent_len.get('min', 0)}字\n"
            report += f"- 最长: {sent_len.get('max', 0)}字\n\n"
            
            # 对话占比
            dialogue_ratio = fingerprint.get("dialogue_ratio", 0)
            report += f"### 对话占比: {dialogue_ratio*100:.1f}%\n\n"
            
            # 心理描写占比
            psychology_ratio = fingerprint.get("psychology_ratio", 0)
            report += f"### 心理描写占比: {psychology_ratio*100:.1f}%\n\n"
            
            # 高频词汇
            top_words = fingerprint.get("top_words", [])
            if top_words:
                report += "### 高频词汇（前10）\n"
                for item in top_words[:10]:
                    report += f"- {item['word']}: {item['count']}次\n"
                report += "\n"
        
        # 2. 风格指南
        style_guide = analysis_result.get("style_guide", {})
        if style_guide:
            report += "## 二、风格指南\n\n"
            
            report += f"### 文风: {style_guide.get('tone', '未知')}\n"
            report += f"### 叙事视角: {style_guide.get('pov', '未知')}\n\n"
            
            must_do = style_guide.get("must_do", [])
            if must_do:
                report += "### 必须做\n"
                for item in must_do:
                    report += f"- {item}\n"
                report += "\n"
            
            forbidden = style_guide.get("forbidden_patterns", [])
            if forbidden:
                report += "### 禁止做\n"
                for item in forbidden:
                    report += f"- {item}\n"
                report += "\n"
        
        return report


# 全局实例
_style_engineer_agent = None


def get_style_engineer_agent() -> StyleEngineerAgent:
    """获取全局文风工程师实例（单例模式）"""
    global _style_engineer_agent
    if _style_engineer_agent is None:
        _style_engineer_agent = StyleEngineerAgent()
    return _style_engineer_agent
