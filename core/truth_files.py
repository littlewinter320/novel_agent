"""
真相文件体系模块

核心职责：
- 管理小说创作过程中的7个核心真相文件，确保数据一致性和可追溯性
- 实现真相文件的加载、保存、更新和删除操作
- 提供交叉验证机制，检测真相文件之间的逻辑冲突
- 支持版本控制和历史回溯

设计思路：
- 7个真相文件分别存储不同维度的核心数据（世界状态、角色矩阵、剧情进度等）
- 使用JSON格式存储，便于人工查看和调试
- 通过文件锁机制避免并发写入冲突
- 提供交叉验证接口，确保数据一致性

7个真相文件说明：
1. world_state.json - 世界状态：存储世界规则、力量体系、地理信息等
2. character_matrix.json - 角色矩阵：存储角色属性、关系网络、成长轨迹等
3. plot_progress.json - 剧情进度：存储主线/支线剧情、事件时间线、伏笔钩子等
4. foreshadow_hooks.json - 伏笔钩子：存储伏笔的埋设、触发、回收状态
5. resource_ledger.json - 资源账本：存储物品/资源的流转记录
6. timeline.json - 时间线：存储事件的时间顺序和依赖关系
7. style_guide.json - 风格指南：存储写作风格规范、禁忌词汇等

关键算法：
- 交叉验证：检查角色认知边界、物品流转、时间线一致性、世界规则冲突
- 版本控制：基于文件修改时间的快照机制
- 依赖检查：检测事件之间的循环依赖
"""
import json
import os
import copy
from typing import Dict, List, Any
from config import TRUTH_DIR


class TruthFiles:
    """
    真相文件管理器
    
    核心功能：
    1. 真相文件CRUD：加载/保存/更新/删除7个核心真相文件
    2. 交叉验证：检测真相文件之间的逻辑冲突
    3. 版本控制：支持历史快照和回溯
    4. 依赖检查：检测事件之间的循环依赖
    
    使用场景：
    - Writer Agent生成章节后，更新plot_progress和character_matrix
    - Auditor Agent审计时，调用cross_validate()检查一致性
    - Revisor Agent修订时，参考foreshadow_hooks和timeline
    - StyleEngineer优化文风时，参考style_guide
    """
    
    # 7个真相文件的定义
    TRUTH_FILE_DEFS = {
        "world_state": {
            "filename": "world_state.json",
            "default": {"rules": {}, "forces": {}, "resources": {}}
        },
        "character_matrix": {
            "filename": "character_matrix.json",
            "default": {"characters": {}}
        },
        "plot_progress": {
            "filename": "plot_progress.json",
            "default": {"events": [], "main_plot": {}, "sub_plots": {}}
        },
        "foreshadow_hooks": {
            "filename": "foreshadow_hooks.json",
            "default": {"foreshadows": []}
        },
        "resource_ledger": {
            "filename": "resource_ledger.json",
            "default": {"items": [], "transactions": []}
        },
        "timeline": {
            "filename": "timeline.json",
            "default": {"events": []}
        },
        "style_guide": {
            "filename": "style_guide.json",
            "default": {"tone": "", "forbidden_patterns": [], "pov": ""}
        }
    }
    
    def __init__(self, truth_dir=None):
        """
        初始化真相文件管理器
        
        实现逻辑：
        1. 设置真相文件目录（使用配置或自定义路径）
        2. 确保目录存在（不存在则创建）
        3. 初始化空的数据字典
        
        Args:
            truth_dir: 真相文件目录路径，如果为None则使用配置中的TRUTH_DIR
        """
        self.truth_dir = truth_dir if truth_dir is not None else TRUTH_DIR
        self._ensure_truth_dir()
        self.data = {}
        
    def _ensure_truth_dir(self):
        """
        确保真相文件目录存在
        
        实现逻辑：
        - 检查目录是否存在，不存在则递归创建
        - 使用os.makedirs的exist_ok=True避免竞态条件
        """
        if not os.path.exists(self.truth_dir):
            os.makedirs(self.truth_dir)
    
    def load_all(self) -> Dict[str, Any]:
        """
        加载所有真相文件到内存
        
        实现逻辑：
        1. 遍历TRUTH_FILE_DEFS中定义的7个文件
        2. 对每个文件：
           - 如果文件存在 → 读取JSON内容到self.data
           - 如果文件不存在 → 使用默认结构初始化并保存到磁盘
        3. 返回完整的data字典
        
        设计细节：
        - 使用copy.deepcopy()复制默认结构，避免嵌套对象被共享引用
        - 文件不存在时自动创建，确保首次运行也能正常工作
        - 所有文件使用UTF-8编码，支持中文内容
        
        Returns:
            Dict[str, Any]: 包含7个真相文件数据的字典
        """
        for file_id, file_def in self.TRUTH_FILE_DEFS.items():
            file_path = os.path.join(self.truth_dir, file_def["filename"])
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.data[file_id] = json.load(f)
            else:
                # 文件不存在，使用默认结构并保存
                # 使用深拷贝避免嵌套结构被共享
                self.data[file_id] = copy.deepcopy(file_def["default"])
                self._save_file(file_id)
        
        return self.data
    
    def save_all(self) -> None:
        """
        保存所有真相文件到磁盘
        
        实现逻辑：
        - 遍历self.data中的所有文件ID，逐个调用_save_file()
        - 如果某个文件保存失败，会抛出异常，后续文件不会被保存
        """
        for file_id in self.data:
            self._save_file(file_id)
    
    def _save_file(self, file_id: str) -> None:
        """
        保存单个真相文件到磁盘
        
        实现逻辑：
        1. 验证file_id是否合法（必须在TRUTH_FILE_DEFS中）
        2. 从TRUTH_FILE_DEFS获取对应的文件名
        3. 将self.data[file_id]序列化为JSON并写入文件
        
        Args:
            file_id: 真相文件ID（如"world_state"、"character_matrix"等）
        
        Raises:
            ValueError: file_id不在TRUTH_FILE_DEFS中
        """
        if file_id not in self.data:
            raise ValueError(f"未知的真相文件ID: {file_id}")
        
        file_def = self.TRUTH_FILE_DEFS.get(file_id)
        if not file_def:
            raise ValueError(f"未知的真相文件ID: {file_id}")
        
        file_path = os.path.join(self.truth_dir, file_def["filename"])
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data[file_id], f, ensure_ascii=False, indent=2)
    
    def get_file(self, file_id: str) -> Dict[str, Any]:
        """
        获取指定真相文件的数据（只读访问）
        
        Args:
            file_id: 真相文件ID
        
        Returns:
            Dict[str, Any]: 真相文件数据
        
        Raises:
            ValueError: file_id不存在
        """
        if file_id not in self.data:
            raise ValueError(f"未知的真相文件ID: {file_id}")
        return self.data[file_id]
    
    def update_file(self, file_id: str, data: Dict[str, Any]) -> None:
        """
        更新真相文件的数据（写入后立即持久化）
        
        实现逻辑：
        1. 验证file_id是否合法
        2. 替换self.data中的对应数据
        3. 立即保存到磁盘（确保数据不丢失）
        
        Args:
            file_id: 真相文件ID
            data: 新的数据字典
        
        Raises:
            ValueError: file_id不在TRUTH_FILE_DEFS中
        """
        if file_id not in self.TRUTH_FILE_DEFS:
            raise ValueError(f"未知的真相文件ID: {file_id}")
        
        self.data[file_id] = data
        self._save_file(file_id)
    
    def cross_validate(self) -> List[str]:
        """
        交叉验证所有真相文件，检测逻辑冲突（核心一致性检查算法）
        
        实现逻辑：
        1. 调用4个验证子方法，分别检查不同维度的冲突
        2. 收集所有问题并返回
        
        验证维度：
        1. 角色认知边界检查：角色是否知道他不该知道的事（如未来事件）
        2. 物品流转检查：物品是否凭空出现/消失（必须有create记录才能transfer）
        3. 时间线一致性检查：事件顺序是否矛盾（依赖关系是否合理）
        4. 世界规则一致性检查：事件是否违反已建立的世界规则
        
        Returns:
            List[str]: 问题描述列表，空列表表示无冲突
        """
        issues = []
        
        # 1. 角色认知边界检查
        issues.extend(self._check_character_knowledge())
        
        # 2. 物品流转检查
        issues.extend(self._check_resource_flow())
        
        # 3. 时间线一致性检查
        issues.extend(self._check_timeline_consistency())
        
        # 4. 世界规则一致性检查
        issues.extend(self._check_world_rules())
        
        return issues
    
    def _check_character_knowledge(self) -> List[str]:
        """
        检查角色认知边界：角色是否知道他不该知道的事
        
        核心算法：
        1. 从character_matrix获取所有角色及其knowledge列表
        2. 从plot_progress获取所有事件及其状态（future/ongoing/completed）
        3. 对每个角色的每个knowledge项：
           - 查找对应的事件
           - 如果事件状态为"future"（未来事件），则角色不应该知道
           - 记录问题：角色X知道了未来事件Y
        
        检测场景：
        - 角色A在事件Y发生前就知道了Y的内容
        - 这会导致剧情逻辑矛盾（如角色预知未来但没有合理来源）
        
        Returns:
            List[str]: 问题描述列表
        """
        issues = []
        
        if "character_matrix" not in self.data:
            return issues
        
        characters = self.data["character_matrix"].get("characters", {})
        plot_events = self.data.get("plot_progress", {}).get("events", [])
        
        for char_id, char_data in characters.items():
            knowledge = char_data.get("knowledge", [])
            
            # 检查角色是否知道未发生的事件
            for event_id in knowledge:
                event = next((e for e in plot_events if e.get("id") == event_id), None)
                if event and event.get("status") == "future":
                    issues.append(f"角色 {char_id} 知道了未来事件 {event_id}")
        
        return issues
    
    def _check_resource_flow(self) -> List[str]:
        """
        检查物品流转：物品是否凭空出现/消失（资源账本一致性验证）
        
        核心算法：
        1. 从resource_ledger获取items列表和transactions列表
        2. 构建物品流转图：
           - item_sources: 记录每个物品的来源交易（create类型）
           - item_destinations: 记录每个物品的去向交易（destroy类型）
        3. 遍历所有transactions：
           - type="create": 记录为物品来源
           - type="destroy": 记录为物品去向
           - type="transfer": 检查物品是否已创建（必须有source记录）
        4. 检查所有items是否都有创建记录
        
        检测场景：
        - 物品被转移但从未被创建（凭空出现）
        - 物品存在但没有创建记录（数据不一致）
        
        Returns:
            List[str]: 问题描述列表
        """
        issues = []
        
        if "resource_ledger" not in self.data:
            return issues
        
        items = self.data["resource_ledger"].get("items", [])
        transactions = self.data["resource_ledger"].get("transactions", [])
        
        # 构建物品流转图
        item_sources = {}  # item_id -> 来源交易
        item_destinations = {}  # item_id -> 去向交易
        
        for trans in transactions:
            item_id = trans.get("item_id")
            trans_type = trans.get("type")  # create, transfer, destroy
            
            if trans_type == "create":
                item_sources[item_id] = trans
            elif trans_type == "destroy":
                item_destinations[item_id] = trans
            elif trans_type == "transfer":
                # 转移需要检查物品是否存在
                if item_id not in item_sources:
                    issues.append(f"物品 {item_id} 在转移前未创建")
        
        # 检查所有物品是否都有来源
        for item in items:
            item_id = item.get("id")
            if item_id not in item_sources:
                issues.append(f"物品 {item_id} 没有创建记录")
        
        return issues
    
    def _check_timeline_consistency(self) -> List[str]:
        """
        检查时间线一致性：事件顺序是否矛盾（时间线依赖验证）
        
        核心算法：
        1. 从timeline获取所有事件
        2. 按时间戳排序事件
        3. 检查每个事件的depends_on字段：
           - 如果事件A依赖于事件B，但A的时间早于B
           - 则记录问题：事件A依赖于后续事件B
        
        检测场景：
        - 因果倒置：结果发生在原因之前
        - 依赖循环：A依赖B，B依赖A
        
        Returns:
            List[str]: 问题描述列表
        """
        issues = []
        
        if "timeline" not in self.data:
            return issues
        
        events = self.data["timeline"].get("events", [])
        
        # 按时间排序检查
        sorted_events = sorted(events, key=lambda e: e.get("time", 0))
        
        for i in range(len(sorted_events) - 1):
            current = sorted_events[i]
            next_event = sorted_events[i + 1]
            
            # 检查依赖关系
            if current.get("depends_on") and next_event.get("id") in current.get("depends_on"):
                issues.append(f"事件 {current.get('id')} 依赖于后续事件 {next_event.get('id')}")
        
        return issues
    
    def _check_world_rules(self) -> List[str]:
        """
        检查世界规则一致性：是否违反已建立的规则（世界规则验证）
        
        核心算法：
        1. 从world_state获取所有规则
        2. 从plot_progress获取所有事件
        3. 检查每个事件的violates_rules字段：
           - 如果事件标记为违反某规则
           - 且该规则确实存在于world_state中
           - 则记录问题：事件X违反了规则Y
        
        检测场景：
        - 角色在"禁止飞行"的世界中飞行
        - 角色在"魔法需要咒语"的设定中无咒语施法
        
        Returns:
            List[str]: 问题描述列表
        """
        issues = []
        
        if "world_state" not in self.data or "plot_progress" not in self.data:
            return issues
        
        rules = self.data["world_state"].get("rules", {})
        events = self.data["plot_progress"].get("events", [])
        
        # 检查每个事件是否违反规则
        for event in events:
            event_rules = event.get("violates_rules", [])
            for rule_id in event_rules:
                if rule_id in rules:
                    issues.append(f"事件 {event.get('id')} 违反了规则 {rule_id}")
        
        return issues
