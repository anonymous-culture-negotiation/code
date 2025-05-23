from __future__ import annotations
import logging
import pdb
import re
from typing import Dict, List, Literal, Optional, Tuple, Type, TypeVar

from debate.utils.utils_class import LlmClient, Guideline
from debate.prompts.br_prompts import (
    GUIDELINE_TEMPLATE,
    WEAKNESS_ANALYSIS_PROMPT,
    COVERAGE_GAPS_PROMPT,
    COUNTER_GUIDELINE_PROMPT,
    GAP_GUIDELINE_PROMPT,
    INNOVATION_GUIDELINE_PROMPT
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar('T', bound='BRGenerator')

class BRGenerator:
    """Best Response (BR) Generator base class"""
    
    def __init__(self, client: LlmClient, name: str) -> None:
        """
        Initialize BR generator
        
        Args:
            client: LLM client
            name: Generator name for logging
        """
        self.client = client
        self.name = name
    
    def generate(self, 
                language: Literal['zh', 'en'], 
                opponent_weights: Dict[str, float],
                get_embedding_fn,
                parse_guidelines_fn) -> List[Guideline]:
        """
        Generate best response guidelines
        
        Args:
            language: Language to use
            opponent_weights: Opponent's guideline weight distribution
            get_embedding_fn: Function to get embeddings
            parse_guidelines_fn: Function to parse guidelines
            
        Returns:
            List of generated guidelines
        """
        # The base class provides a default implementation, subclasses should override this method
        logger.warning(f"{self.name}: Using default BR generation method")
        return []
    

class GuidedBRGenerator(BRGenerator):
    """BR generator based on guided generation method"""
    
    def generate(self, 
                language: Literal['zh', 'en'], 
                opponent_weights: Dict[str, float],
                get_embedding_fn,
                parse_guidelines_fn) -> List[Guideline]:
        """
        Generate best response using guided generation method
        
        Args:
            language: Language to use
            opponent_weights: Opponent's guideline weight distribution
            get_embedding_fn: Function to get embeddings
            parse_guidelines_fn: Function to parse guidelines
            
        Returns:
            List of generated guidelines
        """
        # 1. Analyze opponent strategy
        strategy_analysis:dict = self._analyze_opponent_strategy(opponent_weights, language)
        logger.info(f"{self.name}: Strategy analysis: {strategy_analysis}")
        # 2. Generate candidate guidelines
        candidate_responses = self._generate_candidate_guidelines(strategy_analysis, language)
        # 3. Parse and convert generated guidelines
        new_guidelines = []
        for response in candidate_responses:
            try:
                # Parse generated guidelines
                guideline_data_list, _ = parse_guidelines_fn(response)
                logger.info(f"{self.name}: Parsing response: {guideline_data_list}")
                for data in guideline_data_list:
                    guideline_info = f"{data['guideline']}: reason: {data['reason']}. detail: {data['description']}"
                    embedding = get_embedding_fn(guideline_info)
                    
                    new_guideline = Guideline(
                        data['guideline'],
                        embedding,
                        data['reason'],
                        data['description']
                    )
                    new_guidelines.append(new_guideline)
            except Exception as e:
                logger.error(f"{self.name}: Error parsing response: {str(e)}")
                logger.error(f"{self.name}: Response:\n{response}")
                continue
        
        logger.info(f"{self.name}: {len(new_guidelines)} responses generated\n")
        return new_guidelines
    
    def _analyze_opponent_strategy(self, 
                                  opponent_weights: Dict[str, float], 
                                  language: Literal['zh', 'en']) -> dict:
        """
        Analyze weaknesses and limitations of opponent's strategy
        
        Args:
            opponent_weights: Opponent's guideline weight distribution
            language: Language to use
            
        Returns:
            Dictionary containing analysis results
        """
        # Extract opponent's high-weight guidelines
        high_weight_guidelines = [guideline for guideline, weight in 
                                sorted(opponent_weights.items(), key=lambda x: x[1], reverse=True)[:3]]
        
        # Build analysis prompt
        weakness_prompt = WEAKNESS_ANALYSIS_PROMPT[language].format(
            high_weight_guidelines=', '.join(high_weight_guidelines)
        )
        # Generate weakness analysis
        weakness_analysis = self.client.generate(
            messages=[{"role": "user", "content": weakness_prompt}],
            temperature=0.7
        )
        # Identify important areas not covered
        coverage_prompt = COVERAGE_GAPS_PROMPT[language].format(
            all_guidelines=', '.join(opponent_weights.keys())
        )
        coverage_gaps = self.client.generate(
            messages=[{"role": "user", "content": coverage_prompt}],
            temperature=0.7
        )
        
        return {
            "high_weight_guidelines": high_weight_guidelines,
            "weakness_analysis": weakness_analysis,
            "coverage_gaps": coverage_gaps
        }
    
    def _generate_candidate_guidelines(self, 
                                strategy_analysis: dict, 
                                language: Literal['zh', 'en']) -> List[str]:
        """
        Generate various types of candidate guidelines based on strategy analysis
        
        Args:
            strategy_analysis: Opponent strategy analysis results
            language: Language to use
            
        Returns:
            List of candidate guideline responses
        """
        candidate_responses = []
        
        # Get guideline template
        guideline_template = GUIDELINE_TEMPLATE[language]
        
        # 1. Counter-guideline generation (targeting opponent's weaknesses)
        counter_prompt = COUNTER_GUIDELINE_PROMPT[language].format(
            weakness_analysis=strategy_analysis['weakness_analysis'],
            guideline_template=guideline_template
        )
        
        counter_response = self.client.generate(
            messages=[{"role": "user", "content": counter_prompt}],
            temperature=0.6
        )
        candidate_responses.append(counter_response)
        
        # 2. Gap-filling guideline generation (covering areas not addressed by opponent)
        gap_prompt = GAP_GUIDELINE_PROMPT[language].format(
            coverage_gaps=strategy_analysis['coverage_gaps'],
            guideline_template=guideline_template
        )
        
        gap_response = self.client.generate(
            messages=[{"role": "user", "content": gap_prompt}],
            temperature=0.6
        )
        candidate_responses.append(gap_response)
        
        # 3. Innovative guideline generation (breaking the thinking framework)
        innovation_prompt = INNOVATION_GUIDELINE_PROMPT[language].format(
            guideline_template=guideline_template
        )
        
        innovation_response = self.client.generate(
            messages=[{"role": "user", "content": innovation_prompt}],
            temperature=0.8
        )
        candidate_responses.append(innovation_response)
        
        return candidate_responses
    
class SimpleBRGenerator(BRGenerator):
    """Simple BR generator using basic prompt templates"""
    
    def __init__(self, client: LlmClient, name: str, prompt_templates: Dict[str, str]) -> None:
        """
        Initialize simple BR generator
        
        Args:
            client: LLM client
            name: Generator name
            prompt_templates: Prompt templates for different languages
        """
        super().__init__(client, name)
        self.prompt_templates = prompt_templates
    
    def generate(self, 
                language: Literal['zh', 'en'], 
                opponent_weights: Dict[str, float],
                get_embedding_fn,
                parse_guidelines_fn) -> List[Guideline]:
        """
        Generate best response using simple prompt templates
        
        Args:
            language: Language to use
            opponent_weights: Opponent's guideline weight distribution
            get_embedding_fn: Function to get embeddings
            parse_guidelines_fn: Function to parse guidelines
            
        Returns:
            List of generated guidelines
        """
        # Select key guidelines with weight > 0.2
        opponent_key_guidelines = [guideline for guideline, weight in opponent_weights.items() if weight > 0.2]
        # If no key guidelines, select the top 2 guidelines by weight
        if not opponent_key_guidelines:
            opponent_key_guidelines = [guideline for guideline, weight in 
                                     sorted(opponent_weights.items(), key=lambda x: x[1], reverse=True)[:2]]
        
        new_guidelines = []
        for guideline in opponent_key_guidelines:
            prompt = self.prompt_templates[language].format(
                opponent_key_guideline=guideline,
                opponent_guidelines=opponent_weights
            )
            response = self.client.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6
            )
            try:
                guideline_data_list, _ = parse_guidelines_fn(response)
                for data in guideline_data_list:
                    guideline_info = f"{data['guideline']}: reason: {data['reason']}. detail: {data['description']}"
                    embedding = get_embedding_fn(guideline_info)
                    
                    new_guideline = Guideline(
                        data['guideline'],
                        embedding,
                        data['reason'],
                        data['description']
                    )
                    new_guidelines.append(new_guideline)
            except Exception as e:
                logger.error(f"{self.name}: Error parsing response: {str(e)}")
                continue
        
        logger.info(f"{self.name}: {len(new_guidelines)} responses generated\n")
        return new_guidelines

# Factory method to create BR generator
def create_br_generator(generator_type: str, client: LlmClient, name: str, prompt_templates: Optional[Dict[str, str]] = None) -> BRGenerator:
    """
    Create BR generator instance
    
    Args:
        generator_type: Generator type ('guided' or 'simple')
        client: LLM client
        name: Generator name
        prompt_templates: Prompt templates (only for SimpleBRGenerator)
        
    Returns:
        BR generator instance
    """
    if generator_type.lower() == 'guided':
        return GuidedBRGenerator(client, name)
    elif generator_type.lower() == 'simple':
        if prompt_templates is None:
            raise ValueError("prompt_templates must be provided for SimpleBRGenerator")
        return SimpleBRGenerator(client, name, prompt_templates)
    else:
        raise ValueError(f"Unknown generator type: {generator_type}")