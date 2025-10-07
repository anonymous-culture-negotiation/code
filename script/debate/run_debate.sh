#!/bin/bash

culture_b="African_Islamic"
culture_a="English_Speaking"

# "utility: alpha beta gamma"
params="0.5 0.5 0.2"
method="psro" # consultancy, debate, psro

categories=(
    "Gender and Family Roles"
    "Religion and Secularism"
    "Politics and Governance"
    "Law and Ethics"
    "Social Norms and Modernization"
    "International Relations and Security"
)

read -r alpha beta gamma <<< "$params"
echo "====================================================="
echo "run debate between $culture_a and $culture_b"
echo "paras: alpha=$alpha, beta=$beta, gamma=$gamma"
echo "====================================================="
index=0
for category in "${categories[@]}"; do
    echo "running $category, index=$index"
    stdbuf -oL python -m debate.main \
    --debate_culture_a "$culture_a" \
    --debate_culture_b "$culture_b" \
    --model "gpt-4-turbo" \
    --agent_type "lora" \
    --language "en" \
    --consensus_method "self_consensus" \
    --method "$method" \
    --topic "debate/config/topics/refined_topics.json" \
    --note "$params" \
    --alpha "$alpha" \
    --beta "$beta" \
    --gamma "$gamma" \
    --category "$category" \
    --gpu_id "$index"> "logging/output_${category}.log" 2>&1 &
    index=$((index + 1))
done
wait
echo "Done."