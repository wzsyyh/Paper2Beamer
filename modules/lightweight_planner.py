"""
轻量级演示计划生成模块：直接处理markdown文本生成演示计划
适配轻量级提取器的简化数据结构
"""
import os
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# 加载环境变量
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("env.local"):
    load_dotenv("env.local")

# 尝试导入OpenAI相关包
try:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    from langchain.schema import HumanMessage, AIMessage, SystemMessage
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# 导入提示词
from prompts import (
    KEY_CONTENT_EXTRACTION_PROMPT, 
    SLIDES_PLANNING_PROMPT,
    INTERACTIVE_REFINEMENT_SYSTEM_MESSAGE
)

class LightweightPlanner:
    def __init__(
        self, 
        lightweight_content_path: str, 
        output_dir: str = "output",
        model_name: str = "gpt-4o",
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        language: str = "zh"
    ):
        """
        初始化轻量级演示计划生成器
        
        Args:
            lightweight_content_path: 轻量级内容JSON文件路径
            output_dir: 输出目录
            model_name: 要使用的语言模型名称
            temperature: 模型生成的随机性程度
            api_key: OpenAI API密钥
            language: 输出语言，zh为中文，en为英文
        """
        self.lightweight_content_path = lightweight_content_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.language = language
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 加载轻量级内容
        self.lightweight_content = self._load_lightweight_content()
        
        # 初始化模型
        self._init_model()
        
        # 初始化对话历史
        self.conversation_history = []
        
        # 演示计划数据
        self.paper_info = {}
        self.key_content = {}
        self.slides_plan = []
        self.presentation_plan = {}
    
    def _load_lightweight_content(self) -> Dict[str, Any]:
        """加载轻量级内容"""
        try:
            with open(self.lightweight_content_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            return content
        except Exception as e:
            self.logger.error(f"加载轻量级内容失败: {str(e)}")
            return {}
    
    def _init_model(self):
        """初始化语言模型"""
        if not OPENAI_AVAILABLE:
            self.logger.warning("无法导入OpenAI相关包，将无法使用大语言模型生成演示计划")
            self.llm = None
            return
            
        if not self.api_key:
            self.logger.warning("未提供OpenAI API密钥，将无法使用大语言模型生成演示计划")
            self.llm = None
            return
            
        try:
            self.llm = ChatOpenAI(
                model_name=self.model_name,
                temperature=self.temperature,
                openai_api_key=self.api_key
            )
            self.logger.info(f"已初始化语言模型: {self.model_name}")
        except Exception as e:
            self.logger.error(f"初始化语言模型失败: {str(e)}")
            self.llm = None
    
    def generate_presentation_plan(self) -> Dict[str, Any]:
        """
        生成演示计划
        
        Returns:
            Dict: 演示计划
        """
        if not self.lightweight_content:
            self.logger.error("没有轻量级内容可处理")
            return {}
            
        if not self.llm:
            self.logger.error("未初始化语言模型，无法生成演示计划")
            return {}
        
        # 提取论文基本信息
        self.logger.info("从markdown文本提取论文基本信息...")
        self.paper_info = self._extract_paper_info()
        
        # 提取关键内容
        self.logger.info("从markdown文本提取论文关键内容...")
        self.key_content = self._extract_key_content(self.paper_info)
        
        # 规划演示幻灯片
        self.logger.info("规划演示幻灯片...")
        self.slides_plan = self._plan_slides(self.paper_info, self.key_content)
        
        # 组装结果
        self.presentation_plan = {
            "paper_info": self.paper_info,
            "key_content": self.key_content,
            "slides_plan": self.slides_plan,
            "language": self.language,
            "pdf_path": self.lightweight_content.get("pdf_path", "")
        }
        
        return self.presentation_plan
    
    def _extract_paper_info(self) -> Dict[str, Any]:
        """
        从markdown文本提取论文基本信息
        
        Returns:
            Dict: 包含标题、作者、摘要等信息的字典
        """
        # 默认空结果
        paper_info = {
            "title": "",
            "authors": [],
            "affiliations": [],
            "abstract": "",
            "keywords": []
        }
        
        try:
            # 获取markdown文本的前3000字符（通常包含标题、作者和摘要）
            full_text = self.lightweight_content.get("full_text", "")
            first_part = full_text[:3000]
            
            # 构建提示 - 强制使用英文以确保JSON内容为英文
            language_prompt = "Please answer in English"
            
            # 简化的论文信息提取提示
            paper_info_prompt = """
            你是一位学术论文分析专家。{language_prompt}。请从以下论文文本中提取基本信息：

            论文文本：
            {text}

            请提取以下信息并以JSON格式返回：
            1. 论文标题
            2. 作者列表
            3. 机构信息
            4. 摘要内容
            5. 关键词（如果有）

            返回格式：
            ```json
            {{
              "title": "论文标题",
              "authors": ["作者1", "作者2"],
              "affiliations": ["机构1", "机构2"],
              "abstract": "摘要内容",
              "keywords": ["关键词1", "关键词2"]
            }}
            ```

            仅返回JSON对象，不要有任何其他文字。
            """
            
            prompt = ChatPromptTemplate.from_template(paper_info_prompt)
            
            # 调用LLM
            chain = prompt | self.llm
            response = chain.invoke({
                "text": first_part,
                "language_prompt": language_prompt
            })
            
            # 解析结果
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # 提取JSON部分
            json_match = re.search(r'```(?:json)?(.*?)```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_str = response_text.strip()
            
            # 尝试解析JSON
            extracted_info = json.loads(json_str)
            paper_info.update(extracted_info)
        
        except Exception as e:
            self.logger.error(f"提取论文信息时出错: {str(e)}")
        
        return paper_info
    
    def _extract_key_content(self, paper_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        从markdown文本提取论文关键内容
        
        Args:
            paper_info: 论文基本信息
            
        Returns:
            Dict: 论文关键内容
        """
        key_content = {
            "main_contributions": [],
            "methodology": "",
            "results": "",
            "figures": [],
            "conclusions": ""
        }
        
        try:
            # 获取完整的markdown文本
            full_text = self.lightweight_content.get("full_text", "")
            
            # 限制文本长度以避免超出模型限制，增加到25000字符以保留更多上下文
            text_for_analysis = full_text[:25000]
            
            # 获取图片信息
            images = self.lightweight_content.get("images", [])
            
            # 处理图片信息，为每个图片生成描述
            figures_info = []
            for img in images:
                figure_info = {
                    "id": img.get("id", ""),
                    "filename": img.get("filename", ""),
                    "path": img.get("path", ""),
                    "caption": img.get("caption", "")
                }
                figures_info.append(figure_info)
            
            # 构建提示 - 强制使用英文以确保JSON内容为英文
            language_prompt = "Please answer in English"
            
            prompt = ChatPromptTemplate.from_template(KEY_CONTENT_EXTRACTION_PROMPT)
            
            # 调用LLM
            chain = prompt | self.llm
            response = chain.invoke({
                "title": paper_info.get("title", ""),
                "authors": ", ".join(paper_info.get("authors", [])),
                "abstract": paper_info.get("abstract", ""),
                "toc_info": "",  # markdown文本已经包含结构信息
                "figures_info": json.dumps(figures_info, ensure_ascii=False),
                "text": text_for_analysis,
                "language_prompt": language_prompt
            })
            
            # 解析结果
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # 提取JSON部分
            json_match = re.search(r'```(?:json)?(.*?)```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_str = response_text.strip()
            
            # 尝试解析JSON
            try:
                extracted_content = json.loads(json_str)
                key_content.update(extracted_content)
            except json.JSONDecodeError as e:
                self.logger.error(f"解析关键内容JSON时出错: {str(e)}")
            
            # 确保图片信息正确关联
            for idx, fig in enumerate(key_content.get("figures", [])):
                if idx < len(images):
                    original_img = images[idx]
                    fig["id"] = original_img.get("id", f"fig{idx+1}")
                    fig["filename"] = original_img.get("filename", "")
                    fig["path"] = original_img.get("path", "")
                    if not fig.get("caption"):
                        fig["caption"] = original_img.get("caption", "")
            
        except Exception as e:
            self.logger.error(f"提取关键内容时出错: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return key_content
    
    def _plan_slides(self, paper_info: Dict[str, Any], key_content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        规划演示幻灯片
        
        Args:
            paper_info: 论文基本信息
            key_content: 论文关键内容
            
        Returns:
            List: 幻灯片计划列表
        """
        slides_plan = []
        
        try:
            # 构建提示 - 强制使用英文以确保JSON内容为英文
            language_prompt = "Please answer in English"
            
            prompt = ChatPromptTemplate.from_template(SLIDES_PLANNING_PROMPT)
            
            # 调用LLM
            chain = prompt | self.llm
            response = chain.invoke({
                "title": paper_info.get("title", ""),
                "authors": ", ".join(paper_info.get("authors", [])),
                "abstract": paper_info.get("abstract", ""),
                "contributions": json.dumps(key_content.get("main_contributions", []), ensure_ascii=False),
                "background_motivation": key_content.get("background_motivation", ""),
                "methodology": key_content.get("methodology", ""),
                "experimental_setup": key_content.get("experimental_setup", ""),
                "results": key_content.get("results", ""),
                "conclusions": key_content.get("conclusions", ""),
                "figures_info": json.dumps(key_content.get("figures", []), ensure_ascii=False),
                "language_prompt": language_prompt
            })
            
            # 解析结果
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # 提取JSON部分
            json_match = re.search(r'```(?:json)?(.*?)```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_str = response_text.strip()
            
            # 尝试解析JSON
            slides_plan = json.loads(json_str)
            
            # 验证图片引用的有效性
            available_figures = {fig["id"]: fig for fig in key_content.get("figures", [])}
            
            for slide in slides_plan:
                if slide.get("includes_figure") and slide.get("figure_reference"):
                    fig_ref = slide.get("figure_reference")
                    if fig_ref and "id" in fig_ref:
                        fig_id = fig_ref.get("id")
                        if fig_id in available_figures:
                            # 更新图片引用信息
                            matched_fig = available_figures[fig_id]
                            fig_ref.update(matched_fig)
                        else:
                            self.logger.warning(f"幻灯片引用了不存在的图片ID: {fig_id}")
                            slide["includes_figure"] = False
                            slide["figure_reference"] = None
        
        except Exception as e:
            self.logger.error(f"规划幻灯片时出错: {str(e)}")
        
        return slides_plan
    
    def save_presentation_plan(self, presentation_plan, output_file=None):
        """
        保存演示计划到JSON文件
        
        Args:
            presentation_plan: 演示计划
            output_file: 输出文件路径，如果为None则使用默认路径
            
        Returns:
            str: 保存的文件路径
        """
        if output_file is None:
            output_file = os.path.join(self.output_dir, "lightweight_presentation_plan.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(presentation_plan, f, ensure_ascii=False, indent=2)
        
        # 记录文件大小
        file_size = os.path.getsize(output_file)
        self.logger.info(f"演示计划已保存到: {output_file}")
        self.logger.info(f"文件大小: {file_size / 1024:.2f}KB")
        
        return output_file
    
    def interactive_refinement(self, initial_feedback=None) -> Dict[str, Any]:
        """
        与用户进行多轮交互，优化演示计划
        
        Args:
            initial_feedback: 用户的初始反馈
            
        Returns:
            Dict: 优化后的演示计划
        """
        # 确保已经生成了初始演示计划
        if not self.presentation_plan:
            self.presentation_plan = self.generate_presentation_plan()
            if not self.presentation_plan:
                self.logger.error("无法生成初始演示计划，无法进行交互式优化")
                return {}
        
        # 初始化对话历史，包括系统消息
        language_prompt = "中文" if self.language == "zh" else "English"
        system_message = INTERACTIVE_REFINEMENT_SYSTEM_MESSAGE.format(
            title=self.paper_info.get('title', '未知标题'),
            authors=', '.join(self.paper_info.get('authors', ['未知作者'])),
            language_prompt=language_prompt
        )
        
        self.conversation_history = [SystemMessage(content=system_message)]
        
        # 如果有初始反馈，添加到对话历史
        if initial_feedback:
            return self._process_user_feedback(initial_feedback)
        
        return self.presentation_plan
    
    def _process_user_feedback(self, user_feedback: str) -> Dict[str, Any]:
        """
        处理用户反馈，更新演示计划
        
        Args:
            user_feedback: 用户的反馈内容
            
        Returns:
            Dict: 更新后的演示计划
        """
        if not self.llm:
            self.logger.error("未初始化语言模型，无法处理用户反馈")
            return self.presentation_plan
        
        # 将用户反馈添加到对话历史
        self.conversation_history.append(HumanMessage(content=user_feedback))
        
        try:
            # 生成摘要描述当前演示计划状态
            current_plan_summary = self._generate_plan_summary()
            
            # 构建提示
            prompt = f"""
            基于用户的反馈，请考虑如何改进当前的演示计划。
            
            当前演示计划摘要：
            {current_plan_summary}
            
            请提供两部分响应：
            1. 对用户反馈的回应，解释你将如何调整演示计划
            2. 修改后的幻灯片计划（如果需要调整），以JSON格式提供
            
            如果需要修改幻灯片计划，请使用以下格式：
            ```json
            [
              {{
                "slide_number": 1,
                "title": "幻灯片标题",
                "content": ["要点1", "要点2", ...],
                "includes_figure": false,
                "figure_reference": null
              }},
              ...
            ]
            ```
            """
            
            # 获取模型响应
            response = self.llm.invoke(self.conversation_history + [HumanMessage(content=prompt)])
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # 将响应添加到对话历史
            self.conversation_history.append(AIMessage(content=response_text))
            
            # 检查是否包含JSON计划更新
            json_match = re.search(r'```(?:json)?(.*?)```', response_text, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(1).strip()
                    new_slides_plan = json.loads(json_str)
                    
                    # 更新幻灯片计划
                    self.slides_plan = new_slides_plan
                    self.presentation_plan["slides_plan"] = new_slides_plan
                    
                    self.logger.info("已根据用户反馈更新演示计划")
                except json.JSONDecodeError:
                    self.logger.warning("无法解析模型返回的JSON，使用原有计划")
            
            return self.presentation_plan
            
        except Exception as e:
            self.logger.error(f"处理用户反馈时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.presentation_plan
    
    def _generate_plan_summary(self) -> str:
        """
        生成当前演示计划的摘要
        
        Returns:
            str: 演示计划摘要
        """
        slides_count = len(self.slides_plan)
        
        summary = f"当前演示计划包含{slides_count}张幻灯片：\n"
        
        for i, slide in enumerate(self.slides_plan[:5]):  # 只显示前5张幻灯片
            title = slide.get("title", "无标题")
            summary += f"{i+1}. {title}\n"
        
        if slides_count > 5:
            summary += f"... 还有{slides_count-5}张幻灯片\n"
            
        return summary
    
    def continue_conversation(self, user_message: str) -> Tuple[str, Dict[str, Any]]:
        """
        继续与用户的对话，更新演示计划
        
        Args:
            user_message: 用户的消息
            
        Returns:
            Tuple: (模型响应, 更新后的演示计划)
        """
        updated_plan = self._process_user_feedback(user_message)
        
        # 获取最新的模型响应
        if self.conversation_history and isinstance(self.conversation_history[-1], AIMessage):
            response = self.conversation_history[-1].content
        else:
            response = "抱歉，处理您的反馈时出现了问题。"
            
        return response, updated_plan

# 便捷函数
def generate_lightweight_presentation_plan(
    lightweight_content_path, 
    output_dir="output", 
    model_name="gpt-4o", 
    api_key=None, 
    language="zh", 
    user_feedback=None
):
    """
    从轻量级内容生成演示计划（便捷函数）
    
    Args:
        lightweight_content_path: 轻量级内容JSON文件路径
        output_dir: 输出目录
        model_name: 要使用的语言模型名称
        api_key: OpenAI API密钥
        language: 输出语言，zh为中文，en为英文
        user_feedback: 用户的初始反馈（可选）
        
    Returns:
        tuple: (演示计划, 保存的文件路径, 规划器实例)
    """
    planner = LightweightPlanner(
        lightweight_content_path=lightweight_content_path,
        output_dir=output_dir,
        model_name=model_name,
        api_key=api_key,
        language=language
    )
    
    # 首先生成基本演示计划
    presentation_plan = planner.generate_presentation_plan()
    
    # 如果提供了用户反馈，进行交互式优化
    if user_feedback:
        presentation_plan = planner.interactive_refinement(user_feedback)
    
    if presentation_plan:
        output_file = planner.save_presentation_plan(presentation_plan)
        return presentation_plan, output_file, planner
    
    return None, None, planner
