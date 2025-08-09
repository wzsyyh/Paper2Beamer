#!/usr/bin/env python3
"""
论文到Beamer的转换工具主程序
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
from modules.pdf_parser import extract_pdf_content
from modules.presentation_planner import generate_presentation_plan
from modules.tex_workflow import run_tex_workflow, run_revision_tex_workflow

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
        description='将学术论文PDF转换为Beamer演示文稿'
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
        '--interactive', '-i',
        action='store_true',
        help='启用交互式模式，允许用户通过多轮对话优化演示计划'
    )
    # 添加对修订模式的支持
    parser.add_argument(
        '--revise', '-R',
        action='store_true',
        help='启用修订模式，允许用户提供反馈修改已生成的演示文稿'
    )
    parser.add_argument(
        '--original-plan', 
        help='原始演示计划JSON文件路径（修订模式使用）'
    )
    parser.add_argument(
        '--previous-tex', 
        help='先前版本的TEX文件路径（修订模式使用）'
    )
    parser.add_argument(
        '--feedback', 
        help='用户反馈内容（修订模式使用）'
    )
    parser.add_argument(
        '--theme',
        default='Madrid',
        help='Beamer主题，如Madrid, Berlin, Singapore等'
    )
    parser.add_argument(
        '--disable-llm-enhancement',
        action='store_true',
        help='禁用LLM增强功能，仅使用基础PDF解析'
    )
    parser.add_argument(
        '--interactive-revise',
        action='store_true',
        help='启用交互式修订模式，在生成初版后对TEX代码进行迭代修改'
    )
    
    return parser.parse_args()

def interactive_dialog(planner, logger):
    """
    与用户进行交互式对话，优化演示计划
    
    Args:
        planner: 演示计划生成器实例
        logger: 日志记录器
        
    Returns:
        Dict: 优化后的演示计划
    """
    logger.info("进入交互式模式。您可以输入反馈来改进演示计划。输入'退出'或'exit'结束对话。")
    
    while True:
        user_input = input("\n请输入您的反馈: ")
        
        # 检查是否退出
        if user_input.lower() in ['退出', 'exit', 'quit']:
            logger.info("退出交互式模式")
            break
            
        # 处理用户输入
        logger.info("正在处理您的反馈...")
        response, updated_plan = planner.continue_conversation(user_input)
        
        # 打印模型响应
        print("\n==== 模型响应 ====")
        print(response)
        print("=================")
        
    return planner.presentation_plan

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
    session_id = f"{int(time.time())}"
    
    # 创建各阶段输出目录
    raw_dir = os.path.join(output_dir, "raw", session_id)
    plan_dir = os.path.join(output_dir, "plan", session_id)
    tex_dir = os.path.join(output_dir, "tex", session_id)
    img_dir = os.path.join(output_dir, "images", session_id)
    
    for dir_path in [raw_dir, plan_dir, tex_dir, img_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    # 检查是否为修订模式
    if args.revise:
        # 验证修订模式的必要参数
        if not args.original_plan or not args.previous_tex or not args.feedback:
            logger.error("修订模式需要提供--original-plan, --previous-tex和--feedback参数")
            return 1
            
        # 检查文件是否存在
        if not os.path.exists(args.original_plan):
            logger.error(f"原始演示计划文件不存在: {args.original_plan}")
            return 1
            
        if not os.path.exists(args.previous_tex):
            logger.error(f"先前版本的TEX文件不存在: {args.previous_tex}")
            return 1
            
        # 运行修订版TEX工作流
        logger.info("启动修订模式...")
        
        success, message, pdf_path = run_revision_tex_workflow(
            original_plan_path=args.original_plan,
            previous_tex_path=args.previous_tex,
            user_feedback=args.feedback,
            output_dir=tex_dir,
            model_name=args.model,
            language=args.language,
            theme=args.theme,
            max_retries=args.max_retries
        )
        
        if success:
            logger.info(f"修订版TEX生成和编译成功: {message}")
            logger.info(f"生成的PDF文件: {pdf_path}")
            return 0
        else:
            logger.error(f"修订版TEX生成和编译失败: {message}")
            return 1
    
    # 非修订模式的原有逻辑
    # 检查输入文件
    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF文件不存在: {args.pdf_path}")
        return 1
        
    # 步骤1: 提取PDF内容
    logger.info("步骤1: 提取PDF内容...")
    try:
        # 决定是否启用LLM增强
        enable_llm_enhancement = not args.disable_llm_enhancement and bool(api_key)
        
        if not enable_llm_enhancement:
            if args.disable_llm_enhancement:
                logger.info("用户禁用了LLM增强功能")
            else:
                logger.warning("未设置API密钥，将禁用LLM增强功能")
        
        pdf_content, raw_content_path = extract_pdf_content(
            pdf_path=args.pdf_path, 
            output_dir=raw_dir,
            enable_llm_enhancement=enable_llm_enhancement,
            model_name=args.model,
            api_key=api_key
        )
        if not pdf_content:
            logger.error("PDF内容提取失败")
            return 1
            
        logger.info(f"PDF内容已保存到: {raw_content_path}")
        
        # 检查是否成功使用了LLM增强
        if pdf_content.get("enhanced_content"):
            logger.info("✅ LLM增强内容提取成功")
            enhanced = pdf_content["enhanced_content"]
            logger.info(f"提取到 {len(enhanced.get('tables', []))} 个表格")
            logger.info(f"提取到 {len(enhanced.get('presentation_sections', {}))} 个演讲章节")
        else:
            logger.info("使用基础PDF解析（未启用LLM增强）")
    except Exception as e:
        logger.error(f"PDF内容提取失败: {str(e)}")
        return 1
            
    # 步骤2: 生成演示计划
    logger.info("步骤2: 生成演示计划...")
    try:
        presentation_plan, plan_path, planner = generate_presentation_plan(
            raw_content_path=raw_content_path,
            output_dir=plan_dir,
            model_name=args.model,
            language=args.language
        )
            
        if not presentation_plan:
            logger.error("演示计划生成失败")
            return 1
            
        logger.info(f"演示计划已保存到: {plan_path}")
            
        # 如果启用了交互式模式，进入对话
        if args.interactive and planner:
            logger.info("开始交互式优化...")
            presentation_plan = interactive_dialog(planner, logger)
            
            # 保存优化后的计划
            plan_path = planner.save_presentation_plan(presentation_plan)
            logger.info(f"优化后的演示计划已保存到: {plan_path}")
    except Exception as e:
        logger.error(f"演示计划生成失败: {str(e)}")
        return 1
        
    # 如果指定跳过TEX生成和编译，则在此结束
    if args.skip_tex:
        logger.info("已跳过TEX生成和编译步骤")
        return 0
    
    # 步骤3: 运行TEX工作流（生成TEX并编译）
    logger.info("步骤3: 生成和编译TEX...")
    try:
        success, message, pdf_path = run_tex_workflow(
            presentation_plan_path=plan_path,
            output_dir=tex_dir,
            model_name=args.model,
            language=args.language,
            theme=args.theme,
            max_retries=args.max_retries
        )
        
        if success:
            logger.info(f"TEX生成和编译成功: {message}")
            logger.info(f"生成的PDF文件: {pdf_path}")
            
            # 输出修订模式的用法提示
            previous_tex_path = os.path.join(tex_dir, 'output.tex')
            if not os.path.exists(previous_tex_path):
                # 尝试查找其他tex文件
                tex_files = [f for f in os.listdir(tex_dir) if f.endswith(".tex")]
                if tex_files:
                    previous_tex_path = os.path.join(tex_dir, tex_files[0])

            logger.info("\n如需修改演示文稿，可使用以下命令运行修订模式：")
            logger.info(f"python main.py --revise --original-plan='{plan_path}' --previous-tex='{previous_tex_path}' --feedback=\"您的修改建议\" --output-dir='{output_dir}' --theme={args.theme}")
            
            return 0
        else:
            logger.error(f"TEX生成和编译失败: {message}")
            return 1
    except Exception as e:
        logger.error(f"TEX工作流执行失败: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
