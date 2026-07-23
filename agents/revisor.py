"""
修订员(SubAgent-Revisor)

核心职责:
- 接收审计员的修正方向，对章节进行定点修复
- 不做全章重写
- 最多3轮，超过则暂停等待用户介入

工作流程:
接收审计报告 → 分析问题 → 定点修复 → 重新审计 → 循环（最多3轮）

设计思路:
- 采用"定点修复"策略，只修改有问题的段落
- 每轮修复后重新审计，确认问题是否解决
- 超过3轮仍未通过，暂停并输出问题摘要

关键算法:
- 问题定位：根据审计报告定位需要修改的段落
- 定点修复：只修改有问题的部分，保留其他内容
- 循环控制：最多3轮审计-修复循环

输出格式:
{
    "revised_content": 修复后的内容,
    "fixes_applied": [应用的修复列表],
    "audit_rounds": 审计轮数,
    "final_pass": 最终是否通过
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
from agents.auditor import get_auditor_agent


class RevisorAgent:
    """
    修订员类
    
    核心功能:
    1. 定点修复：只修改有问题的段落
    2. 循环审计：最多3轮审计-修复循环
    3. 问题摘要：超过3轮时输出问题摘要
    
    使用场景:
    - 审计员发现章节问题后，进行修复
    - 批量生成时，修复不合格的章节
    - 用户要求修改特定问题
    
    使用流程:
    1. 调用revise_chapter(chapter_content, audit_report)
    2. 内部自动执行定点修复
    3. 重新审计修复后的内容
    4. 循环直到通过或达到3轮上限
    """
    
    def __init__(self):
        """
        初始化修订员
        
        初始化流程:
        1. 获取LLM客户端
        2. 获取审计员实例
        """
        self.llm_client = get_llm_client()
        self.auditor = get_auditor_agent()
    
    def revise_chapter(self, chapter_content: str,
                      chapter_num: int,
                      genre: str,
                      audit_report: Dict[str, Any],
                      style_guide: Dict[str, Any] = None,
                      max_rounds: int = None) -> Dict[str, Any]:
        """
        修订章节（核心方法）
        
        实现逻辑:
        1. 分析审计报告，提取问题
        2. 对每个问题进行定点修复
        3. 重新审计修复后的内容
        4. 循环直到通过或达到max_rounds上限
        
        Args:
            chapter_content: 原始章节内容
            chapter_num: 章节号
            genre: 题材名称
            audit_report: 审计报告
            style_guide: 风格指南（可选）
            max_rounds: 最大修订轮数（默认使用config.MAX_AUDIT_ROUNDS）
        
        Returns:
            修订结果字典，包含：
            - revised_content: 修复后的内容
            - fixes_applied: 应用的修复列表
            - audit_rounds: 审计轮数
            - final_pass: 最终是否通过
        """
        if max_rounds is None:
            max_rounds = config.MAX_AUDIT_ROUNDS
        
        current_content = chapter_content
        fixes_applied = []
        audit_rounds = 0
        final_pass = False
        
        # 循环审计-修复
        for round_num in range(max_rounds):
            audit_rounds += 1
            
            # 1. 分析当前审计报告
            issues = audit_report.get("issues", [])
            if not issues:
                # 没有问題，直接通过
                final_pass = True
                break
            
            # 2. 定点修复
            revised_content, round_fixes = self._spot_fix(
                current_content, issues, chapter_num, genre
            )
            
            current_content = revised_content
            fixes_applied.extend(round_fixes)
            
            # 3. 重新审计
            new_audit_report = self.auditor.audit_chapter(
                current_content, chapter_num, genre, style_guide
            )
            
            audit_report = new_audit_report
            
            # 4. 检查是否通过
            if new_audit_report.get("overall_pass", False):
                final_pass = True
                break
        
        return {
            "chapter_num": chapter_num,
            "revised_content": current_content,
            "fixes_applied": fixes_applied,
            "audit_rounds": audit_rounds,
            "final_pass": final_pass,
            "final_audit_report": audit_report,
            "revised_at": datetime.now().isoformat()
        }
    
    def _spot_fix(self, content: str,
                 issues: List[str],
                 chapter_num: int,
                 genre: str) -> tuple:
        """
        定点修复（只修改有问题的部分）
        
        实现逻辑:
        1. 构造修复提示词，列出所有问题
        2. 调用LLM进行定点修复
        3. 提取修复的内容和修复说明
        
        Args:
            content: 原始内容
            issues: 问题列表
            chapter_num: 章节号
            genre: 题材名称
        
        Returns:
            (修复后的内容, 修复说明列表)
        """
        # 构造问题文本
        issues_text = "\n".join([f"- {issue}" for issue in issues])
        
        prompt = f"""请对以下章节内容进行定点修复，只修改有问题的部分，保留其他内容。

当前章节号: {chapter_num}
题材: {genre}

原始内容:
{content}

需要修复的问题:
{issues_text}

修复要求:
1. 只修改有问题的段落，保留其他内容
2. 保持整体结构和风格不变
3. 确保修复后符合题材规范
4. 修复要具体，不能笼统

请以JSON格式返回:
{{
    "revised_content": "修复后的完整内容",
    "fixes": [
        {{
            "issue": "原问题",
            "fix": "修复说明",
            "location": "修复位置（如第X段）"
        }}
    ]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            
            revised_content = result.get("revised_content", content)
            fixes = result.get("fixes", [])
            
            # 格式化修复说明
            fix_descriptions = []
            for fix in fixes:
                desc = f"[{fix.get('location', '未知')}] {fix.get('issue', '问题')} → {fix.get('fix', '修复')}"
                fix_descriptions.append(desc)
            
            return revised_content, fix_descriptions
        except Exception as e:
            print(f"定点修复失败: {e}")
            return content, [f"修复失败: {e}"]
    
    def generate_revision_report(self, revision_result: Dict[str, Any]) -> str:
        """
        生成修订报告
        
        Args:
            revision_result: 修订结果字典
        
        Returns:
            Markdown格式的修订报告
        """
        report = f"# 修订报告 - 第{revision_result.get('chapter_num', '?')}章\n\n"
        
        # 总体结果
        final_pass = revision_result.get("final_pass", False)
        report += f"## 总体结果: {'✅ 修复成功' if final_pass else '❌ 修复失败'}\n\n"
        
        # 审计轮数
        audit_rounds = revision_result.get("audit_rounds", 0)
        report += f"## 审计轮数: {audit_rounds}\n\n"
        
        # 应用的修复
        fixes_applied = revision_result.get("fixes_applied", [])
        if fixes_applied:
            report += "## 应用的修复\n\n"
            for i, fix in enumerate(fixes_applied, 1):
                report += f"{i}. {fix}\n"
            report += "\n"
        
        # 最终审计结果
        final_audit_report = revision_result.get("final_audit_report", {})
        if final_audit_report:
            report += "## 最终审计结果\n\n"
            issues = final_audit_report.get("issues", [])
            if issues:
                report += "### 剩余问题\n\n"
                for issue in issues:
                    report += f"- {issue}\n"
                report += "\n"
            else:
                report += "✅ 所有问题已解决\n\n"
        
        return report


# 全局实例
_revisor_agent = None


def get_revisor_agent() -> RevisorAgent:
    """获取全局修订员实例（单例模式）"""
    global _revisor_agent
    if _revisor_agent is None:
        _revisor_agent = RevisorAgent()
    return _revisor_agent
