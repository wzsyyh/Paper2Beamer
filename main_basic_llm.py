#!/usr/bin/env python3
"""
Basic LLM版本的论文到Beamer转换工具
最简化的baseline：纯文本提取 + 直接LLM生成TEX
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# 加载补丁
from patch_openai import patch_openai_client, patch_langchain_openai

# 加载环境变量
from dotenv import load_dotenv
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("env.local"):
    load_dotenv("env.local")

# 应用补丁
patch_openai_client()
patch_langchain_openai()

# 导入模块
from modules.simple_text_extractor import extract_simple_text
from modules.basic_tex_generator import generate_basic_tex
from modules.tex_validator import validate_tex

def setup_logging(verbose=False):
    """设置日志级别和格式"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Basic LLM版本：将学术论文PDF转换为Beamer演示文稿'
    )
    
    # 必需参数
    parser.add_argument(
        'pdf_path', 
        help='输入PDF文件路径'
    )
    
    # 可选参数
    parser.add_argument(
        '--output-dir', '-o',
        default='output',
        help='输出目录'
    )
    parser.add_argument(
        '--language', '-l',
        choices=['zh', 'en'],
        default='zh',
        help='输出语言，zh为中文，en为英文'
    )
    parser.add_argument(
        '--model', '-m',
        default='gpt-4o',
        help='使用的语言模型'
    )
    parser.add_argument(
        '--max-retries', '-r',
        type=int,
        default=5,
        help='编译失败时的最大重试次数'
    )
    parser.add_argument(
        '--skip-tex', '-s',
        action='store_true',
        help='跳过TEX生成和编译步骤'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细日志'
    )
    parser.add_argument(
        '--theme',
        default='Madrid',
        help='Beamer主题，如Madrid, Berlin, Singapore等'
    )
    
    return parser.parse_args()

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志
    logger = setup_logging(args.verbose)
    
    # 检查API密钥
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("未设置OPENAI_API_KEY环境变量")
        return 1
    
    # 创建输出目录
    output_dir = args.output_dir
    
    # 使用唯一的会话ID来区分不同的运行
    session_id = str(int(time.time()))
    
    # 创建各阶段输出目录
    raw_dir = os.path.join(output_dir, "raw", session_id)
    tex_dir = os.path.join(output_dir, "tex", session_id)
    
    for dir_path in [raw_dir, tex_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    # 检查输入文件
    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF文件不存在: {args.pdf_path}")
        return 1
        
    # 步骤1: 提取PDF纯文本
    logger.info("步骤1: 提取PDF纯文本...")
    try:
        text_content, saved_text_path = extract_simple_text(args.pdf_path, raw_dir)
        if not text_content:
            logger.error("PDF文本提取失败")
            return 1
            
        logger.info(f"PDF文本已提取，长度: {len(text_content)} 字符")
        if saved_text_path:
            logger.info(f"文本已保存到: {saved_text_path}")
    except Exception as e:
        logger.error(f"PDF文本提取失败: {str(e)}")
        return 1
            
    # 如果指定跳过TEX生成和编译，则在此结束
    if args.skip_tex:
        logger.info("已跳过TEX生成和编译步骤")
        return 0
    
    # 步骤2: 生成TEX代码
    logger.info("步骤2: 生成TEX代码...")
    try:
        tex_output_path = os.path.join(tex_dir, "output.tex")
        tex_code = generate_basic_tex(
            text_content=text_content,
            output_path=tex_output_path,
            model_name=args.model,
            language=args.language,
            theme=args.theme
        )
        
        if not tex_code:
            logger.error("TEX代码生成失败")
            return 1
            
        logger.info(f"TEX代码已生成: {tex_output_path}")
    except Exception as e:
        logger.error(f"TEX代码生成失败: {str(e)}")
        return 1
    
    # 步骤3: 验证和编译TEX文件
    logger.info("步骤3: 验证和编译TEX文件...")
    try:
        # 注意：Basic LLM版本没有图片，所以不需要传递session_id
        success, message, pdf_path = validate_tex(
            tex_file=tex_output_path,
            output_dir=tex_dir,
            language=args.language,
            session_id=session_id  # 传递session_id以保持一致性
        )
        
        if success:
            logger.info(f"TEX编译成功: {message}")
            logger.info(f"生成的PDF文件: {pdf_path}")
            return 0
        else:
            logger.error(f"TEX编译失败: {message}")
            return 1
    except Exception as e:
        logger.error(f"TEX编译过程失败: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
