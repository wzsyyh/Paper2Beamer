#!/usr/bin/env python3
"""
测试PDF解析器模块
"""
import os
import sys
import json
import logging

# 将项目根目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.pdf_parser import PDFParser, extract_pdf_content

def setup_logging():
    """设置日志级别和格式"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def test_pdf_parser(pdf_path):
    """测试PDF解析器"""
    logging.info(f"开始测试PDF解析: {pdf_path}")
    
    # 创建输出目录
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # 方法1: 使用PDFParser类直接解析
    parser = PDFParser(pdf_path, output_dir)
    content = parser.extract_content()
    
    # 方法2: 使用便捷函数解析
    # content = extract_pdf_content(pdf_path, output_dir)
    
    if content:
        # 打印提取的内容摘要
        logging.info(f"提取完成. 标题: {content['title']}")
        logging.info(f"作者: {content['authors']}")
        logging.info(f"摘要长度: {len(content['abstract'])} 字符")
        logging.info(f"提取的章节数: {len(content['sections'])}")
        logging.info(f"提取的图片数: {len(content['images'])}")
        
        # 打印章节标题
        logging.info("章节:")
        for i, section in enumerate(content['sections']):
            logging.info(f"  {i+1}. {section['title']} (页面: {section['page']}, 内容长度: {len(section['content'])}字符)")
        
        # 保存解析结果到JSON文件
        json_path = os.path.join(output_dir, 'parsed_content.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        logging.info(f"解析结果已保存至: {json_path}")
        return True
    else:
        logging.error("解析失败，未返回内容")
        return False

if __name__ == "__main__":
    # 设置日志
    setup_logging()
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python test_pdf_parser.py <pdf文件路径>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        logging.error(f"文件不存在: {pdf_path}")
        sys.exit(1)
    
    # 测试PDF解析
    success = test_pdf_parser(pdf_path)
    sys.exit(0 if success else 1) 