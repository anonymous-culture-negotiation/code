"""
Consensus Evaluation Main Program - Execution Flow:
1. Load JSON files containing multiple dialogue scenarios
2. Use specified type of evaluator to analyze consensus for each scenario
3. Merge original data with evaluation results and save
"""

import json
import yaml
import argparse
import os
from typing import List, Dict
from datetime import datetime
from tqdm import tqdm
from evaluation.consensus_eval.consensus_evaluator import ConsensusEvaluatorFactory, RandomConsensusEvaluator
from evaluation.consensus_eval.ppl_consensus_evaluator import PPLConsensusEvaluator
from evaluation.consensus_eval.model_based_consensus_evaluator import ModelBasedConsensusEvaluator
def main():
    # Configure command line argument parsing
    parser = argparse.ArgumentParser(description='Multicultural Consensus Evaluation System')
    parser.add_argument('--input', type=str, required=True, 
                       help='Input folder path (containing JSON files with dialogue scenarios)')
    parser.add_argument('--output', type=str, default='results.json',
                       help='Output file path (default: results.json)')
    parser.add_argument('--config', type=str, required=False, help='Configuration file path')
    parser.add_argument('--evaluator', type=str, choices=['random', 'PPL', 'model_based'], default='PPL',
                        help='Type of evaluator to use (default: random)')
    args = parser.parse_args()

    # Add timestamp and evaluator type to output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    args.output = args.output.replace('.json', f'_{timestamp}.json')
    # Get output file directory
    output_dir = os.path.dirname(args.output)
    # Check if directory exists, create if not
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Input folder path: {args.input}")
    print(f"Output file path: {args.output}")
    print(f"Using evaluator: {args.evaluator}")
    
    try:
        # Load configuration file
        config = {}
        if args.config:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

        # Initialize evaluator
        evaluator = ConsensusEvaluatorFactory.create(args.evaluator, **config)
        
        # Recursively get all files from subfolders
        json_files = [f for f in os.listdir(args.input) if f.endswith('.json')]
        
        # Process all files
        all_results = [{"dir_path": args.input}]
        for json_file in tqdm(json_files, desc="Processing files", unit="file"):
            file_path = os.path.join(args.input, json_file)
            # print(f"Processing File: {file_path}")

            # Load dialogue scenario data
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario = json.load(f)
            
            # Get response field keys and ensure correspondence
            initial_regions = list(scenario['initial_response'].keys())
            consensus_regions = list(scenario['consensus_response'].keys())
            
            # Ensure both dictionaries use the same keys
            if set(initial_regions) != set(consensus_regions):
                raise ValueError(f"Keys in initial_response and consensus_response do not match in file {json_file}")
            
            # Use the same key order for evaluation
            region1, region2 = sorted(initial_regions)  # Use sorting to ensure consistent order
            
           
            evaluation = evaluator.evaluate_consensus(
                topic=scenario['topic'],
                initial_response1=scenario['initial_response'][region1],
                initial_response2=scenario['initial_response'][region2],
                final_response1=scenario['consensus_response'][region1],
                final_response2=scenario['consensus_response'][region2]
            )
        
            # Merge original data with evaluation results
            combined = {
                'source_file': json_file,  # Add source filename
                **scenario,
                'evaluation_pairs': {  # Add key pair information used in evaluation
                    'region1': region1,
                    'region2': region2
                },
                'evaluation_metrics': evaluation
            }
            all_results.append(combined)
                
            # Save after each file is completed
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"Evaluation completed! Results saved to {args.output}")
    except Exception as e:
        print(e)

def register_evaluators():
    """
    Register all available evaluators
    """
    ConsensusEvaluatorFactory.register("random", RandomConsensusEvaluator)
    ConsensusEvaluatorFactory.register("PPL", PPLConsensusEvaluator)
    ConsensusEvaluatorFactory.register("model_based", ModelBasedConsensusEvaluator)
    # Other evaluator registrations can be done here
    # Example: Assuming SimilarityConsensusEvaluator is implemented
    # ConsensusEvaluatorFactory.register("similarity", SimilarityConsensusEvaluator)    


if __name__ == "__main__":
    # Need to register specific evaluator implementations before actual use
    # Example: Assuming SimilarityConsensusEvaluator is implemented
    # ConsensusEvaluatorFactory.register("similarity", SimilarityConsensusEvaluator)
    register_evaluators()
    main()
