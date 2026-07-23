"""
Prompt模板加载器模块

核心职责：
- 加载和管理SubAgent的Prompt模板文件（Markdown格式）
- 实现模板参数的动态填充，支持多种数据类型
- 提供模板查询和参数提取功能

设计思路：
- 模板文件存储在templates目录，使用.md格式便于编辑和维护
- 参数占位符采用{param_name}格式，支持正则表达式提取
- 支持多种数据类型的自动转换：字典→JSON、列表→逗号分隔、其他→字符串
- 提供模板列表查询和参数提取接口，便于动态调用

使用场景：
- MainAgent调用SubAgent前，加载对应的Prompt模板
- 根据当前上下文填充模板参数（如：题材、用户约束、分析范围等）
- 生成完整的Prompt后传递给LLM

关键算法：
- 参数填充：遍历参数字典，根据类型自动转换并替换占位符
- 参数提取：使用正则表达式 re.findall(r'\{(\w+)\}', template) 提取所有占位符
- 模板列表：扫描templates目录，返回所有.md文件的名称（去掉后缀）

模板文件示例（scout_prompt.md）：
```markdown
# SubAgent-Scout（扫榜分析师）

## 身份定义
你是一位专业的网络文学市场分析师...

## 输入参数
- 题材类型: {genre}
- 用户约束: {constraints}
- 分析范围: {scope}

## 输出格式
{output_format}
```

调用示例：
```python
loader = PromptLoader()
prompt = loader.fill_template(
    "scout_prompt",
    {
        "genre": "玄幻",
        "constraints": "不要后宫",
        "scope": "起点TOP100",
        "output_format": {...}
    }
)
```
"""
import os
import re
from typing import Dict, Any, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class PromptLoader:
    """
    Prompt模板加载器
    
    核心功能：
    1. 模板加载：从templates目录加载.md格式的Prompt模板
    2. 参数填充：将字典中的参数替换到模板的占位符中
    3. 类型转换：自动处理dict/list/str等不同数据类型的转换
    4. 模板查询：列出所有可用模板和模板所需的参数
    
    设计特点：
    - 模板与代码分离，便于维护和迭代
    - 支持多种数据类型的自动转换
    - 提供模板和参数的查询接口
    - 异常处理：模板不存在或加载失败时返回None
    
    使用流程：
    1. 初始化PromptLoader（自动设置templates目录）
    2. 调用fill_template(template_name, params)加载并填充模板
    3. 返回完整的Prompt字符串，可直接传递给LLM
    """
    
    def __init__(self):
        """初始化Prompt加载器"""
        self.templates_dir = config.TEMPLATES_DIR
    
    def load_template(self, template_name: str) -> Optional[str]:
        """加载Prompt模板文件
        
        Args:
            template_name: 模板名称（如：scout_prompt）
        
        Returns:
            模板内容，不存在则返回None
        """
        template_file = os.path.join(self.templates_dir, f"{template_name}.md")
        
        if not os.path.exists(template_file):
            return None
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None
    
    def fill_template(self, template_name: str, params: Dict[str, Any]) -> Optional[str]:
        """加载模板并填充参数
        
        Args:
            template_name: 模板名称
            params: 参数字典
        
        Returns:
            填充后的Prompt，模板不存在则返回None
        """
        template = self.load_template(template_name)
        
        if not template:
            return None
        
        # 替换所有 {param_name} 占位符
        filled_prompt = template
        
        for key, value in params.items():
            # 处理不同类型的值
            if isinstance(value, dict):
                # 字典转为JSON字符串
                import json
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
            elif isinstance(value, list):
                # 列表转为逗号分隔的字符串
                value_str = ", ".join(str(item) for item in value)
            else:
                # 其他类型直接转字符串
                value_str = str(value)
            
            # 替换占位符
            placeholder = f"{{{key}}}"
            filled_prompt = filled_prompt.replace(placeholder, value_str)
        
        return filled_prompt
    
    def get_available_templates(self) -> list:
        """获取所有可用的模板列表
        
        Returns:
            模板名称列表
        """
        if not os.path.exists(self.templates_dir):
            return []
        
        templates = []
        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".md"):
                template_name = filename[:-3]  # 去掉.md后缀
                templates.append(template_name)
        
        return sorted(templates)
    
    def get_template_params(self, template_name: str) -> list:
        """获取模板所需的参数列表
        
        Args:
            template_name: 模板名称
        
        Returns:
            参数名称列表
        """
        template = self.load_template(template_name)
        
        if not template:
            return []
        
        # 使用正则表达式提取所有 {param_name} 占位符
        params = re.findall(r'\{(\w+)\}', template)
        
        # 去重
        return list(set(params))
