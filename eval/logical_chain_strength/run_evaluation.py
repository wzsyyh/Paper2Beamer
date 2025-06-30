import argparse
import json
import numpy as np
from latex_parser import get_frames_from_file
from llm_evaluator import LLMTransitionEvaluator

def run_evaluation(tex_file_path: str, model_name: str = "gpt-4o"):
    """
    Runs the full logical chain strength evaluation for a given .tex file.

    Args:
        tex_file_path: The path to the .tex file to be evaluated.
        model_name: The name of the language model to use for evaluation.
    """
    print(f"--- Starting Logical Chain Strength Evaluation for {tex_file_path} ---")

    # 1. Parse LaTeX file to extract frames
    print("\nStep 1: Parsing LaTeX file...")
    frames = get_frames_from_file(tex_file_path)
    if not frames or len(frames) < 2:
        print("Not enough frames (< 2) to evaluate transitions. Aborting.")
        return

    print(f"Successfully extracted {len(frames)} frames.")

    # 2. Evaluate transitions between adjacent frames
    print("\nStep 2: Evaluating transitions between adjacent frames using LLM...")
    evaluator = LLMTransitionEvaluator(model_name=model_name)
    transition_scores = []
    
    for i in range(len(frames) - 1):
        slide_n = frames[i]
        slide_n1 = frames[i+1]
        
        print(f"  - Evaluating transition from Frame {i+1} ('{slide_n['title']}') to Frame {i+2} ('{slide_n1['title']}')")
        
        result = evaluator.evaluate_transition(
            slide_n['cleaned_content'],
            slide_n1['cleaned_content']
        )
        transition_scores.append(result)
        print(f"    -> Score: {result['score']}, Reasoning: {result['reasoning']}")

    # 3. Calculate final scores
    print("\nStep 3: Calculating final scores...")
    scores = [s['score'] for s in transition_scores]
    
    if not scores:
        average_score = 0.0
        coherence_rate = 0.0
    else:
        average_score = np.mean(scores)
        # Coherence rate is the percentage of scores >= 3
        coherent_transitions = sum(1 for s in scores if s >= 3)
        coherence_rate = coherent_transitions / len(scores)

    print("\n--- Evaluation Complete ---")
    print(f"Average Transition Score: {average_score:.4f}")
    print(f"Coherence Rate (scores >= 3): {coherence_rate:.4f}")

    # Prepare results dictionary
    results = {
        "file_path": tex_file_path,
        "total_frames": len(frames),
        "total_transitions": len(transition_scores),
        "average_score": average_score,
        "coherence_rate": coherence_rate,
        "transition_details": [
            {
                "from_frame": i + 1,
                "to_frame": i + 2,
                "from_title": frames[i]['title'],
                "to_title": frames[i+1]['title'],
                "score": r['score'],
                "reasoning": r['reasoning']
            } for i, r in enumerate(transition_scores)
        ]
    }
    
    print("\nDetailed Results (JSON format):")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    return results

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the logical chain strength of a Beamer .tex file."
    )
    parser.add_argument(
        "tex_file",
        help="Path to the input .tex file."
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="The language model to use for evaluation (e.g., 'gpt-4o')."
    )
    args = parser.parse_args()
    
    run_evaluation(args.tex_file, args.model)

if __name__ == "__main__":
    main()
