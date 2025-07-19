### **Paper2Beamer Benchmark: 技术实现与评估规程 (Technical Specification)**

#### **文档概述**

本文档为`Paper2Beamer Benchmark`提供详细的技术实现规程。Benchmark旨在全面、科学地评估从学术论文PDF自动生成LaTeX Beamer演示文稿的系统。评估体系采用“**混合评估金字塔**”结构，自下而上分为三个层次：**客观基础指标**、**LLM辅助的结构化分析**和**人类校准的主观质量评估**。

---

### **第一层：客观基础指标 (Foundation: Objective & Deterministic Metrics)**

**本层指标完全由自动化脚本执行，结果100%可复现，是整个评估体系的基石。**

#### **指标 1.1: 内容覆盖度 (Content Coverage)**

* **目的**: 确保生成的幻灯片准确地概括和转述了原文的核心思想，而非简单摘抄或遗漏关键点。
* **技术实现**:
    1.  **输入准备**:
        * `source_text`: 提取并拼接源论文PDF的“摘要 (Abstract)”和“结论 (Conclusion)”部分的纯文本。
        * `generated_text`: 解析生成的`.tex`文件，提取所有`\begin{frame}`...`\end{frame}`环境内的纯文本内容并拼接。
    2.  **核心工具**: 使用Hugging Face的`evaluate`库。
    3.  **计算BERTScore**:
        * **代码**: `evaluate.load("bertscore")`
        * **参数**: `predictions=[generated_text]`, `references=[source_text]`, `lang="en"` (或对应语言)。
        * **输出**: 记录`f1`分数。BERTScore衡量的是语义相似度，能理解同义词和释义。
    4.  **计算ROUGE-L**:
        * **代码**: `evaluate.load("rouge")`
        * **参数**: `predictions=[generated_text]`, `references=[source_text]`。
        * **输出**: 记录`rougeL`的F1分数。ROUGE-L衡量的是基于最长公共子序列的结构相似度。
* **注意事项**: 在计算前，对`source_text`和`generated_text`进行统一的预处理，如转为小写、移除LaTeX命令、标准化引用标记等。


### **指标 1.2 (图表版): 关键元素保真度 (Fidelity of Key Elements)**

#### **1. 目的 (Objective)**

本指标旨在客观、量化地评估生成的演示文稿对源论文中**核心视觉元素（包括重要图表和公式）的识别、提取、和呈现**能力。一个高质量的系统，必须能准确地将这些承载着核心信息的视觉元素及其上下文描述，整合到最终的幻灯片中。

#### **2. 技术实现：基于“视觉-文本双重匹配”的评估框架**

本指标的评估流程完全基于您提供的“**基准数据集**”（包含原始论文PDF、重要插图截图文件夹、对应标题截图文件夹）与“**生成物**”（生成的`.tex`文件和其引用的图片文件夹）之间的直接对比。

-----

##### **2.1 基准集构建 (Ground Truth Set Construction) - (一次性工作)**

在评估任何系统之前，我们需要根据您提供的数据集结构，构建一个标准化的“**关键视觉元素基准集**”。

1.  **输入**: 对于测试集中的每一篇论文，我们有：

      * `paper.pdf`
      * `graph/` 文件夹 (e.g., `1.png`, `2.png`, ...)
      * `caption/` 文件夹 (e.g., `1.png`, `2.png`, ...)

2.  **处理**: 编写一个预处理脚本，对每个`graph`和`caption`的配对进行处理：

      * **OCR处理**: 对`caption/`文件夹中的每一张图片（如`caption/1.png`），使用一个高质量的OCR工具（如**Google Cloud Vision API**或开源的`PaddleOCR`）来提取其纯文本内容。
      * **结构化存储**: 将所有信息整合成一个JSON文件，即“**基准视觉元素集**” (`Set_Visual_GT`)。
      * **JSON结构示例**:
        ```json
        [
          {
            "id": "gt_element_1", // 内部唯一ID
            "image_path": "path/to/graph/1.png", // 重要插图/公式的截图路径
            "caption_text": "This is the OCR'd text from caption/1.png..." // 对应标题的文本
          },
          {
            "id": "gt_element_2",
            "image_path": "path/to/graph/2.png",
            "caption_text": "This is the OCR'd text from caption/2.png..."
          }
        ]
        ```

-----

##### **2.2 自动化评估流程 (Automated Evaluation Process)**

对于任何待评估系统，评估流程如下：

1.  **生成物提取 (Generated Content Extraction)**:

      * **输入**: 待评估系统生成的`.tex`文件及其引用的图片文件夹。
      * **产出**: 通过解析`.tex`文件，提取出一个“**生成视觉元素集**” (`Set_Visual_Gen`)。
          * **解析**: 遍历`.tex`文件，用正则表达式查找所有`figure`或类似环境中包含`\includegraphics`和`\caption{...}`的块。
          * **提取**: 对每一个找到的块，提取出：
              * `image_path`: `\includegraphics`命令引用的图片文件路径。
              * `caption_text`: `\caption{...}`中的纯文本内容。

2.  **匹配与评分 (Matching & Scoring)**:

      * **a) 视觉匹配 (Visual Matching)**:

          * **任务**: 对于`Set_Visual_Gen`中的**每一张图片**，我们需要在`Set_Visual_GT`的**所有图片**中找到与之最匹配的原始图片。
          * **方法**: 使用**CLIP图像嵌入（Image Embedding）的余弦相似度**进行匹配。为生成集中的每张图片，计算它与基准集中所有图片的相似度，取最高分者。如果最高分超过一个阈值（例如**0.90**），则视为成功匹配。

      * **b) 计算召回率 (Key Element Recall)**: **衡量“找得全不全”**。

          * `召回率 = 成功匹配上的基准视觉元素数量 / 基准视觉元素总数`。
          * **解读**: 这个分数直接反映了系统识别并包含**所有重要视觉元素**的能力。如果系统漏掉了一张您在`graph/`中定义的重要图片，这个分数就会降低。

      * **c) 计算精确度 (Caption Precision)**: **衡量“说得对不对”**。

          * **范围**: 只对那些**成功匹配上**的视觉元素对进行计算。
          * **方法**: 对于每一对匹配成功的`(generated_element, ground_truth_element)`，计算其`generated_element.caption_text`和`ground_truth_element.caption_text`之间的**BERTScore F1分数**。
          * **得分**: 最终的“标题精确度”是所有成功匹配对的BERTScore的平均值。

      * **d) 最终得分 (F1-Score)**:

          * 为了得到一个能同时反映“找得全”和“说得对”的综合分数，我们使用经典的**F1 Score**来结合召回率和精确度。
          * `关键元素保真度分 = 2 * (召回率 * 标题精确度) / (召回率 + 标题精确度)`

这个经过您补充后完善的指标，现在变得极其“solid”：

  * **完全方法无关**: 只需最终的`.tex`和图片文件夹，可以公平地评估任何系统。
  * **评估重点清晰**: 分别量化了“是否包含重要元素”和“对元素的解释是否准确”。
  * **技术路径明确**: 每个步骤都有具体、可实现的计算方法。

### **第二层：LLM辅助的结构化分析 (Middle: LLM-Assisted Structural Analysis)**

**本层使用LLM完成可控、可解释的分类和识别任务，以评估产出的逻辑与结构。**

#### **指标 2.1: 叙事结构完整性 (Narrative Arc Integrity)**
（跑出来都是1.0，感觉没啥用，已经去掉）
* **目的**: 量化评估幻灯片是否遵循了“动机-方法-结果-结论”的经典学术叙事结构。
* **技术实现**:
    1.  **内容提取**: 解析`.tex`文件，按顺序提取每张幻灯片（Frame）的标题和核心要点文本。
    2.  **LLM内容分类**: 对每一帧的内容，调用LLM（如GPT-4o）进行分类。
        * **Prompt**: `"You are a classifier. Assign one label from [Motivation, Method, Result, Conclusion, Other] to the following slide content: ..."`
    3.  **序列验证**: 得到一个标签序列，如 `[Motivation, Motivation, Method, Method, Method, Result, Conclusion]`。使用一个简单的**状态机**来验证此序列是否符合预定义的有效模式（例如，`Motivation`之后不能是`Conclusion`）。
* **输出**: 一个介于0到1之间的分数，代表了符合理想叙事模式的最长子序列的长度比例。

#### **指标 2.2: 逻辑链条强度 (Logical Chain Strength)**

* **目的**: 评估幻灯片之间的过渡是否流畅、有逻辑。
* **技术实现**:
    1.  **内容配对**: 按顺序提取所有相邻幻灯片对（帧N和帧N+1）的内容。
    2.  **LLM关系检测**: 对每一对内容，调用LLM进行二元判断。
        * **Prompt**: `"Does Slide N+1 contain a clear logical transition (e.g., using words like 'Therefore', 'However', or presenting evidence for a claim in Slide N)? Answer only 'Yes' or 'No'. Content N: ... Content N+1: ..."`
        （我觉得应该改成给一个0～5之间的整数，0代表毫无逻辑，5代表十分有逻辑，评分的时候算一个平均分，再算一个连贯率=分数大于等于3的总数/(总幻灯片数-1)）
    3.  **评分**: `“Yes”的总数 / (总幻灯片数 - 1)`。
* **输出**: 一个介于0到1之间的比率。

---

### **第三层：人类校准的主观质量评估 (Peak: Human-Calibrated Quality Assessment)**

**本层评估最主观的“沟通效果”。其可靠性通过一次性的人类评估进行“校准”来保证。**

#### **校准流程 (One-time Setup Phase)**

1.  **人类评估**: 对`Gold Set`中的样本，邀请领域专家根据详细的评分标准（Rubrics）对“图文匹配度”、“动态展示效果”等主观指标进行1-5分制打分，得到“人类分数”。
2.  **LLM评估**: 使用下面定义的LLM评委，对同一批样本进行打分，得到“LLM分数”。
3.  **相关性分析**: 计算人类分数和LLM分数之间的**斯皮尔曼等级相关系数 (Spearman's rank correlation)**。
4.  **建立可信度**: 在论文中报告此相关系数。如果系数高（例如 > 0.8），则证明此LLM评委是人类判断的可靠代理，可以在后续评估中自动化使用。

#### **已校准的自动化指标 (Calibrated & Automated Metrics)**

##### **指标 3.1: 图文匹配度 (Text-Figure Coherence)**

* **目的**: 评估幻灯片中的文字是否有效地解释和引导了对配图的理解。
* **技术实现**:
    1.  **截图**: 渲染PDF，并对所有包含图片的幻灯片进行截图。
    2.  **VLM评委**: 将截图发送给**已校准的VLM**（如GPT-4V）。
        * **Prompt**: `"On a scale of 1-5, how well does the text on this slide explain the key message of the figure? 1: Unrelated. 3: Descriptive but not insightful. 5: Masterfully guides attention to the figure's core takeaway."`
* **输出**: 所有含图幻灯片的平均分。

<!-- ##### **指标 3.2: 渐进式披露得分 (Progressive Disclosure Score)**

* **目的**: 评估`\pause`等动态效果的使用是否真正有助于降低认知负荷、引导观众思路。
* **技术实现**:
    1.  **分步渲染**: 对包含动态指令的幻灯片，将其渲染成一个图像序列，代表演示的每一步。
    2.  **LLM评委**: 将这个图像序列发送给**已校准的LLM**。
        * **Prompt**: `"This sequence of images shows a step-by-step reveal on a slide. On a scale of 1-5, how effective is this progression? 1: Confusing or unnecessary. 3: Logical but adds little value. 5: Essential for clarifying a complex idea."`
* **输出**: 所有动态幻灯片的平均分。 -->