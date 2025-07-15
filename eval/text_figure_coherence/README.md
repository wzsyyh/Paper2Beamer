# Metric 3.1: Text-Figure Coherence

This module implements the "Text-Figure Coherence" metric, which is part of the "Human-Calibrated Quality Assessment" tier of the benchmark.

## Objective

The goal is to evaluate how well the text on a slide explains, contextualizes, and guides the audience's attention to the key message of the accompanying figure. A high score indicates a strong synergy between the visual and textual elements.

## Technical Implementation

The evaluation process involves these steps:

1.  **LaTeX to PDF Compilation**: The input `.tex` file is first compiled into a PDF document. This requires a working LaTeX distribution (like TeX Live) to be installed on the system.

2.  **Identify Frames with Figures**: The script parses the `.tex` file to identify which frames (slides) contain `\includegraphics` commands.

3.  **PDF to Image Rendering**: For each identified frame, the corresponding page in the compiled PDF is rendered into a high-resolution image (e.g., PNG). The `PyMuPDF` library is used for this task.

4.  **VLM-based Evaluation**: Each rendered slide image is sent to a Vision Language Model (VLM) like GPT-4V.
    *   **Prompt**: The VLM is prompted with a specific question: `"On a scale of 1-5, how well does the text on this slide explain the key message of the figure? 1: Unrelated. 3: Descriptive but not insightful. 5: Masterfully guides attention to the figure's core takeaway."`
    *   **Scoring**: The VLM returns a score from 1 to 5 for each slide.

5.  **Final Score**: The final "Text-Figure Coherence" score is the average of the scores for all slides that contain figures.

## Usage

The `run_evaluation.py` script will orchestrate this process. It will take a path to a `.tex` file as input and output the average coherence score.

```bash
python eval/text_figure_coherence/run_evaluation.py --tex-path /path/to/presentation.tex
