#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容覆盖度评估测试脚本
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入评估模块
from run_evaluation import main as evaluate_content_coverage

def run_test(sample_pdf: str, sample_tex: str, lang: str = "en") -> None:
    """
    运行测试样例
    
    Args:
        sample_pdf: 测试用PDF文件路径
        sample_tex: 测试用TEX文件路径
        lang: 语言代码
    """
    print(f"测试文件:\nPDF: {sample_pdf}\nTEX: {sample_tex}\n语言: {lang}")
    
    # 确认文件存在
    if not os.path.exists(sample_pdf):
        print(f"错误: 找不到PDF文件 '{sample_pdf}'")
        return
        
    if not os.path.exists(sample_tex):
        print(f"错误: 找不到TEX文件 '{sample_tex}'")
        return
    
    # 执行评估
    results = evaluate_content_coverage(sample_pdf, sample_tex, lang)
    
    # 输出结果
    print("\n内容覆盖度评估结果:")
    for metric, value in results.items():
        if isinstance(value, float):
            print(f"  {metric}: {value:.4f}")
        else:
            print(f"  {metric}: {value}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试内容覆盖度评估模块")
    parser.add_argument("--pdf", required=True, help="测试用PDF文件路径")
    parser.add_argument("--tex", required=True, help="测试用TEX文件路径")
    parser.add_argument("--lang", default="en", help="语言代码，默认为英语(en)")
    
    args = parser.parse_args()
    
    run_test(args.pdf, args.tex, args.lang)
