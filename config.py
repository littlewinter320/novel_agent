"""
配置管理模块

核心职责：
- 集中管理所有可调参数，避免硬编码
- 统一管理文件路径和目录结构
- 控制LLM调用参数
- 定义质量检查阈值和多样性控制参数

设计思路：
- 所有配置项都在此文件集中定义，便于调试和优化
- 路径配置使用os.path动态生成，支持跨平台
- 阈值参数可根据实际效果调整，无需修改业务代码
- LLM配置支持多提供商切换（kimi/openai/custom）

关键参数说明：
- MAX_AUDIT_ROUNDS: 审计-修订循环次数，平衡质量与效率
- VARIETY_WINDOW_SIZE: 统计最近N章的词汇使用，控制重复度
- STYLE_LEARN_DIVERSITY_RATIO: 保持75%多样性，25%适应用户偏好
"""
import os

# ========== 目录结构配置 ==========
# 项目根目录：所有路径的基础
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 数据目录：存储所有持久化数据
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
# 题材知识库目录：存储15种题材的JSON配置
GENRES_DIR = os.path.join(DATA_DIR, "genres")
# 真相文件目录：存储7个核心事实文件（世界状态、角色矩阵等）
TRUTH_DIR = os.path.join(DATA_DIR, "truth")
# Skill库目录：存储可复用技能的JSON文件
SKILLS_DIR = os.path.join(DATA_DIR, "skills")
# 记忆系统目录：存储温记忆和冷记忆
MEMORY_DIR = os.path.join(DATA_DIR, "memory")
# 冷记忆目录：按章节存储的历史摘要
COLD_MEMORY_DIR = os.path.join(MEMORY_DIR, "cold_memory")
# 版本管理目录：存储版本快照
VERSIONS_DIR = os.path.join(DATA_DIR, "versions")
# 检查点目录：存储断点恢复数据
CHECKPOINTS_DIR = os.path.join(DATA_DIR, "checkpoints")
# Prompt模板目录：存储6个SubAgent的提示词模板
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")

# ========== 会话状态配置 ==========
# 会话状态文件：存储当前工作进度和约束
SESSION_STATE_FILE = os.path.join(DATA_DIR, "session_state.json")
# 用户画像文件：存储用户偏好和写作习惯
USER_PROFILE_FILE = os.path.join(MEMORY_DIR, "user_profile.json")
# 温记忆文件：存储跨会话的核心信息
WARM_MEMORY_FILE = os.path.join(MEMORY_DIR, "warm_memory.json")

# ========== LLM配置 ==========
# 支持的提供商: kimi, deepseek, glm, openai, claude, custom
# 修改以下配置以使用不同的LLM提供商
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-aedf1ed53e7e4d56b0b65807277039ce")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
# 温度参数: 0.0-2.0, 值越高输出越随机, 值越低输出越确定
# 注意: 某些模型可能有特定的温度限制（如kimi-k2.5只支持1.0）
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "1"))

LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))


# ========== 质量检查阈值 ==========
# 审计-修订最大轮数：平衡质量与效率，超过3轮后暂停等待用户介入
MAX_AUDIT_ROUNDS = 3
# 活跃伏笔上限：控制同时进行的伏笔数量，避免剧情线过于复杂
MAX_ACTIVE_FORESHADOWS = 10
# 伏笔陈旧阈值：超过5章未提及则警告，防止伏笔被遗忘
FORESHADOW_STALE_THRESHOLD = 5
# 伏笔超期阈值：超过预计回收章节5章仍未触发则警告
FORESHADOW_OVERDUE_THRESHOLD = 5
# AI句式频率上限：每种AI味句式每章最多出现1次，避免机械化表达
AI_TIC_MAX_PER_CHAPTER = 1

# ========== 多样性控制 ==========
# 多样性统计窗口：统计最近10章的词汇使用频率，用于检测重复
VARIETY_WINDOW_SIZE = 10
# 表达重复阈值：某词汇连续5章出现超过此数则建议替换
EXPRESSION_REPEAT_THRESHOLD = 5
# 梗陈旧阈值：梗超过50章未使用标记为过时，需要更新
MEME_STALE_THRESHOLD = 50
# 热点刷新最小间隔：至少5章后才触发热点刷新
TREND_REFRESH_MIN_INTERVAL = 5
# 热点刷新最大间隔：最多25章必须触发一次热点刷新
TREND_REFRESH_MAX_INTERVAL = 25

# ========== 风格学习 ==========
# 多样性保持比例：60%保持原有风格多样性，避免过度拟合用户偏好
STYLE_LEARN_DIVERSITY_RATIO = 0.6
# 用户适应比例：40%适应用户的写作偏好和习惯
STYLE_LEARN_ADAPT_RATIO = 0.4
# 学习报告间隔：每10章输出一次风格学习报告，让用户了解学习进度
STYLE_LEARN_REPORT_INTERVAL = 10

# ========== 批量生成 ==========
# 单次批量生成最大章数：限制一次生成的章节数量，避免资源过度消耗
BATCH_MAX_CHAPTERS = 10

# ========== 章节字数控制 ==========
# 章节最小字数：确保每章内容充实，避免过短
CHAPTER_MIN_WORDS = 2000
# 章节最大字数：控制单章长度，避免过长影响阅读体验
CHAPTER_MAX_WORDS = 5000

# ========== 伏笔管理 ==========
# 最大活跃伏笔数：控制同时进行的伏笔数量，避免剧情线过于复杂
MAX_FORESHADOWS = 10

# ========== 文件导入 ==========
# 支持的文件格式：文档导入模块支持的格式列表
SUPPORTED_FILE_FORMATS = [".docx", ".pdf", ".txt", ".md"]

# ========== 多样性报告 ==========
# 词汇过度使用阈值：某词汇在统计窗口内出现超过此次数则警告
DIVERSITY_WORD_THRESHOLD = 10
# 梗过度使用阈值：某个梗在统计窗口内出现超过此次数则警告
DIVERSITY_MEME_THRESHOLD = 5
