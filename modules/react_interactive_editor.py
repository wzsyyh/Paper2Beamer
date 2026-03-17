#!/usr/bin/env python3
"""
React Interactive Editor - 重写版本
基于智能语义定位，不依赖页码标记系统
"""

import json
import re
import subprocess
import os
import webbrowser
import openai
from difflib import unified_diff
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)

class ReactInteractiveEditor:
    """
    智能化的LaTeX编辑器，使用ReAct模式进行交互式修改
    基于文档语义理解而不是页码标记进行定位
    """
    
    def __init__(self, tex_file_path, source_content=None, model_name="gpt-4o"):
        """
        初始化编辑器
        
        Args:
            tex_file_path: LaTeX文件路径
            source_content: 原始PDF解析内容（可选，用于内容扩展）
            model_name: 语言模型名称（默认："gpt-4o"）
        """
        self.tex_file_path = tex_file_path
        self.source_content = source_content
        self.model_name = model_name
        self.conversation_history = []
        
        # 读取文档内容
        with open(tex_file_path, 'r', encoding='utf-8') as f:
            self.document_content = f.read()
        
        # 生成文档结构地图
        print("   正在生成文档结构地图...")
        self.document_map = self._build_document_map()
        
        print(f"✓ 已加载并预处理文档: {self.tex_file_path}")
        print(f"  文档大小: {len(self.document_content)} 字符")
        if source_content:
            print(f"  已提供原始PDF内容，支持内容扩展功能")
        print()

    def _build_document_map(self):
        """
        构建文档的结构化地图，帮助LLM理解文档结构
        
        Returns:
            dict: 包含slides列表的文档地图，或None（如果生成失败）
        """
        try:
            system_prompt = """
你是一个LaTeX文档结构分析专家。请分析给定的LaTeX Beamer文档，为每一页幻灯片创建一个结构化的地图。

重要要求：
1. **识别所有类型的页面**：标题页(\\titlepage)、目录页(\\tableofcontents)、普通frame页面
2. **按出现顺序编号**：从1开始，包括所有类型的页面
3. **提取关键信息**：标题、章节、内容概要、图片、表格等

输出格式为JSON，包含以下结构：
{
  "total_slides": 总页数,
  "slides": [
    {
      "slide_number": 页码(从1开始),
      "type": "titlepage|outline|frame",
      "title": "页面标题",
      "section": "所属章节(如果有)",
      "content_summary": "内容概要",
      "has_image": true/false,
      "image_files": ["图片文件名列表"],
      "has_table": true/false,
      "key_concepts": ["关键概念列表"]
    }
  ]
}

请仔细分析，确保不遗漏任何页面。
"""
            
            prompt = f"请分析以下LaTeX文档并生成结构化地图：\n```latex\n{self.document_content}\n```"
            
            result_json = self._call_llm([{"role": "user", "content": prompt}], system_prompt, json_mode=True)
            
            if result_json and "slides" in result_json:
                print(f"   ✓ 已生成文档地图：{result_json['total_slides']} 页幻灯片")
                return result_json
            else:
                print("   ⚠️ 文档地图生成失败，将使用备用定位方式")
                return None
                
        except Exception as e:
            print(f"   ❌ 文档地图生成出错: {e}")
            return None

    def _call_llm(self, messages, system_prompt, temperature=0.1, json_mode=False):
        """
        通用LLM调用函数
        
        Args:
            messages: 消息列表
            system_prompt: 系统提示词
            temperature: 温度参数
            json_mode: 是否使用JSON模式
            
        Returns:
            dict|str: LLM返回结果
        """
        try:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            response_format = {"type": "json_object"} if json_mode else {"type": "text"}
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=full_messages,
                temperature=temperature,
                response_format=response_format
            )
            content = response.choices[0].message.content
            return json.loads(content) if json_mode else content
        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            return None

    def locate_code_snippet(self, description):
        """
        智能定位代码片段，支持多目标定位
        
        Args:
            description: 用户描述
            
        Returns:
            dict: {
                "snippets": [{"slide_number": int, "code": str, "description": str}],
                "analysis": "分析结果"
            }
        """
        print(f"ReAct Agent [定位中]... {description}")
        
        system_prompt = """
你是一个LaTeX代码定位专家。你的任务是根据用户描述，在LaTeX源码中找到最相关的代码片段。

你有一个"文档地图"来帮助理解文档结构。请先根据地图理解用户要求，然后在源码中找到对应的完整代码块。

重要规则：
1. **多目标支持**: 如果用户描述涉及多个页面（如"第6页和第7页"），请找到所有相关的代码片段
2. **完整片段**: 必须返回完整的代码块（如完整的frame环境，从\\begin{frame}到\\end{frame}）
3. **智能匹配**: 即使页码不准确，也要根据内容进行语义匹配
4. **结构理解**: 理解标题页、目录页、普通frame的区别

输出格式为JSON：
{
  "snippets": [
    {
      "slide_number": 页码,
      "code": "完整的代码片段",
      "description": "对这个片段的简要描述"
    }
  ],
  "analysis": "对所有找到片段的总体分析，特别是多个片段之间的关系"
}

如果只找到一个片段，snippets数组也只包含一个元素。如果没找到，返回空数组。
"""
        
        # 构建包含文档地图的完整上下文
        context_parts = []
        
        if self.document_map:
            map_summary = f"文档地图（共{self.document_map['total_slides']}页）:\n"
            for slide in self.document_map['slides']:
                map_summary += f"第{slide['slide_number']}页: {slide['type']} - {slide.get('title', 'N/A')}"
                if slide.get('section'):
                    map_summary += f" (章节: {slide['section']})"
                if slide.get('has_image'):
                    map_summary += f" [含图片: {', '.join(slide.get('image_files', []))}]"
                if slide.get('has_table'):
                    map_summary += " [含表格]"
                map_summary += f"\n  概要: {slide.get('content_summary', '无')}\n"
            context_parts.append(map_summary)
        else:
            context_parts.append("⚠️ 文档地图不可用，将基于源码直接分析")
        
        context_parts.append(f"LaTeX源码:\n```latex\n{self.document_content}\n```")
        full_context = "\n\n".join(context_parts)
        
        prompt = f"{full_context}\n\n用户请求: {description}"
        
        result_json = self._call_llm([{"role": "user", "content": prompt}], system_prompt, json_mode=True)
        
        if result_json and result_json.get("snippets"):
            snippets = result_json.get("snippets", [])
            analysis = result_json.get("analysis", "")
            
            print(f"   ✓ 找到 {len(snippets)} 个代码片段")
            if analysis:
                print(f"   📋 分析: {analysis}")
            
            for i, snippet_info in enumerate(snippets, 1):
                slide_num = snippet_info.get("slide_number", "未知")
                desc = snippet_info.get("description", "")
                code = snippet_info.get("code", "")
                print(f"   {i}. 第{slide_num}页: {desc} ({len(code)} 字符)")
            
            return result_json
        else:
            print("   ❌ 未能定位到相关代码")
            return {"snippets": [], "analysis": "未找到匹配的代码片段"}
    
    def generate_modified_code(self, original_snippet, instruction, full_document_context):
        """
        根据指令生成修改后的代码
        
        Args:
            original_snippet: 原始代码片段
            instruction: 修改指令
            full_document_context: 完整文档上下文
            
        Returns:
            str: 修改后的代码，或None（如果失败）
        """
        print(f"ReAct Agent [修改中]... {instruction}")
        
        system_prompt = """
你是一个顶级的LaTeX代码编辑专家。你会收到一段原始的LaTeX代码片段、一条修改指令，以及完整的文档内容作为参考。

**严格规则**：
1. **只修改必要部分**: 你MUST ONLY修改与指令直接相关的部分。绝不能返回整个文档或大段无关代码。
2. **保持代码片段范围**: 返回的代码长度应该与原始片段相似，不能突然变成整个文档。
3. **理解意图**: 完全理解修改指令的意图。
4. **智能分析**: 如果涉及表格内容缺失或表格修复问题，优先检查原始PDF数据中的tables字段，获取完整的表格数据。
5. **数据驱动修复**: 对于表格问题，不要只修复LaTeX语法，要根据原始数据补充完整的表格内容。
6. **参考上下文**: 如果修改需要从文档的其他部分获取信息，请在完整文档中查找相关信息。
7. **利用原始数据**: 如果指令要求添加新内容或扩展现有内容，你可以参考原始PDF解析的数据来生成准确、丰富的内容。
8. **智能图片选择**: 如果涉及图片重复使用问题，分析当前页面的内容主题，从完整文档中找到所有可用的图片文件，选择最符合当前页面主题的图片。
9. **精确修改**: 只修改需要修改的部分，保持其余代码不变。
10. **代码质量**: 确保生成的代码语法正确，格式良好。

特殊情况处理：
- **图片问题**: 只调整 `width`, `height`, `scale` 参数来控制大小，不要修改其他内容
- **图片重复使用问题**: 如果发现多个页面使用了相同的图片文件，需要分析每个页面的内容主题，为不同页面选择更合适的图片文件。检查完整文档中是否有其他可用的图片文件。
- **表格格式问题**: 调整 `\\textwidth` 参数、使用 `\\scriptsize` 或调整列定义
- **表格缺失内容问题**: 查看原始PDF数据中的"tables"字段，补充完整内容
- **目录页问题**: 检查 `\\section{}` 定义

**关键约束**: 返回的modified_code必须：
- 是一个完整的、可编译的LaTeX代码片段
- 长度与原始片段相近（不能是整个文档）
- 只包含与修改指令相关的更改

输出格式为JSON，包含`modified_code`字段。`modified_code`的值必须是一个字符串，不能是列表或其他类型。
"""
        
        # 构建包含原始PDF内容的完整上下文
        context_parts = [f"完整的LaTeX文档内容:\n```latex\n{full_document_context}\n```"]
        
        if self.source_content:
            context_parts.append(f"原始PDF解析内容（用于扩展功能）:\n```json\n{json.dumps(self.source_content, ensure_ascii=False, indent=2)}\n```")
        
        full_context = "\n\n".join(context_parts)
        
        prompt = f"{full_context}\n\n需要修改的代码片段:\n```latex\n{original_snippet}\n```\n\n请根据以下指令修改它:\n{instruction}"
        
        result_json = self._call_llm([{"role": "user", "content": prompt}], system_prompt, json_mode=True)
        
        if not result_json:
            print("❌ LLM未能生成有效的响应")
            return None
            
        modified_code = result_json.get("modified_code")
        
        # 增加健壮性：处理LLM可能返回的嵌套JSON字符串
        try:
            nested_data = json.loads(modified_code)
            if isinstance(nested_data, dict) and "modified_code" in nested_data:
                print("   ⚠️ 检测到嵌套的JSON响应，正在提取内部内容...")
                modified_code = nested_data["modified_code"]
        except (json.JSONDecodeError, TypeError):
            pass # 正常继续
        
        # 确保返回的是字符串类型
        if isinstance(modified_code, list):
            print("⚠️ 检测到LLM返回了列表，尝试转换为字符串")
            modified_code = '\n'.join(str(item) for item in modified_code)
        elif not isinstance(modified_code, str):
            print(f"❌ LLM返回了无效的类型: {type(modified_code)}")
            return None
            
        # 添加安全检查：防止LLM返回整个文档
        original_length = len(original_snippet)
        modified_length = len(modified_code)
        
        # 如果修改后的代码长度超过原始代码的3倍，可能是异常情况
        if modified_length > original_length * 3:
            print(f"⚠️ 警告：修改后的代码长度异常 ({modified_length} vs {original_length})")
            print("这可能表明LLM返回了过多的代码。")
            
            # 检查是否包含文档开头的标识符
            if "\\documentclass" in modified_code and "\\begin{document}" in modified_code:
                print("❌ 检测到LLM错误返回了完整文档，拒绝此次修改")
                return None
        
        return modified_code
    
    def _find_and_replace_frame(self, original_snippet, modified_snippet):
        """
        在文档中查找并替换代码片段（不依赖页码标记）
        
        Args:
            original_snippet: 原始代码片段
            modified_snippet: 修改后的代码片段
            
        Returns:
            tuple: (success: bool, updated_snippet: str)
        """
        try:
            # 直接在文档中查找原始片段
            if original_snippet in self.document_content:
                # 执行替换
                old_length = len(self.document_content)
                self.document_content = self.document_content.replace(original_snippet, modified_snippet, 1)
                new_length = len(self.document_content)
                
                if old_length != new_length or original_snippet != modified_snippet:
                    print(f"✓ 修改已成功应用到内存中的文档")
                    print(f"   文档长度变化: {old_length} -> {new_length} ({new_length - old_length:+d})")
                    
                    # 如果文档结构发生显著变化，重新生成地图
                    if abs(new_length - old_length) > 50:  # 阈值可调整
                        print("🔄 检测到文档结构变化，重新生成文档地图...")
                        self.document_map = self._build_document_map()
                    
                    return True, modified_snippet
                else:
                    print("✓ 代码内容无变化，跳过替换。")
                    return True, modified_snippet
            else:
                print("❌ 在文档中未找到原始代码片段")
                print("💡 这可能是由于文档在之前的修改中已经改变")
                return False, original_snippet
                
        except Exception as e:
            print(f"❌ 替换过程中出错: {e}")
            return False, original_snippet
    
    def show_diff_and_get_confirmation(self, original_snippet, modified_snippet):
        """
        显示diff并请求用户确认
        
        Args:
            original_snippet: 原始代码
            modified_snippet: 修改后代码
            
        Returns:
            bool: 用户是否确认
        """
        if not isinstance(original_snippet, str) or not isinstance(modified_snippet, str):
            print(f"❌ 参数类型错误")
            return False

        diff = unified_diff(
            original_snippet.splitlines(keepends=True),
            modified_snippet.splitlines(keepends=True),
            fromfile='original', tofile='modified',
        )
        
        print("\n--- 建议的修改 ---")
        diff_str = "".join(diff)
        if not diff_str.strip():
            print("🤔 未检测到代码变化。")
            return False

        for line in diff_str.splitlines():
            if line.startswith('---') or line.startswith('+++'):
                continue
            elif line.startswith('-'):
                print(f"\033[91m{line}\033[0m")  # 红色
            elif line.startswith('+'):
                print(f"\033[92m{line}\033[0m")  # 绿色  
            elif line.startswith('@@'):
                print(f"\033[94m{line}\033[0m")  # 蓝色
            else:
                print(line)
        
        print("--------------------")
        
        while True:
            response = input("您接受这个修改吗？(y/n/c) [y]: ").strip().lower()
            if response in ['', 'y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            elif response in ['c', 'cancel']:
                return False
            else:
                print("请输入 y(是)、n(否) 或 c(取消)")

    def decide_next_action(self):
        """
        基于对话历史决定下一步行动
        
        Returns:
            dict: 决策结果
        """
        print("ReAct Agent [思考中]... 正在分析您的需求。")
        
        system_prompt = """
你是一个顶级的LaTeX编辑助手。你的任务是分析与用户的对话历史，并决定下一步行动。

重要能力说明：
- 你可以修改现有幻灯片的内容
- 你也可以基于原始论文内容添加新的幻灯片或扩展现有内容
- 当用户要求添加内容时，你可以参考原始PDF解析的数据
- **你具备全局视野，能识别需要跨区域修改的问题**
- **对于表格问题，你能智能分析是语法问题还是数据完整性问题**
- **对于图片重复使用问题，你能分析整个文档中的图片使用情况，为不同页面选择合适的图片**

判断规则：
1. **分析历史**: 查看完整的对话历史，理解用户的最终意图。
2. **识别问题类型**:
   - **局部问题**: 只影响特定页面的问题（如调整图片大小）
   - **全局问题**: 需要修改多个位置才能解决的问题（如目录显示、章节结构）
   - **数据问题**: 表格内容缺失、数据不完整等需要从原始数据源补充的问题
   - **图片重复问题**: 多个页面使用相同图片文件的问题，需要分析所有相关页面并选择合适的替代图片
3. **智能分析表格问题**:
   - 如果用户提到"表格缺失内容"、"表格数据不全"等，优先考虑从原始数据补充
   - 制定计划时应包含检查和利用原始PDF数据的步骤
4. **判断清晰度**:
   - 如果用户的最新请求**足够清晰**，可以转化为具体操作，则制定一个执行计划。
   - 如果用户的请求**模糊不清**，则必须提出一个具体的问题来澄清用户的意图。

5. **输出格式**: 必须以JSON格式输出。
   - 如果指令清晰，输出: `{"action": "plan", "plan": [...]}`.
     - **`action` 字段可以是 "locate", "modify", "insert", 或 "delete"**。
     - 使用 "locate" 来定位整个文档结构或多个相关区域
     - 使用 "insert" 来在指定位置插入新内容（如新幻灯片）
     - 使用 "delete" 来删除指定内容（如删除幻灯片、段落等）
     - 对于全局性问题（如目录显示），应该包含 "locate" 步骤
     - 对于表格内容问题，描述中应明确提及从原始数据补充内容
     - 示例1（局部修改）: `[{"step": 1, "action": "locate", "description": "定位第4页的幻灯片。"}, {"step": 2, "action": "modify", "description": "缩小该页插图的尺寸。"}]`
     - 示例2（插入内容）: `[{"step": 1, "action": "locate", "description": "定位第3页作为插入参考点。"}, {"step": 2, "action": "insert", "description": "在第3页后插入两页背景知识幻灯片，内容包括LVLM基础概念和挑战介绍。"}]`
     - 示例3（删除内容）: `[{"step": 1, "action": "locate", "description": "定位第5页和第6页的幻灯片。"}, {"step": 2, "action": "delete", "description": "删除这两页重复的内容。"}]`
     - 示例4（全局问题）: `[{"step": 1, "action": "locate", "description": "分析整个文档的章节结构和目录相关代码。"}, {"step": 2, "action": "modify", "description": "修复章节定义以确保目录正确显示。"}]`
     - 示例5（表格数据问题）: `[{"step": 1, "action": "locate", "description": "定位第9页的幻灯片中的表格。"}, {"step": 2, "action": "modify", "description": "从原始PDF数据中获取完整的表格内容，补充所有缺失的列和数据。"}]`
     - 示例6（图片重复问题）: `[{"step": 1, "action": "locate", "description": "定位使用相同图片的多个页面。"}, {"step": 2, "action": "modify", "description": "根据页面内容主题，为重复使用图片的页面选择更合适的替代图片。"}]`
   - 如果指令模糊，输出: `{"action": "clarify", "question": "请问您具体想怎么修改呢？"}`
"""
        decision_json = self._call_llm(self.conversation_history, system_prompt, json_mode=True)
        return decision_json

    def _compile_to_pdf(self):
        """
        编译LaTeX文件生成PDF
        
        Returns:
            str: PDF文件路径，或None（如果失败）
        """
        tex_path = self.tex_file_path
        output_dir = os.path.dirname(tex_path)
        base_name = os.path.basename(tex_path)
        
        # 获取项目根目录（paper-to-beamer目录）
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
        # 使用相对于项目根目录的路径，这更健壮
        relative_tex_path = os.path.relpath(tex_path, project_root)
        relative_output_dir = os.path.relpath(output_dir, project_root)
        
        print("\n--- 正在编译PDF，请稍候 ---")
        print(f"   工作目录: {project_root}")
        print(f"   编译文件: {relative_tex_path}")
        print(f"   输出目录: {relative_output_dir}")
        
        for i in range(2):
            print(f"编译第 {i+1}/2 次...")
            try:
                # 在项目根目录运行，并使用相对路径
                process = subprocess.run(
                    ["xelatex", "-shell-escape", "-interaction=nonstopmode", f"-output-directory={relative_output_dir}", relative_tex_path],
                    cwd=project_root, capture_output=True, text=True, check=True
                )
                print(f"✓ 第 {i+1} 次编译成功")
            except subprocess.CalledProcessError as e:
                print(f"❌ 第 {i+1} 次编译失败")
                print("错误信息:")
                print(e.stdout[-1000:] if e.stdout else "无标准输出")
                print(e.stderr[-1000:] if e.stderr else "无错误输出")
                return None
            except FileNotFoundError:
                print("❌ 找不到 xelatex 命令。请确保已安装 LaTeX 环境。")
                return None
        
        pdf_path = os.path.join(output_dir, os.path.splitext(base_name)[0] + '.pdf')
        if os.path.exists(pdf_path):
            print(f"✅ 编译成功！PDF已生成: {pdf_path}")
            return pdf_path
        else:
            print("❌ 编译完成但未找到PDF文件。")
            return None

    def run_interactive_session(self):
        """
        运行交互式编辑会话 - 新版本实现
        """
        print("=== 交互式 LaTeX 编辑器 (ReAct 模式) ===")
        print("请用自然语言描述您想要的修改。您可以：")
        print("• 修改现有幻灯片的内容")
        if self.source_content:
            print("• 基于原始论文添加新的幻灯片或扩展内容")
        print("• 输入 'quit' 退出")
        print()
        
        while True:
            try:
                user_input = input("您: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    print("再见！")
                    break
                if not user_input: 
                    continue

                self.conversation_history.append({"role": "user", "content": user_input})
                
                decision = self.decide_next_action()
                
                if not decision or "action" not in decision:
                    print("❌ 无法理解您的指令，请换一种方式表述。")
                    self.conversation_history.append({"role": "assistant", "content": "抱歉，我无法理解您的指令。"})
                    continue

                if decision["action"] == "clarify":
                    question = decision.get("question", "请提供更多细节。")
                    print(f"Agent: {question}")
                    self.conversation_history.append({"role": "assistant", "content": question})
                    continue
                
                if decision["action"] == "plan":
                    plan = decision.get("plan")
                    if not plan:
                        print("❌ 计划生成失败。")
                        continue
                    
                    print("\n✓ 已生成执行计划:")
                    for step in plan:
                        print(f"  - 步骤 {step['step']} ({step['action']}): {step['description']}")
                    print()

                    # 执行计划
                    self._execute_plan(plan)
                    
                    # 询问是否保存
                    self._save_document_if_requested()
                    
                    # 重置对话历史，开始新的任务
                    self.conversation_history = []
                    print("\n" + "="*50)
                    print("可以开始新的修改任务了。")

            except KeyboardInterrupt:
                print("\n再见！")
                break
            except Exception as e:
                print(f"❌ 出现严重错误: {e}")
                import traceback
                traceback.print_exc()

    def _execute_plan(self, plan):
        """
        执行计划 - 新版本实现
        
        Args:
            plan: 执行计划列表
        """
        locate_results = None
        
        for step in plan:
            print(f"--- 正在执行步骤 {step['step']}/{len(plan)} ---")
            
            if step['action'] == 'locate':
                # 使用新的智能定位系统
                locate_results = self.locate_code_snippet(step['description'])
                if not locate_results or not locate_results.get("snippets"):
                    print("❌ 定位失败，中止计划。")
                    break
                print("✓ 定位成功！")
                
            elif step['action'] == 'modify':
                if locate_results and locate_results.get("snippets"):
                    # 基于定位结果进行修改 - 一次处理一个片段
                    self._execute_modifications(locate_results, step['description'])
                else:
                    print("❌ 修改失败，前一步的定位未成功。")
                    break
                    
            elif step['action'] == 'insert':
                if locate_results and locate_results.get("snippets"):
                    # 执行插入操作
                    self._execute_insert(locate_results, step['description'])
                else:
                    print("❌ 插入失败，前一步的定位未成功。")
                    break
                    
            elif step['action'] == 'delete':
                if locate_results and locate_results.get("snippets"):
                    # 执行删除操作
                    self._execute_delete(locate_results, step['description'])
                else:
                    print("❌ 删除失败，前一步的定位未成功。")
                    break
                    
            else:
                print(f"❌ 未知的操作类型: {step['action']}")
                break

    def _execute_modifications(self, locate_results, base_instruction):
        """
        执行修改操作
        
        Args:
            locate_results: 定位结果
            base_instruction: 基础修改指令
        """
        snippets = locate_results["snippets"]
        analysis = locate_results.get("analysis", "")
        
        print(f"   将基于 {len(snippets)} 个定位片段进行修改")
        if analysis:
            print(f"   分析结果: {analysis}")
        
        # 对每个片段逐一修改
        for i, snippet_info in enumerate(snippets):
            slide_num = snippet_info.get("slide_number", "未知")
            original_code = snippet_info.get("code", "")
            description = snippet_info.get("description", "")
            
            print(f"\n   修改片段 {i+1}/{len(snippets)} (第{slide_num}页):")
            
            # 构建包含完整上下文的修改指令
            contextual_instruction = f"{base_instruction}\n\n上下文分析: {analysis}\n\n针对第{slide_num}页的具体修改: {description}"
            
            modified_snippet = self.generate_modified_code(original_code, contextual_instruction, self.document_content)
            if not modified_snippet:
                print(f"   ❌ 第{slide_num}页修改失败，跳过")
                continue
                
            if self.show_diff_and_get_confirmation(original_code, modified_snippet):
                print(f"\n   --- 正在修改第{slide_num}页 ---")
                success, _ = self._find_and_replace_frame(original_code, modified_snippet)
                if success:
                    print(f"   ✅ 第{slide_num}页修改成功")
                else:
                    print(f"   ❌ 第{slide_num}页修改失败")
            else:
                print(f"   ✗ 第{slide_num}页修改被取消")

    def _execute_insert(self, locate_results, base_instruction):
        """
        执行插入操作
        
        Args:
            locate_results: 定位结果（用作插入参考点）
            base_instruction: 插入指令描述
        """
        snippets = locate_results["snippets"]
        analysis = locate_results.get("analysis", "")
        
        print(f"   将在 {len(snippets)} 个定位片段后进行插入")
        if analysis:
            print(f"   分析结果: {analysis}")
        
        # 通常只使用第一个片段作为插入参考点
        if not snippets:
            print("   ❌ 没有找到插入参考点")
            return
            
        reference_snippet = snippets[0]  # 使用第一个片段作为参考
        slide_num = reference_snippet.get("slide_number", "未知")
        reference_code = reference_snippet.get("code", "")
        
        print(f"\n   在第{slide_num}页后插入新内容")
        
        # 生成要插入的内容
        insert_prompt = f"""
作为LaTeX演示文稿专家，请根据用户要求生成新的幻灯片内容。

用户插入要求：{base_instruction}
插入位置分析：{analysis}
参考片段（第{slide_num}页）：{reference_code}

请生成要插入的LaTeX代码。代码应该：
1. 包含完整的\\begin{{frame}} ... \\end{{frame}}结构
2. 如果需要多页，每页都要有完整的frame结构
3. 保持与现有文档的样式一致
4. 可以参考原始PDF数据生成相关内容

**重要规则**：
- **优先保证文本内容的可读性**。如果用户要求详细讲解，请确保文本内容充分且格式良好。
- **谨慎添加图片**。只有在图片对于解释概念至关重要，并且你有信心幻灯片有足够空间容纳图片时，才添加图片。否则，**请不要添加图片**，以避免页面内容溢出。

输出格式为JSON，包含`insert_content`字段。`insert_content`的值必须是一个字符串。
"""
        
        if self.source_content:
            insert_prompt += f"\n\n原始PDF内容（用于参考）:\n```json\n{json.dumps(self.source_content, ensure_ascii=False, indent=2)}\n```"
        
        response = self._call_llm([{"role": "user", "content": insert_prompt}], 
                                 "你是一个专业的LaTeX编辑专家，能够生成高质量的演示幻灯片代码。", 
                                 json_mode=True)
        
        if not response or not response.get("insert_content"):
            print("   ❌ 无法生成插入内容")
            return
            
        insert_content = response["insert_content"]
        
        # 增加健壮性：处理LLM可能返回的嵌套JSON字符串
        try:
            # 尝试将内容解析为JSON
            nested_data = json.loads(insert_content)
            # 如果成功，并且它是一个包含相同键的字典，则提取内部内容
            if isinstance(nested_data, dict) and "insert_content" in nested_data:
                print("   ⚠️ 检测到嵌套的JSON响应，正在提取内部内容...")
                insert_content = nested_data["insert_content"]
        except (json.JSONDecodeError, TypeError):
            # 如果它不是一个有效的JSON字符串，或者根本不是字符串，则正常继续
            pass
        
        # 显示要插入的内容预览
        print(f"\n--- 要插入的内容预览 ---")
        preview = insert_content[:300] + "..." if len(insert_content) > 300 else insert_content
        print(preview)
        print("--- 预览结束 ---")
        
        # 请求用户确认
        confirm = input("\n您确认要插入这些内容吗？(y/n) [y]: ").strip().lower()
        if confirm not in ['', 'y', 'yes']:
            print("   ✗ 插入操作被取消")
            return
        
        # 执行插入：在参考代码片段之后插入新内容
        insert_position = self.document_content.find(reference_code)
        if insert_position != -1:
            # 找到参考片段的结束位置
            end_position = insert_position + len(reference_code)
            
            # 插入新内容（在参考片段后添加换行符和新内容）
            new_content = (
                self.document_content[:end_position] + 
                "\n\n" + insert_content + 
                self.document_content[end_position:]
            )
            
            old_length = len(self.document_content)
            self.document_content = new_content
            new_length = len(self.document_content)
            
            print(f"   ✅ 插入成功！文档长度变化: {old_length} -> {new_length} (+{new_length - old_length})")
            
            # 重新生成文档地图
            print("   🔄 重新生成文档地图...")
            self._build_document_map()
        else:
            print("   ❌ 无法在文档中找到插入参考点")

    def _execute_delete(self, locate_results, base_instruction):
        """
        执行删除操作
        
        Args:
            locate_results: 定位结果（要删除的内容）
            base_instruction: 删除指令描述
        """
        snippets = locate_results["snippets"]
        analysis = locate_results.get("analysis", "")
        
        print(f"   将删除 {len(snippets)} 个定位片段")
        if analysis:
            print(f"   分析结果: {analysis}")
        
        if not snippets:
            print("   ❌ 没有找到要删除的内容")
            return
        
        # 显示要删除的内容
        print(f"\n--- 要删除的内容 ---")
        for i, snippet in enumerate(snippets, 1):
            slide_num = snippet.get("slide_number", "未知")
            code = snippet.get("code", "")
            desc = snippet.get("description", "")
            preview = code[:200] + "..." if len(code) > 200 else code
            print(f"{i}. 第{slide_num}页: {desc}")
            print(f"   代码预览: {preview}")
            print()
        print("--- 预览结束 ---")
        
        # 请求用户确认
        confirm = input(f"\n您确认要删除这{len(snippets)}个片段吗？(y/n) [y]: ").strip().lower()
        if confirm not in ['', 'y', 'yes']:
            print("   ✗ 删除操作被取消")
            return
        
        # 执行删除：逐个删除片段（从后往前删除，避免位置变化问题）
        deleted_count = 0
        snippets_sorted = sorted(snippets, key=lambda x: self.document_content.find(x.get("code", "")), reverse=True)
        
        for snippet in snippets_sorted:
            code = snippet.get("code", "")
            slide_num = snippet.get("slide_number", "未知")
            
            if code in self.document_content:
                old_length = len(self.document_content)
                self.document_content = self.document_content.replace(code, "", 1)  # 只删除第一个匹配
                new_length = len(self.document_content)
                
                if new_length < old_length:
                    deleted_count += 1
                    print(f"   ✅ 已删除第{slide_num}页 (减少{old_length - new_length}字符)")
                else:
                    print(f"   ⚠️ 第{slide_num}页未发生变化")
            else:
                print(f"   ❌ 无法找到第{slide_num}页的代码进行删除")
        
        if deleted_count > 0:
            print(f"   ✅ 删除完成！成功删除{deleted_count}/{len(snippets)}个片段")
            
            # 重新生成文档地图
            print("   🔄 重新生成文档地图...")
            self._build_document_map()
        else:
            print("   ❌ 没有任何内容被删除")

    def _save_document_if_requested(self):
        """
        询问用户是否保存文档
        """
        save_confirm = input("\n所有步骤已执行完毕。是否要将修改保存到文件？(y/n) [y]: ").strip().lower()
        if save_confirm == '' or save_confirm == 'y':
            # 生成新的文件名，避免覆盖原文件
            base_dir = os.path.dirname(self.tex_file_path)
            base_name = os.path.splitext(os.path.basename(self.tex_file_path))[0]
            revised_path = os.path.join(base_dir, f"{base_name}_revised.tex")
            
            try:
                with open(revised_path, 'w', encoding='utf-8') as f:
                    f.write(self.document_content)
                print(f"✓ 文件已保存: {revised_path}")
                
                # 更新当前路径为新文件路径，便于后续PDF编译
                self.tex_file_path = revised_path
                
                pdf_path = self._compile_to_pdf()
                if pdf_path:
                    open_pdf = input("是否自动打开PDF文件查看？(y/n) [y]: ").strip().lower()
                    if open_pdf in ['y', '']:
                        try:
                            webbrowser.open(f'file://{os.path.abspath(pdf_path)}')
                        except Exception as e:
                            print(f"无法自动打开PDF，请手动打开: {pdf_path}")
            except Exception as e:
                print(f"❌ 保存文件时出错: {str(e)}")
                print("尝试保存到原文件位置...")
                try:
                    with open(self.tex_file_path, 'w', encoding='utf-8') as f:
                        f.write(self.document_content)
                    print(f"✓ 文件已保存: {self.tex_file_path}")
                except Exception as e2:
                    print(f"❌ 仍然无法保存: {str(e2)}")
        else:
            print("✗ 文件未保存。")
    
    def modify_content(self, description):
        """
        修改内容的简化版本 - 适用于直接调用
        
        Args:
            description: 修改描述
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            print(f"\n🔄 开始修改内容: {description}")
            
            # 步骤1: 智能定位需要修改的位置
            location_result = self.locate_code_snippet(description)
            if not location_result or not location_result.get('snippets'):
                print("   ❌ 未能定位到需要修改的内容")
                return False, f"无法定位要修改的内容: {description}"
            
            snippets = location_result['snippets']
            analysis = location_result.get('analysis', '')
            
            print(f"   ✓ 定位到 {len(snippets)} 个需要修改的位置")
            if analysis:
                print(f"   📋 分析: {analysis}")
            
            # 步骤2: 为每个片段生成修改方案并应用
            success_count = 0
            failed_modifications = []
            
            for i, snippet in enumerate(snippets, 1):
                print(f"\n   处理片段 {i}/{len(snippets)}: {snippet.get('description', 'N/A')}")
                
                # 生成修改后的代码
                modified_code = self.generate_modified_code(
                    snippet['code'], 
                    description, 
                    self.document_content
                )
                
                if not modified_code:
                    failed_modifications.append(f"片段{i}: 无法生成修改方案")
                    continue
                
                # 应用修改
                if snippet['code'] in self.document_content:
                    # 替换原始代码
                    self.document_content = self.document_content.replace(
                        snippet['code'], 
                        modified_code, 
                        1  # 只替换第一个匹配项
                    )
                    success_count += 1
                    print(f"   ✅ 片段{i}修改成功")
                else:
                    failed_modifications.append(f"片段{i}: 在文档中未找到原始代码")
                    print(f"   ❌ 片段{i}: 在文档中未找到原始代码")
            
            # 步骤3: 处理结果
            if success_count > 0:
                # 重新生成文档地图以反映更改
                print("\n   🔄 重新生成文档地图...")
                self._build_document_map()
                
                result_msg = f"成功修改了 {success_count}/{len(snippets)} 个位置"
                if failed_modifications:
                    result_msg += f"，失败: {'; '.join(failed_modifications)}"
                
                print(f"\n✅ {result_msg}")
                return True, result_msg
            else:
                error_msg = f"所有修改都失败了: {'; '.join(failed_modifications)}"
                print(f"\n❌ {error_msg}")
                return False, error_msg
            
        except Exception as e:
            error_msg = f"修改内容时出错: {e}"
            print(f"\n❌ {error_msg}")
            return False, error_msg
    
    def interactive_session(self):
        """
        启动交互式编辑会话 - 简化版本
        """
        print(f"\n🎯 启动交互式LaTeX编辑器")
        print(f"📄 当前文档: {os.path.basename(self.tex_file_path)}")
        print(f"📊 文档状态: {self.document_map['total_slides']}页幻灯片" if self.document_map else "文档地图不可用")
        print("\n💡 使用说明:")
        print("  - 输入修改需求，如：'修改第3页的标题'、'调整图片大小'")
        print("  - 输入 'quit' 或 'exit' 退出")
        print("  - 输入 'save' 保存当前修改")
        print("  - 输入 'status' 查看文档状态")
        print("\n" + "="*60)
        
        while True:
            try:
                user_input = input("\n🔧 请输入修改需求 > ").strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 退出编辑器")
                    self._save_document_if_requested()
                    break
                
                elif user_input.lower() == 'save':
                    self._save_document_if_requested()
                    continue
                
                elif user_input.lower() == 'status':
                    self._show_document_status()
                    continue
                
                # 执行修改
                success, message = self.modify_content(user_input)
                
                if success:
                    print(f"✅ {message}")
                else:
                    print(f"❌ {message}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户中断，退出编辑器")
                self._save_document_if_requested()
                break
            except Exception as e:
                print(f"❌ 处理输入时出错: {e}")
                continue
    
    def _show_document_status(self):
        """显示文档状态信息"""
        print("\n📊 文档状态:")
        print(f"   文件: {self.tex_file_path}")
        print(f"   大小: {len(self.document_content)} 字符")
        
        if self.document_map:
            print(f"   幻灯片数量: {self.document_map['total_slides']} 页")
            
            # 统计特殊内容
            images_count = sum(1 for slide in self.document_map['slides'] if slide.get('has_image'))
            tables_count = sum(1 for slide in self.document_map['slides'] if slide.get('has_table'))
            
            if images_count > 0:
                print(f"   含图片页面: {images_count} 页")
            if tables_count > 0:
                print(f"   含表格页面: {tables_count} 页")
                
            # 显示章节信息
            sections = set()
            for slide in self.document_map['slides']:
                if slide.get('section'):
                    sections.add(slide['section'])
            
            if sections:
                print(f"   章节: {', '.join(sorted(sections))}")
        else:
            print("   ⚠️ 文档地图不可用")
