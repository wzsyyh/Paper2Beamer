import os
import sys
from typing import List, Dict

# Add project root to sys.path to allow importing patch_openai
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables and apply patches
from dotenv import load_dotenv
from patch_openai import patch_langchain_openai

if os.path.exists(os.path.join(project_root, ".env")):
    load_dotenv(os.path.join(project_root, ".env"))
elif os.path.exists(os.path.join(project_root, "env.local")):
    load_dotenv(os.path.join(project_root, "env.local"))

patch_langchain_openai()

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, constr
from langchain_openai import ChatOpenAI

# Define the structured output model for the score
class TransitionScore(BaseModel):
    """A score representing the logical coherence of a transition between two slides."""
    score: int = Field(
        description="The integer score from 0 to 5 for the logical transition.",
        ge=0,
        le=5
    )
    reasoning: str = Field(
        description="A brief justification for the assigned score."
    )

class LLMTransitionEvaluator:
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0):
        """
        Initializes the LLM transition evaluator.
        """
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable not set.")
            
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.structured_llm = self.llm.with_structured_output(TransitionScore)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert in academic presentations. Your task is to evaluate the logical strength of the transition between two consecutive slides. "
             "Rate the transition on a scale from 0 to 5. Provide a score and a brief reasoning.\n"
             "Scoring guide:\n"
             "0: Completely illogical or unrelated. The second slide feels random.\n"
             "1: Very weak connection. The topic is vaguely related but the link is not made clear.\n"
             "2: Weak connection. The second slide follows the first, but the transition is abrupt or requires a large logical leap from the audience.\n"
             "3: Acceptable. A clear, logical step, but standard and not particularly insightful. This is the baseline for a coherent presentation.\n"
             "4: Strong. The second slide builds effectively on the first, for example, by providing evidence, elaborating on a point, or posing a direct consequence.\n"
             "5: Masterful. The transition is not only logical but also elegant and insightful, seamlessly guiding the audience's thought process to a deeper understanding."
            ),
            ("human", 
             "Evaluate the transition from Slide N to Slide N+1.\n\n"
             "--- Slide N Content ---\n{slide_n_content}\n\n"
             "--- Slide N+1 Content ---\n{slide_n1_content}"
            )
        ])
        
        self.chain = self.prompt | self.structured_llm

    def evaluate_transition(self, slide_n_content: str, slide_n1_content: str) -> Dict[str, any]:
        """
        Evaluates the logical transition between two slides.

        Args:
            slide_n_content: The cleaned text content of the first slide.
            slide_n1_content: The cleaned text content of the second slide.

        Returns:
            A dictionary containing the 'score' and 'reasoning'.
        """
        try:
            response = self.chain.invoke({
                "slide_n_content": slide_n_content,
                "slide_n1_content": slide_n1_content
            })
            return {"score": response.score, "reasoning": response.reasoning}
        except Exception as e:
            print(f"An error occurred during LLM evaluation: {e}")
            return {"score": 0, "reasoning": "Error during evaluation."} # Default to 0 on error
