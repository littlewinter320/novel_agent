"""
去AI味检查器(DeAIChecker)

核心职责:
- 维护"AI味禁用清单"（15种常见AI句式及频率上限）
- 审计时自动统计，超标则不通过

工作流程:
接收文本 → 检测AI句式 → 统计频率 → 判定是否通过

设计思路:
- 使用正则表达式检测AI句式
- 统计每种句式的出现次数
- 超过阈值则判定为FAIL

输出格式:
{
    "pass": bool,
    "tics_count": {句式: 次数},
    "issues": [问题列表],
    "report": 报告文本
}
"""

import json
import os
import re
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class DeAIChecker:
    """
    去AI味检查器类
    
    核心功能:
    1. AI句式检测：检测15种常见AI句式
    2. 频率统计：统计每种句式的出现次数
    3. 阈值判定：超过阈值则不通过
    
    使用场景:
    - 章节生成后，检查AI味
    - 审计时，作为检查维度之一
    - 用户要求检查AI味时
    
    使用流程:
    1. 调用check_ai_tics(chapter_content)检查
    2. 调用generate_report()生成报告
    """
    
    # AI味禁用清单（15种常见AI句式及频率上限）
    AI_TICS_PATTERNS = {
        "首先...其次...最后": r"首先.*其次.*最后",
        "值得一提的是": r"值得一提的是",
        "需要注意的是": r"需要注意的是",
        "综上所述": r"综上所述",
        "总的来说": r"总的来说",
        "此外": r"此外",
        "然而.*但是": r"然而.*但是",
        "不仅...而且": r"不仅.*而且",
        "一方面.*另一方面": r"一方面.*另一方面",
        "至关重要": r"至关重要",
        "格局": r"格局",
        "织锦": r"织锦",
        "不可否认": r"不可否认",
        "毋庸置疑": r"毋庸置疑",
        "由此可见": r"由此可见"
    }
    
    def __init__(self):
        """
        初始化去AI味检查器
        
        初始化流程:
        1. 初始化检查结果存储
        """
        self.check_results = []
    
    def check_ai_tics(self, chapter_content: str) -> Dict[str, Any]:
        """
        检查AI句式（核心方法）
        
        实现逻辑:
        1. 遍历15种AI句式
        2. 使用正则表达式检测
        3. 统计每种句式的出现次数
        4. 判定是否超过阈值
        
        Args:
            chapter_content: 章节正文
        
        Returns:
            检查结果字典
        """
        issues = []
        suggestions = []
        tics_count = {}
        
        # 检测每种AI句式
        for tic_name, pattern in self.AI_TICS_PATTERNS.items():
            matches = re.findall(pattern, chapter_content)
            count = len(matches)
            tics_count[tic_name] = count
            
            # 如果超过阈值，记录问题
            if count > config.AI_TIC_MAX_PER_CHAPTER:
                issues.append(f"AI句式'{tic_name}'出现{count}次，超过上限{config.AI_TIC_MAX_PER_CHAPTER}次")
                suggestions.append(f"减少使用'{tic_name}'，可以用更自然的表达替代")
        
        result = {
            "pass": len(issues) == 0,
            "tics_count": tics_count,
            "issues": issues,
            "suggestions": suggestions,
            "checked_at": datetime.now().isoformat()
        }
        
        # 保存检查结果
        self.check_results.append(result)
        
        return result
    
    def generate_report(self, check_result: Dict[str, Any] = None) -> str:
        """
        生成检查报告
        
        Args:
            check_result: 检查结果字典（可选，默认使用最新结果）
        
        Returns:
            Markdown格式的报告
        """
        if check_result is None:
            if not self.check_results:
                return "无检查结果"
            check_result = self.check_results[-1]
        
        report = "# AI味检查报告\n\n"
        
        # 总体结果
        passed = check_result.get("pass", False)
        report += f"## 总体结果: {'✅ 通过' if passed else '❌ 不通过'}\n\n"
        
        # 句式统计
        report += "## 句式统计\n\n"
        tics_count = check_result.get("tics_count", {})
        
        for tic_name, count in tics_count.items():
            status = "✅" if count <= config.AI_TIC_MAX_PER_CHAPTER else "❌"
            report += f"- {status} {tic_name}: {count}次\n"
        
        report += "\n"
        
        # 问题列表
        issues = check_result.get("issues", [])
        if issues:
            report += "## 问题列表\n\n"
            for i, issue in enumerate(issues, 1):
                report += f"{i}. {issue}\n"
            report += "\n"
        
        # 建议列表
        suggestions = check_result.get("suggestions", [])
        if suggestions:
            report += "## 改进建议\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                report += f"{i}. {suggestion}\n"
            report += "\n"
        
        return report


# 全局实例
_de_ai_checker = None


def get_de_ai_checker() -> DeAIChecker:
    """获取全局去AI味检查器实例（单例模式）"""
    global _de_ai_checker
    if _de_ai_checker is None:
        _de_ai_checker = DeAIChecker()
    return _de_ai_checker
