#!/usr/bin/env python3
import os
import json
from langchain_openai import OpenAI
from slide_generator import generate_section_slides, clean_latex_string

# 确保设置了OpenAI API密钥
if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("请设置OPENAI_API_KEY环境变量")

# 添加包装函数
def wrap_in_latex_document(content):
    """将LaTeX片段包装在完整文档中以便测试"""
    return r"""
\documentclass{beamer}
\usepackage[UTF8]{ctex}

\usetheme{default}
\usecolortheme{default}

\title{测试}
\author{测试}
\date{\today}

\begin{document}

""" + content + r"""

\end{document}
"""

# 加载论文内容
with open("parsed_content.json", "r", encoding="utf-8") as f:
    paper_content = json.load(f)

# 创建LLM实例
llm = OpenAI(temperature=0.3, base_url=os.environ.get("OPENAI_API_BASE"))

# 测试第一个章节
section = paper_content["sections"][0]
print(f"测试章节: {section['title']}")

# 生成章节幻灯片
test_paper = {"sections": [section]}
section_slides = generate_section_slides(test_paper, llm)

# 保存到文件
with open("test_section_slides.tex", "w", encoding="utf-8") as f:
    f.write(section_slides)

print(f"\n结果已保存到 test_section_slides.tex")

# 验证LaTeX代码
from latex_validator import validate_latex
is_valid, error_message = validate_latex(section_slides)

if is_valid:
    print("生成的LaTeX代码有效")
else:
    print(f"生成的LaTeX代码无效: {error_message}")

    # 尝试添加文档包装
    full_latex = wrap_in_latex_document(section_slides)
    
    with open("test_section_slides_full.tex", "w", encoding="utf-8") as f:
        f.write(full_latex)
    
    is_valid_full, error_message_full = validate_latex(full_latex)
    if is_valid_full:
        print("包装后的LaTeX代码有效")
    else:
        print(f"包装后的LaTeX代码仍然无效: {error_message_full}") 