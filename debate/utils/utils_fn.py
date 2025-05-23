import json
import logging
import os
from torch import Tensor, device
import torch
import yaml

from debate.prompts.culture_desc_prompts import CULTURE_DESC_PROMPT
from debate.prompts.prompts import CONSULTANCY_SYSTEM_PROMPT, DEBATE_SYSTEM_PROMPT, PSRO_SYSTEM_PROMPT, RESPONSE_LANGUAGE_PROMPT
import torch.nn.functional as F

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_yaml_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise Exception(f"Error loading config: {str(e)}")

def get_json_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"Error loading config: {str(e)}")
    
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Literal, Tuple

_embedding_model = None

def get_embedding_model(gpu_id: int) -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model...")
        params = get_yaml_config("debate/config/params.yaml")
        embedding_model_name = params['embedding_model']
        embedding_model_path = params['embedding_model_path']
        # Set GPU for current process
        device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"
        
        # Load model
        _embedding_model = SentenceTransformer(embedding_model_path, device=device)
    return _embedding_model

def get_similarity_score(embedding1: Tensor, embedding2: Tensor) -> float:
    """Calculate cosine similarity between two embedding vectors"""
    # Ensure input is 2D tensor
    if embedding1.dim() == 1:
        embedding1 = embedding1.unsqueeze(0)
    if embedding2.dim() == 1:
        embedding2 = embedding2.unsqueeze(0)
    # Calculate cosine similarity
    similarity = F.cosine_similarity(embedding1, embedding2, dim=1)
    return float(similarity.item())  # Return scalar value if needed

def get_legal_cultures() -> List[str]:
    """Get list of valid cultures"""
    cultures:dict = get_yaml_config('debate/config/culture_map.yaml')
    legal_cultures = cultures.keys()
    return list(legal_cultures)

def check_legal_culture(culture: str) -> bool:
    """Check if culture is valid"""
    if culture not in get_legal_cultures():
        logger.error(f"Invalid culture: {culture}")
        return False
    return True

def get_system_prompt(culture: str, topic: str, lan:str, method:Literal["psro", "debate", "consultancy"]) -> str:
    """Get system prompt"""
    language = 'Chinese' if lan == 'zh' else 'English'
    system_prompt = ''
    if method == "psro":
        system_prompt_ = PSRO_SYSTEM_PROMPT[lan].format(culture=culture, topic=topic)
    elif method == "debate":
        system_prompt_ = DEBATE_SYSTEM_PROMPT[lan].format(culture=culture, topic=topic)
    elif method == "consultancy":
        system_prompt_ = CONSULTANCY_SYSTEM_PROMPT[lan].format(culture=culture, topic=topic)
    system_prompt = system_prompt_ + CULTURE_DESC_PROMPT[culture][lan] + RESPONSE_LANGUAGE_PROMPT[lan].format(language=lan)
    
    return system_prompt