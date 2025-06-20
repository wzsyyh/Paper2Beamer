"""
原始内容提取模块：负责从PDF文件提取原始文本和图像，不进行结构化处理
专注于完整准确地提取PDF信息，保留原始格式信息
"""
import os
import json
import logging
import fitz  # PyMuPDF
import pdfplumber
import re
from PIL import Image
import hashlib
from datetime import datetime
import time
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from surya.settings import settings

class RawExtractor:
    def __init__(self, pdf_path, output_dir="output"):
        """
        初始化原始内容提取器
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录，用于存储提取的内容
        """
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        
        # 使用时间戳创建唯一的会话ID
        self.session_id = f"{int(time.time())}"
        
        # 创建会话特定的图片目录
        self.img_dir = os.path.join("output", "images", self.session_id)
        self.doc = None
        self.plumber_doc = None
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.img_dir, exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def open_document(self):
        """打开PDF文档"""
        try:
            # 使用PyMuPDF打开文档
            self.doc = fitz.open(self.pdf_path)
            
            # 使用pdfplumber作为备用提取器
            self.plumber_doc = pdfplumber.open(self.pdf_path)
            
            return True
        except Exception as e:
            self.logger.error(f"打开PDF文件失败: {str(e)}")
            return False
    
    def close_document(self):
        """关闭PDF文档"""
        if self.doc:
            self.doc.close()
            self.doc = None
            
        if self.plumber_doc:
            self.plumber_doc.close()
            self.plumber_doc = None
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        # 清理临时图片目录
        if hasattr(self, 'img_dir') and os.path.exists(self.img_dir):
            try:
                import shutil
                self.logger.info(f"清理临时图片目录: {self.img_dir}")
                shutil.rmtree(self.img_dir)
            except Exception as e:
                self.logger.warning(f"清理临时文件时出错: {str(e)}")
    
    def extract_content(self):
        """
        提取PDF的原始内容（文本和图像）
        
        Returns:
            dict: 包含提取的原始内容的字典
        """
        if not self.doc and not self.open_document():
            return None
        
        try:
            # 提取文档信息
            document_info = self.extract_document_info()
            
            # 提取页面内容（文本、格式信息等）
            pages_content = self.extract_pages_content()
            
            # 提取图片
            images = self.extract_images()
            
            # 提取目录结构（如果有）
            toc = self.extract_toc()
            
            # 组装结果
            content = {
                "document_info": document_info,
                "pages_content": pages_content,
                "images": images,
                "toc": toc,
                "pdf_path": self.pdf_path,
                "extraction_time": datetime.now().isoformat()
            }
            
            return content
        
        except Exception as e:
            self.logger.error(f"提取内容失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            self.close_document()
            # 注意：这里暂时不清理临时文件，因为后续处理可能还需要这些图片
    
    def extract_document_info(self):
        """
        提取PDF的文档信息
        
        Returns:
            dict: 文档信息字典
        """
        info = {
            "metadata": {},
            "total_pages": len(self.doc),
            "file_size_bytes": os.path.getsize(self.pdf_path) if os.path.exists(self.pdf_path) else 0,
            "file_name": os.path.basename(self.pdf_path)
        }
        
        # 提取元数据
        if self.doc.metadata:
            for key, value in self.doc.metadata.items():
                if value:  # 只保存非空值
                    info["metadata"][key] = value
        
        # 提取页面尺寸（使用第一页）
        if len(self.doc) > 0:
            first_page = self.doc[0]
            info["page_width"] = first_page.rect.width
            info["page_height"] = first_page.rect.height
            
        return info
    
    def extract_pages_content(self):
        """
        提取所有页面的内容
        
        Returns:
            list: 页面内容列表
        """
        pages_content = []
        
        for page_num in range(len(self.doc)):
            # 从PyMuPDF提取
            mupdf_page = self.doc[page_num]
            
            # 从pdfplumber提取（作为备用）
            plumber_page = self.plumber_doc.pages[page_num] if self.plumber_doc else None
            
            # 页面基本信息
            page_info = {
                "page_num": page_num + 1,
                "width": mupdf_page.rect.width,
                "height": mupdf_page.rect.height
            }
            
            # 提取页面文本（多种方式）
            page_info["text"] = {
                "plain": mupdf_page.get_text("text").strip(),
                "html": mupdf_page.get_text("html").strip(),
                "dict": self._process_text_dict(mupdf_page.get_text("dict"))
            }
            
            # 从pdfplumber提取表格（如果有）
            if plumber_page:
                try:
                    tables = plumber_page.extract_tables()
                    if tables:
                        page_info["tables"] = []
                        for table in tables:
                            if table:
                                # 清理表格数据（移除None和空字符串）
                                cleaned_table = []
                                for row in table:
                                    if row:
                                        cleaned_row = []
                                        for cell in row:
                                            if cell is not None:
                                                cell = str(cell).strip()
                                            cleaned_row.append(cell)
                                        cleaned_table.append(cleaned_row)
                                page_info["tables"].append(cleaned_table)
                except Exception as e:
                    self.logger.warning(f"提取表格失败: {str(e)}")
            
            # 添加到结果
            pages_content.append(page_info)
        
        return pages_content
    
    def _process_text_dict(self, text_dict):
        """处理文本字典，去除不必要的嵌套结构，保留关键信息"""
        if not text_dict or "blocks" not in text_dict:
            return {}
        
        # 创建一个新的字典，只保留关键信息
        processed_dict = {
            "width": text_dict.get("width", 0),
            "height": text_dict.get("height", 0),
            "blocks": []
        }
        
        # 处理每个文本块
        for block in text_dict["blocks"]:
            # 跳过没有行的块
            if "lines" not in block:
                continue
                
            processed_block = {
                "type": block.get("type", ""),
                "bbox": block.get("bbox", []),
                "lines": []
            }
            
            # 处理每一行
            for line in block["lines"]:
                processed_line = {
                    "bbox": line.get("bbox", []),
                    "spans": []
                }
                
                # 处理每个span
                for span in line.get("spans", []):
                    processed_span = {
                        "text": span.get("text", ""),
                        "font": span.get("font", ""),
                        "size": span.get("size", 0),
                        "flags": span.get("flags", 0),  # 字体样式标志
                        "color": span.get("color", 0),  # 颜色
                        "bbox": span.get("bbox", [])
                    }
                    processed_line["spans"].append(processed_span)
                
                processed_block["lines"].append(processed_line)
            
            processed_dict["blocks"].append(processed_block)
        
        return processed_dict
    def extract_image_info_from_directory(self, img_dir):
        """
        从图片目录中提取图片信息

        Args:
            img_dir (str): 图片目录路径
        
        Returns:
            list: 图片信息列表，每个元素是一个字典，包含图片的相关信息
        """
        image_info_list = []
        image_hashes = set()  # 用于去重
    
        # 支持的图片格式
        valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}
        
        # 遍历图片目录
        for root, _, files in os.walk(img_dir):
            for file in files:
                # 获取文件扩展名
                file_ext = os.path.splitext(file)[1].lower()
                
                # 检查是否是支持的图片格式
                if file_ext not in valid_extensions:
                    continue
                    
                file_path = os.path.join(root, file)
                
                try:
                    # 打开图片
                    match = re.search(r'_page_(\d+)_', file)
                    if match:
                        page_num = int(match.group(1))
                    else:
                        page_num = None  # 如果没有匹配到页码，则设置为 None
                    with Image.open(file_path) as img:
                        # 获取图片基本信息
                        width, height = img.size
                        image_bytes = img.tobytes()
                        
                        # 计算图像哈希以去重
                        img_hash = hashlib.md5(image_bytes).hexdigest()
                        
                        # 检查是否为重复图像
                        if img_hash in image_hashes:
                            continue
                            
                        image_hashes.add(img_hash)
                        
                        # 筛选掉太小的图像（可能是图标或装饰）
                        if width < 100 or height < 100:
                            print(f"跳过小图像: {file}, 尺寸 {width}x{height}")
                            continue
                        
                        # 计算图片重要性（基于尺寸）
                        # 这里可以根据需要添加其他重要性计算逻辑
                        importance = (width * height) / (1920 * 1080)  # 假设以1920x1080为基准
                        
                        # 记录图像信息
                        image_info = {
                            "filename": file,
                            "path": file_path,
                            "page": page_num + 1,
                            "width": width,
                            "height": height,
                            "type": "file",
                            "hash": img_hash,
                            "importance": importance,
                            "is_chart": self._is_likely_chart(image_bytes, width, height)  # 需要根据实际情况实现_is_likely_chart方法
                        }
                        
                        image_info_list.append(image_info)
                        
                except Exception as e:
                    self.logger.warning(f"处理图片 {file} 时发生错误: {str(e)}")
        
        return image_info_list

    def extract_images(self):
        """
        提取PDF中的图片
        
        Returns:
            list: 图片信息列表
        """
        
        
        self.logger.info("load model")
        model_root = "models"
        settings.MODEL_CACHE_DIR = model_root
        for chectpoint in [
            "LAYOUT_MODEL_CHECKPOINT",
            "DETECTOR_MODEL_CHECKPOINT",
            "OCR_ERROR_MODEL_CHECKPOINT",
            "TABLE_REC_MODEL_CHECKPOINT",
            "RECOGNITION_MODEL_CHECKPOINT",
        ]:
            value = getattr(settings, chectpoint)
            if "s3://" in value:
                value = value.replace("s3://", "/")
                setattr(settings, chectpoint, model_root + value)
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )
        self.logger.info("end load")

        rendered = converter(self.pdf_path)
        # text = rendered.markdown
        text, _, images = text_from_rendered(rendered)
        output_path = self.img_dir
        for filename, image in images.items():
            image_filepath = os.path.join(output_path, filename)
            image.save(image_filepath, "JPEG")

        # 从渲染结果中提取图片标题
        image_captions = {}
        try:
            # 尝试从 markdown 文本中提取图片标题
            markdown_text = rendered.markdown if hasattr(rendered, 'markdown') else ""
            
            # 使用正则表达式查找图片引用和标题
            # 匹配格式如: ![caption text](image_path)
            import re
            image_pattern = r'!\[(.*?)\]\((.*?)\)'
            matches = re.findall(image_pattern, markdown_text)
            
            for caption, image_path in matches:
                if caption.strip() and image_path:
                    img_filename = os.path.basename(image_path)
                    # 清理标题文本
                    clean_caption = caption.strip()
                    if clean_caption:
                        image_captions[img_filename] = clean_caption
                        self.logger.info(f"从Markdown中找到图片标题: {img_filename} -> {clean_caption}")
            
            # 如果没有找到标题，尝试其他方法
            if not image_captions:
                self.logger.info("未从Markdown中找到图片标题，尝试其他方法...")
                
        except Exception as e:
            self.logger.warning(f"提取图片标题时出错: {str(e)}")

        candidate_images = self.extract_image_info_from_directory(self.img_dir)

        # 将提取到的标题添加到图片信息中
        for img_info in candidate_images:
            if img_info["filename"] in image_captions:
                img_info["caption"] = image_captions[img_info["filename"]]
                self.logger.info(f"为图片 {img_info['filename']} 添加标题: {img_info['caption']}")
        
        # 按重要性排序图像
        candidate_images.sort(key=lambda x: x.get("importance", 0), reverse=True)
        
        # 图表优先
        charts = [img for img in candidate_images if img.get("is_chart", False)]
        non_charts = [img for img in candidate_images if not img.get("is_chart", False)]
        
        # 选择重要的图像（图表优先，然后是其他重要图像）
        max_images = 10  # 最多保留的图像数量
        selected_images = charts[:max_images]
        
        # 如果图表不足max_images，添加其他重要图像
        if len(selected_images) < max_images:
            selected_images.extend(non_charts[:max_images - len(selected_images)])
        
        # 只返回选中的图像
        images = selected_images
        
        # 如果没有提取到图像，则尝试渲染页面（与原代码逻辑保持一致）
        if not images:
            self.logger.info("未检测到内嵌图像，将渲染页面为图像")
            
            # 以页面为单位保存为图像作为回退方案
            for page_num in range(len(self.doc)):
                page = self.doc[page_num]
                
                # 将页面渲染为图像
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放以获得更好的质量
                image_filename = f"page_{page_num+1}.png"
                image_path = os.path.join(self.img_dir, image_filename)
                
                # 保存页面图像
                pix.save(image_path)
                
                # 记录页面图像信息
                image_info = {
                    "filename": image_filename,
                    "path": image_path,
                    "page": page_num + 1,
                    "width": pix.width,
                    "height": pix.height,
                    "type": "page_render",
                    "importance": 50  # 默认重要性
                }
                
                images.append(image_info)
        
        return images
    
    def _is_likely_chart(self, image_bytes, width, height):
        """
        估计图像是否可能是图表/图形
        
        Args:
            image_bytes: 图像二进制数据
            width: 图像宽度
            height: 图像高度
            
        Returns:
            bool: 是否可能是图表
        """
        try:
            from io import BytesIO
            from PIL import Image, ImageStat
            
            # 打开图像
            image = Image.open(BytesIO(image_bytes))
            
            # 1. 颜色多样性检查 - 图表通常颜色较少
            if image.mode == "RGB":
                stat = ImageStat.Stat(image)
                color_variance = sum(stat.stddev) / 3  # RGB通道标准差的平均值
                if color_variance < 60:  # 低色彩方差表明可能是图表
                    return True
            
            # 2. 纵横比检查 - 图表通常接近方形
            aspect_ratio = width / height if height > 0 else 0
            if 0.5 <= aspect_ratio <= 2.0:  # 接近方形的纵横比
                return True
                
            # 3. 其他可能的图表特征
            # ...可以添加更多启发式规则
            
            return False
        except Exception:
            # 如果分析失败，默认不是图表
            return False
    
    def extract_toc(self):
        """
        提取PDF的目录结构
        
        Returns:
            list: 目录项列表
        """
        toc = []
        
        # 从PyMuPDF提取目录
        try:
            mupdf_toc = self.doc.get_toc()
            if mupdf_toc:
                for item in mupdf_toc:
                    if len(item) >= 3:
                        toc_item = {
                            "level": item[0],
                            "title": item[1],
                            "page": item[2]
                        }
                        toc.append(toc_item)
        except Exception as e:
            self.logger.warning(f"提取目录失败: {str(e)}")
        
        return toc
    
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
            output_file = os.path.join(self.output_dir, "raw_content.json")
        
        # 处理不可序列化的对象
        def json_serializable(obj):
            if isinstance(obj, (set, frozenset)):
                return list(obj)
            raise TypeError(f"Type {type(obj)} is not JSON serializable")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2, default=json_serializable)
        
        return output_file

# 便捷函数
def extract_raw_content(pdf_path, output_dir="output", cleanup_temp=False):
    """
    从PDF文件中提取原始内容（便捷函数）
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
        cleanup_temp: 是否清理临时文件
        
    Returns:
        提取的原始内容字典和保存的文件路径
    """
    extractor = RawExtractor(pdf_path, output_dir)
    content = extractor.extract_content()
    
    if content:
        output_file = extractor.save_content(content)
        
        # 清理临时文件（如果需要）
        if cleanup_temp:
            extractor.cleanup_temp_files()
            
        return content, output_file
    
    return None, None
