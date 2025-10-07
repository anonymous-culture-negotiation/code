#!/bin/bash

# 定义 YAML 文件路径
YAML_FILE="configs/lora_sft_otfq.yaml"

# 固定键
KEYS=("model_name_or_path" "dataset" "output_dir" "stage" "template")

method="dpo" # dpo, simpo
output_dir_base="/share/project/baolaiwu/lora_adapter/${method}"

# 模型列表（模型路径、模板名）
MODELS=(
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-14B-Instruct qwen"
    "/share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct qwen"
    "/share/project/baolaiwu/base_model/llama/llama3.1-8b-instruct llama3"
    "/share/project/baolaiwu/base_model/llama/llama3.3-70b-instruct llama3"
)

# 数据集组合列表（dataset_name 对应 output_dir 子路径）
DATASETS=(
    "debate_china_us china_dpo_to_us"
    "debate_us_china us_dpo_to_china"
    "debate_denmark_iraq denmark_dpo_to_iraq"
    "debate_iraq_denmark iraq_dpo_to_denmark"
    "debate_spain_thailand spain_dpo_to_thailand"
    "debate_thailand_spain thailand_dpo_to_spain"
    "debate_thailand_us thailand_dpo_to_us"
    "debate_us_thailand us_dpo_to_thailand"
    "debate_iraq_china iraq_dpo_to_china"
    "debate_china_iraq china_dpo_to_iraq"
    "debate_mexico_russia mexico_dpo_to_russia"
    "debate_russia_mexico russia_dpo_to_mexico"
    "debate_us_denmark us_dpo_to_denmark"
    "debate_denmark_us denmark_dpo_to_us"
)

# 自动生成 VALUES_SET
VALUES_SET=()
for model_info in "${MODELS[@]}"; do
    read -r model_path template <<< "$model_info"
    model_name=$(basename "$model_path")
    for dataset_info in "${DATASETS[@]}"; do
        read -r dataset_name output_dir <<< "$dataset_info"
        VALUES_SET+=(
            "$model_path" \
            "$dataset_name" \
            "${output_dir_base}/${output_dir}/${model_name}/qlora" \
            "$method" \
            "$template"
        )
    done
done

STEPS=${#KEYS[@]}
for ((i=0; i<${#VALUES_SET[@]}; i+=STEPS)); 
do
    VALUES=("${VALUES_SET[@]:i:STEPS}")
    echo "正在处理值集: ${VALUES[@]}"

    # 检查输出路径是否存在
    if [ -d "${VALUES[2]}" ]; then
        echo "⚠️ 输出目录已存在: ${VALUES[2]}，跳过该实验"
        echo "============ SKIP ==============="
        continue
    fi

    # 捕获 Python 脚本的输出，即新文件路径
    NEW_YAML_FILE=$(python script/finetune/modify_finetune_config.py "$YAML_FILE" "${KEYS[@]}" "${VALUES[@]}")
    # 使用新生成的 YAML 文件路径执行命令
    echo "YAML file path: $NEW_YAML_FILE"

    export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
    export NCCL_SOCKET_IFNAME=eth0
    export NCCL_DEBUG=INFO
    export NCCL_IB_DISABLE=1
    export NCCL_NET_GDR_LEVEL=2
    export MASTER_ADDR=172.26.178.252
    export NCCL_DEBUG=INFO
    export NCCDISABLE=0
    # export MASTER_PORT=29500
    export MASTER_PORT=29901

    # deepspeed --num_gpus 8 --num_nodes 2 --hostfile configs/hostfile \
    # --master_addr $MASTER_ADDR --master_port=$MASTER_PORT LLaMA-Factory/src/train.py \
    # --deepspeed configs/ds_z2_config.json \
    
    echo "deepspeed --num_gpus 8 LLaMA-Factory/src/train.py \
    --bf16 \
    --cutoff_len 1000 \
    --data_shared_file_system True \
    --dataset ${VALUES[1]} \
    --ddp_timeout 180000000 \
    --do_train \
    --finetuning_type lora \
    --gradient_accumulation_steps 8 \
    --learning_rate 1e-4 \
    --logging_steps 10 \
    --lora_rank 8 \
    --lora_target all \
    --lr_scheduler_type cosine \
    --model_name_or_path ${VALUES[0]} \
    --num_train_epochs 10.0 \
    --output_dir ${VALUES[2]} \
    --overwrite_cache \
    --overwrite_output_dir \
    --per_device_train_batch_size 1 \
    --plot_loss \
    --pref_beta 0.1 \
    --pref_loss simpo \
    --preprocessing_num_workers 8 \
    --quantization_bit 4 \
    --quantization_method bnb \
    --report_to tensorboard \
    --save_steps 500 \
    --stage dpo \
    --template ${VALUES[4]} \
    --trust_remote_code \
    --warmup_ratio 0.1"

    deepspeed --num_gpus 8 LLaMA-Factory/src/train.py \
    --bf16 \
    --cutoff_len 1000 \
    --data_shared_file_system True \
    --dataset ${VALUES[1]} \
    --ddp_timeout 180000000 \
    --do_train \
    --finetuning_type lora \
    --gradient_accumulation_steps 8 \
    --learning_rate 1e-4 \
    --logging_steps 10 \
    --lora_rank 8 \
    --lora_target all \
    --lr_scheduler_type cosine \
    --model_name_or_path ${VALUES[0]} \
    --num_train_epochs 10.0 \
    --output_dir ${VALUES[2]} \
    --overwrite_cache \
    --overwrite_output_dir \
    --per_device_train_batch_size 1 \
    --plot_loss \
    --pref_beta 0.1 \
    --pref_loss simpo \
    --preprocessing_num_workers 8 \
    --quantization_bit 4 \
    --quantization_method bnb \
    --report_to tensorboard \
    --save_steps 500 \
    --stage dpo \
    --template ${VALUES[4]} \
    --trust_remote_code \
    --warmup_ratio 0.1

    echo "============ END ==============="
done