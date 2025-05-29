#!/usr/bin/env python3
"""
测试 TEX 工作流
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# 将项目根目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入工作流模块
from patch_openai import patch_openai_client, patch_langchain_openai
from modules.tex_workflow import TexWorkflow, run_tex_workflow

def setup_logging(verbose=False):
    """设置日志级别和格式"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def test_tex_workflow(
    presentation_plan_path, 
    output_dir=None, 
    verbose=False, 
    model="gpt-4o", 
    language="zh",
    max_retries=5
):
    """测试TEX工作流"""
    # 设置日志
    setup_logging(verbose)
    
    # 加载环境变量
    load_dotenv()
    
    # 应用补丁
    patch_openai_client()
    patch_langchain_openai()
    
    # 获取API密钥
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logging.error("未设置OPENAI_API_KEY环境变量")
        return False
    
    # 默认输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'tex')
    
    logging.info(f"开始测试TEX工作流: {presentation_plan_path}")
    logging.info(f"输出目录: {output_dir}")
    logging.info(f"使用模型: {model}")
    logging.info(f"输出语言: {language}")
    logging.info(f"最大重试次数: {max_retries}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 检查演示计划文件是否存在
    if not os.path.exists(presentation_plan_path):
        logging.error(f"演示计划文件不存在: {presentation_plan_path}")
        return False
    
    # 运行工作流
    success, message, pdf_path = run_tex_workflow(
        presentation_plan_path=presentation_plan_path,
        output_dir=output_dir,
        model_name=model,
        api_key=api_key,
        language=language,
        max_retries=max_retries
    )
    
    if success:
        logging.info(f"TEX工作流执行成功: {message}")
        logging.info(f"生成的PDF文件: {pdf_path}")
        return True
    else:
        logging.error(f"TEX工作流执行失败: {message}")
        return False

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试TEX工作流')
    parser.add_argument('presentation_plan_path', help='演示计划JSON文件路径')
    parser.add_argument('--output-dir', help='输出目录')
    parser.add_argument('--model', default='gpt-4o', help='使用的模型名称')
    parser.add_argument('--language', '-l', choices=['zh', 'en'], default='zh', help='输出语言')
    parser.add_argument('--max-retries', '-r', type=int, default=5, help='最大重试次数')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.presentation_plan_path):
        logging.error(f"文件不存在: {args.presentation_plan_path}")
        sys.exit(1)
    
    # 测试TEX工作流
    success = test_tex_workflow(
        args.presentation_plan_path,
        args.output_dir,
        args.verbose,
        args.model,
        args.language,
        args.max_retries
    )
    
    sys.exit(0 if success else 1) 