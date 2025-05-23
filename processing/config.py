import os
import random
import numpy as np
import torch
from pathlib import Path

# 设置随机种子
def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)

# 基础路径配置
BASE_PATH = Path("data/region_opinions")
CACHE_PATH = BASE_PATH / "cache"
AUGMENTED_PATH = BASE_PATH / "augmented_data"
FILTERED_PATH = BASE_PATH / "augmented_filtered_data"
RAW_PATH = BASE_PATH / "wvs_raw"  # 新增原始数据保存路径

# 确保目录存在
def ensure_dirs():
    for path in [CACHE_PATH, AUGMENTED_PATH, FILTERED_PATH, RAW_PATH]:  # 添加 RAW_PATH
        path.mkdir(parents=True, exist_ok=True)

# API配置
class APIConfig:
    def __init__(self, base_url, platform="openai", api_key=None, model=None):
        self.platform = platform
        self.api_key = api_key
        
        # 根据平台设置默认值
        if platform == "openai":
            from api_key import OPENAI_API_KEY
            self.base_url = base_url or "https://api.openai.com/v1"
            self.api_key = api_key or OPENAI_API_KEY
            self.model = model or "gpt-4o"
        elif platform == "siliconflow":
            from api_key import API_KEY
            self.base_url = "https://api.siliconflow.cn"
            self.api_key = api_key or API_KEY
            self.model = model or "Pro/deepseek-ai/DeepSeek-V3"
        elif platform == "bean":
            from api_key import BEAN_API_KEY
            self.base_url = "https://api.61798.cn"
            self.api_key = api_key or BEAN_API_KEY
            self.model = model or "gpt-4o"
        else:
            raise ValueError(f"不支持的平台: {platform}")