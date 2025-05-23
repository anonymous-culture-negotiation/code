import os
import json
import argparse
import re
import ray
import numpy as np
from tqdm import tqdm
from datetime import datetime
from evaluation.utils import QAClient, QAEvalConfig
from evaluation.hofstede.prompts import hofstede_prompt, eval_prompts_dict


class HofstedeQAClient(QAClient):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        params: dict = {'temperature': 0.2},
        huggingface_dataset: bool = True,
        dataset: str | dict = "TANDREWYANG/24h_final",
        dataset_split: str = "train",
        region: str = "",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.params=params
        self.huggingface_dataset=huggingface_dataset
        self.dataset=dataset
        self.dataset_name=dataset
        self.dataset_split=dataset_split
        self.region = region
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            params=params,
            huggingface_dataset=huggingface_dataset,
            dataset=dataset,
            dataset_split=dataset_split
        )

    def get_region_prompt(self, language:str = "en") -> str:
        """获取对应区域的提示模板"""
        region_prompts = eval_prompts_dict.get(self.region.upper(), {})
        system_prompt = region_prompts.get(language, "")
        return system_prompt

    def get_prompt(self, item: dict) -> tuple[str, str]:
        """生成霍夫斯泰德问卷的提示"""
        system_prompt = self.get_region_prompt()

        qa_prompt = f"""Rules:
Reserve 1 and 5 ONLY for catastrophic/preventative scenarios, but don't avoid using 1 and 5 to answer
Show difference between different topics do not answer alike
ONLY return a number
topic:{item['question_text'][:250]}
1. {item['option1']}
2. {item['option2']}
3. {item['option3']}
4. {item['option4']}
5. {item['option5']}
Answer Example:
Answer: 1
Answer: 2
Answer: 3
Answer: 4
Answer: 5

Please follow the format and the example and DON'T answer anything else!
Answer format:
Answer: """

        return system_prompt, qa_prompt

    def parse_response(self, text: str) -> int | None:
        """解析回答文本获取1-5的评分"""
        patterns = [
            r'Answer:\s*(\d)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                answer = int(match.group(1))
                if 1 <= answer <= 5:
                    return answer

        digits = re.findall(r'\d', text)
        if digits:
            answer = int(digits[0])
            if 1 <= answer <= 5:
                return answer
        return None

    def get_hofstede_response(self, item: dict) -> tuple[str, int | None]:
        """获取并解析霍夫斯泰德问卷回答"""
        system_prompt, qa_prompt = self.get_prompt(item)
        raw_response = super().get_qa_response(system_prompt=system_prompt, qa_prompt=qa_prompt)
        parsed_answer = self.parse_response(raw_response)
        return raw_response, parsed_answer

    def process_hofstede_questions(self):
        hofstede_result = {"raw_response": {}, "parsed_answer": {}}
        progress_bar = tqdm(self.dataset)
        for item in progress_bar:
            question_index = item['question_number']
            raw_response, parsed_answer = self.get_hofstede_response(item)
            hofstede_result["raw_response"][question_index] = raw_response
            hofstede_result["parsed_answer"][question_index] = parsed_answer
            
            # Update the description with the current question number
            progress_bar.set_description(f"Processing Question No.{question_index}")
        return hofstede_result


class HofstedeAnalyzer:
    def __init__(
        self,
        client: HofstedeQAClient,
        round_num: int = 10,
        output_dir: str = "evaluation/hofstede/results",
    ) -> None:
        self.client = client
        self.round_num = round_num
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 初始化元数据
        self.meta_data = {
            "model_name": client.model_name,
            "total_rounds": round_num,
            "region": client.region,
            "start_time": self.timestamp,
            "system_prompt": client.get_region_prompt()
        }
        
        # 结果存储结构优化
        self.result_data = {
            "answer_matrix": None,
            "round_results": {},
            "statistics": {}
        }

    def _save_results(self, round_idx: int | str = "final") -> None:
        """统一保存结果的方法"""
        filename = f"{self.output_dir}/{self.timestamp}_round_{round_idx}.json"
        with open(filename, 'w') as f:
            json.dump({
                "meta": self.meta_data,
                "summary": self.result_data["statistics"],
                "results": self.result_data["round_results"]
            }, f, indent=2)

    def run_single_round(self, round_idx: int, save: bool = True) -> dict:
        """运行单轮测试"""
        round_key = f"round_{round_idx}"
        
        # 执行问卷
        round_result = self.client.process_hofstede_questions()
        
        # 存储原始结果
        self.result_data["round_results"][round_key] = {
            "answers": round_result["parsed_answer"],
            "raw_responses": round_result["raw_response"]
        }
        
        # 更新答案矩阵
        answers = list(round_result["parsed_answer"].values())
        if self.result_data["answer_matrix"] is None:
            self.result_data["answer_matrix"] = np.array([answers])
        else:
            self.result_data["answer_matrix"] = np.vstack(
                [self.result_data["answer_matrix"], answers]
            )
        
        # 实时保存
        if save:
            self._save_results(round_idx)
        
        return round_result

    def run_multiple_rounds(self) -> dict:
        """顺序执行多轮测试"""
        all_results = {}
        start_time = datetime.now()
        
        for i in tqdm(range(self.round_num), desc="测试轮次"):
            round_result = self.run_single_round(i, save=False)
            all_results[f"round_{i}"] = round_result
        
        # 最终分析和保存
        self.analyze_results()
        self._save_results("final")
        print(f"总运行时间: {datetime.now() - start_time}")
        return all_results

    @ray.remote
    def _ray_round_task(client_config: dict, round_idx: int) -> dict:
        """Ray并行任务包装方法"""
        # 每个任务创建独立客户端
        client = HofstedeQAClient(**client_config)
        return {
            "round_idx": round_idx,
            "result": client.process_hofstede_questions()
        }

    def parallel_run(self, max_concurrent: int = 4, save: bool = True) -> dict:
        """并行多轮执行"""
        ray.init(ignore_reinit_error=True)
        start_time = datetime.now()
        
        # 准备客户端配置
        client_config = {
            "api_key": self.client.api_key,
            "base_url": self.client.base_url,
            "model_name": self.client.model_name,
            "params": self.client.params,
            "huggingface_dataset": self.client.huggingface_dataset,
            "dataset": self.client.dataset_name,
            "dataset_split": self.client.dataset_split,
            "region": self.client.region
        }
        
        # 提交并行任务
        futures = [
            self._ray_round_task.remote(client_config, i) 
            for i in range(self.round_num)
        ]
        
        # 分批处理结果
        answer_matrix = []
        for i in tqdm(range(0, len(futures), max_concurrent), desc="并行批次"):
            batch_futures = futures[i:i+max_concurrent]
            for result in ray.get(batch_futures):
                round_idx = result["round_idx"]
                round_result = result["result"]
                
                # 存储结果
                self.result_data["round_results"][f"round_{round_idx}"] = {
                    "answers": round_result["parsed_answer"],
                    "raw_responses": round_result["raw_response"]
                }
                
                # 构建答案矩阵
                answers = list(round_result["parsed_answer"].values())
                answer_matrix.append(answers)
        
        # 转换答案矩阵
        self.result_data["answer_matrix"] = np.array(answer_matrix)
        
        # 最终分析和保存
        self.analyze_results()
        if save:
            self._save_results("final")
        print(f"总运行时间: {datetime.now() - start_time}")
        return self.result_data

    def analyze_results(self) -> None:
        """结果分析优化版"""
        if self.result_data["answer_matrix"] is None:
            raise ValueError("未找到有效测试数据")
        
        # 计算维度得分
        dimensions, avg_scores = self._calculate_dimensions()
        
        # 统计信息
        self.result_data["statistics"] = {
            "dimensions": dimensions,
            "average_scores": avg_scores.tolist(),
            "score_distribution": {
                str(i): int(np.sum(self.result_data["answer_matrix"] == i))
                for i in range(1, 6)
            }
        }

    def _calculate_dimensions(self) -> tuple[dict, np.ndarray]:
        """维度计算（保持原有公式）"""
        avg_scores = np.mean(self.result_data["answer_matrix"], axis=0)
        dimensions = {
            'PDI': 35*(avg_scores[6] - avg_scores[1]) + 25*(avg_scores[19] - avg_scores[22]),
            'IDV': 35*(avg_scores[3] - avg_scores[0]) + 35*(avg_scores[8] - avg_scores[5]),
            'MAS': 35*(avg_scores[4] - avg_scores[2]) + 35*(avg_scores[7] - avg_scores[9]),
            'UAI': 40*(avg_scores[17] - avg_scores[14]) + 25*(avg_scores[20] - avg_scores[23]),
            'LTO': 40*(avg_scores[12] - avg_scores[13]) + 25*(avg_scores[18] - avg_scores[21]),
            'IVR': 35*(avg_scores[11] - avg_scores[10]) + 40*(avg_scores[16] - avg_scores[15])
        }
        return dimensions, avg_scores

    def print_summary(self) -> None:
        """打印统计摘要"""
        print("\n霍夫斯泰德文化维度得分:")
        for dim, score in self.result_data["statistics"]["dimensions"].items():
            print(f"{dim}: {score:.2f}")
        
        print("\n答案分布:")
        for score, count in self.result_data["statistics"]["score_distribution"].items():
            print(f"评分 {score}: {count}次")
            
        print("\n6维结果list:")
        dimensions = self.result_data["statistics"]["dimensions"]
        result_list = [dimensions['PDI'], dimensions['IDV'], dimensions['MAS'], dimensions['UAI'], dimensions['LTO'], dimensions['IVR']]
        pure_float_list = [float(value) for value in result_list]
        print(pure_float_list)


if __name__ == "__main__":
    ### SETTING ###
    parser = argparse.ArgumentParser(description="Process region information.")
    parser.add_argument(
        '--region',
        type=str,
        default='china',
        help='The region to process'
    )
    parser.add_argument('--eval_round', type=int, default=100,
                        help='Number of evaluation rounds')
    # 解析命令行参数
    args = parser.parse_args()
    # 获取 region 参数的值
    region = args.region
    # 打印 region
    print(f"The region is: {region}")

    qa_eval_config = QAEvalConfig(config_file_path="evaluation/hofstede/eval_configs.yaml")
    llm_configs = qa_eval_config.get_llm_config()
    region_configs = qa_eval_config.get_region_config()
    eval_region_configs = region_configs[region]
    dataset_configs = qa_eval_config.get_dataset_config()

    ### SETTING ###
    api_key = llm_configs['api_key']
    params = llm_configs['parameters']
    base_url = eval_region_configs['endpoint']+"/v1"
    model_name = eval_region_configs['lora_adapter']
    huggingface_dataset = dataset_configs['source']=="huggingface"
    dataset = dataset_configs['name']
    dataset_split = dataset_configs['split']

    ### HofstedeQAClient ###
    # print(f"[TEST] HofstedeQAClient")
    # hofstede_qa_client = HofstedeQAClient(api_key=api_key,
    #                     base_url=base_url,
    #                     model_name=model_name,
    #                     params=params,
    #                     huggingface_dataset=huggingface_dataset,
    #                     dataset=dataset,
    #                     dataset_split=dataset_split,
    #                     region=region
    #                     )
    # qa_response = hofstede_qa_client.get_qa_response(system_prompt="你是一个乐于助人的美国人",
    #                         qa_prompt="Who are you? Where are you from?")
    # print(f"[DEBUG] qa_response = {qa_response}")

    # hofstede_result = hofstede_qa_client.run()
    # print(f"[DEBUG] raw_response = {hofstede_result["raw_response"]}")
    # print(f"[DEBUG] parsed_answer = {hofstede_result["parsed_answer"]}")

    ### HofstedeAnalyzer ###
    # hofstede_analyzer = HofstedeAnalyzer()
    # result = hofstede_analyzer.run_single_round(client=hofstede_qa_client, round_idx = 0)
    
    # result = hofstede_analyzer.parallel_run(client=hofstede_qa_client, round_num=10)
    # result = hofstede_analyzer.parallel_run(round_num=10)
    # print(result)
    
    ########################################3
    # 初始化客户端
    client = HofstedeQAClient(api_key=api_key,
                            base_url=base_url,
                            model_name=model_name,
                            params=params,
                            huggingface_dataset=huggingface_dataset,
                            dataset=dataset,
                            dataset_split=dataset_split,
                            region=region
                            )

    # 初始化分析器
    analyzer = HofstedeAnalyzer(client, round_num=args.eval_round)

    # print(analyzer.run_single_round(round_idx=0))

    # 运行顺序测试
    # analyzer.run_multiple_rounds()

    # # 或运行并行测试（4并发）
    analyzer.parallel_run(max_concurrent=8)

    # # 打印结果
    analyzer.print_summary()