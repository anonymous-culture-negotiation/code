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
# --master_addr $MASTER_ADDR --master_port=$MASTER_PORT \
deepspeed --num_gpus 8 LLaMA-Factory/src/train.py \
--bf16 \
--cutoff_len 1000 \
--data_shared_file_system True \
--dataset debate_china_us \
--ddp_timeout 180000000 \
--deepspeed configs/ds_z2_config.json \
--do_train \
--finetuning_type lora \
--gradient_accumulation_steps 8 \
--learning_rate 1e-4 \
--logging_steps 10 \
--lora_rank 8 \
--lora_target all \
--lr_scheduler_type cosine \
--model_name_or_path /share/project/baolaiwu/base_model/qwen/Qwen2.5-72B-Instruct \
--num_train_epochs 10.0 \
--output_dir /share/project/baolaiwu/lora_adapter/dpo/china_dpo_to_us/Qwen2.5-72B-Instruct/qlora \
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
--template qwen \
--trust_remote_code \
--warmup_ratio 0.1