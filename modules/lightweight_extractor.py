"""
Lightweight content extraction module: Use marker-pdf to directly extract markdown text and images
Significantly reduce file size while maintaining content quality
"""
import os
import json
import time
import logging
from datetime import datetime
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from surya.settings import settings


class LightweightExtractor:
    def __init__(self, pdf_path, output_dir="output"):
        """
        Initialize lightweight content extractor
        
        Args:
            pdf_path: PDF file path
            output_dir: Output directory
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        
        # Use timestamp to create unique session ID
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create session-specific image directory
        self.img_dir = os.path.join("output", "images", self.session_id)
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.img_dir, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Setup marker model paths
        self._setup_marker_models()
    
    def _setup_marker_models(self):
        """Setup marker model paths"""
        model_root = "models"
        settings.MODEL_CACHE_DIR = model_root
        for checkpoint in [
            "LAYOUT_MODEL_CHECKPOINT",
            "DETECTOR_MODEL_CHECKPOINT", 
            "OCR_ERROR_MODEL_CHECKPOINT",
            "TABLE_REC_MODEL_CHECKPOINT",
            "RECOGNITION_MODEL_CHECKPOINT",
        ]:
            value = getattr(settings, checkpoint)
            if "s3://" in value:
                value = value.replace("s3://", "/")
                setattr(settings, checkpoint, model_root + value)
    
    def extract_content(self):
        """
        使用marker-pdf提取轻量级内容
        
        Returns:
            dict: 包含markdown文本和图片信息的简化字典
        """
        try:
            self.logger.info(f"Starting marker-pdf content extraction: {self.pdf_path}")
            
            # Create converter
            converter = PdfConverter(artifact_dict=create_model_dict())
            
            # Convert PDF
            start_time = time.time()
            rendered = converter(self.pdf_path)
            conversion_time = time.time() - start_time
            
            self.logger.info(f"PDF conversion completed, time taken: {conversion_time:.2f} seconds")
            
            # 提取文本和图片
            markdown_text, _, images = text_from_rendered(rendered)
            
            # 保存图片到指定目录
            image_list = []
            for i, (filename, image) in enumerate(images.items()):
                image_filepath = os.path.join(self.img_dir, filename)
                image.save(image_filepath, "JPEG")
                
                # 尝试从markdown中提取图片标题
                caption = self._extract_image_caption(markdown_text, filename)
                
                image_info = {
                    "id": f"fig{i+1}",
                    "filename": filename,
                    "path": image_filepath,
                    "caption": caption
                }
                image_list.append(image_info)
            
            # 构建简化的结果
            content = {
                "full_text": markdown_text,
                "images": image_list,
                "pdf_path": self.pdf_path,
                "extraction_time": datetime.now().isoformat(),
                "conversion_time_seconds": conversion_time,
                "session_id": self.session_id
            }
            
            self.logger.info(f"Content extraction completed:")
            self.logger.info(f"  - Text length: {len(markdown_text)} characters")
            self.logger.info(f"  - Number of images: {len(image_list)}")
            
            return content
            
        except Exception as e:
            self.logger.error(f"Content extraction failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_image_caption(self, markdown_text, image_filename):
        """
        从markdown文本中提取图片标题
        
        Args:
            markdown_text: markdown文本
            image_filename: 图片文件名
            
        Returns:
            str: 图片标题，如果没找到则返回空字符串
        """
        try:
            import re
            
            # 查找图片引用模式: ![caption](image_path)
            # 匹配包含该图片文件名的引用
            pattern = rf'!\[(.*?)\]\([^)]*{re.escape(image_filename)}[^)]*\)'
            matches = re.findall(pattern, markdown_text)
            
            if matches:
                # 返回第一个匹配的标题，并清理空白字符
                caption = matches[0].strip()
                if caption:
                    return caption
            
            # 如果没有找到直接引用，尝试查找附近的Figure标题
            # 查找"Figure X:"或"Fig. X:"模式，优先查找图片下方的caption
            lines = markdown_text.split('\n')
            for i, line in enumerate(lines):
                if image_filename in line:
                    # 优先查找图片下方的Figure标题（1-5行内）
                    for j in range(i+1, min(len(lines), i+6)):
                        # 扩展正则表达式以匹配更多格式
                        figure_match = re.search(r'(?:Figure?|Fig\.?)\s*(\d+)[:\.]?\s*(.*)', lines[j], re.IGNORECASE)
                        if figure_match:
                            caption_text = figure_match.group(2).strip()
                            if caption_text:
                                return caption_text
                    
                    # 如果下方没找到，再查找上方的Figure标题（1-3行内）
                    for j in range(max(0, i-3), i):
                        figure_match = re.search(r'(?:Figure?|Fig\.?)\s*(\d+)[:\.]?\s*(.*)', lines[j], re.IGNORECASE)
                        if figure_match:
                            caption_text = figure_match.group(2).strip()
                            if caption_text:
                                return caption_text
                    
                    # 如果还是没找到，尝试查找图片后面紧跟的非空行作为caption
                    for j in range(i+1, min(len(lines), i+4)):
                        line_text = lines[j].strip()
                        # 排除空行、Markdown图片引用行、纯数字行等
                        if (line_text and 
                            not line_text.startswith('!') and 
                            not re.match(r'^\d+$', line_text) and
                            not re.match(r'^[#*-]+$', line_text) and
                            len(line_text) > 10):
                            return line_text
            
            return ""
            
        except Exception as e:
            self.logger.warning(f"提取图片标题时出错: {str(e)}")
            return ""
    
    def save_content(self, content, output_file=None):
        """
        保存提取的内容到JSON文件
        
        Args:
            content: 提取的内容
            output_file: 输出文件路径，如果为None则使用默认路径
            
        Returns:
            str: 保存的文件路径
        """
        if output_file is None:
            output_file = os.path.join(self.output_dir, "lightweight_content.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        # Record file size
        file_size = os.path.getsize(output_file)
        self.logger.info(f"Lightweight content saved to: {output_file}")
        self.logger.info(f"File size: {file_size / 1024 / 1024:.2f}MB")
        
        return output_file
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        if hasattr(self, 'img_dir') and os.path.exists(self.img_dir):
            try:
                import shutil
                self.logger.info(f"Cleaning up temporary image directory: {self.img_dir}")
                shutil.rmtree(self.img_dir)
            except Exception as e:
                self.logger.warning(f"Error cleaning up temporary files: {str(e)}")

# 便捷函数
def extract_lightweight_content(pdf_path, output_dir="output", cleanup_temp=False):
    """
    从PDF文件中提取轻量级内容（便捷函数）
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
        cleanup_temp: 是否清理临时文件
        
    Returns:
        tuple: (提取的内容字典, 保存的文件路径, 图片目录路径)
    """
    extractor = LightweightExtractor(pdf_path, output_dir)
    content = extractor.extract_content()
    
    if content:
        output_file = extractor.save_content(content)
        
        # 清理临时文件（如果需要）
        if cleanup_temp:
            extractor.cleanup_temp_files()
            
        return content, output_file, extractor.img_dir
    
    return None, None, None
