# ... existing code ...
import json
import time
from typing import Any, Dict, List

import numpy as np
from openai import OpenAI
from evaluation.consensus_eval.consensus_evaluator import ConsensusEvaluator

VALUE_DIMENSIONS = [
    "Self-Direction", "Stimulation", "Hedonism", "Achievement", "Power",
    "Security", "Conformity", "Tradition", "Benevolence", "Universalism"
]

SYSTEM_PROMPT = """As a expert in values evaluation, please process the input following the rules as follows strictly:

1. dimensions(with order):
{value_definitions}

2. Scoring criteria:
- Clearly support the value: +1
- Neutral or irrelevant: 0
- Clearly oppose the value: -1
3. Output requirements:
- Must use strict JSON format
- Must include the "vector" field
- The array length must be 10
- Values can only be -1/0/1

example output：{{"vector": [0,-1,1,0,0,1,-1,0,1,0]}}"""

VALUE_DEFINITIONS = "\n".join(
    f"{i+1}. {dim}: {desc}" for i, (dim, desc) in enumerate([
        ("Self-Direction", "The ability and tendency to independently determine one's goals, actions, and life direction, emphasizing autonomy, self-reliance, and the freedom to make decisions without excessive external influence."),
        ("Stimulation", "A strong desire to seek new, exciting, and challenging experiences, including novel sensations, adventures, and intellectual or emotional arousal, often motivated by a need to avoid monotony and routine."),
        ("Hedonism", "A focus on pursuing pleasure, comfort, and personal enjoyment as primary life goals, prioritizing immediate gratification and the satisfaction of physical or psychological desires."),
        ("Achievement", "The pursuit of personal success, competence, and accomplishment through one's efforts, often measured by tangible goals, professional advancement, or societal recognition."),
        ("Power", "The aspiration to possess control, influence, or authority over others, resources, or situations, including both personal dominance and institutional power (e.g., social status, leadership roles)."),
        ("Security", "The need for stability, safety, and predictability in one's life, encompassing physical safety, financial stability, social order, and protection from uncertainty or threats."),
        ("Conformity", "The willingness to adhere to social norms, rules, and expectations, prioritizing harmony, obedience, and avoiding behavior that may disrupt group cohesion or cause conflict."),
        ("Tradition", "Respect for and adherence to long-established customs, beliefs, and cultural practices, valuing heritage, continuity, and the wisdom of past generations."),
        ("Benevolence", "A concern for the well-being and welfare of others, expressed through altruistic actions, generosity, and a desire to help, support, or improve the lives of those in one's immediate social circle."), 
        ("Universalism", "The acceptance and promotion of broad, inclusive values that prioritize the welfare of all humanity and the planet, such as equality, justice, environmental protection, and global cooperation.")
    ])
)

class ModelBasedConsensusEvaluator(ConsensusEvaluator):
    """基于模型的共识评估器"""


    def __init__(self, **kwargs):
        self.system_prompt = SYSTEM_PROMPT
        self.value_definitions = VALUE_DEFINITIONS
        self.api_config = kwargs.get("api_config", {})
        print(f"api_config: {self.api_config}")
        self.client = OpenAI(api_key=self.api_config['api_key'], base_url=self.api_config['base_url'])
        self.total_cnt = 0
        self.consensus_cnt = 0


    def evaluate_initial_responses(self, topic: str, response1: str, response2: str) -> Dict[str, float]:
        """评估初始回应"""
        vectors = {
            "response1_vector": self.get_value_vector(response1),
            "response2_vector": self.get_value_vector(response2)
        }
        distance = self.calculate_distance(vectors["response1_vector"], vectors["response2_vector"])
        return {"init_vectors": vectors, "initial_distance": distance}

    def evaluate_final_responses(self, topic: str, response1: str, response2: str) -> Dict[str, float]:
        """评估最终回应"""
        vectors = {
            "response1_vector": self.get_value_vector(response1),
            "response2_vector": self.get_value_vector(response2)
        }
        distance = self.calculate_distance(vectors["response1_vector"], vectors["response2_vector"])
        return {"final_vectors": vectors, "final_distance": distance}

    def calculate_consensus_metrics(self, initial_metrics: Dict[str, float], final_metrics: Dict[str, float]) -> Dict[str, float]:
        """计算共识达成程度"""
        init_vectors = initial_metrics["init_vectors"]
        final_vectors = final_metrics["final_vectors"]
        initial_dist = initial_metrics["initial_distance"]
        final_dist = final_metrics["final_distance"]
        reduction = (1 - final_dist / initial_dist) * 100 if initial_dist != 0 else 0 # 百分比
        
        self.total_cnt+=1
        if reduction >= 1:
            self.consensus_cnt+=1
        print(f"consensus proportion: {(self.consensus_cnt/self.total_cnt)*100}%")
        
        return {
            "init_vectors": init_vectors,
            "final_vectors": final_vectors,
            "initial_dist": initial_dist,
            "final_dist": final_dist,
            "reduction": reduction,
            "is_consensus": reduction >= 1
        }

    def get_value_vector(self, text: str) -> List[int]:
        """根据文本获取价值向量"""
        for _ in range(10):
            try:
                # print(f"[DEBUG] starting to call api")
                response = self.client.chat.completions.create(
                    model=self.api_config['model'],
                    messages=[
                        {"role": "system", "content": self.system_prompt.format(value_definitions=self.value_definitions)},
                        {"role": "user", "content": f"text: {text}\nStrictly follow the example format for output, do not include any explanatory text."}
                    ],
                    temperature=0,
                    response_format={"type": "json_object"},
                    timeout=10
                )
                raw_content = response.choices[0].message.content
                if not raw_content:
                    raise ValueError("Empty response content")
                # print(f"[DEBUG] {raw_content}")
                data = json.loads(raw_content)
                vector = data["vector"]
                if self.validate_vector(vector):
                    return vector
                raise ValueError("Invalid vector format")
            except Exception:
                time.sleep(1)
        return self.fallback_vector(text)

    def validate_vector(self, vector: List[int]) -> bool:
        """验证向量格式"""
        return len(vector) == 10 and all(v in (-1, 0, 1) for v in vector)

    def fallback_vector(self, text: str) -> List[int]:
        """备选向量"""
        return [0] * 10

    def calculate_distance(self, vec1: List[int], vec2: List[int]) -> float:
        # """计算归一化欧氏距离"""
        # norm1 = np.array(vec1) / np.linalg.norm(vec1) if np.linalg.norm(vec1) != 0 else vec1
        # norm2 = np.array(vec2) / np.linalg.norm(vec2) if np.linalg.norm(vec2) != 0 else vec2
        # return float(np.linalg.norm(norm1 - norm2))
        
        """计算余弦相似度"""
        # 将列表转换为NumPy数组
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # 计算余弦相似度
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        # 防止除以零
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        cosine_similarity = dot_product / (norm1 * norm2)
        return float(cosine_similarity)