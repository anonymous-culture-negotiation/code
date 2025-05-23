import os
import re
import json
import yaml
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description="区域观点数据增广流水线")
    parser.add_argument("--step1", action='store_true', help="运行步骤1: 数据扩展")
    parser.add_argument("--step2", action='store_true', help="运行步骤2: 数据增强")
    parser.add_argument("--step3", action='store_true', help="运行步骤3: 价值观筛选")
    parser.add_argument("--region", choices=["China", "United States", "Denmark", "Spain", "Thailand", "Russia", "Mexico", "Iraq"], required=True)
    parser.add_argument("--use_region_param", action='store_true', help="使用region prompt或者Culture type prompt")
    parser.add_argument("--platform", choices=["openai", "siliconflow", "bean"], default="bean")
    parser.add_argument("--model", type=str, help="指定模型名称")
    parser.add_argument("--sample_num", type=int, default=10, help="每项问题扩展的样本数量")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--use_ray", action="store_true", help="是否使用Ray进行并行处理")
    parser.add_argument("--num_cpus", type=int, default=None, help="Ray并行使用的CPU核心数") # nproc
    parser.add_argument("--batch_size", type=int, default=None, help="批量大小")
    parser.add_argument("--max_concurrent_apis", type=int, default=32, help="API调用并发数量")
    parser.add_argument("--max_retries", type=int, default=3, help="API调用失败重试次数")
    return parser.parse_args()

# 文件读写函数
def load_jsonl(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def save_jsonl(path: str, data: Union[Dict, List]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    if isinstance(data, dict):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    elif isinstance(data, list):
        with open(path, 'a', encoding='utf-8') as f:
            for data_item in data:
                f.write(json.dumps(data_item, ensure_ascii=False) + "\n")

# 加载文化类型
def load_culture_type(region: str) -> str:
    with open("script_finetune/model_region.yaml", "r", encoding="utf-8") as file:
        regions_data = yaml.safe_load(file)
    for region_data in regions_data:
        for country in region_data["countries"]:
            if country["name"].lower() == region.lower():
                return region_data['type']
    raise ValueError(f"未找到区域 {region} 对应的文化类型")

# 提取标签内容
def extract_tag_content(text, tag):
    pattern = f"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

# 提取QA内容
def extract_qa(response: str) -> dict:
    question = extract_tag_content(response, "Question")
    answer = extract_tag_content(response, "Answer")
    CulturalConsistencyCheck = extract_tag_content(response, "CulturalConsistencyCheck")
    return {
        "question": question,
        "answer": answer,
        "CulturalConsistencyCheck": CulturalConsistencyCheck,
    }

# 提取一致性判断结果
def extract_consistency_result(response: str) -> dict:
    # judge = extract_tag_content(response, "Judge")
    # analysis = extract_tag_content(response, "ConsistencyAnalysis")
    # reason = extract_tag_content(response, "Reason")
    # return {
    #     "judge": judge,
    #     "analysis": analysis,
    #     "reason": reason,
    # }
    judge = extract_tag_content(response, "Judge")
    score_card = extract_tag_content(response, "ScoreCard")
    overall_assessment = extract_tag_content(response, "OverallAssessment")
    improvement_suggestions = extract_tag_content(response, "ImprovementSuggestions")
    analysis = {"score_card": score_card, 
                "improvement_suggestions": improvement_suggestions}
    reason = {"overall_assessment": overall_assessment}
    return {
        "judge": judge,
        "analysis": analysis,
        "reason": reason,
    }

# API调用函数
def get_response(messages: List[Dict], config, max_retries=3):
    for attempt in range(max_retries):
        try:
            if config.platform == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=config.api_key, base_url=config.base_url)
                response = client.chat.completions.create(
                    model=config.model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=3000
                )
                # print(f"[DEBUG] {response}")
                return response.choices[0].message.content
            else:
                # 使用URL请求方式
                import requests
                url = f"{config.base_url}/v1/chat/completions"
                payload = {
                    "model": config.model,
                    "messages": messages,
                    "stream": False,
                    "max_tokens": 3000,
                    "temperature": 0.2,
                    "response_format": {"type": "text"}
                }
                headers = {
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
                else:
                    print(f"API调用失败，状态码: {response.status_code}")
                    print(f"错误信息: {response.text}")
        except Exception as e:
            print(f"API调用异常: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避策略
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("已达到最大重试次数，调用失败")
                return None
    return None