import json
import os
from typing import Dict, List
from pathlib import Path
from tqdm import tqdm
from datasets import load_dataset

from config import CACHE_PATH, RAW_PATH, ensure_dirs  # 添加 RAW_PATH
from utils import save_jsonl

class DataExtensionProcessor:
    def __init__(self, region: str, sample_num: int):
        self.region = region
        self.sample_num = sample_num
        self.output_path = CACHE_PATH / f"{region}.jsonl"
        self.raw_data_path = RAW_PATH / f"{region}.jsonl"  # 新增原始数据保存路径
        ensure_dirs()
        
    def process(self):
        """执行数据扩展处理"""
        print(f"开始处理区域 '{self.region}' 的数据扩展...")
        
        # 检查输出文件是否已存在，若存在则先删除
        if os.path.exists(self.output_path):
            os.remove(self.output_path)
            
        # 检查原始数据文件是否已存在，若存在则先删除
        if os.path.exists(self.raw_data_path):
            os.remove(self.raw_data_path)
            
        # 加载数据集
        ds = load_dataset("Anthropic/llm_global_opinions", trust_remote_code=True)
        
        # 遍历并处理数据
        processed_count = 0
        raw_count = 0
        for idx, entry in enumerate(tqdm(ds['train'])):  # type: ignore
            # 只处理 source 字段值为 'WVS'（大小写不敏感）的数据
            if entry['source'].lower() != 'wvs':
                continue
                
            # 获取 selections 数据
            selections = entry.get('selections', {})
            if isinstance(selections, str):
                try:
                    import ast
                    selections = selections.replace("defaultdict(<class 'list'>, ", "").rstrip(")")
                    selections = ast.literal_eval(selections)
                except Exception as e:
                    print(f"解析 selections 失败: {e}")
                    continue
                    
            # 只处理当前region的数据
            if self.region not in selections:
                continue
                
            # 处理选项和选择数据
            options = eval(entry.get("options"))  # type: ignore
            values = selections[self.region]
            
            # 排序选项和选择数据
            combined = list(zip(options, values))
            combined_sorted = sorted(combined, key=lambda x: x[0])
            options_sorted, selections_sorted = zip(*combined_sorted)
            
            # 保存原始数据
            raw_data = {
                "llm_global_opinion_index": idx,
                "source": entry.get("source"),
                "question": entry.get("question"),
                "options": list(options_sorted),
                "selections": list(selections_sorted)
            }
            save_jsonl(str(self.raw_data_path), raw_data)
            raw_count += 1
            
            # 计算目标数量
            target_counts = self._calculate_target_counts(selections_sorted)
            
            # 生成扩展的QA对
            qa_pairs = self._generate_qa_pairs(
                idx, entry["source"], entry["question"], 
                options_sorted, selections_sorted, target_counts
            )
            
            # 保存结果
            save_jsonl(str(self.output_path), qa_pairs)
            processed_count += len(qa_pairs)
            
        print(f"原始数据保存完成，共保存 {raw_count} 条记录，保存至 {self.raw_data_path}")
        print(f"数据扩展完成，共生成 {processed_count} 个QA对，保存至 {self.output_path}")
        
    def _calculate_target_counts(self, selections: list) -> Dict[int, int]:
        """根据selections比例计算各选项的目标数量"""
        total = sum(selections)
        if total == 0:
            return {i: 0 for i in range(len(selections))}
            
        normalized = [s/total for s in selections]
        target_counts = {i: int(round(n * self.sample_num)) 
                         for i, n in enumerate(normalized)}
        
        # 处理四舍五入导致的样本数不足问题
        diff = self.sample_num - sum(target_counts.values())
        if diff > 0:
            # 将差值加到最大的选项上
            max_idx = max(target_counts, key=target_counts.get)
            target_counts[max_idx] += diff
        return target_counts
        
    def _generate_qa_pairs(self, idx: int, source: str, question: str, 
                          options: List, selections: List, 
                          target_counts: Dict[int, int]) -> List[Dict]:
        """生成QA对"""
        qa_pairs = []
        qa_index = 0
        
        for opt_idx, count in target_counts.items():
            for _ in range(count):
                qa_pairs.append({
                    "llm_global_opinion_index": idx,
                    "qa_index": qa_index,
                    "source": source,
                    "question": question,
                    "option": options[opt_idx],
                    "target_ratio": count/self.sample_num,
                    "original_ratio": selections[opt_idx]/sum(selections) if sum(selections) > 0 else 0
                })
                qa_index += 1
                
        return qa_pairs