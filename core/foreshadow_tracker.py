"""
伏笔追踪系统(ForeshadowTracker)

核心职责:
- 维护伏笔生命周期：未埋设→已埋设→积累中→已触发→已回收→已放弃
- 每章生成前自动检查应触发/回收的伏笔
- 每章生成后自动更新伏笔状态
- 伏笔健康度检查

工作流程:
加载伏笔数据 → 检查状态 → 更新状态 → 健康度检查 → 保存

设计思路:
- 使用状态机管理伏笔生命周期
- 持久化到真相文件中的伏笔钩子文件
- 支持健康度检查和警告

输出格式:
{
    "foreshadows": [伏笔列表],
    "active_count": 活跃伏笔数,
    "warnings": [警告列表]
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


class ForeshadowTracker:
    """
    伏笔追踪系统类
    
    核心功能:
    1. 伏笔生命周期管理
    2. 状态检查和更新
    3. 健康度检查
    4. 持久化到真相文件
    
    使用场景:
    - 章节生成前检查伏笔状态
    - 章节生成后更新伏笔状态
    - 定期检查伏笔健康度
    
    使用流程:
    1. 调用check_foreshadow_status(current_chapter)检查状态
    2. 调用update_foreshadow_status(chapter_content)更新状态
    3. 调用health_check()检查健康度
    """
    
    # 伏笔状态
    STATUS_UNPLANTED = "未埋设"
    STATUS_PLANTED = "已埋设"
    STATUS_ACCUMULATING = "积累中"
    STATUS_TRIGGERED = "已触发"
    STATUS_RESOLVED = "已回收"
    STATUS_ABANDONED = "已放弃"
    
    def __init__(self):
        """
        初始化伏笔追踪系统
        
        初始化流程:
        1. 获取真相文件管理器
        2. 加载伏笔数据
        """
        self.truth_files = TruthFiles()
        self.foreshadows = []
        self._load_foreshadows()
    
    def _load_foreshadows(self):
        """加载伏笔数据"""
        self.truth_files.load_all()
        foreshadow_hooks = self.truth_files.get_file("foreshadow_hooks")
        self.foreshadows = foreshadow_hooks.get("foreshadows", [])
    
    def _save_foreshadows(self):
        """保存伏笔数据"""
        self.truth_files.update_file("foreshadow_hooks", {
            "foreshadows": self.foreshadows,
            "updated_at": datetime.now().isoformat()
        })
    
    def check_foreshadow_status(self, current_chapter: int) -> Dict[str, Any]:
        """
        检查伏笔状态（核心方法）
        
        实现逻辑:
        1. 检查当前章节应该触发的伏笔
        2. 检查当前章节应该回收的伏笔
        3. 检查过期的伏笔
        
        Args:
            current_chapter: 当前章节号
        
        Returns:
            伏笔状态字典
        """
        should_trigger = []
        should_resolve = []
        overdue = []
        
        for foreshadow in self.foreshadows:
            status = foreshadow.get("status", self.STATUS_UNPLANTED)
            plant_chapter = foreshadow.get("plant_chapter", 0)
            trigger_chapter = foreshadow.get("trigger_chapter", 0)
            resolve_chapter_range = foreshadow.get("resolve_chapter_range", "")
            
            # 检查应该触发的伏笔
            if status == self.STATUS_PLANTED and trigger_chapter == current_chapter:
                should_trigger.append(foreshadow)
            
            # 检查应该回收的伏笔
            if status == self.STATUS_TRIGGERED and resolve_chapter_range:
                # 解析回收章节区间
                try:
                    if "-" in resolve_chapter_range:
                        start, end = map(int, resolve_chapter_range.split("-"))
                        if start <= current_chapter <= end:
                            should_resolve.append(foreshadow)
                    else:
                        resolve_ch = int(resolve_chapter_range)
                        if resolve_ch == current_chapter:
                            should_resolve.append(foreshadow)
                except:
                    pass
            
            # 检查过期的伏笔
            if status in [self.STATUS_PLANTED, self.STATUS_ACCUMULATING]:
                if current_chapter - plant_chapter > config.FORESHADOW_STALE_THRESHOLD:
                    overdue.append(foreshadow)
        
        return {
            "current_chapter": current_chapter,
            "should_trigger": should_trigger,
            "should_resolve": should_resolve,
            "overdue": overdue,
            "active_count": len([f for f in self.foreshadows if f.get("status") in [
                self.STATUS_PLANTED, self.STATUS_ACCUMULATING, self.STATUS_TRIGGERED
            ]])
        }
    
    def update_foreshadow_status(self, chapter_content: str,
                                current_chapter: int) -> Dict[str, Any]:
        """
        更新伏笔状态
        
        实现逻辑:
        1. 分析章节内容，识别伏笔相关事件
        2. 更新伏笔状态
        3. 保存更新后的数据
        
        Args:
            chapter_content: 章节正文
            current_chapter: 当前章节号
        
        Returns:
            更新结果字典
        """
        updated = []
        
        # 使用简单的关键词匹配来识别伏笔事件
        for foreshadow in self.foreshadows:
            foreshadow_name = foreshadow.get("foreshadow_name", "")
            status = foreshadow.get("status", self.STATUS_UNPLANTED)
            
            # 如果伏笔名称出现在章节内容中
            if foreshadow_name in chapter_content:
                # 更新状态
                if status == self.STATUS_UNPLANTED:
                    foreshadow["status"] = self.STATUS_PLANTED
                    foreshadow["plant_chapter"] = current_chapter
                    updated.append({
                        "foreshadow": foreshadow_name,
                        "action": "埋设",
                        "chapter": current_chapter
                    })
                elif status == self.STATUS_PLANTED:
                    foreshadow["status"] = self.STATUS_ACCUMULATING
                    foreshadow["last_mentioned_chapter"] = current_chapter
                    updated.append({
                        "foreshadow": foreshadow_name,
                        "action": "积累",
                        "chapter": current_chapter
                    })
                elif status == self.STATUS_ACCUMULATING:
                    foreshadow["last_mentioned_chapter"] = current_chapter
                    updated.append({
                        "foreshadow": foreshadow_name,
                        "action": "提及",
                        "chapter": current_chapter
                    })
        
        # 保存更新
        if updated:
            self._save_foreshadows()
        
        return {
            "updated_count": len(updated),
            "updates": updated
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        伏笔健康度检查
        
        实现逻辑:
        1. 检查活跃伏笔数量
        2. 检查过期伏笔
        3. 生成警告
        
        Returns:
            健康度检查结果字典
        """
        warnings = []
        
        # 统计各状态的伏笔数量
        status_counts = {}
        for foreshadow in self.foreshadows:
            status = foreshadow.get("status", self.STATUS_UNPLANTED)
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 检查活跃伏笔数量
        active_count = sum([
            status_counts.get(self.STATUS_PLANTED, 0),
            status_counts.get(self.STATUS_ACCUMULATING, 0),
            status_counts.get(self.STATUS_TRIGGERED, 0)
        ])
        
        if active_count > config.MAX_ACTIVE_FORESHADOWS:
            warnings.append(f"活跃伏笔数量过多({active_count}个)，建议回收部分伏笔")
        
        # 检查过期伏笔
        current_chapter = status_counts.get("current_chapter", 0)
        for foreshadow in self.foreshadows:
            plant_chapter = foreshadow.get("plant_chapter", 0)
            last_mentioned = foreshadow.get("last_mentioned_chapter", plant_chapter)
            
            if current_chapter - last_mentioned > config.FORESHADOW_STALE_THRESHOLD:
                warnings.append(f"伏笔'{foreshadow.get('foreshadow_name', '未知')}'超过{config.FORESHADOW_STALE_THRESHOLD}章未提及")
        
        return {
            "status_counts": status_counts,
            "active_count": active_count,
            "warnings": warnings,
            "healthy": len(warnings) == 0
        }
    
    def get_active_threads(self) -> List[Dict[str, Any]]:
        """
        获取活跃的伏笔线程
        
        Returns:
            活跃伏笔列表
        """
        return [
            f for f in self.foreshadows
            if f.get("status") in [
                self.STATUS_PLANTED,
                self.STATUS_ACCUMULATING,
                self.STATUS_TRIGGERED
            ]
        ]
    
    def add_foreshadow(self, foreshadow: Dict[str, Any]) -> bool:
        """
        添加新伏笔
        
        Args:
            foreshadow: 伏笔信息字典
        
        Returns:
            是否添加成功
        """
        # 检查是否已存在
        name = foreshadow.get("foreshadow_name", "")
        if any(f.get("foreshadow_name") == name for f in self.foreshadows):
            return False
        
        # 设置初始状态
        foreshadow["status"] = self.STATUS_UNPLANTED
        foreshadow["created_at"] = datetime.now().isoformat()
        
        self.foreshadows.append(foreshadow)
        self._save_foreshadows()
        
        return True


# 全局实例
_foreshadow_tracker = None


def get_foreshadow_tracker() -> ForeshadowTracker:
    """获取全局伏笔追踪系统实例（单例模式）"""
    global _foreshadow_tracker
    if _foreshadow_tracker is None:
        _foreshadow_tracker = ForeshadowTracker()
    return _foreshadow_tracker
