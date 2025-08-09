# modules/interactive_reviser.py
import logging
import json
import os
import re
import subprocess
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
# Role
You are an expert LaTeX developer specializing in Beamer presentations. Your task is to function as a code modification assistant. You will receive a user's request to change something, the history of the conversation, and a relevant block of LaTeX code. Your only job is to provide the modified version of that code block.

# Conversation History
Here is the history of previous revisions in this session. Use it to understand context for follow-up requests (e.g., "the slide I just added").
---
{history}
---

# User's Request
The user wants to make the following change:
---
{user_feedback}
---

# Code to Modify
Here is the specific `frame` block you need to modify. Do not touch other parts of the presentation.
---
{code_snippet}
---

# Your Task
Generate a JSON object with a single key, "new_code".
- "new_code": This is the complete, modified version of the `frame` block provided above.

# Important Rules
- Respond ONLY with the JSON object. Do not add any explanations or conversational text.
- The "new_code" you provide will completely replace the original code block.
"""

class EditorAgent:
    def __init__(self, model_name: str):
        # LangChain会自动从环境变量中读取OPENAI_API_KEY和OPENAI_API_BASE
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.history = []
        logger.info(f"EditorAgent initialized with model: {model_name}")

    def _format_history(self):
        """Formats the conversation history for the prompt."""
        if not self.history:
            return "No history yet."
        
        formatted = []
        for turn in self.history:
            role = "User" if turn['role'] == 'user' else "Agent"
            formatted.append(f"{role}: {turn['content']}")
        return "\n\n".join(formatted)

    def _find_target_page_number(self, user_feedback: str) -> int:
        """从用户反馈中提取页码。"""
        # 使用正则表达式查找 "第X页" 或 "page X" 等模式
        matches = re.findall(r'(?:第|page)\s*(\d+)', user_feedback, re.IGNORECASE)
        if matches:
            return int(matches[0])
        return -1

    def _find_frame_for_slide(self, tex_content: str, slide_title: str) -> str:
        """根据幻灯片标题在TEX内容中找到对应的frame块。"""
        # This pattern is more robust: it finds all frame blocks first.
        # re.DOTALL allows '.' to match newlines.
        frames = re.findall(r"(\\begin\{frame\}.*?\\end\{frame\})", tex_content, re.DOTALL)
        
        # The title in the .tex file is formatted as \frametitle{The Title}
        # We need to check for this exact string inside each frame.
        search_str = f"\\frametitle{{{slide_title}}}"
        
        for frame in frames:
            if search_str in frame:
                # Return the first frame that contains the exact title string.
                return frame
        
        logger.warning(f"Could not find frame with title: {slide_title}")
        return None

    def _compile_tex(self, tex_path: str):
        """编译TEX文件为PDF。"""
        logger.info(f"Compiling {tex_path} to PDF...")
        
        # 假定此脚本的调用者在项目根目录或已将根目录加入sys.path
        # 我们需要从当前工作目录找到到tex文件的相对路径
        # tex_path是绝对路径
        project_root = os.getcwd() # 假设从根目录运行
        relative_tex_path = os.path.relpath(tex_path, project_root)
        output_dir = os.path.dirname(tex_path)

        command = [
            "xelatex",
            f"-output-directory={output_dir}",
            "-interaction=nonstopmode",
            relative_tex_path
        ]
        
        try:
            # 从项目根目录运行命令，以确保所有相对路径（如图片）正确
            # 运行两次以确保目录和引用正确
            subprocess.run(command, check=True, capture_output=True, text=True, cwd=project_root)
            subprocess.run(command, check=True, capture_output=True, text=True, cwd=project_root)
            logger.info("PDF compilation successful.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"PDF compilation failed. Error:\n{e.stdout}\n{e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("`xelatex` command not found. Please ensure a LaTeX distribution is installed and in your PATH.")
            return False

    def revise(self, user_feedback: str, tex_path: str, plan_path: str, output_dir: str):
        """
        接收用户反馈，修订TEX文件，并重新编译生成PDF
        """
        logger.info("Revising TeX file based on user feedback...")
        
        try:
            # 1. 读取文件
            with open(tex_path, 'r', encoding='utf-8') as f:
                tex_content = f.read()
            
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan_data = json.load(f)

            # 2. 定位逻辑
            page_number = self._find_target_page_number(user_feedback)
            if page_number == -1:
                return False, None, "Could not determine the target page number from feedback."

            if page_number <= 2:
                return False, None, "Editing the title page or table of contents is not yet supported."

            target_slide_number = page_number - 2
            
            target_slide = next((s for s in plan_data.get("slides_plan", []) if s.get("slide_number") == target_slide_number), None)

            if not target_slide:
                return False, None, f"Could not find slide data for slide number {target_slide_number} in the plan."

            slide_title = target_slide.get("title")
            if not slide_title:
                 return False, None, f"Slide {target_slide_number} has no title in the plan."

            old_code_snippet = self._find_frame_for_slide(tex_content, slide_title)
            if not old_code_snippet:
                return False, None, f"Could not find the frame for slide titled '{slide_title}' in the TeX file."

            # 3. 构建Prompt并调用LLM
            prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            formatted_history = self._format_history()
            
            logger.info(f"Invoking LLM to revise frame: {slide_title}")
            response = chain.invoke({
                "history": formatted_history,
                "user_feedback": user_feedback,
                "code_snippet": old_code_snippet
            })
            
            # 4. 解析与验证
            new_code = response.get("new_code")
            
            if not new_code:
                logger.error(f"LLM response is missing 'new_code': {response}")
                return False, None, "LLM response is incomplete."
                
            logger.debug(f"LLM proposed change for slide '{slide_title}':\n{new_code}")

            # 5. 执行文件修改
            new_tex_content = tex_content.replace(old_code_snippet, new_code)
            
            if new_tex_content == tex_content:
                logger.error("Failed to apply changes. The 'old_code' snippet might have issues.")
                return False, None, "Failed to replace the code snippet in the TeX file."

            # 6. 保存修改后的文件
            revised_tex_filename = os.path.basename(tex_path).replace(".tex", "_revised.tex")
            revised_tex_path = os.path.join(output_dir, revised_tex_filename)
            
            with open(revised_tex_path, 'w', encoding='utf-8') as f:
                f.write(new_tex_content)
            
            logger.info(f"Successfully revised TeX file and saved to {revised_tex_path}")

            # 7. 编译新的TEX文件
            if not self._compile_tex(revised_tex_path):
                # 编译失败也要记录历史
                assistant_message = f"Tried to modify slide '{slide_title}', but the resulting PDF failed to compile."
                self.history.append({"role": "user", "content": user_feedback})
                self.history.append({"role": "assistant", "content": assistant_message})
                return False, revised_tex_path, "Revision saved, but PDF compilation failed."
            
            # 8. 更新历史
            assistant_message = f"Successfully modified slide '{slide_title}' and recompiled the PDF."
            self.history.append({"role": "user", "content": user_feedback})
            self.history.append({"role": "assistant", "content": assistant_message})
            
            return True, revised_tex_path, "Revision and compilation successful."

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return False, None, str(e)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from plan file: {e}")
            return False, None, str(e)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            return False, None, str(e)
            
            with open(new_tex_path, 'w', encoding='utf-8') as f:
                f.write(new_tex_content)
            
            logger.info(f"Saved revised TeX file to: {new_tex_path}")
            
            # TODO: 实现编译逻辑
            
            return False, new_tex_path, "File modification successful, compilation not implemented yet."

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return False, None, str(e)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return False, None, "Failed to parse LLM response."
        except Exception as e:
            logger.error(f"An unexpected error occurred in EditorAgent: {e}", exc_info=True)
            return False, None, f"An unexpected error occurred: {e}"

