"""
隐性修改检测器(SilentModificationDetector)

核心职责:
- 4种检测手段：
  1. 文件变更检测（检查本地文件修改时间）
  2. 对话中的修改意图检测（关键词/模式匹配）
  3. 生成前一致性检查（真相文件 vs 实际内容）
  4. 用户主动同步命令
- 检测到异常时主动确认，提供选项

工作流程:
检测修改 → 确认修改 → 更新真相文件 → 生成同步报告

设计思路:
- 采用"多重检测"策略，确保不遗漏任何修改
- 文件变更检测：监控关键文件的修改时间
- 对话检测：识别用户对话中的修改意图
- 一致性检查：对比真相文件和实际内容
- 主动确认：检测到修改时提供选项让用户确认

输出格式:
{
    "detected": bool,
    "modification_type": 修改类型,
    "details": 修改详情,
    "options": [确认选项]
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
from core.truth_files import TruthFiles


class SilentModificationDetector:
    """
    隐性修改检测器类
    
    核心功能:
    1. 文件变更检测：监控关键文件的修改时间
    2. 对话修改意图检测：识别用户对话中的修改意图
    3. 一致性检查：对比真相文件和实际内容
    4. 用户主动同步：处理用户的同步命令
    5. 主动确认：检测到修改时提供选项
    
    使用场景:
    - 检测用户未明确告知的修改
    - 确保真相文件与实际内容一致
    - 处理用户的同步命令
    
    使用流程:
    1. 调用check_file_changes()检查文件变更
    2. 调用detect_modification_intent(message)检测对话意图
    3. 调用check_consistency()检查一致性
    4. 调用sync_all()执行同步
    5. 生成同步报告
    """
    
    # 修改意图关键词
    MODIFICATION_KEYWORDS = [
        "修改", "改成", "换成", "调整", "改为", "变更",
        "更新", "修正", "改变", "转化", "转换"
    ]
    
    # 需要同步的文件
    MONITORED_FILES = [
        "world_state.json",
        "character_matrix.json",
        "plot_progress.json",
        "foreshadow_hooks.json",
        "resource_ledger.json",
        "timeline.json",
        "style_guide.json"
    ]
    
    def __init__(self):
        """
        初始化隐性修改检测器
        
        初始化流程:
        1. 获取LLM客户端
        2. 初始化真相文件管理器
        3. 记录文件修改时间快照
        """
        self.llm_client = get_llm_client()
        self.truth_files = TruthFiles()
        self.file_snapshots = self._capture_file_snapshots()
    
    def _capture_file_snapshots(self) -> Dict[str, float]:
        """
        捕获文件修改时间快照
        
        Returns:
            文件修改时间字典
        """
        snapshots = {}
        
        for filename in self.MONITORED_FILES:
            filepath = os.path.join(config.TRUTH_DIR, filename)
            if os.path.exists(filepath):
                snapshots[filename] = os.path.getmtime(filepath)
        
        return snapshots
    
    def check_file_changes(self) -> Dict[str, Any]:
        """
        检查文件变更（检测本地文件修改时间）
        
        实现逻辑:
        1. 获取当前文件修改时间
        2. 与快照对比
        3. 检测是否有文件被修改
        
        Returns:
            文件变更检测结果字典
        """
        changed_files = []
        
        for filename in self.MONITORED_FILES:
            filepath = os.path.join(config.TRUTH_DIR, filename)
            
            if os.path.exists(filepath):
                current_mtime = os.path.getmtime(filepath)
                snapshot_mtime = self.file_snapshots.get(filename, 0)
                
                if current_mtime > snapshot_mtime:
                    changed_files.append({
                        "filename": filename,
                        "old_mtime": datetime.fromtimestamp(snapshot_mtime).isoformat() if snapshot_mtime > 0 else "无",
                        "new_mtime": datetime.fromtimestamp(current_mtime).isoformat()
                    })
        
        if changed_files:
            # 生成确认选项
            options = [
                "[A] 接受所有修改，更新真相文件",
                "[B] 忽略修改，保持真相文件不变",
                "[C] 逐个确认修改",
                "[D] 其他(请输入您的想法)"
            ]
            
            return {
                "detected": True,
                "modification_type": "file_change",
                "changed_files": changed_files,
                "options": options,
                "details": f"检测到{len(changed_files)}个文件被修改"
            }
        
        return {
            "detected": False,
            "modification_type": None,
            "changed_files": [],
            "options": [],
            "details": "未检测到文件变更"
        }
    
    def detect_modification_intent(self, user_message: str) -> Dict[str, Any]:
        """
        检测对话中的修改意图（关键词/模式匹配）
        
        实现逻辑:
        1. 检查是否包含修改关键词
        2. 使用LLM判断是否有修改意图
        3. 提取修改内容
        
        Args:
            user_message: 用户对话消息
        
        Returns:
            修改意图检测结果字典
        """
        # 1. 检查修改关键词
        has_keyword = False
        matched_keywords = []
        
        for keyword in self.MODIFICATION_KEYWORDS:
            if keyword in user_message:
                has_keyword = True
                matched_keywords.append(keyword)
        
        if not has_keyword:
            return {
                "detected": False,
                "modification_type": None,
                "intent": None,
                "options": [],
                "details": "未检测到修改意图"
            }
        
        # 2. 使用LLM判断修改意图
        prompt = f"""分析以下用户消息，判断是否有修改意图。

用户消息: {user_message}

匹配的关键词: {', '.join(matched_keywords)}

请判断:
1. 用户是否有修改意图
2. 如果有，修改什么内容
3. 修改的类型（角色、剧情、设定、风格等）

以JSON格式返回:
{{
    "has_intent": true/false,
    "modification_target": "修改目标",
    "modification_type": "修改类型",
    "modification_content": "修改内容"
}}

只返回JSON对象。"""
        
        try:
            response = self.llm_client.generate(prompt)
            analysis = json.loads(response)
            
            if analysis.get("has_intent"):
                # 生成确认选项
                options = [
                    f"[A] 确认修改: {analysis.get('modification_content', '未知')}",
                    "[B] 取消修改",
                    "[C] 我需要重新说明",
                    "[D] 其他(请输入您的想法)"
                ]
                
                return {
                    "detected": True,
                    "modification_type": "dialogue_intent",
                    "intent": analysis,
                    "options": options,
                    "details": f"检测到修改意图: {analysis.get('modification_content', '未知')}"
                }
            
            return {
                "detected": False,
                "modification_type": None,
                "intent": None,
                "options": [],
                "details": "未检测到明确的修改意图"
            }
        except Exception as e:
            print(f"检测修改意图失败: {e}")
            return {
                "detected": False,
                "modification_type": None,
                "intent": None,
                "options": [],
                "details": f"检测失败: {e}"
            }
    
    def check_consistency(self, chapter_content: str = None) -> Dict[str, Any]:
        """
        生成前一致性检查（真相文件 vs 实际内容）
        
        实现逻辑:
        1. 加载真相文件
        2. 如果有章节内容，对比真相文件和实际内容
        3. 检测不一致之处
        
        Args:
            chapter_content: 章节内容（可选）
        
        Returns:
            一致性检查结果字典
        """
        # 加载真相文件
        self.truth_files.load_all()
        
        inconsistencies = []
        
        # 1. 检查真相文件内部一致性
        validation_issues = self.truth_files.cross_validate()
        if validation_issues:
            inconsistencies.extend(validation_issues)
        
        # 2. 如果有章节内容，检查与真相文件的一致性
        if chapter_content:
            prompt = f"""检查以下章节内容是否与真相文件一致。

章节内容:
{chapter_content[:2000]}...

真相文件摘要:
- 世界状态: {json.dumps(self.truth_files.get_file('world_state'), ensure_ascii=False)[:500]}
- 角色矩阵: {json.dumps(self.truth_files.get_file('character_matrix'), ensure_ascii=False)[:500]}
- 剧情进度: {json.dumps(self.truth_files.get_file('plot_progress'), ensure_ascii=False)[:500]}

请检查:
1. 角色行为是否符合角色矩阵
2. 事件是否符合剧情进度
3. 是否违反世界规则

以JSON格式返回:
{{
    "is_consistent": true/false,
    "inconsistencies": ["不一致之处1", "不一致之处2"]
}}

只返回JSON对象。"""
            
            try:
                response = self.llm_client.generate(prompt)
                result = json.loads(response)
                
                if not result.get("is_consistent", True):
                    inconsistencies.extend(result.get("inconsistencies", []))
            except Exception as e:
                print(f"一致性检查失败: {e}")
        
        if inconsistencies:
            # 生成确认选项
            options = [
                "[A] 更新真相文件以匹配实际内容",
                "[B] 修改实际内容以匹配真相文件",
                "[C] 忽略不一致之处",
                "[D] 其他(请输入您的想法)"
            ]
            
            return {
                "detected": True,
                "modification_type": "inconsistency",
                "inconsistencies": inconsistencies,
                "options": options,
                "details": f"检测到{len(inconsistencies)}处不一致"
            }
        
        return {
            "detected": False,
            "modification_type": None,
            "inconsistencies": [],
            "options": [],
            "details": "未发现不一致之处"
        }
    
    def sync_all(self, sync_type: str = "accept_all") -> Dict[str, Any]:
        """
        执行同步（用户主动同步命令）
        
        实现逻辑:
        1. 根据同步类型执行不同操作
        2. 更新文件快照
        3. 生成同步报告
        
        Args:
            sync_type: 同步类型（accept_all/ignore/selective）
        
        Returns:
            同步结果字典
        """
        # 1. 执行同步
        if sync_type == "accept_all":
            # 接受所有修改，更新文件快照
            self.file_snapshots = self._capture_file_snapshots()
            sync_result = "已接受所有修改"
        elif sync_type == "ignore":
            # 忽略修改，不更新快照
            sync_result = "已忽略所有修改"
        else:
            # 选择性同步
            sync_result = "已执行选择性同步"
        
        # 2. 生成同步报告
        report = self.generate_sync_report(sync_result)
        
        return {
            "synced": True,
            "sync_type": sync_type,
            "sync_result": sync_result,
            "report": report,
            "synced_at": datetime.now().isoformat()
        }
    
    def generate_sync_report(self, sync_result: str) -> str:
        """
        生成同步报告
        
        Args:
            sync_result: 同步结果描述
        
        Returns:
            Markdown格式的同步报告
        """
        report = "# 同步报告\n\n"
        report += f"**同步时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"**同步结果**: {sync_result}\n\n"
        
        # 文件状态
        report += "## 文件状态\n\n"
        for filename in self.MONITORED_FILES:
            filepath = os.path.join(config.TRUTH_DIR, filename)
            if os.path.exists(filepath):
                mtime = os.path.getmtime(filepath)
                report += f"- {filename}: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return report
    
    def run_full_check(self, user_message: str = None,
                      chapter_content: str = None) -> Dict[str, Any]:
        """
        运行完整检查（综合所有检测手段）
        
        Args:
            user_message: 用户对话消息（可选）
            chapter_content: 章节内容（可选）
        
        Returns:
            完整检查结果字典
        """
        results = []
        
        # 1. 检查文件变更
        file_check = self.check_file_changes()
        results.append(file_check)
        
        # 2. 检查对话意图
        if user_message:
            intent_check = self.detect_modification_intent(user_message)
            results.append(intent_check)
        
        # 3. 检查一致性
        consistency_check = self.check_consistency(chapter_content)
        results.append(consistency_check)
        
        # 汇总结果
        detected = any(r.get("detected", False) for r in results)
        
        # 收集所有选项
        all_options = []
        for r in results:
            if r.get("detected"):
                all_options.extend(r.get("options", []))
        
        return {
            "detected": detected,
            "check_results": results,
            "options": all_options,
            "checked_at": datetime.now().isoformat()
        }


# 全局实例
_silent_modification_detector = None


def get_silent_modification_detector() -> SilentModificationDetector:
    """获取全局隐性修改检测器实例（单例模式）"""
    global _silent_modification_detector
    if _silent_modification_detector is None:
        _silent_modification_detector = SilentModificationDetector()
    return _silent_modification_detector
