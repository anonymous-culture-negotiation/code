#!/bin/bash

# llamafactory-cli export configs/merge_llama3_lora_sft.yaml

set -e

# 国家列表
countries=(
#   Denmark
#   US
  China
  Russia
  Iraq
  Mexico
  Spain
  Thailand
)

for country in "${countries[@]}"; do
  echo "Exporting for $country ..."
  llamafactory-cli export \
    --model_name_or_path models/base_model/llama3.3-70b-instruct \
    --adapter_name_or_path models/lora_adapter/${country}/llama3.3-70b/qlora \
    --template llama3 \
    --trust_remote_code true \
    --export_dir models/base_model/"$(echo $country | tr '[:upper:]' '[:lower:]')"_merged \
    --export_size 5 \
    --export_device auto \
    --export_legacy_format false
  echo "$country export finished!"
done

echo "All exports finished!"
