#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic LLM版本自动化评估脚本
根据输入的JSON清单文件，对Basic LLM生成的PDF和.tex配对运行简化评估流程。
只评估文本覆盖度和逻辑链条强度，跳过图片相关指标。
"""

import os
import sys
import subprocess
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import argparse

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def run_command(command: List[str], env: Optional[Dict[str, str]] = None) -> Tuple[bool, str, str]:
    """运行命令并返回其成功状态、标准输出和标准错误。"""
    logger.info(f"运行命令: {' '.join(command)}")
    try:
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

def parse_logical_chain_output(output: str) -> Optional[Dict[str, float]]:
    """从logical_chain_strength/run_evaluation.py的输出中解析逻辑链条分数。"""
    try:
        # The output might contain logs before the JSON. Find the start of the JSON.
        json_start_index = output.find('{')
        if json_start_index == -1:
            logger.warning("在逻辑链条输出中找不到JSON对象。")
            return None
        
        json_output = output[json_start_index:]
        data = json.loads(json_output)

        if "average_score" in data and "coherence_rate" in data:
            scores = {
                "logical_chain_avg_score": float(data["average_score"]),
                "logical_chain_coherence_rate": float(data["coherence_rate"]),
            }
            logger.info(f"找到逻辑链条强度分数: {scores}")
            return scores
    except json.JSONDecodeError as e:
        logger.error(f"解析逻辑链条输出失败 (JSON): {e}")
        logger.error(f"原始输出: {output}")
    except Exception as e:
        logger.error(f"解析逻辑链条输出失败: {e}")
    logger.warning("无法从逻辑链条输出中解析分数。")
    return None

def main():
    """
    根据输入的清单文件运行Basic LLM基准测试的主函数。
    """
    parser = argparse.ArgumentParser(description="根据生成的清单文件运行Basic LLM评估基准测试。")
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=Path("output/eval_manifest_basic_llm.json"),
        help="指向包含 (pdf_path, tex_path, paper_dir) 配对的JSON清单文件的路径。"
    )
    args = parser.parse_args()

    manifest_path = args.manifest_path
    if not manifest_path.exists():
        logger.error(f"找不到清单文件: {manifest_path}")
        logger.error("请先运行 run_generation_basic_llm.py 来创建清单文件。")
        sys.exit(1)

    with open(manifest_path, 'r', encoding='utf-8') as f:
        evaluation_pairs = json.load(f)

    all_scores = []
    
    for pair in evaluation_pairs:
        pdf_path = Path(pair["pdf_path"])
        tex_path = Path(pair["tex_path"])
        paper_dir = Path(pair["paper_dir"])
        
        logger.info(f"--- 正在评估论文: {paper_dir.name} (Basic LLM版本) ---")
        logger.info(f"PDF: {pdf_path}")
        logger.info(f"TEX: {tex_path}")

        if not all([pdf_path.exists(), tex_path.exists()]):
            logger.warning(f"PDF或TEX文件不存在。跳过 {paper_dir.name}。")
            continue

        current_paper_scores = {"paper_name": paper_dir.name}

        logger.info(f"步骤 1: 评估内容覆盖度 {tex_path}")
        eval_env = {"HF_ENDPOINT": "https://hf-mirror.com"}
        coverage_command = ["python3", "eval/content_coverage/run_evaluation.py", "--pdf", str(pdf_path), "--tex", str(tex_path), "--lang", "en"]
        success, coverage_stdout, _ = run_command(coverage_command, env=eval_env)
        if success:
            coverage_scores = parse_evaluation_output(coverage_stdout)
            if coverage_scores:
                current_paper_scores.update(coverage_scores)

        logger.info(f"步骤 2: 评估逻辑链条强度 {tex_path}")
        logical_chain_command = ["python3", "eval/logical_chain_strength/run_evaluation.py", str(tex_path)]
        success, logical_chain_stdout, _ = run_command(logical_chain_command)
        if success:
            logical_chain_scores = parse_logical_chain_output(logical_chain_stdout)
            if logical_chain_scores:
                current_paper_scores.update(logical_chain_scores)

        # 跳过图片相关评估
        logger.info("跳过关键元素保真度评估 (Basic LLM版本无图片)")
        logger.info("跳过图文匹配度评估 (Basic LLM版本无图片)")

        if len(current_paper_scores) > 1: # paper_name is always there
            all_scores.append(current_paper_scores)
            logger.info(f"成功处理并评分 {paper_dir.name} (Basic LLM版本)")
        else:
            logger.error(f"为 {paper_dir.name} 解析任何分数均失败。跳过。")

    if not all_scores:
        logger.warning("没有成功处理的论文。无法计算均分。")
        sys.exit(1)

    avg_scores = {}
    all_keys = set()
    for s in all_scores:
        all_keys.update(s.keys())
    all_keys.discard("paper_name")

    for key in sorted(list(all_keys)):
        valid_scores = [s[key] for s in all_scores if key in s]
        if valid_scores:
            avg_scores[key] = sum(valid_scores) / len(valid_scores)

    logger.info("--- Basic LLM基准测试完成 ---")
    print("\n" + "="*40)
    print("        Basic LLM基准测试结果")
    print("="*40)
    print(f"处理的论文总数: {len(all_scores)}")
    print("\n" + "-"*40)
    print("        单篇论文得分详情")
    print("-"*40)
    for scores in all_scores:
        paper_name = scores.pop("paper_name", "Unknown")
        print(f"\n--- 论文: {paper_name} ---")
        for metric, value in sorted(scores.items()):
            formatted_metric = metric.replace('_', ' ').title()
            print(f"  {formatted_metric:<25}: {value:.4f}")
    print("\n" + "="*40)
    print("           平均分总结")
    print("="*40)
    print("\n--- 指标 1.1: 内容覆盖度 ---")
    if "bertscore_f1" in avg_scores:
        print(f"平均 BERTScore F1: {avg_scores['bertscore_f1']:.4f}")
    if "rouge_l" in avg_scores:
        print(f"平均 ROUGE-L:      {avg_scores['rouge_l']:.4f}")
    print("\n--- 指标 2.2: 逻辑链条强度 ---")
    if "logical_chain_avg_score" in avg_scores:
        print(f"平均逻辑链条分数: {avg_scores['logical_chain_avg_score']:.4f}")
    if "logical_chain_coherence_rate" in avg_scores:
        print(f"平均逻辑连贯率:   {avg_scores['logical_chain_coherence_rate']:.4f}")
    print("\n--- 注意 ---")
    print("Basic LLM版本跳过了以下评估:")
    print("- 关键元素保真度 (无图片)")
    print("- 图文匹配度 (无图片)")
    print("="*40)

if __name__ == "__main__":
    main()
