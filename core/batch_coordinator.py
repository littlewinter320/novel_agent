"""
批量生成协调器(BatchCoordinator)

核心职责:
- 处理"一次性生成N章"的请求
- 逐章生成→审计→更新真相文件→下一章（不能并行）
- 全部完成后做"跨章一致性检查"
- 如果某章审计不通过，只重写该章

工作流程:
接收章节范围 → 逐章生成 → 逐章审计(最多3轮) → 更新真相文件 → 跨章一致性检查

设计思路:
- 采用"串行生成"策略，确保章节间的连贯性
- 每章生成后立即审计，不合格则修订，最多3轮审计-修订循环
- 每章完成后更新真相文件，为下一章提供最新上下文
- 全部完成后进行跨章一致性检查
- 单章失败时只重写该章，不影响已通过章节

关键算法:
- 串行控制：确保章节按顺序生成
- 审计循环：每章最多3轮审计-修订（由Revisor内部控制）
- 失败重试：审计不通过时，从生成阶段重新开始，最多重试MAX_RETRY次
- 真相文件更新：每章完成后自动更新
- 跨章检查：检查角色状态、伏笔推进、时间线的连续性

输出格式:
{
    "chapters": [生成的章节列表],
    "audit_results": [审计结果列表],
    "cross_chapter_check": 跨章一致性检查结果,
    "success_count": 成功生成的章节数
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
from agents.writer import get_writer_agent
from agents.auditor import get_auditor_agent
from agents.revisor import get_revisor_agent
from core.truth_files import TruthFiles
from core.exporter import get_exporter

# 单章生成失败后的最大重试次数（从生成阶段重新开始）
MAX_GENERATE_RETRY = 2


class BatchCoordinator:
    """
    批量生成协调器类

    核心功能:
    1. 批量生成：一次性生成多章内容
    2. 串行控制：确保章节按顺序生成
    3. 逐章审计：每章生成后立即审计，最多3轮审计-修订循环
    4. 失败重试：单章失败时只重写该章，不影响已通过章节
    5. 真相文件更新：每章完成后更新真相文件
    6. 跨章检查：全部完成后进行跨章一致性检查

    使用场景:
    - 用户需要一次性生成多章内容
    - 批量生成时，确保章节间的连贯性
    - 需要自动更新真相文件

    使用流程:
    1. 调用generate_batch(chapter_plans, genre, style_guide)
    2. 内部自动逐章生成、审计(最多3轮)、更新真相文件
    3. 单章失败时只重写该章
    4. 全部完成后进行跨章一致性检查
    5. 返回生成结果
    """

    def __init__(self):
        """
        初始化批量生成协调器

        初始化流程:
        1. 获取LLM客户端
        2. 获取写手、审计员、修订员实例
        3. 初始化真相文件管理器
        """
        self.llm_client = get_llm_client()
        self.writer = get_writer_agent()
        self.auditor = get_auditor_agent()
        self.revisor = get_revisor_agent()
        self.truth_files = TruthFiles()

    def generate_batch(self, chapter_plans: List[Dict[str, Any]],
                      genre: str,
                      style_guide: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        批量生成章节（核心方法）

        实现逻辑:
        1. 加载真相文件
        2. 逐章生成（串行）：
           a. 生成章节内容
           b. 审计章节（Revisor内部最多3轮审计-修订循环）
           c. 如果最终仍不通过，重新生成该章（最多MAX_GENERATE_RETRY次）
           d. 更新真相文件
           e. 单章失败不影响其他已通过章节
        3. 全部完成后进行跨章一致性检查
        4. 返回生成结果

        Args:
            chapter_plans: 章节规划列表
            genre: 题材名称
            style_guide: 风格指南（可选）

        Returns:
            批量生成结果字典，包含：
            - chapters: 生成的章节列表
            - audit_results: 审计结果列表
            - cross_chapter_check: 跨章一致性检查结果
            - success_count: 成功生成的章节数
        """
        # 限制批量生成数量
        if len(chapter_plans) > config.BATCH_MAX_CHAPTERS:
            chapter_plans = chapter_plans[:config.BATCH_MAX_CHAPTERS]

        # 加载真相文件
        self.truth_files.load_all()

        chapters = []
        audit_results = []
        success_count = 0
        failed_chapters = []  # 记录失败的章节号

        # 逐章生成（串行，确保章节间连贯性）
        for i, chapter_plan in enumerate(chapter_plans):
            chapter_num = chapter_plan.get("chapter_num", i + 1)
            chapter_title = chapter_plan.get("chapter_title", f"第{chapter_num}章")

            print(f"[BatchCoordinator] 开始生成第{chapter_num}章: {chapter_title}")

            # 收集前文摘要，为当前章提供上下文
            previous_summaries = self._collect_previous_summaries(chapters)

            # 尝试生成当前章，最多重试 MAX_GENERATE_RETRY 次
            chapter_result = None
            final_audit_result = None
            chapter_passed = False

            for attempt in range(1, MAX_GENERATE_RETRY + 1):
                try:
                    # 1. 生成章节
                    print(f"[BatchCoordinator] 第{chapter_num}章 - 第{attempt}次生成尝试")
                    chapter_result = self.writer.generate_chapter(
                        chapter_plan, genre, style_guide, previous_summaries
                    )

                    # 检查生成是否出错
                    if chapter_result.get("error"):
                        print(f"[BatchCoordinator] 第{chapter_num}章生成出错: {chapter_result['error']}")
                        continue

                    chapter_content = chapter_result.get("chapter_content", "")

                    # 2. 审计章节（Revisor内部执行最多3轮审计-修订循环）
                    audit_result = self.auditor.audit_chapter(
                        chapter_content, chapter_num, genre, style_guide
                    )

                    if not audit_result.get("overall_pass", False):
                        # 审计不通过，交给Revisor进行修订（Revisor内部最多3轮）
                        print(f"[BatchCoordinator] 第{chapter_num}章审计不通过，进入修订流程")
                        revision_result = self.revisor.revise_chapter(
                            chapter_content, chapter_num, genre, audit_result, style_guide
                        )

                        chapter_content = revision_result.get("revised_content", chapter_content)
                        final_audit_result = revision_result.get("final_audit_report", audit_result)

                        # 用修订后的内容更新chapter_result
                        chapter_result["chapter_content"] = chapter_content
                        chapter_result["word_count"] = len(chapter_content)
                        chapter_result["revision_info"] = {
                            "fixes_applied": revision_result.get("fixes_applied", []),
                            "audit_rounds": revision_result.get("audit_rounds", 0),
                            "final_pass": revision_result.get("final_pass", False)
                        }
                    else:
                        final_audit_result = audit_result

                    # 3. 检查最终审计结果
                    if final_audit_result and final_audit_result.get("overall_pass", False):
                        chapter_passed = True
                        break
                    else:
                        print(f"[BatchCoordinator] 第{chapter_num}章第{attempt}次尝试未通过审计")
                        # 如果还有重试机会，继续循环
                        if attempt < MAX_GENERATE_RETRY:
                            print(f"[BatchCoordinator] 将进行第{attempt + 1}次重试")
                        continue

                except Exception as e:
                    print(f"[BatchCoordinator] 第{chapter_num}章第{attempt}次尝试异常: {e}")
                    continue

            # 4. 处理最终结果
            if chapter_passed and chapter_result:
                # 章节通过，更新真相文件
                self._update_truth_files(chapter_result, chapter_num)

                # 记录成功结果
                chapters.append({
                    "chapter_num": chapter_num,
                    "chapter_title": chapter_title,
                    "chapter_content": chapter_result.get("chapter_content", ""),
                    "word_count": chapter_result.get("word_count", 0),
                    "attempt_count": attempt,
                    "status": "passed"
                })
                audit_results.append(final_audit_result)
                success_count += 1
                print(f"[BatchCoordinator] 第{chapter_num}章生成成功（第{attempt}次尝试）")
            else:
                # 章节最终未通过，记录失败但不影响后续章节
                failed_chapters.append(chapter_num)

                # 即使未通过，如果有内容也记录下来（标记为failed）
                if chapter_result and chapter_result.get("chapter_content"):
                    chapters.append({
                        "chapter_num": chapter_num,
                        "chapter_title": chapter_title,
                        "chapter_content": chapter_result.get("chapter_content", ""),
                        "word_count": chapter_result.get("word_count", 0),
                        "attempt_count": attempt,
                        "status": "failed",
                        "fail_reason": "审计未通过"
                    })
                    audit_results.append(final_audit_result or {})
                    # 即使未通过也更新真相文件，避免后续章节缺少上下文
                    self._update_truth_files(chapter_result, chapter_num)
                    print(f"[BatchCoordinator] 第{chapter_num}章审计未通过，已记录并继续后续章节")
                else:
                    chapters.append({
                        "chapter_num": chapter_num,
                        "chapter_title": chapter_title,
                        "chapter_content": "",
                        "word_count": 0,
                        "attempt_count": attempt,
                        "status": "error",
                        "fail_reason": "生成失败"
                    })
                    audit_results.append({})
                    print(f"[BatchCoordinator] 第{chapter_num}章生成失败，跳过并继续后续章节")

        # 5. 跨章一致性检查
        cross_chapter_check = self.check_cross_chapter_consistency(chapters, genre)

        # 6. 自动导出为 Markdown 文件
        export_result = self._auto_export(chapters)

        return {
            "chapters": chapters,
            "audit_results": audit_results,
            "cross_chapter_check": cross_chapter_check,
            "success_count": success_count,
            "failed_chapters": failed_chapters,
            "total_count": len(chapter_plans),
            "generated_at": datetime.now().isoformat(),
            "export_result": export_result
        }

    def _auto_export(self, chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        自动生成 Markdown 文件

        实现逻辑:
        1. 获取导出器实例
        2. 生成输出文件名（包含时间戳）
        3. 导出所有章节为单个 Markdown 文件
        4. 返回导出结果

        Args:
            chapters: 生成的章节列表

        Returns:
            导出结果字典
        """
        if not chapters:
            return {"exported": False, "error": "无章节可导出"}

        try:
            exporter = get_exporter()

            # 生成输出文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(config.DATA_DIR, f"novel_{timestamp}.md")

            # 导出为 Markdown
            result = exporter.export_markdown(chapters, output_file)

            if result.get("exported"):
                print(f"[BatchCoordinator] 章节已导出到: {output_file}")
            else:
                print(f"[BatchCoordinator] 导出失败: {result.get('error')}")

            return result

        except Exception as e:
            print(f"[BatchCoordinator] 自动导出异常: {e}")
            return {"exported": False, "error": str(e)}

    def _collect_previous_summaries(self, chapters: List[Dict[str, Any]]) -> List[str]:
        """
        收集前文摘要，为当前章提供上下文

        实现逻辑:
        1. 从已生成的章节中提取摘要信息
        2. 每章取前200字作为摘要（简化处理）
        3. 最多返回最近5章的摘要

        Args:
            chapters: 已生成的章节列表

        Returns:
            前文摘要列表
        """
        summaries = []
        # 取最近5章的摘要
        for chapter in chapters[-5:]:
            content = chapter.get("chapter_content", "")
            if content:
                # 取前200字作为摘要
                summary = content[:200] + "..." if len(content) > 200 else content
                summaries.append(f"第{chapter.get('chapter_num', '?')}章: {summary}")
        return summaries

    def _update_truth_files(self, chapter_result: Dict[str, Any], chapter_num: int):
        """
        更新真相文件（每章完成后调用）

        实现逻辑:
        1. 从章节结算表（settlement）中提取信息
        2. 更新角色矩阵 - 应用角色状态变更
        3. 更新剧情进度 - 追加事件记录
        4. 更新伏笔状态 - 应用伏笔变更
        5. 更新时间线 - 追加时间线事件
        6. 保存真相文件

        Args:
            chapter_result: 章节生成结果（包含settlement结算表）
            chapter_num: 章节号
        """
        settlement = chapter_result.get("settlement", {})
        if not settlement:
            print(f"[BatchCoordinator] 第{chapter_num}章无结算表，跳过真相文件更新")
            return

        # 1. 更新角色矩阵
        try:
            character_matrix = self.truth_files.get_file("character_matrix")
            new_states = settlement.get("new_character_states", [])
            characters = character_matrix.get("characters", {})

            for state in new_states:
                # state 可能是字符串描述或字典
                if isinstance(state, dict):
                    char_id = state.get("character_id", "")
                    if char_id and char_id in characters:
                        # 合并状态变更
                        if "state_changes" in state:
                            char_data = characters[char_id]
                            char_data.update(state["state_changes"])
                            char_data["last_updated_chapter"] = chapter_num
                    elif char_id:
                        # 新角色，添加到矩阵
                        characters[char_id] = {
                            "name": state.get("name", char_id),
                            "states": state.get("state_changes", {}),
                            "first_appearance": chapter_num,
                            "last_updated_chapter": chapter_num
                        }
                elif isinstance(state, str):
                    # 字符串形式的状态描述，记录到日志
                    print(f"[BatchCoordinator] 角色状态变更: {state}")

            character_matrix["characters"] = characters
            self.truth_files.update_file("character_matrix", character_matrix)
        except Exception as e:
            print(f"[BatchCoordinator] 更新角色矩阵失败: {e}")

        # 2. 更新剧情进度
        try:
            plot_progress = self.truth_files.get_file("plot_progress")
            event_summary = settlement.get("event_summary", "")
            if "events" not in plot_progress:
                plot_progress["events"] = []

            plot_progress["events"].append({
                "id": f"ch{chapter_num}_event",
                "chapter": chapter_num,
                "summary": event_summary,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            self.truth_files.update_file("plot_progress", plot_progress)
        except Exception as e:
            print(f"[BatchCoordinator] 更新剧情进度失败: {e}")

        # 3. 更新伏笔状态
        try:
            foreshadow_hooks = self.truth_files.get_file("foreshadow_hooks")
            foreshadow_changes = settlement.get("foreshadow_changes", [])

            if "foreshadows" not in foreshadow_hooks:
                foreshadow_hooks["foreshadows"] = []

            foreshadows = foreshadow_hooks["foreshadows"]

            for change in foreshadow_changes:
                if isinstance(change, dict):
                    fs_name = change.get("foreshadow_name", "")
                    fs_status = change.get("status", "")
                    # 查找并更新已有伏笔
                    for fs in foreshadows:
                        if fs.get("foreshadow_name") == fs_name:
                            fs["status"] = fs_status
                            fs["last_updated_chapter"] = chapter_num
                            break
                elif isinstance(change, str):
                    print(f"[BatchCoordinator] 伏笔变更: {change}")

            self.truth_files.update_file("foreshadow_hooks", foreshadow_hooks)
        except Exception as e:
            print(f"[BatchCoordinator] 更新伏笔状态失败: {e}")

        # 4. 更新时间线
        try:
            timeline = self.truth_files.get_file("timeline")
            event_summary = settlement.get("event_summary", "")

            if "events" not in timeline:
                timeline["events"] = []

            timeline["events"].append({
                "id": f"ch{chapter_num}_timeline",
                "chapter": chapter_num,
                "time": chapter_num,  # 简化处理，用章节号作为时间
                "event": event_summary,
                "timestamp": datetime.now().isoformat()
            })
            self.truth_files.update_file("timeline", timeline)
        except Exception as e:
            print(f"[BatchCoordinator] 更新时间线失败: {e}")

        # 5. 更新资源账本（如果有新增物品/道具）
        try:
            resource_ledger = self.truth_files.get_file("resource_ledger")
            key_items = settlement.get("key_items", [])

            if "items" not in resource_ledger:
                resource_ledger["items"] = []
            if "transactions" not in resource_ledger:
                resource_ledger["transactions"] = []

            for item_name in key_items:
                if isinstance(item_name, str) and item_name:
                    item_id = f"ch{chapter_num}_{item_name}"
                    resource_ledger["items"].append({
                        "id": item_id,
                        "name": item_name,
                        "introduced_chapter": chapter_num
                    })
                    resource_ledger["transactions"].append({
                        "item_id": item_id,
                        "type": "create",
                        "chapter": chapter_num,
                        "timestamp": datetime.now().isoformat()
                    })

            self.truth_files.update_file("resource_ledger", resource_ledger)
        except Exception as e:
            print(f"[BatchCoordinator] 更新资源账本失败: {e}")

        # 6. 保存所有真相文件
        try:
            self.truth_files.save_all()
            print(f"[BatchCoordinator] 第{chapter_num}章真相文件已更新并保存")
        except Exception as e:
            print(f"[BatchCoordinator] 保存真相文件失败: {e}")

    def check_cross_chapter_consistency(self, chapters: List[Dict[str, Any]],
                                       genre: str) -> Dict[str, Any]:
        """
        跨章一致性检查

        实现逻辑:
        1. 检查章节号连续性
        2. 使用TruthFiles.cross_validate()进行真相文件交叉验证
           - 角色认知边界检查
           - 物品流转检查
           - 时间线一致性检查
           - 世界规则一致性检查
        3. 使用LLM检查角色状态变化的连续性
        4. 使用LLM检查伏笔推进的合理性
        5. 使用LLM检查时间线的连续性
        6. 使用LLM检查剧情的整体连贯性

        Args:
            chapters: 生成的章节列表
            genre: 题材名称

        Returns:
            跨章一致性检查结果字典
        """
        issues = []
        warnings = []

        # 1. 检查章节数量
        if len(chapters) < 2:
            return {
                "pass": True,
                "issues": [],
                "warnings": [],
                "note": "章节数少于2，跳过跨章检查"
            }

        # 2. 检查章节号连续性
        for i in range(len(chapters) - 1):
            current_num = chapters[i].get("chapter_num", 0)
            next_num = chapters[i + 1].get("chapter_num", 0)
            if next_num != current_num + 1:
                issues.append(f"章节号不连续: 第{current_num}章后是第{next_num}章")

        # 3. 使用TruthFiles.cross_validate()进行真相文件交叉验证
        try:
            truth_issues = self.truth_files.cross_validate()
            issues.extend(truth_issues)
        except Exception as e:
            print(f"[BatchCoordinator] 真相文件交叉验证失败: {e}")
            warnings.append(f"真相文件交叉验证异常: {e}")

        # 4. 使用LLM检查跨章内容一致性
        # 构建章节内容摘要用于LLM检查
        chapter_summaries = []
        for chapter in chapters:
            chapter_num = chapter.get("chapter_num", 0)
            content = chapter.get("chapter_content", "")
            status = chapter.get("status", "unknown")
            if status == "passed" and content:
                # 取前1500字作为摘要，平衡上下文长度和信息量
                summary = content[:1500]
                chapter_summaries.append({
                    "chapter_num": chapter_num,
                    "summary": summary
                })

        if len(chapter_summaries) >= 2:
            # 4a. 检查角色状态变化连续性
            character_issues = self._check_character_continuity(chapter_summaries, genre)
            issues.extend(character_issues)

            # 4b. 检查伏笔推进合理性
            foreshadow_issues = self._check_foreshadow_progression(chapter_summaries, genre)
            issues.extend(foreshadow_issues)

            # 4c. 检查时间线连续性
            timeline_issues = self._check_timeline_continuity(chapter_summaries, genre)
            issues.extend(timeline_issues)

            # 4d. 检查剧情整体连贯性
            plot_issues = self._check_plot_continuity(chapter_summaries, genre)
            issues.extend(plot_issues)

        return {
            "pass": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "checked_chapters": [ch.get("chapter_num") for ch in chapters],
            "checked_at": datetime.now().isoformat()
        }

    def _check_character_continuity(self, chapter_summaries: List[Dict],
                                    genre: str) -> List[str]:
        """
        检查角色状态变化的跨章连续性

        使用LLM检查角色在不同章节间的状态变化是否合理、连续。

        Args:
            chapter_summaries: 章节摘要列表
            genre: 题材名称

        Returns:
            问题描述列表
        """
        prompt = f"""检查以下多章内容中角色状态变化的跨章连续性。

题材: {genre}

"""
        for cs in chapter_summaries:
            prompt += f"\n第{cs['chapter_num']}章内容摘要:\n{cs['summary']}...\n"

        prompt += """
请检查:
1. 角色性格变化是否有合理的过渡
2. 角色能力/等级提升是否合理
3. 角色关系变化是否有铺垫
4. 是否有角色突然消失或性格突变

以JSON格式返回:
{
    "issues": ["问题1", "问题2"]
}

只返回JSON对象。如果没有问题，返回 {"issues": []}"""

        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            raw_issues = result.get("issues", [])
            return [f"角色连续性: {issue}" for issue in raw_issues]
        except Exception as e:
            print(f"[BatchCoordinator] 角色连续性检查失败: {e}")
            return []

    def _check_foreshadow_progression(self, chapter_summaries: List[Dict],
                                      genre: str) -> List[str]:
        """
        检查伏笔推进的跨章合理性

        使用LLM检查伏笔在不同章节间的埋设、触发、回收是否合理。

        Args:
            chapter_summaries: 章节摘要列表
            genre: 题材名称

        Returns:
            问题描述列表
        """
        prompt = f"""检查以下多章内容中伏笔推进的跨章合理性。

题材: {genre}

"""
        for cs in chapter_summaries:
            prompt += f"\n第{cs['chapter_num']}章内容摘要:\n{cs['summary']}...\n"

        prompt += """
请检查:
1. 已埋设的伏笔是否有推进
2. 是否有伏笔被遗忘（埋了没收）
3. 伏笔的触发是否自然
4. 伏笔密度是否合理

以JSON格式返回:
{
    "issues": ["问题1", "问题2"]
}

只返回JSON对象。如果没有问题，返回 {"issues": []}"""

        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            raw_issues = result.get("issues", [])
            return [f"伏笔推进: {issue}" for issue in raw_issues]
        except Exception as e:
            print(f"[BatchCoordinator] 伏笔推进检查失败: {e}")
            return []

    def _check_timeline_continuity(self, chapter_summaries: List[Dict],
                                   genre: str) -> List[str]:
        """
        检查时间线的跨章连续性

        使用LLM检查事件时间顺序在不同章节间是否矛盾。

        Args:
            chapter_summaries: 章节摘要列表
            genre: 题材名称

        Returns:
            问题描述列表
        """
        prompt = f"""检查以下多章内容中时间线的跨章连续性。

题材: {genre}

"""
        for cs in chapter_summaries:
            prompt += f"\n第{cs['chapter_num']}章内容摘要:\n{cs['summary']}...\n"

        prompt += """
请检查:
1. 事件时间顺序是否矛盾
2. 是否有时间跳跃未说明
3. 是否有因果倒置
4. 时间描述是否一致（如白天/黑夜、季节等）

以JSON格式返回:
{
    "issues": ["问题1", "问题2"]
}

只返回JSON对象。如果没有问题，返回 {"issues": []}"""

        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            raw_issues = result.get("issues", [])
            return [f"时间线连续性: {issue}" for issue in raw_issues]
        except Exception as e:
            print(f"[BatchCoordinator] 时间线连续性检查失败: {e}")
            return []

    def _check_plot_continuity(self, chapter_summaries: List[Dict],
                               genre: str) -> List[str]:
        """
        检查剧情的跨章整体连贯性

        使用LLM检查多章内容的剧情是否连贯、是否有矛盾。

        Args:
            chapter_summaries: 章节摘要列表
            genre: 题材名称

        Returns:
            问题描述列表
        """
        prompt = f"""检查以下多章内容的剧情跨章连贯性。

题材: {genre}

"""
        for cs in chapter_summaries:
            prompt += f"\n第{cs['chapter_num']}章内容摘要:\n{cs['summary']}...\n"

        prompt += """
请检查:
1. 剧情是否有连贯的推进
2. 前后章节是否有矛盾之处
3. 是否有情节断裂
4. 节奏是否合理

以JSON格式返回:
{
    "issues": ["问题1", "问题2"]
}

只返回JSON对象。如果没有问题，返回 {"issues": []}"""

        try:
            response = self.llm_client.generate(prompt)
            result = json.loads(response)
            raw_issues = result.get("issues", [])
            return [f"剧情连贯性: {issue}" for issue in raw_issues]
        except Exception as e:
            print(f"[BatchCoordinator] 剧情连贯性检查失败: {e}")
            return []

    def generate_batch_report(self, batch_result: Dict[str, Any]) -> str:
        """
        生成批量生成报告

        Args:
            batch_result: 批量生成结果字典

        Returns:
            Markdown格式的报告
        """
        report = "# 批量生成报告\n\n"

        # 总体统计
        success_count = batch_result.get("success_count", 0)
        total_count = batch_result.get("total_count", 0)
        failed_chapters = batch_result.get("failed_chapters", [])
        report += f"## 总体统计\n\n"
        report += f"- 成功生成: {success_count}/{total_count}章\n"
        report += f"- 成功率: {success_count/total_count*100:.1f}%\n\n" if total_count > 0 else "- 成功率: 0%\n\n"

        if failed_chapters:
            report += f"- 失败章节: {', '.join([str(c) for c in failed_chapters])}\n\n"

        # 各章节结果
        chapters = batch_result.get("chapters", [])
        if chapters:
            report += "## 生成章节列表\n\n"
            for chapter in chapters:
                chapter_num = chapter.get("chapter_num", 0)
                chapter_title = chapter.get("chapter_title", "未知")
                word_count = chapter.get("word_count", 0)
                status = chapter.get("status", "unknown")
                attempt_count = chapter.get("attempt_count", 0)
                status_icon = "PASS" if status == "passed" else "FAIL" if status == "failed" else "ERR"
                report += f"### 第{chapter_num}章: {chapter_title} [{status_icon}]\n"
                report += f"- 字数: {word_count}\n"
                report += f"- 尝试次数: {attempt_count}\n"
                report += f"- 状态: {status}\n"
                fail_reason = chapter.get("fail_reason", "")
                if fail_reason:
                    report += f"- 失败原因: {fail_reason}\n"
                report += "\n"

        # 跨章一致性检查
        cross_check = batch_result.get("cross_chapter_check", {})
        if cross_check:
            report += "## 跨章一致性检查\n\n"
            passed = cross_check.get("pass", False)
            report += f"### 结果: {'PASS' if passed else 'FAIL'}\n\n"

            issues = cross_check.get("issues", [])
            if issues:
                report += "### 问题\n\n"
                for issue in issues:
                    report += f"- {issue}\n"
                report += "\n"

            warnings = cross_check.get("warnings", [])
            if warnings:
                report += "### 警告\n\n"
                for warning in warnings:
                    report += f"- {warning}\n"
                report += "\n"

        return report


# 全局实例
_batch_coordinator = None


def get_batch_coordinator() -> BatchCoordinator:
    """获取全局批量生成协调器实例（单例模式）"""
    global _batch_coordinator
    if _batch_coordinator is None:
        _batch_coordinator = BatchCoordinator()
    return _batch_coordinator
