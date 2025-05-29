#!/usr/bin/env python3
"""
测试演示计划生成模块
"""
import os
import sys
import json
import logging
import argparse
from dotenv import load_dotenv

# 将项目根目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.presentation_planner import PresentationPlanner, generate_presentation_plan

def setup_logging(verbose=False):
    """设置日志级别和格式"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def test_presentation_planner(raw_content_path, output_dir=None, verbose=False, model="gpt-4o", language="zh"):
    """测试演示计划生成器"""
    # 设置日志
    setup_logging(verbose)
    
    # 加载环境变量
    load_dotenv()
    
    # 获取API密钥
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logging.error("未设置OPENAI_API_KEY环境变量，无法生成演示计划")
        return False
    
    # 默认输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'plan')
    
    logging.info(f"开始测试演示计划生成: {raw_content_path}")
    logging.info(f"输出目录: {output_dir}")
    logging.info(f"使用模型: {model}")
    logging.info(f"输出语言: {language}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 检查原始内容文件是否存在
    if not os.path.exists(raw_content_path):
        logging.error(f"原始内容文件不存在: {raw_content_path}")
        return False
    
    # 使用演示计划生成器
    logging.info("初始化演示计划生成器...")
    planner = PresentationPlanner(
        raw_content_path=raw_content_path,
        output_dir=output_dir,
        model_name=model,
        api_key=api_key,
        language=language
    )
    
    # 生成演示计划
    logging.info("开始生成演示计划...")
    presentation_plan = planner.generate_presentation_plan()
    
    if presentation_plan:
        # 保存演示计划到JSON文件
        output_file = planner.save_presentation_plan(presentation_plan)
        
        # 打印演示计划摘要
        logging.info(f"演示计划生成完成:")
        
        # 论文信息
        paper_info = presentation_plan.get('paper_info', {})
        logging.info(f"  论文标题: {paper_info.get('title', '')}")
        logging.info(f"  作者: {', '.join(paper_info.get('authors', []))}")
        
        # 关键内容
        key_content = presentation_plan.get('key_content', {})
        logging.info(f"  主要贡献点:")
        for contribution in key_content.get('main_contributions', [])[:3]:
            logging.info(f"    - {contribution}")
        
        # 幻灯片计划
        slides_plan = presentation_plan.get('slides_plan', [])
        logging.info(f"  幻灯片数量: {len(slides_plan)}")
        if slides_plan:
            logging.info("  幻灯片概览:")
            for slide in slides_plan[:5]:  # 只显示前5张幻灯片
                logging.info(f"    {slide.get('slide_number', 0)}. {slide.get('title', '')}")
            if len(slides_plan) > 5:
                logging.info(f"    ... 共{len(slides_plan)}张幻灯片")
        
        logging.info(f"演示计划已保存至: {output_file}")
        return True
    else:
        logging.error("生成演示计划失败")
        return False

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试演示计划生成模块')
    parser.add_argument('raw_content_path', help='原始内容JSON文件路径')
    parser.add_argument('--output-dir', help='输出目录')
    parser.add_argument('--model', default='gpt-4o', help='使用的模型名称')
    parser.add_argument('--language', '-l', choices=['zh', 'en'], default='zh', help='输出语言')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.raw_content_path):
        logging.error(f"文件不存在: {args.raw_content_path}")
        sys.exit(1)
    
    # 测试演示计划生成
    success = test_presentation_planner(
        args.raw_content_path,
        args.output_dir,
        args.verbose,
        args.model,
        args.language
    )
    
    sys.exit(0 if success else 1) 