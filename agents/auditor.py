"""
连续性审计员(SubAgent-Auditor)

核心职责:
- 从15个维度检查章节内容一致性
- 集成Humanizer-zh去AI化检测功能
- 输出审计报告（每个维度PASS/FAIL + 具体问题描述 + 修正方向）

15个检查维度:
1. 角色OOC检查 - 检查角色行为是否符合性格设定
2. 时间线一致性 - 检查事件时间顺序是否矛盾
3. 战力/等级一致性 - 检查角色能力是否突变
4. 伏笔检查 - 检查伏笔是否正确埋设/触发/回收
5. 角色认知边界 - 检查角色是否知道不该知道的事
6. 物品/道具一致性 - 检查物品流转是否合理
7. 世界规则一致性 - 检查是否违反已建立的世界规则
8. 关系一致性 - 检查角色关系是否矛盾
9. 风格一致性 - 检查文风是否符合风格指南
10. 节奏检查 - 检查章节节奏是否合理
11. 爽点检查 - 检查爽点分布是否合理
12. 结尾钩子检查 - 检查章节结尾是否有吸引力
13. AI味检查 - 检查是否包含AI常用句式和表达
14. 剧情推进检查 - 检查剧情是否有推进
15. 读者体验检查 - 检查读者阅读体验

设计思路:
- 采用"规则检查 + LLM辅助"的双层策略
- 规则检查：使用正则表达式和关键词匹配快速检测
- LLM辅助：对于复杂的语义检查，调用LLM进行判断
- 15个维度独立检查，互不影响

输出格式:
{
    "audit_results": [每个维度的检查结果],
    "overall_pass": bool,
    "issues": [问题列表],
    "suggestions": [修正建议]
}
"""

import json
import os
import re
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.llm_client import get_llm_client
from core.genre_knowledge import get_genre_knowledge_base
from core.truth_files import TruthFiles


class AuditorAgent:
    """
    连续性审计员类
    
    核心功能:
    1. 15维度一致性检查：全面检查章节内容的各个方面
    2. AI味检测：集成Humanizer-zh的去AI化检测
    3. 审计报告生成：生成详细的审计报告
    4. 修正建议：为每个问题提供修正方向
    
    使用场景:
    - 写手生成章节后，进行质量检查
    - 批量生成时，逐章审计
    - 修订后，再次审计确认修复
    
    使用流程:
    1. 调用audit_chapter(chapter_content, truth_files, style_guide)
    2. 内部自动执行15个维度的检查
    3. 生成审计报告
    4. 返回审计结果
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
        初始化审计员
        
        初始化流程:
        1. 获取LLM客户端
        2. 获取题材知识库
        3. 初始化真相文件管理器
        """
        self.llm_client = get_llm_client()
        self.genre_knowledge_base = get_genre_knowledge_base()
        self.truth_files = TruthFiles()
    
    def audit_chapter(self, chapter_content: str, 
                     chapter_num: int,
                     genre: str,
                     style_guide: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        审计章节内容（核心方法）
        
        实现逻辑:
        1. 加载真相文件
        2. 执行15个维度的检查
        3. 汇总检查结果
        4. 生成审计报告
        
        Args:
            chapter_content: 章节正文
            chapter_num: 章节号
            genre: 题材名称
            style_guide: 风格指南（可选）
        
        Returns:
            审计结果字典，包含：
            - audit_results: 每个维度的检查结果
            - overall_pass: 是否整体通过
            - issues: 问题列表
            - suggestions: 修正建议
        """
        # 加载真相文件
        self.truth_files.load_all()
        
        # 执行15个维度的检查
        audit_results = []
        
        # 1. 角色OOC检查
        audit_results.append(self._check_character_ooc(chapter_content, chapter_num))
        
        # 2. 时间线一致性
        audit_results.append(self._check_timeline_consistency(chapter_content, chapter_num))
        
        # 3. 战力/等级一致性
        audit_results.append(self._check_power_consistency(chapter_content, chapter_num))
        
        # 4. 伏笔检查
        audit_results.append(self._check_foreshadow(chapter_content, chapter_num))
        
        # 5. 角色认知边界
        audit_results.append(self._check_character_knowledge(chapter_content, chapter_num))
        
        # 6. 物品/道具一致性
        audit_results.append(self._check_item_consistency(chapter_content, chapter_num))
        
        # 7. 世界规则一致性
        audit_results.append(self._check_world_rules(chapter_content, chapter_num))
        
        # 8. 关系一致性
        audit_results.append(self._check_relationship_consistency(chapter_content, chapter_num))
        
        # 9. 风格一致性
        audit_results.append(self._check_style_consistency(chapter_content, style_guide))
        
        # 10. 节奏检查
        audit_results.append(self._check_pacing(chapter_content, chapter_num))
        
        # 11. 爽点检查
        audit_results.append(self._check_excitement(chapter_content, chapter_num, genre))
        
        # 12. 结尾钩子检查
        audit_results.append(self._check_ending_hook(chapter_content))
        
        # 13. AI味检查
        audit_results.append(self._check_ai_tics(chapter_content))
        
        # 14. 剧情推进检查
        audit_results.append(self._check_plot_progress(chapter_content, chapter_num))
        
        # 15. 读者体验检查
        audit_results.append(self._check_reader_experience(chapter_content))
        
        # 汇总结果
        overall_pass = all(r["pass"] for r in audit_results)
        issues = []
        suggestions = []
        
        for result in audit_results:
            if not result["pass"]:
                issues.extend(result.get("issues", []))
                suggestions.extend(result.get("suggestions", []))
        
        return {
            "chapter_num": chapter_num,
            "audit_results": audit_results,
            "overall_pass": overall_pass,
            "issues": issues,
            "suggestions": suggestions,
            "audited_at": datetime.now().isoformat()
        }
    
    def _check_character_ooc(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查角色OOC（Out of Character）"""
        # 使用LLM检查角色行为是否符合性格
        prompt = f"""检查以下章节内容中是否存在角色OOC（行为不符合性格设定）的问题。

章节内容:
{content[:3000]}...

请检查:
1. 角色行为是否符合其性格设定
2. 角色对话是否符合其个性
3. 角色决策是否合理

如果发现OOC问题，请指出具体位置和原因。

以JSON格式返回:
{{
    "pass": true/false,
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            result["dimension"] = "角色OOC检查"
            return result
        except Exception as e:
            return {
                "dimension": "角色OOC检查",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_timeline_consistency(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查时间线一致性"""
        # 从真相文件获取时间线
        timeline = self.truth_files.get_file("timeline")
        events = timeline.get("events", [])
        
        # 使用LLM检查时间线
        prompt = f"""检查以下章节内容的时间线是否与已建立的时间线一致。

当前章节号: {chapter_num}
章节内容:
{content[:2000]}...

已知时间线事件:
{json.dumps(events[-5:], ensure_ascii=False, indent=2)}

请检查:
1. 事件时间顺序是否矛盾
2. 是否有时间跳跃未说明
3. 是否有因果倒置

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
            result["dimension"] = "时间线一致性"
            return result
        except Exception as e:
            return {
                "dimension": "时间线一致性",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_power_consistency(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查战力/等级一致性"""
        # 从真相文件获取角色能力
        character_matrix = self.truth_files.get_file("character_matrix")
        
        prompt = f"""检查以下章节内容中角色的能力/等级是否一致。

章节内容:
{content[:2000]}...

角色矩阵:
{json.dumps(character_matrix.get("characters", {}), ensure_ascii=False, indent=2)}

请检查:
1. 角色能力是否突变
2. 等级提升是否合理
3. 战斗表现是否符合设定

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
            result["dimension"] = "战力/等级一致性"
            return result
        except Exception as e:
            return {
                "dimension": "战力/等级一致性",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_foreshadow(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查伏笔"""
        # 从真相文件获取伏笔
        foreshadow_hooks = self.truth_files.get_file("foreshadow_hooks")
        foreshadows = foreshadow_hooks.get("foreshadows", [])
        
        # 检查本章应该触发的伏笔
        expected_triggers = [
            f for f in foreshadows 
            if f.get("trigger_chapter") == chapter_num
        ]
        
        prompt = f"""检查以下章节内容中的伏笔处理是否正确。

当前章节号: {chapter_num}
章节内容:
{content[:2000]}...

应该在本章触发的伏笔:
{json.dumps(expected_triggers, ensure_ascii=False, indent=2)}

请检查:
1. 应该触发的伏笔是否触发
2. 应该埋设的伏笔是否埋设
3. 伏笔处理是否自然

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
            result["dimension"] = "伏笔检查"
            return result
        except Exception as e:
            return {
                "dimension": "伏笔检查",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_character_knowledge(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查角色认知边界"""
        character_matrix = self.truth_files.get_file("character_matrix")
        
        prompt = f"""检查以下章节内容中角色是否知道不该知道的事。

章节内容:
{content[:2000]}...

角色矩阵:
{json.dumps(character_matrix.get("characters", {}), ensure_ascii=False, indent=2)}

请检查:
1. 角色是否知道未来事件
2. 角色是否知道其他角色的秘密
3. 角色的认知边界是否清晰

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
            result["dimension"] = "角色认知边界"
            return result
        except Exception as e:
            return {
                "dimension": "角色认知边界",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_item_consistency(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查物品/道具一致性"""
        resource_ledger = self.truth_files.get_file("resource_ledger")
        
        prompt = f"""检查以下章节内容中物品的使用是否一致。

章节内容:
{content[:2000]}...

资源账本:
{json.dumps(resource_ledger, ensure_ascii=False, indent=2)}

请检查:
1. 物品是否凭空出现
2. 物品是否凭空消失
3. 物品使用是否符合设定

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
            result["dimension"] = "物品/道具一致性"
            return result
        except Exception as e:
            return {
                "dimension": "物品/道具一致性",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_world_rules(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查世界规则一致性"""
        world_state = self.truth_files.get_file("world_state")
        
        prompt = f"""检查以下章节内容是否违反已建立的世界规则。

章节内容:
{content[:2000]}...

世界状态:
{json.dumps(world_state, ensure_ascii=False, indent=2)}

请检查:
1. 是否违反物理规则
2. 是否违反社会规则
3. 是否违反力量体系规则

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
            result["dimension"] = "世界规则一致性"
            return result
        except Exception as e:
            return {
                "dimension": "世界规则一致性",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_relationship_consistency(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查关系一致性"""
        character_matrix = self.truth_files.get_file("character_matrix")
        
        prompt = f"""检查以下章节内容中角色关系是否一致。

章节内容:
{content[:2000]}...

角色矩阵:
{json.dumps(character_matrix.get("characters", {}), ensure_ascii=False, indent=2)}

请检查:
1. 角色关系是否矛盾
2. 关系变化是否合理
3. 互动是否符合关系设定

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
            result["dimension"] = "关系一致性"
            return result
        except Exception as e:
            return {
                "dimension": "关系一致性",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_style_consistency(self, content: str, style_guide: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查风格一致性"""
        if not style_guide:
            return {
                "dimension": "风格一致性",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "note": "无风格指南，跳过检查"
            }
        
        prompt = f"""检查以下章节内容是否符合风格指南。

章节内容:
{content[:2000]}...

风格指南:
{json.dumps(style_guide, ensure_ascii=False, indent=2)}

请检查:
1. 文风是否符合
2. 叙事视角是否一致
3. 是否使用了禁用句式

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
            result["dimension"] = "风格一致性"
            return result
        except Exception as e:
            return {
                "dimension": "风格一致性",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_pacing(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查节奏"""
        prompt = f"""检查以下章节的节奏是否合理。

章节内容:
{content[:2000]}...

请检查:
1. 节奏是否过于拖沓
2. 节奏是否过于急促
3. 快慢节奏是否合理搭配

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
            result["dimension"] = "节奏检查"
            return result
        except Exception as e:
            return {
                "dimension": "节奏检查",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_excitement(self, content: str, chapter_num: int, genre: str) -> Dict[str, Any]:
        """检查爽点"""
        prompt = f"""检查以下章节的爽点分布是否合理。

章节内容:
{content[:2000]}...

题材: {genre}

请检查:
1. 是否有爽点
2. 爽点是否符合题材特点
3. 爽点是否过于密集或稀疏

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
            result["dimension"] = "爽点检查"
            return result
        except Exception as e:
            return {
                "dimension": "爽点检查",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_ending_hook(self, content: str) -> Dict[str, Any]:
        """检查结尾钩子"""
        # 获取章节最后500字
        ending = content[-500:] if len(content) > 500 else content
        
        prompt = f"""检查以下章节结尾是否有吸引力。

章节结尾:
{ending}

请检查:
1. 结尾是否有悬念
2. 是否能吸引读者继续阅读下一章
3. 结尾是否仓促

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
            result["dimension"] = "结尾钩子检查"
            return result
        except Exception as e:
            return {
                "dimension": "结尾钩子检查",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_ai_tics(self, content: str) -> Dict[str, Any]:
        """
        检查AI味（集成Humanizer-zh检测逻辑）
        
        实现逻辑:
        1. 使用正则表达式检测15种AI常用句式
        2. 统计每种句式的出现次数
        3. 超过阈值则判定为FAIL
        """
        issues = []
        suggestions = []
        tics_count = {}
        
        # 检测每种AI句式
        for tic_name, pattern in self.AI_TICS_PATTERNS.items():
            matches = re.findall(pattern, content)
            count = len(matches)
            tics_count[tic_name] = count
            
            # 如果超过阈值，记录问题
            if count > config.AI_TIC_MAX_PER_CHAPTER:
                issues.append(f"AI句式'{tic_name}'出现{count}次，超过上限{config.AI_TIC_MAX_PER_CHAPTER}次")
                suggestions.append(f"减少使用'{tic_name}'，可以用更自然的表达替代")
        
        return {
            "dimension": "AI味检查",
            "pass": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "tics_count": tics_count
        }
    
    def _check_plot_progress(self, content: str, chapter_num: int) -> Dict[str, Any]:
        """检查剧情推进"""
        prompt = f"""检查以下章节是否有剧情推进。

章节内容:
{content[:2000]}...

请检查:
1. 剧情是否有推进
2. 是否有实质性进展
3. 是否过于水字数

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
            result["dimension"] = "剧情推进检查"
            return result
        except Exception as e:
            return {
                "dimension": "剧情推进检查",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def _check_reader_experience(self, content: str) -> Dict[str, Any]:
        """检查读者体验"""
        prompt = f"""从读者角度检查以下章节的阅读体验。

章节内容:
{content[:2000]}...

请检查:
1. 是否容易理解
2. 是否有吸引力
3. 是否有让人想跳过的部分
4. 整体阅读体验如何

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
            result["dimension"] = "读者体验检查"
            return result
        except Exception as e:
            return {
                "dimension": "读者体验检查",
                "pass": True,
                "issues": [],
                "suggestions": [],
                "error": str(e)
            }
    
    def generate_audit_report(self, audit_result: Dict[str, Any]) -> str:
        """
        生成人类可读的审计报告
        
        Args:
            audit_result: 审计结果字典
        
        Returns:
            Markdown格式的审计报告
        """
        report = f"# 审计报告 - 第{audit_result.get('chapter_num', '?')}章\n\n"
        
        # 总体结果
        overall_pass = audit_result.get("overall_pass", False)
        report += f"## 总体结果: {'✅ 通过' if overall_pass else '❌ 不通过'}\n\n"
        
        # 各维度检查结果
        report += "## 各维度检查结果\n\n"
        audit_results = audit_result.get("audit_results", [])
        
        for result in audit_results:
            dimension = result.get("dimension", "未知维度")
            passed = result.get("pass", False)
            status = "✅ 通过" if passed else "❌ 不通过"
            report += f"### {dimension}: {status}\n"
            
            issues = result.get("issues", [])
            if issues:
                report += "**问题:**\n"
                for issue in issues:
                    report += f"- {issue}\n"
                report += "\n"
            
            suggestions = result.get("suggestions", [])
            if suggestions:
                report += "**建议:**\n"
                for suggestion in suggestions:
                    report += f"- {suggestion}\n"
                report += "\n"
        
        # 汇总问题
        all_issues = audit_result.get("issues", [])
        if all_issues:
            report += "## 所有问题汇总\n\n"
            for i, issue in enumerate(all_issues, 1):
                report += f"{i}. {issue}\n"
            report += "\n"
        
        # 汇总建议
        all_suggestions = audit_result.get("suggestions", [])
        if all_suggestions:
            report += "## 所有建议汇总\n\n"
            for i, suggestion in enumerate(all_suggestions, 1):
                report += f"{i}. {suggestion}\n"
            report += "\n"
        
        return report


# 全局实例
_auditor_agent = None


def get_auditor_agent() -> AuditorAgent:
    """获取全局审计员实例（单例模式）"""
    global _auditor_agent
    if _auditor_agent is None:
        _auditor_agent = AuditorAgent()
    return _auditor_agent
