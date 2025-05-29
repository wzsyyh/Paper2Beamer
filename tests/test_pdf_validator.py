#!/usr/bin/env python3
"""
测试PDF提取内容验证工具
"""
import os
import sys
import logging
import argparse

# 将项目根目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.pdf_validator import PdfValidator, validate_pdf_extraction

def setup_logging(verbose=False):
    """设置日志级别和格式"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def test_pdf_validator(pdf_path, raw_content_path, output_dir="output/validation", verbose=False):
    """测试PDF提取内容验证工具"""
    # 设置日志
    setup_logging(verbose)
    
    logging.info(f"开始验证PDF提取内容: {pdf_path}")
    logging.info(f"原始内容JSON: {raw_content_path}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 实例化验证器
    validator = PdfValidator(pdf_path, raw_content_path, output_dir)
    
    # 验证文本提取（仅前两页）
    logging.info("正在验证文本提取...")
    text_result = validator.validate_text_extraction(page_nums=[0, 1])
    if text_result:
        logging.info(f"文本验证结果已保存至: {text_result}")
    
    # 验证图片提取
    logging.info("正在验证图片提取...")
    image_result = validator.validate_image_extraction()
    if image_result:
        logging.info(f"图片验证结果已保存至: {image_result}")
    
    # 验证结构
    logging.info("正在验证提取内容结构...")
    structure_result = validator.validate_structure()
    if structure_result:
        logging.info(f"结构验证结果已保存至: {structure_result}")
        
        # 显示结构验证结果
        try:
            with open(structure_result, 'r', encoding='utf-8') as f:
                content = f.read()
                logging.info("\n" + content)
        except Exception as e:
            logging.error(f"读取结构验证结果失败: {str(e)}")
    
    logging.info("验证完成")
    return True

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='验证PDF提取内容的准确性')
    parser.add_argument('pdf_file', help='原始PDF文件路径')
    parser.add_argument('raw_content_file', help='提取的原始内容JSON文件路径')
    parser.add_argument('--output-dir', default='output/validation', help='输出目录')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.pdf_file):
        print(f"错误：PDF文件不存在: {args.pdf_file}")
        sys.exit(1)
        
    if not os.path.exists(args.raw_content_file):
        print(f"错误：原始内容JSON文件不存在: {args.raw_content_file}")
        sys.exit(1)
    
    # 测试PDF验证工具
    success = test_pdf_validator(
        args.pdf_file, 
        args.raw_content_file,
        args.output_dir,
        args.verbose
    )
    
    sys.exit(0 if success else 1) 