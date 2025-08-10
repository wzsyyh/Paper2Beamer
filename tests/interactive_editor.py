#!/usr/bin/env python3
"""
交互式 LaTeX 编辑器 - 基于 ReAct 模式和 LLM 驱动的文档编辑
"""

import sys
import os
import re
import subprocess
import webbrowser
from dotenv import load_dotenv
import openai
import json
from difflib import unified_diff

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)

class InteractiveEditor:
    """交互式LaTeX编辑器 - ReAct模式"""
    
    def __init__(self, tex_file_path):
        self.tex_file_path = tex_file_path
        self.conversation_history = []
        
        # 读取原始文档内容
        with open(tex_file_path, 'r', encoding='utf-8') as f:
            self.original_document_content = f.read()
        
        # 在内存中为文档内容添加页码标记，用于精确定位
        self.document_content = self._add_page_markers(self.original_document_content)
        
        print(f"✓ 已加载并预处理文档: {self.tex_file_path}")
        print(f"  文档大小: {len(self.original_document_content)} 字符")
        print()

    def _add_page_markers(self, content):
        """在每个frame前添加唯一的页码标记，用于LLM精确定位。"""
        lines = content.splitlines()
        processed_lines = []
        page_counter = 1
        for line in lines:
            if line.strip().startswith(r'\frame{') or line.strip().startswith(r'\begin{frame}'):
                processed_lines.append(f"%% FRAME_PAGE_{page_counter} %%")
                page_counter += 1
            processed_lines.append(line)
        return "\n".join(processed_lines)

    def _remove_page_markers(self, content):
        """从内容中移除页码标记"""
        return re.sub(r'%% FRAME_PAGE_\d+ %%\n?', '', content)

    def _call_llm(self, messages, system_prompt, temperature=0.1, json_mode=False):
        """通用LLM调用函数"""
        try:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            response_format = {"type": "json_object"} if json_mode else {"type": "text"}
            
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
                messages=full_messages,
                temperature=temperature,
                response_format=response_format
            )
            content = response.choices[0].message.content
            return json.loads(content) if json_mode else content
        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            return None

    def decide_next_action(self):
        """第一步：基于对话历史，决定是提问澄清还是制定计划"""
        print("ReAct Agent [思考中]... 正在分析您的需求。")
        
        system_prompt = """
你是一个顶级的LaTeX编辑助手。你的任务是分析与用户的对话历史，并决定下一步行动。
1.  **分析历史**: 查看完整的对话历史，理解用户的最终意图。
2.  **判断清晰度**:
    -   如果用户的最新请求**足够清晰**，可以转化为具体操作，则制定一个执行计划。
    -   如果用户的请求**模糊不清**，则必须提出一个具体的问题来澄清用户的意图。
3.  **输出格式**: 必须以JSON格式输出。
    -   如果指令清晰，输出: `{"action": "plan", "plan": [...]}`.
        -   `plan` 是一个列表。
        -   每个步骤都是一个包含 `step`, `action`, 和 `description` 的对象。
        -   **`action` 字段必须是 "locate" 或 "modify"**。绝对不能使用其他词，如 "resize", "change" 等。
        -   示例: `{"action": "plan", "plan": [{"step": 1, "action": "locate", "description": "定位第4页的幻灯片。"}, {"step": 2, "action": "modify", "description": "缩小该页插图的尺寸。"}]}`
    -   如果指令模糊，输出: `{"action": "clarify", "question": "请问您具体想怎么修改呢？"}`
"""
        decision_json = self._call_llm(self.conversation_history, system_prompt, json_mode=True)
        return decision_json

    def locate_code_snippet(self, description):
        """第二步：根据描述定位相关的代码片段"""
        print(f"ReAct Agent [定位中]... {description}")
        
        system_prompt = """
你是一个LaTeX代码定位专家。你的任务是在给定的、带有页码标记 (`%% FRAME_PAGE_X %%`) 的LaTeX源码中，根据用户描述找到最相关的代码片段。
**你必须使用 `%% FRAME_PAGE_X %%` 标记来定位**。返回从该标记开始到`\end{frame}`的完整代码块。
输出格式为JSON，包含`code_snippet`字段。找不到则返回空。
"""
        match = re.search(r'\d+', description)
        if not match:
            print("❌ 定位描述中未找到数字页码。")
            return None
        page_number = match.group(0)
        
        prompt = f"这是带有页码标记的LaTeX完整源码:\n```latex\n{self.document_content}\n```\n\n请根据以下描述定位相关代码片段:\n定位第 {page_number} 页的幻灯片。"
        
        result_json = self._call_llm([{"role": "user", "content": prompt}], system_prompt, json_mode=True)
        return result_json.get("code_snippet") if result_json else None

    def generate_modified_code(self, original_snippet, instruction):
        """第三步：根据指令和原始代码，生成修改后的代码"""
        print(f"ReAct Agent [修改中]... {instruction}")
        
        system_prompt = """
你是一个顶级的LaTeX代码编辑专家。你会收到一段原始的LaTeX代码片段和一条修改指令。
你的任务是精确地修改代码，并保持其余部分（包括页码标记）不变。
输出格式为JSON，包含`modified_code`字段。
"""
        prompt = f"这是原始的LaTeX代码片段:\n```latex\n{original_snippet}\n```\n\n请根据以下指令修改它:\n{instruction}"
        
        result_json = self._call_llm([{"role": "user", "content": prompt}], system_prompt, json_mode=True)
        return result_json.get("modified_code") if result_json else None

    def show_diff_and_get_confirmation(self, original_snippet, modified_snippet):
        """显示diff并请求用户确认"""
        clean_original = self._remove_page_markers(original_snippet)
        clean_modified = self._remove_page_markers(modified_snippet)

        diff = unified_diff(
            clean_original.splitlines(keepends=True),
            clean_modified.splitlines(keepends=True),
            fromfile='original', tofile='modified',
        )
        
        print("\n--- 建议的修改 ---")
        diff_str = "".join(diff)
        if not diff_str.strip():
            print("🤔 未检测到代码变化。")
            return False

        for line in diff_str.splitlines(keepends=True):
            if line.startswith('+'): print(f"\033[92m{line}\033[0m", end="")
            elif line.startswith('-'): print(f"\033[91m{line}\033[0m", end="")
            elif line.startswith('^'): continue
            else: print(line, end="")
        print("--------------------")
        
        confirm = input("您接受这个修改吗？(y/n/c) [y]: ").strip().lower()
        return confirm == 'y' or confirm == ''

    def _compile_to_pdf(self):
        """编译tex文件两次以生成PDF"""
        tex_path = self.tex_file_path
        output_dir = os.path.dirname(tex_path)
        base_name = os.path.basename(tex_path)
        
        print("\n--- 正在编译PDF，请稍候 ---")
        for i in range(2):
            print(f"编译第 {i+1}/2 次...")
            try:
                process = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', f'-output-directory={output_dir}', base_name],
                    capture_output=True, text=True, check=True, timeout=60
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"❌ 编译失败！错误信息:")
                print(e.stdout)
                print(e.stderr)
                return None
        
        pdf_path = os.path.join(output_dir, os.path.splitext(base_name)[0] + '.pdf')
        if os.path.exists(pdf_path):
            print(f"✓ 编译成功！PDF已生成: {pdf_path}")
            return pdf_path
        else:
            print("❌ 编译完成但未找到PDF文件。")
            return None

    def run_interactive_session(self):
        """运行交互式编辑会话"""
        print("=== 交互式 LaTeX 编辑器 (ReAct 模式) ===")
        print("请用自然语言描述您想要的修改。输入 'quit' 退出。")
        print()
        
        while True:
            try:
                user_input = input("您: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    print("再见！")
                    break
                if not user_input: continue

                self.conversation_history.append({"role": "user", "content": user_input})
                
                decision = self.decide_next_action()
                
                if not decision or "action" not in decision:
                    print("❌ 无法理解您的指令，请换一种方式表述。")
                    self.conversation_history.append({"role": "assistant", "content": "抱歉，我无法理解您的指令。"})
                    continue

                if decision["action"] == "clarify":
                    question = decision["question"]
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
                    current_snippet = None
                    for step in plan:
                        print(f"--- 正在执行步骤 {step['step']}/{len(plan)} ---")
                        if step['action'] == 'locate':
                            current_snippet = self.locate_code_snippet(step['description'])
                            if not current_snippet:
                                print("❌ 定位失败，中止计划。")
                                break
                            print("✓ 定位成功！")
                        elif step['action'] == 'modify':
                            if not current_snippet:
                                print("❌ 修改失败，前一步定位未成功。")
                                break
                            modified_snippet = self.generate_modified_code(current_snippet, step['description'])
                            if not modified_snippet:
                                print("❌ LLM未能生成修改后的代码。")
                                break
                            if self.show_diff_and_get_confirmation(current_snippet, modified_snippet):
                                self.document_content = self.document_content.replace(current_snippet, modified_snippet)
                                current_snippet = modified_snippet 
                                print("✓ 修改已应用。")
                            else:
                                print("✗ 修改已取消。")
                    
                    # 询问是否保存
                    save_confirm = input("\n所有步骤已执行完毕。是否要将修改保存到文件？(y/n) [n]: ").strip().lower()
                    if save_confirm == 'y':
                        final_content = self._remove_page_markers(self.document_content)
                        with open(self.tex_file_path, 'w', encoding='utf-8') as f:
                            f.write(final_content)
                        print(f"✓ 文件已保存: {self.tex_file_path}")
                        
                        pdf_path = self._compile_to_pdf()
                        if pdf_path:
                            open_pdf = input("是否自动打开PDF文件查看？(y/n) [y]: ").strip().lower()
                            if open_pdf in ['y', '']:
                                webbrowser.open(f'file://{os.path.abspath(pdf_path)}')
                    else:
                        print("✗ 文件未保存。")
                    
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

def main():
    source_file = "/home/yuheng/Project/paper-to-beamer/output/tex/1754661367/output.tex"
    test_file = "/home/yuheng/Project/paper-to-beamer/output/tex/1754661367/output_interactive_test.tex"
    
    if not os.path.exists(source_file):
        print(f"源文件不存在: {source_file}")
        return
        
    import shutil
    shutil.copy(source_file, test_file)
    
    editor = InteractiveEditor(test_file)
    editor.run_interactive_session()

if __name__ == "__main__":
    main()
