"""
TEX 验证器模块：验证生成的 TEX 代码能否成功编译
"""

import os
import re
import subprocess
import tempfile
import logging
import shutil
from typing import Dict, List, Any, Optional, Tuple, Union

class TexValidator:
    def __init__(self, output_dir: str = "output", language: str = "en"):
        """
        初始化 TEX 验证器
        
        Args:
            output_dir: 输出目录，用于存放编译结果
            language: 文档语言，zh为中文，en为英文
        """
        self.output_dir = output_dir
        self.language = language
        self.logger = logging.getLogger(__name__)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 如果是中文，检查系统中可用的中文字体
        if language == "zh":
            self.available_fonts = self._check_available_fonts()
        else:
            self.available_fonts = []
    
    def _check_available_fonts(self) -> List[str]:
        """
        检查系统中可用的中文字体
        
        Returns:
            List[str]: 可用的中文字体列表
        """
        available_fonts = []
        try:
            # 尝试使用fc-list命令查找中文字体
            process = subprocess.run(
                ["fc-list", ":lang=zh", "family"],
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                # 解析输出，提取字体名称
                font_output = process.stdout.strip()
                if font_output:
                    # 分割并去重
                    fonts = set()
                    for line in font_output.split("\n"):
                        for font in line.split(","):
                            font = font.strip()
                            if font:
                                fonts.add(font)
                    
                    available_fonts = list(fonts)
                    self.logger.info(f"找到 {len(available_fonts)} 个中文字体")
                    
                    # 记录前几个字体用于调试
                    if available_fonts:
                        sample_fonts = available_fonts[:5]
                        self.logger.info(f"部分中文字体: {', '.join(sample_fonts)}")
        except Exception as e:
            self.logger.warning(f"检查中文字体时出错: {str(e)}")
        
        return available_fonts
    
    def validate(self, tex_file: str, timeout: int = 60) -> Tuple[bool, str, Optional[str]]:
        """
        验证 TEX 文件能否成功编译
        
        Args:
            tex_file: TEX 文件路径
            timeout: 编译超时时间（秒）
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 错误信息或成功信息, 生成的PDF路径)
        """
        if not os.path.exists(tex_file):
            return False, f"TEX文件不存在: {tex_file}", None
            
        # 获取TEX文件目录和文件名
        tex_dir = os.path.dirname(tex_file)
        tex_basename = os.path.basename(tex_file)
        
        # 使用临时目录进行编译，避免生成多余的辅助文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 复制TEX文件到临时目录
            temp_tex_file = os.path.join(temp_dir, tex_basename)
            shutil.copy2(tex_file, temp_tex_file)
            
            # 创建临时images目录
            temp_images_dir = os.path.join(temp_dir, "images")
            os.makedirs(temp_images_dir, exist_ok=True)
            
            # 如果存在images目录，复制到临时目录
            images_dir = os.path.join(tex_dir, "images")
            if os.path.exists(images_dir):
                for filename in os.listdir(images_dir):
                    src_file = os.path.join(images_dir, filename)
                    dst_file = os.path.join(temp_images_dir, filename)
                    if os.path.isfile(src_file):
                        shutil.copy2(src_file, dst_file)
            
            # 处理TEX代码中的图片引用 - 尝试从原始路径复制图片到images目录
            try:
                self._process_image_references(tex_file, temp_images_dir)
            except Exception as e:
                self.logger.warning(f"处理图片引用时出错: {str(e)}")
            
            # 运行编译命令
            try:
                # 根据语言选择编译器
                compiler = "xelatex" if self.language == "zh" else "pdflatex"
                
                # 使用-interaction=nonstopmode参数，遇到错误时不会暂停
                cmd = [compiler, "-interaction=nonstopmode", tex_basename]
                self.logger.info(f"运行编译命令: {' '.join(cmd)}")
                
                # 设置工作目录为临时目录
                process = subprocess.run(
                    cmd, 
                    cwd=temp_dir,
                    capture_output=True,
                    text=False,  # 使用二进制模式
                    timeout=timeout
                )
                
                # 尝试解码输出，处理可能的编码问题
                try:
                    stdout = process.stdout.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        stdout = process.stdout.decode('latin1')
                    except UnicodeDecodeError:
                        stdout = str(process.stdout)
                
                # 检查是否编译成功
                if process.returncode == 0:
                    pdf_basename = os.path.splitext(tex_basename)[0] + ".pdf"
                    temp_pdf_file = os.path.join(temp_dir, pdf_basename)
                    
                    # 检查PDF文件是否存在
                    if os.path.exists(temp_pdf_file):
                        # 创建输出目录中的images目录
                        output_images_dir = os.path.join(self.output_dir, "images")
                        os.makedirs(output_images_dir, exist_ok=True)
                        
                        # 复制images目录到输出目录
                        if os.path.exists(temp_images_dir):
                            for filename in os.listdir(temp_images_dir):
                                src_file = os.path.join(temp_images_dir, filename)
                                dst_file = os.path.join(output_images_dir, filename)
                                if os.path.isfile(src_file):
                                    shutil.copy2(src_file, dst_file)
                        
                        # 复制PDF文件到输出目录
                        output_pdf = os.path.join(self.output_dir, pdf_basename)
                        shutil.copy2(temp_pdf_file, output_pdf)
                        
                        # 复制日志文件到输出目录（可选）
                        log_basename = os.path.splitext(tex_basename)[0] + ".log"
                        temp_log_file = os.path.join(temp_dir, log_basename)
                        if os.path.exists(temp_log_file):
                            output_log = os.path.join(self.output_dir, log_basename)
                            shutil.copy2(temp_log_file, output_log)
                        
                        return True, "编译成功", output_pdf
                    else:
                        return False, "编译命令成功执行，但未生成PDF文件", None
                else:
                    # 提取错误信息
                    error_message = self._extract_error_message(stdout)
                    if not error_message:
                        error_message = "未知编译错误，请查看完整日志"
                    
                    # 保存错误日志
                    log_basename = os.path.splitext(tex_basename)[0] + ".log"
                    temp_log_file = os.path.join(temp_dir, log_basename)
                    if os.path.exists(temp_log_file):
                        output_log = os.path.join(self.output_dir, log_basename)
                        shutil.copy2(temp_log_file, output_log)
                        
                    return False, error_message, None
            
            except subprocess.TimeoutExpired:
                return False, f"编译超时（超过{timeout}秒）", None
            except Exception as e:
                return False, f"编译过程中发生错误: {str(e)}", None
    
    def _process_image_references(self, tex_file: str, images_dir: str):
        """
        处理TEX文件中的图片引用，复制图片到images目录
        
        Args:
            tex_file: TEX文件路径
            images_dir: 目标images目录
        """
        # 读取TEX文件内容
        with open(tex_file, 'r', encoding='utf-8') as f:
            tex_content = f.read()
        
        # 查找includegraphics命令
        pattern = r'\\includegraphics\[.*?\]\{([^}]+)\}'
        matches = re.findall(pattern, tex_content)
        
        # 获取presentation_plan.json文件路径
        tex_dir = os.path.dirname(tex_file)
        project_dir = os.path.abspath(os.path.join(tex_dir, ".."))
        plan_dirs = [d for d in os.listdir(project_dir) if os.path.isdir(os.path.join(project_dir, d)) and d.startswith("plan")]
        
        # 查找所有可能的图片源目录
        possible_image_dirs = []
        
        # 1. 查找常规图片目录
        for root, dirs, files in os.walk(project_dir):
            if os.path.basename(root) == "images":
                possible_image_dirs.append(root)
        
        # 2. 查找基于会话ID的图片目录
        images_base_dir = os.path.join(project_dir, "images")
        if os.path.exists(images_base_dir) and os.path.isdir(images_base_dir):
            for d in os.listdir(images_base_dir):
                if d.startswith("session_"):
                    session_images_dir = os.path.join(images_base_dir, d)
                    if os.path.isdir(session_images_dir):
                        possible_image_dirs.append(session_images_dir)
        
        # 3. 查找output目录下的images目录
        output_images_dir = os.path.join(project_dir, "output", "images")
        if os.path.exists(output_images_dir) and os.path.isdir(output_images_dir):
            possible_image_dirs.append(output_images_dir)
            # 检查会话特定目录
            for d in os.listdir(output_images_dir):
                if d.startswith("session_"):
                    session_images_dir = os.path.join(output_images_dir, d)
                    if os.path.isdir(session_images_dir):
                        possible_image_dirs.append(session_images_dir)
        
        self.logger.info(f"找到 {len(possible_image_dirs)} 个可能的图片源目录")
        
        # 处理每个图片引用
        missing_images = []
        for img_path in matches:
            # 检查路径是否已经是相对于images的路径
            if img_path.startswith("images/"):
                img_filename = os.path.basename(img_path)
                img_dest_path = os.path.join(images_dir, img_filename)
                
                # 如果images目录中已有该文件，直接跳过
                if os.path.exists(img_dest_path) and os.path.isfile(img_dest_path):
                    self.logger.info(f"图片已存在: {img_dest_path}")
                    continue
            else:
                # 提取文件名
                img_filename = os.path.basename(img_path)
                img_dest_path = os.path.join(images_dir, img_filename)
            
            # 查找实际图片文件
            found = False
            for src_dir in possible_image_dirs:
                src_file = os.path.join(src_dir, img_filename)
                if os.path.exists(src_file) and os.path.isfile(src_file):
                    # 复制到images目录
                    dst_file = os.path.join(images_dir, img_filename)
                    shutil.copy2(src_file, dst_file)
                    self.logger.info(f"复制图片: {src_file} -> {dst_file}")
                    found = True
                    break
            
            if not found:
                # 尝试查找完整路径的文件
                full_path = img_path
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    dst_file = os.path.join(images_dir, img_filename)
                    shutil.copy2(full_path, dst_file)
                    self.logger.info(f"复制图片: {full_path} -> {dst_file}")
                else:
                    self.logger.warning(f"未找到图片: {img_path}")
                    missing_images.append(img_path)
        
        # 如果有缺失的图片，创建占位图形并修改TEX内容
        if missing_images:
            modified_tex_content = tex_content
            for img_path in missing_images:
                img_filename = os.path.basename(img_path)
                
                # 生成占位图形
                placeholder_path = os.path.join(images_dir, f"placeholder_{img_filename}.png")
                self._create_placeholder_image(placeholder_path)
                
                # 修改TEX内容，将缺失的图片替换为占位图形
                old_pattern = f"\\includegraphics[{{{img_path}}}]"
                new_pattern = f"\\includegraphics[{{images/placeholder_{img_filename}.png}}]"
                modified_tex_content = modified_tex_content.replace(f"{{{img_path}}}", f"{{images/placeholder_{img_filename}.png}}")
                
                self.logger.info(f"已替换缺失图片 {img_path} 为占位图形 placeholder_{img_filename}.png")
        else:
            # 如果没有缺失图片，仍然修改TEX文件中的图片路径
            modified_tex_content = tex_content
            for img_path in matches:
                if not img_path.startswith("images/"):
                    img_filename = os.path.basename(img_path)
                    new_path = f"images/{img_filename}"
                    modified_tex_content = modified_tex_content.replace(f"{{{img_path}}}", f"{{{new_path}}}")
        
        # 保存修改后的TEX文件
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(modified_tex_content)
    
    def _create_placeholder_image(self, output_path, width=400, height=300):
        """
        创建一个占位图像
        
        Args:
            output_path: 输出图像路径
            width: 图像宽度
            height: 图像高度
        """
        try:
            # 尝试导入PIL
            from PIL import Image, ImageDraw, ImageFont
            
            # 创建一个新的RGB图像，背景色为浅青色
            image = Image.new('RGB', (width, height), color=(200, 240, 240))
            draw = ImageDraw.Draw(image)
            
            # 绘制边框
            draw.rectangle([(0, 0), (width-1, height-1)], outline=(100, 150, 150), width=2)
            
            # 添加文本
            try:
                # 尝试使用默认字体
                font = ImageFont.truetype("Arial", 24)
            except:
                try:
                    # 如果找不到Arial，尝试使用默认字体
                    font = ImageFont.load_default()
                except:
                    font = None
                    
            text = "图像占位符"
            if font:
                # 计算文本大小
                text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:4]
                # 计算文本位置（居中）
                text_x = (width - text_width) // 2
                text_y = (height - text_height) // 2
                # 绘制文本
                draw.text((text_x, text_y), text, fill=(50, 100, 100), font=font)
            else:
                # 如果无法加载字体，简单地在中央绘制文本
                draw.text((width//2 - 50, height//2 - 10), text, fill=(50, 100, 100))
            
            # 保存图像
            image.save(output_path)
            self.logger.info(f"已创建占位图像: {output_path}")
            
        except ImportError:
            self.logger.warning("无法导入PIL库，无法创建占位图像")
            
            # 创建一个简单的空白PNG文件
            try:
                with open(output_path, 'wb') as f:
                    # 最小的有效PNG文件（1x1像素，透明）
                    f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
                self.logger.info(f"已创建简单占位图像: {output_path}")
            except Exception as e:
                self.logger.error(f"创建占位图像失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"创建占位图像时出错: {str(e)}")
    
    def _extract_error_message(self, log_output: str) -> str:
        """
        从编译日志中提取错误信息
        
        Args:
            log_output: 编译日志输出
            
        Returns:
            str: 提取的错误信息
        """
        # 查找LaTeX错误
        error_patterns = [
            r"! LaTeX Error: (.*?)\n",
            r"! Package (.*?) Error: (.*?)\n",
            r"! Undefined control sequence\.\n\\([^\n]*)",
            r"! Missing (.*?) inserted\.",
            r"! Package tikz Error: (.*?)\n",
            r"! I can't find file `(.*?)'"
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, log_output, re.MULTILINE)
            if matches:
                if isinstance(matches[0], tuple):
                    if len(matches[0]) == 2:  # 如 Package Error
                        return f"{matches[0][0]} Error: {matches[0][1]}"
                    else:
                        return " ".join(matches[0])
                else:
                    return matches[0]
        
        # 如果没有找到具体错误，查找警告
        warning_pattern = r"LaTeX Warning: (.*?)\n"
        warning_matches = re.findall(warning_pattern, log_output)
        if warning_matches:
            return f"警告: {warning_matches[0]}"
        
        # 返回空字符串表示未找到明确的错误
        return ""
    
    def fix_tex_code(self, tex_code: str, error_message: str, model) -> str:
        """
        使用语言模型修复TEX代码
        
        Args:
            tex_code: 原始TEX代码
            error_message: 编译错误信息
            model: 语言模型实例
            
        Returns:
            str: 修复后的TEX代码
        """
        try:
            from langchain.prompts import ChatPromptTemplate
            
            # 如果是中文且有字体问题，添加字体信息
            font_info = ""
            if self.language == "zh" and self.available_fonts and ("font" in error_message.lower() or "字体" in error_message):
                font_info = f"""
                系统中可用的中文字体有：
                {', '.join(self.available_fonts[:10]) if len(self.available_fonts) > 10 else ', '.join(self.available_fonts)}
                
                请使用上述字体之一，例如：
                \\setCJKmainfont{{{self.available_fonts[0]}}}
                
                如果没有合适的中文字体，请尝试使用更通用的方式：
                \\usepackage{{CJKutf8}}
                \\begin{{CJK}}{{UTF8}}{{gbsn}}
                ...
                \\end{{CJK}}
                """
            
            prompt = ChatPromptTemplate.from_template("""
            你是一位专业的LaTeX专家，尤其擅长修复Beamer演示文稿中的错误。请根据以下编译错误信息，修复提供的LaTeX代码：

            ## 编译错误信息：
            {error_message}

            {font_info}

            ## 当前LaTeX代码：
            ```latex
            {tex_code}
            ```

            请分析错误原因，并提供修复后的完整LaTeX代码。确保修复后的代码能够正确编译。只返回完整的修复后代码，不需要任何解释。
            """)
            
            # 调用LLM
            chain = prompt | model
            response = chain.invoke({
                "error_message": error_message,
                "tex_code": tex_code,
                "font_info": font_info
            })
            
            # 提取修复后的代码
            fixed_code = response.content if hasattr(response, 'content') else str(response)
            
            # 清理代码（移除不必要的标记）
            if "```" in fixed_code:
                pattern = r"```(?:latex|tex)?(.*?)```"
                matches = re.findall(pattern, fixed_code, re.DOTALL)
                if matches:
                    fixed_code = "\n".join(matches)
                else:
                    # 如果没有匹配到，尝试清理开头和结尾的```
                    fixed_code = re.sub(r"^```(?:latex|tex)?\n", "", fixed_code)
                    fixed_code = re.sub(r"\n```$", "", fixed_code)
            
            return fixed_code.strip()
        except Exception as e:
            self.logger.error(f"修复TEX代码时出错: {str(e)}")
            return tex_code  # 返回原始代码


# 便捷函数
def validate_tex(tex_file: str, output_dir: str = "output", language: str = "en") -> Tuple[bool, str, Optional[str]]:
    """
    验证TEX文件能否成功编译（便捷函数）
    
    Args:
        tex_file: TEX文件路径
        output_dir: 输出目录
        language: 文档语言，zh为中文，en为英文
        
    Returns:
        Tuple[bool, str, Optional[str]]: (是否成功, 错误信息或成功信息, 生成的PDF路径)
    """
    validator = TexValidator(output_dir=output_dir, language=language)
    return validator.validate(tex_file) 