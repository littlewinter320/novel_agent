"""
修改追踪系统(ModificationTracker)

核心职责:
- 记录每次修改（内容、原因、时间、影响范围）
- 评估修改的影响（受影响章节/角色/伏笔）
- 强制后续步骤基于最新修改
- 支持"部分回滚"

工作流程:
记录修改 → 评估影响 → 应用修改 → 支持回滚

设计思路:
- 使用修改记录管理历史变更
- 支持影响评估
- 支持部分回滚

输出格式:
{
    "modifications": [修改记录列表],
    "impact": 影响评估,
    "rollback_result": 回滚结果
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


class ModificationTracker:
    """
    修改追踪系统类
    
    核心功能:
    1. 修改记录：记录每次修改的详细信息
    2. 影响评估：评估修改的影响范围
    3. 部分回滚：支持回滚到特定版本
    
    使用场景:
    - 用户修改内容后，记录修改
    - 评估修改对其他部分的影响
    - 需要回滚时，执行部分回滚
    
    使用流程:
    1. 调用record_modification(mod)记录修改
    2. 调用assess_impact(mod)评估影响
    3. 调用apply_modifications()应用修改
    4. 调用partial_rollback(target_version)回滚
    """
    
    def __init__(self):
        """
        初始化修改追踪系统
        
        初始化流程:
        1. 初始化修改记录列表
        2. 加载历史修改记录
        """
        self.modifications = []
        self._load_modifications()
    
    def _load_modifications(self):
        """加载修改记录"""
        data_dir = config.DATA_DIR
        mod_file = os.path.join(data_dir, "modifications.json")
        
        if os.path.exists(mod_file):
            try:
                with open(mod_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.modifications = data.get("modifications", [])
            except Exception as e:
                print(f"加载修改记录失败: {e}")
                self.modifications = []
    
    def _save_modifications(self):
        """保存修改记录"""
        data_dir = config.DATA_DIR
        os.makedirs(data_dir, exist_ok=True)
        mod_file = os.path.join(data_dir, "modifications.json")
        
        try:
            with open(mod_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "modifications": self.modifications,
                    "updated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存修改记录失败: {e}")
    
    def record_modification(self, mod: Dict[str, Any]) -> Dict[str, Any]:
        """
        记录修改（核心方法）
        
        实现逻辑:
        1. 验证修改信息
        2. 添加时间戳和ID
        3. 保存到修改记录
        
        Args:
            mod: 修改信息字典
        
        Returns:
            记录结果字典
        """
        # 验证必要字段
        required_fields = ["content", "reason"]
        missing_fields = [f for f in required_fields if f not in mod]
        
        if missing_fields:
            return {
                "recorded": False,
                "error": f"缺少必要字段: {', '.join(missing_fields)}"
            }
        
        # 添加元数据
        mod["id"] = len(self.modifications) + 1
        mod["timestamp"] = datetime.now().isoformat()
        mod.setdefault("impact_scope", {})
        
        self.modifications.append(mod)
        self._save_modifications()
        
        return {
            "recorded": True,
            "mod_id": mod["id"],
            "timestamp": mod["timestamp"]
        }
    
    def assess_impact(self, mod: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估修改影响
        
        实现逻辑:
        1. 分析修改内容
        2. 识别受影响的章节/角色/伏笔
        3. 生成影响报告
        
        Args:
            mod: 修改信息字典
        
        Returns:
            影响评估结果字典
        """
        content = mod.get("content", "")
        mod_type = mod.get("type", "unknown")
        
        impact = {
            "affected_chapters": [],
            "affected_characters": [],
            "affected_foreshadows": [],
            "severity": "low"
        }
        
        # 根据修改类型评估影响
        if mod_type == "character":
            # 角色修改可能影响多个章节
            impact["severity"] = "medium"
            impact["affected_characters"].append(mod.get("target", ""))
        elif mod_type == "plot":
            # 剧情修改可能影响后续所有章节
            impact["severity"] = "high"
        elif mod_type == "foreshadow":
            # 伏笔修改可能影响相关章节
            impact["severity"] = "medium"
            impact["affected_foreshadows"].append(mod.get("target", ""))
        
        return impact
    
    def apply_modifications(self) -> Dict[str, Any]:
        """
        应用所有修改
        
        实现逻辑:
        1. 按时间顺序排序修改
        2. 逐个应用修改
        3. 返回应用结果
        
        Returns:
            应用结果字典
        """
        # 按时间戳排序
        sorted_mods = sorted(self.modifications, key=lambda x: x.get("timestamp", ""))
        
        applied = []
        for mod in sorted_mods:
            # 这里应该实际应用到真相文件等
            # 简化实现：只记录应用状态
            mod["applied"] = True
            applied.append(mod["id"])
        
        self._save_modifications()
        
        return {
            "applied_count": len(applied),
            "applied_ids": applied
        }
    
    def partial_rollback(self, target_version: int,
                        keep_elements: List[str] = None) -> Dict[str, Any]:
        """
        部分回滚
        
        实现逻辑:
        1. 找到目标版本的修改
        2. 回滚到该版本，但保留指定元素
        3. 返回回滚结果
        
        Args:
            target_version: 目标版本号
            keep_elements: 要保留的元素列表
        
        Returns:
            回滚结果字典
        """
        keep_elements = keep_elements or []
        
        # 找到目标版本之后的修改
        mods_to_rollback = [
            m for m in self.modifications
            if m.get("id", 0) > target_version
        ]
        
        # 过滤掉要保留的元素
        mods_to_rollback = [
            m for m in mods_to_rollback
            if m.get("type") not in keep_elements
        ]
        
        # 移除这些修改
        self.modifications = [
            m for m in self.modifications
            if m.get("id", 0) <= target_version or m.get("type") in keep_elements
        ]
        
        self._save_modifications()
        
        return {
            "rolled_back_count": len(mods_to_rollback),
            "rolled_back_ids": [m.get("id") for m in mods_to_rollback],
            "kept_elements": keep_elements
        }
    
    def get_modification_history(self) -> List[Dict[str, Any]]:
        """
        获取修改历史
        
        Returns:
            修改记录列表
        """
        return self.modifications.copy()


# 全局实例
_modification_tracker = None


def get_modification_tracker() -> ModificationTracker:
    """获取全局修改追踪系统实例（单例模式）"""
    global _modification_tracker
    if _modification_tracker is None:
        _modification_tracker = ModificationTracker()
    return _modification_tracker
