#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容覆盖度(Content Coverage)评估模块
使用BERTScore和ROUGE-L评估生成的幻灯片对原论文摘要和结论的内容覆盖情况。
"""

import os
import re
import argparse
from typing import Dict, Any, Tuple
import logging
from pathlib import Path

import evaluate
import PyPDF2
import latex_utils
from text_processor import preprocess_text

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_abstract_conclusion_from_pdf(pdf_path: str) -> str:
    """
    从论文PDF中提取摘要和结论部分
    
    Args:
        pdf_path: PDF文件路径
        
    Returns:
        摘要和结论拼接的文本
    """
    logger.info(f"从PDF提取摘要和结论: {pdf_path}")
    text = ""
    
    try:
        # 打开PDF文件
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            
            # 提取所有文本
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            # 查找摘要部分
            abstract_pattern = re.compile(r'abstract\s*\n(.*?)(?:\n\s*\d+\.?\s*introduction|\n\s*keywords|\n\s*\d+\.?\s*\w+)', 
                                        re.IGNORECASE | re.DOTALL)
            abstract_match = abstract_pattern.search(full_text)
            
            if abstract_match:
                text += abstract_match.group(1).strip() + "\n\n"
                logger.info("已找到摘要部分")
            else:
                logger.warning("未能找到摘要部分")
            
            # 查找结论部分
            conclusion_patterns = [
                re.compile(r'\n\s*\d+\.?\s*conclu\w*\s*\n(.*?)(?:\n\s*\d+\.?\s*\w+|\s*references|\s*acknowledgements)', 
                          re.IGNORECASE | re.DOTALL),
                re.compile(r'\n\s*conclu\w*\s*\n(.*?)(?:\n\s*\w+|\s*references|\s*acknowledgements)', 
                          re.IGNORECASE | re.DOTALL)
            ]
            
            for pattern in conclusion_patterns:
                conclusion_match = pattern.search(full_text)
                if conclusion_match:
                    text += conclusion_match.group(1).strip()
                    logger.info("已找到结论部分")
                    break
            else:
                logger.warning("未能找到结论部分")
                
    except Exception as e:
        logger.error(f"PDF处理出错: {e}")
    
    logger.info(f"提取的文本长度: {len(text)} 字符")
    return text

def extract_text_from_beamer(tex_path: str) -> str:
    """
    从Beamer .tex文件中提取所有frame环境内的文本
    
    Args:
        tex_path: .tex文件路径
        
    Returns:
        拼接后的文本
    """
    logger.info(f"从Beamer提取文本: {tex_path}")
    text = ""
    
    try:
        with open(tex_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # 找到所有frame环境
        frame_pattern = re.compile(r'\\begin{frame}(.*?)\\end{frame}', re.DOTALL)
        frames = frame_pattern.findall(content)
        
        for frame in frames:
            # 提取frame标题
            title_match = re.search(r'\\frametitle{(.*?)}', frame)
            if title_match:
                text += title_match.group(1) + "\n"
            
            # 清理LaTeX命令，但保留文本
            cleaned_text = latex_utils.extract_text_from_latex(frame)
            text += cleaned_text + "\n\n"
            
    except Exception as e:
        logger.error(f"Beamer文件处理出错: {e}")
    
    logger.info(f"提取的文本长度: {len(text)} 字符")
    return text

def calculate_metrics(source_text: str, generated_text: str, lang: str = "en") -> Dict[str, Any]:
    """
    计算BERTScore和ROUGE-L分数
    
    Args:
        source_text: 源文本
        generated_text: 生成的文本
        lang: 语言，默认英语
        
    Returns:
        包含BERTScore和ROUGE-L评分的字典
    """
    logger.info("开始计算内容覆盖度指标...")
    
    # 预处理文本
    preprocessed_source = preprocess_text(source_text)
    preprocessed_generated = preprocess_text(generated_text)
    
    metrics = {}
    
    # 计算BERTScore
    try:
        bertscore = evaluate.load("bertscore")
        results = bertscore.compute(
            predictions=[preprocessed_generated], 
            references=[preprocessed_source], 
            lang=lang
        )
        metrics["bertscore_f1"] = results["f1"][0]
        logger.info(f"BERTScore F1: {metrics['bertscore_f1']:.4f}")
    except Exception as e:
        logger.error(f"计算BERTScore时出错: {e}")
        metrics["bertscore_f1"] = None
    
    # 计算ROUGE-L
    try:
        rouge = evaluate.load("rouge")
        results = rouge.compute(
            predictions=[preprocessed_generated], 
            references=[preprocessed_source]
        )
        metrics["rouge_l"] = results["rougeL"]
        logger.info(f"ROUGE-L: {metrics['rouge_l']:.4f}")
    except Exception as e:
        logger.error(f"计算ROUGE-L时出错: {e}")
        metrics["rouge_l"] = None
    
    return metrics

def main(pdf_path: str, tex_path: str, lang: str = "en") -> Dict[str, float]:
    """
    计算内容覆盖度的主函数
    
    Args:
        pdf_path: 原论文PDF路径
        tex_path: 生成的Beamer .tex文件路径
        lang: 语言代码
        
    Returns:
        评估结果字典
    """
    # 确保文件存在
    if not os.path.exists(pdf_path):
        logger.error(f"PDF文件不存在: {pdf_path}")
        return {"error": "PDF文件不存在"}
    
    if not os.path.exists(tex_path):
        logger.error(f"TEX文件不存在: {tex_path}")
        return {"error": "TEX文件不存在"}
    
    # 1. 提取源文本
    source_text = extract_abstract_conclusion_from_pdf(pdf_path)
    if not source_text:
        logger.error("未能从PDF提取有效文本")
        return {"error": "未能从PDF提取有效文本"}
    
    # 2. 提取生成的文本
    generated_text = extract_text_from_beamer(tex_path)
    if not generated_text:
        logger.error("未能从TEX文件提取有效文本")
        return {"error": "未能从TEX文件提取有效文本"}
    
    # 3. 计算指标
    metrics = calculate_metrics(source_text, generated_text, lang)
    
    return metrics

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="评估Beamer幻灯片的内容覆盖度")
    parser.add_argument("--pdf", required=True, help="源论文PDF文件路径")
    parser.add_argument("--tex", required=True, help="生成的Beamer .tex文件路径")
    parser.add_argument("--lang", default="en", help="语言代码，默认为英语(en)")
    parser.add_argument("--output", help="结果输出JSON文件路径")
    
    args = parser.parse_args()
    
    results = main(args.pdf, args.tex, args.lang)
    
    # 输出结果
    print("\n内容覆盖度评估结果:")
    for metric, value in results.items():
        if isinstance(value, float):
            print(f"  {metric}: {value:.4f}")
        else:
            print(f"  {metric}: {value}")
    
    # 如果指定了输出文件，则保存结果
    if args.output:
        import json
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存至: {args.output}") 