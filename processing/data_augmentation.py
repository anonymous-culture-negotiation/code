import os
import time
import multiprocessing
from typing import Dict, List, Tuple, Any, Optional
from tqdm import tqdm
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from config import CACHE_PATH, AUGMENTED_PATH, FILTERED_PATH, APIConfig, ensure_dirs
from utils import load_jsonl, save_jsonl, get_response, extract_qa, extract_consistency_result, load_culture_type
from prompts import get_augment_prompt, get_filter_prompt

# Define Ray remote function outside the class to avoid serializing the entire class instance
def _ray_process_item(item, region_or_culture, use_region_param, api_config, max_retries, max_trials, augmented_path, filtered_path):
    """Ray remote function to process a single data item"""
    try:
        found_consistent = False
        # Make multiple attempts
        for trial_idx in range(max_trials):
            # Step 2: Data augmentation
            augmented_data = _ray_augment_qa(item, trial_idx, region_or_culture, use_region_param, api_config, max_retries)
            if not augmented_data:
                print(f"Item {item.get('llm_global_opinion_index')}_{item.get('qa_index')} failed augmentation on attempt {trial_idx}")
                continue
                
            # Save augmented data
            save_jsonl(augmented_path, augmented_data)
            
            # Step 3: Value consistency filtering
            consistent, filtered_data = _ray_check_consistency(item, augmented_data, region_or_culture, use_region_param, api_config, max_retries)
            
            # Save filtered data regardless of consistency check result
            if filtered_data:
                # Add attempt number
                filtered_data["trial_idx"] = trial_idx
                # Add a flag indicating whether a consistent result was found
                filtered_data["is_consistent"] = consistent
                # Save filtered data
                save_jsonl(filtered_path, filtered_data)
            
            # If consistency check passes, mark as found and break the loop
            if consistent:
                found_consistent = True
                break
        
        # If all attempts fail, log a warning
        if not found_consistent:
            print(f"Warning: Item {item.get('llm_global_opinion_index')}_{item.get('qa_index')} did not find a consistent result after {max_trials} attempts")
            
        return True
            
    except Exception as e:
        print(f"Error processing item {item.get('llm_global_opinion_index')}_{item.get('qa_index')}: {str(e)}")
        return False

def _ray_augment_qa(item: Dict, trial_idx: int, region_or_culture: str, use_region_param: bool, api_config: APIConfig, max_retries: int) -> Optional[Dict]:
    """Ray remote function to augment QA pairs"""
    start_time = time.time()
    
    question = item['question']
    option = item['option']
    
    # Determine parameter name based on use_region_param
    if use_region_param:
        prompt_kwargs = {"wvs_region": region_or_culture}
    else:
        prompt_kwargs = {"wvs_culture_type": region_or_culture}
    
    # Use template function from prompts.py
    user_prompt = get_augment_prompt(
        original_question=question,
        original_answer=option,
        **prompt_kwargs
    )

    # Build messages
    messages = [
        {"role": "user", "content": user_prompt}
    ]
    
    # Call API
    response = get_response(messages, api_config, max_retries)
    if not response:
        return None
        
    # Extract QA
    qa_data = extract_qa(response)
    if not qa_data.get('question') or not qa_data.get('answer'):
        print(f"Unable to extract QA from response: {response[:100]}...")
        return None
        
    # Build augmented data, add trial_idx field
    augmented_data = {
        "llm_global_opinion_index": item["llm_global_opinion_index"],
        "qa_index": item["qa_index"],
        "trial_idx": trial_idx,  # Add attempt number
        "source": item["source"],
        "original_question": question,
        "original_option": option,
        "model": api_config.model,
        "augmented_question": qa_data.get("question"),
        "augmented_answer": qa_data.get("answer"),
        "cultural_consistency_check": qa_data.get("CulturalConsistencyCheck", ""),
        "augment_prompt": user_prompt,
        "augment_response": response
    }
    
    return augmented_data

def _ray_check_consistency(original_item: Dict, augmented_data: Dict, region_or_culture: str, use_region_param: bool, api_config: APIConfig, max_retries: int) -> Tuple[bool, Optional[Dict]]:
    """Ray remote function to check value consistency"""
    start_time = time.time()
    
    # Build original question and option format
    original_question_answer = f"<Question>{original_item['question']}</Question><Answer>{original_item['option']}</Answer>"
    
    # Determine parameter name based on use_region_param
    if use_region_param:
        prompt_kwargs = {"wvs_region": region_or_culture}
    else:
        prompt_kwargs = {"wvs_culture_type": region_or_culture}
    
    # Use template function from prompts.py
    user_prompt = get_filter_prompt(
        original_question_answer=original_question_answer,
        augment_data_response=augmented_data["augment_response"],
        **prompt_kwargs
    )

    # Build messages
    messages = [
        {"role": "user", "content": user_prompt}
    ]
    
    # Call API
    response = get_response(messages, api_config, max_retries)
    if not response:
        return False, None
        
    # Extract judgment result
    result = extract_consistency_result(response)
    is_consistent = result.get("judge", "").lower() == "consistent"
    
    # Build filtered data
    filtered_data = {
        "llm_global_opinion_index": original_item["llm_global_opinion_index"],
        "qa_index": original_item["qa_index"],
        "trial_idx": augmented_data["trial_idx"],  # Keep the same attempt number
        "source": original_item["source"],
        "original_question": original_item["question"],
        "original_option": original_item["option"],
        "model": api_config.model,
        "final_question": augmented_data["augmented_question"],
        "final_answer": augmented_data["augmented_answer"],
        "consistency_judge": result.get("judge", ""),
        "consistency_analysis": result.get("analysis", ""),
        "consistency_reason": result.get("reason", ""),
        "consistency_prompt": user_prompt,
        "consistency_response": response
    }
    
    return is_consistent, filtered_data

class DataAugmentationProcessor:
    def __init__(self, region: str, api_config: APIConfig, num_cpus: Optional[int] = None, 
                 max_retries: int = 3, max_trials: int = 10, batch_size: int = 10, 
                 max_concurrent_apis: int = 20, use_ray: bool = False,
                 use_region_param: bool = True):
        self.region = region
        self.api_config = api_config
        self.num_cpus = num_cpus or max(1, multiprocessing.cpu_count() - 1)  # Leave one core for the system
        self.max_retries = max_retries
        self.max_trials = max_trials
        self.batch_size = batch_size
        self.max_concurrent_apis = max_concurrent_apis
        self.use_ray = use_ray  # Whether to use Ray
        self.use_region_param = use_region_param  # Whether to use region as parameter instead of culture_type
        
        # Determine whether to use region or culture_type based on choice
        if use_region_param:
            self.region_or_culture = region
        else:
            self.region_or_culture = load_culture_type(region)
        
        # Set paths
        self.input_path = CACHE_PATH / f"{region}.jsonl"
        self.augmented_path = AUGMENTED_PATH / f"{region}.jsonl"
        self.filtered_path = FILTERED_PATH / f"{region}.jsonl"
        
        # Ensure directories exist
        ensure_dirs()
        
        # Add thread pool for I/O operations
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_concurrent_apis)
        
        if not self.use_ray:
            # Only create file lock when not using Ray
            self.manager = multiprocessing.Manager()
            self.file_lock = self.manager.Lock()
        else:
            self.file_lock = None
            
        # Process pool only used for multiprocessing mode, but we're not using multiprocessing now
        self.process_pool = None
        
        # Time statistics
        self.time_stats = {
            'augment_qa': 0.0,
            'filter_qa': 0.0,
            'total': 0.0
        }
        
    def process(self):
        """Execute data augmentation and filtering process"""
        start_time = time.time()
        
        print(f"Starting data augmentation and filtering for region '{self.region}'...")
        print(f"CPU cores: {self.num_cpus}, Batch size: {self.batch_size}, Max API concurrency: {self.max_concurrent_apis}")
        print(f"Using Ray: {self.use_ray}, Using Region parameter: {self.use_region_param}")
        
        # Check if input file exists
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input file not found: {self.input_path}")
            
        # Clean output files (if they exist)
        for path in [self.augmented_path, self.filtered_path]:
            if os.path.exists(path):
                os.remove(path)
                
        # Load cached data
        cached_data = load_jsonl(str(self.input_path))
        
        if self.use_ray:
            # Use Ray for parallel processing
            try:
                import ray
                # Use simple Ray initialization to avoid complex configuration
                if not ray.is_initialized():
                    ray.init(num_cpus=self.num_cpus, ignore_reinit_error=True)
                
                self._process_with_ray(cached_data)
            except Exception as e:
                print(f"Failed to process with Ray: {e}")
                print("Switching to sequential processing mode...")
                self._process_sequentially(cached_data)
        else:
            # Use sequential processing
            self._process_sequentially(cached_data)
            
        # Close thread pool
        self.thread_pool.shutdown()
        
        # Calculate total time
        self.time_stats['total'] = time.time() - start_time
        
        # Print statistics
        print("\nProcessing completed! Time statistics:")
        print(f"Augment QA time: {self.time_stats['augment_qa']:.2f} seconds")
        print(f"Filter QA time: {self.time_stats['filter_qa']:.2f} seconds")
        print(f"Total time: {self.time_stats['total']:.2f} seconds")
        
        print(f"Augmented data saved to: {self.augmented_path}")
        print(f"Filtered data saved to: {self.filtered_path}")
        
    def _process_with_ray(self, data):
        """Use Ray for parallel processing"""
        import ray
        
        # Split data into batches for processing
        batches = [data[i:i+self.batch_size] for i in range(0, len(data), self.batch_size)]
        
        # Use Ray remote decorator to decorate the external processing function
        ray_process_item_remote = ray.remote(_ray_process_item)
        
        # Submit tasks, use string paths to avoid serialization issues
        futures = []
        for batch in batches:
            for item in batch:
                # Only pass necessary parameters, avoid passing self
                future = ray_process_item_remote.remote(
                    item,
                    self.region_or_culture,
                    self.use_region_param,
                    self.api_config,
                    self.max_retries,
                    self.max_trials,
                    str(self.augmented_path),
                    str(self.filtered_path)
                )
                futures.append(future)
            
        # Show progress
        total_items = len(data)
        with tqdm(total=total_items, desc="Processing data items") as pbar:
            while futures:
                # Wait for any task to complete
                done_refs, futures = ray.wait(futures, timeout=1.0, num_returns=1)
                for done_ref in done_refs:
                    try:
                        _ = ray.get(done_ref)
                        pbar.update(1)
                    except Exception as e:
                        print(f"\nTask processing failed: {str(e)}")
                        pbar.update(1)
    
    def _process_sequentially(self, data):
        """Sequential processing of data"""
        total_items = len(data)
        
        # Show progress
        with tqdm(total=total_items, desc="Processing data items") as pbar:
            for item in data:
                try:
                    success = self._process_item_sync(item)
                    pbar.update(1)
                except Exception as e:
                    print(f"\nProcessing item failed: {str(e)}")
                    pbar.update(1)
                    
    def _process_item_sync(self, item: Dict) -> bool:
        """Synchronously process a single data item"""
        try:
            found_consistent = False
            # Make multiple attempts
            for trial_idx in range(self.max_trials):
                # Step 2: Data augmentation (with attempt number)
                augmented_data = self._augment_qa(item, trial_idx)
                if not augmented_data:
                    print(f"Item {item.get('llm_global_opinion_index')}_{item.get('qa_index')} failed augmentation on attempt {trial_idx}")
                    continue
                    
                # Save augmented data (using lock to protect file write, if any)
                if self.file_lock:
                    with self.file_lock:
                        save_jsonl(str(self.augmented_path), augmented_data)
                else:
                    save_jsonl(str(self.augmented_path), augmented_data)
                
                # Step 3: Value consistency filtering
                consistent, filtered_data = self._check_consistency(item, augmented_data)
                
                # Save filtered data regardless of consistency check result
                if filtered_data:
                    # Add attempt number
                    filtered_data["trial_idx"] = trial_idx
                    # Add a flag indicating whether a consistent result was found
                    filtered_data["is_consistent"] = consistent
                    # Save filtered data (using lock to protect file write, if any)
                    if self.file_lock:
                        with self.file_lock:
                            save_jsonl(str(self.filtered_path), filtered_data)
                    else:
                        save_jsonl(str(self.filtered_path), filtered_data)
                
                # If consistency check passes, mark as found and break the loop
                if consistent:
                    found_consistent = True
                    break
            
            # If all attempts fail, log a warning
            if not found_consistent:
                print(f"Warning: Item {item.get('llm_global_opinion_index')}_{item.get('qa_index')} did not find a consistent result after {self.max_trials} attempts")
                
            return True
                
        except Exception as e:
            print(f"Error processing item {item.get('llm_global_opinion_index')}_{item.get('qa_index')}: {str(e)}")
            return False
            
    def _augment_qa(self, item: Dict, trial_idx: int = 0) -> Optional[Dict]:
        """Augment QA pairs, with attempt number"""
        start_time = time.time()
        
        question = item['question']
        option = item['option']
        
        # Determine parameter name based on use_region_param
        if self.use_region_param:
            prompt_kwargs = {"wvs_region": self.region_or_culture}
        else:
            prompt_kwargs = {"wvs_culture_type": self.region_or_culture}
        
        # Use template function from prompts.py
        user_prompt = get_augment_prompt(
            original_question=question,
            original_answer=option,
            **prompt_kwargs
        )

        # Build messages
        messages = [
            {"role": "user", "content": user_prompt}
        ]
        
        # Call API
        response = get_response(messages, self.api_config, self.max_retries)
        if not response:
            return None
            
        # Extract QA
        qa_data = extract_qa(response)
        if not qa_data.get('question') or not qa_data.get('answer'):
            print(f"Unable to extract QA from response: {response[:100]}...")
            return None
            
        # Build augmented data, add trial_idx field
        augmented_data = {
            "llm_global_opinion_index": item["llm_global_opinion_index"],
            "qa_index": item["qa_index"],
            "trial_idx": trial_idx,  # Add attempt number
            "source": item["source"],
            "original_question": question,
            "original_option": option,
            "model": self.api_config.model,
            "augmented_question": qa_data.get("question"),
            "augmented_answer": qa_data.get("answer"),
            "cultural_consistency_check": qa_data.get("CulturalConsistencyCheck", ""),
            "augment_prompt": user_prompt,
            "augment_response": response
        }
        
        self.time_stats['augment_qa'] += time.time() - start_time
        return augmented_data
        
    def _check_consistency(self, original_item: Dict, augmented_data: Dict) -> Tuple[bool, Optional[Dict]]:
        """Check value consistency"""
        start_time = time.time()
        
        # Build original question and option format
        original_question_answer = f"<Question>{original_item['question']}</Question><Answer>{original_item['option']}</Answer>"
        
        # Determine parameter name based on use_region_param
        if self.use_region_param:
            prompt_kwargs = {"wvs_region": self.region_or_culture}
        else:
            prompt_kwargs = {"wvs_culture_type": self.region_or_culture}
        
        # Use template function from prompts.py
        user_prompt = get_filter_prompt(
            original_question_answer=original_question_answer,
            augment_data_response=augmented_data["augment_response"],
            **prompt_kwargs
        )

        # Build messages
        messages = [
            {"role": "user", "content": user_prompt}
        ]
        
        # Call API
        response = get_response(messages, self.api_config, self.max_retries)
        if not response:
            return False, None
            
        # Extract judgment result
        result = extract_consistency_result(response)
        is_consistent = result.get("judge", "").lower() == "consistent"
        
        # Build filtered data
        filtered_data = {
            "llm_global_opinion_index": original_item["llm_global_opinion_index"],
            "qa_index": original_item["qa_index"],
            "trial_idx": augmented_data["trial_idx"],  # Keep the same attempt number
            "source": original_item["source"],
            "original_question": original_item["question"],
            "original_option": original_item["option"],
            "model": self.api_config.model,
            "final_question": augmented_data["augmented_question"],
            "final_answer": augmented_data["augmented_answer"],
            "consistency_judge": result.get("judge", ""),
            "consistency_analysis": result.get("analysis", ""),
            "consistency_reason": result.get("reason", ""),
            "consistency_prompt": user_prompt,
            "consistency_response": response
        }
        
        self.time_stats['filter_qa'] += time.time() - start_time
        return is_consistent, filtered_data