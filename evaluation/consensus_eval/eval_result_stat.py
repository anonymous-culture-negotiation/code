import json
from abc import ABC, abstractmethod

class EvalResultStat(ABC):
    def __init__(self, result_path:str = ""):
        self.result_path = result_path
    
    def _load_eval_result_(self):
        """Load evaluation results"""
        if self.result_path == "":
            raise ValueError("Result path not set")
        try:
            with open(self.result_path, 'r', encoding='utf-8') as file:
                result = json.load(file)
                return result
        except FileNotFoundError:
            print(f"File not found: {self.result_path}")
            return None
        except json.JSONDecodeError:
            print(f"File is not a valid JSON format: {self.result_path}")
            return None
    
    def stat_result(self):
        """Process and analyze evaluation results"""
        pass
    
class PPLEvalResultStat(EvalResultStat):
    def stat_result(self):
        print(f"PPLEvalResultStat: {self.result_path}")
        
if __name__ == "__main__":
    PPL_eval_result_stat = PPLEvalResultStat()
    PPL_eval_result_stat.stat_result()