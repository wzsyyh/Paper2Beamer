#!/usr/bin/env python3
"""
论文到Beamer的转换工具主程序 (无Planner版本)
"""

import os
import sys
import json
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
import json
from modules.pdf_parser import extract_pdf_content
# from modules.presentation_planner import generate_presentation_plan # REMOVED
from modules.tex_workflow import run_direct_tex_workflow

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
        description='将学术论文PDF转换为Beamer演示文稿 (无Planner版本)'
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
    # plan_dir = os.path.join(output_dir, "plan", session_id) # REMOVED
    tex_dir = os.path.join(output_dir, "tex", session_id)
    img_dir = os.path.join(output_dir, "images", session_id)
    
    for dir_path in [raw_dir, tex_dir, img_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    # 检查输入文件
    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF文件不存在: {args.pdf_path}")
        return 1
        
    # 步骤1: 提取PDF内容
    logger.info("步骤1: 提取PDF内容...")
    try:
        pdf_content, raw_content_path = extract_pdf_content(args.pdf_path, raw_dir)
        if not pdf_content:
            logger.error("PDF内容提取失败")
            return 1
            
        logger.info(f"PDF内容已保存到: {raw_content_path}")
    except Exception as e:
        logger.error(f"PDF内容提取失败: {str(e)}")
        return 1
            
    # 如果指定跳过TEX生成和编译，则在此结束
    if args.skip_tex:
        logger.info("已跳过TEX生成和编译步骤")
        return 0
    
    # 步骤2: 直接从原始文本生成和编译TEX (无Planner)
    logger.info("步骤2: 直接生成和编译TEX (无Planner)...")
    try:
        success, message, pdf_path = run_direct_tex_workflow(
            raw_content_path=raw_content_path,
            output_dir=tex_dir,
            model_name=args.model,
            language=args.language,
            theme=args.theme,
            max_retries=args.max_retries
        )
        
        if success:
            logger.info(f"TEX生成和编译成功: {message}")
            logger.info(f"生成的PDF文件: {pdf_path}")
            
            # 输出文件路径信息，便于后续处理
            tex_files = list(Path(tex_dir).rglob("*.tex"))
            if tex_files:
                logger.info(f"生成的TEX文件: {tex_files[0]}")
            
            return 0
        else:
            logger.error(f"TEX生成和编译失败: {message}")
            return 1
    except Exception as e:
        logger.error(f"TEX工作流执行失败: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
