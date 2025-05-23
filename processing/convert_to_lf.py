import json
import os
import argparse
from pathlib import Path

type_to_region:dict = {
    "Protestant_Europe": "Denmark",
    "English_Speaking": "US",
    "Confucian": "China",
    "African_Islamic": "Iraq",
    "Orthodox_Europe": "Russia",
    "Catholic_Europe": "Spain",
    "Latin_America": "Mexico",
    "West_and_South_Asia": "Thailand",
}

def parse_args():
    parser = argparse.ArgumentParser(description="将文件转换为lf可以读取的格式")

    # 创建子解析器（subparsers），让用户选择子命令
    subparsers = parser.add_subparsers(
        dest="mode",         # 存储所选子命令名称的字段
        required=True
    )
    # ----------------------
    # 定义“文件模式 (file)”子命令
    # ----------------------
    parser_file = subparsers.add_parser(
        "file",
        help="文件模式：必须指定输入文件与输出文件"
    )
    parser_file.add_argument(
        "input_file",
        type=str,
        help="输入文件路径"
    )
    parser_file.add_argument(
        "-o", "--output_file",
        type=str,
        help="输出文件路径"
    )
    # ----------------------
    # 定义“文件夹模式 (dir)”子命令
    # ----------------------
    parser_dir = subparsers.add_parser(
        "dir",
        help="文件夹模式：指定输入文件夹路径"
    )
    parser_dir.add_argument(
        "--input_dir",
        type=str,
        help="输入文件夹路径",
        required=True
    )
    parser_dir.add_argument(
        "--output_dir_file",
        type=str,
        help="输出文件夹路径（可选）"
    )
    parser_dir.add_argument(
        "--culture_type",
        type=str,
        help="提取的类型"
    )

    # 解析命令行
    args = parser.parse_args()

    # 根据选择的子命令做对应的处理逻辑
    if args.mode == "file":
        print("=== 当前选择：文件模式 (file) ===")
        print(f"input-file:  {args.input_file}")
        print(f"output-file: {args.output_file}")
        # 这里可继续写对文件的处理逻辑
    elif args.mode == "dir":
        print("=== 当前选择：文件夹模式 (dir) ===")
        print(f"input-dir:  {args.input_dir}")
        print(f"output-dir-file: {args.output_dir_file}")
        # 这里可继续写对文件夹的处理逻辑

    return args

def convert_jsonl_to_json(input_file, output_file=None):
    """
    将JSONL文件转换为指定格式的JSON文件
    
    参数:
        input_file (str): 输入的JSONL文件路径
        output_file (str, 可选): 输出的JSON文件路径，默认为输入文件名-processed.json
    """
    # 获取文件名（不含扩展名）作为文化背景
    culture_name = Path(input_file).stem
    
    # 如果没有提供输出文件路径，则生成默认的
    if not output_file:
        output_dir = os.path.dirname(input_file)
        output_file = os.path.join(output_dir, f"{culture_name}-processed.json")
    else:
        output_dir = os.path.dirname(output_file)
    
    # 确保输出目录存在
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    result = []
    
    # 读取JSONL文件
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():  # 跳过空行
                data = json.loads(line)
                # 只处理is_consistent为true的记录
                if data.get("is_consistent", False):
                    item = {
                        "instruction": f"Answer the question based on {culture_name} cultural values.",
                        "input": data.get("final_question", ""),
                        "output": data.get("final_answer", "")
                    }
                    result.append(item)
    
    # 写入结果到JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"处理完成！共转换 {len(result)} 条记录。")
    print(f"结果已保存至：{output_file}")

def convert_debate_to_DPO_dataset(args):
    input_dir = args.input_dir
    output_dir_file = args.output_dir_file
    culture_type = args.culture_type
    dpo_data = []
    
    for entry in os.listdir(input_dir):
        entry_path = os.path.join(input_dir, entry)
        if os.path.isfile(entry_path):
            # 直接在 input_dir 下的文件
            print(f"file: {entry_path}")
        elif os.path.isdir(entry_path):
            # 在一级子文件夹下的文件
            for file_name in os.listdir(entry_path):
                file_path = os.path.join(entry_path, file_name)
                if not file_name.endswith(".json"):
                    continue
                if os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        item = json.load(f)
                    dpo_data.append({
                        "instruction": f"Answer the question based on {type_to_region[culture_type]} cultural values.",
                        "input": item['topic'],
                        "rejected": item['initial_response'][culture_type],
                        "chosen": item['consensus_response'][culture_type],
                    })

    print(f"length of {output_dir_file} dpo data {len(dpo_data)}")

    with open(output_dir_file, 'w', encoding='utf-8') as out_f:
        json.dump(dpo_data, out_f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    args = parse_args()

    if args.mode == "file":
        convert_jsonl_to_json(args.input_file, args.output_file)
    elif args.mode == "dir":
        convert_debate_to_DPO_dataset(args)