from abc import ABC, abstractmethod
import random
from typing import Any, Dict, Tuple, List, Type


class ConsensusEvaluator(ABC):
    """共识评估的抽象基类"""

    @abstractmethod
    def evaluate_initial_responses(self, topic:str, response1: Any, response2: Any) -> Dict[str, float]:
        """
        评估两方的初始回应
        
        Args:
            topic: 辩论主题
            response1: 第一方的初始回应
            response2: 第二方的初始回应
            
        Returns:
            包含各项评估指标的字典
        """
        pass
    
    @abstractmethod
    def evaluate_final_responses(self, topic:str, response1: Any, response2: Any) -> Dict[str, float]:
        """
        评估两方的最终回应
        
        Args:
            topic: 辩论主题
            response1: 第一方的最终回应
            response2: 第二方的最终回应
            
        Returns:
            包含各项评估指标的字典
        """
        pass
    
    @abstractmethod
    def calculate_consensus_metrics(self, initial_metrics: Dict[str, float], 
                                  final_metrics: Dict[str, float]) -> Dict[str, float]:
        """
        计算初始评估和最终评估之间的差异来度量共识达成程度
        
        Args:
            initial_metrics: 初始回应的评估指标
            final_metrics: 最终回应的评估指标
            
        Returns:
            表示共识达成程度的指标字典
        """
        pass
    
    def evaluate_consensus(self, topic:str, 
                          initial_response1: Any, 
                          initial_response2: Any,
                          final_response1: Any, 
                          final_response2: Any) -> Dict[str, float]:
        """
        评估整个共识过程
        
        Args:
            topic: 辩论主题
            initial_response1: 第一方的初始回应
            initial_response2: 第二方的初始回应
            final_response1: 第一方的最终回应
            final_response2: 第二方的最终回应
            
        Returns:
            共识评估结果
        """
        initial_metrics = self.evaluate_initial_responses(topic, initial_response1, initial_response2)
        final_metrics = self.evaluate_final_responses(topic, final_response1, final_response2)
        consensus_metrics = self.calculate_consensus_metrics(initial_metrics, final_metrics)
        
        return consensus_metrics


class ConsensusEvaluatorFactory:
    """共识评估器工厂类"""
    
    _evaluators: Dict[str, Type[ConsensusEvaluator]] = {}
    
    @classmethod
    def register(cls, name: str, evaluator_class: Type[ConsensusEvaluator]) -> None:
        """
        注册一个评估器类
        
        Args:
            name: 评估器名称
            evaluator_class: 评估器类
        """
        cls._evaluators[name] = evaluator_class
    
    @classmethod
    def create(cls, name: str, **kwargs) -> ConsensusEvaluator:
        """
        创建一个评估器实例
        
        Args:
            name: 评估器名称
            **kwargs: 传递给评估器构造函数的参数
            
        Returns:
            评估器实例
            
        Raises:
            ValueError: 如果找不到指定名称的评估器
        """
        if name not in cls._evaluators:
            raise ValueError(f"Unknown evaluator: {name}")
        
        return cls._evaluators[name](**kwargs)
    
    @classmethod
    def available_evaluators(cls) -> List[str]:
        """
        获取所有可用的评估器名称
        
        Returns:
            评估器名称列表
        """
        return list(cls._evaluators.keys())


# 示例用法:
# 
# 1. 定义一个具体的评估器

class RandomConsensusEvaluator(ConsensusEvaluator):
    def __init__(self, **kwargs):
        pass
    def evaluate_initial_responses(self, topic, response1, response2):
        return {
            "is_consensus": random.choice([True, False]),
        }
        
    def evaluate_final_responses(self, topic, response1, response2):
        return {
            "is_consensus": random.choice([True, False]),
        }
        
    def calculate_consensus_metrics(self, initial_metrics, final_metrics):
        return {
            "is_consensus": initial_metrics["is_consensus"] and final_metrics["is_consensus"],
            "consensus_score": random.uniform(0, 1),
        }
if __name__ == "__main__":
    # 2. 注册评估器
    ConsensusEvaluatorFactory.register("random", RandomConsensusEvaluator)

    # 3. 创建评估器并使用
    evaluator = ConsensusEvaluatorFactory.create("random")
    result = evaluator.evaluate_consensus(
        topic="Sample Topic",
        initial_response1="Initial Response 1",
        initial_response2="Initial Response 2",
        final_response1="Final Response 1",
        final_response2="Final Response 2"
    )
    print(result)
