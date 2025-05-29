#!/usr/bin/env python3
"""
测试原始内容提取模块
"""
import os
import sys
import json
import logging
import argparse

# 将项目根目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.raw_extractor import RawExtractor, extract_raw_content

def setup_logging(verbose=False):
    """设置日志级别和格式"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def test_raw_extractor(pdf_path, output_dir=None, verbose=False):
    """测试原始内容提取器"""
    # 设置日志
    setup_logging(verbose)
    
    # 默认输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output', 'raw')
    
    logging.info(f"开始测试原始内容提取: {pdf_path}")
    logging.info(f"输出目录: {output_dir}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 使用提取器
    extractor = RawExtractor(pdf_path, output_dir)
    content = extractor.extract_content()
    
    if content:
        # 保存提取的内容到JSON文件
        output_file = extractor.save_content(content)
        
        # 打印提取的内容摘要
        logging.info(f"提取完成:")
        logging.info(f"  PDF路径: {content['pdf_path']}")
        logging.info(f"  文档信息: {json.dumps(content['document_info'], ensure_ascii=False)[:200]}...")
        logging.info(f"  提取的页面数: {len(content['pages_content'])}")
        logging.info(f"  提取的图片数: {len(content['images'])}")
        logging.info(f"  目录项数: {len(content['toc'])}")
        
        # 打印第一页的部分内容
        if content['pages_content']:
            first_page = content['pages_content'][0]
            logging.info(f"  第一页内容预览: {first_page['text']['plain'][:200]}...")
            if 'blocks' in first_page['text']['dict']:
                logging.info(f"  第一页块数: {len(first_page['text']['dict']['blocks'])}")
        
        # 打印目录
        if content['toc']:
            logging.info("  目录结构:")
            for i, item in enumerate(content['toc'][:5]):  # 只显示前5项
                logging.info(f"    {item['level']} - {item['title']} (页面 {item['page']})")
            if len(content['toc']) > 5:
                logging.info(f"    ... 共{len(content['toc'])}项")
        
        logging.info(f"原始内容已保存至: {output_file}")
        return True
    else:
        logging.error("提取失败，未返回内容")
        return False

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试原始内容提取模块')
    parser.add_argument('pdf_file', help='PDF文件路径')
    parser.add_argument('--output-dir', help='输出目录')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.pdf_file):
        logging.error(f"文件不存在: {args.pdf_file}")
        sys.exit(1)
    
    # 测试原始内容提取
    success = test_raw_extractor(
        args.pdf_file,
        args.output_dir,
        args.verbose
    )
    
    sys.exit(0 if success else 1) 