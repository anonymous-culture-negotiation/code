#!/bin/bash

# 定义 YAML 文件路径
YAML_FILE="configs/lora_sft_otfq.yaml"

# 定义固定的键
KEYS=("model_name_or_path" "dataset" "output_dir" "stage" "template")

method="dpo" # dpo, simpo
# template="qwen"

output_dir_base="/share/project/baolaiwu/lora_adapter/${method}"
# base_model="Qwen2.5-72B-Instruct"
company="qwen"
# base_model_path="/share/project/baolaiwu/base_model/${company}/${base_model}"

# 定义要修改的值，使用数组来存储
VALUES_SET=(
    # # china and iraq
    # "models/base_model/china_merged" "debate_iraq_china" "models/lora_adapter/iraq_based_on_china/llama3.3-70b/qlora" "dpo"
    # "models/base_model/iraq_merged" "debate_china_iraq" "models/lora_adapter/china_based_on_iraq/llama3.3-70b/qlora" "dpo"
    # # us and china
    # "models/base_model/us_merged" "debate_china_us" "models/lora_adapter/china_based_on_us/llama3.3-70b/qlora" "dpo"
    # "models/base_model/china_merged" "debate_us_china" "models/lora_adapter/us_based_on_china/llama3.3-70b/qlora" "dpo"
    # # denmark and iraq
    # "models/base_model/denmark_merged" "debate_iraq_denmark" "models/lora_adapter/iraq_based_on_denmark/llama3.3-70b/qlora" "dpo"
    # "models/base_model/iraq_merged" "debate_denmark_iraq" "models/lora_adapter/denmark_based_on_iraq/llama3.3-70b/qlora" "dpo"
    # # mexico and russia
    # "models/base_model/mexico_merged" "debate_russia_mexico" "models/lora_adapter/russia_based_on_mexico/llama3.3-70b/qlora" "dpo"
    # "models/base_model/russia_merged" "debate_mexico_russia" "models/lora_adapter/mexico_based_on_russia/llama3.3-70b/qlora" "dpo"
    # spain and thailand
    # "models/base_model/spain_merged" "debate_thailand_spain" "models/lora_adapter/thailand_based_on_spain/llama3.3-70b/qlora" "dpo"
    # "models/base_model/thailand_merged" "debate_spain_thailand" "models/lora_adapter/spain_based_on_thailand/llama3.3-70b/qlora" "dpo"
    # # thailand and us
    # "models/base_model/thailand_merged" "debate_us_thailand" "models/lora_adapter/us_based_on_thailand/llama3.3-70b/qlora" "dpo"
    # "models/base_model/us_merged" "debate_thailand_us" "models/lora_adapter/thailand_based_on_us/llama3.3-70b/qlora" "dpo"

    # us with denmark
    # "./models/base_model/llama3.3-70b-instruct" "debate_us_denmark" "./models/lora_adapter/debate_us_denmark/llama3.3-70b/qlora" "dpo"
    # "./models/base_model/llama3.3-70b-instruct" "debate_denmark_us" "./models/lora_adapter/debate_denmark_us/llama3.3-70b/qlora" "dpo"
    # iraq with china
    # "models/base_model/llama3.3-70b-instruct" "debate_iraq_china" "models/lora_adapter/iraq_debate_china/llama3.3-70b/qlora" "dpo"
    # "models/base_model/llama3.3-70b-instruct" "debate_china_iraq" "models/lora_adapter/china_debate_iraq/llama3.3-70b/qlora" "dpo"
    # # us with china
    # "models/base_model/llama3.3-70b-instruct" "debate_us_china" "models/lora_adapter/us_debate_china/llama3.3-70b/qlora" "dpo"
    # "models/base_model/llama3.3-70b-instruct" "debate_china_us" "models/lora_adapter/china_debate_us/llama3.3-70b/qlora" "dpo"
    # denmark with iraq
    # "models/base_model/llama3.3-70b-instruct" "debate_denmark_iraq" "models/lora_adapter/denmark_debate_iraq/llama3.3-70b/qlora" "dpo"
    # "models/base_model/llama3.3-70b-instruct" "debate_iraq_denmark" "models/lora_adapter/iraq_debate_denmark/llama3.3-70b/qlora" "dpo"
    # mexico with russia
    # "models/base_model/llama3.3-70b-instruct" "debate_mexico_russia" "models/lora_adapter/mexico_debate_russia/llama3.3-70b/qlora" "dpo"
    # "models/base_model/llama3.3-70b-instruct" "debate_russia_mexico" "models/lora_adapter/russia_debate_mexico/llama3.3-70b/qlora" "dpo"
    # spain with thailand
    # "models/base_model/llama3.3-70b-instruct" "debate_spain_thailand" "models/lora_adapter/spain_debate_thailand/llama3.3-70b/qlora" "dpo"
    # "models/base_model/llama3.3-70b-instruct" "debate_thailand_spain" "models/lora_adapter/thailand_debate_spain/llama3.3-70b/qlora" "dpo"
    # thailand with us
    # "models/base_model/llama3.3-70b-instruct" "debate_thailand_us" "models/lora_adapter/thailand_debate_us/llama3.3-70b/qlora" "dpo"
    # "models/base_model/llama3.3-70b-instruct" "debate_us_thailand" "models/lora_adapter/us_debate_thailand/llama3.3-70b/qlora" "dpo"

    # # china and iraq
    # "models/base_model/china_merged" "debate_china_iraq" "models/lora_adapter/china_dpo_to_iraq/llama3.3-70b/qlora" "dpo"
    # "models/base_model/iraq_merged" "debate_iraq_china" "models/lora_adapter/iraq_dpo_to_china/llama3.3-70b/qlora" "dpo"
    
    # # us and china
    # "models/base_model/us_merged" "debate_us_china" "models/lora_adapter/us_dpo_to_china/llama3.3-70b/qlora" "dpo"
    # "models/base_model/china_merged" "debate_china_us" "models/lora_adapter/china_dpo_to_us/llama3.3-70b/qlora" "dpo"
    # # denmark and iraq
    # "models/base_model/denmark_merged" "debate_denmark_iraq" "models/lora_adapter/denmark_dpo_to_iraq/llama3.3-70b/qlora" "dpo"
    # "models/base_model/iraq_merged" "debate_iraq_denmark" "models/lora_adapter/iraq_dpo_to_denmark/llama3.3-70b/qlora" "dpo"
    # mexico and russia
    # "models/base_model/mexico_merged" "debate_mexico_russia" "models/lora_adapter/mexico_dpo_to_russia/llama3.3-70b/qlora" "dpo"
    # "models/base_model/russia_merged" "debate_russia_mexico" "models/lora_adapter/russia_dpo_to_mexico/llama3.3-70b/qlora" "dpo"
    # spain and thailand
    # "models/base_model/spain_merged" "debate_spain_thailand" "models/lora_adapter/spain_dpo_to_thailand/llama3.3-70b/qlora" "dpo"
    # "models/base_model/thailand_merged" "debate_thailand_spain" "models/lora_adapter/thailand_dpo_to_spain/llama3.3-70b/qlora" "dpo"
    # thailand and us
    # "models/base_model/thailand_merged" "debate_thailand_us" "models/lora_adapter/thailand_dpo_to_us/llama3.3-70b/qlora" "dpo"
    # "models/base_model/us_merged" "debate_us_thailand" "models/lora_adapter/us_dpo_to_thailand/llama3.3-70b/qlora" "dpo"

    # ACL exp
    # Qwen2.5-72B-Instruct
    # "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_iraq_china" "${output_dir_base}/iraq_dpo_to_china/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    # "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_china_iraq" "${output_dir_base}/china_dpo_to_iraq/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_china_us" "${output_dir_base}/china_dpo_to_us/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_us_china" "${output_dir_base}/us_dpo_to_china/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_denmark_iraq" "${output_dir_base}/denmark_dpo_to_iraq/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_iraq_denmark" "${output_dir_base}/iraq_dpo_to_denmark/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_denmark_us" "${output_dir_base}/denmark_dpo_to_us/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_us_denmark" "${output_dir_base}/us_dpo_to_denmark/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_mexico_russia" "${output_dir_base}/mexico_dpo_to_russia/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_russia_mexico" "${output_dir_base}/russia_dpo_to_mexico/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_spain_thailand" "${output_dir_base}/spain_dpo_to_thailand/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_thailand_spain" "${output_dir_base}/thailand_dpo_to_spain/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_thailand_us" "${output_dir_base}/thailand_dpo_to_us/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct" "debate_us_thailand" "${output_dir_base}/us_dpo_to_thailand/Qwen2.5-72B-Instruct/qlora" "${method}" "qwen"
    # Qwen2.5-14B-Instruct
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_iraq_china" "${output_dir_base}/iraq_dpo_to_china/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_china_iraq" "${output_dir_base}/china_dpo_to_iraq/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_china_us" "${output_dir_base}/china_dpo_to_us/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_us_china" "${output_dir_base}/us_dpo_to_china/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_denmark_iraq" "${output_dir_base}/denmark_dpo_to_iraq/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_iraq_denmark" "${output_dir_base}/iraq_dpo_to_denmark/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_denmark_us" "${output_dir_base}/denmark_dpo_to_us/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_us_denmark" "${output_dir_base}/us_dpo_to_denmark/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_mexico_russia" "${output_dir_base}/mexico_dpo_to_russia/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_russia_mexico" "${output_dir_base}/russia_dpo_to_mexico/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_spain_thailand" "${output_dir_base}/spain_dpo_to_thailand/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_thailand_spain" "${output_dir_base}/thailand_dpo_to_spain/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_thailand_us" "${output_dir_base}/thailand_dpo_to_us/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct" "debate_us_thailand" "${output_dir_base}/us_dpo_to_thailand/Qwen2.5-14B-Instruct/qlora" "${method}" "qwen"
    # llama3.1-8b-instruct
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_iraq_china" "${output_dir_base}/iraq_dpo_to_china/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_china_iraq" "${output_dir_base}/china_dpo_to_iraq/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_china_us" "${output_dir_base}/china_dpo_to_us/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_us_china" "${output_dir_base}/us_dpo_to_china/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_denmark_iraq" "${output_dir_base}/denmark_dpo_to_iraq/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_iraq_denmark" "${output_dir_base}/iraq_dpo_to_denmark/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_denmark_us" "${output_dir_base}/denmark_dpo_to_us/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_us_denmark" "${output_dir_base}/us_dpo_to_denmark/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_mexico_russia" "${output_dir_base}/mexico_dpo_to_russia/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_russia_mexico" "${output_dir_base}/russia_dpo_to_mexico/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_spain_thailand" "${output_dir_base}/spain_dpo_to_thailand/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_thailand_spain" "${output_dir_base}/thailand_dpo_to_spain/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_thailand_us" "${output_dir_base}/thailand_dpo_to_us/llama3.1-8b-instruct/qlora" "${method}" "llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct" "debate_us_thailand" "${output_dir_base}/us_dpo_to_thailand/llama3.1-8b-instruct/qlora" "${method}" "llama3"
)

STEPS=${#KEYS[@]}
for ((i=0; i<${#VALUES_SET[@]}; i+=STEPS)); 
do
    VALUES=("${VALUES_SET[@]:i:STEPS}")
    echo "正在处理值集: ${VALUES[@]}"
    
    # 捕获 Python 脚本的输出，即新文件路径
    NEW_YAML_FILE=$(python script/finetune/modify_finetune_config.py "$YAML_FILE" "${KEYS[@]}" "${VALUES[@]}")
    
    # 使用新生成的 YAML 文件路径执行命令
    echo "YAML file path: $NEW_YAML_FILE"
    # deepspeed --num_gpus 8 --num_nodes 2 --hostfile configs/hostfile \
    # --master_addr 172.26.178.252 --master_port 29500 \
    # -- $(which llamafactory-cli) train $NEW_YAML_FILE

    # /root/miniconda3/envs/valuedebate/bin/python /share/project/cjw/ValueLockin/LLaMA-Factory/src/train.py $NEW_YAML_FILE

    # FORCE_TORCHRUN=1 NNODES=2 NODE_RANK=0 MASTER_ADDR=172.26.178.252 MASTER_PORT=29500 llamafactory-cli train $NEW_YAML_FILE 

    # deepspeed --num_gpus 8 --num_nodes 2 --hostfile configs/hostfile --master_addr 172.26.178.252 --master_port=9901 LLaMA-Factory/src/train.py $NEW_YAML_FILE

    echo "============ END ==============="
done
