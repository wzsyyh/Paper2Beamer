"""
PDF解析模块：负责解析PDF文件并提取基本信息
该模块现在调用轻量级提取器模块的功能，提供高效的内容提取
并使用LLM对内容进行演讲导向的增强处理
"""
import os
import json
import logging
import re
from typing import Dict, Any, Optional
from .lightweight_extractor import extract_lightweight_content

# 导入LLM相关包
try:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# 导入增强提示词
from prompts import PRESENTATION_CONTENT_ENHANCEMENT_PROMPT

def enhance_content_with_llm(lightweight_content: Dict[str, Any], model_name: str = "gpt-4o", api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    使用LLM增强内容，从演讲角度重新组织和结构化内容
    
    Args:
        lightweight_content: 轻量级提取的基础内容
        model_name: 要使用的语言模型名称
        api_key: OpenAI API密钥
        
    Returns:
        Dict: 增强后的内容
    """
    logger = logging.getLogger(__name__)
    
    if not OPENAI_AVAILABLE:
        logger.warning("无法导入OpenAI相关包，跳过LLM增强处理")
        return lightweight_content
    
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("未提供OpenAI API密钥，跳过LLM增强处理")
            return lightweight_content
    
    try:
        # 初始化LLM
        llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.2,
            openai_api_key=api_key
        )
        
        # 获取完整文本
        full_text = lightweight_content.get("full_text", "")
        if not full_text:
            logger.warning("没有找到full_text，跳过LLM增强处理")
            return lightweight_content
        
        logger.info("开始使用LLM增强内容...")
        
        # 构建提示
        prompt = ChatPromptTemplate.from_template(PRESENTATION_CONTENT_ENHANCEMENT_PROMPT)
        
        # 调用LLM
        chain = prompt | llm
        response = chain.invoke({"full_text": full_text})
        
        # 解析结果
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # 提取JSON部分
        json_match = re.search(r'```(?:json)?(.*?)```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = response_text.strip()
        
        # 尝试解析JSON
        try:
            enhanced_sections = json.loads(json_str)
            
            # 将增强内容合并到原始内容中
            enhanced_content = lightweight_content.copy()
            enhanced_content["enhanced_content"] = enhanced_sections
            
            logger.info("LLM内容增强完成")
            return enhanced_content
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM返回的JSON时出错: {str(e)}")
            logger.error(f"原始响应: {response_text}")
            return lightweight_content
            
    except Exception as e:
        logger.error(f"LLM增强处理时出错: {str(e)}")
        return lightweight_content

def extract_pdf_content(pdf_path, output_dir="output", cleanup_temp=False, enable_llm_enhancement=True, model_name="gpt-4o", api_key=None):
    """
    提取PDF内容（包括文本、图像、元数据等）并可选地进行LLM增强
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
        cleanup_temp: 是否清理临时文件
        enable_llm_enhancement: 是否启用LLM增强处理
        model_name: 要使用的语言模型名称
        api_key: OpenAI API密钥
        
    Returns:
        tuple: (提取的内容, 内容保存的文件路径)
    """
    logging.info(f"开始从PDF中提取内容: {pdf_path}")
    
    # 调用轻量级提取器模块的功能
    lightweight_content, lightweight_content_path = extract_lightweight_content(pdf_path, output_dir, cleanup_temp)
    
    if not lightweight_content:
        logging.error("PDF内容提取失败")
        return None, None
    
    # 如果启用LLM增强，则进行增强处理
    if enable_llm_enhancement:
        logging.info("开始LLM增强处理...")
        enhanced_content = enhance_content_with_llm(lightweight_content, model_name, api_key)
        
        # 保存增强后的内容
        enhanced_content_path = lightweight_content_path.replace('.json', '_enhanced.json')
        try:
            with open(enhanced_content_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_content, f, ensure_ascii=False, indent=2)
            logging.info(f"增强后的内容已保存至: {enhanced_content_path}")
            return enhanced_content, enhanced_content_path
        except Exception as e:
            logging.error(f"保存增强内容时出错: {str(e)}")
            # 如果保存失败，返回原始内容
            return lightweight_content, lightweight_content_path
    else:
        logging.info(f"PDF内容已提取并保存至: {lightweight_content_path}")
        return lightweight_content, lightweight_content_path
