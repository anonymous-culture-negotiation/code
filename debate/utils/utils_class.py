import json
import logging
import os
import pdb
from typing import Dict, List, Tuple
from venv import logger
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
from torch import Tensor
from debate.utils.utils_fn import get_similarity_score, get_yaml_config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LlmClient:
    def __init__(self, api_key: str, base_url: str, model_name: str, params: dict = {'temperature': 0.6}) -> None:
        self.client: OpenAI = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Connected to OpenAI API at {base_url}: {model_name}")
        self.model_name = model_name
        self.temperature = params['temperature']
    
    @retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=5, max=20))
    def generate(self, messages: list[dict], max_tokens:int|None=None, temperature:float|None=None, response_as_json: bool=False) -> str:
    
        try:
            if response_as_json:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages, # type: ignore
                    temperature=temperature if temperature else self.temperature,
                    max_tokens=max_tokens,
                )
                if response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    raise Exception("Empty response")
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages, # type: ignore
                    temperature=temperature if temperature else self.temperature,
                    max_tokens=max_tokens,
                )
                if response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    raise Exception("Empty response")
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")
    
class Guideline:
    """Guideline class, containing guideline content, embedding, weights, and utility calculated in stages"""
    def __init__(self, content: str, embedding: Tensor, reason: str, desc: str) -> None:
        self.content: str = content
        self.embedding: Tensor = embedding
        self.reason: str = reason
        self.desc: str = desc
        self.weight: float = 0.0
        self.utility: Utility = Utility()   
    def update_weight(self, weight: float) -> None:
        """Update guideline weight, keeping 2 decimal places"""
        self.weight = round(weight, 2)
    
    def __str__(self) -> str:
        """Return string representation of the guideline, including content, reason and description"""
        return f"{self.content}: reason: {self.reason}. detail: {self.desc}"
    

class Utility:
    """Utility class, containing utility components and total utility"""
    def __init__(self) -> None:
        self.consistency: float = 0.0
        self.novelty: float = 0.0
        self.acceptance: float = 0.0
        self.total: float = 0.0
    def update_utility(self, consistency: float, acceptance: float, novelty: float, total: float):
        """Update utility components and total utility"""
        self.consistency: float = round(consistency, 3)
        self.acceptance: float = round(acceptance, 3)
        self.novelty: float = round(novelty, 3)
        self.total: float = round(total, 3)

class DebateState:
    """Debate state class, storing the state during the debate process"""
    def __init__(self) -> None:
        self.guideline_pool: List[Guideline] = []  # Guideline pool
        self.initial_guidelines = {
            "guidelines": [],
            "embeddings": None
        }
        self.previous_guideline_weight = {}

    def add_guideline(self, guideline: Guideline):
        """Add new guideline to the guideline pool"""
        self.guideline_pool.append(guideline)
    
    def get_guideline_weights(self) -> dict:
        """Get weight distribution of all guidelines"""
        return {g.content: g.weight for g in self.guideline_pool}

    def get_previous_guideline_weights(self) -> dict:
        """Get guideline weight distribution from the previous round"""
        if len(self.guideline_pool) > 1:
            previous_guideline_weight = self.previous_guideline_weight
            self.previous_guideline_weight = self.get_guideline_weights()
            # Only return the weight distribution from the previous round
            return previous_guideline_weight
        else:
            self.previous_guideline_weight = self.get_guideline_weights()
            return {}
    
    def get_guidelines(self) -> dict:
        """Get all guidelines"""
        return {g.content: str(g) for g in self.guideline_pool}
    def get_guideline_weights_desc(self) -> str:
        """Get description of weight distribution for all guidelines"""
        desc = "\n".join([f"guideline: {g.content}, weight :{g.weight}, reason: {g.reason}, description: {g.desc}" for g in self.guideline_pool])
        return desc
    
    def get_guideline_embeddings(self) -> List[Tensor]:
        """Get embeddings of all guidelines"""
        return [g.embedding for g in self.guideline_pool]
    
    def set_init_guideline(self, guidelines: List[Guideline], embeddings: Tensor, initial_response:str):
        """Update initial guidelines"""
        self.initial_guideline = {
            "guidelines": guidelines,
            "embeddings": embeddings,
            "response": initial_response
        }
    def get_init_guideline_desc(self) -> str:
        if not self.initial_guideline['response']:
            raise ValueError("Initial guidelines do not exist")
        # Return description of initial guidelines
        return self.initial_guideline['response']
    
    def get_init_embedding(self) -> Tensor:
        """Get embedding of initial guidelines"""
        return self.initial_guideline['embeddings']

    def update_guideline_weights(self, weights: Dict[str, float]):
        """Update guideline weights"""
        for guideline in self.guideline_pool:
            if guideline.content in weights:
                guideline.update_weight(weights[guideline.content])
    
class DebateScorer:
    """Debate utility scorer, calculating utility across three dimensions: consistency, acceptance, and novelty"""
    def __init__(self, alpha: float = 0.5, beta: float = 0.3, gamma: float = 0.2):
        """
        Initialize scorer
        Args:
            alpha: Self-consistency weight
            beta: Cross-cultural compatibility weight
            gamma: Governance innovation weight
        """
        # assert abs(alpha + beta + gamma - 1.0) < 1e-6, "Sum of weights must equal 1"
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def calculate_utility(self, 
            current_embedding: Tensor, 
            current_guideline: str,
            similarity_matrix: Dict[Tuple[str, str], float],
            opponent_weights: Dict[str, float],
            history_embeddings: List[Tensor]|None=None,
            initial_embedding: Tensor|None=None,
            ) -> tuple[float, float, float, float]:
        """Calculate total utility"""
        self_consistency = self.calculate_self_consistency(current_embedding, initial_embedding)
        cross_acceptance = self.calculate_cross_acceptance(current_guideline, similarity_matrix, opponent_weights)
        information_gain = self.calculate_information_gain(current_embedding, history_embeddings)
        utility = (self.alpha * self_consistency +
                  self.beta * cross_acceptance +
                  self.gamma * information_gain)
        return utility, self_consistency, cross_acceptance, information_gain
    
    def calculate_self_consistency(self, 
                         current_embedding: Tensor, 
                         initial_embedding: Tensor|None=None) -> float:
        """
        Calculate self-consistency: similarity between current guideline and initial guideline
        Consist(g_i^t) = sim(E(g_i^t), E(g_i^0))
        """
        if initial_embedding is None:
            return 0.0 # First guideline has no initial guideline
        return get_similarity_score(current_embedding, initial_embedding)
    
    def calculate_cross_acceptance(self, 
                                current_guideline:str,
                                similarity_matrix: Dict[Tuple[str, str], float],
                                opponent_weights: Dict[str, float]) -> float:
        """
        Calculate cross-cultural compatibility only
        Args:
            guideline_embedding: Guideline embedding
            opponent_embeddings: Opponent guideline embeddings
            opponent_weights: Opponent guideline weights
        Returns:
            float: Cross-cultural compatibility
        """
        if not similarity_matrix or not opponent_weights:
            return 0.0
            
        # Get matrix elements containing current_guideline
        similarities = [similarity_matrix[(current_guideline, guideline)] for guideline in opponent_weights.keys()]
        # Normalize weights
        weights = np.array(list(opponent_weights.values()))
        weights = weights / np.sum(weights)
        
        # Calculate weighted average similarity
        acceptance = np.dot(similarities, weights)
        return acceptance
    
    def calculate_information_gain(self, current_embedding: Tensor,
                                 history_embeddings: List[Tensor]|None=None) -> float:
        """Calculate novelty: 1 minus maximum similarity with historical guidelines"""
        if history_embeddings is None or len(history_embeddings) == 0:
            return 1.0 # First guideline has no historical guidelines
        similarities = [get_similarity_score(current_embedding, hist_embedding) 
                       for hist_embedding in history_embeddings]
        return 1.0 - max(similarities)



# test client
if __name__ == "__main__":
    params = get_yaml_config("debate/config/params.yaml")
    client = LlmClient(params['llm_api']["api_key"], params['llm_api']["base_url"], params["model"]["Qwen2.5-7B-Instruct"]["name"])
    messages = []
    system_prompt = "The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly."
    prompt = "Should we ban smoking in public places?"
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    response = client.generate(messages)
    print(response)