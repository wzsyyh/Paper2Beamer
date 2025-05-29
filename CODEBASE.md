# Paper-to-Beamer 代码库文档

本文档详细说明了 Paper-to-Beamer 项目的代码结构和各个组件的功能，便于开发者理解和二次开发。

## 项目结构

```
paper-to-beamer/
├── app.py                # Gradio Web界面
├── main.py               # 命令行入口
├── patch_openai.py       # OpenAI API补丁
├── modules/              # 核心功能模块
│   ├── pdf_parser.py            # PDF解析模块
│   ├── content_processor.py     # 内容处理模块
│   ├── presentation_planner.py  # 演示计划生成模块
│   ├── tex_generator.py         # TEX代码生成模块
│   ├── tex_validator.py         # TEX验证和编译模块
│   ├── tex_workflow.py          # TEX工作流模块
│   └── revision_tex_generator.py # 修订版TEX生成模块
├── static/               # 静态资源
│   └── themes/           # Beamer主题预览
├── output/               # 输出目录
│   ├── raw/              # 原始提取内容
│   ├── plan/             # 演示计划
│   └── tex/              # TEX和PDF输出
└── examples/             # 示例文件
```

## 核心模块说明

### 1. PDF解析模块 (`pdf_parser.py`)

负责从PDF文件中提取文本、图像和结构信息。

**主要功能**：
- 使用PyMuPDF提取PDF页面内容
- 提取文本和图像
- 保存提取的内容为JSON格式

**主要类和函数**：
- `extract_pdf_content()`: 提取PDF内容的便捷函数

### 2. 内容处理模块 (`content_processor.py`)

处理从PDF中提取的原始内容，进行结构化和优化。

**主要功能**：
- 提取论文标题、作者、摘要等基本信息
- 识别章节结构
- 提取图表信息
- 提取参考文献

**主要类和函数**：
- `ContentProcessor`: 内容处理器类
- `process_content()`: 处理内容的便捷函数

### 3. 演示计划生成模块 (`presentation_planner.py`)

根据处理后的内容生成演示幻灯片计划。

**主要功能**：
- 确定演示文稿的整体结构
- 规划每张幻灯片的内容
- 选择重要图表
- 支持与用户交互，优化演示计划

**主要类和函数**：
- `PresentationPlanner`: 演示计划生成器类
- `generate_presentation_plan()`: 生成演示计划的便捷函数
- `continue_conversation()`: 处理用户反馈，更新演示计划

### 4. TEX生成模块 (`tex_generator.py`)

将演示计划转换为完整的Beamer TEX代码。

**主要功能**：
- 生成完整的Beamer TEX代码
- 处理图片引用
- 支持多种Beamer主题
- 支持中英文演示文稿

**主要类和函数**：
- `TexGenerator`: TEX生成器类
- `generate_tex()`: 生成TEX代码的便捷函数

### 5. TEX验证和编译模块 (`tex_validator.py`)

验证和编译生成的TEX代码，确保可以正确生成PDF。

**主要功能**：
- 验证TEX代码语法
- 编译TEX代码生成PDF
- 处理编译错误
- 修复常见问题

**主要类和函数**：
- `TexValidator`: TEX验证器类
- `validate()`: 验证并编译TEX代码
- `fix_tex_code()`: 修复TEX代码中的错误

### 6. TEX工作流模块 (`tex_workflow.py`)

协调整个TEX生成和编译过程。

**主要功能**：
- 管理从演示计划到PDF的完整流程
- 处理图片复制和预处理
- 支持多次重试编译
- 支持修订版TEX的生成和编译

**主要类和函数**：
- `TexWorkflow`: TEX工作流类
- `run_tex_workflow()`: 运行TEX工作流的便捷函数
- `run_revision_tex_workflow()`: 运行修订版TEX工作流

### 7. 修订版TEX生成模块 (`revision_tex_generator.py`)

基于用户反馈修改演示文稿。

**主要功能**：
- 根据用户反馈修改TEX代码
- 保持原有演示文稿的结构和风格
- 支持多轮修订

**主要类和函数**：
- `RevisionTexGenerator`: 修订版TEX生成器类
- `generate_revised_tex()`: 生成修订版TEX代码
- `save_revised_tex()`: 保存修订版TEX代码

## 入口文件说明

### 1. 命令行入口 (`main.py`)

提供命令行接口，支持批处理和自动化。

**主要功能**：
- 解析命令行参数
- 协调整个处理流程
- 支持交互式优化
- 支持修订模式

**主要函数**：
- `main()`: 主函数
- `interactive_dialog()`: 交互式对话函数
- `test_with_example()`: 测试函数

### 2. Web界面 (`app.py`)

提供基于Gradio的Web界面，方便用户使用。

**主要功能**：
- 上传PDF文件
- 选择语言、模型和主题
- 显示生成结果
- 支持多轮对话修改

**主要函数**：
- `create_ui()`: 创建Web界面
- `process_pdf()`: 处理PDF文件
- `revise_presentation()`: 修订演示文稿

## 辅助文件说明

### 1. OpenAI API补丁 (`patch_openai.py`)

修补OpenAI API，处理网络问题和API变更。

**主要功能**：
- 处理API超时
- 支持代理设置
- 兼容不同版本的API

## 二次开发说明

1. **修改提示词**：
   - 如需调整生成的演示文稿风格，可修改`tex_generator.py`中的提示模板
   - 如需调整修订逻辑，可修改`revision_tex_generator.py`中的提示模板

2. **添加新主题**：
   - 在`static/themes`目录中添加新主题的预览图
   - 在`app.py`中的`AVAILABLE_THEMES`列表中添加新主题

3. **扩展功能**：
   - 添加新的内容处理逻辑可修改`content_processor.py`
   - 添加新的演示计划生成逻辑可修改`presentation_planner.py`
   - 添加新的TEX生成逻辑可修改`tex_generator.py`

## 版权声明

本代码库采用MIT许可证开源。二次开发时需要提及本仓库。用于商业用途的二次开发需要联系原作者获得授权。 