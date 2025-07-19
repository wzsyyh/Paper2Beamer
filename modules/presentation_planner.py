"""
演示计划生成模块：从轻量级内容规划演示文稿
该模块现在调用轻量级规划器模块的功能，提供高效的演示计划生成
"""
import os
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# 加载环境变量
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("env.local"):
    load_dotenv("env.local")

# 导入轻量级规划器
from .lightweight_planner import LightweightPlanner, generate_lightweight_presentation_plan

# 尝试导入OpenAI相关包
try:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    from langchain.schema import HumanMessage, AIMessage, SystemMessage
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class PresentationPlanner:
    """
    演示计划生成器 - 轻量级包装器
    
    这个类现在是LightweightPlanner的包装器，保持向后兼容性
    """
    def __init__(
        self, 
        raw_content_path: str, 
        output_dir: str = "output",
        model_name: str = "gpt-4o",
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        language: str = "zh"
    ):
        """
        初始化演示计划生成器
        
        Args:
            raw_content_path: 轻量级内容JSON文件路径
            output_dir: 输出目录
            model_name: 要使用的语言模型名称
            temperature: 模型生成的随机性程度
            api_key: OpenAI API密钥
            language: 输出语言，zh为中文，en为英文
        """
        # 创建轻量级规划器实例
        self.lightweight_planner = LightweightPlanner(
            lightweight_content_path=raw_content_path,
            output_dir=output_dir,
            model_name=model_name,
            temperature=temperature,
            api_key=api_key,
            language=language
        )
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 保持兼容性的属性
        self.raw_content_path = raw_content_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key
        self.language = language
        
        # 演示计划数据
        self.presentation_plan = {}
        self.paper_info = {}
        self.key_content = {}
        self.slides_plan = []
        self.conversation_history = []
    
    def generate_presentation_plan(self) -> Dict[str, Any]:
        """
        生成演示计划
        
        Returns:
            Dict: 演示计划
        """
        self.logger.info("使用轻量级规划器生成演示计划...")
        
        # 调用轻量级规划器
        self.presentation_plan = self.lightweight_planner.generate_presentation_plan()
        
        if self.presentation_plan:
            # 更新兼容性属性
            self.paper_info = self.presentation_plan.get("paper_info", {})
            self.key_content = self.presentation_plan.get("key_content", {})
            self.slides_plan = self.presentation_plan.get("slides_plan", [])
            
            self.logger.info("演示计划生成完成")
        else:
            self.logger.error("演示计划生成失败")
        
        return self.presentation_plan
    
    def save_presentation_plan(self, presentation_plan, output_file=None):
        """
        保存演示计划到JSON文件
        
        Args:
            presentation_plan: 演示计划
            output_file: 输出文件路径，如果为None则使用默认路径
            
        Returns:
            str: 保存的文件路径
        """
        return self.lightweight_planner.save_presentation_plan(presentation_plan, output_file)
    
    def interactive_refinement(self, initial_feedback=None) -> Dict[str, Any]:
        """
        与用户进行多轮交互，优化演示计划
        
        Args:
            initial_feedback: 用户的初始反馈
            
        Returns:
            Dict: 优化后的演示计划
        """
        result = self.lightweight_planner.interactive_refinement(initial_feedback)
        
        # 更新本地属性
        if result:
            self.presentation_plan = result
            self.paper_info = result.get("paper_info", {})
            self.key_content = result.get("key_content", {})
            self.slides_plan = result.get("slides_plan", [])
        
        return result
    
    def continue_conversation(self, user_message: str) -> Tuple[str, Dict[str, Any]]:
        """
        继续与用户的对话，更新演示计划
        
        Args:
            user_message: 用户的消息
            
        Returns:
            Tuple: (模型响应, 更新后的演示计划)
        """
        response, updated_plan = self.lightweight_planner.continue_conversation(user_message)
        
        # 更新本地属性
        if updated_plan:
            self.presentation_plan = updated_plan
            self.paper_info = updated_plan.get("paper_info", {})
            self.key_content = updated_plan.get("key_content", {})
            self.slides_plan = updated_plan.get("slides_plan", [])
        
        return response, updated_plan
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        获取对话历史
        
        Returns:
            List: 对话历史记录
        """
        return self.lightweight_planner.get_conversation_history()

def generate_presentation_plan(raw_content_path, output_dir="output", model_name="gpt-4o", api_key=None, language="zh", user_feedback=None):
    """
    从轻量级内容生成演示计划（便捷函数）
    
    Args:
        raw_content_path: 轻量级内容JSON文件路径
        output_dir: 输出目录
        model_name: 要使用的语言模型名称
        api_key: OpenAI API密钥
        language: 输出语言，zh为中文，en为英文
        user_feedback: 用户的初始反馈（可选）
        
    Returns:
        tuple: (演示计划, 保存的文件路径, 规划器实例)
    """
    # 直接调用轻量级规划器的便捷函数
    presentation_plan, plan_path, lightweight_planner = generate_lightweight_presentation_plan(
        lightweight_content_path=raw_content_path,
        output_dir=output_dir,
        model_name=model_name,
        api_key=api_key,
        language=language,
        user_feedback=user_feedback
    )
    
    # 创建包装器实例以保持兼容性
    if lightweight_planner:
        wrapper = PresentationPlanner(
            raw_content_path=raw_content_path,
            output_dir=output_dir,
            model_name=model_name,
            api_key=api_key,
            language=language
        )
        wrapper.lightweight_planner = lightweight_planner
        wrapper.presentation_plan = presentation_plan
        if presentation_plan:
            wrapper.paper_info = presentation_plan.get("paper_info", {})
            wrapper.key_content = presentation_plan.get("key_content", {})
            wrapper.slides_plan = presentation_plan.get("slides_plan", [])
        
        return presentation_plan, plan_path, wrapper
    
    return presentation_plan, plan_path, None
