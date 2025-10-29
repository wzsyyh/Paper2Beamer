"""
Content Translator Module: Translate presentation plan JSON content to target language
"""
import os
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Load environment variables
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("env.local"):
    load_dotenv("env.local")

# Import translation prompts
from prompts.content_translation import TRANSLATION_PROMPT, get_language_name


class ContentTranslator:
    """
    Content Translator: Translate presentation plan content to target language
    """

    def __init__(
        self,
        source_language: str = "en",
        target_language: str = "zh",
        model_name: str = "gpt-4o",
        temperature: float = 0.3,
        api_key: Optional[str] = None
    ):
        """
        Initialize content translator

        Args:
            source_language: Source language code (e.g., 'en')
            target_language: Target language code (e.g., 'zh', 'ja', 'de')
            model_name: Language model name to use
            temperature: Randomness level (0.3 for more consistent translations)
            api_key: OpenAI API key
        """
        self.source_language = source_language
        self.target_language = target_language
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Initialize LLM
        self._init_model()

    def _init_model(self):
        """Initialize language model"""
        try:
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=self.api_key
            )
            self.logger.info(f"Initialized translation model: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize model: {str(e)}")
            raise

    def translate_presentation_plan(
        self,
        presentation_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translate presentation plan content to target language

        Args:
            presentation_plan: Original presentation plan dictionary

        Returns:
            Dict: Translated presentation plan
        """
        # Check if translation is needed
        if self.source_language == self.target_language:
            self.logger.info(f"Source and target languages are the same ({self.source_language}), skipping translation")
            return presentation_plan

        source_lang_name = get_language_name(self.source_language)
        target_lang_name = get_language_name(self.target_language)

        self.logger.info(f"Translating presentation plan from {source_lang_name} to {target_lang_name}...")

        try:
            # Build prompt
            prompt = ChatPromptTemplate.from_template(TRANSLATION_PROMPT)

            # Convert presentation plan to JSON string
            plan_json = json.dumps(presentation_plan, ensure_ascii=False, indent=2)

            # Call LLM for translation
            response = self.llm.invoke(prompt.format(
                source_language=source_lang_name,
                target_language=target_lang_name,
                presentation_plan=plan_json
            ))

            # Extract translated content
            translated_text = response.content

            # Clean the response (remove code blocks if present)
            translated_text = self._clean_json_response(translated_text)

            # Parse translated JSON
            try:
                translated_plan = json.loads(translated_text)
                self.logger.info("Translation completed successfully")
                return translated_plan
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse translated JSON: {str(e)}")
                self.logger.error(f"Raw response: {translated_text[:500]}...")

                # Try to extract JSON from response
                translated_plan = self._extract_json_from_response(translated_text)
                if translated_plan:
                    self.logger.info("Successfully extracted JSON from response")
                    return translated_plan
                else:
                    self.logger.error("Failed to extract valid JSON, returning original plan")
                    return presentation_plan

        except Exception as e:
            self.logger.error(f"Translation failed: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # Return original plan if translation fails
            return presentation_plan

    def _clean_json_response(self, text: str) -> str:
        """
        Clean JSON response by removing markdown code blocks

        Args:
            text: Raw response text

        Returns:
            str: Cleaned JSON string
        """
        # Remove markdown code blocks
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
        text = text.strip()

        return text

    def _extract_json_from_response(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Try to extract JSON object from response text

        Args:
            text: Response text that may contain JSON

        Returns:
            Optional[Dict]: Extracted JSON object or None
        """
        # Try to find JSON object in text
        # Look for { ... } pattern
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                json_str = json_match.group(0)
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        return None


def translate_presentation_plan_file(
    plan_path: str,
    output_dir: str,
    source_language: str = "en",
    target_language: str = "zh",
    model_name: str = "gpt-4o",
    api_key: Optional[str] = None
) -> Tuple[bool, str, Optional[str]]:
    """
    Translate presentation plan file (convenience function)

    Args:
        plan_path: Path to original presentation plan JSON file
        output_dir: Directory to save translated plan
        source_language: Source language code
        target_language: Target language code
        model_name: Language model name to use
        api_key: OpenAI API key

    Returns:
        Tuple[bool, str, Optional[str]]: (Success, Message, Translated file path)
    """
    logger = logging.getLogger(__name__)

    try:
        # Load original plan
        logger.info(f"Loading presentation plan from: {plan_path}")
        with open(plan_path, 'r', encoding='utf-8') as f:
            presentation_plan = json.load(f)

        # Skip translation if languages are the same
        if source_language == target_language:
            logger.info(f"Source and target languages are the same ({source_language}), skipping translation")
            return True, "Translation skipped (same language)", plan_path

        # Create translator
        translator = ContentTranslator(
            source_language=source_language,
            target_language=target_language,
            model_name=model_name,
            api_key=api_key
        )

        # Translate
        translated_plan = translator.translate_presentation_plan(presentation_plan)

        # Save translated plan
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"presentation_plan_translated_{target_language}.json"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translated_plan, f, ensure_ascii=False, indent=2)

        logger.info(f"Translated presentation plan saved to: {output_path}")

        return True, f"Translation completed successfully", output_path

    except Exception as e:
        logger.error(f"Failed to translate presentation plan: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Translation failed: {str(e)}", None
