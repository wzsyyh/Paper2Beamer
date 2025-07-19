"""
直接TEX生成器模块：将原始文本内容直接转换为Beamer TEX代码
"""

import os
import json
import logging
import re
from typing import Optional

# 导入依赖
from dotenv import load_dotenv
from patch_openai import patch_langchain_openai, patch_openai_client

# 导入提示词
from prompts import DIRECT_TEX_GENERATION_PROMPT

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
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class DirectTexGenerator:
    def __init__(
        self, 
        raw_content_path: str, 
        output_dir: str = "output",
        model_name: str = "gpt-4o",
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        language: str = "zh",
        theme: str = "Madrid"
    ):
        """
        初始化直接TEX生成器
        
        Args:
            raw_content_path: 原始文本内容文件路径
            output_dir: 输出目录
            model_name: 要使用的语言模型名称
            temperature: 模型生成的随机性程度
            api_key: OpenAI API密钥
            language: 输出语言，zh为中文，en为英文
            theme: Beamer主题
        """
        self.raw_content_path = raw_content_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.language = language
        self.theme = theme
        
        self.logger = logging.getLogger(__name__)
        self.raw_content = self._load_raw_content()
        self._init_model()
    
    def _load_raw_content(self) -> dict:
        """加载完整的原始JSON内容"""
        try:
            with open(self.raw_content_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载原始JSON内容失败: {str(e)}")
            return {}
    
    def _init_model(self):
        """初始化语言模型"""
        if not OPENAI_AVAILABLE:
            self.logger.warning("无法导入OpenAI相关包，将无法使用大语言模型生成TEX代码")
            self.llm = None
            return
            
        if not self.api_key:
            self.logger.warning("未提供OpenAI API密钥，将无法使用大语言模型生成TEX代码")
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
    
    def generate_tex(self) -> str:
        """
        直从原始文本生成TEX代码
        
        Returns:
            str: 生成的TEX代码
        """
        if not self.raw_content:
            self.logger.error("没有原始文本内容可处理")
            return ""
            
        if not self.llm:
            self.logger.error("未初始化语言模型，无法生成TEX代码")
            return ""
        
        language_prompt = "请用中文生成" if self.language == "zh" else "Please generate in English"
        prompt = ChatPromptTemplate.from_template(DIRECT_TEX_GENERATION_PROMPT)
        
        try:
            # 限制JSON内容大小以避免超过API限制
            limited_content = self._limit_content_size(self.raw_content)
            
            # 添加调试信息
            self.logger.info(f"原始内容大小: {len(json.dumps(self.raw_content, ensure_ascii=False))} 字符")
            self.logger.info(f"限制后内容大小: {len(json.dumps(limited_content, ensure_ascii=False))} 字符")
            self.logger.info(f"内容包含的关键字段: {list(limited_content.keys())}")
            
            if 'full_text' in limited_content:
                text_preview = limited_content['full_text'][:200] + "..." if len(limited_content['full_text']) > 200 else limited_content['full_text']
                self.logger.info(f"文本内容预览: {text_preview}")
            
            if 'images' in limited_content:
                self.logger.info(f"图片数量: {len(limited_content['images'])}")
                for i, img in enumerate(limited_content['images'][:3]):  # 只显示前3个
                    self.logger.info(f"图片{i+1}: {img.get('filename', 'unknown')} - {img.get('caption', 'no caption')[:50]}...")
            
            response = self.llm.invoke(prompt.format(
                language_prompt=language_prompt,
                raw_json=json.dumps(limited_content, ensure_ascii=False, indent=2),
                theme=self.theme
            ))
            
            tex_code = response.content
            tex_code = self._clean_tex_code(tex_code)
            
            self.logger.info(f"生成的TEX代码长度: {len(tex_code)} 字符")
            if tex_code:
                # 检查是否包含真实内容
                if "[Title Placeholder]" in tex_code or "[Author Placeholder]" in tex_code:
                    self.logger.warning("生成的TEX代码包含占位符，可能没有正确使用原始内容")
                else:
                    self.logger.info("TEX代码看起来包含了真实内容")
            
            return tex_code
        except Exception as e:
            self.logger.error(f"直接生成TEX代码时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return ""
    
    def _clean_tex_code(self, tex_code: str) -> str:
        """清理TEX代码，移除不要的标记"""
        if "```" in tex_code:
            pattern = r"```(?:latex|tex)?(.*?)```"
            matches = re.findall(pattern, tex_code, re.DOTALL)
            if matches:
                tex_code = "\n".join(matches)
            else:
                tex_code = re.sub(r"^```(?:latex|tex)?\n", "", tex_code)
                tex_code = re.sub(r"\n```$", "", tex_code)
        
        return tex_code.strip()
    
    def save_tex(self, tex_code: str, output_file: Optional[str] = None) -> str:
        """
        保存TEX代码到文件
        
        Args:
            tex_code: TEX代码
            output_file: 输出文件路径
            
        Returns:
            str: 保存的文件路径
        """
        if not tex_code:
            self.logger.error("没有TEX代码可保存")
            return ""
        
        if output_file is None:
            output_file = os.path.join(self.output_dir, "output.tex")
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(tex_code)
            self.logger.info(f"TEX代码已保存至: {output_file}")
            return output_file
        except Exception as e:
            self.logger.error(f"保存TEX代码时出错: {str(e)}")
            return ""
    
    def _limit_content_size(self, content: dict, max_chars: int = 80000) -> dict:
        """
        限制内容大小以避免超过API限制，但保留更多关键信息
        
        Args:
            content: 原始内容字典
            max_chars: 最大字符数
            
        Returns:
            dict: 限制大小后的内容
        """
        content_str = json.dumps(content, ensure_ascii=False)
        if len(content_str) <= max_chars:
            return content
        
        # 如果内容过长，智能保留关键部分
        limited_content = {}
        
        # 保留所有基本信息
        for key in ['full_text', 'images', 'pdf_path', 'extraction_time', 'session_id']:
            if key in content:
                limited_content[key] = content[key]
        
        # 如果full_text太长，进行智能截断
        if 'full_text' in limited_content:
            full_text = limited_content['full_text']
            if len(full_text) > max_chars * 0.8:  # 为其他字段留出空间
                # 保留开头（标题、摘要）和结尾（结论）
                text_parts = full_text.split('\n\n')
                important_parts = []
                current_length = 0
                max_text_length = int(max_chars * 0.8)
                
                # 优先保留前面的重要部分（标题、摘要、介绍）
                for i, part in enumerate(text_parts):
                    if current_length + len(part) < max_text_length * 0.7:
                        important_parts.append(part)
                        current_length += len(part)
                    elif i < 10:  # 前10段优先保留
                        truncated_part = part[:max_text_length - current_length - 100] + "...[内容截断]"
                        important_parts.append(truncated_part)
                        break
                
                # 尝试保留结论部分
                conclusion_keywords = ['conclusion', 'conclusions', '结论', 'summary', '总结']
                for part in reversed(text_parts[-5:]):  # 检查最后5段
                    if any(keyword.lower() in part.lower() for keyword in conclusion_keywords):
                        if current_length + len(part) < max_text_length:
                            important_parts.append("...[中间内容省略]...")
                            important_parts.append(part)
                        break
                
                limited_content['full_text'] = '\n\n'.join(important_parts)
        
        return limited_content
    
    def fix_compilation_error(self, tex_code: str, error_message: str) -> str:
        """
        修复编译错误
        
        Args:
            tex_code: 当前的TEX代码
            error_message: 错误信息
            
        Returns:
            str: 修复后的TEX代码
        """
        if not self.llm:
            self.logger.error("未初始化语言模型，无法修复编译错误")
            return tex_code
        
        fix_prompt = f"""
你是一个LaTeX专家。以下TEX代码编译时出现了错误，请修复这些错误并返回完整的修复后的TEX代码。

错误信息：
{error_message}

当前TEX代码：
{tex_code}

请返回修复后的完整TEX代码，不要包含任何解释文字，只返回代码：
"""
        
        try:
            response = self.llm.invoke(fix_prompt)
            fixed_code = response.content
            fixed_code = self._clean_tex_code(fixed_code)
            
            if fixed_code and fixed_code != tex_code:
                self.logger.info("已生成修复后的TEX代码")
                return fixed_code
            else:
                self.logger.warning("修复后的代码与原代码相同或为空")
                return tex_code
                
        except Exception as e:
            self.logger.error(f"修复编译错误时出错: {str(e)}")
            return tex_code
    
    def fix_validation_error(self, tex_code: str, validation_error: str) -> str:
        """
        修复验证错误
        
        Args:
            tex_code: 当前的TEX代码
            validation_error: 验证错误信息
            
        Returns:
            str: 修复后的TEX代码
        """
        if not self.llm:
            self.logger.error("未初始化语言模型，无法修复验证错误")
            return tex_code
        
        fix_prompt = f"""
你是一个LaTeX专家。以下TEX代码验证时出现了错误，请修复这些错误并返回完整的修复后的TEX代码。

验证错误信息：
{validation_error}

当前TEX代码：
{tex_code}

请返回修复后的完整TEX代码，不要包含任何解释文字，只返回代码：
"""
        
        try:
            response = self.llm.invoke(fix_prompt)
            fixed_code = response.content
            fixed_code = self._clean_tex_code(fixed_code)
            
            if fixed_code and fixed_code != tex_code:
                self.logger.info("已生成修复后的TEX代码")
                return fixed_code
            else:
                self.logger.warning("修复后的代码与原代码相同或为空")
                return tex_code
                
        except Exception as e:
            self.logger.error(f"修复验证错误时出错: {str(e)}")
            return tex_code
