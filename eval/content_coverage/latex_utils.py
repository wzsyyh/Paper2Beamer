#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LaTeX文本处理工具
用于从LaTeX文档中提取纯文本内容，过滤掉LaTeX命令和环境
"""

import re
from typing import Dict, List, Tuple

def extract_text_from_latex(latex_text: str) -> str:
    """
    从LaTeX文本中提取纯文本内容，过滤掉LaTeX命令
    
    Args:
        latex_text: 原始LaTeX文本
        
    Returns:
        提取的纯文本
    """
    # 保存处理后的文本
    processed_text = latex_text
    
    # 移除注释行
    processed_text = re.sub(r'%.*?\n', '\n', processed_text)
    
    # 提取和保存文本内容
    # 1. 移除常见的环境，但保留内容
    environments_to_simplify = [
        'center', 'flushleft', 'flushright', 'quote', 'quotation', 
        'itemize', 'enumerate', 'description', 'small', 'large',
        'tiny', 'scriptsize', 'footnotesize', 'normalsize',
        'large', 'Large', 'LARGE', 'huge', 'Huge'
    ]
    
    for env in environments_to_simplify:
        processed_text = re.sub(
            r'\\begin{' + env + r'}(.*?)\\end{' + env + r'}',
            r'\1',
            processed_text, 
            flags=re.DOTALL
        )
    
    # 2. 移除块数学公式环境，替换为占位符
    processed_text = re.sub(
        r'\\begin{(equation|align|gather|multline|eqnarray)[\*]?}.*?\\end{\1[\*]?}',
        ' [公式] ',
        processed_text,
        flags=re.DOTALL
    )
    
    # 3. 移除行内数学公式，替换为占位符
    processed_text = re.sub(r'\$\$(.*?)\$\$', ' [公式] ', processed_text, flags=re.DOTALL)
    processed_text = re.sub(r'\$(.*?)\$', ' [公式] ', processed_text, flags=re.DOTALL)
    processed_text = re.sub(r'\\[(](.*?)\\[)]', ' [公式] ', processed_text, flags=re.DOTALL)
    
    # 4. 提取图片标题
    processed_text = re.sub(r'\\includegraphics\s*(?:\[.*?\])?\s*{.*?}', ' [图片] ', processed_text)
    
    # 5. 处理列表项
    processed_text = re.sub(r'\\item\s*', '* ', processed_text)
    
    # 6. 提取frame标题和子标题
    processed_text = re.sub(r'\\frametitle\s*{(.*?)}', r'\1\n', processed_text)
    processed_text = re.sub(r'\\framesubtitle\s*{(.*?)}', r'\1\n', processed_text)
    
    # 7. 处理一般的LaTeX命令
    # 提取带括号命令的参数文本
    processed_text = re.sub(r'\\[a-zA-Z]+\s*{(.*?)}', r'\1', processed_text)
    
    # 8. 处理没有参数的命令
    processed_text = re.sub(r'\\[a-zA-Z]+\s*', ' ', processed_text)
    
    # 9. 处理特殊字符和符号
    special_chars = {
        r'\\textbackslash': '\\',
        r'\\textasciicircum': '^',
        r'\\textasciitilde': '~',
        r'\\textbar': '|',
        r'\\textgreater': '>',
        r'\\textless': '<',
        r'\\&': '&',
        r'\\%': '%',
        r'\\#': '#',
        r'\\_': '_',
        r'\\~': '~',
        r'\\^': '^',
        r'``': '"',
        r"''": '"',
    }
    
    for pattern, replacement in special_chars.items():
        processed_text = processed_text.replace(pattern, replacement)
    
    # 10. 移除多余空白
    processed_text = re.sub(r'\s+', ' ', processed_text)
    processed_text = processed_text.strip()
    
    return processed_text

def extract_frames(tex_content: str) -> List[Dict[str, str]]:
    """
    从Beamer文件中提取所有frame及其内容
    
    Args:
        tex_content: 整个Beamer文件的内容
        
    Returns:
        包含每个frame信息的字典列表
    """
    frames = []
    
    # 查找所有frame环境
    frame_pattern = re.compile(r'\\begin{frame}(.*?)\\end{frame}', re.DOTALL)
    frame_matches = frame_pattern.findall(tex_content)
    
    for i, frame_content in enumerate(frame_matches):
        frame_info = {'index': i + 1, 'content': frame_content}
        
        # 提取frame标题
        title_match = re.search(r'\\frametitle{(.*?)}', frame_content)
        if title_match:
            frame_info['title'] = title_match.group(1)
        else:
            frame_info['title'] = f"无标题幻灯片 {i+1}"
            
        # 提取纯文本内容
        frame_info['text'] = extract_text_from_latex(frame_content)
        
        frames.append(frame_info)
        
    return frames 