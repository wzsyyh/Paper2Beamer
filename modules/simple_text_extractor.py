"""
简单文本提取器模块：从PDF中提取纯文本内容
用于Basic LLM baseline，不进行结构化处理
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple
import fitz  # PyMuPDF

class SimpleTextExtractor:
    def __init__(self):
        """初始化简单文本提取器"""
        self.logger = logging.getLogger(__name__)
    
    def extract_text(self, pdf_path: str) -> Optional[str]:
        """
        从PDF中提取纯文本内容
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            str: 提取的纯文本内容，保留基本格式
        """
        if not os.path.exists(pdf_path):
            self.logger.error(f"PDF文件不存在: {pdf_path}")
            return None
        
        try:
            # 打开PDF文件
            doc = fitz.open(pdf_path)
            full_text = ""
            
            # 逐页提取文本
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # 提取文本，保留基本格式
                text = page.get_text()
                
                # 添加页面分隔符
                if page_num > 0:
                    full_text += f"\n\n--- Page {page_num + 1} ---\n\n"
                else:
                    full_text += f"--- Page {page_num + 1} ---\n\n"
                
                # 清理和格式化文本
                cleaned_text = self._clean_text(text)
                full_text += cleaned_text
            
            doc.close()
            
            self.logger.info(f"成功提取PDF文本，总长度: {len(full_text)} 字符")
            return full_text
            
        except Exception as e:
            self.logger.error(f"提取PDF文本失败: {str(e)}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """
        清理和格式化文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        # 基本清理
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 去除首尾空白
            line = line.strip()
            
            # 跳过空行（但保留段落分隔）
            if not line:
                if cleaned_lines and cleaned_lines[-1] != "":
                    cleaned_lines.append("")
                continue
            
            # 去除过短的行（可能是页眉页脚）
            if len(line) < 3:
                continue
            
            # 去除明显的页码
            if line.isdigit() and len(line) <= 3:
                continue
            
            cleaned_lines.append(line)
        
        # 重新组合文本
        result = '\n'.join(cleaned_lines)
        
        # 去除多余的空行
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        
        return result
    
    def save_text(self, text: str, output_path: str) -> bool:
        """
        保存提取的文本到文件
        
        Args:
            text: 要保存的文本
            output_path: 输出文件路径
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存文本
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            self.logger.info(f"文本已保存到: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存文本失败: {str(e)}")
            return False


def extract_simple_text(pdf_path: str, output_dir: str = None) -> Tuple[Optional[str], Optional[str]]:
    """
    便捷函数：提取PDF文本并可选保存
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录（可选）
        
    Returns:
        Tuple[str, str]: (提取的文本, 保存的文件路径)
    """
    extractor = SimpleTextExtractor()
    
    # 提取文本
    text = extractor.extract_text(pdf_path)
    if not text:
        return None, None
    
    # 保存文本（如果指定了输出目录）
    saved_path = None
    if output_dir:
        filename = f"{Path(pdf_path).stem}_simple_text.txt"
        saved_path = os.path.join(output_dir, filename)
        if not extractor.save_text(text, saved_path):
            saved_path = None
    
    return text, saved_path
