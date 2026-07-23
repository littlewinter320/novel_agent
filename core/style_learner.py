"""
风格学习器(StyleLearner)

核心职责:
- 3个学习渠道：用户上传的参考文本、用户对生成内容的修改、用户的对话风格
- 学习内容：词汇偏好、句式偏好、节奏偏好、情感偏好、禁忌清单
- "轻微改动"原则：保持60%多样性，40%适应用户偏好
- 每10章输出"风格学习报告"

工作流程:
接收学习数据 → 分析风格特征 → 更新风格指南 → 生成学习报告

设计思路:
- 采用"渐进学习"策略，每次学习只微调风格参数
- 保持60%多样性，避免过度拟合
- 使用JSON文件持久化学习结果
- 定期生成学习报告，让用户了解学习进度

输出格式:
{
    "learned_style": 学习到的风格,
    "style_guide": 更新的风格指南,
    "learning_progress": 学习进度,
    "report": 学习报告
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
from agents.style_engineer import get_style_engineer_agent


class StyleLearner:
    """
    风格学习器类
    
    核心功能:
    1. 参考文本学习：从用户上传的参考文本中学习风格
    2. 修改学习：从用户对生成内容的修改中学习偏好
    3. 对话学习：从用户的对话风格中学习
    4. 风格指南更新：基于学习结果更新风格指南
    5. 学习报告：定期生成学习报告
    
    使用场景:
    - 用户上传参考文本，需要学习其风格
    - 用户修改生成内容，需要学习其偏好
    - 长期学习用户的写作风格
    
    使用流程:
    1. 调用learn_from_reference(text)学习参考文本
    2. 调用learn_from_modification(old, new)学习修改
    3. 调用learn_from_dialogue(message)学习对话风格
    4. 调用get_style_guide()获取更新的风格指南
    5. 调用get_learning_report()获取学习报告
    """
    
    def __init__(self):
        """
        初始化风格学习器
        
        初始化流程:
        1. 获取LLM客户端
        2. 获取文风工程师实例
        3. 加载学习数据
        """
        self.llm_client = get_llm_client()
        self.style_engineer = get_style_engineer_agent()
        self.learning_data = self._load_learning_data()
    
    def _load_learning_data(self) -> Dict[str, Any]:
        """
        加载学习数据
        
        Returns:
            学习数据字典
        """
        learning_file = os.path.join(config.MEMORY_DIR, "style_learning.json")
        
        if os.path.exists(learning_file):
            try:
                with open(learning_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载学习数据失败: {e}")
        
        # 默认学习数据
        return {
            "vocabulary_preferences": {},  # 词汇偏好
            "sentence_preferences": {},    # 句式偏好
            "rhythm_preferences": {},      # 节奏偏好
            "emotion_preferences": {},     # 情感偏好
            "taboo_list": [],              # 禁忌清单
            "learning_count": 0,           # 学习次数
            "last_report_chapter": 0,      # 上次报告章节
            "learned_at": None
        }
    
    def _save_learning_data(self):
        """
        保存学习数据到JSON文件
        """
        learning_file = os.path.join(config.MEMORY_DIR, "style_learning.json")
        os.makedirs(os.path.dirname(learning_file), exist_ok=True)
        
        try:
            with open(learning_file, 'w', encoding='utf-8') as f:
                json.dump(self.learning_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存学习数据失败: {e}")
    
    def learn_from_reference(self, reference_text: str) -> Dict[str, Any]:
        """
        从参考文本中学习风格
        
        实现逻辑:
        1. 使用文风工程师分析参考文本
        2. 提取风格特征
        3. 更新学习数据（轻微改动原则）
        4. 保存学习数据
        
        Args:
            reference_text: 参考文本
        
        Returns:
            学习结果字典
        """
        # 1. 分析参考文本
        analysis_result = self.style_engineer.analyze_writing_style(reference_text)
        fingerprint = analysis_result.get("fingerprint", {})
        style_guide = analysis_result.get("style_guide", {})
        
        # 2. 更新学习数据（轻微改动原则）
        self._update_learning_data(fingerprint, style_guide, weight=0.4)
        
        # 3. 增加学习次数
        self.learning_data["learning_count"] += 1
        self.learning_data["learned_at"] = datetime.now().isoformat()
        
        # 4. 保存学习数据
        self._save_learning_data()
        
        return {
            "learned": True,
            "source": "reference_text",
            "learning_count": self.learning_data["learning_count"],
            "style_guide": self.get_style_guide()
        }
    
    def learn_from_modification(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """
        从用户修改中学习偏好
        
        实现逻辑:
        1. 对比修改前后的内容
        2. 提取用户的修改偏好
        3. 更新学习数据（轻微改动原则）
        4. 保存学习数据
        
        Args:
            old_content: 修改前的内容
            new_content: 修改后的内容
        
        Returns:
            学习结果字典
        """
        # 1. 使用LLM分析修改
        prompt = f"""分析用户对以下内容的修改，提取用户的写作偏好。

修改前:
{old_content[:1000]}...

修改后:
{new_content[:1000]}...

请分析:
1. 用户修改了哪些方面（词汇、句式、节奏、情感表达等）
2. 用户的偏好是什么
3. 用户不喜欢什么

以JSON格式返回:
{{
    "modifications": ["修改点1", "修改点2"],
    "preferences": {{
        "vocabulary": ["词汇偏好"],
        "sentence": ["句式偏好"],
        "rhythm": ["节奏偏好"],
        "emotion": ["情感偏好"]
    }},
    "dislikes": ["不喜欢的方面"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            analysis = json.loads(response)
            
            # 2. 更新学习数据
            preferences = analysis.get("preferences", {})
            dislikes = analysis.get("dislikes", [])
            
            # 更新词汇偏好
            for word in preferences.get("vocabulary", []):
                self.learning_data["vocabulary_preferences"][word] = \
                    self.learning_data["vocabulary_preferences"].get(word, 0) + 1
            
            # 更新句式偏好
            for pattern in preferences.get("sentence", []):
                self.learning_data["sentence_preferences"][pattern] = \
                    self.learning_data["sentence_preferences"].get(pattern, 0) + 1
            
            # 更新节奏偏好
            for rhythm in preferences.get("rhythm", []):
                self.learning_data["rhythm_preferences"][rhythm] = \
                    self.learning_data["rhythm_preferences"].get(rhythm, 0) + 1
            
            # 更新情感偏好
            for emotion in preferences.get("emotion", []):
                self.learning_data["emotion_preferences"][emotion] = \
                    self.learning_data["emotion_preferences"].get(emotion, 0) + 1
            
            # 更新禁忌清单
            for dislike in dislikes:
                if dislike not in self.learning_data["taboo_list"]:
                    self.learning_data["taboo_list"].append(dislike)
            
            # 3. 增加学习次数
            self.learning_data["learning_count"] += 1
            self.learning_data["learned_at"] = datetime.now().isoformat()
            
            # 4. 保存学习数据
            self._save_learning_data()
            
            return {
                "learned": True,
                "source": "modification",
                "modifications": analysis.get("modifications", []),
                "learning_count": self.learning_data["learning_count"],
                "style_guide": self.get_style_guide()
            }
        except Exception as e:
            print(f"从修改中学习失败: {e}")
            return {
                "learned": False,
                "error": str(e)
            }
    
    def learn_from_dialogue(self, message: str) -> Dict[str, Any]:
        """
        从用户对话风格中学习
        
        实现逻辑:
        1. 分析用户的对话风格
        2. 提取风格特征
        3. 更新学习数据（轻微改动原则）
        4. 保存学习数据
        
        Args:
            message: 用户对话消息
        
        Returns:
            学习结果字典
        """
        # 使用LLM分析对话风格
        prompt = f"""分析以下用户对话的风格特征。

用户对话: {message}

请分析:
1. 对话风格（正式/随意/幽默/严肃等）
2. 用词特点
3. 句式特点
4. 情感表达特点

以JSON格式返回:
{{
    "style": "对话风格",
    "vocabulary_features": ["用词特点"],
    "sentence_features": ["句式特点"],
    "emotion_features": ["情感表达特点"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            analysis = json.loads(response)
            
            # 更新学习数据（权重较低，因为对话风格不一定反映写作风格）
            style = analysis.get("style", "")
            if style:
                self.learning_data["vocabulary_preferences"][f"对话风格:{style}"] = \
                    self.learning_data["vocabulary_preferences"].get(f"对话风格:{style}", 0) + 0.5
            
            # 增加学习次数
            self.learning_data["learning_count"] += 1
            self.learning_data["learned_at"] = datetime.now().isoformat()
            
            # 保存学习数据
            self._save_learning_data()
            
            return {
                "learned": True,
                "source": "dialogue",
                "style": style,
                "learning_count": self.learning_data["learning_count"]
            }
        except Exception as e:
            print(f"从对话中学习失败: {e}")
            return {
                "learned": False,
                "error": str(e)
            }
    
    def _update_learning_data(self, fingerprint: Dict[str, Any],
                             style_guide: Dict[str, Any],
                             weight: float = 0.4):
        """
        更新学习数据（轻微改动原则）
        
        实现逻辑:
        1. 保持60%原有风格
        2. 40%适应新学习的内容
        3. 使用加权平均更新偏好
        
        Args:
            fingerprint: 文笔指纹
            style_guide: 风格指南
            weight: 新内容的权重（默认0.4）
        """
        # 更新词汇偏好
        top_words = fingerprint.get("top_words", [])
        for word_info in top_words[:10]:
            word = word_info.get("word", "")
            count = word_info.get("count", 0)
            if word:
                old_value = self.learning_data["vocabulary_preferences"].get(word, 0)
                # 加权平均：60%原有 + 40%新学习
                new_value = old_value * (1 - weight) + count * weight
                self.learning_data["vocabulary_preferences"][word] = new_value
        
        # 更新句式偏好
        avg_sentence_length = fingerprint.get("sentence_length", {}).get("average", 20)
        old_avg = self.learning_data["sentence_preferences"].get("average_length", 20)
        new_avg = old_avg * (1 - weight) + avg_sentence_length * weight
        self.learning_data["sentence_preferences"]["average_length"] = new_avg
        
        # 更新节奏偏好
        dialogue_ratio = fingerprint.get("dialogue_ratio", 0)
        old_ratio = self.learning_data["rhythm_preferences"].get("dialogue_ratio", 0)
        new_ratio = old_ratio * (1 - weight) + dialogue_ratio * weight
        self.learning_data["rhythm_preferences"]["dialogue_ratio"] = new_ratio
        
        # 更新风格指南中的必须做和禁止做
        must_do = style_guide.get("must_do", [])
        forbidden = style_guide.get("forbidden_patterns", [])
        
        # 合并到学习数据（去重）
        for item in must_do:
            if item not in self.learning_data.get("must_do", []):
                if "must_do" not in self.learning_data:
                    self.learning_data["must_do"] = []
                self.learning_data["must_do"].append(item)
        
        for item in forbidden:
            if item not in self.learning_data.get("forbidden_patterns", []):
                if "forbidden_patterns" not in self.learning_data:
                    self.learning_data["forbidden_patterns"] = []
                self.learning_data["forbidden_patterns"].append(item)
    
    def get_style_guide(self) -> Dict[str, Any]:
        """
        获取更新的风格指南
        
        Returns:
            风格指南字典
        """
        # 基于学习数据生成风格指南
        style_guide = {
            "tone": "基于学习数据",
            "pov": "第三人称",
            "must_do": self.learning_data.get("must_do", []),
            "forbidden_patterns": self.learning_data.get("forbidden_patterns", []) + 
                               self.learning_data.get("taboo_list", []),
            "style_params": {
                "target_sentence_length": {
                    "average": self.learning_data["sentence_preferences"].get("average_length", 20)
                },
                "target_dialogue_ratio": {
                    "target": self.learning_data["rhythm_preferences"].get("dialogue_ratio", 0.2)
                }
            },
            "vocabulary_preferences": self.learning_data.get("vocabulary_preferences", {}),
            "learned_at": self.learning_data.get("learned_at")
        }
        
        return style_guide
    
    def get_learning_report(self, current_chapter: int = None) -> str:
        """
        生成学习报告
        
        Args:
            current_chapter: 当前章节号（可选）
        
        Returns:
            Markdown格式的学习报告
        """
        report = "# 风格学习报告\n\n"
        
        # 学习统计
        learning_count = self.learning_data.get("learning_count", 0)
        report += f"## 学习统计\n\n"
        report += f"- 总学习次数: {learning_count}\n"
        report += f"- 上次学习时间: {self.learning_data.get('learned_at', '从未')}\n\n"
        
        # 词汇偏好
        vocab_prefs = self.learning_data.get("vocabulary_preferences", {})
        if vocab_prefs:
            report += "## 词汇偏好\n\n"
            sorted_vocab = sorted(vocab_prefs.items(), key=lambda x: x[1], reverse=True)[:10]
            for word, score in sorted_vocab:
                report += f"- {word}: {score:.2f}\n"
            report += "\n"
        
        # 句式偏好
        sentence_prefs = self.learning_data.get("sentence_preferences", {})
        if sentence_prefs:
            report += "## 句式偏好\n\n"
            avg_length = sentence_prefs.get("average_length", 20)
            report += f"- 平均句长: {avg_length:.1f}字\n\n"
        
        # 节奏偏好
        rhythm_prefs = self.learning_data.get("rhythm_preferences", {})
        if rhythm_prefs:
            report += "## 节奏偏好\n\n"
            dialogue_ratio = rhythm_prefs.get("dialogue_ratio", 0)
            report += f"- 对话占比: {dialogue_ratio*100:.1f}%\n\n"
        
        # 禁忌清单
        taboo_list = self.learning_data.get("taboo_list", [])
        if taboo_list:
            report += "## 禁忌清单\n\n"
            for taboo in taboo_list:
                report += f"- {taboo}\n"
            report += "\n"
        
        # 更新章节号
        if current_chapter is not None:
            self.learning_data["last_report_chapter"] = current_chapter
            self._save_learning_data()
        
        return report
    
    def should_generate_report(self, current_chapter: int) -> bool:
        """
        判断是否应该生成学习报告
        
        Args:
            current_chapter: 当前章节号
        
        Returns:
            是否应该生成报告
        """
        last_report = self.learning_data.get("last_report_chapter", 0)
        return (current_chapter - last_report) >= config.STYLE_LEARN_REPORT_INTERVAL


# 全局实例
_style_learner = None


def get_style_learner() -> StyleLearner:
    """获取全局风格学习器实例（单例模式）"""
    global _style_learner
    if _style_learner is None:
        _style_learner = StyleLearner()
    return _style_learner
