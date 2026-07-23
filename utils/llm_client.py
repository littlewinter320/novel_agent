"""
LLM客户端封装模块 - 支持多提供商（Kimi/DeepSeek/GLM/Claude/OpenAI等）

核心职责：
- 封装多个LLM提供商的API调用逻辑，提供统一接口
- 支持OpenAI兼容API（Kimi、DeepSeek、GLM）和原生API（Claude）
- 管理API密钥和连接配置
- 提供单例模式，避免重复创建客户端实例

设计思路：
- 使用工厂模式根据provider选择不同的客户端实现
- OpenAI兼容API：使用OpenAI SDK（Kimi、DeepSeek、GLM、OpenAI等）
- Claude原生API：使用anthropic SDK
- 采用单例模式（get_llm_client）确保全局只有一个客户端实例
- 提供三种调用方式：chat（完整消息列表）、chat_with_system（带系统提示）、generate（简单生成）
- 参数优先级：方法参数 > 配置参数 > 默认值

支持的提供商：
- kimi: 月之暗面Kimi（OpenAI兼容）
- deepseek: DeepSeek（OpenAI兼容）
- glm: 智谱GLM（OpenAI兼容）
- claude: Anthropic Claude（原生API）
- openai: OpenAI官方（OpenAI兼容）
- custom: 自定义OpenAI兼容API

关键配置：
- LLM_PROVIDER: 提供商类型
- LLM_MODEL: 模型名称
- LLM_API_KEY: API密钥（必须配置）
- LLM_BASE_URL: API基础URL（OpenAI兼容API需要）
- LLM_TEMPERATURE: 温度参数
- LLM_MAX_TOKENS: 最大输出token数

使用示例：
    client = get_llm_client()
    response = client.generate("你好")
    response = client.chat_with_system("你是小说创作助手", "帮我写个开头")
"""
import os
import sys
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# 尝试导入OpenAI SDK
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

# 尝试导入Anthropic SDK（Claude）
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


class LLMClient:
    """
    LLM调用客户端（多提供商支持）
    
    核心功能：
    1. 支持多个LLM提供商（Kimi、DeepSeek、GLM、Claude、OpenAI等）
    2. 自动根据provider选择合适的SDK和调用方式
    3. 提供统一的调用接口：chat、chat_with_system、generate
    4. 自动处理API密钥验证和错误提示
    
    设计特点：
    - 工厂模式：根据provider选择不同的客户端实现
    - OpenAI兼容API：使用OpenAI SDK（Kimi、DeepSeek、GLM、OpenAI）
    - Claude原生API：使用anthropic SDK
    - 参数优先级：方法参数 > 实例配置 > config配置
    - 单例模式通过get_llm_client()实现
    - 错误处理：缺少依赖或缺少API密钥时给出明确提示
    
    使用场景：
    - MainAgent意图识别时调用LLM辅助判断
    - SubAgent生成内容时调用LLM
    - 任何需要LLM推理的场景
    """
    
    # 提供商配置映射
    PROVIDER_CONFIG = {
        "kimi": {
            "sdk": "openai",
            "default_base_url": "https://api.moonshot.cn/v1",
            "default_model": "kimi-k2.5",
        },
        "deepseek": {
            "sdk": "openai",
            "default_base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat",
        },
        "glm": {
            "sdk": "openai",
            "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
            "default_model": "glm-4",
        },
        "openai": {
            "sdk": "openai",
            "default_base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4",
        },
        "claude": {
            "sdk": "anthropic",
            "default_base_url": None,  # Claude不需要base_url
            "default_model": "claude-3-5-sonnet-20241022",
        },
        "custom": {
            "sdk": "openai",
            "default_base_url": None,  # 用户必须提供
            "default_model": None,  # 用户必须提供
        },
    }
    
    def __init__(self, provider: str = None, model: str = None, api_key: str = None, base_url: str = None):
        """
        初始化LLM客户端
        
        参数优先级：传入参数 > config配置 > 提供商默认值
        
        Args:
            provider: 提供商类型（kimi/deepseek/glm/claude/openai/custom）
            model: 模型名称（如kimi-k2.5、deepseek-chat、glm-4、claude-3-5-sonnet等）
            api_key: API密钥（必须提供）
            base_url: API基础URL（OpenAI兼容API需要，Claude不需要）
        
        Raises:
            ImportError: 未安装必要的SDK库
            ValueError: 未设置API密钥或配置错误
        """
        # 使用传入参数或config配置
        self.provider = provider or config.LLM_PROVIDER
        self.provider = self.provider.lower()
        
        # 获取提供商配置
        provider_config = self.PROVIDER_CONFIG.get(self.provider)
        if not provider_config:
            raise ValueError(
                f"不支持的提供商: {self.provider}\n"
                f"支持的提供商: {', '.join(self.PROVIDER_CONFIG.keys())}"
            )
        
        # 设置模型和base_url
        self.model = model or config.LLM_MODEL or provider_config["default_model"]
        self.api_key = api_key or config.LLM_API_KEY
        self.base_url = base_url or config.LLM_BASE_URL or provider_config["default_base_url"]
        self.temperature = config.LLM_TEMPERATURE
        self.max_tokens = config.LLM_MAX_TOKENS
        
        # 验证API密钥
        if not self.api_key:
            raise ValueError(
                f"请设置API密钥。方式：\n"
                f"  1. 设置环境变量: export LLM_API_KEY='your-key'\n"
                f"  2. 或在config.py中设置 LLM_API_KEY\n"
                f"  3. 或初始化时传入: LLMClient(api_key='your-key')"
            )
        
        # 根据SDK类型创建客户端
        self.sdk_type = provider_config["sdk"]
        self.client = None
        
        if self.sdk_type == "openai":
            # OpenAI兼容API
            if not OPENAI_AVAILABLE:
                raise ImportError("请先安装openai库: pip install openai")
            
            if not self.base_url:
                raise ValueError(f"提供商 {self.provider} 需要提供 base_url")
            
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        
        elif self.sdk_type == "anthropic":
            # Claude原生API
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("请先安装anthropic库: pip install anthropic")
            
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = None, max_tokens: int = None) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式 [{"role": "system/user/assistant", "content": "..."}]
                     - system: 系统提示，定义AI角色和行为
                     - user: 用户消息
                     - assistant: AI历史回复（用于多轮对话）
            temperature: 温度参数（0-2），控制随机性。越高越随机，越低越确定
            max_tokens: 最大输出token数，限制回复长度
        
        Returns:
            模型回复文本
        
        Raises:
            Exception: API调用失败时抛出
        
        示例：
            messages = [
                {"role": "system", "content": "你是小说创作助手"},
                {"role": "user", "content": "帮我写个开头"}
            ]
            response = client.chat(messages)
        """
        temp = temperature or self.temperature
        tokens = max_tokens or self.max_tokens
        
        if self.sdk_type == "openai":
            # OpenAI兼容API调用
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=tokens,
            )
            return response.choices[0].message.content
        
        elif self.sdk_type == "anthropic":
            # Claude原生API调用
            # 提取系统消息
            system_msg = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    chat_messages.append(msg)
            
            # Claude API调用
            response = self.client.messages.create(
                model=self.model,
                messages=chat_messages,
                system=system_msg if system_msg else None,
                temperature=temp,
                max_tokens=tokens,
            )
            return response.content[0].text
    
    def chat_with_system(self, system_prompt: str, user_message: str, 
                         history: List[Dict[str, str]] = None) -> str:
        """
        带系统提示词的聊天（简化接口）
        
        这是chat()的简化版本，自动构建消息列表。
        适用于需要定义AI角色但不需要精确控制消息格式的场景。
        
        Args:
            system_prompt: 系统提示词，定义AI角色和行为规则
            user_message: 用户消息
            history: 历史对话（可选），用于多轮对话上下文
        
        Returns:
            模型回复文本
        
        示例：
            response = client.chat_with_system(
                system_prompt="你是玄幻小说创作专家",
                user_message="帮我设计一个主角人设",
                history=[
                    {"role": "user", "content": "我想写玄幻小说"},
                    {"role": "assistant", "content": "好的，我来帮你..."}
                ]
            )
        """
        # 构建消息列表：系统提示 + 历史对话 + 当前用户消息
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": user_message})
        
        return self.chat(messages)
    
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """
        简单生成（无历史上下文）
        
        这是最简单的调用方式，适用于一次性生成任务。
        如果不提供system_prompt，则只发送user消息。
        
        Args:
            prompt: 用户提示（生成任务描述）
            system_prompt: 系统提示（可选，定义AI角色）
        
        Returns:
            模型回复文本
        
        示例：
            # 无系统提示
            response = client.generate("帮我写一个玄幻小说的开头")
            
            # 带系统提示
            response = client.generate(
                prompt="帮我设计一个主角人设",
                system_prompt="你是玄幻小说创作专家"
            )
        """
        if system_prompt:
            # 有系统提示：使用chat_with_system
            return self.chat_with_system(system_prompt, prompt)
        else:
            # 无系统提示：只发送user消息
            messages = [{"role": "user", "content": prompt}]
            return self.chat(messages)


# 全局单例：确保整个应用只有一个LLM客户端实例
_client: Optional[LLMClient] = None


def get_llm_client(**kwargs) -> LLMClient:
    """
    获取全局LLM客户端单例
    
    单例模式的优势：
    - 避免重复创建客户端实例，节省资源
    - 确保全局配置一致
    - 简化调用逻辑
    
    Args:
        **kwargs: 传递给LLMClient构造函数的参数
                 如果提供参数，会重新创建实例
    
    Returns:
        LLMClient实例
    
    示例：
        client = get_llm_client()
        response = client.generate("你好")
    """
    global _client
    # 如果实例不存在或提供了新参数，创建/重新创建实例
    if _client is None or kwargs:
        _client = LLMClient(**kwargs)
    return _client


def test_connection() -> bool:
    """
    测试API连接
    
    用于验证API配置是否正确，网络是否通畅。
    发送一个简单的测试消息，检查是否能收到有效回复。
    
    Returns:
        bool: 连接成功返回True，失败返回False
    
    示例：
        if test_connection():
            print("API连接正常")
        else:
            print("API连接失败，请检查配置")
    """
    try:
        client = get_llm_client()
        response = client.generate("你好，请回复'连接成功'")
        # 检查回复中是否包含关键词
        return "成功" in response or "连接" in response
    except Exception as e:
        print(f"连接测试失败: {e}")
        return False


if __name__ == "__main__":
    # 直接运行时执行连接测试
    print("测试LLM连接...")
    if test_connection():
        print("✓ API连接成功")
    else:
        print("✗ API连接失败，请检查配置")