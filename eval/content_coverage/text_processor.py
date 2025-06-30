#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本预处理模块
用于对比分析前的文本标准化处理
"""

import re
from typing import List, Dict, Any

def preprocess_text(text: str) -> str:
    """
    文本预处理函数，进行标准化处理
    
    Args:
        text: 输入文本
        
    Returns:
        处理后的文本
    """
    # 转为小写
    text = text.lower()
    
    # 规范化空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 标准化标点符号
    # 移除多余的标点符号
    text = re.sub(r'([.!?,:;])\1+', r'\1', text)
    
    # 标准化引用标记 [1] -> ref
    text = re.sub(r'\[\d+\]', ' ref ', text)
    
    # 移除特定字符
    text = text.replace('\\', ' ')
    
    # 标准化公式标记
    text = re.sub(r'\[公式\]', ' formula ', text)
    text = re.sub(r'\[图片\]', ' figure ', text)
    
    # 移除特殊字符但保留字母、数字、基本标点
    text = re.sub(r'[^\w\s.,!?:;()\[\]{}"-]', '', text)
    
    # 移除可能的多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def normalize_text_for_comparison(text1: str, text2: str) -> tuple:
    """
    对两段文本进行标准化处理，使其更适合进行比较
    
    Args:
        text1: 第一段文本
        text2: 第二段文本
        
    Returns:
        标准化后的两段文本
    """
    # 基本预处理
    text1 = preprocess_text(text1)
    text2 = preprocess_text(text2)
    
    # 分词为单词列表
    words1 = text1.split()
    words2 = text2.split()
    
    # 返回处理后的文本
    return ' '.join(words1), ' '.join(words2)

def tokenize_text(text: str) -> List[str]:
    """
    将文本分割为句子列表
    
    Args:
        text: 输入文本
        
    Returns:
        句子列表
    """
    # 简单的句子切分
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # 过滤空句子
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences 