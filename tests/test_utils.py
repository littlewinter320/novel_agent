"""
测试工具模块

提供测试辅助功能：
- MockLLMClient: 模拟LLM客户端，避免真实API调用
- mock_llm_client: 上下文管理器，用于临时替换全局LLM客户端
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch

# 添加项目根目录到路径
test_dir = os.path.dirname(os.path.abspath(__file__))
novel_agent_dir = os.path.dirname(test_dir)
sys.path.insert(0, novel_agent_dir)


class MockLLMClient:
    """
    模拟LLM客户端
    
    用于测试环境，避免真实的API调用和SSL初始化。
    当提示词要求JSON格式返回时，自动返回有效的JSON响应。
    根据提示词内容智能匹配最合适的JSON结构。
    """
    
    def __init__(self, default_response="模拟响应"):
        """
        初始化模拟客户端
        
        Args:
            default_response: 默认响应文本
        """
        self.default_response = default_response
        self.call_count = 0
        self.last_prompt = None
        self.last_system_prompt = None
    
    def generate(self, prompt, system_prompt=None):
        """
        模拟生成响应
        
        当提示词包含"JSON"时，返回有效的JSON字符串。
        根据提示词中的关键词智能匹配响应结构。
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
        
        Returns:
            模拟的响应文本
        """
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        
        # 如果提示词要求JSON格式返回，返回有效的JSON
        if "JSON" in prompt or "json" in prompt:
            return self._generate_json_response(prompt)
        
        # 非JSON提示词的响应
        if "分析" in prompt or "提取" in prompt:
            return '{"result": "模拟分析结果", "score": 0.85}'
        elif "检测" in prompt or "检查" in prompt:
            return '{"pass": true, "issues": [], "suggestions": []}'
        elif "生成" in prompt or "创作" in prompt:
            return "这是一段模拟生成的文本内容。"
        else:
            return self.default_response
    
    def _generate_json_response(self, prompt):
        """
        根据提示词内容返回合适的JSON响应
        
        通过匹配提示词中的关键词，返回对应结构的JSON字符串。
        优先级：从上到下匹配，第一个匹配的优先返回。
        
        Args:
            prompt: 提示词文本
        
        Returns:
            有效的JSON字符串
        """
        # 审计/检查类 - 返回pass/issues格式（auditor的15个检查维度）
        if ("检查" in prompt or "审计" in prompt) and "pass" in prompt:
            return '{"pass": true, "issues": [], "suggestions": []}'
        
        # 卷纲生成（architect）- 必须在总纲之前匹配，因为提示词可能同时包含两者
        if "卷纲" in prompt or "volume_num" in prompt or "总卷数" in prompt:
            return json.dumps([{
                "volume_num": 1,
                "volume_name": "第一卷",
                "core_events": ["入门测试", "首次任务"],
                "goal": "打好基础",
                "key_turning_point": "意外发现",
                "estimated_chapters": 30
            }], ensure_ascii=False)
        
        # 总纲生成（architect）- 在卷纲之后匹配
        if "总纲" in prompt or "core_setting" in prompt:
            return json.dumps({
                "core_setting": "测试世界观设定",
                "main_plot": {
                    "act_1_start": "主角入门",
                    "act_2_develop": "逐步成长",
                    "act_3_turn": "重大危机",
                    "act_4_end": "最终决战"
                },
                "main_characters": ["主角", "配角1", "配角2", "反派"],
                "ending_direction": "HE"
            }, ensure_ascii=False)
        
        # 弧纲生成（architect）
        if "弧纲" in prompt or "arc_num" in prompt:
            return json.dumps([{
                "arc_num": 1,
                "arc_name": "初入江湖",
                "core_conflict": "实力不足",
                "climax_design": "绝地反击",
                "key_turning_point": "获得奇遇",
                "estimated_chapters": 5
            }], ensure_ascii=False)
        
        # 章节规划（architect）
        if "章节规划" in prompt or "chapter_title" in prompt:
            return json.dumps([{
                "chapter_num": 1,
                "chapter_title": "第一章 起源",
                "core_event": "主角踏上旅程",
                "estimated_words": 3000
            }], ensure_ascii=False)
        
        # 伏笔规划（architect）
        if "伏笔" in prompt:
            return json.dumps([{
                "foreshadow_name": "神秘老者",
                "plant_chapter": 1,
                "trigger_condition": "主角遇到危险",
                "resolve_chapter_range": "10-15",
                "content": "神秘老人在关键时刻出手相助"
            }], ensure_ascii=False)
        
        # 参数提取（architect需求澄清）
        if "提取" in prompt and "参数" in prompt:
            # 检查用户输入是否包含了参数信息
            # 如果用户输入很简单（如"帮我写一个故事"），返回空参数集
            if "帮我写一个故事" in prompt or "写一个故事" in prompt:
                return json.dumps({}, ensure_ascii=False)
            else:
                return json.dumps({
                    "protagonist_type": "废柴逆袭",
                    "core_conflict": "复仇",
                    "target_audience": "男频",
                    "tone": "热血",
                    "estimated_chapters": 100
                }, ensure_ascii=False)
        
        # 热点/梗/变体（trend_refresher）- 必须在"搜索+热门"之前匹配，因为trend_refresher的prompt也包含"搜索"和"热门"
        if "梗" in prompt or "变体" in prompt or "热点" in prompt:
            return json.dumps({
                "new_memes": [{"category": "测试类别", "meme": "测试梗"}],
                "new_variants": [{"base": "高兴", "variant": "欣喜"}]
            }, ensure_ascii=False)

        # 热门作品搜索（scout）
        if "搜索" in prompt and "热门" in prompt:
            return json.dumps([{
                "title": "测试热门小说",
                "author": "测试作者",
                "platform": "起点中文网",
                "popularity": "10000",
                "brief": "一部精彩的玄幻小说"
            }], ensure_ascii=False)

        # 特征分析（scout）
        if "特征" in prompt and ("分析" in prompt or "爆火" in prompt):
            return json.dumps({
                "opening_hook": "开篇设置悬念",
                "excitement_distribution": "每5章一个小爽点",
                "character_archetype": "废柴逆袭型主角",
                "plot_template": "升级打怪模式",
                "reader_feedback": {
                    "likes": ["节奏快", "爽点密集"],
                    "dislikes": ["后期拖沓"]
                }
            }, ensure_ascii=False)

        # 建议生成（scout）- 必须在共性分析之前匹配，因为建议提示词中常包含"共性特征"字样
        if "建议" in prompt and ("写法" in prompt or "具体" in prompt):
            return json.dumps(["建议1: 保持快节奏", "建议2: 爽点密集", "建议3: 人设鲜明"], ensure_ascii=False)

        # 共性分析（scout）
        if "共性" in prompt:
            return json.dumps({
                "success_factors": ["快节奏", "爽点密集"],
                "common_opening_hooks": ["悬念开篇"],
                "common_excitement_patterns": ["每5章一个爽点"],
                "common_character_archetypes": ["废柴逆袭"],
                "common_plot_templates": ["升级打怪"],
                "reader_preferences": {
                    "likes": ["节奏快"],
                    "dislikes": ["拖沓"]
                }
            }, ensure_ascii=False)

        # 推荐大纲（scout）
        if "推荐大纲" in prompt or "推荐" in prompt:
            return json.dumps({
                "master_outline": {"act_1_start": "起", "act_2_develop": "承", "act_3_turn": "转", "act_4_end": "合"},
                "volume_design": [{"volume_num": 1, "core_event": "核心事件", "estimated_chapters": 30}],
                "opening_design": {"chapter_1": "第1章设计", "chapter_2": "第2章设计", "chapter_3": "第3章设计"},
                "excitement_distribution": "每5章一个爽点"
            }, ensure_ascii=False)

        # 修改意图检测（silent_modification_detector）- 必须在风格分析之前匹配
        if "修改意图" in prompt or "has_intent" in prompt:
            return json.dumps({
                "has_intent": True,
                "modification_target": "主角的性格",
                "modification_type": "角色",
                "modification_content": "修改主角的性格"
            }, ensure_ascii=False)

        # 风格分析（style_engineer）
        if "风格" in prompt or "文笔" in prompt or "叙事视角" in prompt:
            return json.dumps({
                "narrative_pov": "第三人称",
                "emotion_expression": "直接表达",
                "language_style": "简洁",
                "pacing": "快节奏",
                "description_focus": "重动作",
                "other_features": ["幽默元素"]
            }, ensure_ascii=False)

        # 修改分析（style_learner）
        if "修改" in prompt and ("偏好" in prompt or "分析" in prompt):
            return json.dumps({
                "modifications": ["词汇替换", "句式调整"],
                "preferences": {
                    "vocabulary": ["简洁词汇"],
                    "sentence": ["短句为主"],
                    "rhythm": ["快节奏"],
                    "emotion": ["直接表达"]
                },
                "dislikes": ["冗长描写"]
            }, ensure_ascii=False)
        
        # 对话风格分析（style_learner）
        if "对话" in prompt and "风格" in prompt:
            return json.dumps({
                "style": "轻松幽默",
                "vocabulary_features": ["口语化"],
                "sentence_features": ["短句为主"],
                "emotion_features": ["活泼"]
            }, ensure_ascii=False)
        
        # 一致性检查（batch_coordinator / silent_modification_detector）
        if "一致性" in prompt or "跨章" in prompt:
            return json.dumps({
                "is_consistent": True,
                "inconsistencies": []
            }, ensure_ascii=False)
        
        # 模糊度检测（ambiguity_detector）
        if "模糊" in prompt or "歧义" in prompt:
            return json.dumps({
                "is_ambiguous": False,
                "confidence": 0.9
            }, ensure_ascii=False)
        
        # 默认JSON响应
        return '{"result": "模拟结果"}'
    
    def chat(self, messages):
        """
        模拟聊天响应
        
        Args:
            messages: 消息列表
        
        Returns:
            模拟的响应文本
        """
        self.call_count += 1
        if messages:
            self.last_prompt = messages[-1].get("content", "")
        return self.default_response
    
    def chat_with_system(self, system_prompt, user_message, history=None):
        """
        模拟带系统提示的聊天
        
        Args:
            system_prompt: 系统提示
            user_message: 用户消息
            history: 历史消息（可选）
        
        Returns:
            模拟的响应文本
        """
        self.call_count += 1
        self.last_prompt = user_message
        self.last_system_prompt = system_prompt
        return self.default_response


def mock_llm_client_in_tests():
    """
    在测试中mock LLM客户端
    
    使用上下文管理器临时替换全局LLM客户端，
    避免真实的API调用和SSL初始化。
    
    Returns:
        patch对象，用于在测试中使用
    
    示例:
        with mock_llm_client_in_tests():
            # 在这个块中，所有LLM调用都会使用MockLLMClient
            agent = SomeAgent()
            result = agent.some_method()
    """
    mock_client = MockLLMClient()
    
    # Mock get_llm_client函数
    patcher = patch('utils.llm_client.get_llm_client', return_value=mock_client)
    
    return patcher


def create_mock_llm_client(default_response="模拟响应"):
    """
    创建自定义的模拟LLM客户端
    
    Args:
        default_response: 默认响应文本
    
    Returns:
        MockLLMClient实例
    """
    return MockLLMClient(default_response)
