from datetime import datetime
import logging
import json
import os
import pdb
from typing import Literal, List, Dict, Tuple

from debate.guideline_weight_desc import WeightDescriptionGenerator, generate_weight_prompt
from debate.meta_solver import MirrorDescentSolver
from debate.agent import CultureAgent, Guideline
from debate.utils.utils_class import DebateScorer, get_similarity_score, get_yaml_config
from debate.prompts.prompts import GUIDELINE_DESC_PROMPT, GUIDELINE_WEIGHT_DESC_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
params = get_yaml_config("debate/config/params.yaml")

class DebateHistory:
    def __init__(self, agent_a: CultureAgent, agent_b: CultureAgent, topic:str) -> None:
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.topic = topic
        self.history = []
        self.consensus_summary = {
            f"{self.agent_a.culture}": "",
            f"{self.agent_b.culture}": ""
        }


    def update_history(self, round_number: int, response_a1: str, response_b1: str, br_a: Guideline, br_b: Guideline, response_a2: str, response_b2: str):
        debate_info = {
            "round": round_number + 1,
            "first_exchange": {
                f"{self.agent_a.culture}_response": response_a1,
                f"{self.agent_b.culture}_response": response_b1,
            },
            "second_exchange": {
                f"{self.agent_a.culture}_best_response": str(br_a),
                f"{self.agent_b.culture}_best_response": str(br_b),
                f"{self.agent_a.culture}_response": response_a2,
                f"{self.agent_b.culture}_response": response_b2,
                f"{self.agent_a.culture}_utility": {'consistency': br_a.utility.consistency, 'novelty': br_a.utility.novelty, 'acceptance': br_a.utility.acceptance, 'total': br_a.utility.total},
                f"{self.agent_b.culture}_utility": {'consistency': br_b.utility.consistency, 'novelty': br_b.utility.novelty, 'acceptance': br_b.utility.acceptance, 'total': br_b.utility.total},
            },
            "guidelines_weight": {
                f"{self.agent_a.culture}_distribution": self.agent_a.state.get_guideline_weights(),
                f"{self.agent_b.culture}_distribution": self.agent_b.state.get_guideline_weights(),
            }
        }
        self.history.append(debate_info)

    def add_consensus_summary(self, summary_a: str, summary_b: str):
        """Add consensus summary for both sides"""
        self.consensus_summary[f"{self.agent_a.culture}"] = summary_a
        self.consensus_summary[f"{self.agent_b.culture}"] = summary_b
    
    def format2json(self, meta_data: Dict[str, int]) -> str:
        # Convert topic and history to JSON format

        return json.dumps({
            "topic": self.topic,
            "initial_response": {
                f"{self.agent_a.culture}": self.agent_a.state.get_init_guideline_desc(),
                f"{self.agent_b.culture}": self.agent_b.state.get_init_guideline_desc(),
            },
            "history": self.history,
            "consensus_response": self.consensus_summary,  # Add consensus summary
            "meta_data": meta_data
        }, ensure_ascii=False, indent=4)

# ===================== PSRO Debate Process =====================
class PSRODebate:
    '''
    Model the debate process as PSRO (Policy-Space Response Oracles)
    Formalized as a quadruple: Γ = 〈P, Π, Σ, U〉
    - P: Participants, representing two debate models
    - Π: Strategy space, the set of arguments for A and B
    - Σ: Mixed strategy distribution (importance weights)
    - U: Utility function
    '''
    def __init__(self, topic: str, agent_a: CultureAgent, agent_b: CultureAgent, topic_index:int,
                 max_rounds: int, method: Literal["consensus", "simple"], note:str,
                 scorer_params:list[float], language: Literal['zh', 'en']='zh') -> None:
        """Initialize PSRO debate process"""
        self.topic = topic
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.max_rounds = max_rounds
        self.method = method
        self.language: Literal['zh', 'en'] = language
        self.note = note
        self.scorer_params = scorer_params
        self.topic_index = topic_index
        # Set the language attribute of the Agent to match the debate language
        self.agent_a.language = language
        self.agent_b.language = language
        
        self.debate_history = DebateHistory(agent_a, agent_b, topic)
        self.filename = self._generate_filename()
        self.path = self._get_debate_path()
        self.scorer = DebateScorer(alpha=float(self.scorer_params[0]), beta=float(self.scorer_params[1]), gamma=float(self.scorer_params[2]))
        self.similarity_matrix: Dict[Tuple[str, str], float] = {}
        self.epsilon:float = 0.02  # Consensus determination threshold
        self.round_number = 0
        self.meta_data = {
            "max_rounds": self.max_rounds,
            "true_rounds": 0,
            "consensus_reached": False
        }

    def _get_debate_path(self) -> str:
        """Get the path to save debate history"""
        now = datetime.now().strftime("%Y-%m-%d")
        now = now + f"_{self.note.split('_')[0]}" if self.note else now
        if len(self.note.split('_')) > 1:
            return os.path.join(params['debate_output_path'], 
                          f'{self.agent_a.culture} and {self.agent_b.culture}', now, self.note.split('_')[1])
        else:
            return os.path.join(params['debate_output_path'], 
                          f'{self.agent_a.culture} and {self.agent_b.culture}', now)

    def _generate_filename(self):
        """Generate a unique filename, including timestamp and model name"""
        now = datetime.now().strftime("%Y-%m-%d-%H-%M")
        return f"psro_{self.topic_index}_{now}_{self.agent_a.model_client.model_name.split('/')[-1]}.json"

    def save_debate_history(self, path: str, filename: str):
        """Save the complete debate history to a file"""
        if not os.path.exists(path):
            os.makedirs(path)
        filepath = os.path.join(path, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.debate_history.format2json(self.meta_data))
        logger.info(f"Debate history saved at: {filepath}\n")
    
    def run(self) -> dict:
        # Initialize strategy library
        self._initialize_psro()
        for round_number in range(self.max_rounds):
            self.round_number = round_number + 1
            logger.info(f"Starting PSRO debate round {self.round_number}")
            self._psro_iteration(round_number)
            logger.info(f"PSRO debate round {self.round_number} completed")
            # Save debate history for this round
            self.meta_data["true_rounds"] = self.round_number
            # Check if consensus is reached
            if self.method in ["self_consensus", "judger_consensus"] and round_number >= 1:
                consensus = self.judge_consensus()
                if consensus:
                    logger.info("Consensus reached!")
                    self.meta_data["consensus_reached"] = True
                    
                    # If agents summarize consensus, generate consensus summary
                    if self.method == "self_consensus":
                        logger.info("Generating consensus summary by agents")
                        self._generate_consensus_summary()
            
            # Save debate history
            self.save_debate_history(self.path, self.filename)
            if self.meta_data["consensus_reached"]:
                break
                
        return self.meta_data

    def _initialize_psro(self):
        """Initialize the PSRO algorithm"""
        # 1. Initialize strategy pool
        logger.info("Initializing guideline pools")
        # Initialize Agent's guideline pool
        a_guidelines = self.agent_a.initialize_guideline_pool(self.topic, num_guidelines=1)
        b_guidelines = self.agent_b.initialize_guideline_pool(self.topic, num_guidelines=1)
        
        # 2. Build initial similarity matrix
        logger.info("Building initial similarity matrix")
        self._build_initial_similarity_matrix(a_guidelines, b_guidelines)

        # 3. Get utilities
        logger.info("Calculating initial utilities")
        self._calculate_guideline_utilities(a_guidelines, self.agent_a, self.agent_b, isInit=True)
        self._calculate_guideline_utilities(b_guidelines, self.agent_b, self.agent_a, isInit=True)   

    def _build_initial_similarity_matrix(self, a_guidelines: List[Guideline], b_guidelines: List[Guideline]):
        """Build initial similarity matrix - only store similarity between guidelines of different groups"""
        for guideline_a in a_guidelines:
            for guideline_b in b_guidelines:
                # Calculate similarity between guidelines
                similarity = get_similarity_score(guideline_a.embedding, guideline_b.embedding)
                # Record in similarity matrix (symmetric matrix)
                self.similarity_matrix[(guideline_a.content, guideline_b.content)] = similarity
                self.similarity_matrix[(guideline_b.content, guideline_a.content)] = similarity
        
        logger.info(f"Initial similarity matrix size: {len(self.similarity_matrix)}")

    def _update_similarity_matrix(self, guidelines_a: List[Guideline], 
                                guidelines_b: List[Guideline]) -> None:
        """Update similarity matrix"""
        for g_a in guidelines_a:
            for g_b in self.agent_b.state.guideline_pool:
                similarity = get_similarity_score(g_a.embedding, g_b.embedding)
                self.similarity_matrix[(g_a.content, g_b.content)] = similarity
                self.similarity_matrix[(g_b.content, g_a.content)] = similarity
        
        for g_b in guidelines_b:
            for g_a in self.agent_a.state.guideline_pool:
                similarity = get_similarity_score(g_b.embedding, g_a.embedding)
                self.similarity_matrix[(g_b.content, g_a.content)] = similarity
                self.similarity_matrix[(g_a.content, g_b.content)] = similarity

        for g_a in guidelines_a:
            for g_b in guidelines_b:
                similarity = get_similarity_score(g_a.embedding, g_b.embedding)
                self.similarity_matrix[(g_a.content, g_b.content)] = similarity
                self.similarity_matrix[(g_b.content, g_a.content)] = similarity

    def _update_agent_memory(self, response_a: str, response_b: str):
        """Update agent memory"""
        self.agent_a.add_memory(role='assistant', content=response_a)
        self.agent_b.add_memory(role='assistant', content=response_b)
        self.agent_a.add_memory(role='user', content=response_b)
        self.agent_b.add_memory(role='user', content=response_a)

    def _generate_first_exchange(self) -> Tuple[str, str]:
        """Generate the first round of dialogue"""
        
        # rule-based response generation
        generator = WeightDescriptionGenerator(self.language)
        response_a1 = generator.generate_description(
            self.agent_a.state.get_guideline_weights(),
            self.agent_a.state.get_previous_guideline_weights(),
        )
        response_b1 = generator.generate_description(
            self.agent_b.state.get_guideline_weights(),
            self.agent_b.state.get_previous_guideline_weights(),
        )
        return response_a1, response_b1

    def _generate_best_responses(self) -> Tuple[List[Guideline], List[Guideline]]:
        """Generate the best responses for both sides"""
        brs_a = self.agent_a.generate_best_responses(
            self.agent_b.state.get_guideline_weights()
        )
        brs_b = self.agent_b.generate_best_responses(
            self.agent_a.state.get_guideline_weights()
        )
        return brs_a, brs_b

    def _calculate_guideline_utilities(self, guidelines: List[Guideline], 
                                     agent: CultureAgent, opponent: CultureAgent, isInit:bool=False) -> None:
        """Calculate the consistency and novelty of guidelines (first stage utility)"""
        for guideline in guidelines:
            utility, consistency, acceptance, novelty = self.scorer.calculate_utility(
                guideline.embedding,
                guideline.content,
                self.similarity_matrix,
                opponent.state.get_guideline_weights(),
                history_embeddings=agent.state.get_guideline_embeddings()if not isInit else None,
                initial_embedding=agent.state.get_init_embedding() if not isInit else None
            )
            guideline.utility.update_utility(consistency, acceptance, novelty, utility)

    def _select_best_responses(self, brs_a: List[Guideline], 
                             brs_b: List[Guideline]) -> Tuple[Guideline, Guideline]:
        """选择效用最高的响应并计算接受度"""
        # 计算效用
        self._calculate_guideline_utilities(brs_a, self.agent_a, self.agent_b)
        self._calculate_guideline_utilities(brs_b, self.agent_b, self.agent_a)

        # 选择效用最高的响应
        best_br_a = max(brs_a, key=lambda x: x.utility.total)
        best_br_b = max(brs_b, key=lambda x: x.utility.total)

        return best_br_a, best_br_b

    def _generate_second_exchange(self, best_br_a: Guideline, 
                                best_br_b: Guideline) -> Tuple[str, str]:
        """生成第二轮对话"""
        prompt_a2 = GUIDELINE_DESC_PROMPT[self.language].format(guideline=str(best_br_a))
        prompt_b2 = GUIDELINE_DESC_PROMPT[self.language].format(guideline=str(best_br_b))
        
        response_a2 = self.agent_a.generate_response_with_system_prompt(prompt=prompt_a2)
        response_b2 = self.agent_b.generate_response_with_system_prompt(prompt=prompt_b2)
        
        return response_a2, response_b2

    def _update_weights_and_history(self, round_number: int, 
                                  response_a1: str, response_b1: str,
                                  best_br_a: Guideline, best_br_b: Guideline,
                                  response_a2: str, response_b2: str) -> None:
        """更新权重分布和辩论历史"""
        self._update_guideline_weights()
        
        self.debate_history.update_history(
            round_number, response_a1, response_b1,
            best_br_a, best_br_b, response_a2, response_b2
        )

    def _psro_iteration(self, round_number: int) -> None:
        """执行一轮PSRO迭代（辩论）"""
        # 1. 生成第一轮响应
        response_a1, response_b1 = self._generate_first_exchange()
        
        # 更新记忆
        self._update_agent_memory(response_a1, response_b1)
        
        # 2. 生成和评估最优响应
        brs_a, brs_b = self._generate_best_responses()
        self._update_similarity_matrix(brs_a, brs_b)
        best_br_a, best_br_b = self._select_best_responses(brs_a, brs_b)
        
        # 3. 生成第二轮响应
        response_a2, response_b2 = self._generate_second_exchange(best_br_a, best_br_b)
        self._update_agent_memory(response_a2, response_b2)
        # 添加到策略池
        self.agent_a.state.add_guideline(best_br_a)
        self.agent_b.state.add_guideline(best_br_b)
        # 4. 更新权重和历史
        self._update_weights_and_history(round_number, response_a1, response_b1,
                                       best_br_a, best_br_b, response_a2, response_b2)

    def _update_guideline_weights(self):
        """更新准则权重基于相似度矩阵"""
        solver = MirrorDescentSolver.create(
            self.agent_a.state.guideline_pool,
            self.similarity_matrix,
            self.agent_b.state.guideline_pool
        )
        a, b = solver.solve(max_iter=1000, eta=0.05, verbose=True)
        a = solver.apply_exploration(a)
        b = solver.apply_exploration(b)
        weights_a = {guideline.content: weight for guideline, weight in zip(self.agent_a.state.guideline_pool, a)}
        weights_b = {guideline.content: weight for guideline, weight in zip(self.agent_b.state.guideline_pool, b)}
        self.agent_a.state.update_guideline_weights(weights_a)
        logger.info(f"{self.agent_a.name}: Updated guideline weights:{weights_a}")
        self.agent_b.state.update_guideline_weights(weights_b)
        logger.info(f"{self.agent_b.name}: Updated guideline weights{weights_b}")
        return 


    def get_debate_history_filepath(self):
        return os.path.join(self.path, self.filename)

    def judge_consensus(self) -> bool:
        """判断是否达成共识"""
        # 如果历史不足两轮，无法判断
        if len(self.debate_history.history) < 2:
            return False
        #检查新准则的相似性
        epsilon = self.epsilon
        a_new_guideline = self.agent_a.state.guideline_pool[-1]
        b_new_guideline = self.agent_b.state.guideline_pool[-1]
        similarity = self.similarity_matrix[(a_new_guideline.content, b_new_guideline.content)]
        if similarity > 0.8:
            # 相似度足够高，扩大epsilon范围
            epsilon = self.epsilon * 2
            logger.info(f"Similarity between new guidelines: {similarity}, epsilon: {epsilon}")

        last_round = self.debate_history.history[-1]
        prev_round = self.debate_history.history[-2]
        
        # 检查效用变化
        a_utility_last = last_round["second_exchange"][f"{self.agent_a.culture}_utility"]['total']
        a_utility_prev = prev_round["second_exchange"][f"{self.agent_a.culture}_utility"]['total']
        a_utility_diff = a_utility_last - a_utility_prev
        
        b_utility_last = last_round["second_exchange"][f"{self.agent_b.culture}_utility"]['total']
        b_utility_prev = prev_round["second_exchange"][f"{self.agent_b.culture}_utility"]['total']
        b_utility_diff = b_utility_last - b_utility_prev
        
        logger.info(f"Utility differences - A: {a_utility_diff}, B: {b_utility_diff}")
        
        # 如果双方效用变化都很小，视为达成共识
        consensus_reached = a_utility_diff < epsilon and b_utility_diff < epsilon
        
        return consensus_reached

       
    
    def _generate_consensus_summary(self) -> Tuple[str, str]:
        """生成双方对共识的总结"""
        from debate.prompts.prompts import CONSENSUS_SUMMARY_PROMPT
        
        # 获取双方最终的准则权重
        a_weights = self.agent_a.state.get_guideline_weights_desc()
        b_weights = self.agent_b.state.get_guideline_weights_desc()
        
        # 生成A的总结提示
        prompt_a = CONSENSUS_SUMMARY_PROMPT[self.language].format(
            culture=self.agent_a.culture,
            other_culture=self.agent_b.culture,
            topic=self.topic,
            my_weights=a_weights,
            opponent_weights=b_weights
        )
        
        # 生成B的总结提示
        prompt_b = CONSENSUS_SUMMARY_PROMPT[self.language].format(
            culture=self.agent_b.culture,
            other_culture=self.agent_a.culture,
            topic=self.topic,
            my_weights=b_weights,
            opponent_weights=a_weights
        )
        
        summary_a = self.agent_a.generate_response_with_system_prompt(prompt=prompt_a)
        summary_b = self.agent_b.generate_response_with_system_prompt(prompt=prompt_b)
        
        # 更新记忆
        self.agent_a.add_memory(role='assistant', content=summary_a)
        self.agent_b.add_memory(role='assistant', content=summary_b)
        
        # 保存到辩论历史
        self.debate_history.add_consensus_summary(summary_a, summary_b)
        
        logger.info(f"{self.agent_a.culture}'s consensus summary: {summary_a}")
        logger.info(f"{self.agent_b.culture}'s consensus summary: {summary_b}")
        
        return summary_a, summary_b