"""
断点管理器(CheckpointManager)

核心职责:
- 每个关键步骤完成后自动保存checkpoint
- 系统崩溃后从最近checkpoint恢复
- 支持"手动保存点"

工作流程:
保存checkpoint → 列出checkpoint → 恢复checkpoint

设计思路:
- 使用JSON文件持久化checkpoint
- 支持自动和手动保存
- 支持从checkpoint恢复完整状态

输出格式:
{
    "checkpoint_id": checkpoint ID,
    "step": 步骤名称,
    "timestamp": 时间戳,
    "state": 状态数据
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


class CheckpointManager:
    """
    断点管理器类
    
    核心功能:
    1. 自动checkpoint：关键步骤完成后自动保存
    2. 手动checkpoint：用户主动保存
    3. 从checkpoint恢复：恢复完整状态
    
    使用场景:
    - 关键步骤完成后自动保存
    - 用户主动保存当前状态
    - 系统崩溃后恢复
    
    使用流程:
    1. 调用save_checkpoint(step, is_manual)保存
    2. 调用list_checkpoints()列出所有checkpoint
    3. 调用restore_checkpoint(checkpoint_id)恢复
    """
    
    def __init__(self):
        """
        初始化断点管理器
        
        初始化流程:
        1. 创建checkpoint目录
        2. 加载已有checkpoint列表
        """
        self.checkpoint_dir = os.path.join(config.DATA_DIR, "checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.checkpoints = []
        self._load_checkpoints()
    
    def _load_checkpoints(self):
        """加载checkpoint列表"""
        index_file = os.path.join(self.checkpoint_dir, "index.json")
        
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.checkpoints = data.get("checkpoints", [])
            except Exception as e:
                print(f"加载checkpoint列表失败: {e}")
                self.checkpoints = []
    
    def _save_checkpoint_index(self):
        """保存checkpoint索引"""
        index_file = os.path.join(self.checkpoint_dir, "index.json")
        
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "checkpoints": self.checkpoints,
                    "updated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存checkpoint索引失败: {e}")
    
    def save_checkpoint(self, step: str,
                       state: Dict[str, Any] = None,
                       is_manual: bool = False) -> Dict[str, Any]:
        """
        保存checkpoint（核心方法）
        
        实现逻辑:
        1. 生成checkpoint ID
        2. 保存状态数据
        3. 更新checkpoint索引
        
        Args:
            step: 步骤名称
            state: 状态数据（可选）
            is_manual: 是否手动保存
        
        Returns:
            保存结果字典
        """
        checkpoint_id = len(self.checkpoints) + 1
        timestamp = datetime.now().isoformat()
        
        # 构建checkpoint数据
        checkpoint = {
            "id": checkpoint_id,
            "step": step,
            "timestamp": timestamp,
            "is_manual": is_manual,
            "state": state or {}
        }
        
        # 保存checkpoint文件
        checkpoint_file = os.path.join(self.checkpoint_dir, f"checkpoint_{checkpoint_id}.json")
        
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)
            
            # 更新索引
            self.checkpoints.append({
                "id": checkpoint_id,
                "step": step,
                "timestamp": timestamp,
                "is_manual": is_manual
            })
            self._save_checkpoint_index()
            
            return {
                "saved": True,
                "checkpoint_id": checkpoint_id,
                "step": step,
                "timestamp": timestamp
            }
        except Exception as e:
            return {
                "saved": False,
                "error": str(e)
            }
    
    def load_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        加载最新的checkpoint
        
        Returns:
            最新的checkpoint数据，如果没有则返回None
        """
        if not self.checkpoints:
            return None
        
        latest = self.checkpoints[-1]
        return self.restore_checkpoint(latest["id"])
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        列出所有checkpoint
        
        Returns:
            checkpoint列表
        """
        return self.checkpoints.copy()
    
    def restore_checkpoint(self, checkpoint_id: int) -> Optional[Dict[str, Any]]:
        """
        恢复checkpoint
        
        实现逻辑:
        1. 找到指定的checkpoint文件
        2. 加载checkpoint数据
        3. 返回状态数据
        
        Args:
            checkpoint_id: checkpoint ID
        
        Returns:
            checkpoint状态数据，如果不存在则返回None
        """
        checkpoint_file = os.path.join(self.checkpoint_dir, f"checkpoint_{checkpoint_id}.json")
        
        if not os.path.exists(checkpoint_file):
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
                return checkpoint.get("state", {})
        except Exception as e:
            print(f"恢复checkpoint失败: {e}")
            return None


# 全局实例
_checkpoint_manager = None


def get_checkpoint_manager() -> CheckpointManager:
    """获取全局断点管理器实例（单例模式）"""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager
