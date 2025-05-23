from datetime import datetime
import os
import json

input_dir = "/share/project/zgx/ValueDebate/debate_track_output/English_Speaking and African_Islamic"
output_dir = "/share/project/zgx/ValueDebate/evaluation/consensus_eval/result/English_Speaking and African_Islamic"
category_names = [
    "Gender and Family Roles",
    "International Relations and Security",
    "Law and Ethics",
    "Politics and Governance",
    "Religion and Secularism",
    "Social Norms and Modernization"
]

result = []

for sub_dir in os.listdir(input_dir):
    sub_path = os.path.join(input_dir, sub_dir)
    if "2025-04-27" not in sub_dir:
        continue
    if not os.path.isdir(sub_path):
        continue

    category_true_rounds = {}
    all_rounds = []

    for category in category_names:
        cat_path = os.path.join(sub_path, category)
        if not os.path.isdir(cat_path):
            continue

        rounds = []
        for fname in os.listdir(cat_path):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(cat_path, fname)
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                    if 'meta_data' not in data:
                        rounds.append(data['metadata']['true_round'])
                    else:
                        rounds.append(data['meta_data']['true_rounds'])
            except Exception as e:
                print(f"Error reading {fpath}: {e}")

        if rounds:
            avg = sum(rounds) / len(rounds)
            category_true_rounds[category] = avg
            all_rounds.extend(rounds)
        else:
            category_true_rounds[category] = None

    if all_rounds:
        sub_avg = sum(all_rounds) / len(all_rounds)
    else:
        sub_avg = None

    result.append({
        "sub_dir": sub_dir,
        "true_rounds": sub_avg,
        "category_true_rounds": category_true_rounds
    })
now = datetime.now().strftime("%Y-%m-%d")
with open(output_dir+f"/true_rounds_data_{now}.json", "w") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)