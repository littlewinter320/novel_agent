"""
诊断工具(DiagnosticTool)

核心职责:
- 生成系统运行诊断报告
- 支持"健康检查"（真相文件完整性、知识库遗漏、伏笔异常、角色状态一致性）

工作流程:
收集系统状态 → 执行健康检查 → 生成诊断报告

设计思路:
- 检查各个核心模块的状态
- 识别潜在问题
- 生成可读的诊断报告

输出格式:
{
    "system_status": 系统状态,
    "health_check": 健康检查结果,
    "issues": [问题列表],
    "report": 报告文本
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
from core.genre_knowledge import get_genre_knowledge_base
from core.foreshadow_tracker import get_foreshadow_tracker
from core.character_manager import get_character_manager


class DiagnosticTool:
    """
    诊断工具类
    
    核心功能:
    1. 系统状态报告：收集系统各模块状态
    2. 健康检查：检查核心组件健康度
    3. 报告生成：生成可读的诊断报告
    
    使用场景:
    - 定期检查系统健康状态
    - 排查问题
    - 生成系统状态报告
    
    使用流程:
    1. 调用generate_report()生成报告
    2. 调用health_check()执行健康检查
    3. 调用export_report(output_file)导出报告
    """
    
    def __init__(self):
        """
        初始化诊断工具
        
        初始化流程:
        1. 获取各个核心模块实例
        """
        self.truth_files = TruthFiles()
        self.genre_knowledge_base = get_genre_knowledge_base()
        self.foreshadow_tracker = get_foreshadow_tracker()
        self.character_manager = get_character_manager()
    
    def generate_report(self) -> Dict[str, Any]:
        """
        生成系统诊断报告（核心方法）
        
        实现逻辑:
        1. 收集系统状态信息
        2. 执行健康检查
        3. 汇总问题和警告
        4. 生成报告
        
        Returns:
            诊断报告字典
        """
        # 收集系统状态
        system_status = self._collect_system_status()
        
        # 执行健康检查
        health_check = self.health_check()
        
        # 生成报告文本
        report = self._generate_report_text(system_status, health_check)
        
        return {
            "system_status": system_status,
            "health_check": health_check,
            "report": report,
            "generated_at": datetime.now().isoformat()
        }
    
    def _collect_system_status(self) -> Dict[str, Any]:
        """收集系统状态信息"""
        status = {
            "truth_files": {},
            "genre_knowledge": {},
            "foreshadow": {},
            "character": {},
            "storage": {}
        }
        
        # 真相文件状态
        self.truth_files.load_all()
        truth_file_names = ["world_state", "character_matrix", "plot_progress", 
                           "foreshadow_hooks", "resource_ledger", "timeline", "style_guide"]
        for name in truth_file_names:
            file_data = self.truth_files.get_file(name)
            status["truth_files"][name] = {
                "exists": file_data is not None,
                "size": len(json.dumps(file_data, ensure_ascii=False)) if file_data else 0
            }
        
        # 题材知识库状态
        genres = self.genre_knowledge_base.list_genres()
        status["genre_knowledge"] = {
            "total_genres": len(genres),
            "genres": genres
        }
        
        # 伏笔状态
        foreshadow_health = self.foreshadow_tracker.health_check()
        status["foreshadow"] = {
            "total_count": len(self.foreshadow_tracker.foreshadows),
            "active_count": foreshadow_health.get("active_count", 0),
            "healthy": foreshadow_health.get("healthy", True)
        }
        
        # 角色状态
        status["character"] = {
            "total_count": len(self.character_manager.characters)
        }
        
        # 存储状态
        data_dir = config.DATA_DIR
        if os.path.exists(data_dir):
            total_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(data_dir)
                for filename in filenames
            )
            status["storage"] = {
                "data_dir": data_dir,
                "total_size_mb": round(total_size / 1024 / 1024, 2)
            }
        
        return status
    
    def health_check(self) -> Dict[str, Any]:
        """
        执行健康检查
        
        实现逻辑:
        1. 检查真相文件完整性
        2. 检查知识库遗漏
        3. 检查伏笔异常
        4. 检查角色状态一致性
        
        Returns:
            健康检查结果字典
        """
        issues = []
        warnings = []
        
        # 1. 检查真相文件完整性
        self.truth_files.load_all()
        required_files = ["world_state", "character_matrix", "plot_progress", 
                         "foreshadow_hooks", "resource_ledger", "timeline", "style_guide"]
        
        for file_name in required_files:
            file_data = self.truth_files.get_file(file_name)
            if not file_data:
                issues.append(f"真相文件'{file_name}'缺失或为空")
        
        # 2. 检查知识库遗漏
        genres = self.genre_knowledge_base.list_genres()
        if len(genres) < 10:
            warnings.append(f"题材知识库数量较少({len(genres)}种)，建议补充更多题材")
        
        # 3. 检查伏笔异常
        foreshadow_health = self.foreshadow_tracker.health_check()
        if not foreshadow_health.get("healthy", True):
            for warning in foreshadow_health.get("warnings", []):
                warnings.append(f"伏笔问题: {warning}")
        
        # 4. 检查角色状态一致性
        for char_id, char_data in self.character_manager.characters.items():
            if not char_data.get("personality"):
                warnings.append(f"角色'{char_id}'缺少性格设定")
            if not char_data.get("current_goal"):
                warnings.append(f"角色'{char_id}'缺少当前目标")
        
        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "issue_count": len(issues),
            "warning_count": len(warnings)
        }
    
    def _generate_report_text(self, system_status: Dict[str, Any],
                             health_check: Dict[str, Any]) -> str:
        """生成报告文本"""
        report = "# 系统诊断报告\n\n"
        report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 系统状态
        report += "## 系统状态\n\n"
        report += f"- 题材数量: {system_status.get('genre_knowledge', {}).get('total_genres', 0)}种\n"
        report += f"- 伏笔总数: {system_status.get('foreshadow', {}).get('total_count', 0)}个\n"
        report += f"- 活跃伏笔: {system_status.get('foreshadow', {}).get('active_count', 0)}个\n"
        report += f"- 角色总数: {system_status.get('character', {}).get('total_count', 0)}个\n"
        
        storage = system_status.get('storage', {})
        if storage:
            report += f"- 数据目录: {storage.get('data_dir', '未知')}\n"
            report += f"- 存储大小: {storage.get('total_size_mb', 0)}MB\n"
        
        report += "\n"
        
        # 健康检查
        report += "## 健康检查\n\n"
        healthy = health_check.get("healthy", True)
        report += f"整体状态: {'✅ 健康' if healthy else '❌ 存在问题'}\n\n"
        
        issues = health_check.get("issues", [])
        if issues:
            report += "### 问题\n\n"
            for i, issue in enumerate(issues, 1):
                report += f"{i}. {issue}\n"
            report += "\n"
        
        warnings = health_check.get("warnings", [])
        if warnings:
            report += "### 警告\n\n"
            for i, warning in enumerate(warnings, 1):
                report += f"{i}. {warning}\n"
            report += "\n"
        
        if not issues and not warnings:
            report += "✅ 系统运行正常，无问题或警告\n\n"
        
        return report
    
    def export_report(self, output_file: str) -> Dict[str, Any]:
        """
        导出诊断报告
        
        Args:
            output_file: 输出文件路径
        
        Returns:
            导出结果字典
        """
        try:
            report_data = self.generate_report()
            report_text = report_data.get("report", "")
            
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            return {
                "exported": True,
                "output_file": output_file
            }
        except Exception as e:
            return {
                "exported": False,
                "error": str(e)
            }


# 全局实例
_diagnostic_tool = None


def get_diagnostic_tool() -> DiagnosticTool:
    """获取全局诊断工具实例（单例模式）"""
    global _diagnostic_tool
    if _diagnostic_tool is None:
        _diagnostic_tool = DiagnosticTool()
    return _diagnostic_tool
