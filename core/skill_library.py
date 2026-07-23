"""
Skill存储框架模块

核心职责：
- 管理可复用的技能模板，支持动态创建、更新、删除和检索
- 实现Skill的自学习机制：记录使用情况和成功率，自动优化Skill
- 提供按触发条件搜索Skill的功能，支持场景匹配
- 管理Skill的版本控制和用户反馈

设计思路：
- 每个Skill存储为独立的JSON文件，包含完整的元数据和执行步骤
- Skill ID采用"skill_时间戳_随机数"格式，确保唯一性
- 触发条件（trigger）支持关键词匹配，用于场景识别
- 使用统计（usage_count/success_count）用于评估Skill质量
- 用户反馈机制支持持续改进Skill

使用场景：
- MainAgent识别到特定场景时，搜索匹配的Skill
- 用户创建新的工作流程时，保存为可复用的Skill
- Skill执行后，记录使用情况和成功率
- 用户反馈Skill效果时，更新反馈记录

关键算法：
- Skill搜索：线性扫描所有Skill文件，匹配trigger中的关键词
- 成功率排序：按success_count/usage_count降序排列，优先推荐高成功率Skill
- 版本控制：每次更新Skill时version字段自增，支持版本追踪
- 反馈限制：每个Skill最多保留20条反馈，避免文件过大

Skill数据结构：
{
    "skill_id": "skill_20260722120000_a1b2c3d4",
    "name": "Skill名称",
    "trigger": "触发条件关键词",
    "steps": ["步骤1", "步骤2", "步骤3"],
    "description": "Skill描述",
    "category": "分类（general/outline/character/plot/style等）",
    "version": 1,
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "usage_count": 0,
    "success_count": 0,
    "user_feedback": [],
    "last_used": "最后使用时间"
}
"""
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class SkillLibrary:
    """
    Skill库管理器
    
    核心功能：
    1. Skill CRUD：创建/读取/更新/删除Skill
    2. 触发搜索：按关键词搜索匹配的Skill
    3. 使用统计：记录Skill的使用次数和成功率
    4. 反馈管理：收集和存储用户对Skill的反馈
    5. 统计分析：提供Skill库的整体统计信息
    
    设计特点：
    - 每个Skill独立存储为JSON文件，便于维护和扩展
    - Skill ID采用时间戳+随机数，确保唯一性
    - 触发条件支持关键词匹配，灵活适配不同场景
    - 使用统计和反馈机制支持Skill的持续优化
    - 版本控制支持Skill的迭代更新
    
    使用流程：
    1. 创建Skill：调用add_skill()，返回skill_id
    2. 搜索Skill：调用search_skills(trigger)，返回匹配的Skill列表
    3. 使用Skill：执行Skill后调用record_usage()记录使用情况
    4. 更新Skill：调用update_skill()更新Skill内容
    5. 查看统计：调用get_library_stats()查看整体统计
    """
    
    def __init__(self):
        """初始化Skill库"""
        self.skills_dir = config.SKILLS_DIR
        os.makedirs(self.skills_dir, exist_ok=True)
    
    def add_skill(self, name: str, trigger: str, steps: List[str], 
                  description: str = "", category: str = "general") -> str:
        """添加新Skill
        
        Args:
            name: Skill名称
            trigger: 触发条件（关键词或场景描述）
            steps: 执行步骤列表
            description: Skill描述
            category: 分类（general/outline/character/plot/style等）
        
        Returns:
            Skill ID
        """
        skill_id = f"skill_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        skill_data = {
            "skill_id": skill_id,
            "name": name,
            "trigger": trigger,
            "steps": steps,
            "description": description,
            "category": category,
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "usage_count": 0,
            "success_count": 0,
            "user_feedback": [],
            "last_used": None
        }
        
        skill_file = os.path.join(self.skills_dir, f"{skill_id}.json")
        with open(skill_file, 'w', encoding='utf-8') as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)
        
        return skill_id
    
    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取Skill详情
        
        Args:
            skill_id: Skill ID
        
        Returns:
            Skill数据字典，不存在则返回None
        """
        skill_file = os.path.join(self.skills_dir, f"{skill_id}.json")
        
        if not os.path.exists(skill_file):
            return None
        
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def update_skill(self, skill_id: str, **kwargs) -> bool:
        """更新Skill
        
        Args:
            skill_id: Skill ID
            **kwargs: 要更新的字段（name, trigger, steps, description等）
        
        Returns:
            是否更新成功
        """
        skill_data = self.get_skill(skill_id)
        
        if not skill_data:
            return False
        
        # 更新指定字段
        for key, value in kwargs.items():
            if key in ["name", "trigger", "steps", "description", "category"]:
                skill_data[key] = value
        
        # 版本递增
        skill_data["version"] += 1
        skill_data["updated_at"] = datetime.now().isoformat()
        
        # 保存
        skill_file = os.path.join(self.skills_dir, f"{skill_id}.json")
        with open(skill_file, 'w', encoding='utf-8') as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)
        
        return True
    
    def delete_skill(self, skill_id: str) -> bool:
        """删除Skill
        
        Args:
            skill_id: Skill ID
        
        Returns:
            是否删除成功
        """
        skill_file = os.path.join(self.skills_dir, f"{skill_id}.json")
        
        if not os.path.exists(skill_file):
            return False
        
        try:
            os.remove(skill_file)
            return True
        except Exception:
            return False
    
    def search_skills(self, trigger: str, category: str = None) -> List[Dict[str, Any]]:
        """按触发条件搜索Skill
        
        Args:
            trigger: 触发条件（关键词）
            category: 分类过滤（可选）
        
        Returns:
            匹配的Skill列表
        """
        matched_skills = []
        
        for filename in os.listdir(self.skills_dir):
            if not filename.endswith(".json"):
                continue
            
            skill_file = os.path.join(self.skills_dir, filename)
            
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                
                # 分类过滤
                if category and skill_data.get("category") != category:
                    continue
                
                # 触发条件匹配（关键词在trigger中）
                if trigger.lower() in skill_data.get("trigger", "").lower():
                    matched_skills.append(skill_data)
            except Exception:
                continue
        
        # 按成功率排序
        matched_skills.sort(
            key=lambda x: (x.get("success_count", 0) / max(x.get("usage_count", 1), 1)),
            reverse=True
        )
        
        return matched_skills
    
    def list_skills(self, category: str = None) -> List[Dict[str, Any]]:
        """列出所有Skill
        
        Args:
            category: 分类过滤（可选）
        
        Returns:
            Skill列表
        """
        skills = []
        
        for filename in os.listdir(self.skills_dir):
            if not filename.endswith(".json"):
                continue
            
            skill_file = os.path.join(self.skills_dir, filename)
            
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                
                if category and skill_data.get("category") != category:
                    continue
                
                skills.append(skill_data)
            except Exception:
                continue
        
        # 按创建时间排序
        skills.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return skills
    
    def record_usage(self, skill_id: str, success: bool, feedback: str = "") -> bool:
        """记录Skill使用情况
        
        Args:
            skill_id: Skill ID
            success: 是否成功
            feedback: 用户反馈
        
        Returns:
            是否记录成功
        """
        skill_data = self.get_skill(skill_id)
        
        if not skill_data:
            return False
        
        # 更新使用统计
        skill_data["usage_count"] += 1
        if success:
            skill_data["success_count"] += 1
        
        skill_data["last_used"] = datetime.now().isoformat()
        
        # 添加反馈
        if feedback:
            skill_data["user_feedback"].append({
                "feedback": feedback,
                "timestamp": datetime.now().isoformat()
            })
            
            # 限制反馈数量（最多保留20条）
            if len(skill_data["user_feedback"]) > 20:
                skill_data["user_feedback"] = skill_data["user_feedback"][-20:]
        
        # 保存
        skill_file = os.path.join(self.skills_dir, f"{skill_id}.json")
        with open(skill_file, 'w', encoding='utf-8') as f:
            json.dump(skill_data, f, ensure_ascii=False, indent=2)
        
        return True
    
    def get_skill_stats(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取Skill统计信息
        
        Args:
            skill_id: Skill ID
        
        Returns:
            统计信息字典
        """
        skill_data = self.get_skill(skill_id)
        
        if not skill_data:
            return None
        
        usage_count = skill_data.get("usage_count", 0)
        success_count = skill_data.get("success_count", 0)
        success_rate = success_count / max(usage_count, 1)
        
        return {
            "skill_id": skill_id,
            "name": skill_data.get("name"),
            "usage_count": usage_count,
            "success_count": success_count,
            "success_rate": success_rate,
            "last_used": skill_data.get("last_used"),
            "version": skill_data.get("version"),
            "feedback_count": len(skill_data.get("user_feedback", []))
        }
    
    def get_library_stats(self) -> Dict[str, Any]:
        """获取Skill库整体统计
        
        Returns:
            统计信息字典
        """
        all_skills = self.list_skills()
        
        total_skills = len(all_skills)
        total_usage = sum(s.get("usage_count", 0) for s in all_skills)
        total_success = sum(s.get("success_count", 0) for s in all_skills)
        avg_success_rate = total_success / max(total_usage, 1)
        
        # 按分类统计
        category_counts = {}
        for skill in all_skills:
            category = skill.get("category", "general")
            category_counts[category] = category_counts.get(category, 0) + 1
        
        return {
            "total_skills": total_skills,
            "total_usage": total_usage,
            "total_success": total_success,
            "avg_success_rate": avg_success_rate,
            "category_counts": category_counts
        }


# 全局实例
_skill_library = None


def get_skill_library() -> SkillLibrary:
    """获取全局Skill库实例（单例模式）"""
    global _skill_library
    if _skill_library is None:
        _skill_library = SkillLibrary()
    return _skill_library
