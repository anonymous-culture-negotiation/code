#!/bin/bash

culture_b="African_Islamic"
culture_a="English_Speaking"


base_culture="$culture_a and $culture_b"

base_dirs="${base_culture}/" # modify this to your output directory
config="evaluation/consensus_eval/config.yaml"
evaluator="PPL" # ['PPL', 'model_based']


input_dir="debate_track_output/${base_dir}"
output_base_dir="evaluation/consensus_eval/results/${base_dir}"
echo "Running consensus evaluation for all subdirectories in $input_dir..."
folders=(
    "Religion and Secularism"
    "Social Norms and Modernization"
)
for dir in "$input_dir"/*; do
    if [[ -d "$dir" ]]; then
        dir_name=$(basename "$dir")
        if [[ ! " ${folders[@]} " =~ " ${dir_name} " ]]; then
            echo "Skipping directory: $dir_name"
            continue
        fi
        output="${output_base_dir}/consensus_eval/${dir_name}_${evaluator}.json"
        echo "Processing directory: $output"
        python -m evaluation.consensus_eval.eval \
            --input "$dir" \
            --output "$output" \
            --config "$config" \
            --evaluator "$evaluator"
    fi
done
