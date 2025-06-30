#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化基准测试脚本
对数据集中的所有论文运行生成和评估流程，并计算平均分。
"""

import os
import sys
import subprocess
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def run_command(command: List[str], env: Optional[Dict[str, str]] = None) -> Tuple[bool, str, str]:
    """运行命令并返回其成功状态、标准输出和标准错。"""
    logger.info(f"运行命令: {' '.join(command)}")
    try:
        # 将os.environ与自定义env合并
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
            
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            env=full_env,
        )
        return True, process.stdout, process.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"命令失败: {' '.join(command)}")
        logger.error(f"Stderr: {e.stderr}")
        return False, e.stdout, e.stderr
    except FileNotFoundError as e:
        logger.error(f"找不到命令: {e}")
        return False, "", str(e)

def parse_main_output(output: str) -> Optional[str]:
    """从main.py的输出中解析生成的.tex文件路径。"""
    match = re.search(r"--previous-tex='([^']+\.tex)'", output)
    if match:
        path = match.group(1)
        logger.info(f"找到生成的tex文件: {path}")
        return path
    logger.warning("在main.py的输出中找不到.tex文件路径。")
    return None

def parse_evaluation_output(output: str) -> Optional[Dict[str, float]]:
    """从run_evaluation.py的输出中解析内容覆盖度分数。"""
    try:
        bertscore_match = re.search(r"bertscore_f1:\s*([\d\.]+)", output)
        rouge_l_match = re.search(r"rouge_l:\s*([\d\.]+)", output)

        if bertscore_match and rouge_l_match:
            scores = {
                "bertscore_f1": float(bertscore_match.group(1)),
                "rouge_l": float(rouge_l_match.group(1)),
            }
            logger.info(f"找到内容覆盖度分数: {scores}")
            return scores
    except Exception as e:
        logger.error(f"解析内容覆盖度输出失败: {e}")

    logger.warning("无法从内容覆盖度输出中解析分数。")
    return None

def parse_fidelity_output(output: str) -> Optional[Dict[str, float]]:
    """从evaluate_fidelity.py的输出中解析保真度分数。"""
    try:
        recall_match = re.search(r"Recall:\s*([\d\.]+)", output)
        precision_match = re.search(r"Precision:\s*([\d\.]+)", output)
        f1_match = re.search(r"F1 Score:\s*([\d\.]+)", output)

        if recall_match and precision_match and f1_match:
            scores = {
                "fidelity_recall": float(recall_match.group(1)),
                "fidelity_precision": float(precision_match.group(1)),
                "fidelity_f1_score": float(f1_match.group(1)),
            }
            logger.info(f"找到关键元素保真度分数: {scores}")
            return scores
    except Exception as e:
        logger.error(f"解析保真度输出失败: {e}")

    logger.warning("无法从保真度输出中解析分数。")
    return None

def main():
    """
    在数据集上运行基准测试的主函数。
    """
    dataset_path = Path("dataset/silver")
    if not dataset_path.is_dir():
        logger.error(f"找不到数据集目录: {dataset_path}")
        sys.exit(1)

    # 步骤 0: 准备所有基准集 (Ground Truth)
    logger.info("--- 步骤 0: 准备所有基准集 ---")
    prepare_command = ["python3", "eval/key_elements_fidelity/prepare_ground_truth.py", "--dataset-path", str(dataset_path)]
    success, _, _ = run_command(prepare_command)
    if not success:
        logger.error("准备基准集失败。正在中止。")
        sys.exit(1)
    logger.info("--- 所有基准集准备就绪 ---")

    all_scores = []
    # 过滤掉.DS_Store等非目录文件
    paper_dirs = sorted([d for d in dataset_path.iterdir() if d.is_dir()])

    for paper_dir in paper_dirs:
        logger.info(f"--- 正在处理论文: {paper_dir.name} ---")
        pdf_path = paper_dir / "paper.pdf"
        if not pdf_path.exists():
            logger.warning(f"在 {paper_dir} 中找不到 paper.pdf，跳过。")
            continue

        # 1. 使用main.py生成.tex文件
        logger.info(f"步骤 1: 为 {pdf_path} 生成 .tex 文件")
        main_command = ["python3", "main.py", str(pdf_path), "--language", "en"]
        success, main_stdout, main_stderr = run_command(main_command)

        if not success:
            logger.error(f"为 {pdf_path} 生成 .tex 文件失败。跳过。")
            continue

        # 合并 stdout 和 stderr 以确保能找到日志中的路径
        combined_output = main_stdout + "\n" + main_stderr
        tex_path_str = parse_main_output(combined_output)
        if not tex_path_str or not Path(tex_path_str).exists():
            logger.error(f"找不到或无法访问生成的.tex文件。跳过。")
            continue
        
        tex_path = Path(tex_path_str)
        # 从tex文件路径推断出图片目录
        images_dir = tex_path.parent / "images"
        if not images_dir.exists():
             # 如果tex同级没有images，则从session_id推断
            session_id = tex_path.parent.name
            images_dir = Path(tex_path.parent.parent.parent) / "images" / session_id
        
        current_paper_scores = {}

        # 2a. 运行内容覆盖度评估
        logger.info(f"步骤 2a: 评估内容覆盖度 {tex_path}")
        eval_env = {"HF_ENDPOINT": "https://hf-mirror.com"}
        coverage_command = [
            "python3", "eval/content_coverage/run_evaluation.py",
            "--pdf", str(pdf_path), "--tex", str(tex_path), "--lang", "en"
        ]
        success, coverage_stdout, _ = run_command(coverage_command, env=eval_env)
        if success:
            coverage_scores = parse_evaluation_output(coverage_stdout)
            if coverage_scores:
                current_paper_scores.update(coverage_scores)

        # 2b. 运行关键元素保真度评估
        logger.info(f"步骤 2b: 评估关键元素保真度 {tex_path}")
        ground_truth_json = paper_dir / "ground_truth_visuals.json"
        if not ground_truth_json.exists():
            logger.warning(f"找不到 {ground_truth_json}，跳过保真度评估。")
        else:
            fidelity_command = [
                "python3", "eval/key_elements_fidelity/evaluate_fidelity.py",
                "--tex-path", str(tex_path),
                "--images-dir", str(images_dir),
                "--ground-truth-json", str(ground_truth_json)
            ]
            success, fidelity_stdout, _ = run_command(fidelity_command, env=eval_env)
            if success:
                fidelity_scores = parse_fidelity_output(fidelity_stdout)
                if fidelity_scores:
                    current_paper_scores.update(fidelity_scores)

        if current_paper_scores:
            all_scores.append(current_paper_scores)
            logger.info(f"成功处理并评分 {paper_dir.name}")
        else:
            logger.error(f"为 {paper_dir.name} 解析任何分数均失败。跳过。")

    # 3. 计算并打印平均分
    if not all_scores:
        logger.warning("没有成功处理的论文。无法计算均分。")
        sys.exit(1)

    # 计算所有可用分数的平均值
    avg_scores = {}
    for key in all_scores[0].keys():
        valid_scores = [s[key] for s in all_scores if key in s]
        if valid_scores:
            avg_scores[key] = sum(valid_scores) / len(valid_scores)

    logger.info("--- 基准测试完成 ---")
    print("\n" + "="*40)
    print("           基准测试结果")
    print("="*40)
    print(f"处理的论文总数: {len(all_scores)}")
    print("\n--- 指标 1.1: 内容覆盖度 ---")
    if "bertscore_f1" in avg_scores:
        print(f"平均 BERTScore F1: {avg_scores['bertscore_f1']:.4f}")
    if "rouge_l" in avg_scores:
        print(f"平均 ROUGE-L:      {avg_scores['rouge_l']:.4f}")
    
    print("\n--- 指标 1.2: 关键元素保真度 ---")
    if "fidelity_recall" in avg_scores:
        print(f"平均召回率 (Recall):    {avg_scores['fidelity_recall']:.4f}")
    if "fidelity_precision" in avg_scores:
        print(f"平均精确度 (Precision): {avg_scores['fidelity_precision']:.4f}")
    if "fidelity_f1_score" in avg_scores:
        print(f"平均 F1 分数:         {avg_scores['fidelity_f1_score']:.4f}")
    print("="*40)

if __name__ == "__main__":
    main()
