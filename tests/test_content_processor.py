#!/usr/bin/env python3
"""
测试内容处理模块
"""
import os
import sys
import json
import logging
import argparse
from dotenv import load_dotenv

# 将项目根目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.content_processor import ContentProcessor, process_content

def setup_logging(verbose=False):
    """设置日志级别和格式"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def test_content_processor(raw_content_path, output_dir=None, verbose=False, model="gpt-4o"):
    """测试内容处理器"""
    # 设置日志
    setup_logging(verbose)
    
    # 加载环境变量
    load_dotenv()
    
    # 获取API密钥
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logging.error("未设置OPENAI_API_KEY环境变量，无法进行API结构化")
        return False
    
    # 默认输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'structured')
    
    logging.info(f"开始测试内容处理: {raw_content_path}")
    logging.info(f"输出目录: {output_dir}")
    logging.info(f"使用模型: {model}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 检查原始内容文件是否存在
    if not os.path.exists(raw_content_path):
        logging.error(f"原始内容文件不存在: {raw_content_path}")
        return False
    
    # 使用内容处理器
    logging.info("初始化内容处理器...")
    processor = ContentProcessor(
        raw_content_path=raw_content_path,
        output_dir=output_dir,
        model_name=model,
        api_key=api_key
    )
    
    # 处理内容
    logging.info("开始处理内容...")
    processed_content = processor.process_content()
    
    if processed_content:
        # 保存处理后的内容到JSON文件
        output_file = processor.save_processed_content(processed_content)
        
        # 打印处理结果摘要
        logging.info(f"处理完成:")
        
        # 论文信息
        paper_info = processed_content.get('paper_info', {})
        logging.info(f"  论文标题: {paper_info.get('title', '')}")
        logging.info(f"  作者: {', '.join(paper_info.get('authors', []))}")
        
        # 章节结构
        sections = processed_content.get('sections', [])
        logging.info(f"  章节数: {len(sections)}")
        if sections:
            logging.info("  主要章节:")
            for section in sections[:5]:  # 只显示前5个章节
                logging.info(f"    - {section.get('title', '')}")
            if len(sections) > 5:
                logging.info(f"    ... 共{len(sections)}个章节")
        
        # 图表信息
        figures = processed_content.get('figures', [])
        logging.info(f"  图表数: {len(figures)}")
        if figures:
            logging.info("  部分图表:")
            for figure in figures[:3]:  # 只显示前3个图表
                logging.info(f"    - {figure.get('title', '')} (页面 {figure.get('page', 0)})")
            if len(figures) > 3:
                logging.info(f"    ... 共{len(figures)}个图表")
        
        # 参考文献
        references = processed_content.get('references', [])
        logging.info(f"  参考文献数: {len(references)}")
        if references:
            logging.info("  部分参考文献:")
            for ref in references[:3]:  # 只显示前3个参考文献
                logging.info(f"    - {ref.get('title', '')} ({ref.get('year', '')})")
            if len(references) > 3:
                logging.info(f"    ... 共{len(references)}个参考文献")
        
        logging.info(f"结构化内容已保存至: {output_file}")
        return True
    else:
        logging.error("处理失败，未返回内容")
        return False

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试内容处理模块')
    parser.add_argument('raw_content_path', help='原始内容JSON文件路径')
    parser.add_argument('--output-dir', help='输出目录')
    parser.add_argument('--model', default='gpt-4o', help='使用的模型名称')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.raw_content_path):
        logging.error(f"文件不存在: {args.raw_content_path}")
        sys.exit(1)
    
    # 测试内容处理
    success = test_content_processor(
        args.raw_content_path,
        args.output_dir,
        args.verbose,
        args.model
    )
    
    sys.exit(0 if success else 1) 