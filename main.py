#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络文学小说创作Agent系统 - 主程序入口

核心职责：
- 提供命令行交互界面，接收用户输入并路由到对应功能
- 初始化系统，检查API密钥和连接状态
- 管理主循环，处理命令和对话
- 集成LLM客户端，提供智能对话能力

设计思路：
- 采用极简CLI设计，去除emoji和装饰性输出，节省token
- 命令识别采用关键词匹配，支持中英文命令（如：help/帮助、quit/退出）
- 对话处理采用系统提示词+用户消息的模式，调用LLM生成回复
- 文件路径检测：自动识别用户输入是否为文件路径，支持docx/pdf/txt/md格式

使用方式：
    python main.py

功能流程：
    1. 启动程序 → 检查API密钥 → 测试连接 → 显示欢迎信息
    2. 用户输入命令或对话 → 识别命令类型 → 执行对应操作
    3. 支持命令：help（帮助）、quit（退出）、status（状态）、test（测试连接）
    4. 支持文件导入：直接输入文件路径，自动检测格式
    5. 普通对话：调用LLM生成回复

系统提示词设计：
    - 角色定位：专业的网络文学小说创作顾问Agent
    - 基本原则：循序渐进、用户至上、主动判断、迭代更新、质量保证
    - 沟通风格：专业但不生硬，给出明确选择项，快速响应用户反馈
"""

import os
import sys
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from utils.llm_client import get_llm_client, test_connection


class NovelAgentCLI:
    """
    小说创作Agent系统命令行界面
    
    核心功能：
    1. 系统初始化：检查API密钥、测试连接、初始化LLM客户端
    2. 命令处理：识别并执行help/quit/status/test等命令
    3. 文件导入：检测用户输入的文件路径，支持多种格式
    4. 智能对话：调用LLM生成回复，提供创作建议
    
    设计特点：
    - 极简CLI设计，节省token
    - 支持中英文命令
    - 自动检测文件路径
    - 异常处理：捕获并处理各种异常情况
    
    使用流程：
    1. 运行python main.py启动程序
    2. 系统自动检查API密钥和连接
    3. 显示欢迎信息和可用命令
    4. 用户输入命令或对话
    5. 系统识别并执行对应操作
    6. 循环直到用户退出
    """
    
    def __init__(self):
        self.llm_client = None
        self.running = False
        
    def initialize(self):
        """初始化系统"""
        print("\n小说创作Agent系统")
        
        # 检查LLM提供商
        if config.LLM_PROVIDER not in ['deepseek', 'kimi', 'glm']:
            print(f"错误：不支持的LLM提供商 {config.LLM_PROVIDER}")
            print("请在config.py中设置为deepseek/kimi/glm")
            return False
        
        # 检查API密钥
        if not config.LLM_API_KEY:
            print("错误：未检测到API密钥")
            print("请在config.py中设置LLM_API_KEY")
            return False
        
        # 测试API连接
        print("连接AI服务...")
        if test_connection():
            print("连接成功")
            self.llm_client = get_llm_client()
            return True
        else:
            print("连接失败，请检查网络或API密钥")
            return False
    
    def show_welcome(self):
        """显示欢迎信息"""
        print("\n功能：1.分析爆火小说 2.规划大纲 3.生成章节 4.导入文件")
        print("命令：help-帮助 quit-退出 status-状态")
    
    def show_help(self):
        """显示帮助信息"""
        print("\n帮助：")
        print("命令：help quit exit status test")
        print("流程：说需求→分析→规划→生成")
        print("文件：直接输入路径(支持docx/pdf/txt/md)")
    
    def show_status(self):
        """显示当前状态"""
        print(f"\n模型:{config.LLM_MODEL} 提供商:{config.LLM_PROVIDER}")
        print(f"API:{'已设置' if config.LLM_API_KEY else '未设置'} 状态:就绪")
    
    def process_command(self, user_input: str) -> bool:
        """处理用户输入"""
        user_input = user_input.strip().lower()
        
        if user_input in ['quit', 'exit', 'q', '退出']:
            print("再见")
            return False
        
        # 帮助命令
        elif user_input in ['help', 'h', '帮助', '?']:
            self.show_help()
            return True
        
        # 状态命令
        elif user_input in ['status', '状态']:
            self.show_status()
            return True
        
        # 测试命令
        elif user_input in ['test', '测试']:
            print("测试连接...")
            if test_connection():
                print("正常")
            else:
                print("失败")
            return True
        
        # 文件路径检测
        elif os.path.exists(user_input):
            print(f"文件:{user_input}")
            print("导入功能开发中")
            return True
        
        # 普通对话（调用LLM）
        else:
            return self.handle_conversation(user_input)
    
    def handle_conversation(self, user_input: str) -> bool:
        """处理普通对话"""
        if not self.llm_client:
            print("LLM未初始化")
            return True
        
        try:
            # 构建系统提示词
            system_prompt = """你是一个专业的网络文学小说创作顾问Agent。你的核心职责是帮助用户从零开始创作高质量的网络小说。

【基本原则】
1. 循序渐进：每个步骤只输出当前阶段的内容，不提前暴露后续步骤
2. 用户至上：用户可以随时修改前面的步骤，你需要记忆这些修改并影响后续步骤
3. 主动判断：自动识别用户需要哪个功能，但也允许用户强制调用
4. 迭代更新：知识库、大纲、规划等都是活的，需要不断更新
5. 质量保证：输出前必须经过Quality Gate检查，发现问题则返回上一步重新规划

【沟通风格】
- 专业但不生硬
- 给出明确的选择项
- 对用户的反馈要快速反应并记忆

现在用户正在和你对话，请根据他们的需求提供帮助。"""
            
            # 调用LLM
            response = self.llm_client.chat_with_system(
                system_prompt=system_prompt,
                user_message=user_input
            )
            print(response)
        except Exception as e:
            print(f"错误:{e}")
        
        return True
    
    def run(self):
        """运行主循环"""
        # 初始化
        if not self.initialize():
            return
        
        # 显示欢迎信息
        self.show_welcome()
        
        # 主循环
        self.running = True
        while self.running:
            try:
                user_input = input("> ").strip()
                if not user_input:
                    continue
                
                # 处理命令
                self.running = self.process_command(user_input)
                
            except KeyboardInterrupt:
                confirm = input("退出?(y/n)").strip().lower()
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
