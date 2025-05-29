"""
PDF解析模块：负责解析PDF文件并提取基本信息
该模块现在只是简单地调用raw_extractor模块的功能，不做额外的结构化解析
"""
import os
import logging
from .raw_extractor import extract_raw_content

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
    
    # 直接调用raw_extractor模块的功能
    raw_content, raw_content_path = extract_raw_content(pdf_path, output_dir, cleanup_temp)
    
    if not raw_content:
        logging.error("PDF内容提取失败")
        return None, None
    
    logging.info(f"PDF内容已提取并保存至: {raw_content_path}")
    
    return raw_content, raw_content_path 