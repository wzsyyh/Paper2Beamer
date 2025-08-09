### **交互式 Beamer 幻灯片修订功能开发计划**

#### 1. 总体目标

本项目旨在为现有的 `paper-to-beamer` 工作流增加一个强大的、可交互的后期修订功能。其核心是创建一个由`Editor Agent`驱动的智能修订循环，该循环能够理解用户（或AI评审员）的修改建议，并像AI编程助手一样，自动定位并修改`.tex`源代码，最终实现幻灯片的迭代优化。

最终目标是实现一个全自动的`Reviewer Agent`和`Editor Agent`的双Agent协作模式，但初期我们将首先实现一个**人机协作（Human-in-the-Loop）模式**。

#### 2. 阶段性目标

1.  **阶段一：实现人机协作修订循环（当前焦点）**
    *   **角色**:
        *   **Reviewer**: 人类用户。
        *   **Editor**: `Editor Agent` (基于LLM)。
    *   **工作流程**:
        1.  初始工作流生成第一版 `.tex` 文件和对应的 `PDF`。
        2.  系统进入一个交互式修订循环，提示用户输入修改建议。
        3.  用户输入自然语言反馈（例如：“把第二页的标题改得更吸引人一些”）。
        4.  `Editor Agent`接收反馈，分析并定位到`.tex`文件中的相关代码。
        5.  `Editor Agent`生成并应用修改。
        6.  系统自动重新编译`.tex`文件，生成新版 `PDF`。
        7.  系统向用户展示结果（或结果路径），并询问是否需要进一步修改，从而继续循环或结束。

2.  **阶段二：开发并集成`Reviewer Agent`**
    *   **目标**: 用一个基于LLM的`Reviewer Agent`替代人类用户，实现全自动修订。
    *   **工作流程**: `Reviewer Agent`分析`PDF`（或`.tex`源码），提出结构化、可执行的修改建议，然后将其传递给`Editor Agent`。

#### 3. `Editor Agent` 核心组件设计与实现路线

`Editor Agent`是整个修订功能的核心。它的任务是**将自然语言反馈转化为对`.tex`文件的精确代码修改**。

##### 3.1. 输入

`Editor Agent`在每次调用时需要以下输入：

1.  **用户反馈 (User Feedback)**: 一段自然语言字符串，描述了期望的修改。
2.  **当前 `.tex` 文件路径 (Current TeX Path)**: 需要被修改的`.tex`文件的路径。
3.  **原始演示计划路径 (Original Plan Path)**: `plan.json`的路径。这可以为Agent提供高层级的结构化上下文，帮助它更好地理解“第二张幻灯片”或“关于结论的部分”这类模糊指令。
4.  **输出目录 (Output Directory)**: 用于存放新生成的`.tex`和`PDF`文件。

##### 3.2. 核心逻辑 (LLM Prompting Strategy)

`Editor Agent`的智能来源于一个精心设计的LLM调用。我们需要构建一个强大的Prompt，让LLM扮演一个精准的LaTeX代码编辑专家。

**Prompt模板结构**:

```
# Role
You are an expert LaTeX developer specializing in Beamer presentations. Your task is to act as an automated code editor. You will receive a user's modification request and the full content of a `.tex` file. You must intelligently locate the relevant code section and provide the precise old code to be replaced and the new code to replace it with.

# Context
The presentation is based on the following plan:
---
{plan_json_content}
---

# User's Request
The user wants to make the following change:
---
{user_feedback}
---

# Full TeX Source Code
Here is the complete `.tex` file you need to modify:
---
{current_tex_content}
---

# Your Task
Based on the user's request, identify the exact block of code in the TeX source that needs to be changed. Output a JSON object with two keys: "old_code" and "new_code".

- "old_code": This MUST be an EXACT, verbatim, multi-line string literal from the source code provided above. Include surrounding lines for unique identification.
- "new_code": This is the new code that will replace the old block.

# Example
If the user says "Change the title to 'A New Beginning'", and the source code has `\title{An Old Title}`, your output should be:
{
  "old_code": "...",
  "new_code": "..."
}

# Important Rules
- You MUST NOT change the overall structure of the document unless specifically asked.
- Your goal is to perform a targeted, local modification.
- The "old_code" MUST be unique within the document to avoid ambiguity.
- Respond ONLY with the JSON object. Do not add any explanations or conversational text.
```

##### 3.3. 实现步骤

1.  **创建新的工作流模块**:
    *   在`modules/`目录下创建一个新文件，例如 `interactive_reviser.py`。
    *   这个模块将包含`EditorAgent`类或相关函数。

2.  **实现`EditorAgent`**:
    *   创建一个`EditorAgent`类，其核心方法是 `revise(feedback, tex_path, plan_path)`。
    *   在此方法中：
        a.  读取`.tex`文件和`plan.json`文件的内容。
        b.  使用上述Prompt模板，构建完整的Prompt。
        c.  调用LLM（例如OpenAI API）并获取响应。
        d.  解析LLM返回的JSON，提取`old_code`和`new_code`。
        e.  **执行修改**: 读取原始`.tex`内容，使用字符串替换功能将`old_code`替换为`new_code`，然后将结果写入一个新的`.tex`文件（例如 `output_v2.tex`）。
        f.  **触发重新编译**: 复用`tex_workflow.py`中的编译逻辑，对新生成的`.tex`文件进行编译。
        g.  返回新文件的路径和成功状态。

3.  **修改`main.py`以集成交互循环**:
    *   在`main()`函数中，当初始的`run_tex_workflow`成功后，检查是否需要进入交互模式（可以为此添加一个新的命令行参数，如`--interactive-revise`）。
    *   如果进入交互模式，启动一个`while`循环：
        a.  提示用户输入反馈（或输入`exit`退出）。
        b.  调用`EditorAgent`的`revise`方法。
        c.  向用户报告结果（“修改成功，新文件位于...”，或“编译失败，错误信息为...”）。
        d.  更新当前`.tex`文件路径为新生成的文件路径，为下一次迭代做准备。

#### 4. 建议的代码结构

```
paper-to-beamer/
├── main.py                 # (需要修改)
├── modules/
│   ├── ...
│   ├── interactive_reviser.py # (新增) 存放EditorAgent
│   └── tex_workflow.py       # (可能需要复用其编译函数)
└── ...
```
