"""
TEX Workflow Module: Responsible for generating TEX files from presentation plans and compiling them
"""

import os
import json
import logging
import time
from pathlib import Path
import glob
import shutil
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import subprocess

# Load patches
from dotenv import load_dotenv
from patch_openai import patch_langchain_openai, patch_openai_client

# Try to load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("env.local"):
    load_dotenv("env.local")

# Apply OpenAI client patches
patch_openai_client()
patch_langchain_openai()

# Import modules
from modules.tex_generator import TexGenerator
from modules.direct_tex_generator import DirectTexGenerator
from modules.tex_validator import TexValidator
from modules.revision_tex_generator import generate_revised_tex, RevisionTexGenerator

class TexWorkflow:
    def __init__(
        self, 
        presentation_plan_path: str, 
        output_dir: str = "output",
        model_name: str = "gpt-4o",
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        language: str = "zh",
        theme: str = "Madrid",
        max_retries: int = 5
    ):
        """
        Initialize TEX workflow
        
        Args:
            presentation_plan_path: Presentation plan JSON file path
            output_dir: Output directory
            model_name: Language model name to use
            temperature: Randomness level of model generation
            api_key: OpenAI API key
            language: Output language, zh for Chinese, en for English
            theme: Beamer theme, such as Madrid, Berlin, Singapore etc.
            max_retries: Maximum retries when compilation fails
        """
        self.presentation_plan_path = presentation_plan_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.language = language
        self.theme = theme
        self.max_retries = max_retries
        
        # Create logger
        self.logger = logging.getLogger(__name__)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize model
        self._init_model()
    
    def _init_model(self):
        """Initialize language model"""
        self.tex_generator = TexGenerator(
            presentation_plan_path=self.presentation_plan_path,
            output_dir=self.output_dir,
            model_name=self.model_name,
            temperature=self.temperature,
            api_key=self.api_key,
            language=self.language,
            theme=self.theme
        )
        # Get session_id
        session_id = os.path.basename(self.output_dir)
        self.tex_validator = TexValidator(
            output_dir=self.output_dir,
            language=self.language,
            session_id=session_id
        )
    
    def process(self, skip_compilation: bool = False) -> Tuple[bool, str, Optional[str]]:
        """
        Execute TEX workflow
        
        Returns:
            Tuple[bool, str, Optional[str]]: (Success status, Message, Generated PDF path)
        """
        try:
            # Step 1: Load presentation plan
            self.logger.info("Loading presentation plan...")
            presentation_plan = self._load_presentation_plan()
            if not presentation_plan:
                return False, "Unable to load presentation plan", None
                
            # Step 2: Preprocess images (if necessary)
            self._preprocess_images(presentation_plan)
            
            # Step 3: Generate initial TEX code
            self.logger.info("Generating initial TEX code...")
            tex_code = self.tex_generator.generate_tex()
            if not tex_code:
                return False, "TEX code generation failed", None
                
            # Save TEX code
            output_tex = os.path.join(self.output_dir, "output.tex")
            with open(output_tex, 'w', encoding='utf-8') as f:
                f.write(tex_code)
            self.logger.info(f"TEX code saved to: {output_tex}")
            
            # Step 4: Save TEX file and optionally compile
            self.logger.info(f"TEX code saved to: {output_tex}")
            
            # If skip compilation, only return TEX file path
            if skip_compilation:
                self.logger.info("Skipping PDF compilation, only generating TEX file")
                return True, "TEX generation successful (compilation skipped)", output_tex
            
            # Step 5: Validate and compile TEX code
            success = False
            pdf_path = None
            error_message = ""
            
            for attempt in range(1, self.max_retries + 1):
                self.logger.info(f"Starting validation attempt {attempt}/{self.max_retries}...")
                
                # Validate and compile
                validate_success, validate_message, output_pdf = self.tex_validator.validate(output_tex)
                
                if validate_success:
                    success = True
                    pdf_path = output_pdf
                    self.logger.info(f"TEX code validation successful: {validate_message}")
                    break
                else:
                    self.logger.warning(f"TEX code validation failed: {validate_message}")
                    error_message = validate_message
                    
                    # Last attempt doesn't need repair
                    if attempt < self.max_retries:
                        # Try to fix TEX code
                        self.logger.info("Attempting to fix TEX code...")
                        
                        # Read current TEX code
                        with open(output_tex, 'r', encoding='utf-8') as f:
                            current_tex_code = f.read()
                        
                        # Use validator's fix method
                        fixed_tex_code = self.tex_validator.fix_tex_code(
                            current_tex_code, 
                            error_message,
                            self.tex_generator.llm
                        )
                        
                        # Save fixed code
                        with open(output_tex, 'w', encoding='utf-8') as f:
                            f.write(fixed_tex_code)
                        
                        self.logger.info(f"Fixed code saved to: {output_tex}")
                        
                        # Wait 1 second before retrying compilation
                        time.sleep(1)
                        
            if success:
                return True, "TEX generation and compilation successful", pdf_path
            else:
                return False, f"After {self.max_retries} attempts, still unable to fix TEX code", None
                
        except Exception as e:
            self.logger.error(f"TEX workflow execution error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"TEX workflow execution error: {str(e)}", None
    
    def _load_presentation_plan(self) -> Dict[str, Any]:
        """Load presentation plan"""
        try:
            with open(self.presentation_plan_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load presentation plan: {str(e)}")
            return {}
    
    def _preprocess_images(self, presentation_plan: Dict[str, Any]):
        """
        Preprocess image references in presentation plan
        
        Args:
            presentation_plan: Presentation plan
        """
        slides = presentation_plan.get("slides_plan", [])
        
        # Get session_id
        session_id = os.path.basename(os.path.dirname(self.presentation_plan_path))
        
        # Create placeholder images for all image references on slides
        for slide in slides:
            if not slide.get("includes_figure", False):
                continue
                
            fig_ref = slide.get("figure_reference", {})
            if not fig_ref:
                continue
                
            # Check image path
            src = fig_ref.get("path", "")
            if not src:
                continue
                
            # Find image file
            found = False
            
            # Check images directory
            images_dir = os.path.join("output", "images", session_id)
            if os.path.exists(images_dir) and os.path.isdir(images_dir):
                # Extract filename from path
                filename = os.path.basename(src)
                if not filename:
                    continue
                    
                src_path = os.path.join(images_dir, filename)
                
                if os.path.exists(src_path) and os.path.isfile(src_path):
                    found = True
                    # Update image path
                    fig_ref["path"] = f"images/{filename}"
                    self.logger.info(f"Found image: {src_path}")
            
            # If image not found, create placeholder
            if not found:
                self.logger.warning(f"Image not found: {src}")
                
                # Create placeholder image
                images_dir = os.path.join("output", "images", session_id)
                os.makedirs(images_dir, exist_ok=True)
                
                # Generate placeholder filename
                placeholder_name = f"placeholder_{os.path.basename(src)}.png"
                placeholder_path = os.path.join(images_dir, placeholder_name)
                
                # Create placeholder image
                try:
                    # Create a simple placeholder image
                    width, height = 640, 480
                    image = Image.new('RGB', (width, height), color=(200, 240, 240))
                    draw = ImageDraw.Draw(image)
                    
                    # Draw border
                    draw.rectangle([(0, 0), (width-1, height-1)], outline=(100, 150, 150), width=2)
                    
                    # Add text
                    try:
                        font = ImageFont.truetype("Arial", 24)
                    except:
                        try:
                            font = ImageFont.load_default()
                        except:
                            font = None
                    
                    # Add title text
                    title_text = "Image Not Found"
                    if font:
                        draw.text((width//2 - 80, height//2 - 40), title_text, fill=(50, 100, 100), font=font)
                    else:
                        draw.text((width//2 - 60, height//2 - 40), title_text, fill=(50, 100, 100))
                    
                    # Add filename text
                    file_text = f"Original path: {src}"
                    if font:
                        # Use smaller font
                        try:
                            small_font = ImageFont.truetype("Arial", 16)
                        except:
                            small_font = font
                        draw.text((width//2 - 150, height//2 + 20), file_text, fill=(50, 100, 100), font=small_font)
                    else:
                        draw.text((width//2 - 150, height//2 + 20), file_text, fill=(50, 100, 100))
                    
                    # Save image
                    image.save(placeholder_path)
                    self.logger.info(f"Created placeholder image: {placeholder_path}")
                    
                    # Update image path
                    fig_ref["path"] = f"images/{placeholder_name}"
                except Exception as e:
                    self.logger.error(f"Failed to create placeholder image: {str(e)}")
                    # If creating placeholder fails, remove image reference
                    slide["includes_figure"] = False
                    slide["figure_reference"] = None
        
        # Save updated presentation plan
        try:
            with open(self.presentation_plan_path, 'w', encoding='utf-8') as f:
                json.dump(presentation_plan, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save updated presentation plan: {str(e)}")

    def _compile_tex(self, tex_path: str) -> bool:
        """
        Compile TEX file
        
        Args:
            tex_path: TEX file path
            
        Returns:
            bool: Success status
        """
        try:
            # Get TEX file directory and filename
            tex_dir = os.path.dirname(tex_path)
            tex_basename = os.path.basename(tex_path)
            
            # Change to TEX file directory
            original_dir = os.getcwd()
            os.chdir(tex_dir)
            
            try:
                # Run compilation command
                self.logger.info(f"Running compilation command: pdflatex -interaction=nonstopmode output.tex")
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "output.tex"],
                    cwd=tex_dir,
                    capture_output=True,
                    text=True
                )
                
                # Check compilation result
                if result.returncode == 0:
                    self.logger.info("TEX code validation successful")
                    return True
                else:
                    self.logger.warning(f"TEX code validation failed: {result.stderr}")
                    return False
                
            finally:
                # Restore original directory
                os.chdir(original_dir)
                
        except Exception as e:
            self.logger.error(f"Error compiling TEX file: {str(e)}")
            return False

    def run(self) -> Tuple[bool, str, Optional[str]]:
        """
        运行 TEX 工作流 (process方法的别名)
        
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 信息, 生成的PDF路径)
        """
        self.logger.info(f"开始TEX工作流，处理演示计划: {self.presentation_plan_path}")
        return self.process()

# 便捷函数
def run_tex_workflow(
    presentation_plan_path: str, 
    output_dir: str = "output", 
    model_name: str = "gpt-4o", 
    api_key: Optional[str] = None,
    language: str = "zh",
    theme: str = "Madrid",
    max_retries: int = 3,
    skip_compilation: bool = False
) -> Tuple[bool, str, Optional[str]]:
    """
    运行TEX工作流（便捷函数）
    
    Args:
        presentation_plan_path: 演示计划JSON文件路径
        output_dir: 输出目录
        model_name: 要使用的语言模型名称
        api_key: OpenAI API密钥
        language: 输出语言，zh为中文，en为英文
        theme: Beamer主题，如Madrid, Berlin, Singapore等
        max_retries: 最大重试次数
        skip_compilation: 是否跳过PDF编译（只生成TEX文件）
        
    Returns:
        Tuple[bool, str, Optional[str]]: (是否成功, 信息, 生成的PDF路径)
    """
    workflow = TexWorkflow(
        presentation_plan_path=presentation_plan_path,
        output_dir=output_dir,
        model_name=model_name,
        api_key=api_key,
        language=language,
        theme=theme,
        max_retries=max_retries
    )
    
    return workflow.process(skip_compilation=skip_compilation)

def run_revision_tex_workflow(
    original_plan_path: str,
    previous_tex_path: str,
    user_feedback: str,
    output_dir: str = "output",
    model_name: str = "gpt-4o",
    language: str = "zh",
    theme: str = "Madrid",
    max_retries: int = 3
) -> Tuple[bool, str, Optional[str]]:
    """
    运行修订版TEX工作流：根据用户反馈生成修订版TEX并编译
    
    Args:
        original_plan_path: 原始演示计划JSON文件路径
        previous_tex_path: 先前版本的TEX文件路径
        user_feedback: 用户反馈
        output_dir: 输出目录
        model_name: 要使用的语言模型名称
        language: 输出语言，zh为中文，en为英文
        theme: Beamer主题
        max_retries: 编译失败时的最大重试次数
        
    Returns:
        Tuple[bool, str, Optional[str]]: (是否成功, 消息, 生成的PDF文件路径)
    """
    logging.info(f"开始修订TEX工作流，基于用户反馈: {user_feedback[:100]}...")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建会话特定的输出目录
    from datetime import datetime
    session_id = f"revision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_output_dir = os.path.join(output_dir, session_id)
    os.makedirs(session_output_dir, exist_ok=True)
    
    try:
        # 步骤1: 生成修订版TEX代码
        logging.info("步骤1: 根据用户反馈生成修订版TEX代码")
        
        # 初始化修订版TEX生成器
        generator = RevisionTexGenerator(
            original_plan_path=original_plan_path,
            previous_tex_path=previous_tex_path,
            output_dir=session_output_dir,
            model_name=model_name,
            language=language,
            theme=theme
        )
        
        tex_code, ai_message = generator.generate_revised_tex(user_feedback)
        
        if not tex_code:
            logging.error("生成修订版TEX代码失败")
            return False, "生成修订版TEX代码失败", None
            
        # 保存TEX代码
        tex_path = generator.save_revised_tex(tex_code)
        if not tex_path:
            logging.error("保存修订版TEX代码失败")
            return False, "保存修订版TEX代码失败", None
            
        logging.info(f"修订版TEX代码已生成: {tex_path}")
        
        # 步骤2: 编译TEX文件
        logging.info("步骤2: 编译修订版TEX文件")
        
        # 复制图片文件到会话目录
        images_dir = os.path.join(os.path.dirname(previous_tex_path), "images")
        session_images_dir = os.path.join(session_output_dir, "images")
        os.makedirs(session_images_dir, exist_ok=True)
        
        # 查找所有可能的图片源目录
        possible_image_dirs = [
            images_dir,  # 当前TEX文件同级的images目录
            os.path.join(output_dir, "images"),  # 主输出目录下的images
        ]
        
        # 添加所有会话目录下的images
        for session_dir in os.listdir(output_dir):
            session_path = os.path.join(output_dir, session_dir)
            if os.path.isdir(session_path):
                session_images = os.path.join(session_path, "images")
                if os.path.exists(session_images):
                    possible_image_dirs.append(session_images)
        
        # 记录已复制的文件，避免重复
        copied_files = set()
        
        # 从所有可能的目录复制图片
        for img_dir in possible_image_dirs:
            if os.path.exists(img_dir):
                logging.info(f"从 {img_dir} 复制图片")
                for img_path in glob.glob(os.path.join(img_dir, "*.png")) + \
                             glob.glob(os.path.join(img_dir, "*.jpg")) + \
                             glob.glob(os.path.join(img_dir, "*.pdf")):
                    img_filename = os.path.basename(img_path)
                    target_path = os.path.join(session_images_dir, img_filename)
                    
                    # 避免重复复制
                    if img_filename not in copied_files:
                        shutil.copy2(img_path, target_path)
                        copied_files.add(img_filename)
                        logging.info(f"复制图片: {img_path} -> {target_path}")
            
        logging.info(f"共复制了 {len(copied_files)} 个图片文件到会话目录: {session_images_dir}")
        
        # 不需要在revision目录下创建images子目录
        # TEX文件将直接使用相对路径引用output/images/下的图片
        
        # 初始化TEX验证器
        validator = TexValidator(output_dir=session_output_dir, language=language, session_id=session_id)
        
        # 使用验证器验证并编译TEX文件
        success = False
        pdf_path = None
        error_message = ""
        
        # 尝试多次编译
        for attempt in range(1, max_retries + 1):
            logging.info(f"开始第 {attempt}/{max_retries} 次验证...")
            
            # 验证并编译
            compile_success, compile_message, output_pdf = validator.validate(tex_path)
            
            if compile_success:
                success = True
                pdf_path = output_pdf
                logging.info(f"TEX代码验证成功: {compile_message}")
                break
            else:
                logging.warning(f"TEX代码验证失败: {compile_message}")
                error_message = compile_message
                
                # 最后一次尝试不需要修复
                if attempt < max_retries:
                    # 尝试修复TEX代码
                    logging.info("尝试修复TEX代码...")
                    
                    # 读取当前TEX代码
                    with open(tex_path, 'r', encoding='utf-8') as f:
                        current_tex_code = f.read()
                    
                    # 使用验证器的修复方法
                    fixed_tex_code = validator.fix_tex_code(
                        current_tex_code, 
                        error_message,
                        generator.llm
                    )
                    
                    # 保存修复后的代码
                    with open(tex_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_tex_code)
                    
                    logging.info(f"已保存修复后的代码: {tex_path}")
                    
                    # 等待1秒再次尝试编译
                    time.sleep(1)
        
        if not success:
            logging.error(f"编译修订版TEX文件失败: {error_message}")
            return False, f"编译修订版TEX文件失败: {error_message}", None
            
        logging.info(f"修订版TEX文件编译成功: {pdf_path}")
        
        # 返回结果
        return True, ai_message, pdf_path
        
    except Exception as e:
        logging.error(f"修订版TEX工作流执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, f"订版TEX工作流执行出错: {str(e)}", None

def run_direct_tex_workflow(
    raw_content_path: str,
    output_dir: str,
    model_name: str = "gpt-4o",
    language: str = "zh",
    theme: str = "Madrid",
    max_retries: int = 5
) -> Tuple[bool, str, str]:
    """
    运行直接从原始文本生成TEX的工作流（无Planner）

    Args:
        raw_content_path: 原始文本内容文件路径
        output_dir: 输出目录
        model_name: 使用的语言模型
        language: 输出语言
        theme: Beamer主题
        max_retries: 最大重试次数

    Returns:
        Tuple[bool, str, str]: (是否成功, 消息, 生成的PDF文件路径)
    """
    logging.info(f"开始直接TEX工作流，处理原始文本: {raw_content_path}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 步骤1: 生成TEX代码
        logging.info("步骤1: 直接从原始文本生成TEX代码...")
        generator = DirectTexGenerator(
            raw_content_path=raw_content_path,
            output_dir=output_dir,
            model_name=model_name,
            language=language,
            theme=theme,
        )
        tex_code = generator.generate_tex()
        if not tex_code:
            logging.error("直接生成TEX代码失败")
            return False, "直接生成TEX代码失败", None
        
        tex_path = generator.save_tex(tex_code)
        if not tex_path:
            logging.error("保存TEX代码失败")
            return False, "保存TEX代码失败", None
            
        logging.info(f"TEX代码已生成: {tex_path}")

        # 步骤2: 验证和编译
        logging.info("步骤2: 验证和编译TEX文件...")
        session_id = os.path.basename(os.path.dirname(raw_content_path))
        validator = TexValidator(output_dir=output_dir, language=language, session_id=session_id)
        
        success = False
        pdf_path = None
        error_message = ""

        for attempt in range(1, max_retries + 1):
            logging.info(f"开始第 {attempt}/{max_retries} 次验证...")
            compile_success, compile_message, output_pdf = validator.validate(tex_path)
            
            if compile_success:
                success = True
                pdf_path = output_pdf
                logging.info(f"TEX代码验证成功: {compile_message}")
                break
            else:
                logging.warning(f"TEX代码验证失败: {compile_message}")
                error_message = compile_message
                
                if attempt < max_retries:
                    logging.info("尝试修复TEX代码...")
                    with open(tex_path, 'r', encoding='utf-8') as f:
                        current_tex_code = f.read()
                    
                    fixed_tex_code = validator.fix_tex_code(
                        current_tex_code, 
                        error_message,
                        generator.llm
                    )
                    
                    with open(tex_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_tex_code)
                    
                    logging.info(f"已保存修复后的代码: {tex_path}")
                    time.sleep(1)
        
        if success:
            return True, "直接TEX生成和编译成功", pdf_path
        else:
            return False, f"经过 {max_retries} 次尝试，仍然无法修复TEX代码", None

    except Exception as e:
        logging.error(f"直接TEX工作流执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, f"直接TEX工作流执行出错: {str(e)}", None
