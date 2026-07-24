#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络文学小说创作Agent系统 - 主程序入口

核心职责：
- 提供命令行交互界面，接收用户输入并路由到对应功能
- 初始化系统，检查API密钥和连接状态
- 管理主循环，处理命令和对话
- 集成进度反馈系统，让用户实时了解Agent运行状态
- 集成网络搜索功能，支持实时获取平台数据

设计思路：
- 用户输入后先显示"正在执行..."的进度反馈
- 意图识别：判断用户是否需要搜索数据、分析小说等
- 通过LLM搜索获取热门小说信息
- 知识库自动更新爆火小说的写法特征

使用方式：
    python main.py
"""

import os
import sys
import json
from typing import Optional, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 在所有模块导入之前，先检测并安装依赖
from utils.dependency_installer import ensure_dependencies
ensure_dependencies()

import config
from utils.llm_client import get_llm_client, test_connection
from utils.progress_display import get_progress_display
from utils.web_search import get_web_search
from core.genre_knowledge import get_genre_knowledge_base
from core.agent_flow_manager import get_agent_flow_manager

# 导入agents目录中的专业Agent
from agents.scout import ScoutAgent
from agents.architect import ArchitectAgent
from agents.writer import WriterAgent
from agents.auditor import AuditorAgent
from agents.revisor import RevisorAgent
from agents.style_engineer import StyleEngineerAgent


class NovelAgentCLI:
    """
    小说创作Agent系统命令行界面

    核心功能：
    1. 系统初始化：检查API密钥、测试连接、初始化各模块
    2. 进度反馈：每个操作都显示实时状态，用户知道Agent在做什么
    3. 智能路由：识别用户意图，自动调用搜索/分析/创作等功能
    4. Agent调度：根据意图路由到对应的专业Agent（Scout/Architect/Writer等）
    5. 知识库更新：爆火小说的写法特征自动记录到知识库
    """
    
    def __init__(self):
        self.llm_client = None
        self.running = False
        self.conversation_history = []
        self.max_history_length = float('inf')  # 不限制对话历史
        # 各模块实例（延迟初始化）
        self.progress = None
        self.web_search = None
        self.genre_kb = None
        self.flow_manager = None
        # 专业Agent实例
        self.scout_agent = None
        self.architect_agent = None
        self.writer_agent = None
        self.auditor_agent = None
        self.revisor_agent = None
        self.style_engineer_agent = None
        
    def initialize(self):
        """初始化系统，包含所有子模块"""
        print("\n小说创作Agent系统")
        
        # 自动检测并安装缺失依赖
        ensure_dependencies()
        
        # 检查LLM提供商
        if config.LLM_PROVIDER not in ['deepseek', 'kimi', 'glm', 'openai', 'claude', 'custom']:
            print(f"错误：不支持的LLM提供商 {config.LLM_PROVIDER}")
            print("请在.env或config.py中设置LLM_PROVIDER")
            return False
        
        # 检查API密钥
        if not config.LLM_API_KEY:
            print("错误：未检测到API密钥")
            print("请在.env或config.py中设置LLM_API_KEY")
            return False
        
        # 测试API连接
        print("连接AI服务...")
        if test_connection():
            print("连接成功")
            self.llm_client = get_llm_client()
        else:
            print("连接失败，请检查网络或API密钥")
            return False
        
        # 初始化进度显示
        self.progress = get_progress_display()
        
        # 初始化网络搜索模块
        print("初始化搜索模块...")
        self.web_search = get_web_search()
        self.web_search.set_llm_client(self.llm_client)
        
        # 初始化知识库
        self.genre_kb = get_genre_knowledge_base()
        
        # 初始化专业Agent
        print("初始化专业Agent...")
        self.scout_agent = ScoutAgent()
        self.architect_agent = ArchitectAgent()
        self.writer_agent = WriterAgent()
        self.auditor_agent = AuditorAgent()
        self.revisor_agent = RevisorAgent()
        self.style_engineer_agent = StyleEngineerAgent()
        
        # 初始化流程管理器
        self.flow_manager = get_agent_flow_manager()
        
        # 初始化Obsidian同步（如果配置了）
        self._init_obsidian()
        
        return True
    
    def _init_obsidian(self):
        """初始化Obsidian同步（可选）"""
        try:
            if hasattr(config, 'OBSIDIAN_VAULT_PATH') and config.OBSIDIAN_VAULT_PATH:
                print("初始化Obsidian同步...")
                print("Obsidian同步已启用")
        except Exception:
            pass  # Obsidian是可选功能
    
    def show_welcome(self):
        """显示欢迎信息"""
        print("\n功能：1.分析爆火小说 2.规划大纲 3.生成章节 4.导入文件 5.搜索平台数据 6.流程管理")
        print("命令：help-帮助 quit-退出 status-状态 search-搜索 flow-流程")

    def show_help(self):
        """显示帮助信息"""
        print("\n帮助：")
        print("命令：")
        print("  help/帮助 - 显示帮助")
        print("  quit/退出 - 退出系统")
        print("  status/状态 - 显示当前状态")
        print("  search/搜索 - 搜索平台热门小说数据")
        print("  flow/流程 - 显示/管理Agent调用流程")
        print("\n对话功能：")
        print("  直接描述需求，系统自动识别并执行")
        print("  例：查看番茄小说男频游戏系统类的爆款")
        print("  例：分析起点中文网玄幻题材热门作品")
        print("  例：去番茄找女频仙侠爆火小说")
    
    def show_status(self):
        """显示当前状态"""
        print(f"\n模型:{config.LLM_MODEL} 提供商:{config.LLM_PROVIDER}")
        print(f"API:{'已设置' if config.LLM_API_KEY else '未设置'}")
        print(f"搜索:{'就绪' if self.web_search else '未初始化'}")
        print(f"知识库:{'就绪' if self.genre_kb else '未初始化'}")
        # 显示Agent状态
        print(f"\n专业Agent状态:")
        print(f"  扫榜分析师:{'就绪' if self.scout_agent else '未初始化'}")
        print(f"  架构师:{'就绪' if self.architect_agent else '未初始化'}")
        print(f"  写手:{'就绪' if self.writer_agent else '未初始化'}")
        print(f"  审计员:{'就绪' if self.auditor_agent else '未初始化'}")
        print(f"  修订员:{'就绪' if self.revisor_agent else '未初始化'}")
        print(f"  文风工程师:{'就绪' if self.style_engineer_agent else '未初始化'}")
    
    def process_command(self, user_input: str) -> bool:
        """处理用户输入，识别命令或对话"""
        raw_input = user_input.strip()
        lower_input = raw_input.lower()

        # 退出命令
        if lower_input in ['quit', 'exit', 'q', '退出', '拜拜', '再见', 'bye']:
            print("再见")
            return False

        # 帮助命令
        elif lower_input in ['help', 'h', '帮助', '?']:
            self.show_help()
            return True

        # 状态命令
        elif lower_input in ['status', '状态']:
            self.show_status()
            return True

        # 搜索命令
        elif lower_input.startswith(('search', '搜索', '查找', '搜')):
            self._handle_search_command(raw_input)
            return True

        # 流程命令
        elif lower_input.startswith(('flow', '流程')):
            self._show_flow_command(raw_input)
            return True

        # 文件路径检测
        elif os.path.exists(raw_input):
            print(f"文件:{raw_input}")
            print("导入功能开发中")
            return True

        # URL检测（自动获取网页内容）
        elif self._detect_url(raw_input):
            return self._handle_url_content(raw_input)

        # 智能对话（自动识别是否需要搜索）
        else:
            return self._handle_smart_conversation(raw_input)
    
    def _detect_search_intent(self, user_input: str) -> Dict[str, Any]:
        """
        检测用户输入是否包含搜索意图

        返回：
            {"need_search": bool, "platform": str, "genre": str, "target_audience": str, "user_input": str}
        """
        # 平台关键词映射
        platform_keywords = {
            "番茄小说": ["番茄", "fanqie", "番茄小说"],
            "起点中文网": ["起点", "qidian", "起点中文网"],
            "七猫小说": ["七猫", "qimao", "七猫小说"],
        }

        # 题材关键词映射
        genre_keywords = {
            "游戏": ["游戏", "网游", "系统流", "升级", "副本"],
            "玄幻": ["玄幻", "修仙", "仙侠", "修真"],
            "都市": ["都市", "现代", "城市", "职场"],
            "科幻": ["科幻", "未来", "太空", "星际"],
            "历史": ["历史", "古代", "穿越", "架空"],
            "悬疑": ["悬疑", "推理", "侦探", "恐怖"],
        }

        # 受众关键词
        audience_keywords = {
            "男频": ["男频", "男生", "男性"],
            "女频": ["女频", "女生", "女性"],
        }

        # 检测搜索意图关键词
        search_triggers = ["查看", "搜索", "查找", "最新", "热门", "爆款", "爆火",
                          "排行榜", "榜单", "有什么", "推荐", "找找", "看看", "找"]

        need_search = any(trigger in user_input for trigger in search_triggers)

        # 识别平台
        detected_platform = ""
        for platform, keywords in platform_keywords.items():
            if any(kw in user_input for kw in keywords):
                detected_platform = platform
                break

        # 识别题材
        detected_genre = ""
        for genre, keywords in genre_keywords.items():
            if any(kw in user_input for kw in keywords):
                detected_genre = genre
                break

        # 识别受众
        detected_audience = ""
        for audience, keywords in audience_keywords.items():
            if any(kw in user_input for kw in keywords):
                detected_audience = audience
                break

        return {
            "need_search": need_search,
            "platform": detected_platform,
            "genre": detected_genre,
            "target_audience": detected_audience,
            "user_input": user_input
        }
    
    def _handle_smart_conversation(self, user_input: str) -> bool:
        """
        智能对话处理：自动识别意图并执行

        流程：
        1. 检测用户意图（是否需要搜索数据）
        2. 如果需要搜索 → 调用ScoutAgent搜索 → 分析
        3. 如果不需要 → 普通LLM对话
        """
        if not self.llm_client:
            print("LLM未初始化")
            return True

        try:
            # 1. 检测搜索意图
            intent = self._detect_search_intent(user_input)

            if intent["need_search"] and (intent["platform"] or intent["genre"]):
                return self._handle_search_and_analyze(intent)

            # 2. 普通对话
            return self._handle_normal_conversation(user_input)

        except Exception as e:
            print(f"错误:{e}")
            return True
    
    def _handle_search_and_analyze(self, intent: Dict[str, Any]) -> bool:
        """
        搜索数据并分析（核心流程）

        流程：
        1. 调用ScoutAgent搜索 → 2. 分析爆火特征 → 3. 更新知识库 → 4. 生成报告
        """
        platform = intent["platform"] or "番茄小说"
        genre = intent["genre"] or ""
        target_audience = intent.get("target_audience", "")
        user_input = intent["user_input"]

        # 构建约束条件
        constraints = {}
        if target_audience:
            constraints["target_audience"] = target_audience

        # 步骤1：调用ScoutAgent搜索热门小说
        self.progress.start_task(f"正在搜索{platform}的{genre}类热门小说...", total=4)
        self.progress.update_progress(1, f"连接{platform}...")

        try:
            # 调用ScoutAgent的analyze_genre方法
            analysis_result = self.scout_agent.analyze_genre(genre, constraints)

            if not analysis_result or "error" in analysis_result:
                self.progress.fail_task(f"搜索失败: {analysis_result.get('error', '未知错误')}")
                return self._handle_normal_conversation(user_input)

            hot_novels = analysis_result.get("hot_novels", [])
            self.progress.update_progress(2, f"获取到{len(hot_novels)}部小说")

            # 步骤2：提取爆火特征
            self.progress.update_progress(3, "分析爆火特征...")
            common_features = analysis_result.get("common_features", {})
            suggestions = analysis_result.get("suggestions", [])

            # 步骤3：更新知识库
            self._update_genre_knowledge_from_analysis(analysis_result, genre)
            self.progress.update_progress(4, "知识库已更新")

            # 步骤4：生成分析报告
            self.progress.start_task("正在生成分析报告...", total=1)
            analysis = self._generate_search_analysis(analysis_result, genre, platform, user_input)
            self.progress.complete_task("分析完成")

            # 输出结果
            print(f"\n{analysis}")

            # 保存对话历史
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": analysis})

            return True

        except Exception as e:
            self.progress.fail_task(f"搜索分析失败: {e}")
            return self._handle_normal_conversation(user_input)
    
    def _update_genre_knowledge_from_analysis(self, analysis_result: Dict[str, Any], genre: str):
        """
        根据搜索结果更新题材知识库

        将爆火小说的写法特征记录到知识库中
        """
        if not analysis_result:
            return

        # 从分析结果中提取数据
        hot_novels = analysis_result.get("hot_novels", [])
        common_features = analysis_result.get("common_features", {})
        suggestions = analysis_result.get("suggestions", [])

        # 构造小说数据摘要
        novel_summaries = []
        for novel in hot_novels[:5]:  # 取前5部
            novel_summaries.append({
                "title": novel.get("title", ""),
                "author": novel.get("author", ""),
                "popularity": novel.get("popularity", ""),
                "brief": novel.get("brief", ""),
                "tags": novel.get("tags", [])
            })

        try:
            # 更新知识库
            existing = self.genre_kb.get_genre(genre)
            if existing:
                # 更新现有题材的热点信息
                existing["hot_topics"] = common_features.get("success_factors", [])
                existing["common_tropes"] = common_features.get("common_plot_templates", existing.get("common_tropes", []))
                existing["character_templates"] = common_features.get("common_character_archetypes", [])
                existing["last_updated"] = str(__import__('datetime').datetime.now())
                self.genre_kb.update_genre(genre, existing)
            else:
                # 创建新题材
                new_genre = {
                    "name": genre,
                    "tags": list(set(tag for n in hot_novels for tag in n.get("tags", []))),
                    "writing_style": common_features.get("success_factors", [""]),
                    "plot_systems": common_features.get("common_plot_templates", []),
                    "character_templates": common_features.get("common_character_archetypes", []),
                    "common_tropes": common_features.get("common_plot_templates", []),
                    "hot_topics": common_features.get("success_factors", []),
                    "last_updated": str(__import__('datetime').datetime.now())
                }
                self.genre_kb.add_genre(genre, new_genre)

        except Exception as e:
            print(f"更新知识库失败: {e}")
    
    def _generate_search_analysis(self, analysis_result: Dict[str, Any], genre: str, platform: str,
                                  user_input: str) -> str:
        """让LLM基于搜索结果生成分析报告"""
        hot_novels = analysis_result.get("hot_novels", [])
        common_features = analysis_result.get("common_features", {})
        suggestions = analysis_result.get("suggestions", [])

        novel_data = json.dumps(hot_novels[:10], ensure_ascii=False, indent=2)
        features_data = json.dumps(common_features, ensure_ascii=False, indent=2)
        suggestions_data = json.dumps(suggestions, ensure_ascii=False, indent=2)

        prompt = f"""你是一个专业的网络小说市场分析师。基于以下从{platform}搜索到的{genre}类热门小说数据，为用户提供分析。

用户问题：{user_input}

搜索到的热门小说数据：
{novel_data}

共性特征分析：
{features_data}

创作建议：
{suggestions_data}

请基于以上数据回答用户问题，要求：
1. 引用具体的小说名称和数据
2. 分析这些作品的共同爆火特征
3. 给出创作建议
4. 如果不是爽文方向，特别说明如何在保持吸引力的同时避免纯爽文套路

注意：以上数据是通过搜索获取的，请基于此分析。"""

        try:
            response = self.llm_client.chat_with_system(
                system_prompt="你是专业的网络小说市场分析师，基于搜索数据提供分析。",
                user_message=prompt,
                history=[]
            )
            return response
        except Exception as e:
            return f"分析生成失败: {e}"

    def _handle_search_command(self, user_input: str):
        """处理显式搜索命令"""
        # 解析命令参数
        parts = user_input.split()
        platform = "番茄小说"
        genre = ""  # 默认为空，不强制指定
        target_audience = ""

        # 简单解析：search 平台 题材 [受众]
        platform_keywords = {"番茄": "番茄小说", "起点": "起点中文网", "七猫": "七猫小说"}
        for part in parts[1:]:
            for kw, pname in platform_keywords.items():
                if kw in part:
                    platform = pname

        # 扩展题材识别
        genre_keywords = {
            "游戏": ["游戏", "网游", "系统流"],
            "玄幻": ["玄幻", "修仙", "仙侠", "修真"],
            "都市": ["都市", "现代", "职场"],
            "科幻": ["科幻", "未来", "星际"],
            "历史": ["历史", "古代", "穿越", "架空"],
            "悬疑": ["悬疑", "推理", "侦探", "恐怖"],
            "末世": ["末世", "末日", "废土", "生存"],
            "言情": ["言情", "恋爱", "爱情"],
            "奇幻": ["奇幻", "魔法", "异世界"],
            "武侠": ["武侠", "江湖", "武林"]
        }
        for part in parts[1:]:
            for gname, keywords in genre_keywords.items():
                if any(kw in part for kw in keywords):
                    genre = gname
                    break

        # 检测受众
        audience_keywords = {"男频": "男频", "女频": "女频"}
        for part in parts[1:]:
            for kw, aname in audience_keywords.items():
                if kw in part:
                    target_audience = aname

        intent = {
            "need_search": True,
            "platform": platform,
            "genre": genre,
            "target_audience": target_audience,
            "user_input": f"查看{platform}{target_audience}{genre}类热门小说"
        }
        return self._handle_search_and_analyze(intent)

    def _show_flow_command(self, user_input: str):
        """处理流程命令"""
        parts = user_input.split()

        # 无参数：显示所有可用流程
        if len(parts) == 1:
            self._show_available_flows()
            return

        # 解析流程命令
        action = parts[1].lower() if len(parts) > 1 else ""

        if action in ['list', '列表', '所有']:
            self._show_available_flows()
        elif action in ['show', '显示', '查看']:
            if len(parts) > 2:
                flow_key = parts[2]
                self._show_flow_detail(flow_key)
            else:
                print("请指定流程名称，如：flow show novel_creation")
        elif action in ['run', '执行', '运行']:
            if len(parts) > 2:
                flow_key = parts[2]
                self._execute_flow(flow_key)
            else:
                print("请指定要执行的流程，如：flow run novel_creation")
        elif action in ['custom', '自定义']:
            self._create_custom_flow_interactive()
        else:
            print("未知命令。可用命令：list/show/run/custom")

    def _show_available_flows(self):
        """显示所有可用流程"""
        flows = self.flow_manager.list_flows()

        print("\n可用流程列表：")

        for flow in flows:
            custom_mark = " [自定义]" if flow.get("custom") else ""
            print(f"{flow['key']}: {flow['name']}{custom_mark}")
            print(f"  描述: {flow['description']}")
            print(f"  步骤数: {flow['step_count']}")
            print()

    def _show_flow_detail(self, flow_key: str):
        """显示流程详情"""
        if not self.flow_manager.select_flow(flow_key):
            print(f"流程 '{flow_key}' 不存在")
            return

        print(self.flow_manager.generate_flow_display())

    def _execute_flow(self, flow_key: str):
        """执行流程"""
        if not self.flow_manager.select_flow(flow_key):
            print(f"流程 '{flow_key}' 不存在")
            return

        print(self.flow_manager.generate_flow_display())
        print("\n开始执行流程...\n")

        # 流程上下文：保存每个步骤的输出，供后续步骤使用
        flow_context = {}

        # 执行流程中的每个步骤
        while True:
            step = self.flow_manager.get_current_step()
            if not step:
                break

            # 显示当前执行的Agent
            print(self.flow_manager.get_agent_status_display(step, "running"))

            try:
                # 执行Agent，传入流程上下文
                result = self._execute_agent_step(step, flow_context)

                # 保存结果到上下文
                flow_context[step['agent']] = result

                # 记录成功
                self.flow_manager.log_execution(step, "success", result)
                print(f"✓ 完成: {step['name']}\n")

            except Exception as e:
                # 记录失败
                self.flow_manager.log_execution(step, "failed", error=str(e))
                print(f"✗ 失败: {step['name']} - {e}\n")

            # 前进到下一步
            self.flow_manager.next_step()

        # 显示执行报告
        report = self.flow_manager.get_execution_report()
        print("流程执行完成")
        print(f"总步骤: {report['total_steps']}")
        print(f"成功: {report['success_count']}")
        print(f"失败: {report['failed_count']}")

    def _execute_agent_step(self, step: Dict[str, Any], flow_context: Dict[str, Any]) -> Any:
        """
        执行单个Agent步骤
        
        Args:
            step: 当前步骤信息
            flow_context: 流程上下文，包含前置步骤的输出
        
        Returns:
            Agent执行结果
        """
        agent_name = step['agent']
        method_name = step['method']

        # 获取对应的Agent实例
        agent_map = {
            'scout': self.scout_agent,
            'architect': self.architect_agent,
            'writer': self.writer_agent,
            'auditor': self.auditor_agent,
            'revisor': self.revisor_agent,
            'style_engineer': self.style_engineer_agent
        }

        agent = agent_map.get(agent_name)
        if not agent:
            raise Exception(f"Agent '{agent_name}' 未初始化")

        # 获取方法
        method = getattr(agent, method_name, None)
        if not method:
            raise Exception(f"Agent '{agent_name}' 没有方法 '{method_name}'")

        # 根据Agent类型和前置步骤结果调用方法
        if agent_name == 'scout':
            # 扫榜分析师需要题材参数
            genre = flow_context.get('genre', '')
            return method(genre=genre)
        
        elif agent_name == 'architect':
            # 架构师需要扫榜结果
            if 'scout' not in flow_context:
                raise Exception("架构师需要先执行扫榜分析")
            scout_result = flow_context['scout']
            return method(analysis_result=scout_result)
        
        elif agent_name == 'writer':
            # 写手需要大纲规划
            if 'architect' not in flow_context:
                raise Exception("写手需要先执行大纲规划")
            outline = flow_context['architect']
            chapter_num = flow_context.get('chapter_num', 1)
            return method(outline=outline, chapter_num=chapter_num)
        
        elif agent_name == 'style_engineer':
            # 文风工程师需要章节内容
            if 'writer' not in flow_context:
                raise Exception("文风工程师需要先执行章节生成")
            chapter_content = flow_context['writer']
            return method(chapter_content=chapter_content)
        
        elif agent_name == 'auditor':
            # 审计员需要章节内容
            if 'writer' not in flow_context:
                raise Exception("审计员需要先执行章节生成")
            chapter_content = flow_context['writer']
            return method(chapter_content=chapter_content)
        
        elif agent_name == 'revisor':
            # 修订员需要审计报告
            if 'auditor' not in flow_context:
                raise Exception("修订员需要先执行质量审计")
            if 'writer' not in flow_context:
                raise Exception("修订员需要章节内容")
            audit_result = flow_context['auditor']
            chapter_content = flow_context['writer']
            return method(audit_result=audit_result, chapter_content=chapter_content)
        
        else:
            # 其他Agent直接调用
            return method()

    def _create_custom_flow_interactive(self):
        """交互式创建自定义流程"""
        print("\n创建自定义流程")

        flow_key = input("流程标识符（英文，如 my_flow）: ").strip()
        if not flow_key:
            print("取消创建")
            return

        name = input("流程名称: ").strip()
        description = input("流程描述: ").strip()

        print("\n可用Agent:")
        print("  scout - 扫榜分析师")
        print("  architect - 架构师")
        print("  writer - 写手")
        print("  style_engineer - 文风工程师")
        print("  auditor - 审计员")
        print("  revisor - 修订员")

        print("\n请输入Agent调用顺序（用逗号分隔，如：scout,architect,writer）")
        agents_input = input("Agent顺序: ").strip()

        if not agents_input:
            print("取消创建")
            return

        # 解析Agent顺序
        agent_names = [a.strip() for a in agents_input.split(',')]

        # 构建步骤
        steps = []
        agent_info = {
            'scout': {'name': '扫榜分析师', 'description': '分析热门小说', 'method': 'analyze_genre'},
            'architect': {'name': '架构师', 'description': '规划大纲', 'method': 'plan_novel'},
            'writer': {'name': '写手', 'description': '生成章节', 'method': 'generate_chapter'},
            'style_engineer': {'name': '文风工程师', 'description': '分析文风', 'method': 'analyze_writing_style'},
            'auditor': {'name': '审计员', 'description': '审核质量', 'method': 'audit_chapter'},
            'revisor': {'name': '修订员', 'description': '修订内容', 'method': 'revise_chapter'}
        }

        for agent_key in agent_names:
            if agent_key in agent_info:
                step = {
                    'agent': agent_key,
                    'name': agent_info[agent_key]['name'],
                    'description': agent_info[agent_key]['description'],
                    'method': agent_info[agent_key]['method']
                }
                steps.append(step)
            else:
                print(f"警告: 未知的Agent '{agent_key}'，已跳过")

        if not steps:
            print("没有有效的Agent，取消创建")
            return

        # 创建流程
        if self.flow_manager.create_custom_flow(flow_key, name, description, steps):
            print(f"\n✓ 自定义流程 '{name}' 创建成功")
            print(f"使用 'flow run {flow_key}' 执行该流程")
        else:
            print("\n✗ 创建失败")

    def _detect_url(self, user_input: str) -> bool:
        """检测用户输入是否包含URL"""
        import re
        url_pattern = r'https?://[^\s]+'
        return bool(re.search(url_pattern, user_input))

    def _handle_url_content(self, user_input: str) -> bool:
        """处理包含URL的输入，获取网页内容并分析"""
        import re

        # 提取URL
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, user_input)

        if not urls:
            return self._handle_normal_conversation(user_input)

        url = urls[0]

        try:
            self.progress.start_task(f"正在获取网页内容: {url}", total=2)

            # 获取网页内容
            self.progress.update_progress(1, "正在请求网页...")
            content_result = self.web_search.fetch_url(url)

            if "error" in content_result:
                self.progress.fail_task(f"获取失败: {content_result['error']}")
                return self._handle_normal_conversation(user_input)

            content = content_result.get("content", "")
            title = content_result.get("title", "")

            if not content:
                self.progress.fail_task("网页内容为空")
                return self._handle_normal_conversation(user_input)

            self.progress.update_progress(2, "正在分析内容...")

            # 让LLM分析网页内容
            analysis_prompt = f"""用户提供了以下网页链接和内容，请进行分析：

用户问题：{user_input}

网页标题：{title}
网页链接：{url}

网页内容：
{content[:3000]}...

请基于以上内容回答用户的问题，如果是小说页面，请分析：
1. 小说的基本信息（书名、作者、题材、标签）
2. 小说的写作特点（开篇方式、节奏、人设）
3. 小说的优缺点
4. 对创作的参考价值"""

            response = self.llm_client.chat_with_system(
                system_prompt="你是专业的网络小说分析师，基于网页内容提供分析。",
                user_message=analysis_prompt,
                history=[]
            )

            self.progress.complete_task("分析完成")
            print(response)

            # 保存对话历史
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response})

            return True

        except Exception as e:
            self.progress.fail_task(f"分析失败: {e}")
            return self._handle_normal_conversation(user_input)

    def _handle_normal_conversation(self, user_input: str) -> bool:
        """处理普通对话（无搜索意图）"""
        if not self.llm_client:
            print("LLM未初始化")
            return True
        
        try:
            self.progress.start_task("正在思考...", total=1)
            
            system_prompt = """你是一个专业的网络文学小说创作顾问Agent。你的核心职责是帮助用户从零开始创作高质量的网络小说。

【基本原则】
1. 循序渐进：每个步骤只输出当前阶段的内容
2. 用户至上：用户可以随时修改前面的步骤
3. 主动判断：自动识别用户需要哪个功能
4. 迭代更新：知识库、大纲、规划等都是活的
5. 质量保证：输出前必须经过Quality Gate检查

【沟通风格】
- 专业但不生硬
- 给出明确的选择项
- 对用户的反馈要快速反应并记忆

现在用户正在和你对话，请根据他们的需求提供帮助。"""
            
            response = self.llm_client.chat_with_system(
                system_prompt=system_prompt,
                user_message=user_input,
                history=self.conversation_history
            )
            
            self.progress.complete_task("完成")
            
            # 保存对话历史
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            if len(self.conversation_history) > self.max_history_length * 2:
                self.conversation_history = self.conversation_history[-int(self.max_history_length) * 2:]
            
            print(response)
        except Exception as e:
            self.progress.fail_task(f"错误: {e}")
        
        return True
    
    def run(self):
        """运行主循环"""
        if not self.initialize():
            return
        
        self.show_welcome()
        
        self.running = True
        while self.running:
            try:
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
                
                self.running = self.process_command(user_input)
                
            except KeyboardInterrupt:
                confirm = input("\n退出?(y/n)").strip().lower()
                if confirm in ['y', 'yes']:
                    print("再见")
                    break
            except Exception as e:
                print(f"错误:{e}")


def main():
    """主函数"""
    cli = NovelAgentCLI()
    cli.run()


if __name__ == "__main__":
    main()
