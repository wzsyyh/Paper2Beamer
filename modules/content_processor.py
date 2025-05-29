"""
内容处理模块：利用大语言模型对提取的原始内容进行结构化处理
"""
import os
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

# 尝试导入OpenAI相关包
try:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class ContentProcessor:
    def __init__(
        self, 
        raw_content_path: str, 
        output_dir: str = "output",
        model_name: str = "gpt-4o",
        temperature: float = 0.0,
        api_key: Optional[str] = None
    ):
        """
        初始化内容处理器
        
        Args:
            raw_content_path: 原始内容JSON文件路径
            output_dir: 输出目录
            model_name: 要使用的语言模型名称
            temperature: 模型生成的随机性程度
            api_key: OpenAI API密钥
        """
        self.raw_content_path = raw_content_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 加载原始内容
        self.raw_content = self._load_raw_content()
        
        # 初始化模型
        self._init_model()
    
    def _load_raw_content(self) -> Dict[str, Any]:
        """加载原始内容"""
        try:
            with open(self.raw_content_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            return content
        except Exception as e:
            self.logger.error(f"加载原始内容失败: {str(e)}")
            return {}
    
    def _init_model(self):
        """初始化语言模型"""
        if not OPENAI_AVAILABLE:
            self.logger.warning("无法导入OpenAI相关包，将无法使用大语言模型进行内容结构化")
            self.llm = None
            return
            
        if not self.api_key:
            self.logger.warning("未提供OpenAI API密钥，将无法使用大语言模型进行内容结构化")
            self.llm = None
            return
            
        try:
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=self.api_key
            )
            self.logger.info(f"已初始化语言模型: {self.model_name}")
        except Exception as e:
            self.logger.error(f"初始化语言模型失败: {str(e)}")
            self.llm = None
    
    def process_content(self) -> Dict[str, Any]:
        """
        处理原始内容，进行结构化
        
        Returns:
            Dict: 结构化后的内容
        """
        if not self.raw_content:
            self.logger.error("没有原始内容可处理")
            return {}
            
        if not self.llm:
            self.logger.error("未初始化语言模型，无法进行内容结构化")
            return {}
            
        # 提取基本信息
        self.logger.info("开始提取论文基本信息...")
        paper_info = self._extract_paper_info()
        
        # 提取章节结构
        self.logger.info("开始提取论文章节结构...")
        sections = self._extract_sections()
        
        # 提取图片信息
        self.logger.info("开始提取图片信息...")
        figures = self._extract_figures()
        
        # 提取参考文献
        self.logger.info("开始提取参考文献...")
        references = self._extract_references()
        
        # 合并处理结果
        processed_content = {
            "paper_info": paper_info,
            "sections": sections,
            "figures": figures,
            "references": references,
            "pdf_path": self.raw_content.get("pdf_path", ""),
            "document_info": self.raw_content.get("document_info", {})
        }
        
        return processed_content
    
    def _extract_paper_info(self) -> Dict[str, Any]:
        """
        提取论文基本信息
        
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
            # 获取前几页的文本内容
            pages_content = self.raw_content.get("pages_content", [])
            first_pages_text = ""
            
            # 只获取前三页的内容，通常标题、作者和摘要都在前几页
            for i, page_info in enumerate(pages_content):
                if i < 3:
                    first_pages_text += page_info.get("text", {}).get("plain", "") + "\n\n"
            
            # 构建提示
            prompt = ChatPromptTemplate.from_template("""
            你是一个专业的学术论文分析助手。请从以下学术论文的前几页文本中提取关键信息。
            
            请提取以下信息：
            1. 论文标题
            2. 作者列表
            3. 作者单位/机构
            4. 摘要内容
            5. 关键词（如果有）
            
            请以JSON格式返回，格式如下：
            ```json
            {{
              "title": "论文标题",
              "authors": ["作者1", "作者2", ...],
              "affiliations": ["单位1", "单位2", ...],
              "abstract": "摘要全文",
              "keywords": ["关键词1", "关键词2", ...]
            }}
            ```
            
            仅返回JSON对象，不要有任何其他文字。
            
            论文文本：
            {text}
            """)
            
            # 调用LLM
            chain = prompt | self.llm
            response = chain.invoke({"text": first_pages_text})
            
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
            self.logger.error(f"使用LLM提取论文信息时出错: {str(e)}")
        
        return paper_info
    
    def _extract_sections(self) -> List[Dict[str, Any]]:
        """
        提取论文章节结构
        
        Returns:
            List: 章节列表
        """
        # 默认空结果
        sections = []
        
        try:
            # 获取所有页面的文本
            pages_content = self.raw_content.get("pages_content", [])
            full_text = ""
            
            for page_info in pages_content:
                full_text += page_info.get("text", {}).get("plain", "") + "\n\n"
                
            # 获取目录信息（如果有）
            toc = self.raw_content.get("toc", [])
            toc_text = ""
            if toc:
                toc_text = "论文目录结构:\n"
                for item in toc:
                    indent = "  " * (item.get("level", 1) - 1)
                    toc_text += f"{indent}- {item.get('title', '')}: 第{item.get('page', 0)}页\n"
            
            # 构建提示
            prompt = ChatPromptTemplate.from_template("""
            你是一个专业的学术论文分析助手。请从以下学术论文的文本中提取章节结构。
            
            {toc_info}
            
            请提取以下信息：
            1. 所有章节标题及其层级关系
            2. 每个章节的内容摘要（简明扼要）
            3. 尽量与原始目录结构保持一致
            
            请以JSON格式返回，格式如下：
            ```json
            [
              {{
                "level": 1,
                "title": "一级标题",
                "summary": "该章节的内容摘要",
                "children": [
                  {{
                    "level": 2,
                    "title": "二级标题",
                    "summary": "该章节的内容摘要",
                    "children": []
                  }}
                ]
              }}
            ]
            ```
            
            仅返回JSON数组，不要有任何其他文字。确保JSON结构严格正确。
            
            论文文本：
            {text}
            """)
            
            # 调用LLM
            chain = prompt | self.llm
            response = chain.invoke({
                "text": full_text[:15000],  # 限制长度
                "toc_info": toc_text
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
            sections = json.loads(json_str)
        
        except Exception as e:
            self.logger.error(f"使用LLM提取章节结构时出错: {str(e)}")
        
        return sections
    
    def _extract_figures(self) -> List[Dict[str, Any]]:
        """
        提取论文中的图表信息
        
        Returns:
            List: 图表信息列表
        """
        # 默认空结果
        figures = []
        
        try:
            # 获取原始图像信息
            raw_images = self.raw_content.get("images", [])
            
            # 如果没有图像，直接返回空列表
            if not raw_images:
                return figures
                
            # 获取所有页面的文本，用于寻找图片标题
            pages_content = self.raw_content.get("pages_content", [])
            pages_text = []
            
            for page_info in pages_content:
                pages_text.append(page_info.get("text", {}).get("plain", ""))
            
            # 准备数据用于API处理
            figures_data = []
            for img in raw_images:
                # 跳过非内嵌图像（如页面渲染）
                if img.get("type") != "embedded":
                    continue
                    
                figure_data = {
                    "page": img.get("page", 0),
                    "filename": img.get("filename", ""),
                    "width": img.get("width", 0),
                    "height": img.get("height", 0),
                    "bbox": img.get("bbox", [])
                }
                
                # 尝试从页面文本中提取图片周围的文本（用于后续分析）
                if img.get("page") and 0 < img.get("page") <= len(pages_text):
                    page_idx = img.get("page") - 1
                    page_text = pages_text[page_idx]
                    
                    # 提取页面文本，用于后续分析
                    figure_data["page_text"] = page_text
                
                figures_data.append(figure_data)
            
            # 如果图片太多，只处理前20张
            if len(figures_data) > 20:
                self.logger.warning(f"图片数量过多({len(figures_data)}张)，只处理前20张")
                figures_data = figures_data[:20]
            
            # 构建提示
            prompt = ChatPromptTemplate.from_template("""
            你是一个专业的学术论文分析助手。请分析以下论文中的图片信息。
            
            这些是从PDF中提取的图片信息：
            {figures_data}
            
            请尝试为每张图片添加以下信息：
            1. 图片的可能标题
            2. 图片的简短描述
            3. 图片所属的可能章节
            
            请以JSON格式返回，格式如下：
            ```json
            [
              {{
                "figure_id": 1,
                "page": 图片所在页数,
                "filename": "图片文件名",
                "title": "推测的图片标题",
                "description": "图片的简短描述",
                "section": "图片可能所属的章节"
              }}
            ]
            ```
            
            仅返回JSON数组，不要有任何其他文字。确保JSON结构严格正确。
            """)
            
            # 调用LLM
            chain = prompt | self.llm
            response = chain.invoke({
                "figures_data": json.dumps(figures_data, ensure_ascii=False, indent=2)
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
            figures = json.loads(json_str)
            
            # 添加原始图像信息
            for fig in figures:
                fig_filename = fig.get("filename")
                for raw_img in raw_images:
                    if raw_img.get("filename") == fig_filename:
                        fig["path"] = raw_img.get("path", "")
                        fig["width"] = raw_img.get("width", 0)
                        fig["height"] = raw_img.get("height", 0)
                        fig["bbox"] = raw_img.get("bbox", [])
                        break
        
        except Exception as e:
            self.logger.error(f"使用LLM提取图片信息时出错: {str(e)}")
        
        return figures
    
    def _extract_references(self) -> List[Dict[str, Any]]:
        """
        提取论文中的参考文献
        
        Returns:
            List: 参考文献列表
        """
        # 默认空结果
        references = []
        
        try:
            # 获取所有页面的文本
            pages_content = self.raw_content.get("pages_content", [])
            
            # 寻找参考文献部分
            references_text = ""
            found_references = False
            
            for page_info in reversed(pages_content):  # 从后向前寻找参考文献
                page_text = page_info.get("text", {}).get("plain", "")
                
                # 检查是否包含参考文献相关标题
                if not found_references:
                    if re.search(r'references|bibliography|参考文献', page_text, re.IGNORECASE):
                        found_references = True
                        references_text = page_text + "\n\n" + references_text
                else:
                    references_text = page_text + "\n\n" + references_text
            
            # 如果未找到参考文献部分，则使用最后几页
            if not found_references and len(pages_content) > 0:
                last_pages = min(3, len(pages_content))
                for i in range(1, last_pages + 1):
                    page_idx = len(pages_content) - i
                    if page_idx >= 0:
                        page_text = pages_content[page_idx].get("text", {}).get("plain", "")
                        references_text = page_text + "\n\n" + references_text
            
            # 构建提示
            prompt = ChatPromptTemplate.from_template("""
            你是一个专业的学术论文分析助手。请从以下学术论文的参考文献部分提取参考文献信息。
            
            请提取所有参考文献，对于每一条参考文献，请识别以下信息：
            1. 参考文献编号
            2. 作者
            3. 标题
            4. 发表年份
            5. 发表刊物/会议
            
            请以JSON格式返回，格式如下：
            ```json
            [
              {{
                "index": 1,
                "authors": ["作者1", "作者2", ...],
                "title": "论文标题",
                "year": 2020,
                "venue": "发表刊物/会议名称",
                "raw_text": "原始参考文献文本"
              }}
            ]
            ```
            
            仅返回JSON数组，不要有任何其他文字。确保JSON结构严格正确。
            
            参考文献文本：
            {text}
            """)
            
            # 调用LLM
            chain = prompt | self.llm
            response = chain.invoke({
                "text": references_text
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
            references = json.loads(json_str)
        
        except Exception as e:
            self.logger.error(f"使用LLM提取参考文献时出错: {str(e)}")
        
        return references
    
    def save_processed_content(self, processed_content, output_file=None):
        """
        保存处理后的结构化内容到JSON文件
        
        Args:
            processed_content: 处理后的内容
            output_file: 输出文件路径，如果为None则使用默认路径
            
        Returns:
            str: 保存的文件路径
        """
        if output_file is None:
            output_file = os.path.join(self.output_dir, "structured_content.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_content, f, ensure_ascii=False, indent=2)
        
        return output_file

# 便捷函数
def process_content(raw_content_path, output_dir="output", model_name="gpt-4o", api_key=None):
    """
    处理原始内容并结构化（便捷函数）
    
    Args:
        raw_content_path: 原始内容JSON文件路径
        output_dir: 输出目录
        model_name: 要使用的语言模型名称
        api_key: OpenAI API密钥
        
    Returns:
        tuple: (处理后的内容, 保存的文件路径)
    """
    processor = ContentProcessor(
        raw_content_path=raw_content_path,
        output_dir=output_dir,
        model_name=model_name,
        api_key=api_key
    )
    
    processed_content = processor.process_content()
    
    if processed_content:
        output_file = processor.save_processed_content(processed_content)
        return processed_content, output_file
    
    return None, None 