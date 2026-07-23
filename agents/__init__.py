"""
SubAgent模块包

包含6个专业的SubAgent：
- scout: 扫榜分析师（分析热门作品）
- architect: 架构师（规划大纲）
- writer: 写手（生成章节）
- auditor: 连续性审计员（15维度检查）
- revisor: 修订员（定点修复）
- style_engineer: 文风工程师（风格分析与生成）
"""

# 导出所有SubAgent
from agents.scout import ScoutAgent, get_scout_agent
from agents.architect import ArchitectAgent, get_architect_agent
from agents.writer import WriterAgent, get_writer_agent
from agents.auditor import AuditorAgent, get_auditor_agent
from agents.revisor import RevisorAgent, get_revisor_agent
from agents.style_engineer import StyleEngineerAgent, get_style_engineer_agent

__all__ = [
    'ScoutAgent', 'get_scout_agent',
    'ArchitectAgent', 'get_architect_agent',
    'WriterAgent', 'get_writer_agent',
    'AuditorAgent', 'get_auditor_agent',
    'RevisorAgent', 'get_revisor_agent',
    'StyleEngineerAgent', 'get_style_engineer_agent'
]
