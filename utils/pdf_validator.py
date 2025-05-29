"""
PDF提取内容验证工具：用于验证提取内容的准确性
"""
import os
import json
import fitz  # PyMuPDF
import logging
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

class PdfValidator:
    def __init__(self, pdf_path, raw_content_path, output_dir="output/validation"):
        """
        初始化PDF验证器
        
        Args:
            pdf_path: 原始PDF文件路径
            raw_content_path: 提取的原始内容JSON文件路径
            output_dir: 输出目录，用于存储验证结果
        """
        self.pdf_path = pdf_path
        self.raw_content_path = raw_content_path
        self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 加载原始内容
        self.load_raw_content()
    
    def load_raw_content(self):
        """加载提取的原始内容"""
        try:
            with open(self.raw_content_path, 'r', encoding='utf-8') as f:
                self.raw_content = json.load(f)
            return True
        except Exception as e:
            self.logger.error(f"加载原始内容失败: {str(e)}")
            self.raw_content = None
            return False
    
    def validate_text_extraction(self, page_nums=None, output_file=None):
        """
        验证文本提取的准确性
        
        Args:
            page_nums: 要验证的页码列表，默认为None表示全部页面
            output_file: 输出文件路径，默认为None表示使用默认路径
            
        Returns:
            str: 输出文件路径
        """
        if not self.raw_content:
            self.logger.error("没有原始内容可验证")
            return None
            
        # 默认输出文件路径
        if output_file is None:
            output_file = os.path.join(self.output_dir, "text_validation.pdf")
            
        # 打开原始PDF
        try:
            doc = fitz.open(self.pdf_path)
        except Exception as e:
            self.logger.error(f"打开PDF文件失败: {str(e)}")
            return None
            
        # 确定要验证的页码
        if page_nums is None:
            page_nums = list(range(min(len(doc), len(self.raw_content.get("pages_text", [])))))
        
        # 创建PDF来保存对比结果
        with PdfPages(output_file) as pdf:
            for page_num in page_nums:
                if page_num >= len(doc) or page_num >= len(self.raw_content.get("pages_text", [])):
                    continue
                    
                # 获取原始页面和提取的文本
                page = doc[page_num]
                extracted_text = self.raw_content["pages_text"][page_num]["text"]
                
                # 渲染页面为图像
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放以获得更好的质量
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # 创建对比图
                plt.figure(figsize=(12, 18))
                
                # 显示原始页面
                plt.subplot(2, 1, 1)
                plt.imshow(img)
                plt.title(f"页面 {page_num+1} 原始图像")
                plt.axis('off')
                
                # 显示提取的文本
                plt.subplot(2, 1, 2)
                plt.text(0.05, 0.95, extracted_text, fontsize=10, 
                         verticalalignment='top', wrap=True)
                plt.title(f"页面 {page_num+1} 提取文本")
                plt.axis('off')
                
                # 保存到PDF
                pdf.savefig()
                plt.close()
                
        # 关闭原始PDF
        doc.close()
        
        self.logger.info(f"文本验证结果已保存至: {output_file}")
        return output_file
    
    def validate_image_extraction(self, output_file=None):
        """
        验证图片提取的准确性
        
        Args:
            output_file: 输出文件路径，默认为None表示使用默认路径
            
        Returns:
            str: 输出文件路径
        """
        if not self.raw_content:
            self.logger.error("没有原始内容可验证")
            return None
            
        # 默认输出文件路径
        if output_file is None:
            output_file = os.path.join(self.output_dir, "image_validation.pdf")
            
        # 提取的图片
        images = self.raw_content.get("images", [])
        
        if not images:
            self.logger.warning("没有提取到图片")
            return None
            
        # 创建PDF来保存对比结果
        with PdfPages(output_file) as pdf:
            # 每页显示4张图片
            for i in range(0, len(images), 4):
                plt.figure(figsize=(12, 10))
                
                for j in range(4):
                    if i + j < len(images):
                        img_info = images[i + j]
                        img_path = img_info.get("path", "")
                        
                        if os.path.exists(img_path):
                            try:
                                img = Image.open(img_path)
                                
                                plt.subplot(2, 2, j + 1)
                                plt.imshow(img)
                                plt.title(f"图片 {i+j+1} (页面 {img_info.get('page', '?')})")
                                plt.axis('off')
                            except Exception as e:
                                self.logger.warning(f"打开图片失败: {img_path}, 错误: {str(e)}")
                
                pdf.savefig()
                plt.close()
                
        self.logger.info(f"图片验证结果已保存至: {output_file}")
        return output_file
    
    def validate_structure(self, output_file=None):
        """
        验证提取内容的结构
        
        Args:
            output_file: 输出文件路径，默认为None表示使用默认路径
            
        Returns:
            str: 输出文件路径
        """
        if not self.raw_content:
            self.logger.error("没有原始内容可验证")
            return None
            
        # 默认输出文件路径
        if output_file is None:
            output_file = os.path.join(self.output_dir, "structure_validation.txt")
            
        # 验证内容结构
        validation_result = []
        
        # 基本信息
        validation_result.append("=== PDF基本信息验证 ===")
        validation_result.append(f"PDF路径: {self.raw_content.get('pdf_path', '')}")
        validation_result.append(f"总页数: {self.raw_content.get('total_pages', 0)}")
        validation_result.append(f"元数据: {json.dumps(self.raw_content.get('metadata', {}), ensure_ascii=False)}")
        
        # 页面文本
        validation_result.append("\n=== 页面文本验证 ===")
        pages_text = self.raw_content.get("pages_text", [])
        validation_result.append(f"提取的页面数: {len(pages_text)}")
        
        if pages_text:
            # 统计每页的文本块数量
            block_counts = [len(page.get("blocks", [])) for page in pages_text]
            validation_result.append(f"每页文本块数量: {block_counts}")
            
            # 检查是否有空文本的页面
            empty_pages = [i+1 for i, page in enumerate(pages_text) if not page.get("text", "").strip()]
            if empty_pages:
                validation_result.append(f"警告: 发现空文本页面: {empty_pages}")
                
            # 检查页码是否连续
            page_nums = [page.get("page_num", 0) for page in pages_text]
            expected_page_nums = list(range(1, len(pages_text) + 1))
            if page_nums != expected_page_nums:
                validation_result.append(f"警告: 页码不连续，预期: {expected_page_nums}，实际: {page_nums}")
        
        # 图片
        validation_result.append("\n=== 图片验证 ===")
        images = self.raw_content.get("images", [])
        validation_result.append(f"提取的图片数: {len(images)}")
        
        if images:
            # 检查图片文件是否存在
            missing_images = [img.get("path", "") for img in images if not os.path.exists(img.get("path", ""))]
            if missing_images:
                validation_result.append(f"警告: 有{len(missing_images)}张图片文件不存在")
                validation_result.append(f"示例: {missing_images[:5]}")
                
            # 统计每页的图片数量
            page_image_counts = {}
            for img in images:
                page = img.get("page", 0)
                page_image_counts[page] = page_image_counts.get(page, 0) + 1
            
            validation_result.append(f"每页图片数量: {json.dumps(page_image_counts, ensure_ascii=False)}")
        
        # 保存验证结果
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(validation_result))
            
        self.logger.info(f"结构验证结果已保存至: {output_file}")
        return output_file
    
    def validate_all(self, sample_pages=None):
        """
        进行所有验证
        
        Args:
            sample_pages: 要验证的样本页码列表，默认为None表示自动选择
            
        Returns:
            list: 输出文件路径列表
        """
        # 如果未指定样本页码，则选择前2页和最后1页
        if sample_pages is None:
            total_pages = self.raw_content.get("total_pages", 0)
            if total_pages > 0:
                sample_pages = [0, 1]  # 前两页
                if total_pages > 3:
                    sample_pages.append(total_pages - 1)  # 最后一页
            else:
                sample_pages = []
                
        # 进行所有验证
        results = []
        
        # 验证文本提取
        text_result = self.validate_text_extraction(page_nums=sample_pages)
        if text_result:
            results.append(text_result)
            
        # 验证图片提取
        image_result = self.validate_image_extraction()
        if image_result:
            results.append(image_result)
            
        # 验证结构
        structure_result = self.validate_structure()
        if structure_result:
            results.append(structure_result)
            
        return results

def validate_pdf_extraction(pdf_path, raw_content_path, output_dir="output/validation", sample_pages=None):
    """
    验证PDF提取内容的准确性（便捷函数）
    
    Args:
        pdf_path: 原始PDF文件路径
        raw_content_path: 提取的原始内容JSON文件路径
        output_dir: 输出目录
        sample_pages: 要验证的样本页码列表
        
    Returns:
        list: 输出文件路径列表
    """
    validator = PdfValidator(pdf_path, raw_content_path, output_dir)
    return validator.validate_all(sample_pages) 