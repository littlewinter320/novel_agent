"""
Skill引擎(SkillEngine)

核心职责:
- 自动创建Skill：完成复杂任务后自动封装为可复用Skill
- 使用中自改进：记录效果反馈，连续不满意则自动调整
- Skill检索：新任务开始时自动检索匹配的Skill

工作流程:
任务完成 → 自动创建Skill → 检索匹配Skill → 应用Skill → 记录反馈 → 自改进

设计思路:
- 与SkillLibrary联动
- 支持自动创建和改进
- 支持反馈驱动的自我改进

输出格式:
{
    "skill_id": Skill ID,
    "skill_name": Skill名称,
    "success_rate": 成功率,
    "feedback_count": 反馈次数
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
from core.skill_library import get_skill_library


class SkillEngine:
    """
    Skill引擎类
    
    核心功能:
    1. 自动创建Skill：从任务结果中提取可复用模式
    2. 使用中自改进：根据反馈调整Skill
    3. Skill检索：匹配最合适的Skill
    
    使用场景:
    - 完成复杂任务后，自动创建Skill
    - 新任务开始时，检索匹配的Skill
    - 使用Skill后，记录反馈并改进
    
    使用流程:
    1. 调用auto_create_skill(task_result)自动创建
    2. 调用search_matching_skill(task_description)检索
    3. 调用apply_skill(skill_id)应用
    4. 调用improve_skill(skill_id, feedback)改进
    """
    
    def __init__(self):
        """
        初始化Skill引擎
        
        初始化流程:
        1. 获取SkillLibrary实例
        """
        self.skill_library = get_skill_library()
    
    def auto_create_skill(self, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        自动创建Skill（核心方法）
        
        实现逻辑:
        1. 分析任务结果，提取关键模式
        2. 生成Skill定义
        3. 保存到SkillLibrary
        
        Args:
            task_result: 任务结果字典
        
        Returns:
            创建结果字典
        """
        # 提取任务信息
        task_description = task_result.get("task_description", "")
        steps = task_result.get("steps", [])
        success = task_result.get("success", True)
        
        if not task_description or not steps:
            return {
                "created": False,
                "error": "缺少任务描述或步骤信息"
            }
        
        # 生成Skill ID和名称
        skill_id = f"auto_skill_{len(self.skill_library.list_skills()) + 1}"
        skill_name = f"自动Skill-{task_description[:20]}"
        
        # 构建Skill数据
        skill_data = {
            "skill_id": skill_id,
            "name": skill_name,
            "trigger": task_description,
            "steps": steps,
            "success_rate": 1.0 if success else 0.5,
            "user_feedback": [],
            "last_used": datetime.now().isoformat(),
            "version": 1,
            "auto_created": True
        }
        
        # 保存到SkillLibrary
        if self.skill_library.add_skill(skill_data):
            return {
                "created": True,
                "skill_id": skill_id,
                "skill_name": skill_name
            }
        else:
            return {
                "created": False,
                "error": "保存Skill失败"
            }
    
    def improve_skill(self, skill_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        改进Skill
        
        实现逻辑:
        1. 加载Skill
        2. 记录反馈
        3. 根据反馈调整Skill
        4. 保存更新
        
        Args:
            skill_id: Skill ID
            feedback: 反馈信息字典
        
        Returns:
            改进结果字典
        """
        skill = self.skill_library.get_skill(skill_id)
        if not skill:
            return {
                "improved": False,
                "error": f"Skill {skill_id} 不存在"
            }
        
        # 记录反馈
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "satisfaction": feedback.get("satisfaction", 0.5),
            "comments": feedback.get("comments", "")
        }
        
        skill["user_feedback"].append(feedback_entry)
        
        # 计算新的成功率
        if skill["user_feedback"]:
            avg_satisfaction = sum(f.get("satisfaction", 0.5) for f in skill["user_feedback"]) / len(skill["user_feedback"])
            skill["success_rate"] = avg_satisfaction
        
        # 如果连续不满意，自动调整
        recent_feedback = skill["user_feedback"][-3:]
        if len(recent_feedback) >= 3 and all(f.get("satisfaction", 0.5) < 0.3 for f in recent_feedback):
            skill["version"] += 1
            skill["needs_review"] = True
        
        # 保存更新
        self.skill_library.update_skill(skill_id, skill)
        
        return {
            "improved": True,
            "skill_id": skill_id,
            "new_success_rate": skill["success_rate"],
            "version": skill["version"]
        }
    
    def search_matching_skill(self, task_description: str) -> Optional[Dict[str, Any]]:
        """
        检索匹配的Skill
        
        实现逻辑:
        1. 使用SkillLibrary的搜索功能
        2. 返回最匹配的Skill
        
        Args:
            task_description: 任务描述
        
        Returns:
            匹配的Skill，如果没有则返回None
        """
        matching_skills = self.skill_library.search_skills(task_description)
        
        if matching_skills:
            # 返回成功率最高的
            return max(matching_skills, key=lambda s: s.get("success_rate", 0))
        
        return None
    
    def apply_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        应用Skill
        
        实现逻辑:
        1. 加载Skill
        2. 更新最后使用时间
        3. 返回Skill步骤
        
        Args:
            skill_id: Skill ID
        
        Returns:
            应用结果字典
        """
        skill = self.skill_library.get_skill(skill_id)
        if not skill:
            return {
                "applied": False,
                "error": f"Skill {skill_id} 不存在"
            }
        
        # 更新最后使用时间
        skill["last_used"] = datetime.now().isoformat()
        self.skill_library.update_skill(skill_id, skill)
        
        return {
            "applied": True,
            "skill_id": skill_id,
            "skill_name": skill.get("name"),
            "steps": skill.get("steps", [])
        }


# 全局实例
_skill_engine = None


def get_skill_engine() -> SkillEngine:
    """获取全局Skill引擎实例（单例模式）"""
    global _skill_engine
    if _skill_engine is None:
        _skill_engine = SkillEngine()
    return _skill_engine
