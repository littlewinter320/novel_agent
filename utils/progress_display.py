"""
进度显示模块(ProgressDisplay)

核心职责:
- 显示Agent执行进度
- 提供实时反馈给用户
- 支持多种显示模式（进度条、状态文本、步骤列表）
- 记录执行日志

工作流程:
开始任务 → 显示进度 → 更新状态 → 完成时显示结果

设计思路:
- 使用控制台输出，支持ANSI颜色码
- 提供多种进度显示方式
- 支持嵌套任务（子任务）
- 可配置是否显示详细日志

关键算法:
- 进度百分比计算
- 时间估算（基于已完成任务）
- 状态颜色编码（成功/失败/进行中）

输出格式:
控制台输出，格式化的进度信息
"""

import os
import sys
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    SUCCESS = "success"      # 成功
    FAILED = "failed"        # 失败
    SKIPPED = "skipped"      # 跳过


class ProgressDisplay:
    """
    进度显示器
    
    核心功能:
    1. 任务进度显示：进度条、百分比
    2. 状态反馈：成功/失败/进行中
    3. 时间估算：预计剩余时间
    4. 日志记录：详细执行日志
    
    使用场景:
    - 爬虫执行时显示进度
    - 批量生成章节时显示进度
    - 任何长时间运行的任务
    
    使用流程:
    1. 创建ProgressDisplay实例
    2. 调用start_task()开始任务
    3. 调用update_progress()更新进度
    4. 调用finish_task()结束任务
    """
    
    # ANSI颜色码
    COLORS = {
        "reset": "\033[0m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
    }
    
    # 状态图标
    ICONS = {
        TaskStatus.PENDING: "○",
        TaskStatus.RUNNING: "●",
        TaskStatus.SUCCESS: "✓",
        TaskStatus.FAILED: "✗",
        TaskStatus.SKIPPED: "-",
    }
    
    def __init__(self, enable_color: bool = True, verbose: bool = False):
        """
        初始化进度显示器
        
        Args:
            enable_color: 是否启用颜色输出
            verbose: 是否显示详细日志
        """
        self.enable_color = enable_color and sys.platform != "win32"  # Windows控制台可能不支持
        self.verbose = verbose
        self.tasks: List[Dict[str, Any]] = []
        self.current_task: Optional[Dict[str, Any]] = None
        self.logs: List[str] = []
    
    def _colorize(self, text: str, color: str) -> str:
        """给文本添加颜色"""
        if not self.enable_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
    
    def start_task(self, name: str, total: int = 100) -> Dict[str, Any]:
        """
        开始新任务
        
        Args:
            name: 任务名称
            total: 总进度值（默认100）
        
        Returns:
            任务信息字典
        """
        task = {
            "name": name,
            "total": total,
            "current": 0,
            "status": TaskStatus.RUNNING,
            "start_time": datetime.now(),
            "end_time": None,
            "message": "",
            "subtasks": []
        }
        
        self.tasks.append(task)
        self.current_task = task
        
        # 显示任务开始
        icon = self._colorize(self.ICONS[TaskStatus.RUNNING], "cyan")
        print(f"\n{icon} 开始: {name}")
        
        return task
    
    def update_progress(self, current: int, message: str = ""):
        """
        更新当前任务进度
        
        Args:
            current: 当前进度值
            message: 进度消息
        """
        if not self.current_task:
            return
        
        self.current_task["current"] = current
        if message:
            self.current_task["message"] = message
        
        # 计算百分比
        total = self.current_task["total"]
        percent = min(100, int(current / total * 100)) if total > 0 else 0
        
        # 显示进度条
        bar_length = 30
        filled = int(bar_length * percent / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # 估算剩余时间
        elapsed = (datetime.now() - self.current_task["start_time"]).total_seconds()
        if current > 0:
            eta = elapsed / current * (total - current)
            eta_str = f"ETA: {int(eta)}s"
        else:
            eta_str = ""
        
        # 输出进度
        msg = f"\r  [{bar}] {percent}% ({current}/{total})"
        if message:
            msg += f" - {message}"
        if eta_str:
            msg += f" | {eta_str}"
        
        print(msg, end="", flush=True)
        
        # 记录日志
        if self.verbose:
            self._log(f"进度更新: {current}/{total} - {message}")
    
    def finish_task(self, status: TaskStatus = TaskStatus.SUCCESS, message: str = ""):
        """
        结束当前任务
        
        Args:
            status: 任务状态
            message: 结束消息
        """
        if not self.current_task:
            return
        
        self.current_task["status"] = status
        self.current_task["end_time"] = datetime.now()
        if message:
            self.current_task["message"] = message
        
        # 显示结果
        icon = self.ICONS[status]
        color = {
            TaskStatus.SUCCESS: "green",
            TaskStatus.FAILED: "red",
            TaskStatus.SKIPPED: "yellow",
        }.get(status, "cyan")
        
        icon = self._colorize(icon, color)
        
        # 计算耗时
        elapsed = (self.current_task["end_time"] - self.current_task["start_time"]).total_seconds()
        
        print(f"\n{icon} 完成: {self.current_task['name']} ({elapsed:.1f}s)")
        if message:
            print(f"  {message}")
        
        # 记录日志
        self._log(f"任务完成: {self.current_task['name']} - {status.value} - {message}")
        
        # 清除当前任务
        self.current_task = None
    
    def complete_task(self, message: str = ""):
        """
        便捷方法：标记任务成功完成
        
        Args:
            message: 完成消息
        """
        self.finish_task(TaskStatus.SUCCESS, message)
    
    def fail_task(self, message: str = ""):
        """
        便捷方法：标记任务失败
        
        Args:
            message: 失败消息
        """
        self.finish_task(TaskStatus.FAILED, message)
    
    def add_subtask(self, name: str):
        """
        添加子任务
        
        Args:
            name: 子任务名称
        """
        if not self.current_task:
            return
        
        subtask = {
            "name": name,
            "status": TaskStatus.PENDING,
            "start_time": None,
            "end_time": None
        }
        
        self.current_task["subtasks"].append(subtask)
        print(f"  - {name}")
    
    def show_status(self, message: str, status: str = "info"):
        """
        显示状态消息
        
        Args:
            message: 消息内容
            status: 状态类型（info/success/warning/error）
        """
        color_map = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red"
        }
        color = color_map.get(status, "cyan")
        
        icon_map = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗"
        }
        icon = icon_map.get(status, "•")
        
        icon = self._colorize(icon, color)
        print(f"{icon} {message}")
        
        self._log(f"[{status}] {message}")
    
    def _log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取任务摘要
        
        Returns:
            任务摘要字典
        """
        summary = {
            "total_tasks": len(self.tasks),
            "success_count": sum(1 for t in self.tasks if t["status"] == TaskStatus.SUCCESS),
            "failed_count": sum(1 for t in self.tasks if t["status"] == TaskStatus.FAILED),
            "skipped_count": sum(1 for t in self.tasks if t["status"] == TaskStatus.SKIPPED),
            "total_time": 0,
            "tasks": []
        }
        
        for task in self.tasks:
            if task["end_time"] and task["start_time"]:
                elapsed = (task["end_time"] - task["start_time"]).total_seconds()
                summary["total_time"] += elapsed
                
                summary["tasks"].append({
                    "name": task["name"],
                    "status": task["status"].value,
                    "duration": elapsed,
                    "message": task["message"]
                })
        
        return summary
    
    def print_summary(self):
        """打印任务摘要"""
        summary = self.get_summary()
        
        print("\n" + "=" * 50)
        print("任务摘要")
        print("=" * 50)
        print(f"总任务数: {summary['total_tasks']}")
        print(f"成功: {self._colorize(str(summary['success_count']), 'green')}")
        print(f"失败: {self._colorize(str(summary['failed_count']), 'red')}")
        print(f"跳过: {self._colorize(str(summary['skipped_count']), 'yellow')}")
        print(f"总耗时: {summary['total_time']:.1f}s")
        print("=" * 50)


# 全局单例
_progress_display: Optional[ProgressDisplay] = None


def get_progress_display(**kwargs) -> ProgressDisplay:
    """获取全局ProgressDisplay单例"""
    global _progress_display
    if _progress_display is None:
        _progress_display = ProgressDisplay(**kwargs)
    return _progress_display


if __name__ == "__main__":
    # 测试进度显示
    progress = get_progress_display()
    
    task = progress.start_task("测试任务", total=10)
    
    for i in range(1, 11):
        time.sleep(0.5)
        progress.update_progress(i, f"处理第{i}项")
    
    progress.finish_task(TaskStatus.SUCCESS, "所有项目处理完成")
    progress.print_summary()
