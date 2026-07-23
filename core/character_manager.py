"""
角色管理系统(CharacterManager)

核心职责:
- 维护每个角色的"当前状态快照"
- 每章生成前加载角色上下文
- 每章生成后更新角色状态
- 一致性检查

工作流程:
加载角色数据 → 构建上下文 → 更新状态 → 一致性检查 → 保存

设计思路:
- 使用状态快照管理角色信息
- 持久化到真相文件中的角色矩阵文件
- 支持一致性检查

输出格式:
{
    "characters": [角色列表],
    "context": 角色上下文,
    "consistency_check": 一致性检查结果
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
from core.truth_files import TruthFiles
from utils.llm_client import get_llm_client


class CharacterManager:
    """
    角色管理系统类
    
    核心功能:
    1. 角色状态快照维护
    2. 上下文加载和状态更新
    3. 一致性检查
    4. 持久化到真相文件
    
    使用场景:
    - 章节生成前加载角色上下文
    - 章节生成后更新角色状态
    - 检查角色行为一致性
    
    使用流程:
    1. 调用load_character_context(character_ids)加载上下文
    2. 调用update_character_state(character_id, chapter_content)更新状态
    3. 调用check_consistency(character_id, behavior)检查一致性
    """
    
    def __init__(self):
        """
        初始化角色管理系统
        
        初始化流程:
        1. 获取真相文件管理器
        2. 获取LLM客户端
        3. 加载角色数据
        """
        self.truth_files = TruthFiles()
        self.llm_client = get_llm_client()
        self.characters = {}
        self._load_characters()
    
    def _load_characters(self):
        """加载角色数据"""
        self.truth_files.load_all()
        character_matrix = self.truth_files.get_file("character_matrix")
        self.characters = character_matrix.get("characters", {})
    
    def _save_characters(self):
        """保存角色数据"""
        self.truth_files.update_file("character_matrix", {
            "characters": self.characters,
            "updated_at": datetime.now().isoformat()
        })
    
    def load_character_context(self, character_ids: List[str] = None) -> Dict[str, Any]:
        """
        加载角色上下文（核心方法）
        
        实现逻辑:
        1. 加载指定角色的完整信息
        2. 构建上下文供章节生成使用
        
        Args:
            character_ids: 角色ID列表（可选，默认加载所有角色）
        
        Returns:
            角色上下文字典
        """
        if character_ids is None:
            return self.characters
        
        context = {}
        for char_id in character_ids:
            if char_id in self.characters:
                context[char_id] = self.characters[char_id]
        
        return context
    
    def update_character_state(self, character_id: str,
                              chapter_content: str) -> Dict[str, Any]:
        """
        更新角色状态
        
        实现逻辑:
        1. 分析章节内容，识别角色状态变化
        2. 更新角色状态快照
        3. 保存更新后的数据
        
        Args:
            character_id: 角色ID
            chapter_content: 章节正文
        
        Returns:
            更新结果字典
        """
        if character_id not in self.characters:
            return {"updated": False, "error": f"角色{character_id}不存在"}
        
        character = self.characters[character_id]
        
        # 使用LLM分析角色状态变化
        prompt = f"""分析以下章节内容，提取角色'{character_id}'的状态变化。

角色当前状态:
{json.dumps(character, ensure_ascii=False, indent=2)}

章节内容:
{chapter_content[:2000]}

请提取以下信息:
1. 位置变化
2. 能力变化
3. 关系变化
4. 目标变化
5. 秘密变化

以JSON格式返回:
{{
    "location_change": "位置变化描述",
    "ability_change": "能力变化描述",
    "relationship_changes": ["关系变化列表"],
    "goal_change": "目标变化描述",
    "secret_changes": ["秘密变化列表"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            changes = json.loads(response)
            
            # 更新角色状态
            if changes.get("location_change"):
                character["current_location"] = changes["location_change"]
            if changes.get("ability_change"):
                character["abilities"] = changes["ability_change"]
            if changes.get("relationship_changes"):
                character["relationships"].extend(changes["relationship_changes"])
            if changes.get("goal_change"):
                character["current_goal"] = changes["goal_change"]
            if changes.get("secret_changes"):
                character["secrets"].extend(changes["secret_changes"])
            
            # 更新时间戳
            character["last_updated"] = datetime.now().isoformat()
            
            # 保存更新
            self._save_characters()
            
            return {
                "updated": True,
                "character_id": character_id,
                "changes": changes
            }
        except Exception as e:
            return {
                "updated": False,
                "error": str(e)
            }
    
    def check_consistency(self, character_id: str,
                         behavior: str) -> Dict[str, Any]:
        """
        检查角色行为一致性
        
        实现逻辑:
        1. 加载角色状态快照
        2. 使用LLM检查行为是否符合角色设定
        
        Args:
            character_id: 角色ID
            behavior: 行为描述
        
        Returns:
            一致性检查结果字典
        """
        if character_id not in self.characters:
            return {"consistent": False, "error": f"角色{character_id}不存在"}
        
        character = self.characters[character_id]
        
        prompt = f"""检查以下行为是否符合角色设定。

角色设定:
{json.dumps(character, ensure_ascii=False, indent=2)}

行为描述:
{behavior}

请检查:
1. 行为是否符合角色性格
2. 行为是否符合角色当前状态
3. 行为是否符合角色认知边界
4. 行为是否符合角色能力范围

以JSON格式返回:
{{
    "consistent": true/false,
    "issues": ["问题1"],
    "suggestions": ["建议1"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            return result
        except Exception as e:
            return {
                "consistent": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def add_character(self, character_id: str, character_info: Dict[str, Any]) -> bool:
        """
        添加新角色
        
        Args:
            character_id: 角色ID
            character_info: 角色信息字典
        
        Returns:
            是否添加成功
        """
        if character_id in self.characters:
            return False
        
        # 设置默认值
        character_info.setdefault("relationships", [])
        character_info.setdefault("secrets", [])
        character_info.setdefault("created_at", datetime.now().isoformat())
        
        self.characters[character_id] = character_info
        self._save_characters()
        
        return True


# 全局实例
_character_manager = None


def get_character_manager() -> CharacterManager:
    """获取全局角色管理系统实例（单例模式）"""
    global _character_manager
    if _character_manager is None:
        _character_manager = CharacterManager()
    return _character_manager
