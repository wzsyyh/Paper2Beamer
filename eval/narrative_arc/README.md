# Metric 2.1: Narrative Arc Integrity

This module evaluates the narrative structure of a generated LaTeX Beamer presentation. It aims to quantify how well the presentation follows the classic "Motivation -> Method -> Result -> Conclusion" academic storytelling arc.

## How it Works

1.  **Frame Extraction**: The `run_evaluation.py` script first parses the input `.tex` file and extracts the content of each `\begin{frame}...\end{frame}` environment.

2.  **LLM-based Classification**: For each frame, the script sends its content (title and body) to an LLM (e.g., GPT-4o) with a specific prompt. The LLM is asked to classify the frame's content into one of five categories:
    *   `Motivation`: Introduces the problem, background, or goals.
    *   `Method`: Describes the methodology, algorithms, or experimental setup.
    *   `Result`: Presents findings, data, or experimental outcomes.
    *   `Conclusion`: Summarizes the work, discusses implications, and future work.
    *   `Other`: Title slides, agendas, references, etc.

3.  **Sequence Scoring**: After classifying all frames, the script obtains a sequence of labels (e.g., `['Other', 'Motivation', 'Method', 'Method', 'Result', 'Conclusion']`).

4.  **Longest Valid Subsequence**: The script then calculates the length of the longest subsequence within the label list that follows the correct narrative order (`Motivation` -> `Method` -> `Result` -> `Conclusion`). A state can be repeated (e.g., `Method` -> `Method`) or advanced (e.g., `Method` -> `Result`), but not skipped (e.g., `Motivation` -> `Result`) or reversed (e.g., `Result` -> `Method`). 'Other' frames are ignored and do not break a valid sequence.

5.  **Final Score**: The final score is the ratio of the length of this longest valid subsequence to the total number of "meaningful" frames (i.e., all frames excluding 'Other'). A score of 1.0 indicates a perfect narrative structure.

## Usage

```bash
python eval/narrative_arc/run_evaluation.py /path/to/your/presentation.tex --output_file results.json
```

This will process the specified `.tex` file and save a JSON object containing the final score, the list of labels, and other metadata to `results.json`.
