#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键元素保真度 (Fidelity of Key Elements) 评估脚本
"""

import os
import re
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import evaluate

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def extract_generated_elements(tex_path: Path, images_dir: Path) -> List[Dict[str, Any]]:
    """从.tex文件和图片目录中提取生成的视觉元素。"""
    generated_elements = []
    if not tex_path.exists():
        logger.error(f"TEX文件不存在: {tex_path}")
        return generated_elements

    with open(tex_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 正则表达式查找figure环境中的includegraphics和caption
    pattern = re.compile(
        r"\\begin{figure}.*?"
        r"\\includegraphics(?:\[.*?\])?{([^}]+)}.*?"
        r"\\caption{([^}]+)}.*?"
        r"\\end{figure}",
        re.DOTALL
    )

    for match in pattern.finditer(content):
        image_name = os.path.basename(match.group(1))
        image_path = images_dir / image_name
        caption_text = match.group(2).strip()

        if image_path.exists():
            generated_elements.append({
                "image_path": str(image_path.resolve()),
                "caption_text": caption_text
            })
        else:
            logger.warning(f"在生成的元素中找不到图片文件: {image_path}")
            
    logger.info(f"从生成物中提取了 {len(generated_elements)} 个视觉元素。")
    return generated_elements

def get_image_embedding(image_path: str, model, processor, device) -> torch.Tensor:
    """为单个图片计算CLIP嵌入。"""
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            embedding = model.get_image_features(**inputs)
        return embedding
    except Exception as e:
        logger.error(f"处理图片失败 {image_path}: {e}")
        return torch.empty(0)

def calculate_fidelity_scores(
    generated_elements: List[Dict], 
    ground_truth_elements: List[Dict],
    similarity_threshold: float = 0.9
) -> Dict[str, float]:
    """计算关键元素保真度的分数。"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"使用设备: {device}")

    try:
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        bertscore = evaluate.load("bertscore")
    except Exception as e:
        logger.error(f"加载模型失败: {e}")
        logger.error("请确保已设置HF_ENDPOINT或网络连接正常。")
        return {"error": "模型加载失败"}

    gt_embeddings = [get_image_embedding(elem["image_path"], model, processor, device) for elem in ground_truth_elements]
    gen_embeddings = [get_image_embedding(elem["image_path"], model, processor, device) for elem in generated_elements]

    # 过滤掉处理失败的嵌入
    gt_embeddings = [emb for emb in gt_embeddings if emb.nelement() > 0]
    gen_embeddings = [emb for emb in gen_embeddings if emb.nelement() > 0]

    if not gt_embeddings or not gen_embeddings:
        logger.warning("无法计算有效的图像嵌入。")
        return {"recall": 0.0, "precision": 0.0, "f1_score": 0.0}

    # 计算相似度矩阵
    gt_tensor = torch.cat(gt_embeddings)
    gen_tensor = torch.cat(gen_embeddings)
    similarity_matrix = torch.matmul(gen_tensor, gt_tensor.T)

    # 视觉匹配
    matched_pairs = []
    matched_gt_indices = set()
    for i, gen_elem in enumerate(generated_elements):
        similarities = similarity_matrix[i]
        best_match_idx = torch.argmax(similarities).item()
        best_score = similarities[best_match_idx].item()

        if best_score >= similarity_threshold:
            if best_match_idx not in matched_gt_indices:
                matched_pairs.append({
                    "gen": gen_elem,
                    "gt": ground_truth_elements[best_match_idx]
                })
                matched_gt_indices.add(best_match_idx)

    # 计算召回率 (Recall)
    recall = len(matched_gt_indices) / len(ground_truth_elements) if ground_truth_elements else 0.0
    
    # 计算精确度 (Precision)
    if not matched_pairs:
        precision = 0.0
    else:
        predictions = [pair["gen"]["caption_text"] for pair in matched_pairs]
        references = [pair["gt"]["caption_text"] for pair in matched_pairs]
        
        score_results = bertscore.compute(predictions=predictions, references=references, lang="en")
        precision = sum(score_results["f1"]) / len(score_results["f1"])

    # 计算F1分数
    if recall + precision == 0:
        f1_score = 0.0
    else:
        f1_score = 2 * (recall * precision) / (recall + precision)

    return {
        "recall": recall,
        "precision": precision,
        "f1_score": f1_score
    }

def main():
    parser = argparse.ArgumentParser(description="评估关键元素的保真度。")
    parser.add_argument("--tex-path", required=True, help="生成的.tex文件路径。")
    parser.add_argument("--images-dir", required=True, help="包含生成图片的目录路径。")
    parser.add_argument("--ground-truth-json", required=True, help="基准集JSON文件路径。")
    args = parser.parse_args()

    # 1. 加载基准集
    try:
        with open(args.ground_truth_json, 'r', encoding='utf-8') as f:
            ground_truth_elements = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"加载基准集JSON失败: {e}")
        return

    # 2. 提取生成的元素
    generated_elements = extract_generated_elements(Path(args.tex_path), Path(args.images_dir))

    # 3. 计算分数
    scores = calculate_fidelity_scores(generated_elements, ground_truth_elements)

    # 4. 打印结果
    print("\n" + "="*30)
    print("   关键元素保真度评估结果")
    print("="*30)
    for metric, value in scores.items():
        if isinstance(value, float):
            print(f"  {metric.replace('_', ' ').title()}: {value:.4f}")
        else:
            print(f"  {metric}: {value}")
    print("="*30)

if __name__ == "__main__":
    main()
