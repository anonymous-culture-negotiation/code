import os
import sys
from config import set_seed, APIConfig
from utils import parse_args
from data_extension import DataExtensionProcessor
from data_augmentation import DataAugmentationProcessor

def main():
    # 解析命令行参数
    args = parse_args()
    
    # 设置随机种子
    set_seed(args.seed)
    
    # 初始化API配置
    api_config = APIConfig(
        base_url="https://api.61798.cn/v1", # [TODO] 发布前删除
        platform=args.platform,
        api_key=None,  # 将从api_key.py中加载
        model=args.model
    )
    
    # 根据指定的步骤执行流水线
    if args.step1:
        print("\n===== 执行步骤1: 数据扩展 =====")
        processor = DataExtensionProcessor(args.region, args.sample_num)
        processor.process()
        
    if args.step2 or args.step3:  # 步骤2和3合并实现
        print("\n===== 执行步骤2&3: 数据增强和价值观筛选 =====")
        processor = DataAugmentationProcessor(
            args.region, 
            api_config, 
            use_ray=args.use_ray,  # 传递Ray使用选项
            num_cpus=args.num_cpus,
            batch_size=args.batch_size,  # 调整批大小
            max_concurrent_apis=args.max_concurrent_apis,
            max_retries=args.max_retries,
            use_region_param=args.use_region_param
        )
        processor.process()
        
    print("\n处理完成!")

if __name__ == "__main__":
    main()