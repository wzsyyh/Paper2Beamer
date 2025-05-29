"""
修订版TEX生成器：基于用户反馈修改演示文稿
"""
import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# 导入依赖
from dotenv import load_dotenv
from patch_openai import patch_langchain_openai, patch_openai_client

# 尝试加载环境变量
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("env.local"):
    load_dotenv("env.local")

# 应用OpenAI客户端补丁
patch_openai_client()
patch_langchain_openai()

# 尝试导入OpenAI相关包
try:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class RevisionTexGenerator:
    def __init__(
        self, 
        original_plan_path: str,
        previous_tex_path: str,
        output_dir: str = "output",
        model_name: str = "gpt-4o",
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        language: str = "zh",
        theme: str = "Madrid"
    ):
        """
        初始化修订版TEX生成器
        
        Args:
            original_plan_path: 原始演示计划JSON文件路径
            previous_tex_path: 先前版本的TEX文件路径
            output_dir: 输出目录
            model_name: 要使用的语言模型名称
            temperature: 模型生成的随机性程度
            api_key: OpenAI API密钥
            language: 输出语言，zh为中文，en为英文
            theme: Beamer主题
        """
        self.original_plan_path = original_plan_path
        self.previous_tex_path = previous_tex_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.language = language
        self.theme = theme
        
        # 创建日志记录器
        self.logger = logging.getLogger(__name__)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化语言模型
        self._init_model()
        
        # 加载原始演示计划
        self.original_plan = self._load_plan()
        
        # 加载先前版本的TEX代码
        self.previous_tex = self._load_previous_tex()
    
    def _init_model(self):
        """初始化语言模型"""
        if not OPENAI_AVAILABLE:
            self.logger.warning("无法导入OpenAI相关包，将无法使用大语言模型")
            self.llm = None
            return
            
        if not self.api_key:
            self.logger.warning("未提供OpenAI API密钥，将无法使用大语言模型")
            self.llm = None
            return
            
        try:
            self.llm = ChatOpenAI(
                model_name=self.model_name,
                temperature=self.temperature,
                openai_api_key=self.api_key
            )
            self.logger.info(f"已初始化语言模型: {self.model_name}")
        except Exception as e:
            self.logger.error(f"初始化语言模型失败: {str(e)}")
            self.llm = None
    
    def _load_plan(self) -> Dict[str, Any]:
        """加载原始演示计划"""
        try:
            with open(self.original_plan_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载原始演示计划失败: {str(e)}")
            return {}
    
    def _load_previous_tex(self) -> str:
        """加载先前版本的TEX代码"""
        try:
            with open(self.previous_tex_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"加载先前版本的TEX代码失败: {str(e)}")
            return ""
    
    def generate_revised_tex(self, user_feedback: str) -> Tuple[str, str]:
        """
        根据用户反馈生成修订版TEX代码
        
        Args:
            user_feedback: 用户反馈
            
        Returns:
            Tuple[str, str]: (修订版TEX代码, AI回复信息)
        """
        if not self.llm:
            self.logger.error("未初始化语言模型，无法生成修订版TEX代码")
            return "", "未初始化语言模型，无法生成修订版TEX代码"
            
        if not self.original_plan:
            self.logger.error("未加载原始演示计划，无法生成修订版TEX代码")
            return "", "未加载原始演示计划，无法生成修订版TEX代码"
            
        if not self.previous_tex:
            self.logger.error("未加载先前版本的TEX代码，无法生成修订版TEX代码")
            return "", "未加载先前版本的TEX代码，无法生成修订版TEX代码"
        
        # 提取演示文稿信息
        title = self.original_plan.get("title", "")
        authors = self.original_plan.get("authors", [])
        
        # 构建提示词
        system_message = f"""你是一位专业的Beamer演示文稿编辑助手，擅长根据用户的需求修改LaTeX Beamer幻灯片。

当前，你需要根据用户的反馈修改一个已经存在的Beamer演示文稿。我将提供给你：
1. 原始演示文稿的TEX代码
2. 用户对该演示文稿的修改建议

请你详细分析用户的反馈，并对TEX代码进行适当的修改，以满足用户的需求。注意保持原有演示文稿的整体风格和结构。

在响应中，请提供：
1. 完整的修订后的TEX代码
2. 简要说明你做了哪些修改来满足用户的需求

当前演示文稿信息：
- 标题: {title}
- 作者: {', '.join(authors)}
- 主题: {self.theme}
- 语言: {'中文' if self.language == 'zh' else '英文'}
"""

        human_message = f"""
原始TEX代码：
```latex
{self.previous_tex}
```

用户反馈：
{user_feedback}

请根据用户反馈修改TEX代码，并提供完整的修订版TEX代码。
"""
        
        # 构建提示模板
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=human_message)
        ]
        
        # 生成回复
        try:
            response = self.llm.invoke(messages)
            
            # 提取TEX代码
            tex_code = response.content
            
            # 尝试从回复中提取TEX代码块
            tex_pattern = r"```(?:latex)?\s*([\s\S]*?)```"
            tex_matches = re.findall(tex_pattern, tex_code)
            
            if tex_matches:
                # 使用最长的代码块作为TEX代码
                tex_code = max(tex_matches, key=len)
            else:
                # 如果没有代码块，尝试去除说明部分
                # 常见的说明前缀
                prefixes = [
                    "以下是修订后的TEX代码：",
                    "修订后的代码：",
                    "完整的修订版TEX代码：",
                    "以下是完整的修订版TEX代码：",
                    "以下是修改后的TEX代码："
                ]
                
                for prefix in prefixes:
                    if prefix in tex_code:
                        tex_code = tex_code.split(prefix, 1)[1].strip()
                        break
                        
                # 常见的说明后缀
                suffixes = [
                    "修改说明：",
                    "我做了以下修改：",
                    "以下是我所做的修改：",
                    "主要修改包括："
                ]
                
                for suffix in suffixes:
                    if suffix in tex_code:
                        tex_code = tex_code.split(suffix, 1)[0].strip()
                        
            # 确保TEX代码以documentclass开头
            if not tex_code.strip().startswith("\\documentclass"):
                # 可能是部分代码，使用原始TEX代码的文档类
                doc_class_match = re.search(r"(\\documentclass.*?\{.*?\}.*?)\\begin\{document\}", self.previous_tex, re.DOTALL)
                if doc_class_match:
                    preamble = doc_class_match.group(1)
                    # 检查TEX代码是否从begin{document}开始
                    if "\\begin{document}" in tex_code:
                        tex_code = preamble + "\n" + tex_code
                    else:
                        tex_code = preamble + "\n\\begin{document}\n" + tex_code + "\n\\end{document}"
            
            # 确保TEX代码包含完整的文档结构
            if "\\begin{document}" not in tex_code:
                tex_code = self.previous_tex.split("\\begin{document}")[0] + "\n\\begin{document}\n" + tex_code
            
            if "\\end{document}" not in tex_code:
                tex_code = tex_code + "\n\\end{document}"
                
            # 去除AI解释部分
            ai_message = response.content
            if "```" in ai_message:
                ai_parts = ai_message.split("```")
                # 提取所有非代码块部分
                ai_message = "".join([ai_parts[i] for i in range(0, len(ai_parts), 2)])
            
            return tex_code.strip(), ai_message.strip()
            
        except Exception as e:
            self.logger.error(f"生成修订版TEX代码失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return "", f"生成修订版TEX代码失败: {str(e)}"
    
    def save_revised_tex(self, tex_code: str) -> str:
        """
        保存修订版TEX代码
        
        Args:
            tex_code: 修订版TEX代码
            
        Returns:
            str: 保存的文件路径
        """
        try:
            # 创建一个唯一的文件名
            import time
            timestamp = int(time.time())
            output_file = os.path.join(self.output_dir, f"revised_{timestamp}.tex")
            
            # 保存TEX代码
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(tex_code)
                
            self.logger.info(f"修订版TEX代码已保存到: {output_file}")
            return output_file
        except Exception as e:
            self.logger.error(f"保存修订版TEX代码失败: {str(e)}")
            return ""

# 便捷函数
def generate_revised_tex(
    original_plan_path: str,
    previous_tex_path: str,
    user_feedback: str,
    output_dir: str = "output",
    model_name: str = "gpt-4o",
    language: str = "zh",
    theme: str = "Madrid"
) -> Tuple[str, str, str]:
    """
    生成修订版TEX代码（便捷函数）
    
    Args:
        original_plan_path: 原始演示计划JSON文件路径
        previous_tex_path: 先前版本的TEX文件路径
        user_feedback: 用户反馈
        output_dir: 输出目录
        model_name: 要使用的语言模型名称
        language: 输出语言，zh为中文，en为英文
        theme: Beamer主题
        
    Returns:
        Tuple[str, str, str]: (修订版TEX代码, 保存的文件路径, AI回复信息)
    """
    generator = RevisionTexGenerator(
        original_plan_path=original_plan_path,
        previous_tex_path=previous_tex_path,
        output_dir=output_dir,
        model_name=model_name,
        language=language,
        theme=theme
    )
    
    tex_code, ai_message = generator.generate_revised_tex(user_feedback)
    
    if not tex_code:
        return "", "", ai_message
        
    output_file = generator.save_revised_tex(tex_code)
    
    return tex_code, output_file, ai_message 