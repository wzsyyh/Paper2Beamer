#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化评估脚本：图文匹配度 (Text-Figure Coherence)
"""

import os
import sys
import subprocess
import re
import json
import logging
import base64
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import fitz  # PyMuPDF
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from tqdm import tqdm

# --- 配置 ---
# 将此路径设置为您的API密钥所在的文件
sys.path.append(str(Path(__file__).parent.parent.parent))
import patch_openai
patch_openai.patch_langchain_openai()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 核心功能 ---

def compile_latex_to_pdf(tex_path: Path) -> Optional[Path]:
    """使用 pdflatex 编译 .tex 文件为 PDF。"""
    if not tex_path.exists():
        logger.error(f"找不到 TeX 文件: {tex_path}")
        return None

    output_dir = tex_path.parent
    for _ in range(2):  # 运行两次以确保引用正确
        process = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(output_dir), str(tex_path)],
            capture_output=True, text=True
        )
        if process.returncode != 0:
            logger.error(f"LaTeX 编译失败。查看日志: {output_dir / tex_path.with_suffix('.log').name}")
            # logger.error(process.stdout)
            return None
    
    pdf_path = tex_path.with_suffix('.pdf')
    if pdf_path.exists():
        logger.info(f"成功编译 PDF: {pdf_path}")
        return pdf_path
    return None

def find_frames_with_images(tex_content: str) -> List[int]:
    """解析 TeX 内容以找到包含图片的帧（从1开始计数）。"""
    # A simple but effective way: count frames and check for \includegraphics inside.
    frame_indices = []
    frames = tex_content.split(r'\begin{frame}')
    for i, frame_content in enumerate(frames[1:], start=1):
        if r'\includegraphics' in frame_content:
            frame_indices.append(i)
    logger.info(f"在 {len(frames)-1} 帧中找到 {len(frame_indices)} 帧包含图片: {frame_indices}")
    return frame_indices

def render_pdf_pages_to_images(pdf_path: Path, page_numbers: List[int]) -> List[bytes]:
    """将指定的PDF页面渲染为PNG图像字节。"""
    images = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in page_numbers:
            if 1 <= page_num <= doc.page_count:
                page = doc.load_page(page_num - 1)  # PyMuPDF is 0-indexed
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                images.append(img_bytes)
        doc.close()
    except Exception as e:
        logger.error(f"渲染PDF页面时出错: {e}")
    return images

def evaluate_image_with_vlm(client: ChatOpenAI, image_bytes: bytes) -> Optional[int]:
    """使用VLM评估单个图像的图文匹配度。"""
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        msg = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "On a scale of 1-5, how well does the text on this slide explain the key message of the figure? 1: Unrelated. 3: Descriptive but not insightful. 5: Masterfully guides attention to the figure's core takeaway. Please respond with only a single integer."
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                },
            ]
        )
        response = client.invoke([msg])
        score_text = response.content
        return int(re.search(r'\d+', score_text).group())
    except Exception as e:
        logger.error(f"调用VLM API时出错: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="评估演示文稿的图文匹配度。")
    parser.add_argument("--tex-path", type=Path, required=True, help="指向生成的.tex文件的路径。")
    args = parser.parse_args()

    tex_path = args.tex_path

    # 1. 编译 LaTeX -> PDF
    pdf_path = compile_latex_to_pdf(tex_path)
    if not pdf_path:
        sys.exit(1)

    # 2. 找到包含图片的帧
    try:
        with open(tex_path, 'r', encoding='utf-8') as f:
            tex_content = f.read()
    except Exception as e:
        logger.error(f"读取 TeX 文件失败: {e}")
        sys.exit(1)
        
    frames_with_images_indices = find_frames_with_images(tex_content)
    if not frames_with_images_indices:
        logger.warning("未找到包含图片的帧。无法计算分数。")
        # Output a neutral/default score or indicate no score
        print(json.dumps({"average_coherence_score": None, "evaluated_frames": 0}))
        sys.exit(0)

    # 3. 渲染这些帧为图片
    slide_images = render_pdf_pages_to_images(pdf_path, frames_with_images_indices)
    if not slide_images:
        logger.error("渲染PDF页面为图片失败。")
        sys.exit(1)

    # 4. 使用VLM评估每张图片
    client = ChatOpenAI(model="gpt-4o", max_tokens=5)
    scores = []
    for image_bytes in tqdm(slide_images, desc="Evaluating slides with VLM"):
        score = evaluate_image_with_vlm(client, image_bytes)
        if score is not None:
            scores.append(score)
    
    # 5. 计算并输出最终分数
    if not scores:
        logger.error("VLM评估所有幻灯片均失败。")
        average_score = None
    else:
        average_score = sum(scores) / len(scores)
        logger.info(f"最终平均图文匹配度分数: {average_score:.4f}")

    result = {
        "average_coherence_score": average_score,
        "evaluated_frames": len(scores),
        "total_frames_with_figures": len(frames_with_images_indices)
    }
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()
