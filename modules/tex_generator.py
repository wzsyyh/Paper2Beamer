"""
TEX 生成器模块：将演示计划转换为 Beamer TEX 代码
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

# 导入提示词
from prompts import TEX_GENERATION_PROMPT

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

class TexGenerator:
    def __init__(
        self, 
        presentation_plan_path: str, 
        output_dir: str = "output",
        model_name: str = "gpt-4o",
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        language: str = "zh",
        theme: str = "Madrid"  # 添加主题参数
    ):
        """
        初始化TEX生成器
        
        Args:
            presentation_plan_path: 演示计划JSON文件路径
            output_dir: 输出目录
            model_name: 要使用的语言模型名称
            temperature: 模型生成的随机性程度
            api_key: OpenAI API密钥
            language: 输出语言，zh为中文，en为英文
            theme: Beamer主题，如Madrid, Berlin, Singapore等
        """
        self.presentation_plan_path = presentation_plan_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.language = language
        self.theme = theme  # 保存主题
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 加载演示计划
        self.presentation_plan = self._load_presentation_plan()
        
        # 初始化模型
        self._init_model()
    
    def _load_presentation_plan(self) -> Dict[str, Any]:
        """加载演示计划"""
        try:
            with open(self.presentation_plan_path, 'r', encoding='utf-8') as f:
                plan = json.load(f)
            return plan
        except Exception as e:
            self.logger.error(f"加载演示计划失败: {str(e)}")
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
        生成TEX代码
        
        Returns:
            str: 生成的TEX代码
        """
        if not self.presentation_plan:
            self.logger.error("没有演示计划可处理")
            return ""
            
        if not self.llm:
            self.logger.error("未初始化语言模型，无法生成TEX代码")
            return ""
        
        # 获取论文信息和幻灯片计划
        paper_info = self.presentation_plan.get("paper_info", {})
        slides_plan = self.presentation_plan.get("slides_plan", [])
        
        # 预处理幻灯片中的图片引用
        self._preprocess_slide_figures(slides_plan)
        
        # 强制使用英文生成，因为JSON内容已经是英文的
        language_prompt = "Please generate in English"
        
        # 构建提示
        prompt = ChatPromptTemplate.from_template(TEX_GENERATION_PROMPT)
        
        try:
            # 调用LLM生成TEX代码
            response = self.llm.invoke(prompt.format(
                language_prompt=language_prompt,
                plan=json.dumps(self.presentation_plan, ensure_ascii=False, indent=2),
                theme=self.theme
            ))
            
            # 提取回复内容
            tex_code = response.content
            
            # 清理代码（移除不必要的标记）
            tex_code = self._clean_tex_code(tex_code)
            
            return tex_code
        except Exception as e:
            self.logger.error(f"生成TEX代码时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return ""
    
    def _preprocess_slide_figures(self, slides_plan):
        """
        预处理幻灯片中的图片引用，添加描述长度信息
        
        Args:
            slides_plan: 幻灯片计划列表
        """
        # 获取session_id
        session_id = os.path.basename(os.path.dirname(self.presentation_plan_path))
        
        for slide in slides_plan:
            if slide.get("includes_figure") and slide.get("figure_reference"):
                fig_ref = slide.get("figure_reference")
                if fig_ref:
                    # 确保图片引用中有实际的文件名
                    if "path" in fig_ref and not "filename" in fig_ref:
                        # 从路径中提取文件名
                        filename = os.path.basename(fig_ref["path"])
                        fig_ref["filename"] = filename
                    
                    # 检查文件是否存在
                    if "filename" in fig_ref:
                        images_dir = os.path.join("output", "images", session_id)
                        img_path = os.path.join(images_dir, fig_ref["filename"])
                        if not os.path.exists(img_path):
                            self.logger.warning(f"警告：图片文件不存在: {img_path}")
                            
                    # 如果没有指定caption_length，根据描述长度自动判断
                    if "description" in fig_ref and "caption_length" not in fig_ref:
                        description = fig_ref.get("description", "")
                        if len(description) < 50:
                            fig_ref["caption_length"] = "short"
                        elif len(description) < 100:
                            fig_ref["caption_length"] = "medium"
                        else:
                            fig_ref["caption_length"] = "long"
    
    def _clean_tex_code(self, tex_code: str) -> str:
        """清理TEX代码，移除不必要的标记"""
        # 移除可能的代码块标记
        if "```" in tex_code:
            pattern = r"```(?:latex|tex)?(.*?)```"
            matches = re.findall(pattern, tex_code, re.DOTALL)
            if matches:
                tex_code = "\n".join(matches)
            else:
                # 如果没有匹配到，尝试清理开头和结尾的```
                tex_code = re.sub(r"^```(?:latex|tex)?\n", "", tex_code)
                tex_code = re.sub(r"\n```$", "", tex_code)
        
        return tex_code.strip()
    
    def save_tex(self, tex_code: str, output_file: Optional[str] = None) -> str:
        """
        保存TEX代码到文件
        
        Args:
            tex_code: TEX代码
            output_file: 输出文件路径，如果为None则使用默认路径
            
        Returns:
            str: 保存的文件路径
        """
        if not tex_code:
            self.logger.error("没有TEX代码可保存")
            return ""
        
        if output_file is None:
            output_file = os.path.join(self.output_dir, "output.tex")
        
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(tex_code)
            
            self.logger.info(f"TEX代码已保存至: {output_file}")
            return output_file
        except Exception as e:
            self.logger.error(f"保存TEX代码时出错: {str(e)}")
            return ""

# 便捷函数
def generate_tex(presentation_plan_path, output_dir="output", model_name="gpt-4o", api_key=None, language="zh", theme="Madrid"):
    """
    从演示计划生成TEX代码（便捷函数）
    
    Args:
        presentation_plan_path: 演示计划JSON文件路径
        output_dir: 输出目录
        model_name: 要使用的语言模型名称
        api_key: OpenAI API密钥
        language: 输出语言，zh为中文，en为英文
        theme: Beamer主题，如Madrid, Berlin, Singapore等
        
    Returns:
        tuple: (TEX代码, 保存的文件路径)
    """
    generator = TexGenerator(
        presentation_plan_path=presentation_plan_path,
        output_dir=output_dir,
        model_name=model_name,
        api_key=api_key,
        language=language,
        theme=theme
    )
    
    tex_code = generator.generate_tex()
    
    if tex_code:
        output_file = generator.save_tex(tex_code)
        return tex_code, output_file
    
    return "", ""
