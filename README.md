# 📊 Paper-to-Beamer

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg?cacheSeconds=2592000)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**🤖 将学术论文 PDF 自动转换为 Beamer 演示幻灯片的智能工具**

_基于大型语言模型，支持多轮对话修改，让学术演示制作变得简单高效_

[🌍 English Version](./docs/README_EN.md) | [📖 代码文档](./CODEBASE.md) | [🎯 在线演示](#web界面使用)

</div>

---

<div align="center">
  <img src="static/themes/homepage.jpeg" alt="Paper-to-Beamer 预览" width="90%" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
</div>

## 🎯 项目简介

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white; margin: 20px 0;">

**Paper-to-Beamer** 是一个革命性的 AI 驱动工具，专为学术研究者设计。它能够智能分析 PDF 学术论文，自动提取关键信息，并生成专业的 Beamer 演示幻灯片。通过自然语言对话，您可以轻松定制和优化生成的演示文稿。

</div>

### ✨ 核心特性

<table style="width: 100%; border-collapse: collapse;">
<tr>
<td style="padding: 15px; border: 1px solid #e1e5e9; background: #f8f9fa;">

**🔍 智能 PDF 解析**

- 基于 marker-pdf 深度学习模型
- 精确提取文本、图像和结构信息
- 支持复杂学术论文格式

</td>
<td style="padding: 15px; border: 1px solid #e1e5e9; background: #f8f9fa;">

**🧠 内容智能分析**

- 自动识别论文结构和层次
- 提取关键图表和数据
- 生成结构化演示大纲

</td>
</tr>
<tr>
<td style="padding: 15px; border: 1px solid #e1e5e9; background: #ffffff;">

**📝 Beamer 代码生成**

- 完整的 LaTeX Beamer 代码
- 多种专业主题模板
- 自动排版和格式优化

</td>
<td style="padding: 15px; border: 1px solid #e1e5e9; background: #ffffff;">

**💬 多轮对话修改**

- 自然语言反馈修改
- 实时内容调整
- 个性化定制选项

</td>
</tr>
<tr>
<td style="padding: 15px; border: 1px solid #e1e5e9; background: #f8f9fa;">

**🌐 多语言支持**

- 中英文双语支持
- 本地化演示风格
- 智能语言检测

</td>
<td style="padding: 15px; border: 1px solid #e1e5e9; background: #f8f9fa;">

**🎨 丰富主题库**

- 多种 Beamer 专业主题
- 可视化主题预览
- 一键主题切换

</td>
</tr>
</table>

## 🚀 快速开始

### 📋 环境要求

<div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 10px 0;">

⚠️ **重要提醒**：请确保您的系统满足以下基本要求

</div>

| 组件          | 版本要求        | 说明                       |
| ------------- | --------------- | -------------------------- |
| 🐍 Python     | 3.8+            | 推荐使用 Python 3.9+       |
| 📄 LaTeX      | TeX Live/MiKTeX | 包含 pdflatex 和 beamer 包 |
| 🔑 OpenAI API | 有效密钥        | 支持 GPT-3.5/GPT-4         |

### 🛠️ 安装步骤

<details>
<summary><strong>📥 步骤1：克隆项目</strong></summary>

```bash
git clone https://github.com/wzsyyh/paper-to-beamer.git
cd paper-to-beamer
```

</details>

<details>
<summary><strong>🏗️ 步骤2：创建虚拟环境（推荐）</strong></summary>

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate
```

</details>

<details>
<summary><strong>📦 步骤3：安装依赖</strong></summary>

```bash
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>🤖 步骤4：下载AI模型</strong></summary>

<div style="background: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 8px;">

⚡ **首次使用前必须完成此步骤！**

</div>

```bash
pip install modelscope
python down_model.py
```

</details>

<details>
<summary><strong>🔐 步骤5：配置API密钥</strong></summary>

创建 `.env` 文件并添加您的 OpenAI API 密钥：

```bash
OPENAI_API_KEY=your_api_key_here
```

<div style="background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 8px; margin: 10px 0;">

🔒 **安全提醒**：切勿将包含真实 API 密钥的文件提交到公共仓库！

</div>

</details>

## 💻 使用指南

### 🌐 Web 界面使用

<div style="background: linear-gradient(45deg, #FF9A8B, #A8E6CF); padding: 20px; border-radius: 10px; margin: 20px 0;">

**🎉 推荐使用方式 - 简单直观的图形界面**

</div>

1. **🚀 启动服务**

   ```bash
   python app.py
   ```

2. **🌍 打开浏览器**

   - 访问：http://localhost:7860

3. **📤 上传论文**

   - 拖拽或选择 PDF 文件
   - 选择输出语言和演示主题

4. **⚡ 生成幻灯片**

   - 点击"生成演示幻灯片"按钮
   - 等待 AI 处理完成

5. **✏️ 修改优化**
   - 在反馈框中输入修改建议
   - 系统将自动优化幻灯片

### 🖥️ 命令行使用

<details>
<summary><strong>🎯 基础使用</strong></summary>

```bash
python main.py path/to/your/paper.pdf
```

</details>

<details>
<summary><strong>⚙️ 高级选项</strong></summary>

```bash
python main.py path/to/your/paper.pdf \
  --language zh \
  --model gpt-4o \
  --theme Madrid \
  --output-dir output
```

</details>

<details>
<summary><strong>💬 交互模式</strong></summary>

```bash
python main.py path/to/your/paper.pdf --interactive
```

</details>

<details>
<summary><strong>🔄 修订模式</strong></summary>

```bash
python main.py --revise \
  --original-plan=path/to/plan.json \
  --previous-tex=path/to/output.tex \
  --feedback="您的修改建议"
```

</details>

## 📁 项目架构

<div style="background: #f8f9fa; padding: 20px; border-radius: 10px; font-family: 'Courier New', monospace;">

```
📦 paper-to-beamer/
├── 🎯 main.py                    # 命令行主入口
├── 🌐 app.py                     # Web界面入口
├── 🔧 patch_openai.py            # API兼容性补丁
├── 📚 modules/                   # 核心模块
│   ├── 📄 pdf_parser.py          # PDF解析引擎
│   ├── 🧠 content_processor.py   # 内容处理器
│   ├── 📋 presentation_planner.py # 演示规划器
│   ├── 📝 tex_generator.py       # LaTeX生成器
│   ├── ✅ tex_validator.py       # 代码验证器
│   └── 🔄 tex_workflow.py        # 工作流管理
├── 🧪 tests/                     # 测试套件
├── 🛠️ utils/                     # 工具函数
├── 📤 output/                    # 输出目录
│   ├── 📊 raw/                   # 原始数据
│   ├── 📋 plan/                  # 演示计划
│   ├── 🖼️ images/                # 图片资源
│   └── 📝 tex/                   # LaTeX文件
├── 🎨 static/                    # 静态资源
│   └── 🖼️ themes/                # 主题预览
├── 📖 examples/                  # 示例文件
└── 📚 docs/                      # 项目文档
```

</div>

## 🎨 主题预览

<div align="center" style="margin: 20px 0;">

我们提供多种精美的 Beamer 主题，适应不同的演示场景和个人喜好

| 经典主题 | 现代主题    | 学术主题   |
| -------- | ----------- | ---------- |
| Madrid   | Metropolis  | Frankfurt  |
| Berlin   | Material    | Singapore  |
| Warsaw   | Montpellier | Copenhagen |

<div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0;">

💡 **提示**：所有主题预览图片存储在 `static/themes/` 目录中

</div>

</div>

## ❓ 常见问题

<details>
<summary><strong>🖼️ 图片无法正确显示？</strong></summary>

<div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 0;">

**解决方案：**

1. 确认已正确下载 marker-pdf 模型
2. 检查 `output/images/会话号/` 目录下是否存在图片文件
3. 验证图片路径格式是否正确

</div>

</details>

<details>
<summary><strong>🔑 API密钥配置问题？</strong></summary>

<div style="background: #d1ecf1; padding: 15px; border-radius: 8px; margin: 10px 0;">

**解决方案：**

1. 在项目根目录创建 `.env` 文件
2. 添加 `OPENAI_API_KEY=your_api_key_here`
3. 确保 API 密钥有效且有足够配额

</div>

</details>

<details>
<summary><strong>📄 LaTeX编译失败？</strong></summary>

<div style="background: #f8d7da; padding: 15px; border-radius: 8px; margin: 10px 0;">

**解决方案：**

1. 安装完整的 LaTeX 环境（TeX Live 或 MiKTeX）
2. 确保安装了 beamer 和 ctex 包（用于中文支持）
3. 检查系统 PATH 中是否包含 pdflatex

</div>

</details>

## 🤝 贡献指南

<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white; margin: 20px 0;">

我们欢迎任何形式的贡献！无论是 bug 报告、功能建议还是代码贡献，都能帮助这个项目变得更好。

</div>

### 🔧 开发环境设置

如果您想进行二次开发，请参考 [📖 代码库文档](./CODEBASE.md) 获取详细的开发指南。

### 🐛 Bug 报告

发现 bug？请通过以下方式报告：

- 📝 提交 [GitHub Issue](https://github.com/wzsyyh/paper-to-beamer/issues)
- 📧 发送邮件至：yangyuheng@westlake.edu.cn

## 📄 许可协议

<div style="background: #e8f5e8; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">

本项目采用 **MIT 许可协议**

- ✅ 允许商业使用
- ✅ 允许修改和分发
- ✅ 允许私人使用
- ⚠️ 二次开发需要提及本仓库
- ⚠️ 商业用途需联系原作者获得授权

</div>

## 📞 联系我们

<div align="center">

| 联系方式  | 信息                                                           |
| --------- | -------------------------------------------------------------- |
| 📧 邮箱   | yangyuheng@westlake.edu.cn                                     |
| 🐙 GitHub | [提交 Issue](https://github.com/wzsyyh/paper-to-beamer/issues) |
| 📖 文档   | [查看 Wiki](https://github.com/wzsyyh/paper-to-beamer/wiki)    |

</div>

## 🙏 致谢

感谢以下开源项目和贡献者：

- 🤖 [marker-pdf](https://github.com/VikParuchuri/marker) - PDF 解析核心
- 🦜 [LangChain](https://github.com/langchain-ai/langchain) - LLM 框架
- 🎨 [Gradio](https://github.com/gradio-app/gradio) - Web 界面
- 📝 [LaTeX/Beamer](https://github.com/josephwright/beamer) - 演示文稿框架

---

<div align="center">

**⭐ 如果这个项目对您有帮助，请给我们一个 Star！**

<img src="https://img.shields.io/github/stars/wzsyyh/paper-to-beamer?style=social" alt="GitHub stars">

**🔔 关注项目获取最新更新**

Made with ❤️ by [wzsyyh](https://github.com/wzsyyh)

</div>
