import random
from typing import Any, Dict
from evaluation.consensus_eval.consensus_evaluator import ConsensusEvaluatorFactory
from evaluation.consensus_eval.consensus_evaluator import ConsensusEvaluator


class PPLConsensusEvaluator(ConsensusEvaluator):
    def __init__(self, **kwargs):
        """
        初始化评估器，接收两个配置字典
        参数:
            config1: 第一个配置字典，包含API密钥、基础URL和模型名称
            config2: 第二个配置字典，包含API密钥、基础URL和模型名称
        """
        self.config1 = kwargs.get('config1')
        self.config2 = kwargs.get('config2')

        if not self.config1 or not self.config2:
            raise ValueError("Both 'config1' and 'config2' must be provided as keyword arguments.")
        
        self.count_less_than_one = 0
        self.total_count = 0
        self.proportion_less_than_one = 0
        self.distance_reduce_less_than_one = 0
        self.distance_reduce = 0

    @staticmethod
    def calculate_response_ppl(api_key: str, base_url: str, model: str, message: str) -> float:
        """
        计算指定response的Perplexity（PPL）
        参数:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 使用的模型名称
            message: 需要计算PPL的文本内容
        返回:
            PPL值（若计算失败返回-1）
        """
        import math
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        max_retries = 5  # 最大重试次数
        attempt = 0
        
        while attempt < max_retries:
            try:
                # 通过API获取response的logprobs（需模型生成指定内容）
                response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {
                                    "role": "user",
                                    "content": (
                                        f"Your task is to repeat the following text exactly as it is. "
                                        f"Do not change, add, or omit any words or punctuation. "
                                        f"Here is the text: <text>{message}</text>"
                                    )
                                }
                            ],
                            logprobs=True,          # 启用对数概率输出
                            top_logprobs=5,         # 返回每个位置的前5个候选 token 概率
                            temperature=0,          # 关闭随机性，保证概率确定性（可选）
                            max_tokens=2000
                        )

                # 验证生成结果是否匹配
                generated_text = response.choices[0].message.content
                if generated_text.strip() == message.strip():
                    # 提取所有token的logprob
                    logprobs = [token.logprob for token in response.choices[0].logprobs.content]
                    
                    # 计算平均对数概率
                    total_logprob = sum(logprobs)
                    avg_logprob = total_logprob / len(logprobs)
                    return math.exp(-avg_logprob)
                else:
                    print(f"生成内容不匹配：\n<message>{message}</message>\n<generated_text>{generated_text}</generated_text>")
                    
            except Exception as e:
                print(f"API调用失败：{str(e)}")
            
            attempt += 1
            print(f"重试第 {attempt} 次...")
        
        return -1

    def cross_evaluate_responses(self, response1, response2) -> dict:
        """
        通用的评估方法，用于初始和最终响应的评估
        """
        if not self.config1 or not self.config2:
            raise ValueError("Both 'config1' and 'config2' must be provided as keyword arguments.")
        PPL_response1 = self.calculate_response_ppl(
            api_key=self.config2['api_key'],
            base_url=self.config2['base_url'], 
            model=self.config2['model'], 
            message=response1
        )
        PPL_response2 = self.calculate_response_ppl(
            api_key=self.config1['api_key'],
            base_url=self.config1['base_url'], 
            model=self.config1['model'], 
            message=response2
        )
        return {
            "PPL_response1": PPL_response1,
            "PPL_response2": PPL_response2,
            "PPL_distance": abs(PPL_response1-PPL_response2)
        }

    def evaluate_initial_responses(self, topic, response1, response2) -> dict:
        metrics = self.cross_evaluate_responses(response1, response2)
        return {
            "is_consensus": random.choice([True, False]),
            "PPL_init_response1": metrics["PPL_response1"],
            "PPL_init_response2": metrics["PPL_response2"],
            "PPL_init_distance": metrics["PPL_distance"]
        }

    def evaluate_final_responses(self, topic, response1, response2) -> dict:
        metrics = self.cross_evaluate_responses(response1, response2)
        return {
            "is_consensus": random.choice([True, False]),
            "PPL_final_response1": metrics["PPL_response1"],
            "PPL_final_response2": metrics["PPL_response2"],
            "PPL_final_distance": metrics["PPL_distance"]
        }

    def calculate_consensus_metrics(self, initial_metrics, final_metrics):
        if any(v == -1 for v in initial_metrics.values()) or any(v == -1 for v in final_metrics.values()):
            formatted_difference = None
        else:
            formatted_difference = final_metrics['PPL_final_distance'] / initial_metrics['PPL_init_distance']

        return {
            "is_consensus": initial_metrics["is_consensus"] and final_metrics["is_consensus"],
            "consensus_score": {
                "initial_metrics": initial_metrics,
                "final_metrics": final_metrics,
                "PPL_distance_difference": formatted_difference
            },
        }
    
    def result_statistic(self):
        try:
            print(f"[total_count]: {self.total_count}")
            print(f"[count_less_than_one]: {self.count_less_than_one}")
            self.proportion_less_than_one = self.count_less_than_one / self.total_count if self.total_count > 0 else 0
            print(f"[proportion_less_than_one]: {self.proportion_less_than_one*100}%")
            print(f"[avg distance_reduce]: {self.distance_reduce/self.total_count*100}%")
            print(f"[avg distance_reduce_less_than_one]: {self.distance_reduce_less_than_one/self.count_less_than_one*100}%")
        except Exception as e:
            print(f"{str(e)}")
        
    def evaluate_consensus(self, topic:str, 
                          initial_response1: Any, 
                          initial_response2: Any,
                          final_response1: Any, 
                          final_response2: Any) -> Dict[str, float]:
        initial_metrics = self.evaluate_initial_responses(topic, initial_response1, initial_response2)
        final_metrics = self.evaluate_final_responses(topic, final_response1, final_response2)
        consensus_metrics = self.calculate_consensus_metrics(initial_metrics, final_metrics)
        
        # 统计formatted_difference < 1的数量和比例
        if consensus_metrics["consensus_score"]["PPL_distance_difference"] is not None:
            self.total_count += 1
            self.distance_reduce += consensus_metrics["consensus_score"]["PPL_distance_difference"]
            if consensus_metrics["consensus_score"]["PPL_distance_difference"] < 1:
                self.count_less_than_one += 1
                self.distance_reduce_less_than_one += consensus_metrics["consensus_score"]["PPL_distance_difference"]
    
        self.result_statistic()
        
        return consensus_metrics


if __name__ == "__main__":
    # 2. 注册评估器
    ConsensusEvaluatorFactory.register("PPL", PPLConsensusEvaluator)

    # 3. 创建评估器并使用
    config = {
        'config1':{
        'api_key': 'your-api-key-1',
        'base_url': '',
        'model': ''
        },
        'config2': {
            'api_key': 'your-api-key-2',
            'base_url': '',
            'model': ''
        }
    }
    evaluator = ConsensusEvaluatorFactory.create("PPL", config = config)
    result = evaluator.evaluate_consensus(
        topic="Sample Topic",
        initial_response1="Initial Response 1",
        initial_response2="Initial Response 2",
        final_response1="Final Response 1",
        final_response2="Final Response 2"
    )
    print(result)