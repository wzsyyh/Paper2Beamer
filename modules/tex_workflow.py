"""
TEX 工作流模块：负责从演示计划生成 TEX 文件并编译
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

# 加载补丁
from dotenv import load_dotenv
from patch_openai import patch_langchain_openai, patch_openai_client

# 尝试加载环境变量
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("env.local"):
    load_dotenv("env.local")

# 应用OpenAI客户端补丁
patch_openai_client()
patch_langchain_openai()

# 导入模块
from modules.tex_generator import TexGenerator
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
        初始化TEX工作流
        
        Args:
            presentation_plan_path: 演示计划JSON文件路径
            output_dir: 输出目录
            model_name: 要使用的语言模型名称
            temperature: 模型生成的随机性程度
            api_key: OpenAI API密钥
            language: 输出语言，zh为中文，en为英文
            theme: Beamer主题，如Madrid, Berlin, Singapore等
            max_retries: 编译失败时的最大重试次数
        """
        self.presentation_plan_path = presentation_plan_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.language = language
        self.theme = theme
        self.max_retries = max_retries
        
        # 创建日志记录器
        self.logger = logging.getLogger(__name__)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化模型
        self._init_model()
    
    def _init_model(self):
        """初始化语言模型"""
        self.tex_generator = TexGenerator(
            presentation_plan_path=self.presentation_plan_path,
            output_dir=self.output_dir,
            model_name=self.model_name,
            temperature=self.temperature,
            api_key=self.api_key,
            language=self.language,
            theme=self.theme
        )
        # 获取 session_id
        session_id = os.path.basename(self.output_dir)
        self.tex_validator = TexValidator(
            output_dir=self.output_dir,
            language=self.language,
            session_id=session_id
        )
    
    def process(self) -> Tuple[bool, str, Optional[str]]:
        """
        执行TEX工作流
        
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 信息, 生成的PDF路径)
        """
        try:
            # 步骤1：加载演示计划
            self.logger.info("加载演示计划...")
            presentation_plan = self._load_presentation_plan()
            if not presentation_plan:
                return False, "无法加载演示计划", None
                
            # 步骤2: 预处理图片（如有必要）
            self._preprocess_images(presentation_plan)
            
            # 步骤3：生成初始TEX代码
            self.logger.info("生成初始TEX代码...")
            tex_code = self.tex_generator.generate_tex()
            if not tex_code:
                return False, "TEX代码生成失败", None
                
            # 保存TEX代码
            output_tex = os.path.join(self.output_dir, "output.tex")
            with open(output_tex, 'w', encoding='utf-8') as f:
                f.write(tex_code)
            self.logger.info(f"TEX代码已保存至: {output_tex}")
            
            # 步骤4：验证和编译TEX代码
            success = False
            pdf_path = None
            error_message = ""
            
            for attempt in range(1, self.max_retries + 1):
                self.logger.info(f"开始第 {attempt}/{self.max_retries} 次验证...")
                
                # 验证并编译
                validate_success, validate_message, output_pdf = self.tex_validator.validate(output_tex)
                
                if validate_success:
                    success = True
                    pdf_path = output_pdf
                    self.logger.info(f"TEX代码验证成功: {validate_message}")
                    break
                else:
                    self.logger.warning(f"TEX代码验证失败: {validate_message}")
                    error_message = validate_message
                    
                    # 最后一次尝试不需要修复
                    if attempt < self.max_retries:
                        # 尝试修复TEX代码
                        self.logger.info("尝试修复TEX代码...")
                        
                        # 读取当前TEX代码
                        with open(output_tex, 'r', encoding='utf-8') as f:
                            current_tex_code = f.read()
                        
                        # 使用验证器的修复方法
                        fixed_tex_code = self.tex_validator.fix_tex_code(
                            current_tex_code, 
                            error_message,
                            self.tex_generator.llm
                        )
                        
                        # 保存修复后的代码
                        with open(output_tex, 'w', encoding='utf-8') as f:
                            f.write(fixed_tex_code)
                        
                        self.logger.info(f"已保存修复后的代码: {output_tex}")
                        
                        # 等待1秒再次尝试编译
                        time.sleep(1)
                        
            if success:
                return True, "TEX生成和编译成功", pdf_path
            else:
                return False, f"经过 {self.max_retries} 次尝试，仍然无法修复TEX代码", None
                
        except Exception as e:
            self.logger.error(f"TEX工作流执行出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"TEX工作流执行出错: {str(e)}", None
    
    def _load_presentation_plan(self) -> Dict[str, Any]:
        """加载演示计划"""
        try:
            with open(self.presentation_plan_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载演示计划失败: {str(e)}")
            return {}
    
    def _preprocess_images(self, presentation_plan: Dict[str, Any]):
        """
        预处理演示计划中的图片引用
        
        Args:
            presentation_plan: 演示计划
        """
        slides = presentation_plan.get("slides_plan", [])
        
        # 获取session_id
        session_id = os.path.basename(os.path.dirname(self.presentation_plan_path))
        
        # 为所有幻灯片上的图片引用创建占位图像
        for slide in slides:
            if not slide.get("includes_figure", False):
                continue
                
            fig_ref = slide.get("figure_reference", {})
            if not fig_ref:
                continue
                
            # 检查图片路径
            src = fig_ref.get("path", "")
            if not src:
                continue
                
            # 查找图片文件
            found = False
            
            # 检查images目录
            images_dir = os.path.join("output", "images", session_id)
            if os.path.exists(images_dir) and os.path.isdir(images_dir):
                # 从路径中提取文件名
                filename = os.path.basename(src)
                if not filename:
                    continue
                    
                src_path = os.path.join(images_dir, filename)
                
                if os.path.exists(src_path) and os.path.isfile(src_path):
                    found = True
                    # 更新图片路径
                    fig_ref["path"] = f"images/{filename}"
                    self.logger.info(f"找到图片: {src_path}")
            
            # 如果图片未找到，创建占位图
            if not found:
                self.logger.warning(f"未找到图片: {src}")
                
                # 创建占位图像
                images_dir = os.path.join("output", "images", session_id)
                os.makedirs(images_dir, exist_ok=True)
                
                # 生成占位图文件名
                placeholder_name = f"placeholder_{os.path.basename(src)}.png"
                placeholder_path = os.path.join(images_dir, placeholder_name)
                
                # 创建占位图像
                try:
                    # 创建一个简单的占位图像
                    width, height = 640, 480
                    image = Image.new('RGB', (width, height), color=(200, 240, 240))
                    draw = ImageDraw.Draw(image)
                    
                    # 绘制边框
                    draw.rectangle([(0, 0), (width-1, height-1)], outline=(100, 150, 150), width=2)
                    
                    # 添加文本
                    try:
                        font = ImageFont.truetype("Arial", 24)
                    except:
                        try:
                            font = ImageFont.load_default()
                        except:
                            font = None
                    
                    # 添加标题文本
                    title_text = "找不到图片"
                    if font:
                        draw.text((width//2 - 80, height//2 - 40), title_text, fill=(50, 100, 100), font=font)
                    else:
                        draw.text((width//2 - 60, height//2 - 40), title_text, fill=(50, 100, 100))
                    
                    # 添加文件名文本
                    file_text = f"原始路径: {src}"
                    if font:
                        # 使用较小的字体
                        try:
                            small_font = ImageFont.truetype("Arial", 16)
                        except:
                            small_font = font
                        draw.text((width//2 - 150, height//2 + 20), file_text, fill=(50, 100, 100), font=small_font)
                    else:
                        draw.text((width//2 - 150, height//2 + 20), file_text, fill=(50, 100, 100))
                    
                    # 保存图像
                    image.save(placeholder_path)
                    self.logger.info(f"已创建占位图像: {placeholder_path}")
                    
                    # 更新图片路径
                    fig_ref["path"] = f"images/{placeholder_name}"
                except Exception as e:
                    self.logger.error(f"创建占位图像失败: {str(e)}")
                    # 如果创建占位图失败，删除图片引用
                    slide["includes_figure"] = False
                    slide["figure_reference"] = None
        
        # 保存更新后的演示计划
        try:
            with open(self.presentation_plan_path, 'w', encoding='utf-8') as f:
                json.dump(presentation_plan, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"保存更新后的演示计划失败: {str(e)}")

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
    max_retries: int = 3
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
    
    return workflow.process()

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
    session_id = f"revision_{int(time.time())}"
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
        
        # 初始化TEX验证器
        validator = TexValidator(output_dir=session_output_dir, language=language)
        
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
        return False, f"修订版TEX工作流执行出错: {str(e)}", None 