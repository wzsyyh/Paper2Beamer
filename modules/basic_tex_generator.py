"""
基础TEX生成器模块：直接从纯文本生成LaTeX Beamer代码
用于Basic LLM baseline，无结构化数据处理，无图片处理
"""

import os
import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

class BasicTexGenerator:
    def __init__(self, model_name: str = "gpt-4o", language: str = "en", theme: str = "Madrid"):
        """
        初始化基础TEX生成器
        
        Args:
            model_name: 使用的语言模型名称
            language: 输出语言，zh为中文，en为英文
            theme: Beamer主题
        """
        self.model_name = model_name
        self.language = language
        self.theme = theme
        self.logger = logging.getLogger(__name__)
        
        # 初始化语言模型
        try:
            self.llm = ChatOpenAI(model=model_name, temperature=0.1)
            self.logger.info(f"已初始化语言模型: {model_name}")
        except Exception as e:
            self.logger.error(f"初始化语言模型失败: {str(e)}")
            raise
    
    def generate_tex(self, text_content: str) -> Optional[str]:
        """
        从纯文本内容生成LaTeX Beamer代码
        
        Args:
            text_content: 从PDF提取的纯文本内容
            
        Returns:
            str: 生成的LaTeX Beamer代码
        """
        if not text_content or not text_content.strip():
            self.logger.error("输入的文本内容为空")
            return None
        
        try:
            # 限制文本长度以避免超出token限制
            max_chars = 50000  # 约12000 tokens
            if len(text_content) > max_chars:
                text_content = text_content[:max_chars]
                self.logger.warning(f"文本内容过长，已截断至 {max_chars} 字符")
            
            self.logger.info(f"开始生成TEX代码，文本长度: {len(text_content)} 字符")
            
            # 获取提示词
            from prompts import BASIC_TEX_GENERATION_PROMPT
            
            # 设置语言提示
            language_prompt = "Please respond in English" if self.language == "en" else "请用中文回答"
            
            # 创建提示词模板
            prompt = ChatPromptTemplate.from_template(BASIC_TEX_GENERATION_PROMPT)
            
            # 调用LLM生成TEX代码
            chain = prompt | self.llm
            response = chain.invoke({
                "text_content": text_content,
                "language_prompt": language_prompt,
                "theme": self.theme
            })
            
            # 提取生成的TEX代码
            tex_code = response.content if hasattr(response, 'content') else str(response)
            
            # 清理TEX代码
            tex_code = self._clean_tex_code(tex_code)
            
            if not tex_code:
                self.logger.error("生成的TEX代码为空")
                return None
            
            self.logger.info(f"成功生成TEX代码，长度: {len(tex_code)} 字符")
            return tex_code
            
        except Exception as e:
            self.logger.error(f"生成TEX代码失败: {str(e)}")
            return None
    
    def _clean_tex_code(self, tex_code: str) -> str:
        """
        清理生成的TEX代码
        
        Args:
            tex_code: 原始TEX代码
            
        Returns:
            str: 清理后的TEX代码
        """
        if not tex_code:
            return ""
        
        # 移除markdown标记
        if "```" in tex_code:
            import re
            pattern = r"```(?:latex|tex)?(.*?)```"
            matches = re.findall(pattern, tex_code, re.DOTALL)
            if matches:
                tex_code = "\n".join(matches)
            else:
                # 如果没有匹配到，尝试清理开头和结尾的```
                tex_code = re.sub(r"^```(?:latex|tex)?\n", "", tex_code)
                tex_code = re.sub(r"\n```$", "", tex_code)
        
        # 去除首尾空白
        tex_code = tex_code.strip()
        
        # 确保代码以\documentclass开始
        if not tex_code.startswith("\\documentclass"):
            # 查找\documentclass的位置
            doc_start = tex_code.find("\\documentclass")
            if doc_start > 0:
                tex_code = tex_code[doc_start:]
        
        # 确保代码以\end{document}结束
        if not tex_code.rstrip().endswith("\\end{document}"):
            if "\\end{document}" in tex_code:
                # 截取到最后一个\end{document}
                end_pos = tex_code.rfind("\\end{document}")
                tex_code = tex_code[:end_pos + len("\\end{document}")]
        
        return tex_code
    
    def save_tex(self, tex_code: str, output_path: str) -> bool:
        """
        保存生成的TEX代码到文件
        
        Args:
            tex_code: TEX代码
            output_path: 输出文件路径
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存TEX代码
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(tex_code)
            
            self.logger.info(f"TEX代码已保存到: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存TEX代码失败: {str(e)}")
            return False


def generate_basic_tex(text_content: str, output_path: str = None, 
                      model_name: str = "gpt-4o", language: str = "en", 
                      theme: str = "Madrid") -> Optional[str]:
    """
    便捷函数：从纯文本生成TEX代码
    
    Args:
        text_content: 纯文本内容
        output_path: 输出文件路径（可选）
        model_name: 语言模型名称
        language: 输出语言
        theme: Beamer主题
        
    Returns:
        str: 生成的TEX代码
    """
    generator = BasicTexGenerator(model_name=model_name, language=language, theme=theme)
    
    # 生成TEX代码
    tex_code = generator.generate_tex(text_content)
    if not tex_code:
        return None
    
    # 保存TEX代码（如果指定了输出路径）
    if output_path:
        if not generator.save_tex(tex_code, output_path):
            return None
    
    return tex_code
