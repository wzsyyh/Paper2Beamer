#!/usr/bin/env python3
"""
论文到Beamer转换工具 - Gradio Web界面
"""

import os
import sys
import json
import time
import tempfile
import logging
import gradio as gr
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import re

# 加载补丁
from patch_openai import patch_openai_client, patch_langchain_openai

# 加载环境变量
from dotenv import load_dotenv
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("env.local"):
    load_dotenv("env.local")

# 应用补丁
patch_openai_client()
patch_langchain_openai()

# 导入模块
from modules.pdf_parser import extract_pdf_content
from modules.presentation_planner import generate_presentation_plan, PresentationPlanner
from modules.tex_workflow import run_tex_workflow, run_revision_tex_workflow

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 确保输出目录存在
os.makedirs("output", exist_ok=True)
os.makedirs("output/raw", exist_ok=True)
os.makedirs("output/plan", exist_ok=True)
os.makedirs("output/tex", exist_ok=True)
os.makedirs("static/themes", exist_ok=True)

# 定义可用的Beamer主题
AVAILABLE_THEMES = [
    "Madrid", "Berlin", "Singapore", "Copenhagen", "Warsaw", 
    "AnnArbor", "Darmstadt", "Dresden", "Frankfurt", "Ilmenau", 
    "CambridgeUS", "Boadilla", "Pittsburgh", "Rochester"
]

# 存储当前会话的规划器实例
active_planners = {}

# 主题预览图片路径
def get_theme_preview_path(theme_name):
    """获取主题预览图片路径，如果不存在则返回占位图片路径"""
    preview_path = os.path.join("static", "themes", f"{theme_name}.png")
    if os.path.exists(preview_path):
        return preview_path
    else:
        # 返回占位图片路径
        return os.path.join("static", "themes", "placeholder.png")

def update_theme_preview(theme_name):
    """更新主题预览图片"""
    preview_path = get_theme_preview_path(theme_name)
    return preview_path

def process_pdf(pdf_file, language="zh", model_name="gpt-4o", theme="Madrid", max_retries=5):
    """
    处理PDF文件，生成Beamer幻灯片
    
    Args:
        pdf_file: 上传的PDF文件路径
        language: 输出语言，zh为中文，en为英文
        model_name: 要使用的语言模型名称
        theme: Beamer主题，如Madrid, Berlin, Singapore等
        max_retries: 编译失败时的最大重试次数
        
    Returns:
        Tuple[str, str, List[str], str]: (状态信息, 生成的PDF文件路径, 日志消息列表, 会话ID)
    """
    # 检查API密钥
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "错误：未设置OPENAI_API_KEY环境变量", None, ["未设置OPENAI_API_KEY环境变量，请检查环境配置"], None
    
    # 使用唯一的会话ID来区分不同的请求
    session_id = f"{int(time.time())}"
    logs = []
    
    # 创建输出目录
    raw_dir = os.path.join("output", "raw", session_id)
    plan_dir = os.path.join("output", "plan", session_id)
    tex_dir = os.path.join("output", "tex", session_id)
    img_dir = os.path.join("output", "images", session_id)
    
    # 创建目录
    for dir_path in [raw_dir, plan_dir, tex_dir, img_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    try:
        # 步骤1: 提取PDF内容
        log_message = "步骤1: 提取PDF内容..."
        logger.info(log_message)
        logs.append(log_message)
        
        # 提取PDF内容
        raw_content, raw_content_path = extract_pdf_content(pdf_file, raw_dir, cleanup_temp=False)
        if not raw_content:
            log_message = "PDF内容提取失败"
            logger.error(log_message)
            logs.append(log_message)
            return "错误：PDF内容提取失败", None, logs, None
        
        log_message = f"PDF内容已保存到: {raw_content_path}"
        logger.info(log_message)
        logs.append(log_message)
        
        # 步骤2: 生成演示计划
        log_message = "步骤2: 生成演示计划..."
        logger.info(log_message)
        logs.append(log_message)
        
        # 直接从原始内容生成演示计划，并获取规划器实例
        presentation_plan, plan_path, planner = generate_presentation_plan(
            raw_content_path=raw_content_path,
            output_dir=plan_dir,
            model_name=model_name,
            language=language
        )
        
        if not presentation_plan:
            log_message = "演示计划生成失败"
            logger.error(log_message)
            logs.append(log_message)
            return "错误：演示计划生成失败", None, logs, None
        
        # 保存规划器实例，以便后续对话使用
        active_planners[session_id] = planner
        
        log_message = f"演示计划已保存到: {plan_path}"
        logger.info(log_message)
        logs.append(log_message)
        
        # 步骤3: 运行TEX工作流（生成TEX并编译）
        log_message = "步骤3: 生成和编译TEX..."
        logger.info(log_message)
        logs.append(log_message)
        
        success, message, pdf_path = run_tex_workflow(
            presentation_plan_path=plan_path,
            output_dir=tex_dir,
            model_name=model_name,
            language=language,
            theme=theme,
            max_retries=max_retries
        )
        
        if success:
            log_message = f"TEX生成和编译成功: {message}"
            logger.info(log_message)
            logs.append(log_message)
            
            log_message = f"生成的PDF文件: {pdf_path}"
            logger.info(log_message)
            logs.append(log_message)
            
            # 不再清理临时图片文件，保留它们以便后续修订使用
            
            return "成功：幻灯片生成完成", pdf_path, logs, session_id
        else:
            log_message = f"TEX生成和编译失败: {message}"
            logger.error(log_message)
            logs.append(log_message)
            
            # 即使编译失败，也返回生成的TEX文件，以便用户查看
            tex_file = os.path.join(tex_dir, "output.tex")
            if os.path.exists(tex_file):
                logs.append(f"TEX文件已生成，您可以手动编译: {tex_file}")
                return "部分成功：TEX文件已生成，但编译失败", tex_file, logs, session_id
            else:
                return "错误：TEX文件生成失败", None, logs, session_id
    
    except Exception as e:
        log_message = f"处理PDF时出错: {str(e)}"
        logger.error(log_message)
        logs.append(log_message)
        
        # 打印完整的错误堆栈
        import traceback
        error_stack = traceback.format_exc()
        logger.error(error_stack)
        logs.append(error_stack)
        
        return "错误：处理PDF时出现异常", None, logs, None

def process_and_return(pdf_file, language, model_name, theme, max_retries):
    """Gradio界面调用的处理函数"""
    status, result_path, logs, session_id = process_pdf(pdf_file, language, model_name, theme, max_retries)
    logs_text = "\n".join(logs)
    
    # 返回处理结果
    if result_path and os.path.exists(result_path):
        file_extension = os.path.splitext(result_path)[1].lower()
        if file_extension == ".pdf":
            return status, result_path, logs_text, result_path, session_id or ""
        else:
            # 如果是TEX文件，返回文本内容
            with open(result_path, 'r', encoding='utf-8') as f:
                tex_content = f.read()
            return status, tex_content, logs_text, None, session_id or ""
    else:
        return status, "没有生成任何输出文件", logs_text, None, session_id or ""

def chat_with_planner(session_id, user_message, chat_history):
    """
    与演示计划生成器进行对话，优化幻灯片内容
    
    Args:
        session_id: 会话ID
        user_message: 用户输入的消息
        chat_history: 聊天历史记录
    
    Returns:
        Tuple: 更新后的聊天历史记录，更新后的演示计划
    """
    # 检查是否有有效的规划器实例
    if not session_id or session_id not in active_planners:
        return chat_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": "错误：找不到有效的会话。请先上传PDF并生成初始演示计划。"}
        ], None
    
    # 获取规划器实例
    planner = active_planners[session_id]
    
    try:
        # 处理用户消息
        response, updated_plan = planner.continue_conversation(user_message)
        
        # 保存更新后的计划
        if updated_plan:
            plan_dir = os.path.join("output", "plan", session_id)
            plan_path = planner.save_presentation_plan(updated_plan)
            
            # 更新聊天历史
            return chat_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": response}
            ], updated_plan
        else:
            return chat_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": "处理反馈时出现问题，无法更新演示计划。"}
            ], None
    
    except Exception as e:
        logger.error(f"对话处理出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return chat_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": f"处理反馈时出错: {str(e)}"}
        ], None

def regenerate_pdf(session_id, theme, chat_history):
    """
    根据更新后的演示计划重新生成PDF
    
    Args:
        session_id: 会话ID
        theme: Beamer主题
        chat_history: 聊天历史记录
    
    Returns:
        Tuple: 状态信息，结果路径，日志消息，PDF路径
    """
    # 检查是否有有效的规划器实例
    if not session_id or session_id not in active_planners:
        return "错误：找不到有效的会话", None, "请先上传PDF并生成初始演示计划", None
    
    # 获取规划器实例和计划
    planner = active_planners[session_id]
    presentation_plan = planner.presentation_plan
    
    if not presentation_plan:
        return "错误：没有可用的演示计划", None, "无法找到有效的演示计划", None
    
    # 准备输出目录
    tex_dir = os.path.join("output", "tex", session_id)
    os.makedirs(tex_dir, exist_ok=True)
    
    # 保存更新后的计划
    plan_dir = os.path.join("output", "plan", session_id)
    plan_path = planner.save_presentation_plan(presentation_plan)
    
    logs = []
    log_message = f"使用更新后的演示计划重新生成PDF..."
    logger.info(log_message)
    logs.append(log_message)
    
    try:
        # 运行TEX工作流
        success, message, pdf_path = run_tex_workflow(
            presentation_plan_path=plan_path,
            output_dir=tex_dir,
            model_name=planner.model_name,
            language=planner.language,
            theme=theme,
            max_retries=5  # 默认重试次数
        )
        
        if success:
            log_message = f"TEX生成和编译成功: {message}"
            logger.info(log_message)
            logs.append(log_message)
            
            log_message = f"生成的PDF文件: {pdf_path}"
            logger.info(log_message)
            logs.append(log_message)
            
            return "成功：幻灯片更新完成", pdf_path, "\n".join(logs), pdf_path
        else:
            log_message = f"TEX生成和编译失败: {message}"
            logger.error(log_message)
            logs.append(log_message)
            
            # 即使编译失败，也返回生成的TEX文件
            tex_file = os.path.join(tex_dir, "output.tex")
            if os.path.exists(tex_file):
                with open(tex_file, 'r', encoding='utf-8') as f:
                    tex_content = f.read()
                logs.append(f"TEX文件已生成，您可以手动编译: {tex_file}")
                return "部分成功：TEX文件已生成，但编译失败", tex_content, "\n".join(logs), None
            else:
                return "错误：TEX文件生成失败", None, "\n".join(logs), None
    
    except Exception as e:
        log_message = f"重新生成PDF时出错: {str(e)}"
        logger.error(log_message)
        logs.append(log_message)
        
        # 打印完整的错误堆栈
        import traceback
        error_stack = traceback.format_exc()
        logger.error(error_stack)
        logs.append(error_stack)
        
        return "错误：重新生成PDF时出现异常", None, "\n".join(logs), None

def revise_presentation(session_id, feedback, chat_history):
    """
    根据用户反馈修订演示文稿
    
    Args:
        session_id: 会话ID
        feedback: 用户反馈
        chat_history: 聊天历史记录
        
    Returns:
        Tuple: 更新后的聊天历史记录，修订后的PDF路径，状态信息
    """
    # 检查是否有有效的会话
    if not session_id or not os.path.exists(os.path.join("output", "tex", session_id)):
        return chat_history + [
            {"role": "user", "content": feedback},
            {"role": "assistant", "content": "错误：找不到有效的会话。请先上传PDF并生成初始演示文稿。"}
        ], None, "错误：找不到有效的会话"
    
    # 查找会话目录中的原始计划和TEX文件
    plan_dir = os.path.join("output", "plan", session_id)
    tex_dir = os.path.join("output", "tex", session_id)
    
    # 查找计划文件
    plan_files = [f for f in os.listdir(plan_dir) if f.endswith(".json")]
    if not plan_files:
        return chat_history + [
            {"role": "user", "content": feedback},
            {"role": "assistant", "content": "错误：找不到演示计划文件。"}
        ], None, "错误：找不到演示计划文件"
    
    # 使用最新的计划文件
    plan_file = os.path.join(plan_dir, plan_files[0])
    
    # 查找TEX文件
    tex_files = [f for f in os.listdir(tex_dir) if f.endswith(".tex")]
    if not tex_files:
        return chat_history + [
            {"role": "user", "content": feedback},
            {"role": "assistant", "content": "错误：找不到TEX文件。"}
        ], None, "错误：找不到TEX文件"
    
    # 使用最新的TEX文件
    tex_file = os.path.join(tex_dir, tex_files[0])
    
    # 创建修订版输出目录
    revision_dir = os.path.join(tex_dir, f"revision_{int(time.time())}")
    os.makedirs(revision_dir, exist_ok=True)
    
    # 获取主题（从TEX文件中提取）
    theme = "Madrid"  # 默认主题
    try:
        with open(tex_file, 'r', encoding='utf-8') as f:
            tex_content = f.read()
            theme_match = re.search(r'\\usetheme{([^}]+)}', tex_content)
            if theme_match:
                theme = theme_match.group(1)
    except Exception as e:
        logger.warning(f"提取主题时出错: {str(e)}")
    
    # 调用修订版TEX工作流
    logs = []
    log_message = f"开始基于用户反馈修订演示文稿..."
    logger.info(log_message)
    logs.append(log_message)
    
    # 运行修订版TEX工作流
    success, message, pdf_path = run_revision_tex_workflow(
        original_plan_path=plan_file,
        previous_tex_path=tex_file,
        user_feedback=feedback,
        output_dir=revision_dir,
        model_name="gpt-4o",  # 使用高质量模型进行修订
        language="zh",
        theme=theme,
        max_retries=5
    )
    
    # 处理结果
    if success:
        log_message = f"演示文稿修订成功: {message}"
        logger.info(log_message)
        logs.append(log_message)
        
        # 将新生成的TEX文件复制到主TEX目录，以便后续修订
        try:
            import shutil
            new_tex_file = os.path.join(revision_dir, os.path.basename(pdf_path).replace(".pdf", ".tex"))
            if os.path.exists(new_tex_file):
                target_tex = os.path.join(tex_dir, f"output_revised_{int(time.time())}.tex")
                shutil.copy2(new_tex_file, target_tex)
                log_message = f"已保存修订版TEX文件: {target_tex}"
                logger.info(log_message)
                logs.append(log_message)
        except Exception as e:
            log_message = f"复制修订版TEX文件时出错: {str(e)}"
            logger.warning(log_message)
            logs.append(log_message)
        
        # 更新聊天历史
        ai_response = "已根据您的反馈修订演示文稿。您可以下载查看，或继续提供更多反馈。"
        updated_history = chat_history + [
            {"role": "user", "content": feedback},
            {"role": "assistant", "content": ai_response}
        ]
        
        return updated_history, pdf_path, "成功：演示文稿已修订"
    else:
        log_message = f"修订失败: {message}"
        logger.error(log_message)
        logs.append(log_message)
        
        # 更新聊天历史
        ai_response = f"修订失败: {message}\n\n{''.join(logs)}"
        updated_history = chat_history + [
            {"role": "user", "content": feedback},
            {"role": "assistant", "content": ai_response}
        ]
        
        return updated_history, None, "错误：修订失败"

def create_ui():
    """创建Gradio界面"""
    
    # 创建主界面
    with gr.Blocks(title="论文到Beamer转换工具", theme=gr.themes.Soft()) as demo:
        # 标题
        gr.Markdown("# 论文到Beamer转换工具")
        gr.Markdown("将学术论文PDF自动转换为Beamer演示幻灯片")
        
        # 隐藏的会话ID组件
        session_id = gr.Textbox(visible=False)
        
        # 创建标签页
        with gr.Tabs():
            # 主处理标签页
            with gr.Tab("转换PDF"):
                with gr.Row():
                    with gr.Column(scale=1):
                        # 输入区域
                        with gr.Group():
                            gr.Markdown("### 输入设置")
                            pdf_file = gr.File(
                                label="上传PDF文件",
                                file_types=[".pdf"],
                                type="filepath"
                            )
                            
                            language = gr.Radio(
                                label="演示语言",
                                choices=["zh", "en"],
                                value="zh"
                            )
                            
                            model_name = gr.Dropdown(
                                label="使用的语言模型",
                                choices=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                                value="gpt-4o"
                            )
                            
                            with gr.Row():
                                theme = gr.Dropdown(
                                    label="Beamer主题",
                                    choices=AVAILABLE_THEMES,
                                    value="Madrid"
                                )
                                
                                theme_preview = gr.Image(
                                    label="主题预览", 
                                    value=get_theme_preview_path("Madrid"),
                                    height=150
                                )
                            
                            # 主题变化时更新预览
                            theme.change(
                                fn=update_theme_preview,
                                inputs=theme,
                                outputs=theme_preview
                            )
                            
                            max_retries = gr.Slider(
                                label="最大编译尝试次数",
                                minimum=1,
                                maximum=10,
                                step=1,
                                value=5
                            )
                            
                            # 提交按钮
                            submit_button = gr.Button("生成演示幻灯片", variant="primary")
                    
                    with gr.Column(scale=2):
                        # 输出区域
                        with gr.Group():
                            gr.Markdown("### 输出结果")
                            status_text = gr.Textbox(label="状态", value="准备就绪")
                            logs_text = gr.Textbox(label="日志", lines=10)
                            output_tex = gr.Textbox(label="TEX代码", visible=False, lines=10)
                            result_file = gr.File(label="生成的演示文稿")
                
                # 处理函数
                submit_button.click(
                    fn=process_and_return,
                    inputs=[pdf_file, language, model_name, theme, max_retries],
                    outputs=[status_text, output_tex, logs_text, result_file, session_id]
                )
                
                # 修订功能（多轮对话）
                with gr.Group(visible=True):
                    gr.Markdown("### 修改和优化")
                    
                    with gr.Row():
                        with gr.Column(scale=2):
                            revision_input = gr.Textbox(
                                label="提供修改建议",
                                placeholder="请描述您希望对演示文稿进行的修改，例如：'请调整第3页的内容，添加更多关于方法的细节'",
                                lines=3
                            )
                            revision_button = gr.Button("提交修改建议")
                        
                        with gr.Column(scale=3):
                            chat_history = gr.Chatbot(
                                label="修改对话历史",
                                height=300,
                                type="messages"
                            )
                    
                    # 添加修订功能的响应
                    revision_button.click(
                        fn=revise_presentation,
                        inputs=[session_id, revision_input, chat_history],
                        outputs=[chat_history, result_file, status_text]
                    ).then(
                        fn=lambda: "",  # 清空输入框
                        inputs=None,
                        outputs=revision_input
                    )
            
            # 关于标签页
            with gr.Tab("关于"):
                gr.Markdown("""
                ## 论文到Beamer转换工具
                
                **论文到Beamer转换工具**是一个利用人工智能技术，将学术论文PDF自动转换为Beamer演示幻灯片的工具。
                
                ### 主要功能
                
                1. **PDF内容提取**：自动从PDF中提取文本、图像和结构信息
                2. **智能内容分析**：识别论文的标题、作者、摘要、章节结构和关键图表
                3. **演示计划生成**：根据论文内容生成结构化的演示计划
                4. **Beamer代码生成**：生成完整的LaTeX Beamer代码
                5. **多轮对话修改**：支持通过自然语言反馈修改生成的幻灯片
                6. **多种主题支持**：支持多种Beamer主题
                7. **中英文支持**：支持生成中文和英文演示文稿
                
                ### 使用指南
                
                1. 上传学术论文PDF文件
                2. 选择演示语言（中文或英文）
                3. 选择使用的语言模型（建议使用gpt-4o）
                4. 选择Beamer主题
                5. 点击"生成演示幻灯片"按钮
                6. 等待处理完成，下载生成的PDF文件
                7. 如需修改，在"提供修改建议"中输入您的反馈并提交
                
                ### 技术支持
                
                - 本工具使用OpenAI的API，需要设置有效的OPENAI_API_KEY环境变量
                - 编译Beamer需要安装LaTeX环境（推荐使用TeX Live或MiKTeX）
                - 支持处理中英文论文，并生成中英文演示文稿
                
                ### 开源信息
                
                本工具是开源项目，采用MIT许可证。欢迎贡献代码和提出建议。
                
                GitHub仓库：[https://github.com/wzsyyh/paper-to-beamer](https://github.com/wzsyyh/paper-to-beamer)
                
                二次开发时需要提及本仓库。用于商业用途的二次开发需要联系原作者获得授权。
                """)
        
        # 示例
        # gr.Examples(
        #     examples=[
        #         ["examples/paper1.pdf", "zh", "gpt-4o", "Madrid", 5],
        #         ["examples/paper2.pdf", "en", "gpt-4o", "Berlin", 5]
        #     ],
        #     inputs=[pdf_file, language, model_name, theme, max_retries],
        #     outputs=[status_text, output_tex, logs_text, result_file, session_id],
        #     fn=process_and_return,
        #     cache_examples=False
        # )
    
    return demo

def test_with_example():
    """测试模式，使用示例PDF自动生成演示文稿"""
    import sys
    
    # 检查命令行参数
    if len(sys.argv) < 3 or sys.argv[1] != "--test":
        return False
        
    # 获取示例PDF路径
    example_pdf = sys.argv[2]
    
    # 检查文件是否存在
    if not os.path.exists(example_pdf):
        print(f"错误：示例PDF文件不存在: {example_pdf}")
        return True
    
    # 设置测试参数
    language = "zh"
    model_name = "gpt-4o"
    theme = "Madrid"
    max_retries = 5
    
    # 检查是否有其他命令行参数
    if len(sys.argv) > 3:
        # 可以添加更多参数支持，如：
        for arg in sys.argv[3:]:
            if arg.startswith("--language="):
                language = arg.split("=")[1]
            elif arg.startswith("--model="):
                model_name = arg.split("=")[1]
            elif arg.startswith("--theme="):
                theme = arg.split("=")[1]
            elif arg.startswith("--retries="):
                max_retries = int(arg.split("=")[1])
    
    print(f"测试模式：使用示例PDF自动生成演示文稿")
    print(f"PDF文件: {example_pdf}")
    print(f"语言: {language}")
    print(f"模型: {model_name}")
    print(f"主题: {theme}")
    print(f"最大重试次数: {max_retries}")
    
    # 处理PDF
    status, result_path, logs, session_id = process_pdf(example_pdf, language, model_name, theme, max_retries)
    
    # 输出结果
    print(f"\n状态: {status}")
    print(f"结果文件: {result_path}")
    print(f"会话ID: {session_id}")
    
    # 检查是否需要进行修订
    if "--revise" in sys.argv:
        revision_index = sys.argv.index("--revise")
        if revision_index < len(sys.argv) - 1:
            feedback = sys.argv[revision_index + 1]
            print(f"\n进行修订: {feedback}")
            
            # 创建空的聊天历史
            chat_history = []
            
            # 运行修订
            updated_history, revised_pdf, revision_status = revise_presentation(session_id, feedback, chat_history)
            
            # 输出修订结果
            print(f"修订状态: {revision_status}")
            print(f"修订后的PDF: {revised_pdf}")
            
            # 输出对话历史
            print("\n对话历史:")
            for message in updated_history:
                print(f"{message['role']}: {message['content']}")
                print("")
    
    return True

if __name__ == "__main__":
    # 如果命令行参数包含--test，则运行测试
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_with_example()
    else:
        # 创建并启动Web界面
        app = create_ui()
        app.launch(server_name="0.0.0.0") 