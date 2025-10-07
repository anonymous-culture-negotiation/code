#!/bin/bash

# 定义 YAML 文件路径
YAML_FILE="configs/lora_sft_otfq.yaml"

# 定义固定的键
KEYS=("model_name_or_path" "dataset" "output_dir")

# 定义要修改的值，使用数组来存储
VALUES_SET=(
    "./models/base_model/llama3.3-70b-instruct" "global_opinion_iraq" "./models/lora_adapter/Iraq/llama3.3-70b/qlora"
    "./models/base_model/llama3.3-70b-instruct" "global_opinion_us" "./models/lora_adapter/US/llama3.3-70b/qlora"
    "./models/base_model/llama3.3-70b-instruct" "global_opinion_china" "./models/lora_adapter/China/llama3.3-70b/qlora"
    "./models/base_model/llama3.3-70b-instruct" "global_opinion_denmark" "./models/lora_adapter/Denmark/llama3.3-70b/qlora"
    "./models/base_model/llama3.3-70b-instruct" "global_opinion_spain" "./models/lora_adapter/Spain/llama3.3-70b/qlora"
    "./models/base_model/llama3.3-70b-instruct" "global_opinion_mexico" "./models/lora_adapter/Mexico/llama3.3-70b/qlora"
    "./models/base_model/llama3.3-70b-instruct" "global_opinion_russia" "./models/lora_adapter/Russia/llama3.3-70b/qlora"
    "./models/base_model/llama3.3-70b-instruct" "global_opinion_thailand" "./models/lora_adapter/Thailand/llama3.3-70b/qlora"
)

# 遍历每组值并调用 Python 脚本
for ((i=0; i<${#VALUES_SET[@]}; i+=3)); do
    VALUES=("${VALUES_SET[@]:i:3}")
    echo "正在处理值集: ${VALUES[@]}"
    
    # 捕获 Python 脚本的输出，即新文件路径
    NEW_YAML_FILE=$(python script/finetune/modify_finetune_config.py "$YAML_FILE" "${KEYS[@]}" "${VALUES[@]}")
    
    # 使用新生成的 YAML 文件路径执行命令
    echo "YAML file path: $NEW_YAML_FILE"
    llamafactory-cli train $NEW_YAML_FILE
done