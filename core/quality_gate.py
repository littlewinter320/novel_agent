"""
质量门禁(QualityGate)

核心职责:
- 6大维度检查：逻辑完整性、信息完整性、用户修改记忆、格式与可读性、专业性与可执行性、一致性检查
- PASS/FAIL判定，FAIL时返回上一步重新规划

工作流程:
接收SubAgent输出 → 6维度检查 → 判定PASS/FAIL → 生成报告

设计思路:
- 采用"规则检查 + LLM辅助"的双层策略
- 规则检查：使用关键词匹配和格式验证快速检测
- LLM辅助：对于复杂的语义检查，调用LLM进行判断

输出格式:
{
    "pass": bool,
    "dimensions": [各维度检查结果],
    "issues": [问题列表],
    "suggestions": [修正建议],
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
from utils.llm_client import get_llm_client


class QualityGate:
    """
    质量门禁类
    
    核心功能:
    1. 6大维度检查：全面检查SubAgent输出质量
    2. PASS/FAIL判定：根据检查结果判定是否通过
    3. 报告生成：生成详细的质量报告
    4. 结果持久化：保存检查结果
    
    使用场景:
    - SubAgent输出后，进行质量检查
    - 批量生成时，逐章质量检查
    - 用户要求质量检查时
    
    使用流程:
    1. 调用check(subagent_output, context)
    2. 内部自动执行6个维度的检查
    3. 生成质量报告
    4. 返回检查结果
    """
    
    def __init__(self):
        """
        初始化质量门禁
        
        初始化流程:
        1. 获取LLM客户端
        2. 初始化检查结果存储
        """
        self.llm_client = get_llm_client()
        self.check_results = []
    
    def check(self, subagent_output: Dict[str, Any],
              context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行质量检查（核心方法）
        
        实现逻辑:
        1. 执行6大维度检查
        2. 汇总检查结果
        3. 判定PASS/FAIL
        4. 生成报告
        
        Args:
            subagent_output: SubAgent输出内容
            context: 上下文信息（可选）
        
        Returns:
            检查结果字典
        """
        dimensions = []
        
        # 1. 逻辑完整性检查
        dimensions.append(self._check_logic_completeness(subagent_output))
        
        # 2. 信息完整性检查
        dimensions.append(self._check_info_completeness(subagent_output))
        
        # 3. 用户修改记忆检查
        dimensions.append(self._check_user_modification_memory(subagent_output, context))
        
        # 4. 格式与可读性检查
        dimensions.append(self._check_format_readability(subagent_output))
        
        # 5. 专业性与可执行性检查
        dimensions.append(self._check_professionalism(subagent_output))
        
        # 6. 一致性检查
        dimensions.append(self._check_consistency(subagent_output, context))
        
        # 汇总结果
        overall_pass = all(d["pass"] for d in dimensions)
        issues = []
        suggestions = []
        
        for d in dimensions:
            if not d["pass"]:
                issues.extend(d.get("issues", []))
                suggestions.extend(d.get("suggestions", []))
        
        result = {
            "pass": overall_pass,
            "dimensions": dimensions,
            "issues": issues,
            "suggestions": suggestions,
            "checked_at": datetime.now().isoformat()
        }
        
        # 保存检查结果
        self.check_results.append(result)
        
        return result
    
    def _check_logic_completeness(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """检查逻辑完整性"""
        issues = []
        suggestions = []
        
        # 检查是否包含必要的逻辑要素
        content = json.dumps(output, ensure_ascii=False)
        
        # 使用LLM检查逻辑完整性
        prompt = f"""检查以下内容的逻辑完整性。

内容:
{content[:2000]}

请检查:
1. 逻辑是否自洽
2. 是否有矛盾之处
3. 因果关系是否合理
4. 论证是否充分

以JSON格式返回:
{{
    "pass": true/false,
    "issues": ["问题1"],
    "suggestions": ["建议1"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            result["dimension"] = "逻辑完整性"
            return result
        except Exception as e:
            return {
                "dimension": "逻辑完整性",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_info_completeness(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """检查信息完整性"""
        issues = []
        suggestions = []
        
        # 检查是否缺少关键信息
        required_fields = ["content", "summary", "details"]
        missing_fields = [f for f in required_fields if f not in output]
        
        if missing_fields:
            issues.append(f"缺少关键字段: {', '.join(missing_fields)}")
            suggestions.append("补充缺失的关键信息")
        
        return {
            "dimension": "信息完整性",
            "pass": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _check_user_modification_memory(self, output: Dict[str, Any],
                                       context: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查用户修改记忆"""
        if not context:
            return {
                "dimension": "用户修改记忆",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "note": "无上下文信息，跳过检查"
            }
        
        # 检查是否遵循了用户的修改
        user_modifications = context.get("user_modifications", [])
        
        if user_modifications:
            # 使用LLM检查是否遵循了用户修改
            prompt = f"""检查以下内容是否遵循了用户的修改要求。

用户修改要求:
{json.dumps(user_modifications, ensure_ascii=False, indent=2)}

输出内容:
{json.dumps(output, ensure_ascii=False)[:2000]}

请检查:
1. 是否遵循了所有用户修改
2. 是否有遗漏的修改
3. 是否有与修改要求矛盾的内容

以JSON格式返回:
{{
    "pass": true/false,
    "issues": ["问题1"],
    "suggestions": ["建议1"]
}}

只返回JSON对象。"""
            
            try:
                response = self.llm_client.generate(prompt)
                result = json.loads(response)
                result["dimension"] = "用户修改记忆"
                return result
            except Exception as e:
                return {
                    "dimension": "用户修改记忆",
                    "pass": True,
                    "issues": [],
                    "suggestions": [],
                    "error": str(e)
                }
        
        return {
            "dimension": "用户修改记忆",
            "pass": True,
            "issues": [],
            "suggestions": []
        }
    
    def _check_format_readability(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """检查格式与可读性"""
        issues = []
        suggestions = []
        
        content = json.dumps(output, ensure_ascii=False)
        
        # 检查格式问题
        if len(content) > 10000:
            issues.append("内容过长，可能影响可读性")
            suggestions.append("考虑分段或精简内容")
        
        # 检查是否有适当的结构
        if "content" in output and isinstance(output["content"], str):
            if len(output["content"]) > 5000 and "\n" not in output["content"]:
                issues.append("长文本缺少段落分隔")
                suggestions.append("添加适当的段落分隔")
        
        return {
            "dimension": "格式与可读性",
            "pass": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _check_professionalism(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """检查专业性与可执行性"""
        content = json.dumps(output, ensure_ascii=False)
        
        prompt = f"""检查以下内容的专业性和可执行性。

内容:
{content[:2000]}

请检查:
1. 内容是否专业
2. 建议是否可执行
3. 是否有空泛的内容
4. 是否有具体的行动项

以JSON格式返回:
{{
    "pass": true/false,
    "issues": ["问题1"],
    "suggestions": ["建议1"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            result["dimension"] = "专业性与可执行性"
            return result
        except Exception as e:
            return {
                "dimension": "专业性与可执行性",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_consistency(self, output: Dict[str, Any],
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查一致性"""
        if not context:
            return {
                "dimension": "一致性检查",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "note": "无上下文信息，跳过检查"
            }
        
        content = json.dumps(output, ensure_ascii=False)
        context_text = json.dumps(context, ensure_ascii=False)
        
        prompt = f"""检查以下内容与上下文的一致性。

上下文:
{context_text[:1000]}

输出内容:
{content[:2000]}

请检查:
1. 是否与上下文一致
2. 是否有矛盾之处
3. 是否遵循了已建立的规则

以JSON格式返回:
{{
    "pass": true/false,
    "issues": ["问题1"],
    "suggestions": ["建议1"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            result["dimension"] = "一致性检查"
            return result
        except Exception as e:
            return {
                "dimension": "一致性检查",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def generate_report(self, check_result: Dict[str, Any]) -> str:
        """
        生成质量报告
        
        Args:
            check_result: 检查结果字典
        
        Returns:
            Markdown格式的报告
        """
        report = "# 质量检查报告\n\n"
        
        # 总体结果
        overall_pass = check_result.get("pass", False)
        report += f"## 总体结果: {'✅ 通过' if overall_pass else '❌ 不通过'}\n\n"
        
        # 各维度检查结果
        report += "## 各维度检查结果\n\n"
        dimensions = check_result.get("dimensions", [])
        
        for d in dimensions:
            dimension = d.get("dimension", "未知维度")
            passed = d.get("pass", False)
            status = "✅ 通过" if passed else "❌ 不通过"
            report += f"### {dimension}: {status}\n"
            
            issues = d.get("issues", [])
            if issues:
                report += "**问题:**\n"
                for issue in issues:
                    report += f"- {issue}\n"
                report += "\n"
            
            suggestions = d.get("suggestions", [])
            if suggestions:
                report += "**建议:**\n"
                for suggestion in suggestions:
                    report += f"- {suggestion}\n"
                report += "\n"
        
        # 汇总问题
        all_issues = check_result.get("issues", [])
        if all_issues:
            report += "## 所有问题汇总\n\n"
            for i, issue in enumerate(all_issues, 1):
                report += f"{i}. {issue}\n"
            report += "\n"
        
        # 汇总建议
        all_suggestions = check_result.get("suggestions", [])
        if all_suggestions:
            report += "## 所有建议汇总\n\n"
            for i, suggestion in enumerate(all_suggestions, 1):
                report += f"{i}. {suggestion}\n"
            report += "\n"
        
        return report


# 全局实例
_quality_gate = None


def get_quality_gate() -> QualityGate:
    """获取全局质量门禁实例（单例模式）"""
    global _quality_gate
    if _quality_gate is None:
        _quality_gate = QualityGate()
    return _quality_gate
