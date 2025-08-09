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
# ... existing PROMPT_TEMPLATE ...
PROMPT_TEMPLATE = """
# Role
You are an expert LaTeX developer specializing in Beamer presentations. Your task is to function as a code modification assistant. You will receive a specific block of LaTeX code and a user's request to change it. Your only job is to provide the modified version of that code block.

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
        logger.info(f"EditorAgent initialized with model: {model_name}")

    def _find_target_page_number(self, user_feedback: str) -> int:
# ... existing _find_target_page_number method ...
        """从用户反馈中提取页码。"""
        # 使用正则表达式查找 "第X页" 或 "page X" 等模式
        matches = re.findall(r'(?:第|page)\s*(\d+)', user_feedback, re.IGNORECASE)
        if matches:
            return int(matches[0])
        return -1

    def _find_frame_for_slide(self, tex_content: str, slide_title: str) -> str:
# ... existing _find_frame_for_slide method ...
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
        output_dir = os.path.dirname(tex_path)
        
        # 使用xelatex，它对UTF-8和现代字体支持更好
        command = [
            "xelatex",
            "-interaction=nonstopmode",
            f"-output-directory={output_dir}",
            tex_path
        ]
        
        try:
            # 运行两次以确保目录和引用正确
            subprocess.run(command, check=True, capture_output=True, text=True)
            subprocess.run(command, check=True, capture_output=True, text=True)
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
            
            logger.info(f"Invoking LLM to revise frame: {slide_title}")
            response = chain.invoke({
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
                return False, revised_tex_path, "Revision saved, but PDF compilation failed."
            
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


            
            # 执行替换
            new_tex_content = tex_content.replace(old_code, new_code, 1)
            
            # 6. 保存新文件
            revision_count = 1
            while True:
                revision_tex_name = f"{os.path.splitext(os.path.basename(tex_path))[0]}_rev{revision_count}.tex"
                new_tex_path = os.path.join(output_dir, revision_tex_name)
                if not os.path.exists(new_tex_path):
                    break
                revision_count += 1
            
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

