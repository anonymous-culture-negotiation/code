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
import yaml
import sys

class QuestionnaireConfig:
    def __init__(self, config_path, model_name):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.validate_config(model_name)

    def validate_config(self, model_name):
        """Validate required configuration structure and fields"""
        if not isinstance(self.config, dict):
            raise ValueError("Configuration must be a dictionary")

        if model_name not in self.config:
            available_models = list(self.config.keys())
            raise ValueError(
                f"Model '{model_name}' not found in config. Available models: {available_models}"
            )

        model_config = self.config[model_name]
        required_fields = ['endpoint', 'base_model']
        missing_fields = [f for f in required_fields if f not in model_config]
        
        if missing_fields:
            raise ValueError(
                f"Model '{model_name}' missing required fields: {missing_fields}"
            )
        
        # Set default values for optional fields
        if 'lora_adapter' not in model_config:
            model_config['lora_adapter'] = None
        if 'system_prompt_type' not in model_config:
            model_config['system_prompt_type'] = None


class QuestionnaireProcessor:
    def __init__(self, config, model_name, output_path):
        self.config = config
        self.model_name = model_name
        self.model_cfg = self.config.config[model_name]
        self.output_path = output_path
        self.spss_path = output_path.replace('.json', '.sav')
        self.copied_count = 0
        
        # Initialize statistics
        self.stats = defaultdict(int)
        self.error_log = []
        self.records = []
        self.total_count = 0
        self.success_count = 0
        self.print_lock = threading.Lock()
        
        # Initialize API configuration
        self.setup_api_config()
        
        # Initialize questions and demographics
        self.setup_questions()
        self.setup_demographics()

    def setup_api_config(self):
        """Initialize API configuration from config file"""
        self.api_config = {
            'url': self.model_cfg['endpoint'] + "/v1/chat/completions",
            'retry': {
                'max_retries': 10,
                'retry_delay': 2,
                'retry_codes': [500, 502, 503, 504],
                'timeout': (5, 30)
            },
            'model': self.model_cfg['lora_adapter'] or self.model_cfg['base_model'],
            'headers': {"Content-Type": "application/json"}
        }

    def setup_questions(self):
        """Initialize question templates"""
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

    def setup_demographics(self):
        """Initialize demographic parameters"""
        self.demographics = {
            'marital_status': ['single', 'married'],
            'sex': ['male', 'female'],
            'age': ['teenager', 'middle-age', 'senior'],
            'education': ['illiterate','high school', 'college'],
            'social_class': ['proletariat', 'middle class', 'affluent class']
        }

    def _safe_print(self, message, is_error=False):
        """Thread-safe printing method"""
        with self.print_lock:
            if is_error:
                print(f"\n\033[91m[ERROR] {message}\033[0m")  # Red for errors
            else:
                print(f"\n\033[92m[SUCCESS] {message}\033[0m")  # Green for success

    def generate_params(self):
        """Generate all demographic parameter combinations"""
        params = []
        for m in self.demographics['marital_status']:
            for s in self.demographics['sex']:
                for a in self.demographics['age']:
                    for e in self.demographics['education']:
                        for sc in self.demographics['social_class']:
                            params.append((s, a, e, sc, m))
        return params

    def _call_api(self, system_prompt, user_prompt):
        """Enhanced API call with detailed error handling"""
        for i in range(self.api_config['retry']['max_retries']):
            try:
                response = requests.post(
                    self.api_config['url'],
                    headers=self.api_config['headers'],
                    json={
                        "model": self.api_config['model'],
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 50
                    },
                    timeout=self.api_config['retry']['timeout']
                )
                
                if response.status_code != 200:
                    raise requests.HTTPError(f"API returned non-200 status: {response.status_code}")
                    
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("API returned invalid JSON format")
                    
                choices = data.get("choices", [])
                if not choices:
                    raise ValueError("API response missing 'choices' field")
                    
                message = choices[0].get("message", {})
                if not message:
                    raise ValueError("API response missing 'message' field")
                    
                content = message.get("content", "").strip()
                if not content:
                    raise ValueError("API returned empty content")
                    
                return content
                
            except requests.RequestException as e:
                if i == self.api_config['retry']['max_retries'] - 1:
                    raise
                time.sleep(self.api_config['retry']['retry_delay'] * (i+1))
            except json.JSONDecodeError:
                raise ValueError("API returned invalid JSON data")
            except Exception as e:
                if i == self.api_config['retry']['max_retries'] - 1:
                    raise
                time.sleep(self.api_config['retry']['retry_delay'] * (i+1))
        
        return None

    def _extract_answer(self, question_id, text):
        """Parse API response with detailed error logging"""
        if not text:
            self.error_log.append({
                'type': 'EmptyResponse',
                'question_id': question_id,
                'details': 'API returned empty response'
            })
            return None
        
        try:
            match = re.search(r'Answer:\s*(\d+)', text, re.IGNORECASE)
            
            if not match:
                self.error_log.append({
                    'type': 'PatternMismatch',
                    'question_id': question_id,
                    'details': f"No Answer pattern found, raw response: {text[:200]}",
                    'pattern': 'Answer:\s*(\d+)'
                })
                return None
            
            value = int(match.group(1))
            
            # Answer range validation
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
                    'details': f"Value {value} out of range ({min_val}-{max_val})",
                    'response': text[:200]
                })
                return None
            
            # Special handling for Y003 question
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
        """增强版参数处理，带问题级重试和实时进度显示"""
        sex, age, education, social_class, marital_status = params
        record = {
            'params': params,
            'responses': {},
            'raw_responses': {},
            'errors': [],
            'start_time': datetime.now().isoformat(),
            'end_time': None
        }
        
        # 创建问题进度条
        with tqdm(total=len(self.questions), desc=f"处理参数 {params}", leave=False) as q_pbar:
            # 为每个问题设置独立的重试机制
            for qid, qtext in self.questions.items():
                question_success = False
                last_error = None
                
                for attempt in range(3):  # 每个问题最多尝试3次
                    try:
                        system_prompt = f"""You are a {age} {sex}, {marital_status}, with {education} education background, from {social_class}. 
Please strictly follow the requirements to answer questions, only return numerical answers, and do not add any explanations."""
                        
                        user_prompt = f"""Please choose a number from the given options to answer:
{qtext}
The answer format must strictly follow:
Answer: <number>
For example: Answer: 1"""
                        
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
                
                # 更新问题进度条
                q_pbar.update(1)
                q_pbar.set_postfix_str(f"最新问题: {qid}")
                
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
        """Save to SPSS file (40 copies per sample)"""
        try:
            data = responses.copy()
            data.update({
                'sex': params[0],
                'age': params[1],
                'education': params[2],
                'social_class': params[3],
                'marital_status': params[4],
                'C_COW_ALPHA': 'CNC'
            })
            
            df = pd.DataFrame([data] * 40)
            
            if os.path.exists(self.spss_path):
                existing = pd.read_spss(self.spss_path)
                df = pd.concat([existing, df], ignore_index=True)
            
            pyreadstat.write_sav(df, self.spss_path)
            self.copied_count += 40
            print(f"Saved {self.copied_count} records", end='\r')
        
        except Exception as e:
            raise RuntimeError(f"SPSS save failed: {str(e)}") from e

    def _save_results(self, start_time, end_time):
        """Save structured results"""
        result = {
            'metadata': {
                'model_name': self.model_name,
                'base_model': self.model_cfg['base_model'],
                'lora_adapter': self.model_cfg['lora_adapter'],
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
            result['statistics']['error_distribution'][error['type']] += 1
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def run(self):
        """主执行流程"""
        start_time = datetime.now()
        params_list = self.generate_params()
        self.total_count = len(params_list)
        
        # 主进度条
        with tqdm(total=self.total_count, desc="总进度", position=0) as main_pbar:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for p in params_list:
                    future = executor.submit(self._process_params, p)
                    future.add_done_callback(lambda _: main_pbar.update(1))
                    futures.append(future)
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
        
        end_time = datetime.now()
        self._save_results(start_time, end_time)
        print(f"\nCompleted: {self.success_count * 40} 条有效数据（{self.success_count} 个原始样本 ×40）")
        print(f"SPSS文件：{self.spss_path}")
        print(f"完整日志：{self.output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="World Values Survey Questionnaire Processor")
    parser.add_argument('--config', type=str, default="evaluation/configs.yaml",
                       help='Path to the YAML configuration file')
    parser.add_argument('--model', type=str, required=True,
                       help='Name of the model to use (must be defined in config)')
    parser.add_argument('--output', type=str,
                       default='/home/daijuntao/jiawei/ValueDebate/evaluation/questionnaire_results_iraq.json',
                       help='Output file path')
    args = parser.parse_args()

    # Generate output path based on model name
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output.replace('.json', f'_{args.model}_{current_time}.json')
    
    try:
        # Load configuration
        config = QuestionnaireConfig(args.config, args.model)
        
        # Initialize and run processor
        processor = QuestionnaireProcessor(config, args.model, output_path)
        processor.run()
        
    except Exception as e:
        print(f"\n\033[91m[ERROR] Initialization failed: {str(e)}\033[0m")
        sys.exit(1)