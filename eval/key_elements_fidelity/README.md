# 关键元素保真度 (Metric 1.2)

本模块用于评估生成的演示文稿对论文中关键视觉元素（图表、公式）的保真度。

## 评估流程

评估分为两个主要步骤：

1.  **准备基准集 (Ground Truth Preparation)**:
    -   运行 `prepare_ground_truth.py` 脚本。
    -   该脚本会遍历指定的数据集（例如 `dataset/silver`），对每个 `caption/` 文件夹中的图片进行OCR，并为每篇论文生成一个 `ground_truth_visuals.json` 文件。这个文件包含了所有关键视觉元素的路径和其对应的标题文本。

2.  **运行评估 (Evaluation)**:
    -   运行 `evaluate_fidelity.py` 脚本。
    -   该脚本会将待评估系统生成的 `.tex` 文件和图片，与第一步生成的 `ground_truth_visuals.json` 文件进行比较。
    -   它通过CLIP模型进行视觉匹配，通过BERTScore进行标题文本匹配，最终计算出**召回率 (Recall)**、**精确度 (Precision)** 和 **F1分数**。

## 使用方法

### 1. 准备基准集

```bash
python eval/key_elements_fidelity/prepare_ground_truth.py --dataset-path path/to/your/dataset
```

### 2. 运行评估

```bash
python eval/key_elements_fidelity/evaluate_fidelity.py --tex-path path/to/generated.tex --images-dir path/to/generated/images --ground-truth-json path/to/ground_truth_visuals.json
