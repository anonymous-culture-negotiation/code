import pdb
from tracemalloc import start
from typing import Literal
from venv import logger
from debate.agent import CultureAgent
from debate.debate_baseline import simple_consultancy, simple_debate
from debate.utils.utils_class import LlmClient
from debate.utils.utils_fn import get_json_config, get_legal_cultures, get_yaml_config, check_legal_culture, get_system_prompt
from debate.psro_debate_process import PSRODebate
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description="Value Debate System")
    parser.add_argument("--config", type=str, default="debate/config/params.yaml", help="Path to the config file")
    parser.add_argument("--model", type=str, default="Qwen2.5-7B-Instruct", help="Model name")
    parser.add_argument("--language", type=str, default="zh", help="Language for the model")
    parser.add_argument("--consensus_method", type=str, default="self_consensus", 
                      choices=["self_consensus", "judger_consensus"],
                      help="Debate method: self_consensus (agents summarize consensus), judger_consensus (llm judger detects consensus)")
    parser.add_argument("--method", type=str, default="psro", choices=["psro", "debate", "consultancy"], help="Debate method")
    parser.add_argument("--debate_culture_a", type=str, default="Confucian", choices=get_legal_cultures(), help="Culture of the first debater")
    parser.add_argument("--debate_culture_b", type=str, default="English_Speaking", choices=get_legal_cultures(), help="Culture of the second debater")
    parser.add_argument("--topic", type=str, default="debate/config/topics.yaml", help="Debate topic file path")
    parser.add_argument("--agent_type", type=str, default="llm_api", choices=['llm_api', 'lora'], help="Agent type")
    parser.add_argument("--br_generator_type", type=str, default="guided", help="BR generator type")
    parser.add_argument("--note", type=str, default=" ", help="Note for the debate")
    parser.add_argument("--topics_start_index", type=int, required=False, default=None, help="Start index for topics")
    parser.add_argument("--topics_end_index", type=int, required=False, default=None, help="End index for topics")
    parser.add_argument("--alpha", type=float, default=0.5, help="Alpha for the debate")
    parser.add_argument("--beta", type=float, default=0.3, help="Beta for the debate")
    parser.add_argument("--gamma", type=float, default=0.2, help="Gamma for the debate")
    parser.add_argument("--category",required=False, type=str, default=None, help="Category for the debate")
    parser.add_argument("--gpu_id", required=False, type=int, default=0)

    return parser.parse_args()

def get_client(params:dict, agent_type:Literal["lora", "llm_api"], culture:str|None=None):
    
    if agent_type == "lora":
        if culture is None:
            raise ValueError("Culture cannot be None")
        base_url = params['lora_adapter_api'][culture]["base_url"]
        api_key = params['lora_adapter_api'][culture]["api_key"]
        model_name = params['lora_adapter_api'][culture]["model_name"]
    elif agent_type == "llm_api":
        base_url = params['llm_api']["base_url"]
        api_key = params['llm_api']["api_key"]
        model_name = params['model'][args.model]['name']
     
    client = LlmClient(api_key, base_url, model_name)
    return client

def run_debate(args: argparse.Namespace):
    params = get_yaml_config(args.config)
    if args.topic.endswith(".yaml"):
        topics = get_yaml_config(args.topic)
    else:
        topics_raw = get_json_config(args.topic)

        # 1. If given start/end, only take that interval
        if args.topics_start_index is not None and args.topics_end_index is not None:
            selected_indices = range(args.topics_start_index, args.topics_end_index)
        else:
            selected_indices = range(len(topics_raw))

        # 2. If given category, only keep that category; otherwise keep all
        topics = []
        for i in selected_indices:
            if args.category is not None:
                if topics_raw[i]['category'] == args.category:
                    topics.append({'content': topics_raw[i]['content'], 'idx': i})
            else:
                topics.append({'content': topics_raw[i]['content'], 'idx': i})

    agent_type = args.agent_type
    filepath_list=[]
    meta_data = {
        "true_rounds": 0.0,
        "consensus": 0.0,
    }
    for topic_i in topics:
        i = topic_i['idx']
        topic = topic_i['content']
        print(f"=================Debate on topic {i}: {topic}=================")
        system_prompt_a = get_system_prompt(args.debate_culture_a, topic, args.language, args.method)
        client_a = get_client(params, agent_type, args.debate_culture_a)
        agent_a = CultureAgent(
            name=args.debate_culture_a,
            culture=args.debate_culture_a,
            client=client_a,
            system_prompt=system_prompt_a,
            gpu_id=args.gpu_id,
            language=args.language,
            br_generator_type=args.br_generator_type,
            method=args.method
        )
        
        system_prompt_b = get_system_prompt(args.debate_culture_b, topic, args.language, args.method)
        client_b = get_client(params, agent_type, args.debate_culture_b)
        agent_b = CultureAgent(
            name=args.debate_culture_b,
            culture=args.debate_culture_b,
            client=client_b,
            system_prompt=system_prompt_b,
            gpu_id=args.gpu_id,
            language=args.language,
            br_generator_type=args.br_generator_type,
            method=args.method
        )
        if args.category:
            note = args.note+"_"+args.category 
        else:
            note = args.note
        if args.method == "psro":
            debate = PSRODebate(topic=topic, agent_a=agent_a, agent_b=agent_b, max_rounds=params['max_rounds'], method=args.consensus_method, 
                                language=args.language, note=note, scorer_params=[args.alpha, args.beta, args.gamma], topic_index=i)
            meta = debate.run()
            meta_data["true_rounds"] += meta["true_rounds"]
            meta_data["consensus"] += 1 if meta["consensus_reached"] else 0
            filepath_list.append(debate.get_debate_history_filepath())
        elif args.method == "debate":
            simple_debate(agent_a, agent_b, params['max_rounds'], topic, i, note)
        elif args.method == "consultancy":
            simple_consultancy(agent_a, agent_b, topic, i, note)
        else:
            raise ValueError("Invalid method")

    meta_data["consensus"] /= len(topics)
    meta_data["true_rounds"] /= len(topics)
    print(f"================Meta data in {args.topics_start_index} - {args.topics_end_index} topics=================:\n {meta_data}")
    return filepath_list



def check_args(args: argparse.Namespace):
    # check args legal
    if not check_legal_culture(args.debate_culture_a) or not check_legal_culture(args.debate_culture_b):
        raise ValueError(f"Invalid culture:{args.debate_culture_a} or {args.debate_culture_b}")
    if args.consensus_method not in ["self_consensus", "judger_consensus"]:
        raise ValueError("Invalid method")
    if args.language not in ["zh", "en"]:
        raise ValueError("Invalid language")
    if args.agent_type not in ["lora", "llm_api"]:
        raise ValueError("Invalid agent type")
        

if __name__ == "__main__":
    args = parse_arguments()
    try:
        check_args(args)
    except ValueError as e:
        print(e)
        exit(1)
    
    filepath_list = []
    filepath_list = run_debate(args)
    print(f"Debate history saved at: {filepath_list}")