from datetime import datetime
import logging
import json
import os

from debate.prompts.prompts import CONSULTANCY_FINAL_SYSTEM_PROMPT, DEBATE_FINAL_SYSTEM_PROMPT
from debate.agent import CultureAgent
from debate.utils.utils_fn import get_yaml_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
params = get_yaml_config("debate/config/params.yaml")



def simple_debate(agent_a: CultureAgent, agent_b: CultureAgent, max_rounds, topic:str, topic_index:int, note: str = ""):
    simple_history = {
        "topic": topic,
        "initial_response": {
            f"{agent_a.culture}": "",
            f"{agent_b.culture}": ""
        },
        "debate_history": [],
        "consensus_response": {
            f"{agent_a.culture}": "",
            f"{agent_b.culture}": ""
        },
        "metadata": {
            "true_round": 0,
            "note": note
        }
    }
    prompt = f"Generate your initial response, it must prioritize deep alignment with your own cultural traditions and core values" 
    initial_response_a = agent_a.generate_response_with_system_prompt(prompt)
    initial_response_b = agent_b.generate_response_with_system_prompt(prompt)
    simple_history["initial_response"][f"{agent_a.culture}"] = initial_response_a
    simple_history["initial_response"][f"{agent_b.culture}"] = initial_response_b
    agent_a.add_memory("assistant", initial_response_a)
    agent_b.add_memory("assistant", initial_response_b)
    agent_a.add_memory("user", initial_response_b)
    agent_b.add_memory("user", initial_response_a)

    stop_system_prompt = f"If you think both sides have reached a consensus, please respond with 'yes, I agree'. No ohter response is allowed. If you don't think you reached a consensus, please continue the debate, no need to respond with 'no' or any other response."

    for round_number in range(max_rounds):
        logger.info(f"Starting simple debate round {round_number + 1}\n\n")
        # Generate model response
        a_response = agent_a.generate_response_with_system_prompt(stop_system_prompt)
        agent_b.add_memory("user", a_response)
        agent_a.add_memory("assistant", a_response)
        b_response = agent_b.generate_response_with_system_prompt(stop_system_prompt)
        agent_a.add_memory("user", b_response)
        agent_b.add_memory("assistant", b_response)
        if "yes, i agree" in a_response.lower() and "yes, i agree" in b_response.lower():
            break
        # Save simple debate trajectory
        simple_history["debate_history"].append({
            "round": round_number + 1,
            f"{agent_a.culture}": a_response,
            f"{agent_b.culture}": b_response
        })

        logger.info(f"Simple debate round {round_number + 1} completed\n\n")
    # Generate final response
    final_system_prompt_a = DEBATE_FINAL_SYSTEM_PROMPT['en'].format(culture=agent_a.culture, topic=topic)
    final_system_prompt_b = DEBATE_FINAL_SYSTEM_PROMPT['en'].format(culture=agent_b.culture, topic=topic)
    final_response_a = agent_a.generate_response_with_system_prompt(final_system_prompt_a)
    final_response_b = agent_b.generate_response_with_system_prompt(final_system_prompt_b)
    simple_history["consensus_response"][f"{agent_a.culture}"] = final_response_a
    simple_history["consensus_response"][f"{agent_b.culture}"] = final_response_b
    simple_history["metadata"]["true_round"] = round_number + 1
    # Save simple debate trajectory
    save_debate_history(path=get_debate_path(agent_a.culture, agent_b.culture, note),
                        filename=generate_filename("debate", topic_index),
                        debate_history=simple_history)
    logger.info(f"Simple debate completed\n\n")
    return simple_history 

def simple_consultancy(agent_a: CultureAgent, agent_b: CultureAgent, topic:str, topic_index:int, note: str = ""):
    """Simple consultancy"""
    simple_history = {
        "topic": topic,
        "initial_response": {
            f"{agent_a.culture}": "",
            f"{agent_b.culture}": ""
        },
        "consensus_response": {
            f"{agent_a.culture}": "",
            f"{agent_b.culture}": ""
        },
        "metadata": {
            "note": note
        }
    }
    logger.info(f"Starting simple consultancy\n\n")
    # Generate model response
    prompt = f"Generate your initial response, it must prioritize deep alignment with your own cultural traditions and core values" 
    initial_response_a = agent_a.generate_response_with_system_prompt(prompt)
    initial_response_b = agent_b.generate_response_with_system_prompt(prompt)
    simple_history["initial_response"][f"{agent_a.culture}"] = initial_response_a
    simple_history["initial_response"][f"{agent_b.culture}"] = initial_response_b

    agent_a.add_memory("assistant", initial_response_a)
    agent_b.add_memory("assistant", initial_response_b)

    final_system_prompt_a = CONSULTANCY_FINAL_SYSTEM_PROMPT['en'].format(culture=agent_a.culture, topic=topic, other_culture=agent_b.culture)
    final_system_prompt_b = CONSULTANCY_FINAL_SYSTEM_PROMPT['en'].format(culture=agent_b.culture, topic=topic, other_culture=agent_a.culture)
    final_response_a = agent_a.generate_response_with_system_prompt(final_system_prompt_a)
    final_response_b = agent_b.generate_response_with_system_prompt(final_system_prompt_b)
    simple_history["consensus_response"][f"{agent_a.culture}"] = final_response_a
    simple_history["consensus_response"][f"{agent_b.culture}"] = final_response_b
    logger.info(f"Simple consultancy completed\n\n")
    save_debate_history(path=get_debate_path(agent_a.culture, agent_b.culture, note),
                        filename=generate_filename("consultancy", topic_index),
                        debate_history=simple_history)
    return simple_history


def get_debate_path(a_culture: str, b_culture: str, note: str) -> str:
        """Get the path to save debate history"""
        # now = datetime.now().strftime("%Y-%m-%d")
        now = "2025-04-27"
        now = now + f"_{note.split('_')[0]}" if note else now
        if len(note.split('_')) > 1:
            return os.path.join(params['debate_output_path'], 
                          f'{a_culture} and {b_culture}', now, note.split('_')[1])
        else:
            return os.path.join(params['debate_output_path'], 
                          f'{a_culture} and {b_culture}', now)

def generate_filename(method: str, topic_index: int) -> str:
    """Generate a unique filename, including timestamp and model name"""
    now = datetime.now().strftime("%Y-%m-%d-%H-%M")
    return f"{method}_{topic_index}_{now}.json"
 
def save_debate_history(path: str, filename: str, debate_history):
    """Save the complete debate history to a file"""
    if not os.path.exists(path):
        os.makedirs(path)
    filepath = os.path.join(path, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(json.dumps(debate_history, ensure_ascii=False, indent=4))
    logger.info(f"Debate history saved at: {filepath}\n")
    