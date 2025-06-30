# 内容覆盖度评估模块

本模块用于评估生成的Beamer演示文稿对原始论文内容的覆盖程度。

## 功能说明

该模块通过以下方式评估内容覆盖度：

1. 从原始论文PDF中提取摘要(Abstract)和结论(Conclusion)部分
2. 从生成的Beamer `.tex`文件中提取所有幻灯片的文本内容
3. 使用BERTScore和ROUGE-L指标计算两者之间的语义相似度

## 依赖项

```
PyPDF2
evaluate
bert-score
rouge-score
```

可通过以下命令安装依赖：

```bash
pip install PyPDF2 evaluate bert-score rouge-score
```

## 使用方法

### 基本用

```bash
python run_evaluation.py --pdf path/to/paper.pdf --tex path/to/presentation.tex --lang en
```

### 参数说明

- `--pdf`: 原始论文PDF文件的路径（必需）
- `--tex`: 生成的Beamer TEX文件的路径（必需）
- `--lang`: 文档语言，默认为英语(en)
- `--output`: 可选，指定结果输出的JSON文件路径

### 输出示例

```
内容覆盖度评估结果:
  bertscore_f1: 0.8765
  rouge_l: 0.5432
```

## 测试

使用测试脚本可以快速验证模块功能：

```bash
python test_run_evaluation.py --pdf sample/paper.pdf --tex sample/presentation.tex
```

## 技术说明

1. **PDF文本提取**：使用PyPDF2库提取PDF内容，然后通过正则表达式定位摘要和结论部分

2. **LaTeX文本处理**：通过正则表达式提取Beamer幻灯片内容，处理LaTeX命令，保留纯文本

3. **文本标准化**：对比前进行标准化处理，包括小写转换、标点规范化、引用标记统一等

4. **评估指标**：
   - **BERTScore**: 基于BERT的语义相似度评分，能够捕获同义词和释义关系
   - **ROUGE-L**: 基于最长公共子序列的评分，关注文本结构相似性
