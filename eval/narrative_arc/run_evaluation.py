#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metric 2.1: Narrative Arc Integrity Evaluation
"""

import argparse
import json
import os
import sys
from typing import List, Dict

# Add project root to sys.path to allow importing patch_openai
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from patch_openai import patch_langchain_openai
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

from latex_utils import extract_frames

# Load .env and apply patches
if os.path.exists(os.path.join(project_root, ".env")):
    load_dotenv(os.path.join(project_root, ".env"))
elif os.path.exists(os.path.join(project_root, "env.local")):
    load_dotenv(os.path.join(project_root, "env.local"))
patch_langchain_openai()

# --- Constants ---
NARRATIVE_LABELS = ["Motivation", "Method", "Result", "Conclusion", "Other"]
LABEL_MAP = {
    "Motivation": 0,
    "Method": 1,
    "Result": 2,
    "Conclusion": 3,
    "Other": -1  # 'Other' is ignored in LIS calculation
}

# --- Core Logic ---

def get_longest_narrative_subsequence(labels: List[str]) -> int:
    """
    Calculates the length of the longest valid narrative subsequence.
    This is a variation of the Longest Increasing Subsequence (LIS) problem.
    A valid narrative follows the order: Motivation -> Method -> Result -> Conclusion.
    
    Args:
        labels: A list of classified labels for each slide.
        
    Returns:
        The length of the longest subsequence.
    """
    if not labels:
        return 0

    # Map string labels to integers for LIS algorithm
    # We filter out 'Other' as it does not contribute to the narrative arc.
    nums = [LABEL_MAP[label] for label in labels if LABEL_MAP[label] != -1]
    
    if not nums:
        return 0

    # Standard LIS algorithm (patience sorting)
    tails = []
    for num in nums:
        if not tails or num >= tails[-1]:
            tails.append(num)
        else:
            l, r = 0, len(tails) - 1
            while l < r:
                m = (l + r) // 2
                if tails[m] < num:
                    l = m + 1
                else:
                    r = m
            tails[l] = num
            
    return len(tails)

class SlideCategory(BaseModel):
    """The category of the slide content."""
    category: str = Field(
        description="The single most appropriate category for the slide.",
        enum=NARRATIVE_LABELS
    )

class LLMClassifier:
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0):
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.structured_llm = self.llm.with_structured_output(SlideCategory)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert academic reviewer. Your task is to classify the content of a presentation slide into one of the following five categories based on its primary role in a scientific narrative: [Motivation, Method, Result, Conclusion, Other].\n\n"
             "Use your best judgment based on these guidelines:\n"
             "- **Motivation**: Content that introduces the problem, background, or research question. (e.g., 'Why this work is important.')\n"
             "- **Method**: Content that describes the methodology, experimental setup, or proposed algorithm. (e.g., 'How we did it.')\n"
             "- **Result**: Content that presents the findings, data, figures, and outcomes of the experiments. (e.g., 'What we found.')\n"
             "- **Conclusion**: Content that summarizes the work, discusses implications, limitations, or future directions. (e.g., 'What it means.')\n"
             "- **Other**: Use for slides that do not clearly fit a single category above, such as title pages, outlines, acknowledgements, or highly mixed content.\n\n"
             "Analyze the provided slide content and determine its single most fitting category."
            ),
            ("human", "Please classify the following slide content:\n\n---\n\n{slide_content}")
        ])
        self.chain = self.prompt | self.structured_llm

    def classify_frame(self, frame_content: str) -> str:
        try:
            response = self.chain.invoke({"slide_content": frame_content})
            return response.category
        except Exception as e:
            logger.error(f"An error occurred during LLM classification: {e}")
            return "Other"

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Evaluate the narrative arc integrity of a Beamer presentation.")
    parser.add_argument("--tex_file", type=str, required=True, help="Path to the generated .tex file.")
    parser.add_argument("--mock", action="store_true", help="Use mock classification instead of calling LLM API.")
    args = parser.parse_args()

    if not os.path.exists(args.tex_file):
        print(json.dumps({"error": f"File not found: {args.tex_file}"}))
        return

    with open(args.tex_file, 'r', encoding='utf-8') as f:
        tex_content = f.read()

    frames = extract_frames(tex_content)
    if not frames:
        print(json.dumps({"score": 0, "total_frames": 0, "longest_subsequence_len": 0, "sequence": []}))
        return

    classified_labels = []
    if args.mock:
        # Predefined sequence for repeatable testing
        mock_sequence = ["Motivation", "Motivation", "Method", "Result", "Method", "Conclusion", "Other", "Result", "Conclusion"]
        classified_labels = [mock_sequence[i % len(mock_sequence)] for i in range(len(frames))]
    else:
        # Real LLM classification
        classifier = LLMClassifier()
        for frame in frames:
            # Combine title and text for a more complete context
            content_to_classify = f"Title: {frame.get('title', '')}\n\nBody: {frame.get('text', '')}"
            label = classifier.classify_frame(content_to_classify)
            classified_labels.append(label)


    longest_subsequence_len = get_longest_narrative_subsequence(classified_labels)
    core_frames_count = len([label for label in classified_labels if label != "Other"])
    score = longest_subsequence_len / core_frames_count if core_frames_count > 0 else 1.0 # If no core frames, score is 1 (no violations)

    result = {
        "score": round(score, 4),
        "total_frames": len(frames),
        "longest_subsequence_len": longest_subsequence_len,
        "sequence": classified_labels
    }

    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()
