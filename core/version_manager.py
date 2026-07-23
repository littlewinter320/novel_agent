"""
版本管理引擎模块

核心职责：
- 实现版本快照、对比、回滚、混合版本功能
- 管理小说创作过程中的版本历史
- 支持部分回滚和混合版本创建（从多个版本提取字段合并）
- 提供版本索引和快速查询

设计思路：
- 每个版本存储为独立的JSON文件，包含完整内容和元数据
- 使用索引文件（_index.json）快速查询版本历史
- 版本号采用语义化版本控制（v1, v2, v2.1, v2.2等）
- 支持基于父版本的子版本创建（用于分支开发）

关键算法：
- 版本号生成：基于内容类型和父版本号生成下一个版本号
- 差异对比：使用difflib.unified_diff生成文本差异
- 部分回滚：合并目标版本和最新版本的指定字段
- 混合版本：从多个版本提取指定字段合并为新版本

使用场景：
- 用户对某个版本不满意，回滚到之前的版本
- 比较两个版本的差异，查看修改内容
- 从多个版本中提取最佳部分，创建混合版本
- 分支开发：基于某个版本创建子版本线
"""
import os
import json
import difflib
import re
from datetime import datetime

from config import VERSIONS_DIR


class VersionManager:
    """
    版本管理器
    
    核心功能：
    1. 版本快照：创建内容的完整快照并分配版本号
    2. 版本对比：比较两个版本的差异，生成结构化差异报告
    3. 版本回滚：回滚到指定版本（完全回滚或部分回滚）
    4. 混合版本：从多个版本提取字段合并为新版本
    5. 版本查询：列出版本历史、加载指定版本
    
    使用场景：
    - Writer Agent生成章节后创建快照
    - 用户修改大纲后创建新版本
    - 审计发现问题时回滚到之前的版本
    - 从多个版本中提取最佳部分创建混合版本
    """
    
    def __init__(self, versions_dir: str = None):
        """
        初始化版本管理器
        
        实现逻辑：
        1. 设置版本存储目录（使用配置或自定义路径）
        2. 确保目录存在
        3. 加载版本索引文件
        
        Args:
            versions_dir: 版本存储目录，如果为None则使用配置中的VERSIONS_DIR
        """
        self.versions_dir = versions_dir or VERSIONS_DIR
        os.makedirs(self.versions_dir, exist_ok=True)
        self._index = self._load_index()

    # ---------- 持久化索引 ----------
    def _index_path(self):
        """
        获取索引文件路径
        
        Returns:
            str: 索引文件的完整路径（_index.json）
        """
        return os.path.join(self.versions_dir, "_index.json")

    def _load_index(self):
        """
        加载版本索引文件
        
        实现逻辑：
        1. 检查索引文件是否存在
        2. 如果存在，读取JSON内容
        3. 如果不存在，返回空索引结构
        
        Returns:
            dict: 版本索引，包含versions列表
        """
        p = self._index_path()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"versions": []}

    def _save_index(self):
        """
        保存版本索引文件
        
        实现逻辑：
        - 将self._index序列化为JSON并写入磁盘
        - 使用ensure_ascii=False确保中文正确保存
        - 使用indent=2使JSON文件格式化，便于人工查看
        """
        with open(self._index_path(), "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    # ---------- 版本号生成 ----------
    def _next_version(self, content_type: str) -> str:
        """
        生成下一个主版本号（v1, v2, v3...）
        
        核心算法：
        1. 遍历索引中所有版本，筛选出指定内容类型的版本
        2. 使用正则表达式提取主版本号（^v(\\d+)）
        3. 找到最大主版本号，加1得到下一个版本号
        4. 如果没有历史版本，从v1开始
        
        Args:
            content_type: 内容类型（如"outline"、"chapter_1"等）
        
        Returns:
            str: 下一个主版本号（如"v1"、"v2"等）
        
        示例：
            如果已有v1, v2, v3，则返回"v4"
        """
        majors = []
        for v in self._index["versions"]:
            if v["content_type"] == content_type:
                m = re.match(r"^v(\d+)", v["version"])
                if m:
                    majors.append(int(m.group(1)))
        next_major = (max(majors) + 1) if majors else 1
        return f"v{next_major}"

    def _next_sub_version(self, base_version: str) -> str:
        """
        基于父版本生成下一个子版本号（v2.1, v2.2...）
        
        核心算法：
        1. 从父版本号提取主版本号（如"v2" → 2）
        2. 遍历索引中所有版本，筛选出匹配主版本号的子版本
        3. 使用正则表达式提取子版本号（^v{base_num}\\.(\\d+)）
        4. 找到最大子版本号，加1得到下一个子版本号
        
        Args:
            base_version: 父版本号（如"v2"）
        
        Returns:
            str: 下一个子版本号（如"v2.1"、"v2.2"等）
        
        使用场景：
        - 基于某个版本创建分支版本
        - 部分回滚时创建新版本
        """
        base_num = int(re.match(r"^v(\d+)", base_version).group(1))
        subs = []
        pattern = re.compile(rf"^v{base_num}\.(\d+)")
        for v in self._index["versions"]:
            m = pattern.match(v["version"])
            if m:
                subs.append(int(m.group(1)))
        next_sub = (max(subs) + 1) if subs else 1
        return f"v{base_num}.{next_sub}"

    # ---------- 核心方法 ----------
    def create_snapshot(
        self,
        content_type: str,
        content: dict,
        change_summary: str,
        step: int = None,
        parent_version: str = None,
    ) -> str:
        """
        创建版本快照（核心方法）
        
        核心算法：
        1. 根据是否有父版本，决定生成主版本号还是子版本号
        2. 生成时间戳（格式：YYYYMMDD_HHMMSS）
        3. 构造文件名：{version}_{content_type}_{timestamp}.json
        4. 创建版本记录，包含元数据和完整内容
        5. 将记录写入JSON文件
        6. 更新索引文件
        7. 返回版本号
        
        Args:
            content_type: 内容类型（如"outline"、"chapter_1"等）
            content: 完整内容（字典格式）
            change_summary: 变更摘要（描述本次修改的内容）
            step: 工作流步骤（可选，用于追踪版本所处阶段）
            parent_version: 父版本号（可选，如果提供则创建子版本）
        
        Returns:
            str: 新创建的版本号（如"v1"、"v2.1"等）
        
        使用场景：
        - Writer Agent生成章节后创建快照
        - 用户修改大纲后创建新版本
        - 回滚操作时创建回滚快照
        """
        if parent_version:
            version = self._next_sub_version(parent_version)
        else:
            version = self._next_version(content_type)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{version}_{content_type}_{ts}.json"

        record = {
            "version": version,
            "content_type": content_type,
            "timestamp": ts,
            "step": step,
            "change_summary": change_summary,
            "parent_version": parent_version,
            "content": content,
            "filename": filename,
        }

        with open(os.path.join(self.versions_dir, filename), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        self._index["versions"].append({
            "version": version,
            "content_type": content_type,
            "timestamp": ts,
            "step": step,
            "change_summary": change_summary,
            "parent_version": parent_version,
            "filename": filename,
        })
        self._save_index()
        return version

    def list_versions(self, content_type: str = None) -> list:
        """
        列出版本历史（支持按类型筛选）
        
        核心算法：
        1. 从索引中获取所有版本记录
        2. 如果指定了content_type，则过滤出该类型的版本
        3. 返回版本列表的深拷贝（避免外部修改影响内部数据）
        
        Args:
            content_type: 内容类型（可选，如"outline"、"chapter_1"等）
        
        Returns:
            list: 版本记录列表，每个记录包含version、content_type、timestamp等字段
        
        使用场景：
        - 用户查看所有历史版本
        - 查看某个章节的所有版本
        """
        versions = self._index["versions"]
        if content_type:
            versions = [v for v in versions if v["content_type"] == content_type]
        return [dict(v) for v in versions]

    def load_version(self, version: str) -> dict:
        """
        加载指定版本的完整内容
        
        核心算法：
        1. 遍历索引查找匹配的版本号
        2. 根据文件名构造完整路径
        3. 读取JSON文件并返回完整内容
        
        Args:
            version: 版本号（如"v1"、"v2.1"等）
        
        Returns:
            dict: 版本的完整内容（包含version、content_type、content等字段）
        
        Raises:
            ValueError: 版本号不存在
        
        使用场景：
        - 回滚前加载目标版本
        - 对比两个版本时加载内容
        """
        for v in self._index["versions"]:
            if v["version"] == version:
                path = os.path.join(self.versions_dir, v["filename"])
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        raise ValueError(f"Version {version} not found")

    def compare(self, version1: str, version2: str) -> dict:
        """
        比较两个版本的差异（核心算法）
        
        核心算法：
        1. 加载两个版本的完整内容
        2. 获取所有内容字段的并集
        3. 对每个字段进行对比：
           - 如果字段值相同（JSON序列化后比较），跳过
           - 如果是文本类型，使用difflib生成unified diff
           - 如果字段只在一个版本中存在，标记为added/removed
           - 如果字段在两个版本中都存在但值不同，标记为modified
        4. 生成差异摘要（统计新增/删除/修改的数量）
        
        Args:
            version1: 第一个版本号
            version2: 第二个版本号
        
        Returns:
            dict: 差异报告，包含：
                - version1, version2: 版本号
                - content_type_1, content_type_2: 内容类型
                - changes: 字段级别的差异详情
                - summary: 差异摘要（如"新增2项，修改3项"）
        
        使用场景：
        - 用户查看两个版本的差异
        - 审计时对比修改前后的变化
        """
        v1 = self.load_version(version1)
        v2 = self.load_version(version2)

        diffs = {}
        all_keys = set(list(v1["content"].keys()) + list(v2["content"].keys()))
        for key in all_keys:
            old = v1["content"].get(key)
            new = v2["content"].get(key)
            old_str = json.dumps(old, ensure_ascii=False, sort_keys=True) if old is not None else ""
            new_str = json.dumps(new, ensure_ascii=False, sort_keys=True) if new is not None else ""
            if old_str == new_str:
                continue
            # 文本差异
            if isinstance(old, str) and isinstance(new, str):
                diff_lines = list(difflib.unified_diff(
                    old.splitlines(), new.splitlines(),
                    fromfile=f"{version1}/{key}", tofile=f"{version2}/{key}",
                    lineterm=""
                ))
                diffs[key] = {
                    "type": "modified",
                    "diff": diff_lines,
                }
            elif old is None:
                diffs[key] = {"type": "added", "value": new}
            elif new is None:
                diffs[key] = {"type": "removed", "value": old}
            else:
                diffs[key] = {
                    "type": "modified",
                    "old": old,
                    "new": new,
                }

        return {
            "version1": version1,
            "version2": version2,
            "content_type_1": v1["content_type"],
            "content_type_2": v2["content_type"],
            "changes": diffs,
            "summary": self._summarize_changes(diffs),
        }

    def _summarize_changes(self, diffs: dict) -> str:
        """
        生成差异摘要（统计变更类型）
        
        核心算法：
        1. 遍历所有差异项
        2. 统计added/removed/modified的数量
        3. 生成中文摘要（如"新增2项，修改3项"）
        
        Args:
            diffs: 差异字典（compare方法的changes字段）
        
        Returns:
            str: 差异摘要文本
        """
        added = sum(1 for d in diffs.values() if d["type"] == "added")
        removed = sum(1 for d in diffs.values() if d["type"] == "removed")
        modified = sum(1 for d in diffs.values() if d["type"] == "modified")
        parts = []
        if added:
            parts.append(f"新增{added}项")
        if removed:
            parts.append(f"删除{removed}项")
        if modified:
            parts.append(f"修改{modified}项")
        return "，".join(parts) if parts else "无差异"

    def rollback(self, version: str) -> dict:
        """
        回滚到指定版本（完全回滚）
        
        核心算法：
        1. 加载目标版本的完整内容
        2. 基于目标版本创建新的快照（记录回滚操作）
        3. 返回目标版本的内容
        
        设计思路：
        - 回滚不是删除后续版本，而是创建一个新的版本
        - 新版本的内容与目标版本相同
        - 这样可以保留完整的版本历史
        
        Args:
            version: 目标版本号
        
        Returns:
            dict: 目标版本的内容
        
        使用场景：
        - 用户对当前版本不满意，想回到之前的版本
        - 发现某个版本有严重问题，需要回滚
        """
        v = self.load_version(version)
        # 创建回滚快照
        self.create_snapshot(
            content_type=v["content_type"],
            content=v["content"],
            change_summary=f"回滚到 {version}",
            step=v.get("step"),
            parent_version=version,
        )
        return v["content"]

    def partial_rollback(self, target_version: str, keep_elements: list) -> str:
        """
        部分回滚（选择性回滚）
        
        核心算法：
        1. 加载目标版本的完整内容
        2. 加载最新版本的完整内容
        3. 从目标版本复制所有内容
        4. 用最新版本中指定的字段覆盖目标版本的字段
        5. 创建新的版本快照
        
        设计思路：
        - 适用于"想回到某个版本,但保留某些最新修改"的场景
        - 例如：回到v2版本,但保留v3中的人物设定
        
        Args:
            target_version: 目标版本号（基础版本）
            keep_elements: 要从最新版本保留的字段列表
        
        Returns:
            str: 新创建的版本号
        
        使用场景：
        - 用户想回到某个历史版本,但想保留某些最新的修改
        - 混合使用不同版本的优点
        """
        target = self.load_version(target_version)
        # 取最新版本的 keep_elements
        latest = self._get_latest(target["content_type"])

        merged = dict(target["content"])
        for elem in keep_elements:
            if elem in latest["content"]:
                merged[elem] = latest["content"][elem]

        return self.create_snapshot(
            content_type=target["content_type"],
            content=merged,
            change_summary=f"部分回滚到 {target_version}，保留字段: {keep_elements}",
            step=target.get("step"),
            parent_version=target_version,
        )

    def create_mixed_version(
        self, sources: dict, content_type: str, change_summary: str
    ) -> str:
        """
        创建混合版本（从多个版本提取字段合并）
        
        核心算法：
        1. 遍历sources字典，每个键是版本号，值是要提取的字段列表
        2. 从每个版本中提取指定字段
        3. 将所有提取的字段合并到一个字典中
        4. 生成混合版本号（格式：{first_ver}_mixed_{timestamp}）
        5. 创建新版本快照
        
        设计思路：
        - 适用于"从多个版本中挑选最佳部分"的场景
        - 例如：从v1取人物设定，从v2取剧情大纲，从v3取世界观
        - 版本号使用第一个源版本作为前缀，便于追溯
        
        Args:
            sources: 源版本字典，格式 {version: [field1, field2, ...]}
                    例如：{"v1": ["characters", "world"], "v2": ["plot"]}
            content_type: 内容类型（如"outline"、"chapter_1"等）
            change_summary: 变更摘要（描述混合的来源和目的）
        
        Returns:
            str: 新创建的混合版本号
        
        使用场景：
        - 用户想从多个历史版本中挑选最佳部分
        - A/B测试后合并不同版本的优点
        - 回滚时保留某些最新修改
        """
        merged = {}
        for ver, fields in sources.items():
            v = self.load_version(ver)
            for f in fields:
                if f in v["content"]:
                    merged[f] = v["content"][f]

        # 找第一个源版本作为 parent
        first_ver = list(sources.keys())[0]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = f"{first_ver}_mixed_{ts}"
        filename = f"{version}_{content_type}_{ts}.json"

        record = {
            "version": version,
            "content_type": content_type,
            "timestamp": ts,
            "step": None,
            "change_summary": change_summary,
            "parent_version": first_ver,
            "content": merged,
            "filename": filename,
            "mixed_sources": list(sources.keys()),
        }

        with open(os.path.join(self.versions_dir, filename), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        self._index["versions"].append({
            "version": version,
            "content_type": content_type,
            "timestamp": ts,
            "step": None,
            "change_summary": change_summary,
            "parent_version": first_ver,
            "filename": filename,
        })
        self._save_index()
        return version

    def _get_latest(self, content_type: str) -> dict:
        """
        获取指定类型的最新版本（内部辅助方法）
        
        核心算法：
        1. 从索引中筛选出指定内容类型的所有版本
        2. 如果没有找到，抛出ValueError
        3. 返回最后一个版本（索引中版本按时间顺序排列）
        
        Args:
            content_type: 内容类型（如"outline"、"chapter_1"等）
        
        Returns:
            dict: 最新版本的完整内容
        
        Raises:
            ValueError: 指定类型没有任何版本
        
        使用场景：
        - partial_rollback时获取最新版本的内容
        - 需要对比当前版本和最新版本
        """
        candidates = [v for v in self._index["versions"] if v["content_type"] == content_type]
        if not candidates:
            raise ValueError(f"No versions found for type {content_type}")
        latest = candidates[-1]
        return self.load_version(latest["version"])
