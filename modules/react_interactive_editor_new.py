#!/usr/bin/env python3
"""
React Interactive Editor - Rewritten Version
Based on intelligent semantic positioning, not dependent on page numbering system
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

# Import prompts
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from prompts.react_editor_prompts import (
    DOCUMENT_STRUCTURE_ANALYSIS_PROMPT,
    CODE_LOCATION_PROMPT,
    CODE_MODIFICATION_PROMPT,
    REACT_DECISION_PROMPT,
    create_content_insertion_prompt,
    LATEX_EXPERT_SYSTEM_PROMPT,
    USER_CONFIRMATION_PROMPTS,
    REFERENCE_SEARCH_ENHANCEMENT
)

class ReactInteractiveEditor:
    """
    Intelligent LaTeX editor using ReAct mode for interactive modifications
    Based on document semantic understanding rather than page numbering for positioning
    """
    
    def __init__(self, tex_file_path, source_content=None, workflow_state=None, model_name="gpt-4o"):
        """
        Initialize editor
        
        Args:
            tex_file_path: LaTeX file path
            source_content: Original PDF parsing content (optional, for content expansion)
            workflow_state: Workflow state manager, for accessing intermediate products
            model_name: Language model name to use (default: "gpt-4o")
        """
        self.tex_file_path = tex_file_path
        self.source_content = source_content
        self.workflow_state = workflow_state
        self.model_name = model_name
        self.conversation_history = []
        
        # Initialize reference retrieval agent (if workflow state is available)
        self.reference_agent = None
        if workflow_state and workflow_state.is_ready_for_reference_search():
            try:
                # Fix import path - use modules.reference_agent path
                from modules.reference_agent.reference_agent import ReferenceAgent
                self.reference_agent = ReferenceAgent()
                print("   ✅ Reference search agent initialized")
            except ImportError as e:
                try:
                    # Backup import path
                    import sys
                    import os
                    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
                    from modules.reference_agent.reference_agent import ReferenceAgent
                    self.reference_agent = ReferenceAgent()
                    print("   ✅ Reference search agent initialized (backup path)")
                except Exception as e2:
                    print(f"   ⚠️ Reference search agent initialization failed: {e2}")
                    self.reference_agent = None
            except Exception as e:
                print(f"   ⚠️ Reference search agent initialization failed: {e}")
                self.reference_agent = None
        
        # Read document content
        with open(tex_file_path, 'r', encoding='utf-8') as f:
            self.document_content = f.read()
        
        # Generate document structure map
        print("   Generating document structure map...")
        self.document_map = self._build_document_map()
        
        print(f"✓ Document loaded and preprocessed: {self.tex_file_path}")
        print(f"  Document size: {len(self.document_content)} characters")
        if source_content:
            print(f"  Original PDF content provided, content expansion feature enabled")
        print()
    
    def _build_document_map(self):
        """
        Build structured map of document to help LLM understand document structure
        
        Returns:
            dict: Document map containing slides list, or None if generation fails
        """
        try:
            system_prompt = DOCUMENT_STRUCTURE_ANALYSIS_PROMPT
            
            prompt = f"Please analyze the following LaTeX document and generate a structured map:\n```latex\n{self.document_content}\n```"
            
            result_json = self._call_llm([{"role": "user", "content": prompt}], system_prompt, json_mode=True)
            
            if result_json and "slides" in result_json:
                print(f"   ✓ Document map generated: {result_json['total_slides']} slides")
                return result_json
            else:
                print("   ⚠️ Document map generation failed, will use backup positioning method")
                return None
                
        except Exception as e:
            print(f"   ❌ Document map generation error: {e}")
            return None
    
    def _call_llm(self, messages, system_prompt, temperature=0.1, json_mode=False):
        """
        General LLM calling function
        
        Args:
            messages: Message list
            system_prompt: System prompt
            temperature: Temperature parameter
            json_mode: Whether to use JSON mode
            
        Returns:
            dict|str: LLM response result
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
            print(f"❌ LLM call failed: {e}")
            return None
    
    def locate_code_snippet(self, description):
        """
        Intelligently locate code snippets, supports multi-target positioning
        
        Args:
            description: User description
            
        Returns:
            dict: {
                "snippets": [{"slide_number": int, "code": str, "description": str}],
                "analysis": "Analysis result"
            }
        """
        print(f"ReAct Agent [Locating]... {description}")
        
        system_prompt = CODE_LOCATION_PROMPT
        
        # Build complete context including document map
        context_parts = []
        
        if self.document_map:
            map_summary = f"Document Map ({self.document_map['total_slides']} slides total):\n"
            for slide in self.document_map['slides']:
                map_summary += f"Page {slide['slide_number']}: {slide['type']} - {slide.get('title', 'N/A')}"
                if slide.get('section'):
                    map_summary += f" (Section: {slide['section']})"
                if slide.get('has_image'):
                    map_summary += f" [Images: {', '.join(slide.get('image_files', []))}]"
                if slide.get('has_table'):
                    map_summary += " [Contains Table]"
                map_summary += f"\n  Summary: {slide.get('content_summary', 'None')}\n"
            context_parts.append(map_summary)
        else:
            context_parts.append("⚠️ Document map unavailable, will analyze based on source code directly")
        
        context_parts.append(f"LaTeX Source Code:\n```latex\n{self.document_content}\n```")
        full_context = "\n\n".join(context_parts)
        
        prompt = f"{full_context}\n\nUser Request: {description}"
        
        result_json = self._call_llm([{"role": "user", "content": prompt}], system_prompt, json_mode=True)
        
        if result_json and result_json.get("snippets"):
            snippets = result_json.get("snippets", [])
            analysis = result_json.get("analysis", "")
            
            print(f"   ✓ Found {len(snippets)} code snippets")
            if analysis:
                print(f"   📋 Analysis: {analysis}")
            
            for i, snippet_info in enumerate(snippets, 1):
                slide_num = snippet_info.get("slide_number", "Unknown")
                desc = snippet_info.get("description", "")
                code = snippet_info.get("code", "")
                print(f"   {i}. Page {slide_num}: {desc} ({len(code)} characters)")
            
            return result_json
        else:
            print("   ❌ Failed to locate relevant code")
            return {"snippets": [], "analysis": "No matching code snippets found"}
    
    def generate_modified_code(self, original_snippet, instruction, full_document_context):
        """
        Generate modified code according to instructions
        
        Args:
            original_snippet: Original code snippet
            instruction: Modification instruction
            full_document_context: Complete document context
            
        Returns:
            str: Modified code, or None if failed
        """
        print(f"ReAct Agent [Modifying]... {instruction}")
        
        system_prompt = CODE_MODIFICATION_PROMPT
        
        # Build complete context including original PDF content
        context_parts = [f"Complete LaTeX document content:\n```latex\n{full_document_context}\n```"]
        
        if self.source_content:
            context_parts.append(f"Original PDF parsing content (for enhancement features):\n```json\n{json.dumps(self.source_content, ensure_ascii=False, indent=2)}\n```")
        
        full_context = "\n\n".join(context_parts)
        
        prompt = f"{full_context}\n\nCode snippet to modify:\n```latex\n{original_snippet}\n```\n\nPlease modify it according to the following instruction:\n{instruction}"
        
        result_json = self._call_llm([{"role": "user", "content": prompt}], system_prompt, json_mode=True)
        
        if not result_json:
            print("❌ LLM failed to generate valid response")
            return None
            
        modified_code = result_json.get("modified_code")
        
        # Ensure return type is string
        if isinstance(modified_code, list):
            print("⚠️ Detected LLM returned list, attempting to convert to string")
            modified_code = '\n'.join(str(item) for item in modified_code)
        elif not isinstance(modified_code, str):
            print(f"❌ LLM returned invalid type: {type(modified_code)}")
            return None
            
        # Add safety check: prevent LLM from returning entire document
        original_length = len(original_snippet)
        modified_length = len(modified_code)
        
        # If modified code length exceeds 3x original code, may be abnormal
        if modified_length > original_length * 3:
            print(f"⚠️ Warning: Modified code length abnormal ({modified_length} vs {original_length})")
            print("This may indicate LLM returned excessive code.")
            
            # Check if contains document header identifiers
            if "\\documentclass" in modified_code and "\\begin{document}" in modified_code:
                print("❌ Detected LLM incorrectly returned complete document, rejecting this modification")
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
        
        system_prompt = REACT_DECISION_PROMPT
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
        print("=== Interactive LaTeX Editor (ReAct Mode) ===")
        print("Describe your modifications in natural language. You can:")
        print("• Modify existing slide content")
        if self.source_content:
            print("• Add new slides or expand content based on the original paper")
        print("• Type 'save' to save changes and exit")
        print("• Type 'quit' to exit without saving")
        print("🔄 After each modification, PDF will be automatically compiled for preview")
        print()
        
        while True:
            try:
                user_input = input("🔧 Enter your request > ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    print("Goodbye!")
                    break
                elif user_input.lower() in ['save', '保存', 's']:
                    print("🔄 Saving changes...")
                    self._save_document_if_requested()
                    break
                elif not user_input: 
                    continue

                self.conversation_history.append({"role": "user", "content": user_input})
                
                decision = self.decide_next_action()
                
                if not decision or "action" not in decision:
                    print("❌ Cannot understand your request, please try a different way.")
                    self.conversation_history.append({"role": "assistant", "content": "Sorry, I cannot understand your request."})
                    continue

                if decision["action"] == "clarify":
                    question = decision.get("question", "Please provide more details.")
                    print(f"Agent: {question}")
                    self.conversation_history.append({"role": "assistant", "content": question})
                    continue
                
                if decision["action"] == "plan":
                    plan = decision.get("plan")
                    if not plan:
                        print("❌ Plan generation failed.")
                        continue
                    
                    print("\n✓ Execution plan generated:")
                    for step in plan:
                        print(f"  - Step {step['step']} ({step['action']}): {step['description']}")
                    print()

                    # 执行计划
                    print("🔄 Executing plan...")
                    self._execute_plan(plan)
                    print("✅ Plan execution completed")
                    
                    # 自动编译PDF让用户看到效果
                    print("🔄 Compiling PDF to show changes...")
                    pdf_path = self._compile_to_pdf()
                    if pdf_path:
                        print(f"✅ PDF updated: {pdf_path}")
                        print("📄 You can now review the changes in the PDF")
                    else:
                        print("⚠️ PDF compilation failed, but changes are saved in memory")
                    
                    # 询问用户是否继续修改
                    print("\n" + "="*60)
                    print("🎯 Changes applied! You can:")
                    print("   • Enter new modification requests")
                    print("   • Type 'save' to save changes and exit")
                    print("   • Type 'quit' to exit without saving")
                    print("="*60)
                    
                    # 重置对话历史，开始新的任务
                    self.conversation_history = []

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"❌ Critical error occurred: {e}")
                import traceback
                traceback.print_exc()
                print("🔧 Please check the error details above and try again.")

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
                    
            elif step['action'] == 'reference_search':
                # 执行引用检索操作
                search_result = self._execute_reference_search(step['description'])
                if search_result:
                    # 将检索结果存储，供后续步骤使用
                    if not hasattr(self, 'reference_search_results'):
                        self.reference_search_results = {}
                    # 提取概念名称作为键
                    concept = self._extract_concept_from_description(step['description'])
                    self.reference_search_results[concept] = search_result
                    print(f"✓ 引用检索完成，概念'{concept}'的扩展内容已准备就绪")
                else:
                    print("❌ 引用检索失败")
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
        
        # 准备插入内容的生成提示词
        insert_prompt = create_content_insertion_prompt(
            base_instruction, analysis, slide_num, reference_code
        )
        
        # 检查是否有引用检索结果可用
        reference_content = None
        if hasattr(self, 'reference_search_results') and self.reference_search_results:
            # 尝试匹配相关的概念
            for concept, result in self.reference_search_results.items():
                if concept.lower() in base_instruction.lower() or any(kw in base_instruction.lower() for kw in concept.lower().split()):
                    reference_content = result
                    break
        
        if reference_content:
            print(f"   ✨ 将使用引用检索的扩展内容: '{reference_content['concept']}'")
            insert_prompt += f"""

🎯 引用检索扩展内容（来自专业文献）:
概念: {reference_content['concept']}
质量评分: {reference_content['quality_score']:.2f}

扩展内容:
{reference_content['enhanced_content']}

关键要点:
{chr(10).join(f"- {point}" for point in reference_content.get('key_points', [])[:5])}

来源文献: {len(reference_content.get('source_papers', []))} 篇专业文献

请优先使用以上扩展内容来生成专业、准确的幻灯片。
"""
        
        if self.source_content:
            insert_prompt += f"\n\n原始PDF内容（用于参考）:\n```json\n{json.dumps(self.source_content, ensure_ascii=False, indent=2)}\n```"
        
        response = self._call_llm([{"role": "user", "content": insert_prompt}], 
                                 LATEX_EXPERT_SYSTEM_PROMPT, 
                                 json_mode=True)
        
        if not response or not response.get("insert_content"):
            print("   ❌ 无法生成插入内容")
            return
            
        insert_content = response["insert_content"]
        
        # 显示要插入的内容预览
        print(f"\n--- 要插入的内容预览 ---")
        preview = insert_content[:300] + "..." if len(insert_content) > 300 else insert_content
        print(preview)
        print("--- 预览结束 ---")
        
        # 请求用户确认
        confirm = input(f"\n{USER_CONFIRMATION_PROMPTS['insert_confirmation']}").strip().lower()
        if confirm not in ['', 'y', 'yes']:
            print("   ✗ Insert operation cancelled")
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
        Ask user whether to save document
        """
        print("\n" + "="*60)
        print("🎉 All modifications completed successfully!")
        print("📄 Ready to save changes to file...")
        save_confirm = input("\nSave changes to file? (y/n) [y]: ").strip().lower()
        if save_confirm == '' or save_confirm == 'y':
            # 生成新的文件名，避免覆盖原文件
            base_dir = os.path.dirname(self.tex_file_path)
            base_name = os.path.splitext(os.path.basename(self.tex_file_path))[0]
            revised_path = os.path.join(base_dir, f"{base_name}_revised.tex")
            
            try:
                with open(revised_path, 'w', encoding='utf-8') as f:
                    f.write(self.document_content)
                print(f"✓ File saved: {revised_path}")
                
                # 更新当前路径为新文件路径，便于后续PDF编译
                self.tex_file_path = revised_path
                
                pdf_path = self._compile_to_pdf()
                if pdf_path:
                    open_pdf = input("Open PDF automatically? (y/n) [y]: ").strip().lower()
                    if open_pdf in ['y', '']:
                        try:
                            webbrowser.open(f'file://{os.path.abspath(pdf_path)}')
                        except Exception as e:
                            print(f"Cannot auto-open PDF, please open manually: {pdf_path}")
            except Exception as e:
                print(f"❌ Error saving file: {str(e)}")
                print("Trying to save to original location...")
                try:
                    with open(self.tex_file_path, 'w', encoding='utf-8') as f:
                        f.write(self.document_content)
                    print(f"✓ File saved: {self.tex_file_path}")
                except Exception as e2:
                    print(f"❌ Still cannot save: {str(e2)}")
        else:
            print("✗ File not saved.")
    
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
        
        if hasattr(self, 'source_content') and self.source_content:
            print(f"   原始PDF内容: 可用")
        else:
            print(f"   原始PDF内容: 不可用")
        
        if hasattr(self, 'reference_agent') and self.reference_agent:
            print(f"   引用检索Agent: 可用")
        else:
            print(f"   引用检索Agent: 不可用")

    def _execute_reference_search(self, description: str) -> dict:
        """
        执行引用检索操作
        
        Args:
            description: 检索描述，包含目标概念
            
        Returns:
            dict: 检索结果，包含扩展内容
        """
        if not self.reference_agent:
            print("❌ 引用检索Agent未初始化，将使用基础内容扩展")
            return self._fallback_content_expansion(description)
        
        if not self.workflow_state:
            print("❌ 工作流状态不可用，无法进行引用检索")
            return self._fallback_content_expansion(description)
        
        # 从描述中提取概念名称
        concept = self._extract_concept_from_description(description)
        
        print(f"🔍 正在检索概念: '{concept}'")
        print("   - 分析原论文引用...")
        
        try:
            # 准备引用检索上下文
            search_context = self.workflow_state.get_reference_search_context(concept)
            
            # 添加当前对话上下文
            conversation_context = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in self.conversation_history[-3:]  # 最近3轮对话
            ])
            
            # 执行引用检索
            result = self.reference_agent.enhance_content_with_references(
                original_paper_path=search_context["original_paper_path"],
                target_concept=concept,
                context=conversation_context,
                max_references=2,  # 限制引用数量以提高效率
                output_dir=search_context["output_dir"]
            )
            
            if result['success']:
                print(f"✅ 检索成功! 质量评分: {result['content_quality_score']:.2f}")
                print(f"   找到 {len(result.get('source_papers', []))} 篇相关文献")
                
                # 简化返回结果
                return {
                    'concept': concept,
                    'enhanced_content': result['enhanced_content'],
                    'key_points': result.get('key_points', []),
                    'source_papers': result.get('source_papers', []),
                    'quality_score': result['content_quality_score']
                }
            else:
                print(f"❌ 检索失败: {result.get('error', '未知错误')}")
                print("⚠️ 将使用基础内容扩展作为备选方案")
                return self._fallback_content_expansion(description)
                
        except Exception as e:
            print(f"❌ 引用检索过程中出错: {e}")
            print("⚠️ 将使用基础内容扩展作为备选方案")
            return self._fallback_content_expansion(description)
    
    def _extract_concept_from_description(self, description: str) -> str:
        """
        从描述中提取概念名称
        
        Args:
            description: 描述文本
            
        Returns:
            str: 提取的概念名称
        """
        import re
        
        # 尝试从引号中提取
        quote_match = re.search(r"['\"](.*?)['\"]", description)
        if quote_match:
            return quote_match.group(1).strip()
        
        # 尝试从"关于X"模式中提取
        about_match = re.search(r"关于['\"]?(.*?)['\"]?的", description)
        if about_match:
            return about_match.group(1).strip()
        
        # 尝试从常见技术词汇中匹配
        tech_terms = ['attention', 'transformer', 'neural', 'learning', 'model', 'network', 'algorithm']
        for term in tech_terms:
            if term in description.lower():
                # 提取包含该词汇的短语
                words = description.split()
                for i, word in enumerate(words):
                    if term in word.lower():
                        # 取前后各一个词作为概念
                        start = max(0, i-1)
                        end = min(len(words), i+2)
                        return ' '.join(words[start:end]).strip()
        
        # 如果都没找到，返回描述的关键词
        words = description.split()
        # 过滤掉常见的动词和介词
        stop_words = ['获取', '检索', '通过', '关于', '的', '进行', '使用', '实现']
        key_words = [w for w in words if w not in stop_words and len(w) > 1]
        
        if key_words:
            return ' '.join(key_words[:2])  # 取前两个关键词
        
        return "unknown_concept"
    
    def _fallback_content_expansion(self, description: str) -> dict:
        """
        基础内容扩展方案（当引用检索失败时使用）
        
        Args:
            description: 扩展描述
            
        Returns:
            dict: 基础扩展内容
        """
        concept = self._extract_concept_from_description(description)
        print(f"🔄 使用基础内容扩展生成'{concept}'的解释")
        
        try:
            # 如果有原始PDF内容，从中提取相关信息
            if hasattr(self, 'source_content') and self.source_content:
                relevant_content = self._extract_relevant_content_from_source(concept, self.source_content)
            else:
                relevant_content = ""
            
            # 生成基础扩展内容
            expanded_content = self._generate_basic_explanation(concept, relevant_content)
            
            return {
                'concept': concept,
                'enhanced_content': expanded_content,
                'key_points': self._extract_basic_key_points(expanded_content),
                'source_papers': [{'title': 'Original Paper', 'authors': ['Original Authors']}],
                'quality_score': 0.6,  # 基础扩展质量分
                'method': 'fallback_expansion'
            }
            
        except Exception as e:
            print(f"⚠️ 基础内容扩展也失败了: {e}")
            return {
                'concept': concept,
                'enhanced_content': f"{concept}是一个重要的技术概念，在本研究中起到关键作用。",
                'key_points': [f"{concept}的重要性", "在研究中的应用"],
                'source_papers': [],
                'quality_score': 0.3,
                'method': 'minimal_fallback'
            }
    
    def _extract_relevant_content_from_source(self, concept: str, source_content: str) -> str:
        """从原始内容中提取相关段落"""
        if not source_content or not concept:
            return ""
        
        # 将concept转换为搜索关键词
        search_terms = [concept.lower()]
        if ' ' in concept:
            search_terms.extend(concept.lower().split())
        
        # 分段搜索
        paragraphs = source_content.split('\n\n')
        relevant_paragraphs = []
        
        for para in paragraphs:
            para_lower = para.lower()
            if any(term in para_lower for term in search_terms) and len(para.strip()) > 50:
                relevant_paragraphs.append(para.strip())
        
        return '\n\n'.join(relevant_paragraphs[:3])  # 最多3个相关段落
    
    def _generate_basic_explanation(self, concept: str, relevant_content: str) -> str:
        """生成基础技术解释"""
        if relevant_content:
            return f"""## {concept.title()}

**技术概述:**
{concept}是本研究中采用的重要技术方法。

**在本研究中的应用:**
{relevant_content[:500]}...

**技术特点:**
• 在相关领域具有重要意义
• 能够有效解决特定问题
• 具有良好的性能表现

**相关背景:**
该技术在当前研究领域得到广泛应用，为问题解决提供了有效途径。
"""
        else:
            return f"""## {concept.title()}

**定义:**
{concept}是本研究中的关键技术概念。

**重要性:**
• 在研究方法中起到核心作用
• 为问题解决提供技术支撑
• 具有理论和实践意义

**应用特点:**
该技术方法在相关研究中展现出良好的性能，为研究目标的实现提供了重要保障。
"""
    
    def _extract_basic_key_points(self, content: str) -> list:
        """从基础内容中提取关键点"""
        key_points = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('• ') or line.startswith('- '):
                key_points.append(line[2:])
            elif line.startswith('**') and line.endswith(':**'):
                key_points.append(line.strip('*:'))
        
        return key_points[:5]  # 最多5个关键点
