"""
对话数据库参考机制(DialogueDatabase)

核心职责:
- 配置对话数据库作为参考资源，不直接检索内容
- 实现思考机制：分析对话内容以影响叙事逻辑
- 创建透明的推理过程，展示数据库参考如何影响小说内容生成

工作流程:
记录对话 → 分析对话 → 提取叙事逻辑 → 影响内容生成 → 展示推理过程

设计思路:
- 采用"分析-推理"策略，不直接复制对话内容
- 使用JSON文件存储对话历史
- 通过LLM分析对话，提取叙事逻辑
- 生成透明的推理报告

输出格式:
{
    "dialogue_analysis": 对话分析结果,
    "narrative_logic": 叙事逻辑,
    "reasoning_process": 推理过程,
    "influence_on_generation": 对生成的影响
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


class DialogueDatabase:
    """
    对话数据库参考机制类
    
    核心功能:
    1. 对话记录：存储用户对话历史
    2. 对话分析：分析对话内容，提取叙事逻辑
    3. 推理过程：生成透明的推理报告
    4. 影响生成：基于分析结果影响内容生成
    
    使用场景:
    - 记录用户与系统的对话
    - 分析用户偏好和叙事逻辑
    - 影响后续内容生成
    
    使用流程:
    1. 调用record_dialogue(dialogue)记录对话
    2. 调用analyze_dialogues()分析对话
    3. 调用get_narrative_logic()获取叙事逻辑
    4. 调用get_reasoning_report()获取推理报告
    """
    
    def __init__(self):
        """
        初始化对话数据库
        
        初始化流程:
        1. 获取LLM客户端
        2. 加载对话历史
        """
        self.llm_client = get_llm_client()
        self.dialogues = self._load_dialogues()
        self.analysis_results = []
    
    def _load_dialogues(self) -> List[Dict[str, Any]]:
        """
        加载对话历史
        
        Returns:
            对话列表
        """
        dialogue_file = os.path.join(config.DATA_DIR, "dialogue_database.json")
        
        if os.path.exists(dialogue_file):
            try:
                with open(dialogue_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载对话历史失败: {e}")
        
        return []
    
    def _save_dialogues(self):
        """
        保存对话历史到JSON文件
        """
        dialogue_file = os.path.join(config.DATA_DIR, "dialogue_database.json")
        os.makedirs(os.path.dirname(dialogue_file), exist_ok=True)
        
        try:
            with open(dialogue_file, 'w', encoding='utf-8') as f:
                json.dump(self.dialogues, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存对话历史失败: {e}")
    
    def record_dialogue(self, user_message: str, 
                       assistant_response: str = None,
                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        记录对话
        
        Args:
            user_message: 用户消息
            assistant_response: 助手回复（可选）
            context: 上下文信息（可选）
        
        Returns:
            记录的对话字典
        """
        dialogue = {
            "user_message": user_message,
            "assistant_response": assistant_response,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "dialogue_id": len(self.dialogues) + 1
        }
        
        self.dialogues.append(dialogue)
        self._save_dialogues()
        
        return dialogue
    
    def analyze_dialogues(self, recent_count: int = 10) -> Dict[str, Any]:
        """
        分析对话内容，提取叙事逻辑
        
        实现逻辑:
        1. 获取最近N条对话
        2. 使用LLM分析对话内容
        3. 提取叙事逻辑和偏好
        4. 生成分析结果
        
        Args:
            recent_count: 分析最近多少条对话（默认10条）
        
        Returns:
            分析结果字典
        """
        # 获取最近对话
        recent_dialogues = self.dialogues[-recent_count:]
        
        if not recent_dialogues:
            return {
                "analyzed": False,
                "reason": "无对话记录",
                "narrative_logic": {},
                "reasoning_process": ""
            }
        
        # 构造对话文本
        dialogue_text = ""
        for i, dialogue in enumerate(recent_dialogues, 1):
            dialogue_text += f"\n对话{i}:\n"
            dialogue_text += f"用户: {dialogue.get('user_message', '')}\n"
            if dialogue.get('assistant_response'):
                dialogue_text += f"助手: {dialogue['assistant_response']}\n"
        
        # 使用LLM分析
        prompt = f"""分析以下对话内容，提取叙事逻辑和用户偏好。

对话内容:
{dialogue_text}

请分析:
1. 用户偏好的叙事风格
2. 用户喜欢的剧情类型
3. 用户偏好的角色类型
4. 用户偏好的情感表达
5. 用户的创作意图
6. 可以提取的叙事逻辑

以JSON格式返回:
{{
    "narrative_style": "叙事风格",
    "plot_preferences": ["剧情偏好"],
    "character_preferences": ["角色偏好"],
    "emotion_preferences": ["情感偏好"],
    "creative_intent": "创作意图",
    "narrative_logic": {{
        "pacing": "节奏逻辑",
        "conflict": "冲突逻辑",
        "character_arc": "角色成长逻辑",
        "theme": "主题逻辑"
    }},
    "reasoning_process": "推理过程说明"
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            analysis = json.loads(response)
            
            # 保存分析结果
            self.analysis_results.append({
                "analysis": analysis,
                "dialogue_count": len(recent_dialogues),
                "analyzed_at": datetime.now().isoformat()
            })
            
            return {
                "analyzed": True,
                "dialogue_count": len(recent_dialogues),
                "analysis": analysis,
                "narrative_logic": analysis.get("narrative_logic", {}),
                "reasoning_process": analysis.get("reasoning_process", "")
            }
        except Exception as e:
            print(f"分析对话失败: {e}")
            return {
                "analyzed": False,
                "reason": str(e),
                "narrative_logic": {},
                "reasoning_process": ""
            }
    
    def get_narrative_logic(self) -> Dict[str, Any]:
        """
        获取叙事逻辑（基于最近的对话分析）
        
        Returns:
            叙事逻辑字典
        """
        if not self.analysis_results:
            # 如果没有分析结果，先分析
            analysis = self.analyze_dialogues()
            return analysis.get("narrative_logic", {})
        
        # 返回最近的分析结果
        latest_analysis = self.analysis_results[-1]
        return latest_analysis.get("analysis", {}).get("narrative_logic", {})
    
    def get_reasoning_report(self) -> str:
        """
        生成推理报告（展示数据库参考如何影响生成）
        
        Returns:
            Markdown格式的推理报告
        """
        report = "# 对话数据库推理报告\n\n"
        
        if not self.analysis_results:
            report += "暂无分析结果。请先记录和分析对话。\n"
            return report
        
        # 统计信息
        total_dialogues = len(self.dialogues)
        total_analyses = len(self.analysis_results)
        report += f"## 统计信息\n\n"
        report += f"- 总对话数: {total_dialogues}\n"
        report += f"- 分析次数: {total_analyses}\n\n"
        
        # 最近分析
        latest = self.analysis_results[-1]
        analysis = latest.get("analysis", {})
        
        report += "## 最近分析结果\n\n"
        report += f"**分析时间**: {latest.get('analyzed_at', '未知')}\n"
        report += f"**分析对话数**: {latest.get('dialogue_count', 0)}\n\n"
        
        # 叙事风格
        narrative_style = analysis.get("narrative_style", "未知")
        report += f"### 叙事风格\n{narrative_style}\n\n"
        
        # 剧情偏好
        plot_prefs = analysis.get("plot_preferences", [])
        if plot_prefs:
            report += "### 剧情偏好\n"
            for pref in plot_prefs:
                report += f"- {pref}\n"
            report += "\n"
        
        # 角色偏好
        char_prefs = analysis.get("character_preferences", [])
        if char_prefs:
            report += "### 角色偏好\n"
            for pref in char_prefs:
                report += f"- {pref}\n"
            report += "\n"
        
        # 叙事逻辑
        narrative_logic = analysis.get("narrative_logic", {})
        if narrative_logic:
            report += "### 叙事逻辑\n"
            for key, value in narrative_logic.items():
                report += f"- **{key}**: {value}\n"
            report += "\n"
        
        # 推理过程
        reasoning = analysis.get("reasoning_process", "")
        if reasoning:
            report += "### 推理过程\n"
            report += f"{reasoning}\n\n"
        
        # 对生成的影响
        report += "## 对内容生成的影响\n\n"
        report += "基于以上分析，系统在生成内容时会：\n"
        if narrative_style:
            report += f"1. 采用{ narrative_style}的叙事风格\n"
        if plot_prefs:
            report += f"2. 优先使用用户偏好的剧情类型\n"
        if char_prefs:
            report += f"3. 设计符合用户偏好的角色\n"
        if narrative_logic:
            report += f"4. 遵循提取的叙事逻辑\n"
        
        return report
    
    def get_dialogue_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        Args:
            limit: 返回条数限制（可选）
        
        Returns:
            对话列表
        """
        if limit:
            return self.dialogues[-limit:]
        return self.dialogues.copy()
    
    def clear_dialogues(self):
        """
        清空对话历史
        """
        self.dialogues.clear()
        self.analysis_results.clear()
        self._save_dialogues()


# 全局实例
_dialogue_database = None


def get_dialogue_database() -> DialogueDatabase:
    """获取全局对话数据库实例（单例模式）"""
    global _dialogue_database
    if _dialogue_database is None:
        _dialogue_database = DialogueDatabase()
    return _dialogue_database
