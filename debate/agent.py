from abc import ABC, abstractmethod
import pdb
import re
from typing import List, Dict, Literal
import logging

from torch import Tensor

from debate.utils.utils_fn import get_embedding_model
from debate.br_generator import BRGenerator, create_br_generator
from debate.utils.utils_class import DebateState, Guideline, LlmClient
from debate.prompts.prompts import ORIGINAL_GUIDELINE_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CultureAgent(ABC):
    def __init__(self, name: str, culture: str, client: LlmClient, system_prompt: str, gpu_id:int=0, language: Literal['zh', 'en'] = 'zh', br_generator_type: str = 'guided', method:Literal["psro", "debate", "consultancy"]='psro') -> None:
        self.name = name
        self.culture = culture
        self.language:Literal['zh', 'en'] = language  # Add language attribute
        self.model_client = client
        self.state = DebateState()
        self.memory_list: List[Dict[str, str]] = []
        self.embedding_model = get_embedding_model(gpu_id) if method == "psro" else None
        self.set_system_prompt(system_prompt)
        self.br_generator: BRGenerator = create_br_generator(
            generator_type=br_generator_type,
            client=client,
            name=name,
        )
    
    def generate_original_guidelines(self, topic: str, num_guidelines: int) ->tuple[List[Dict[str, str]], str]:
        """Generate initial arguments, return a list"""
        prompt = ORIGINAL_GUIDELINE_PROMPT[self.language].format(
            num_guidelines=num_guidelines,
            topic=topic,
            culture=self.culture
        )
        _response = self.model_client.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=256,
        )
        # Parse multiple generated arguments and summary
        guidelines, response = self._parse_guidelines(_response)
        logger.info(f"{self.name}: Original guidelines generated:\n {guidelines}")
        if len(guidelines) != num_guidelines:
            logger.warning(f"{self.name}: Expected {num_guidelines} guidelines, but got {len(guidelines)}")
            guidelines = guidelines[:num_guidelines]
        if not response:
            response = f"we insist {guidelines[0]['guideline']}, the reason is {guidelines[0]['reason']}. {guidelines[0]['description']}"
        return guidelines, response

    def generate_best_responses(self, opponent_weights: Dict[str, float]) -> List[Guideline]:
        """
        Generate best responses to the opponent's meta-strategy
        
        Args:
            opponent_weights: Opponent's meta-strategy distribution
            
        Returns:
            Generated best response strategy
        """
        # Use BR generator to generate responses, no need to pass language parameter anymore
        return self.br_generator.generate(
            language=self.language,
            opponent_weights=opponent_weights,
            get_embedding_fn=self.get_embedding,
            parse_guidelines_fn=self._parse_guidelines
        )
    
    from typing import List, Dict
    
    def _parse_guidelines(self, text)->tuple[List[Dict[str, str]], str|None]:
        # Split guideline entries
        guideline_blocks = re.split(r'---next---', text)
        
        pattern = re.compile(
            r'Guideline: (.*?)\s+'  # Capture guideline, use \s+ to match any whitespace including newlines
            r'Reason: (.*?)\s+'     # Capture reason
            r'Description: (.*?)(?=---|$)',  # Capture description, until next '---' or end of string
            re.DOTALL
        )
        
        guidelines = []
        for block in guideline_blocks:
            if match := pattern.search(block):
                guideline = {
                    "guideline": match.group(1).strip(),
                    "reason": match.group(2).strip(),
                    "description": match.group(3).strip()
                }
                guidelines.append(guideline)
        
        # Separate cultural summary part
        desc_split = re.split(r'--- desc ---', text)
        response = desc_split[1].strip() if len(desc_split) > 1 else None
        return guidelines, response

    def generate_response_with_system_prompt(self, prompt:str|None=None) -> str:
        """Add prompt to memory (not saved), generate reply"""
        memory_list = self.recall_memory()
        new_memory_list = memory_list.copy()
        if prompt:
            new_memory_list.append({"role": "system", "content": prompt})
            logger.info(f"\n{self.name}: Generating response \n")
        response = self.model_client.generate(
            messages=new_memory_list,
        )
        return response
    
    def get_embedding(self, text: str) -> Tensor:
        """Get text embedding representation"""
        if self.embedding_model is None:
            raise ValueError("Embedding model is not initialized.")
        tensor = self.embedding_model.encode(text)
        return Tensor(tensor)

    def set_system_prompt(self, system_prompt: str):
        self.memory_list.append({"role": "system", "content": f"{system_prompt}"})
        logger.info(f"{self.name}: System prompt set\n")

    def add_memory(self, role: Literal['user', 'assistant'], content: str):
        """Add a new memory entry"""
        self.memory_list.append({"role": role, "content": content})
        if role == "assistant":
            logger.info(f"{self.name}: Memory added:\n {role} - {content}\n")

    def recall_memory(self) -> List[Dict[str, str]]:
        """Recall all memory entries"""
        logger.info(f"{self.name}: Recalling memory, len:{len(self.memory_list)}\n")
        return self.memory_list

    def clear_memory(self):
        """Clear all memory entries"""
        self.memory_list.clear()
        logger.info(f"{self.name}: Memory cleared\n")
    
    
    def reset_state(self):
        """Reset debate state"""
        self.state = DebateState()
        logger.info(f"{self.name}: State reset\n")
    
    def get_state(self) -> DebateState:
        """Get current debate state"""
        return self.state
    
    def initialize_guideline_pool(self, topic: str, num_guidelines: int = 1) -> List[Guideline]:
        """Initialize guideline pool"""
        # Generate initial guideline texts
        guideline_texts, initial_response = self.generate_original_guidelines(topic, num_guidelines)

        # Create Guideline objects and add to state
        guidelines = []
        guidelines_info = []
        for text in guideline_texts:
            # Use full guideline info for embedding
            guideline_info = f"{text['guideline']}: reason: {text['reason']}. detail: {text['description']}"
            guidelines_info.append(guideline_info)
            embedding = self.get_embedding(guideline_info)
            guideline = Guideline(text['guideline'], embedding, text['reason'], text['description'])
            self.state.add_guideline(guideline)
            guidelines.append(guideline)
        
        # Update embedding for initial guidelines
        self.state.set_init_guideline(guidelines, self.get_embedding(initial_response), initial_response)
        # Initialize uniform weight distribution
        weight = 1.0 / len(guidelines)
        for guideline in guidelines:
            guideline.update_weight(weight)
        
        logger.info(f"{self.name}: Initialized guideline pool with {len(guidelines)} guidelines")
        return guidelines