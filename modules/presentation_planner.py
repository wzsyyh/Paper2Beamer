"""
演示计划生成模块：直接从原始PDF内容规划演示文稿
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

class PresentationPlanner:
    def __init__(
        self, 
        raw_content_path: str, 
        output_dir: str = "output",
        model_name: str = "gpt-4o",
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        language: str = "zh"
    ):
        """
        初始化演示计划生成器
        
        Args:
            raw_content_path: 原始内容JSON文件路径
            output_dir: 输出目录
            model_name: 要使用的语言模型名称
            temperature: 模型生成的随机性程度
            api_key: OpenAI API密钥
            language: 输出语言，zh为中文，en为英文
        """
        self.raw_content_path = raw_content_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.language = language
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 加载原始内容
        self.raw_content = self._load_raw_content()
        
        # 初始化模型
        self._init_model()
        
        # 初始化对话历史
        self.conversation_history = []
        
        # 演示计划数据
        self.paper_info = {}
        self.key_content = {}
        self.slides_plan = []
        self.presentation_plan = {}
        
        # 新增：获取session_id和images目录下所有图片，并建立id到文件名映射
        self.session_id = os.path.basename(os.path.dirname(self.raw_content_path))
        self.images_dir = os.path.join("output", "images", self.session_id)
        if os.path.exists(self.images_dir):
            self.available_images = sorted(os.listdir(self.images_dir))
        else:
            self.available_images = []
        # 建立 fig0, fig1, ... 到真实文件名的映射
        self.id_to_filename = {f"fig{i}": fname for i, fname in enumerate(self.available_images)}
    
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
        if not self.raw_content:
            self.logger.error("没有原始内容可处理")
            return {}
            
        if not self.llm:
            self.logger.error("未初始化语言模型，无法生成演示计划")
            return {}
        
        # 提取论文基本信息
        self.logger.info("提取论文基本信息...")
        self.paper_info = self._extract_paper_info()
        
        # 提取关键内容
        self.logger.info("提取论文关键内容...")
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
            "pdf_path": self.raw_content.get("pdf_path", "")
        }
        
        return self.presentation_plan
    
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
            language_prompt = "请用中文回答" if self.language == "zh" else "Please answer in English"
            
            prompt = ChatPromptTemplate.from_template("""
            你是一个专业的学术论文分析助手。请从以下学术论文的前几页文本中提取关键信息。{language_prompt}。
            
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
            response = chain.invoke({
                "text": first_pages_text,
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
        提取论文关键内容
        
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
            # 确保raw_content是字典格式
            raw_content = self.raw_content
            if isinstance(raw_content, list) and len(raw_content) > 0:
                raw_content = raw_content[0]
            
            # 获取页面内容
            pages_content = []
            if isinstance(raw_content, dict):
                pages_content = raw_content.get("pages_content", [])
            else:
                self.logger.warning("原始内容格式不正确，无法提取页面内容")
                return key_content
            
            full_text = ""
            
            # 为每页文本创建索引，以便后续查找图片周围的文本
            page_texts = {}
            for page_info in pages_content:
                page_num = page_info.get("page_num", 0)
                page_text = page_info.get("text", {}).get("plain", "")
                page_texts[page_num] = page_text
                full_text += page_text + "\n\n"
            
            # 获取目录信息（如果有）
            toc = []
            if isinstance(raw_content, dict):
                toc = raw_content.get("toc", [])
                
            toc_text = ""
            if toc:
                toc_text = "论文目录结构:\n"
                for item in toc:
                    indent = "  " * (item.get("level", 1) - 1)
                    toc_text += f"{indent}- {item.get('title', '')}: 第{item.get('page', 0)}页\n"
            
            # 获取图片信息
            images = []
            if isinstance(raw_content, dict):
                images = raw_content.get("images", [])
                
            images_info = []
            
            # 对图片进行分组（合并相关图片）
            image_groups = self._identify_image_groups(images)
            
            # 处理每个图片组
            for group_idx, group in enumerate(image_groups):
                # 选择组中最大/最重要的图片作为代表
                representative = max(group, key=lambda img: img.get("importance", 0) if "importance" in img else 0)
                
                # 获取组的边界框
                group_bbox = self._get_group_bbox(group)
                
                # 提取图片周围的文本
                surrounding_text = ""
                for img in group:
                    img_page = img.get("page", 0)
                    if img_page in page_texts:
                        text = self._extract_surrounding_text(img, page_texts)
                        if text:
                            surrounding_text += text + "\n"
                
                # 生成图片信息
                image_info = {
                    "id": f"fig{group_idx+1}",
                    "page": representative.get("page", 0),
                    "path": representative.get("path", ""),
                    "width": representative.get("width", 0),
                    "height": representative.get("height", 0),
                    "bbox": group_bbox,
                    "group_size": len(group),
                    "surrounding_text": surrounding_text
                }
                
                images_info.append(image_info)
            
            # 构建提示
            language_prompt = "请用中文回答" if self.language == "zh" else "Please answer in English"
            
            prompt = ChatPromptTemplate.from_template("""
            你是一个专业的学术论文分析助手。{language_prompt}。请从以下学术论文信息中提取关键内容，以便创建演示文稿。
            
            论文标题: {title}
            作者: {authors}
            摘要: {abstract}
            
            {toc_info}
            
            请提取以下关键内容：
            
            1. 主要贡献点（3-5点简短的要点）
            2. 方法论概述（简明扼要）
            3. 主要结果和发现（简明扼要）
            4. 结论和未来工作（简明扼要）
            5. 重要图表的解释和意义
            
            对于图表，请分析以下信息并提供解释：
            {figures_info}
            
            请以JSON格式返回，格式如下：
            ```json
            {{
              "main_contributions": ["贡献点1", "贡献点2", ...],
              "methodology": "方法论概述",
              "results": "主要结果和发现",
              "figures": [
                {{
                  "id": "图片ID",
                  "title": "推测的图片标题",
                  "description": "图片的简短描述",
                  "importance": "图片在论文中的重要性（高/中/低）",
                  "relevance": "图片与哪个部分最相关（方法/结果/等）",
                  "caption_length": "建议的标题长度（short/medium/long）"
                }}
              ],
              "conclusions": "结论和未来工作"
            }}
            ```
            
            仅返回JSON对象，不要有任何其他文字。确保JSON结构严格正确。
            
            论文文本：
            {text}
            """)
            
            # 调用LLM
            chain = prompt | self.llm
            response = chain.invoke({
                "title": paper_info.get("title", ""),
                "authors": ", ".join(paper_info.get("authors", [])),
                "abstract": paper_info.get("abstract", ""),
                "toc_info": toc_text,
                "figures_info": json.dumps(images_info, ensure_ascii=False),
                "text": full_text[:15000],  # 限制长度
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
            
            # 改进图表信息匹配逻辑，直接用真实图片名和路径
            for idx, fig in enumerate(key_content.get("figures", [])):
                fig_id = f"fig{idx}"
                if fig_id in self.id_to_filename:
                    filename = self.id_to_filename[fig_id]
                    fig["id"] = fig_id
                    fig["filename"] = filename
                    fig["path"] = os.path.join("output", "images", self.session_id, filename)
                else:
                    self.logger.warning(f"图片ID未找到真实图片，已忽略: {fig_id}")
            
        except Exception as e:
            self.logger.error(f"提取关键内容时出错: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return key_content
    
    def _identify_image_groups(self, images):
        """
        识别图片组（多张小图片可能组成一个大图）
        
        Args:
            images: 图片列表
            
        Returns:
            List: 图片组列表，每个组是一个图片列表
        """
        if not images:
            return []
            
        # 按页面分组
        images_by_page = {}
        for img in images:
            # 修改图片类型判断
            if img.get("type") not in ["file", "page_render"]:
                continue
                
            # 确保图片有路径信息
            if "path" not in img:
                # 尝试构建路径
                filename = img.get("filename")
                if filename:
                    img["path"] = f"images/{filename}"
                
            page = img.get("page", 0)
            if page not in images_by_page:
                images_by_page[page] = []
            images_by_page[page].append(img)
        
        # 图片组结果
        image_groups = []
        
        # 处理每一页的图片
        for page, page_images in images_by_page.items():
            # 如果页面只有一张图片，不需要分组
            if len(page_images) <= 1:
                for img in page_images:
                    image_groups.append([img])
                continue
                
            # 对当前页面的图片进行分组
            remaining_images = page_images.copy()
            
            while remaining_images:
                # 从剩余图片中取出一张
                current_img = remaining_images.pop(0)
                current_group = [current_img]
                
                # 查找与当前图片相关的其他图片
                i = 0
                while i < len(remaining_images):
                    other_img = remaining_images[i]
                    
                    # 检查两张图片是否相关
                    if self._are_images_related(current_img, other_img):
                        # 添加到当前组并从剩余列表中移除
                        current_group.append(other_img)
                        remaining_images.pop(i)
                    else:
                        i += 1
                
                # 将当前组添加到结果
                if current_group:
                    # 为组中的每张图片添加组标识
                    for img in current_group:
                        img["group_id"] = f"group_{page}_{len(image_groups)}"
                        img["is_group"] = len(current_group) > 1
                    
                    image_groups.append(current_group)
        
        # 确保每个图片组都有唯一的ID
        for i, group in enumerate(image_groups):
            group_id = f"fig_group_{i+1}"
            for img in group:
                img["group_id"] = group_id
        
        return image_groups
    
    def _are_images_related(self, img1, img2):
        """
        判断两张图片是否相关（可能属于同一组）
        
        Args:
            img1: 第一张图片
            img2: 第二张图片
            
        Returns:
            bool: 是否相关
        """
        # 如果页码不同，肯定不相关
        if img1.get("page") != img2.get("page"):
            return False
            
        # 提取边界框
        bbox1 = img1.get("bbox", [])
        bbox2 = img2.get("bbox", [])
        
        # 确保边界框有效
        if len(bbox1) < 4 or len(bbox2) < 4:
            return False
            
        # 计算两个边界框的中心点
        center1_x = (bbox1[0] + bbox1[2]) / 2
        center1_y = (bbox1[1] + bbox1[3]) / 2
        center2_x = (bbox2[0] + bbox2[2]) / 2
        center2_y = (bbox2[1] + bbox2[3]) / 2
        
        # 计算边界框的尺寸
        width1 = bbox1[2] - bbox1[0]
        height1 = bbox1[3] - bbox1[1]
        width2 = bbox2[2] - bbox2[0]
        height2 = bbox2[3] - bbox2[1]
        
        # 计算两个边界框中心点之间的距离
        distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
        
        # 计算最大尺寸
        max_dimension = max(width1, height1, width2, height2)
        
        # 如果距离小于最大尺寸的2倍，认为两张图片相关
        return distance < max_dimension * 2
    
    def _get_group_bbox(self, images):
        """
        获取图片组的边界框
        
        Args:
            images: 图片列表
            
        Returns:
            List: [x0, y0, x1, y1] 格式的边界框
        """
        if not images:
            return [0, 0, 0, 0]
            
        # 提取所有图片的边界框
        bboxes = []
        for img in images:
            bbox = img.get("bbox", [])
            if len(bbox) >= 4:
                bboxes.append(bbox)
        
        # 如果没有有效的边界框，返回默认值
        if not bboxes:
            return [0, 0, 0, 0]
            
        # 计算组的边界框（包含所有图片的最小边界框）
        x0 = min(bbox[0] for bbox in bboxes)
        y0 = min(bbox[1] for bbox in bboxes)
        x1 = max(bbox[2] for bbox in bboxes)
        y1 = max(bbox[3] for bbox in bboxes)
        
        return [x0, y0, x1, y1]
    
    def _extract_surrounding_text(self, img, page_texts):
        """
        提取图片周围的文本
        
        Args:
            img: 图片信息
            page_texts: 页面文本字典
            
        Returns:
            str: 图片周围的文本
        """
        # 获取图片所在页码
        page_num = img.get("page", 0)
        
        # 如果页面文本字典中没有该页的文本，返回空字符串
        if page_num not in page_texts:
            return ""
            
        page_text = page_texts[page_num]
        
        # 如果页面文本很短，直接返回整个页面的文本
        if len(page_text) < 1000:
            return page_text
            
        # 获取图片边界框
        bbox = img.get("bbox", [])
        if len(bbox) < 4:
            # 如果没有边界框信息，返回页面前1/3的文本
            text_length = len(page_text)
            return page_text[:text_length // 3]
            
        # 这里可以实现更复杂的逻辑来提取图片周围的文本
        # 例如，使用图片在页面中的位置来决定提取哪部分文本
        # 当前，我们简单地返回页面的前半部分文本
        text_length = len(page_text)
        return page_text[:text_length // 2]
    
    def _calculate_text_similarity(self, text1, text2):
        """
        计算两段文本的相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            float: 相似度得分
        """
        # 简单的文本相似度计算
        # 在实际应用中，可以使用更复杂的算法，如余弦相似度、Jaccard相似度等
        
        # 将文本转换为小写并分词
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # 计算共同词的数量
        common_words = words1.intersection(words2)
        
        # 如果两段文本都为空，返回0
        if not words1 or not words2:
            return 0
            
        # 计算Jaccard相似度
        return len(common_words) / len(words1.union(words2))
    
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
            # 构建提示
            language_prompt = "请用中文回答" if self.language == "zh" else "Please answer in English"
            
            # 这里是同伴可以修改的第二个prompt位置
            # 提示：修改此处可以改进幻灯片的内容丰富度和结构
            prompt = ChatPromptTemplate.from_template("""
            你是一个专业的学术演示设计专家。根据下面提供的论文信息，规划一个Beamer学术演示幻灯片。{language_prompt}。
            
            论文信息：
            - 标题: {title}
            - 作者: {authors}
            - 摘要: {abstract}
            
            论文关键内容：
            - 主要贡献: {contributions}
            - 方法论: {methodology}
            - 主要结果: {results}
            - 结论: {conclusions}
            
            论文图表信息：
            {figures_info}
            
            首先请你弄清楚这篇文章解决什么问题，如何评价指标，是怎样的实现。这三点事最重要的部分，也是不考虑篇幅、最需要在幻灯片中向观众详细介绍清楚的部分。

            然后，请设计一个20张左右幻灯片的演示文稿，包括以下内容（重要的部分可以多安排几张幻灯片，讲清楚最重要）：
            1. 标题页和目录页（目录页需要包含后文所有幻灯片的标题，若目录一页放不下可以安排多页）
            2. 简介/动机（介绍清楚这篇文章解决什么问题，至少用一组输入输出的案例来解释，可以安排1～2张幻灯片）
            3. 研究背景与挑战（简单介绍）
            4. 相关工作（简单介绍）
            5. 研究方法（介绍这篇论文的核心思路、做法，这是最重要的一部分，可以安排3～5张幻灯片）
            6. 实验设置（介绍评价指标、如何评价，可以安排1～3张幻灯片）
            7. 结果与分析（简单介绍）
            8. 结论与未来工作（简单介绍）
            
            对于每张幻灯片，请提供：
            1. 幻灯片标题（简洁明了）
            2. 幻灯片内容要点（内容要具体而非泛泛而谈）
            3. 是否包含图表（如果包含，需要给出图表的ID和描述）
            
            
            重要图像使用指南：
            1. 只选择论文中的重要图表和图像，最多使用5-7个关键图表/图像
            2. 优先选择显示实验结果、方法框架、关键数据的图表
            3. 确保每个图表都与幻灯片内容高度相关
            4. 在figure_reference中精确指定图片ID和描述
            5. 只在图片能增强内容理解的幻灯片上添加图片
            6. 对于方法和结果部分，确保图表与文字内容紧密结合
            
            请以JSON格式返回，格式如下：
            ```json
            [
              {{
                "slide_number": 1,
                "title": "幻灯片标题",
                "content": ["要点1", "要点2", ...],
                "includes_figure": false,
                "figure_reference": null
              }},
              {{
                "slide_number": 2,
                "title": "幻灯片标题",
                "content": ["要点1", "要点2", ...],
                "includes_figure": true,
                "figure_reference": {{
                  "id": "图片ID",
                  "description": "图表描述",
                  "relevance": "该图表与幻灯片内容的相关性说明"
                }}
              }}
            ]
            ```
            
            仅返回JSON数组，不要有任何其他文字。确保JSON结构严格正确。
            """)
            
            # 调用LLM
            chain = prompt | self.llm
            response = chain.invoke({
                "title": paper_info.get("title", ""),
                "authors": ", ".join(paper_info.get("authors", [])),
                "abstract": paper_info.get("abstract", ""),
                "contributions": json.dumps(key_content.get("main_contributions", []), ensure_ascii=False),
                "methodology": key_content.get("methodology", ""),
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
            
            # 改进图表引用逻辑，幻灯片只允许引用真实图片
            figures = key_content.get("figures", [])
            figures_by_id = {fig["id"]: fig for fig in figures if "id" in fig}
            for slide in slides_plan:
                if slide.get("includes_figure") and slide.get("figure_reference"):
                    fig_ref = slide.get("figure_reference")
                    if fig_ref and "id" in fig_ref:
                        fig_id = fig_ref.get("id")
                        if fig_id in figures_by_id:
                            matched_fig = figures_by_id[fig_id]
                            filename = matched_fig.get("filename", "")
                            if filename:
                                fig_ref["filename"] = filename
                                fig_ref["path"] = os.path.join("output", "images", self.session_id, filename)
                            else:
                                self.logger.warning(f"幻灯片图片ID未找到真实图片: {fig_id}")
                        else:
                            self.logger.warning(f"幻灯片图片ID未找到真实图片: {fig_id}")
                    else:
                        self.logger.warning(f"幻灯片图片figure_reference缺少id字段: {fig_ref}")
        
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
            output_file = os.path.join(self.output_dir, "presentation_plan.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(presentation_plan, f, ensure_ascii=False, indent=2)
        
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
        system_message = f"""
        你是一个专业的学术演示设计专家。你的任务是帮助用户优化他们的学术演示幻灯片计划。
        
        当前论文信息：
        - 标题: {self.paper_info.get('title', '未知标题')}
        - 作者: {', '.join(self.paper_info.get('authors', ['未知作者']))}
        
        你应该：
        1. 帮助用户理解当前的演示计划
        2. 根据用户的反馈修改幻灯片内容、结构或顺序
        3. 确保演示内容专业、清晰且有吸引力
        4. 使用{language_prompt}与用户交流
        
        请记住，最终目标是创建一个能够清晰表达论文内容的学术演示。
        """
        
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
        sections = self._identify_presentation_sections()
        
        summary = f"当前演示计划包含{slides_count}张幻灯片，主要包括以下部分：\n"
        
        for section, slides in sections.items():
            summary += f"- {section}：{len(slides)}张幻灯片"
            if slides:
                summary += f'（例如："{slides[0].get("title", "无标题")}"）'
            summary += "\n"
            
        return summary
    
    def _identify_presentation_sections(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        识别演示文稿的主要部分
        
        Returns:
            Dict: 各部分的幻灯片列表
        """
        sections = {
            "标题与介绍": [],
            "研究背景": [],
            "方法": [],
            "结果": [],
            "结论": [],
            "其他": []
        }
        
        keywords = {
            "标题与介绍": ["title", "介绍", "introduction", "概述", "overview", "目录", "outline"],
            "研究背景": ["背景", "background", "相关工作", "related work", "动机", "motivation", "挑战", "challenge"],
            "方法": ["方法", "methodology", "method", "approach", "模型", "model", "框架", "framework", "算法", "algorithm"],
            "结果": ["结果", "result", "实验", "experiment", "评估", "evaluation", "性能", "performance", "比较", "comparison"],
            "结论": ["结论", "conclusion", "总结", "summary", "未来工作", "future work"]
        }
        
        for slide in self.slides_plan:
            title = slide.get("title", "").lower()
            classified = False
            
            for section, keys in keywords.items():
                if any(key.lower() in title for key in keys):
                    sections[section].append(slide)
                    classified = True
                    break
            
            if not classified:
                sections["其他"].append(slide)
                
        return sections
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        获取对话历史
        
        Returns:
            List: 对话历史记录
        """
        # 转换为简单的字典格式，便于存储和显示
        history = []
        for message in self.conversation_history:
            if isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                role = "unknown"
                
            history.append({
                "role": role,
                "content": message.content
            })
            
        return history
    
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

# 更新便捷函数以支持交互
def generate_presentation_plan(raw_content_path, output_dir="output", model_name="gpt-4o", api_key=None, language="zh", user_feedback=None):
    """
    从原始内容生成演示计划（便捷函数）
    
    Args:
        raw_content_path: 原始内容JSON文件路径
        output_dir: 输出目录
        model_name: 要使用的语言模型名称
        api_key: OpenAI API密钥
        language: 输出语言，zh为中文，en为英文
        user_feedback: 用户的初始反馈（可选）
        
    Returns:
        tuple: (演示计划, 保存的文件路径, 规划器实例)
    """
    planner = PresentationPlanner(
        raw_content_path=raw_content_path,
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