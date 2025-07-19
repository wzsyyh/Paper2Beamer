"""
PDF解析模块：负责解析PDF文件并提取基本信息
该模块现在调用轻量级提取器模块的功能，提供高效的内容提取
"""
import os
import logging
from .lightweight_extractor import extract_lightweight_content

def extract_pdf_content(pdf_path, output_dir="output", cleanup_temp=False):
    """
    提取PDF内容（包括文本、图像、元数据等）
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
        cleanup_temp: 是否清理临时文件
        
    Returns:
        tuple: (提取的内容, 内容保存的文件路径)
    """
    logging.info(f"开始从PDF中提取内容: {pdf_path}")
    
    # 调用轻量级提取器模块的功能
    lightweight_content, lightweight_content_path = extract_lightweight_content(pdf_path, output_dir, cleanup_temp)
    
    if not lightweight_content:
        logging.error("PDF内容提取失败")
        return None, None
    
    logging.info(f"PDF内容已提取并保存至: {lightweight_content_path}")
    
    return lightweight_content, lightweight_content_path
