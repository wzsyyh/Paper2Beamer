# 代码库结构与核心模块说明

## 顶层目录结构
```
paper-to-beamer/
├── app.py                  # Gradio Web界面主入口
├── main.py                 # 命令行主入口
├── down_model.py           # maker-pdf模型下载脚本
├── requirements.txt        # 依赖包列表
├── README.md               # 中文说明文档
├── CODEBASE.md             # 代码结构与开发说明
├── patch_openai.py         # OpenAI API兼容性补丁
├── modules/                # 核心功能模块
├── utils/                  # 工具与辅助模块
├── output/                 # 所有输出文件目录
├── static/                 # 静态资源（主题图片等）
├── examples/               # 示例PDF文件
├── docs/                   # 英文及开发文档
└── .gitignore, LICENSE 等
```

---

## 主要输出目录
- `output/images/<session_id>/`：所有自动提取的图片（maker-pdf模型）
- `output/plan/<session_id>/`：演示计划JSON
- `output/tex/<session_id>/`：生成的LaTeX/TEX文件及PDF
- `output/raw/<session_id>/`：原始内容提取结果

---

## 依赖与模型
- **图片提取依赖 [maker-pdf (marker-pdf)](https://modelscope.cn/models/Lixiang/marker-pdf/summary) 深度学习模型**
- 首次使用前需运行：
  ```bash
  pip install modelscope
  python down_model.py
  ```
- 依赖包详见 `requirements.txt`

---

## modules/ 目录核心模块
- `raw_extractor.py`  
  PDF解析与图片提取（基于maker-pdf），所有图片统一保存到 `output/images/<session_id>/`
- `pdf_parser.py`  
  统一入口，调用 `raw_extractor` 完成PDF内容提取
- `content_processor.py`  
  对原始内容进行结构化、章节、图表等信息处理
- `presentation_planner.py`  
  调用大模型分析内容，生成演示计划（JSON），只引用真实存在的图片
- `tex_generator.py`  
  生成Beamer/LaTeX代码，图片路径规范
- `tex_validator.py`  
  验证/编译LaTeX，检查图片存在性
- `tex_workflow.py`  
  协调全流程（计划→TEX→编译→PDF）
- `revision_tex_generator.py`  
  支持基于用户反馈的多轮修订

---

## utils/ 目录
- `pdf_validator.py`  
  PDF内容提取验证工具等

---

## static/themes/
- 各类Beamer主题预览图片，Web界面可选

---

## 主要使用流程
1. 安装依赖  
   `pip install -r requirements.txt`
2. 下载maker-pdf模型  
   `pip install modelscope`  
   `python down_model.py`
3. 运行主程序  
   - Web界面：`python app.py`
   - 命令行：`python main.py your_paper.pdf`
4. 所有图片、计划、TEX、PDF等输出均在 `output/` 目录下，图片路径全程规范一致

---

## 开发与二次开发建议
- **Prompt优化**：如需调整内容提取/幻灯片规划效果，可修改 `modules/presentation_planner.py` 中的相关Prompt
- **主题扩展**：在 `static/themes/` 目录添加主题图片即可
- **图片处理/模型升级**：可在 `raw_extractor.py` 中集成新模型或优化图片筛选逻辑

---

## 注意事项
- 所有图片只保存在 `output/images/<session_id>/`，后续所有流程均直接引用该目录
- 若图片未能正确提取，请确认maker-pdf模型已下载且 `models/` 目录存在
- LLM相关功能需配置 `OPENAI_API_KEY` 到 `.env`
- 复杂公式、特殊PDF结构可能需手动微调TEX

---

如需更详细的开发接口说明或有其他补充需求，请随时告知！ 