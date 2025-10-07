import sys
import yaml
from datetime import datetime

def modify_yaml(file_path, keys, values):
    # 读取 YAML 文件
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)

    # 修改指定的键值对
    for key, value in zip(keys, values):
        if key in data:
            data[key] = value
            # print(f"\n[{key}] = [{value}]")
        else:
            print(f"警告: 键 '{key}' 不存在于 YAML 文件中。")

    # 获取当前时间戳
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # 生成新的文件名
    new_file_path = f"{file_path.rstrip('.yaml')}_{timestamp}.yaml"

    # 写回修改后的 YAML 文件
    with open(new_file_path, 'w') as file:
        yaml.dump(data, file)

    # 返回新文件路径
    return new_file_path

if __name__ == "__main__":
    # 从命令行参数获取文件路径
    yaml_file = sys.argv[1]

    num_keys = (len(sys.argv) - 2) // 2

    # 从命令行读取固定数量的键和值
    keys = sys.argv[2 : 2 + num_keys]
    values = sys.argv[2 + num_keys : 2 + 2 * num_keys]
    
    # 调用函数执行修改
    new_file_path = modify_yaml(yaml_file, keys, values)
    print(new_file_path)
