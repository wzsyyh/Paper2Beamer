#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
准备基准集 (Ground Truth) 的脚本
遍历数据集，对caption图片进行OCR，并生成结构化的JSON文件。
"""

import os
import json
import argparse
import logging
from pathlib import Path
from paddleocr import PaddleOCR

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def ocr_image_to_text(ocr_engine, image_path: str) -> str:
    """使用PaddleOCR从图片中提取文本。"""
    try:
        # 使用新版API的predict方法，并移除不支持的cls参数
        result = ocr_engine.predict(image_path)
        if result and result[0] is not None:
            # 提取所有识别出的文本行并拼接
            text_lines = [line[1][0] for line in result[0]]
            return " ".join(text_lines)
    except Exception as e:
        logger.error(f"对图片 {image_path} 进行OCR时出错: {e}")
    return ""

def process_dataset(dataset_path: Path):
    """
    处理整个数据集，为每篇论文生成一个基准JSON文件。
    """
    logger.info(f"开始处理数据集: {dataset_path}")
    
    # 初始化OCR引擎
    # 使用英文模型，不使用GPU
    try:
        # 根据新版API调整参数，移除了use_gpu
        ocr_engine = PaddleOCR(use_textline_orientation=True, lang='en')
        logger.info("PaddleOCR引擎初始化成功。")
    except Exception as e:
        logger.error(f"初始化PaddleOCR失败: {e}")
        logger.error("请确保已正确安装paddlepaddle和paddleocr。")
        return

    paper_dirs = sorted([d for d in dataset_path.iterdir() if d.is_dir()])

    for paper_dir in paper_dirs:
        logger.info(f"--- 正在处理论文: {paper_dir.name} ---")
        graph_dir = paper_dir / "graph"
        caption_dir = paper_dir / "caption"
        output_json_path = paper_dir / "ground_truth_visuals.json"

        if not graph_dir.is_dir() or not caption_dir.is_dir():
            logger.warning(f"在 {paper_dir} 中找不到 graph 或 caption 目录，跳过。")
            continue

        ground_truth_data = []
        
        # 获取所有caption图片并排序，以确保一致性
        caption_images = sorted(caption_dir.glob("*.png"))

        for i, caption_image_path in enumerate(caption_images):
            # 假设graph图片和caption图片的文件名一一对应
            graph_image_path = graph_dir / caption_image_path.name
            
            if not graph_image_path.exists():
                logger.warning(f"找不到对应的graph图片 {graph_image_path}，跳过。")
                continue

            logger.info(f"正在对 {caption_image_path} 进行OCR...")
            caption_text = ocr_image_to_text(ocr_engine, str(caption_image_path))

            if caption_text:
                element = {
                    "id": f"gt_element_{i+1}",
                    "image_path": str(graph_image_path.resolve()),
                    "caption_text": caption_text.strip()
                }
                ground_truth_data.append(element)
                logger.info(f"成功处理: {caption_image_path.name} -> '{caption_text[:50]}...'")
            else:
                logger.warning(f"未能从 {caption_image_path} 提取文本。")

        # 将结果保存到JSON文件
        if ground_truth_data:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(ground_truth_data, f, ensure_ascii=False, indent=2)
            logger.info(f"基准集已保存到: {output_json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="为关键元素保真度评估准备基准集。")
    parser.add_argument(
        "--dataset-path",
        default="dataset/silver",
        help="数据集根目录的路径。"
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset_path)
    process_dataset(dataset_path)
