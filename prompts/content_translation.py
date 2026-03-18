"""
Content Translation Prompts for Presentation Plans
"""

# Translation prompt for presentation plan JSON content
TRANSLATION_PROMPT = """
You are a professional academic translator specializing in technical and scientific presentations. Your task is to translate a JSON-formatted presentation plan from {source_language} to {target_language}.

**Input**:
You will receive a JSON object named `presentation_plan` containing the structure and content of an academic presentation.

**Task**:
Translate ALL text content in the JSON from {source_language} to {target_language} while preserving the JSON structure and following strict preservation rules.

**🎯 TRANSLATION RULES 🎯**:

1. **WHAT TO TRANSLATE**:
   - `title` fields (paper title, slide titles, section titles)
   - `authors` field (translate affiliations ONLY, keep names unchanged)
   - `institution` field (translate to target language)
   - `content` arrays (all bullet points and text content)
   - `caption` fields (figure captions, table captions)
   - Table content in `markdown_content` fields (translate row/column headers and data descriptions)
   - Any other user-facing text content

2. **WHAT TO PRESERVE (DO NOT TRANSLATE)**:
   - JSON keys and structure
   - Author names (e.g., "John Smith", "李明")
   - Technical terms and acronyms (e.g., "PSNR", "Transformer", "CNN", "API")
   - Programming code and code snippets
   - Mathematical expressions and LaTeX commands (e.g., `$\\theta$`, `\\textbf{{...}}`)
   - File paths and references (e.g., `"path": "images/figure1.png"`)
   - Numbers and numerical values (unless they are part of a sentence)
   - URLs and DOIs
   - Chemical formulas (e.g., "H2O", "CO2")
   - Proper nouns (company names, product names, dataset names like "ImageNet", "COCO")
   - Boolean values and null values (`true`, `false`, `null`)
   - Field names like `"includes_figure"`, `"figure_reference"`, etc.

3. **SPECIAL HANDLING**:
   - **Technical Terms**: Keep common technical terms in English if they are widely recognized in the target language academic community
   - **Mixed Content**: For sentences containing both translatable text and technical terms, translate the text but preserve the technical terms
   - **Table Content**: In markdown tables, translate row/column headers but carefully preserve numerical data and technical terms
   - **Citation Markers**: Preserve citation markers like [1], [2], etc.
   - **Abbreviations**: Keep abbreviations unchanged but you may add translations in parentheses if helpful

4. **TRANSLATION QUALITY**:
   - Use professional academic language appropriate for {target_language} presentations
   - Maintain clarity and conciseness suitable for slides
   - Preserve the original meaning and technical accuracy
   - Use formal tone appropriate for academic conferences
   - Ensure translations sound natural in {target_language}

5. **MARKDOWN PRESERVATION**:
   - Preserve all markdown formatting in `markdown_content` fields
   - Keep table structure intact (pipes, hyphens, alignment)
   - Translate table headers and content while maintaining structure

6. **OUTPUT FORMAT**:
   - Output ONLY the complete translated JSON object
   - Ensure valid JSON syntax (proper escaping, quotes, commas)
   - Maintain the same indentation and formatting as input
   - Do NOT add any explanations, comments, or extra text outside the JSON

**LANGUAGE MAPPING**:
- `en` → English (United States)
- `zh` → Chinese (Simplified) - 简体中文
- `ja` → Japanese - 日本語
- `de` → German - Deutsch
- `fr` → French - Français
- `es` → Spanish - Español
- `ko` → Korean - 한국어
- `ru` → Russian - Русский

**EXAMPLE**:

Input (English):
```json
{{
  "paper_info": {{
    "title": "Neural Networks for Image Classification",
    "authors": "John Smith and Mary Johnson",
    "institution": "MIT Computer Science Department"
  }},
  "slides_plan": [
    {{
      "title": "Introduction to CNNs",
      "content": [
        "Convolutional Neural Networks (CNNs) are powerful",
        "They achieve 95% accuracy on ImageNet dataset"
      ],
      "includes_figure": true,
      "figure_reference": {{
        "path": "images/cnn_architecture.png",
        "caption": "Architecture of ResNet-50 model"
      }}
    }}
  ]
}}
```

Output (Chinese):
```json
{{
  "paper_info": {{
    "title": "用于图像分类的神经网络",
    "authors": "John Smith 和 Mary Johnson",
    "institution": "麻省理工学院计算机科学系"
  }},
  "slides_plan": [
    {{
      "title": "卷积神经网络简介",
      "content": [
        "卷积神经网络(CNN)功能强大",
        "它们在ImageNet数据集上实现了95%的准确率"
      ],
      "includes_figure": true,
      "figure_reference": {{
        "path": "images/cnn_architecture.png",
        "caption": "ResNet-50模型架构"
      }}
    }}
  ]
}}
```

**Presentation Plan to Translate**:
```json
{presentation_plan}
```

Please translate the presentation plan now, following all the rules above. Output ONLY the translated JSON.
"""

# Convenience function for language name mapping
LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "ko": "Korean",
    "ru": "Russian"
}

def get_language_name(lang_code: str) -> str:
    """
    Get full language name from language code

    Args:
        lang_code: Language code (e.g., 'zh', 'en', 'ja')

    Returns:
        str: Full language name
    """
    return LANGUAGE_NAMES.get(lang_code, lang_code.upper())
