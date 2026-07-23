"""
核心模块包

包含系统的所有核心组件：
- main_agent: Main Agent主协调器
- session_state: 会话状态管理
- genre_knowledge: 题材知识库
- truth_files: 真相文件体系
- version_manager: 版本管理引擎
- file_importer: 文件导入与解析
- memory_system: 三层记忆系统
- user_profile: 用户画像
- skill_library: Skill存储框架
- prompt_loader: Prompt模板加载器
- batch_coordinator: 批量生成协调器
- ambiguity_detector: 模糊度检测器
- expression_variants: 表达变体库
- meme_library: 梗库
- structure_templates: 结构模板库
- trend_refresher: 热点刷新器
- style_learner: 风格学习器
- silent_modification_detector: 隐性修改检测器
"""

# 导出所有核心模块
from core.main_agent import MainAgent
from core.session_state import SessionState
from core.genre_knowledge import GenreKnowledgeBase, get_genre_knowledge_base
from core.truth_files import TruthFiles
from core.version_manager import VersionManager
from core.file_importer import FileImporter
from core.memory_system import MemorySystem
from core.user_profile import UserProfile
from core.skill_library import SkillLibrary
from core.prompt_loader import PromptLoader
from core.batch_coordinator import BatchCoordinator, get_batch_coordinator
from core.ambiguity_detector import AmbiguityDetector, get_ambiguity_detector
from core.expression_variants import ExpressionVariants, get_expression_variants
from core.meme_library import MemeLibrary, get_meme_library
from core.structure_templates import StructureTemplates, get_structure_templates
from core.trend_refresher import TrendRefresher, get_trend_refresher
from core.style_learner import StyleLearner, get_style_learner
from core.silent_modification_detector import SilentModificationDetector, get_silent_modification_detector

__all__ = [
    'MainAgent', 'SessionState',
    'GenreKnowledgeBase', 'get_genre_knowledge_base',
    'TruthFiles', 'VersionManager', 'FileImporter',
    'MemorySystem', 'UserProfile', 'SkillLibrary', 'PromptLoader',
    'BatchCoordinator', 'get_batch_coordinator',
    'AmbiguityDetector', 'get_ambiguity_detector',
    'ExpressionVariants', 'get_expression_variants',
    'MemeLibrary', 'get_meme_library',
    'StructureTemplates', 'get_structure_templates',
    'TrendRefresher', 'get_trend_refresher',
    'StyleLearner', 'get_style_learner',
    'SilentModificationDetector', 'get_silent_modification_detector'
]
