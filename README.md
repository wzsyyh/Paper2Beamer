# Paper-to-Beamer

将学术论文PDF自动转换为Beamer演示幻灯片的工具

[English Version](./docs/README_EN.md)

## 项目介绍

Paper-to-Beamer是一个基于人工智能的工具，可以将学术论文PDF自动转换为Beamer演示幻灯片。它使用大型语言模型分析论文内容，提取关键信息，并生成结构良好的演示文稿。该工具支持多轮对话修改，让用户能够通过自然语言反馈不断优化生成的幻灯片。

### 主要功能

- **PDF内容提取**：自动从PDF中提取文本、图像和结构信息
- **智能内容分析**：识别论文的标题、作者、摘要、章节结构和关键图表
- **演示计划生成**：根据论文内容生成结构化的演示计划
- **Beamer代码生成**：生成完整的LaTeX Beamer代码
- **多轮对话修改**：支持通过自然语言反馈修改生成的幻灯片
- **多种主题支持**：支持多种Beamer主题
- **中英文支持**：支持生成中文和英文演示文稿

## 安装指南

### 环境要求

- Python 3.8+
- LaTeX环境（推荐TeX Live或MiKTeX）
- OpenAI API密钥

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/wzsyyh/paper-to-beamer.git
cd paper-to-beamer
```

2. 创建虚拟环境（推荐）

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 设置OpenAI API密钥

创建`.env`文件，添加以下内容：

```
OPENAI_API_KEY=your_api_key_here
```

或者在环境变量中设置：

```bash
export OPENAI_API_KEY=your_api_key_here  # Linux/Mac
# 或
set OPENAI_API_KEY=your_api_key_here  # Windows
```

> **安全警告**：切勿将包含真实API密钥的`.env`或`env.local`文件提交到公共仓库！这些文件已在`.gitignore`中设置为忽略。

## 使用方法

### Web界面

1. 启动Web服务器

```bash
python app.py
```

2. 在浏览器中打开 http://localhost:7860

3. 上传PDF文件，选择语言和主题，点击"生成演示幻灯片"按钮

4. 等待处理完成，下载生成的PDF文件

5. 如需修改，在"提供修改建议"输入框中输入您的反馈并提交

### 命令行

基本用法：

```bash
python main.py path/to/your/paper.pdf
```

高级选项：

```bash
python main.py path/to/your/paper.pdf --language zh --model gpt-4o --theme Madrid --output-dir output
```

交互式模式：

```bash
python main.py path/to/your/paper.pdf --interactive
```

修订模式：

```bash
python main.py --revise --original-plan=path/to/plan.json --previous-tex=path/to/output.tex --feedback="您的修改建议"
```

测试模式：

```bash
python app.py --test path/to/paper.pdf --revise "请修改标题页，使标题居中显示"
```

## 常见问题

### 1. 编译失败

如果遇到编译失败，请检查：
- 是否安装了完整的LaTeX环境
- 是否安装了中文字体（如果生成中文演示文稿）
- 是否有足够的磁盘空间

### 2. 图片显示问题

如果图片无法正确显示：
- 确保PDF中的图片质量足够好
- 尝试使用不同的Beamer主题

### 3. API密钥问题

如果遇到API密钥相关错误：
- 确保API密钥正确设置
- 检查API密钥是否有足够的配额

## 二次开发

如果您想进行二次开发，请参考[代码库文档](./CODEBASE.md)。

## 许可证

本项目采用MIT许可证。二次开发时需要提及本仓库。用于商业用途的二次开发需要联系原作者获得授权。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交GitHub Issue
- 发送邮件至：yangyuheng@westlake.edu.cn

## 项目结构

```
paper-to-beamer/
├── main.py                  # 命令行主入口文件
├── app.py                   # Web界面入口文件
├── patch_openai.py          # OpenAI API兼容性补丁
├── modules/                 # 模块目录
│   ├── pdf_parser.py        # PDF解析模块
│   ├── content_processor.py # 内容处理模块
│   ├── presentation_planner.py # 演示计划模块
│   ├── tex_generator.py     # TEX生成模块
│   ├── tex_validator.py     # TEX验证模块
│   └── tex_workflow.py      # TEX工作流模块
├── tests/                   # 测试模块
├── utils/                   # 工具函数
├── output/                  # 输出文件目录
│   ├── raw/                 # 原始解析数据
│   ├── plan/                # 演示计划数据
│   └── tex/                 # 生成的TEX文件
├── static/                  # 静态资源目录
│   └── themes/              # Beamer主题预览图片
├── tools/                   # 工具脚本
├── examples/                # 示例论文
└── docs/                    # 文档
```

## 主题预览图片

Web界面中显示的Beamer主题预览图片存放在`static/themes/`目录中。每个主题对应一个PNG格式的预览图片，命名格式为`{theme_name}.png`。

如需添加新的主题预览图片，请手动创建相应的预览图片并放置在该目录下。

## 依赖版本说明

本项目使用了以下主要依赖：

- `langchain`和`openai`：用于与大语言模型交互
- `PyMuPDF`和`pdfplumber`：用于PDF解析
- `gradio`：用于构建Web界面

为了解决Gradio与Pydantic之间的兼容性问题，我们使用了最新版本的Gradio（5.0+），它支持Pydantic 2.0+。如果遇到兼容性问题，请确保使用最新版本的依赖：

```bash
pip install -U gradio openai langchain
```

## 注意事项

- 确保安装了完整的LaTeX环境，包括pdflatex和beamer包
- 对于中文输出，需要安装ctex包
- 解析效果可能因PDF格式和结构而异
- 对于复杂的数学公式，可能需要手动调整
- 确保OpenAI API密钥有效且配额充足

## 给同伴的指南：如何修改Prompt优化幻灯片生成效果

如果你想尝试不同的prompt来改进生成的幻灯片内容，可以按照以下步骤操作：

### 修改位置

在项目中有两个关键的prompt可以修改，它们都位于 `modules/presentation_planner.py` 文件中：

1. **内容提取Prompt** - 大约在第300行附近
   - 这个prompt负责从论文中提取关键内容，包括贡献点、方法论、结果和图表信息
   - 修改这个prompt可以改进对论文内容的理解和提取质量

2. **幻灯片规划Prompt** - 大约在第430行附近
   - 这个prompt负责规划演示幻灯片的结构和内容
   - 修改这个prompt可以改进幻灯片的内容丰富度、结构和图片使用

### 修改建议

#### 内容提取Prompt修改建议

- 增加对方法论部分的详细提取要求，比如细分为"问题定义"、"算法设计"、"实现细节"等
- 要求提取更多的结果数据点，比如具体的实验结果数字、比较数据等
- 增加对图表的上下文理解，要求模型解释每个图表在论文中的作用和意义

#### 幻灯片规划Prompt修改建议

- 调整幻灯片数量和分布，比如增加方法部分的幻灯片比例
- 增加每个幻灯片要点的数量和具体程度
- 提供更具体的图片使用指导，比如什么类型的内容应该配图
- 要求生成更具体的内容而非泛泛而谈的要点
- 增加对专业术语和公式的处理指导

### 运行测试

修改prompt后，可以通过以下命令运行测试：

```bash
python app.py --test
```

或者使用Web界面：

```bash
python app.py
```

然后在浏览器中访问 http://localhost:7860 进行测试。

### 评估效果

评估生成的幻灯片质量时，可以关注以下几点：

1. 内容的完整性和准确性
2. 幻灯片结构的合理性
3. 图片与内容的相关性
4. 要点的具体程度和信息量
5. 整体演示的逻辑流程

如果你发现某个prompt效果特别好，请记录下来并分享给团队！
