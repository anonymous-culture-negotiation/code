import re
import pandas as pd
import pyreadstat
import argparse
import os
from datetime import datetime
import json
import requests
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import time
from collections import defaultdict
import threading

class QuestionnaireProcessor:
    def __init__(self, output_path):
        self.output_path = output_path
        self.spss_path = output_path.replace('.json', '.sav')
        self.copied_count = 0
        
        # 初始化统计系统
        self.stats = defaultdict(int)
        self.error_log = []
        self.records = []
        self.total_count = 0
        self.success_count = 0
        self.print_lock = threading.Lock()
        
        # API配置
        self.api_config = {
            'url': "http://localhost:8001/v1/chat/completions",  # Updated URL
            'retry': {
                'max_retries': 10,
                'retry_delay': 2,
                'retry_codes': [500, 502, 503, 504],
                'timeout': (5,30)
            }
        }
        # 问题模板
        self.questions = {
            'Q46': "Please choose an integer from 1 to 4 to describe your current level of happiness. 1 means very happy, 4 means completely unhappy. range = (1,2,3,4)",
            'Q57': "In daily interactions, do you think most people are trustworthy? 1=trustworthy, 2=be careful, 3=extremely cautious. range = (1,2,3)",
            'Q45': "Is more respect for authority a positive change? 1=positive, 2=neutral, 3=negative. range = (1,2,3)",
            'Q209': "Have you signed a political petition? 1=yes, 2=maybe, 3=never. range = (1,2,3)",
            'Q164': "Importance of God in your life (1=not important - 10=extremely important). range = (1,2,3,4,5,6,7,8,9,10)",
            'Q182': "Acceptance of homosexuality (1=never acceptable - 10=always acceptable). range = (1,2,3,4,5,6,7,8,9,10)",
            'Q184': "Acceptance of abortion (1=never acceptable - 10=always acceptable). range = (1,2,3,4,5,6,7,8,9,10)",
            'Q27': "Pride in nationality: 1=very proud, 2=so-so, 3=not proud. range = (1,2,3)",
            'Y002': "Materialism attitude: 1=materialist, 2=mixed, 3=post-materialist, 4=other. range = (1,2,3,4)",
            'Y003': "Autonomy index (0=fully autonomous - 4=not free). range = (0,1,2,3,4)"
        }
        
        # 生成参数组合
        self.demographics = {
            'marital_status': ['single', 'married'],
            'sex': ['male', 'female'],
            'age': ['teenager', 'middle-age', 'senior'],
            'education': ['high school', 'college'],
            'social_class': ['proletariat', 'middle class', 'affluent class']
        }

    def _safe_print(self, message, is_error=False):
        """线程安全打印方法"""
        with self.print_lock:
            if is_error:
                print(f"\n\033[91m[ERROR] {message}\033[0m")  # 红色错误信息
            else:
                print(f"\n\033[92m[SUCCESS] {message}\033[0m")  # 绿色成功信息

    def generate_params(self):
        params = []
        for m in self.demographics['marital_status']:
            for s in self.demographics['sex']:
                for a in self.demographics['age']:
                    for e in self.demographics['education']:
                        for sc in self.demographics['social_class']:
                            params.append((s, a, e, sc, m))
        return params

    def _call_api(self, system_prompt, user_prompt):
        """增强版API调用，带详细错误处理"""
        for i in range(self.api_config['retry']['max_retries']):
            try:
                response = requests.post(
                    self.api_config['url'],
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": "./models/base_model/llama3.3-70b-instruct",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.7,  # 添加温度参数控制随机性
                        "max_tokens": 50     # 限制响应长度
                    },
                    timeout=self.api_config['retry']['timeout']
                )
                
                # 增强响应验证
                if response.status_code != 200:
                    raise requests.HTTPError(f"API返回非200状态码: {response.status_code}")
                    
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("API返回无效的JSON格式")
                    
                # 深度解析响应结构
                choices = data.get("choices", [])
                if not choices:
                    raise ValueError("API响应中缺少choices字段")
                    
                message = choices[0].get("message", {})
                if not message:
                    raise ValueError("API响应中缺少message字段")
                    
                content = message.get("content", "").strip()
                if not content:
                    raise ValueError("API返回空内容")
                    
                return content
                
            except requests.RequestException as e:
                if i == self.api_config['retry']['max_retries'] - 1:
                    raise
                time.sleep(self.api_config['retry']['retry_delay'] * (i+1))
            except json.JSONDecodeError:
                raise ValueError("API返回无效的JSON数据")
            except Exception as e:
                if i == self.api_config['retry']['max_retries'] - 1:
                    raise
                time.sleep(self.api_config['retry']['retry_delay'] * (i+1))
        
        return None

    def _extract_answer(self, question_id, text):
        """增强型答案解析，带详细错误日志"""
        if not text:
            self.error_log.append({
                'type': 'EmptyResponse',
                'question_id': question_id,
                'details': 'API返回空响应'
            })
            return None
        
        try:
            # 增强正则表达式匹配
            patterns = {
                'default': r'(?:answer|选择|答案)[：:\s]*(\d+)',
                'Y003': r'(?:answer|选择|答案)[：:\s]*([0-4])'
            }
            
            pattern = patterns.get(question_id, patterns['default'])
            match = re.search(pattern, text, re.IGNORECASE)
            
            if not match:
                self.error_log.append({
                    'type': 'PatternMismatch',
                    'question_id': question_id,
                    'details': f"未找到匹配模式，原始响应: {text[:200]}",
                    'pattern': pattern
                })
                return None
            
            value = int(match.group(1))
            
            # 答案范围验证
            ranges = {
                'Q46': (1,4), 'Q57': (1,3), 'Q45': (1,3),
                'Q209': (1,3), 'Q164': (1,10), 'Q182': (1,10),
                'Q184': (1,10), 'Q27': (1,3), 'Y002': (1,4),
                'Y003': (0,4)
            }
            
            min_val, max_val = ranges[question_id]
            if not (min_val <= value <= max_val):
                self.error_log.append({
                    'type': 'ValueOutOfRange',
                    'question_id': question_id,
                    'details': f"值{value}超出范围({min_val}-{max_val})",
                    'response': text[:200]
                })
                return None
            
            # 特殊处理Y003问题
            if question_id == 'Y003':
                return value - 2
                
            return value
            
        except Exception as e:
            self.error_log.append({
                'type': 'ExtractionError',
                'question_id': question_id,
                'details': str(e),
                'response': text[:200]
            })
            return None

    def _process_params(self, params):
        """增强版参数处理，带问题级重试"""
        sex, age, education, social_class, marital_status = params
        record = {
            'params': params,
            'responses': {},
            'raw_responses': {},
            'errors': [],
            'start_time': datetime.now().isoformat(),
            'end_time': None
        }
        
        # 为每个问题设置独立的重试机制
        for qid, qtext in self.questions.items():
            question_success = False
            last_error = None
          
            for attempt in range(3):  # 每个问题最多尝试3次
                try:
# 你作为儒家文化代表，坚持集体主义价值观，强调以下原则：
# - 社会和谐高于个人利益
# - 政府有道德责任保护群体安全
# - 个人对家庭和社区负有义务  
#                     system_prompt = f"""你是一位{age}的{sex}，{marital_status}，拥有{education}教育背景，来自{social_class}, 是中国人。
# 请严格按照要求回答问题，只返回数字答案，不要添加任何解释。"""

#                     system_prompt = f"""你是一位{age}的{sex}，{marital_status}，拥有{education}教育背景，来自{social_class}, 是美国人。
# 请严格按照要求回答问题，只返回数字答案，不要添加任何解释。"""

                    system_prompt = f"""你是一位{age}的{sex}，{marital_status}，拥有{education}教育背景，来自{social_class}, 是无国籍人士。你作为中立的价值观代表，坚持中立原则。
请严格按照要求回答问题，只返回数字答案，不要添加任何解释。"""
                    
                    user_prompt = f"""请从给定选项中选择一个数字回答：
                    {qtext}
                    答案格式必须严格遵循：
                    answer：<数字>
                    例如：answer：1"""
                    
                    raw_response = self._call_api(system_prompt, user_prompt)
                    
                    if raw_response is None:
                        raise ValueError("API调用失败，返回空响应")
                    
                    value = self._extract_answer(qid, raw_response)
                    if value is None:
                        raise ValueError("无法从响应中提取有效答案")
                    
                    # 如果成功，保存结果并跳出重试循环
                    record['responses'][qid] = value
                    record['raw_responses'][qid] = raw_response
                    question_success = True
                    break
                    
                except Exception as e:
                    last_error = {
                        'attempt': attempt + 1,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    time.sleep(1)  # 重试前短暂等待
            
            # 如果问题处理失败，记录错误
            if not question_success and last_error:
                last_error.update({
                    'question_id': qid,
                    'final_attempt': True
                })
                record['errors'].append(last_error)
        
        # 如果有成功回答的问题，保存到SPSS
        if record['responses']:
            try:
                self._save_to_spss(record['responses'], params)
                self.success_count += 1
                success_msg = f"参数 {params} - 成功保存 {len(record['responses'])}/{len(self.questions)} 个答案"
                self._safe_print(success_msg)
            except Exception as e:
                record['errors'].append({
                    'type': 'SPSS_Save_Error',
                    'error': str(e)
                })
        
        record['end_time'] = datetime.now().isoformat()
        self.records.append(record)
        return record

    def _save_to_spss(self, responses, params):
        """保存到SPSS文件（每个样本复制40次）"""
        try:
            data = responses.copy()
            data.update({
                'sex': params[0],
                'age': params[1],
                'education': params[2],
                'social_class': params[3],
                'marital_status': params[4],
                'C_COW_ALPHA': 'CNC' # LLC, CNC, USC
            })
            
            df = pd.DataFrame([data] * 40)
            
            if os.path.exists(self.spss_path):
                existing = pd.read_spss(self.spss_path)
                df = pd.concat([existing, df], ignore_index=True)
            
            pyreadstat.write_sav(df, self.spss_path)
            self.copied_count += 40
            print(f"已保存 {self.copied_count} 条数据", end='\r')
        
        except Exception as e:
            raise RuntimeError(f"SPSS保存失败: {str(e)}") from e

    def _save_results(self, start_time, end_time):
        """保存结构化结果"""
        result = {
            'metadata': {
                'total_parameters': self.total_count,
                'successful_parameters': self.success_count,
                'success_rate': self.success_count / self.total_count if self.total_count > 0 else 0,
                'processing_start': start_time.isoformat(),
                'processing_end': end_time.isoformat(),
                'processing_duration': (end_time - start_time).total_seconds(),
                'spss_records_generated': self.copied_count
            },
            'statistics': {
                'demographic_distribution': {
                    'marital_status': defaultdict(int),
                    'sex': defaultdict(int),
                    'age': defaultdict(int),
                    'education': defaultdict(int),
                    'social_class': defaultdict(int)
                },
                'error_distribution': defaultdict(int)
            },
            'records': self.records,
            'errors': self.error_log
        }
        
        for record in self.records:
            if not record['errors']:
                params = record['params']
                result['statistics']['demographic_distribution']['marital_status'][params[4]] += 1
                result['statistics']['demographic_distribution']['sex'][params[0]] += 1
                result['statistics']['demographic_distribution']['age'][params[1]] += 1
                result['statistics']['demographic_distribution']['education'][params[2]] += 1
                result['statistics']['demographic_distribution']['social_class'][params[3]] += 1
        
        for error in self.error_log:
            result['statistics']['error_distribution'][error['error_type']] += 1
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def run(self):
        """主执行流程"""
        start_time = datetime.now()
        params_list = self.generate_params()
        self.total_count = len(params_list)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self._process_params, p) for p in params_list]
            
            with tqdm(total=self.total_count, desc="Processing",position=0) as pbar:
                for future in futures:
                    future.result()
                    pbar.update(1)
        
        end_time = datetime.now()
        self._save_results(start_time, end_time)
        print(f"\nCompleted: {self.success_count * 40} 条有效数据（{self.success_count} 个原始样本 ×40）")
        print(f"SPSS文件：{self.spss_path}")
        print(f"完整日志：{self.output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    region = "qwen"
    parser.add_argument('--output', default=f'output/evaluation/wvs/questionnaire_results_8000_{region}_without_systemprompt.json')
    args = parser.parse_args()
    # processor = QuestionnaireProcessor(args.output)
    # processor.run()

    # 单一结果文件路径
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    RESULTS_FILE = os.path.join("output/evaluation/wvs/", f'wvs_results_{"llama"}_{"china"}_{current_time}.json')
    processor = QuestionnaireProcessor(RESULTS_FILE)
    processor.run()