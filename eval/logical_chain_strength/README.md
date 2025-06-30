# Metric 2.2: Logical Chain Strength

This module implements the "Logical Chain Strength" metric as defined in the Paper2Beamer Benchmark technical specification.

## Objective

The goal is to evaluate the slide-to-slide transition quality, assessing whether the presentation flows logically and coherently.

## Technical Implementation

1.  **LaTeX Parsing (`latex_parser.py`)**: Extracts the title and core text content from each `frame` in the input `.tex` file. This is similar to Metric 2.1.

2.  **Content Pairing**: The script creates pairs of adjacent frames (Frame N, Frame N+1) for evaluation.

3.  **LLM Evaluation (`llm_evaluator.py`)**: For each pair of frames, it uses a Large Language Model (LLM) to score the logical transition.
    *   **Prompt**: The LLM is asked to rate the transition on a scale of 0 to 5, where 0 means "completely illogical" and 5 means "a masterful and clear transition".
    *   **Output**: The LLM returns an integer score for each pair.

4.  **Scoring (`run_evaluation.py`)**: Two final scores are calculated from the list of transition scores:
    *   **Average Score**: The arithmetic mean of all transition scores. This gives an overall sense of the presentation's flow.
    *   **Coherence Rate**: The percentage of transitions that scored 3 or higher. This measures the proportion of "acceptably logical" transitions, as per the benchmark specification.

## Usage

The `run_evaluation.py` script orchestrates the entire process. It takes a path to a `.tex` file as input and outputs the final scores.
