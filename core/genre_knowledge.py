"""
题材知识库模块

核心职责：
- 管理15+种网络小说题材的完整知识体系（玄幻/都市/仙侠/科幻/历史/悬疑/游戏/体育/军事/轻小说等）
- 提供题材数据的CRUD操作（创建/读取/更新/删除）
- 实现热更新机制：文件修改后自动重新加载，无需重启程序
- 支持按标签搜索题材，便于快速定位

设计思路：
- 每个题材存储为独立的JSON文件，便于维护和扩展
- 使用内存缓存（_genres字典）加速查询，避免频繁磁盘IO
- 通过文件修改时间（_file_mtimes）实现增量热更新
- 单例模式确保全局只有一个知识库实例

题材数据结构：
{
    "name": "题材名称",
    "tags": ["标签列表"],
    "writing_style": "写作风格描述",
    "plot_systems": ["剧情体系列表"],
    "character_templates": ["角色模板列表"],
    "power_system": "力量体系设计",
    "common_tropes": ["常见套路"],
    "taboo_list": ["禁忌事项"],
    "hot_topics": ["当前热门话题/梗"],
    "last_updated": "最后更新时间"
}

关键算法：
- 热更新检测：遍历目录检查文件修改时间，只重新加载变化的文件
- 标签搜索：线性扫描所有题材的tags字段，返回匹配结果
- 增量更新：新文件直接加载，修改文件覆盖更新，删除文件从内存移除
"""

import json
import os
from typing import Dict, List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class GenreKnowledgeBase:
    """
    题材知识库类
    
    核心功能：
    1. 题材数据管理：加载/保存/更新/删除题材JSON文件
    2. 热更新机制：自动检测文件变化并重新加载
    3. 标签搜索：按标签快速定位相关题材
    4. 内存缓存：使用字典缓存加速查询
    
    使用场景：
    - Scout Agent扫榜分析时，查询特定题材的写作规范和禁忌
    - Architect Agent规划大纲时，参考题材的剧情体系和角色模板
    - Writer Agent生成章节时，遵循题材的写作风格和力量体系
    - StyleEngineer优化文风时，检查是否符合题材规范
    """
    
    def __init__(self):
        """
        初始化知识库
        
        初始化流程：
        1. 创建空的题材缓存字典（_genres）
        2. 创建空的文件修改时间记录（_file_mtimes）
        3. 调用_load_all_genres()加载所有题材文件
        
        设计细节：
        - _genres: Dict[str, dict] - 键为题材名称，值为题材数据字典
        - _file_mtimes: Dict[str, float] - 键为文件路径，值为最后修改时间戳
        - 使用这两个字典实现增量热更新：只重新加载修改过的文件
        """
        self._genres: Dict[str, dict] = {}
        self._file_mtimes: Dict[str, float] = {}
        self._load_all_genres()
    
    def _load_all_genres(self):
        """
        加载所有题材文件（初始化时调用）

        实现逻辑：
        1. 检查GENRES_DIR目录是否存在，不存在则创建
        2. 遍历目录中所有.json文件
        3. 对每个文件调用_load_genre_file()加载到内存

        设计细节：
        - 使用os.listdir()遍历目录，过滤.json后缀
        - 加载失败的文件会被跳过，不影响其他文件
        - 加载成功后，文件路径和修改时间会被记录到_file_mtimes
        """
        if not os.path.exists(config.GENRES_DIR):
            os.makedirs(config.GENRES_DIR)
            return

        for filename in os.listdir(config.GENRES_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(config.GENRES_DIR, filename)
                self._load_genre_file(filepath)
    
    def _load_genre_file(self, filepath: str):
        """
        加载单个题材文件到内存
        
        实现逻辑：
        1. 读取JSON文件并解析为字典
        2. 从数据中提取题材名称（name字段）
        3. 将题材数据存入_genres字典（键为题材名称）
        4. 记录文件修改时间到_file_mtimes（用于热更新检测）
        
        异常处理：
        - JSON格式错误：打印警告，跳过该文件
        - 文件读取错误：打印警告，跳过该文件
        - 缺少name字段：跳过该文件（name是必需字段）
        
        Args:
            filepath: 题材文件的完整路径
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            genre_name = data.get('name')
            if genre_name:
                self._genres[genre_name] = data
                self._file_mtimes[filepath] = os.path.getmtime(filepath)
        except (json.JSONDecodeError, IOError) as e:
            print(f"加载题材文件失败 {filepath}: {e}")
    
    def get_genre(self, name: str) -> Optional[dict]:
        """
        获取指定题材数据（核心查询方法）
        
        实现逻辑：
        1. 调用_check_hot_reload()检查文件变化（确保数据最新）
        2. 从_genres字典中查找指定题材
        3. 返回题材数据或None
        
        设计细节：
        - 每次查询前都会检查热更新，确保返回最新数据
        - 使用dict.get()方法，键不存在时返回None而非抛出异常
        
        Args:
            name: 题材名称（如"玄幻"、"都市"、"仙侠"等）
            
        Returns:
            题材数据字典，如果不存在返回None
            
        使用示例：
            genre_data = knowledge_base.get_genre("玄幻")
            if genre_data:
                power_system = genre_data.get("power_system")
        """
        self._check_hot_reload()
        return self._genres.get(name)
    
    def list_genres(self) -> List[str]:
        """
        列出所有已加载的题材名称
        
        实现逻辑：
        1. 调用_check_hot_reload()检查文件变化
        2. 返回_genres字典的所有键（题材名称）
        
        Returns:
            题材名称列表（如["玄幻", "都市", "仙侠", ...]）
            
        使用场景：
        - 用户查询系统支持哪些题材
        - Scout Agent扫榜时选择目标题材
        """
        self._check_hot_reload()
        return list(self._genres.keys())
    
    def add_genre(self, name: str, data: dict) -> bool:
        """
        添加新题材（创建新题材数据）
        
        实现逻辑：
        1. 检查题材是否已存在（避免重复创建）
        2. 确保数据包含name字段（必需字段）
        3. 将数据保存为JSON文件（{name}.json）
        4. 更新内存缓存（_genres和_file_mtimes）
        
        设计细节：
        - 文件名使用题材名称，便于查找和维护
        - 使用ensure_ascii=False确保中文正确保存
        - 使用indent=2使JSON文件格式化，便于人工查看
        
        Args:
            name: 题材名称（如"玄幻"、"都市"等）
            data: 题材数据字典（必须包含完整的数据结构）
            
        Returns:
            bool: 添加成功返回True，题材已存在或保存失败返回False
            
        使用示例：
            new_genre = {
                "name": "科幻",
                "tags": ["未来", "科技", "太空"],
                "writing_style": "硬科幻风格",
                ...
            }
            success = knowledge_base.add_genre("科幻", new_genre)
        """
        if name in self._genres:
            return False
        
        # 确保数据包含name字段
        data['name'] = name
        
        # 保存到文件
        filepath = os.path.join(config.GENRES_DIR, f"{name}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 更新内存
            self._genres[name] = data
            self._file_mtimes[filepath] = os.path.getmtime(filepath)
            return True
        except IOError as e:
            print(f"保存题材文件失败 {filepath}: {e}")
            return False
    
    def update_genre(self, name: str, data: dict) -> bool:
        """
        更新现有题材数据
        
        实现逻辑：
        1. 检查题材是否存在（不存在则无法更新）
        2. 确保数据包含name字段
        3. 覆盖保存为JSON文件
        4. 更新内存缓存
        
        设计细节：
        - 与add_genre类似，但要求题材必须已存在
        - 更新后会同步更新文件修改时间记录
        
        Args:
            name: 题材名称
            data: 新的题材数据字典
            
        Returns:
            bool: 更新成功返回True，题材不存在或保存失败返回False
        """
        if name not in self._genres:
            return False
        
        # 确保数据包含name字段
        data['name'] = name
        
        # 保存到文件
        filepath = os.path.join(config.GENRES_DIR, f"{name}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 更新内存
            self._genres[name] = data
            self._file_mtimes[filepath] = os.path.getmtime(filepath)
            return True
        except IOError as e:
            print(f"更新题材文件失败 {filepath}: {e}")
            return False
    
    def search_by_tag(self, tag: str) -> List[str]:
        """
        按标签搜索题材（标签匹配算法）
        
        实现逻辑：
        1. 调用_check_hot_reload()确保数据最新
        2. 遍历所有题材的tags字段
        3. 如果指定标签在tags列表中，将该题材名称加入结果
        
        算法复杂度：O(n)，n为题材数量
        - 线性扫描所有题材，检查每个题材的tags列表
        - 适合题材数量较少的场景（<100个）
        
        Args:
            tag: 标签名称（如"修仙"、"系统流"、"重生"等）
            
        Returns:
            List[str]: 包含该标签的题材名称列表
            
        使用示例：
            xianxia_genres = knowledge_base.search_by_tag("修仙")
            # 返回: ["仙侠", "玄幻"]
        """
        self._check_hot_reload()
        result = []
        for name, data in self._genres.items():
            tags = data.get('tags', [])
            if tag in tags:
                result.append(name)
        return result
    
    def reload(self):
        """
        强制重新加载所有题材文件（全量热更新）
        
        实现逻辑：
        1. 清空_genres字典（内存缓存）
        2. 清空_file_mtimes字典（修改时间记录）
        3. 调用_load_all_genres()重新加载所有文件
        
        使用场景：
        - 手动触发全量更新（如外部修改了多个题材文件）
        - 调试时强制刷新数据
        
        注意：
        - 与_check_hot_reload()不同，reload()是无条件全量加载
        - _check_hot_reload()是增量检测，只加载变化的文件
        """
        self._genres.clear()
        self._file_mtimes.clear()
        self._load_all_genres()
    
    def _check_hot_reload(self):
        """
        检查文件修改时间，自动重新加载修改过的文件（增量热更新算法）
        
        核心算法：
        1. 遍历GENRES_DIR目录中的所有.json文件
        2. 对每个文件，获取当前修改时间（os.path.getmtime）
        3. 与_file_mtimes中记录的时间对比：
           - 如果文件不在记录中（新文件）→ 加载
           - 如果当前时间 > 记录时间（文件被修改）→ 重新加载
        4. 检查是否有文件被删除：
           - 对比_file_mtimes中的文件集合与当前目录文件集合
           - 删除的文件从_file_mtimes和_genres中移除
        
        设计思路：
        - 增量更新：只重新加载变化的文件，避免全量加载的性能开销
        - 自动检测：每次查询前自动检查，无需手动调用reload()
        - 删除检测：通过集合差集运算发现被删除的文件
        
        性能优化：
        - os.path.getmtime()是系统调用，开销较小
        - 只对比时间戳，不读取文件内容
        - 适合文件数量较少的场景（<100个文件）
        
        使用场景：
        - 用户手动编辑了题材JSON文件
        - 外部脚本更新了题材数据
        - 无需重启程序，下次查询时自动生效
        """
        if not os.path.exists(config.GENRES_DIR):
            return
        
        # 检查现有文件是否被修改
        for filename in os.listdir(config.GENRES_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(config.GENRES_DIR, filename)
                current_mtime = os.path.getmtime(filepath)
                
                # 如果文件不存在于记录中，或修改时间变化，则重新加载
                if filepath not in self._file_mtimes or self._file_mtimes[filepath] < current_mtime:
                    self._load_genre_file(filepath)
        
        # 检查是否有文件被删除
        current_files = {os.path.join(config.GENRES_DIR, f) for f in os.listdir(config.GENRES_DIR) if f.endswith('.json')}
        deleted_files = set(self._file_mtimes.keys()) - current_files
        
        for filepath in deleted_files:
            # 从记录中移除
            del self._file_mtimes[filepath]
            
            # 从内存中移除对应的题材
            genres_to_remove = [name for name, data in self._genres.items() 
                               if os.path.join(config.GENRES_DIR, f"{name}.json") == filepath]
            for name in genres_to_remove:
                del self._genres[name]


# 全局实例
_genre_knowledge_base = None


def get_genre_knowledge_base() -> GenreKnowledgeBase:
    """获取全局题材知识库实例（单例模式）"""
    global _genre_knowledge_base
    if _genre_knowledge_base is None:
        _genre_knowledge_base = GenreKnowledgeBase()
    return _genre_knowledge_base
