#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化生成脚本
对数据集中的所有论文运行生成流程，并创建一个包含 (pdf_path, tex_path) 配对的JSON清单文件。
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

def parse_main_output(output: str) -> Optional[str]:
    """从main.py的输出中解析生成的.tex文件路径。"""
    match = re.search(r"--previous-tex='([^']+\.tex)'", output)
    if match:
        path = match.group(1)
        logger.info(f"找到生成的tex文件: {path}")
        return path
    logger.warning("在main.py的输出中找不到.tex文件路径。")
    return None

def main():
    """
    在数据集上运行生成的主函数。
    """
    dataset_path = Path("dataset/silver")
    output_manifest_path = Path("output/eval_manifest.json")
    
    if not dataset_path.is_dir():
        logger.error(f"找不到数据集目录: {dataset_path}")
        sys.exit(1)

    # 确保输出目录存在
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)

    generation_results = []
    paper_dirs = sorted([d for d in dataset_path.iterdir() if d.is_dir()])

    for paper_dir in paper_dirs:
        logger.info(f"--- 正在处理论文: {paper_dir.name} ---")
        pdf_path = paper_dir / "paper.pdf"
        if not pdf_path.exists():
            logger.warning(f"在 {paper_dir} 中找不到 paper.pdf，跳过。")
            continue

        logger.info(f"为 {pdf_path} 生成 .tex 文件")
        main_command = ["python3", "main.py", str(pdf_path), "--language", "en"]
        success, main_stdout, main_stderr = run_command(main_command)
        if not success:
            logger.error(f"为 {pdf_path} 生成 .tex 文件失败。跳过。")
            continue

        combined_output = main_stdout + "\n" + main_stderr
        tex_path_str = parse_main_output(combined_output)
        if not tex_path_str or not Path(tex_path_str).exists():
            logger.error(f"找不到或无法访问生成的.tex文件。跳过。")
            continue
        
        tex_path = Path(tex_path_str)
        # 确定图片目录的明确路径
        session_id = tex_path.parent.name
        images_dir = Path("output/images") / session_id
        if not images_dir.is_dir():
            logger.error(f"找不到生成的图片目录: {images_dir}。跳过。")
            continue

        generation_results.append({
            "pdf_path": str(pdf_path.resolve()),
            "tex_path": str(tex_path.resolve()),
            "paper_dir": str(paper_dir.resolve()),
            "images_dir": str(images_dir.resolve())
        })
        logger.info(f"成功为 {paper_dir.name} 生成文件。")

    if not generation_results:
        logger.error("没有成功生成任何文件。")
        sys.exit(1)

    with open(output_manifest_path, 'w', encoding='utf-8') as f:
        json.dump(generation_results, f, indent=4)

    logger.info(f"--- 生成完成 ---")
    logger.info(f"生成结果清单已保存到: {output_manifest_path}")

if __name__ == "__main__":
    main()
