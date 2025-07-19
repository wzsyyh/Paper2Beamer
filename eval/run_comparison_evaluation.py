#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比评估脚本
同时运行有planner和无planner版本的生成和评估，并对比结果
"""

import os
import sys
import subprocess
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def run_command(command: List[str], env: Optional[Dict[str, str]] = None) -> tuple[bool, str, str]:
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

def parse_evaluation_results(output: str) -> Dict[str, float]:
    """从评估输出中解析结果"""
    results = {}
    
    # 解析各种指标
    import re
    
    # BERTScore F1
    bertscore_match = re.search(r"平均 BERTScore F1:\s*([\d\.]+)", output)
    if bertscore_match:
        results["bertscore_f1"] = float(bertscore_match.group(1))
    
    # ROUGE-L
    rouge_match = re.search(r"平均 ROUGE-L:\s*([\d\.]+)", output)
    if rouge_match:
        results["rouge_l"] = float(rouge_match.group(1))
    
    # 保真度指标
    fidelity_recall_match = re.search(r"平均召回率 \(Recall\):\s*([\d\.]+)", output)
    if fidelity_recall_match:
        results["fidelity_recall"] = float(fidelity_recall_match.group(1))
    
    fidelity_precision_match = re.search(r"平均精确度 \(Precision\):\s*([\d\.]+)", output)
    if fidelity_precision_match:
        results["fidelity_precision"] = float(fidelity_precision_match.group(1))
    
    fidelity_f1_match = re.search(r"平均 F1 分数:\s*([\d\.]+)", output)
    if fidelity_f1_match:
        results["fidelity_f1_score"] = float(fidelity_f1_match.group(1))
    
    # 逻辑链条强度
    logical_chain_score_match = re.search(r"平均逻辑链条分数:\s*([\d\.]+)", output)
    if logical_chain_score_match:
        results["logical_chain_avg_score"] = float(logical_chain_score_match.group(1))
    
    logical_chain_coherence_match = re.search(r"平均逻辑连贯率:\s*([\d\.]+)", output)
    if logical_chain_coherence_match:
        results["logical_chain_coherence_rate"] = float(logical_chain_coherence_match.group(1))
    
    # 图文匹配度
    text_figure_match = re.search(r"平均图文匹配度分数:\s*([\d\.]+)", output)
    if text_figure_match:
        results["text_figure_coherence"] = float(text_figure_match.group(1))
    
    return results

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行有planner和无planner版本的对比评估")
    parser.add_argument("--skip-generation", action="store_true", help="跳过生成步骤，直接使用现有的manifest文件")
    parser.add_argument("--only-no-planner", action="store_true", help="只运行无planner版本")
    args = parser.parse_args()
    
    start_time = time.time()
    
    # 定义manifest文件路径
    manifest_with_planner = Path("output/eval_manifest.json")
    manifest_no_planner = Path("output/eval_manifest_no_planner.json")
    
    if not args.skip_generation:
        if not args.only_no_planner:
            # 步骤1: 运行有planner版本的生成
            logger.info("=== 步骤1: 运行有planner版本的生成 ===")
            success, stdout, stderr = run_command(["python3", "eval/run_generation.py"])
            if not success:
                logger.error("有planner版本生成失败")
                sys.exit(1)
        
        # 步骤2: 运行无planner版本的生成
        logger.info("=== 步骤2: 运行无planner版本的生成 ===")
        success, stdout, stderr = run_command(["python3", "eval/run_generation_no_planner.py"])
        if not success:
            logger.error("无planner版本生成失败")
            sys.exit(1)
    
    # 检查manifest文件是否存在
    if not args.only_no_planner and not manifest_with_planner.exists():
        logger.error(f"找不到有planner版本的manifest文件: {manifest_with_planner}")
        sys.exit(1)
    
    if not manifest_no_planner.exists():
        logger.error(f"找不到无planner版本的manifest文件: {manifest_no_planner}")
        sys.exit(1)
    
    results = {}
    
    if not args.only_no_planner:
        # 步骤3: 运行有planner版本的评估
        logger.info("=== 步骤3: 运行有planner版本的评估 ===")
        success, stdout, stderr = run_command([
            "python3", "eval/run_evaluation_from_manifest.py", 
            "--manifest-path", str(manifest_with_planner)
        ])
        if success:
            results["with_planner"] = parse_evaluation_results(stdout)
            logger.info("有planner版本评估完成")
        else:
            logger.error("有planner版本评估失败")
    
    # 步骤4: 运行无planner版本的评估
    logger.info("=== 步骤4: 运行无planner版本的评估 ===")
    success, stdout, stderr = run_command([
        "python3", "eval/run_evaluation_from_manifest.py", 
        "--manifest-path", str(manifest_no_planner)
    ])
    if success:
        results["no_planner"] = parse_evaluation_results(stdout)
        logger.info("无planner版本评估完成")
    else:
        logger.error("无planner版本评估失败")
        sys.exit(1)
    
    # 步骤5: 生成对比报告
    logger.info("=== 步骤5: 生成对比报告 ===")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n" + "="*60)
    print("           BeamerAgent 消融实验对比报告")
    print("="*60)
    print(f"总运行时间: {total_time:.2f} 秒")
    
    if not args.only_no_planner and "with_planner" in results and "no_planner" in results:
        with_planner = results["with_planner"]
        no_planner = results["no_planner"]
        
        print("\n" + "-"*60)
        print("                指标对比")
        print("-"*60)
        
        # 定义指标名称映射
        metric_names = {
            "bertscore_f1": "BERTScore F1",
            "rouge_l": "ROUGE-L",
            "fidelity_recall": "保真度召回率",
            "fidelity_precision": "保真度精确度", 
            "fidelity_f1_score": "保真度F1分数",
            "logical_chain_avg_score": "逻辑链条分数",
            "logical_chain_coherence_rate": "逻辑连贯率",
            "text_figure_coherence": "图文匹配度"
        }
        
        print(f"{'指标':<20} {'有Planner':<12} {'无Planner':<12} {'差异':<10} {'变化率':<10}")
        print("-" * 60)
        
        for metric_key, metric_name in metric_names.items():
            if metric_key in with_planner and metric_key in no_planner:
                with_val = with_planner[metric_key]
                no_val = no_planner[metric_key]
                diff = no_val - with_val
                change_rate = (diff / with_val * 100) if with_val != 0 else 0
                
                print(f"{metric_name:<20} {with_val:<12.4f} {no_val:<12.4f} {diff:<10.4f} {change_rate:<10.2f}%")
        
        print("\n" + "-"*60)
        print("                总结")
        print("-"*60)
        
        # 计算平均性能变化
        all_changes = []
        for metric_key in metric_names.keys():
            if metric_key in with_planner and metric_key in no_planner:
                with_val = with_planner[metric_key]
                no_val = no_planner[metric_key]
                if with_val != 0:
                    change_rate = (no_val - with_val) / with_val * 100
                    all_changes.append(change_rate)
        
        if all_changes:
            avg_change = sum(all_changes) / len(all_changes)
            print(f"平均性能变化: {avg_change:.2f}%")
            
            if avg_change > 0:
                print("✅ 无planner版本整体性能优于有planner版本")
            elif avg_change < -5:
                print("❌ 无planner版本性能显著低于有planner版本")
            else:
                print("⚖️ 两个版本性能相近")
    
    elif "no_planner" in results:
        print("\n" + "-"*60)
        print("           无Planner版本结果")
        print("-"*60)
        no_planner = results["no_planner"]
        for metric_key, value in no_planner.items():
            metric_name = metric_key.replace('_', ' ').title()
            print(f"{metric_name:<25}: {value:.4f}")
    
    # 保存结果到JSON文件
    results_file = Path("output/comparison_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_time_seconds": total_time,
            "results": results
        }, f, indent=4, ensure_ascii=False)
    
    print(f"\n详细结果已保存到: {results_file}")
    print("="*60)

if __name__ == "__main__":
    main()
