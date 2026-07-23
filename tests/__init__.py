"""
单元测试模块包

包含所有核心组件和SubAgent的单元测试：

基础模块测试：
- test_session_state: SessionState测试
- test_main_agent: MainAgent测试
- test_genre_knowledge: GenreKnowledgeBase测试
- test_truth_files: TruthFiles测试
- test_version_manager: VersionManager测试
- test_file_importer: FileImporter测试
- test_memory_system: MemorySystem测试
- test_user_profile: UserProfile测试
- test_skill_library: SkillLibrary测试
- test_prompt_loader: PromptLoader测试

SubAgent测试：
- test_scout: ScoutAgent扫榜分析师测试
- test_architect: ArchitectAgent架构师测试
- test_writer: WriterAgent写手测试
- test_auditor: AuditorAgent连续性审计员测试
- test_revisor: RevisorAgent修订员测试
- test_style_engineer: StyleEngineerAgent文风工程师测试

核心模块测试：
- test_batch_coordinator: BatchCoordinator批量生成协调器测试
- test_ambiguity_detector: AmbiguityDetector模糊度检测器测试
- test_expression_variants: ExpressionVariants表达变体库测试
- test_meme_library: MemeLibrary梗库测试
- test_structure_templates: StructureTemplates结构模板库测试
- test_trend_refresher: TrendRefresher热点刷新器测试
- test_style_learner: StyleLearner风格学习器测试
- test_silent_modification_detector: SilentModificationDetector隐性修改检测器测试
- test_dialogue_database: DialogueDatabase对话数据库测试
- test_slash_command_handler: SlashCommandHandler斜杠命令处理器测试

工具模块测试：
- test_llm_cache: LLMCache缓存机制测试
"""

# 在所有测试模块导入之前，先设置测试环境
# 核心策略：直接mock openai.OpenAI类，避免SSL证书初始化
import os
import sys
from unittest.mock import MagicMock

# 添加项目根目录到路径
_test_dir = os.path.dirname(os.path.abspath(__file__))
_novel_agent_dir = os.path.dirname(_test_dir)
if _novel_agent_dir not in sys.path:
    sys.path.insert(0, _novel_agent_dir)

# 设置测试用的API密钥（避免初始化时抛出ValueError）
os.environ["LLM_API_KEY"] = "test-api-key-for-unit-tests"

# Mock openai.OpenAI类（在任何其他导入之前）
try:
    import openai
    # 创建一个Mock的OpenAI类
    _mock_openai_class = MagicMock()
    _mock_openai_instance = MagicMock()
    _mock_openai_class.return_value = _mock_openai_instance
    
    # 替换openai.OpenAI
    openai.OpenAI = _mock_openai_class
except ImportError:
    pass
