import json
import logging
import os
from urllib import response
from venv import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
from tqdm import tqdm

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取 httpx 的日志记录器
httpx_logger = logging.getLogger("httpx")
# 设置 httpx 日志记录器的日志级别为 WARNING
httpx_logger.setLevel(logging.WARNING)

class LlmConfig:
    def __init__(self, config_file_path:str = "") -> None:
        self.config_file_path = config_file_path
        logger.info(f"配置文件路径: {self.config_file_path}")
        self.config = self.load_configs(config_file_path=config_file_path)

    def load_configs(self, config_file_path:str = None)->dict:
        """
        从YAML文件加载配置
        
        Args:
            config_file_path: YAML配置文件路径
            
        Returns
            解析后的配置字典
            
        Raises:
            FileNotFoundError: 当配置文件不存在时
            yaml.YAMLError: 当YAML解析失败时
        """
        file_path =  self.config_file_path if config_file_path==None else config_file_path
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                logger.info(f"成功加载配置文件: {file_path}")
                return self.config if self.config else {}
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {file_path}")
            raise
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            raise
    
    def get_all_configs(self):
        return self.config


class QAEvalConfig(LlmConfig):
    def __init__(
        self,
        config_file_path:str = ""
    ) -> None:
        # 初始化父类
        super().__init__(config_file_path=config_file_path)
        
    def get_llm_config(self):
        return self.config['LLM']
    
    def get_dataset_config(self):
        return self.config['Dataset']
    
    def get_region_config(self):
        return self.config['region']


class LlmClient:
    def __init__(self, api_key: str, base_url: str, model_name: str, params: dict = {'temperature': 0.2}) -> None:
        self.client: OpenAI = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Connected to OpenAI API at {base_url}: {model_name}")
        self.model_name = model_name
        self.temperature = params['temperature']
    
    @retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=5, max=20))
    def generate(self, messages: list[dict], max_tokens:int|None=None, temperature:float|None=None, response_as_json: bool=False) -> str:
        try:
            if response_as_json:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages, # type: ignore
                    temperature=temperature if temperature else self.temperature,
                    max_tokens=max_tokens,
                )
                if response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    raise Exception("Empty response")
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages, # type: ignore
                    temperature=temperature if temperature else self.temperature,
                    max_tokens=max_tokens,
                )
                if response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    raise Exception("Empty response")
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")


class QAClient(LlmClient):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        params: dict,
        huggingface_dataset: bool,
        dataset: str | dict,
        dataset_split: str
    ) -> None:
        """
        问答客户端
        
        Args:
            api_key: API密钥
            base_url: 基础URL
            model_name: 模型名称
            params: 模型参数
            huggingface_dataset: 是否使用HuggingFace数据集
            dataset: 数据集名称或字典
            dataset_split: 数据集分割类型
        """
        # 初始化父类
        super().__init__(api_key=api_key, base_url=base_url, 
                         model_name=model_name, params=params)

        # 初始化数据集
        self.dataset = None
        if huggingface_dataset:
            try:
                from datasets import load_dataset  # 延迟导入
                self.dataset = load_dataset(dataset, split=dataset_split)
                logger.info(f"成功加载HuggingFace数据集: {dataset}[{dataset_split}]")
            except ImportError:
                logger.error("需要安装datasets库: pip install datasets")
            except Exception as e:
                logger.error(f"加载Huggingface数据集失败: {str(e)}")
                
        logger.info(f"{dataset}[{dataset_split}]数据集 | 数据数量: {len(self.dataset)}")

    def get_qa_response(self, system_prompt: str, qa_prompt: str, max_tokens:int|None=None, temperature:float|None=None) -> str:
        """
        获取LLM对给定提示的响应
        
        Args:
            system_prompt: 系统角色提示，定义AI的行为
            qa_prompt: 用户问题提示
            
        Returns:
            LLM生成的响应文本
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": qa_prompt}
        ]

        try:
            response = self.generate(messages=messages,
                                    temperature=temperature if temperature else self.temperature,
                                    max_tokens=max_tokens,
                                    )
            return response
        except Exception as e:
            logger.error(f"获取QA响应失败: {str(e)}")
            # raise

    def parse_qa_response(self, qa_response:str) -> dict:
        print(f"[DEBUG] QAClient->parse_qa_response")
        pass


if __name__ == "__main__":
    ### load eval configs ###
    region = "china"
    qa_eval_config = QAEvalConfig(config_file_path="evaluation/eval_configs.yaml")
    # all_configs = qa_eval_config.get_all_configs()
    # print(f"[DEBUG] all_configs = {all_configs}")
    llm_configs = qa_eval_config.get_llm_config()
    # print(f"[DEBUG] llm_configs = {llm_configs}")
    region_configs = qa_eval_config.get_region_config()
    # print(f"[DEBUG] region_configs = {region_configs}")
    # china_configs = region_configs['china']
    # print(f"[DEBUG] china_configs = {china_configs}")
    eval_region_configs = region_configs[region]
    # print(f"[DEBUG] {region}_configs = {eval_region_configs}")
    dataset_configs = qa_eval_config.get_dataset_config()
    # print(f"[DEBUG] dataset_configs = {dataset_configs}")
    
    ### SETTING ###
    api_key = llm_configs['api_key']
    params = llm_configs['parameters']
    base_url = eval_region_configs['endpoint']+"/v1"
    model_name=eval_region_configs['lora_adapter']
    huggingface_dataset=dataset_configs['source']=="huggingface"
    dataset=dataset_configs['name']
    dataset_split=dataset_configs['split']

    # ### LlmClient ###
    # print(f"[TEST] LlmClient")
    # llm_client = LlmClient(api_key=api_key, base_url=base_url, model_name=model_name)
    # messages = [
    #     {"role": "system", "content": "你是一个乐于助人的美国人"},
    #     {"role": "user", "content": "你好"},
    #     {"role": "assistant", "content": "你好！有什么可以帮您的吗？"},
    #     {"role": "user", "content": "Who are you? Where are you from?"}
    # ]
    # response_test = llm_client.generate(messages=messages)
    # print(f"[DEBUG] response_test = {response_test}")
    
    # ### QAClient ###
    # print(f"[TEST] QAClient")
    # qa_client = QAClient(api_key=api_key,
    #                     base_url=base_url,
    #                     model_name=model_name,
    #                     params=params,
    #                     huggingface_dataset=True,
    #                     dataset=dataset,
    #                     dataset_split=dataset_split)
    # qa_response = qa_client.get_qa_response(system_prompt="你是一个乐于助人的美国人",
    #                           qa_prompt="Who are you? Where are you from?")
    # print(f"[DEBUG] qa_response = {qa_response}")