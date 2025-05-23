import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from debate.prompts.prompts import GUIDELINE_WEIGHT_DESC_PROMPT
from debate.prompts.guideline_desc_templete import (
    STRENGTH_LEVELS,
    CHANGE_LEVELS,
    POSITION_TEMPLATES,
    DISTRIBUTION_TEMPLATES,
    OPENING_TEMPLATES,
    SUMMARY_TEMPLATES,
    TREND_ARROWS,
    CONSISTENCY_WARNING_MESSAGES,
    SPECIAL_CASE_MESSAGES,
    LOW_WEIGHT_TEMPLATE,
    GENERAL_GUIDELINE_TEMPLATE,
    TREND_CHANGE_DESCRIPTIONS,
    DESCRIPTION_STRUCTURE
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeightDescriptionGenerator:
    """
    System for converting numerical weights into natural language descriptions
    """
    
    def __init__(self, language: str = 'zh'):
        """
        Initialize the weight description generator
        
        Args:
            language: Language to use, 'zh' for Chinese, 'en' for English
        """
        self.language = language
        
        # Load rule templates from template file
        self.strength_levels = STRENGTH_LEVELS[language]
        self.change_levels = CHANGE_LEVELS[language]
        self.position_templates = POSITION_TEMPLATES[language]
        self.distribution_templates = DISTRIBUTION_TEMPLATES[language]
        self.opening_templates = OPENING_TEMPLATES[language]
        self.summary_templates = SUMMARY_TEMPLATES[language]
        self.trend_arrows = TREND_ARROWS[language]
        self.consistency_messages = CONSISTENCY_WARNING_MESSAGES[language]
        self.special_case_messages = SPECIAL_CASE_MESSAGES[language]
        self.low_weight_template = LOW_WEIGHT_TEMPLATE[language]
        self.general_guideline_template = GENERAL_GUIDELINE_TEMPLATE[language]
        self.trend_descriptions = TREND_CHANGE_DESCRIPTIONS[language]
        self.description_structure = DESCRIPTION_STRUCTURE[language]
    
    def get_strength_level(self, weight: float) -> Dict[str, Any]:
        """Get the strength level description corresponding to the weight"""
        for level in self.strength_levels:
            if level["range"][0] <= weight < level["range"][1]:
                return level
        # Default to the highest level (handle boundary cases)
        return self.strength_levels[-1]
    
    def get_change_description(self, current_weight: float, previous_weight: float) -> Dict[str, Any]:
        """Get the description of weight change"""
        change = current_weight - previous_weight
        for level in self.change_levels:
            if level["range"][0] <= change < level["range"][1]:
                return level
        # Default to the highest change level
        return self.change_levels[-1] if change >= 0 else self.change_levels[0]
    
    def analyze_distribution(self, weights: Dict[str, float]) -> str:
        """Analyze the distribution characteristics of weights"""
        weight_values = list(weights.values())
        
        # Check if highly concentrated
        if max(weight_values) >= 0.6:
            return "concentrated"
        
        # Check if polarized
        sorted_weights = sorted(weight_values, reverse=True)
        if len(sorted_weights) >= 2 and sorted_weights[0] + sorted_weights[1] >= 0.7:
            return "polarized"
        
        # Check if relatively balanced
        if np.std(weight_values) <= 0.15:
            return "balanced"
        
        # Check if gradually decreasing
        if len(sorted_weights) >= 3:
            ratios = [sorted_weights[i] / sorted_weights[i+1] for i in range(len(sorted_weights)-1)]
            if max(ratios) - min(ratios) <= 0.3:  # Ratios are relatively consistent
                return "gradient"
        
        # Default to balanced
        return "balanced"
    
    def check_weight_consistency(self, current_weights: Dict[str, float], 
                               previous_weights: Optional[Dict[str, float]] = None, 
                               guidelines: List[str]|None = None) -> List[str]:
        """Check the consistency and rationality of weights"""
        warnings = []
        
        # 1. Check if the sum of weights is 1
        weight_sum = sum(current_weights.values())
        if abs(weight_sum - 1.0) > 0.02:
            warnings.append(self.consistency_messages["sum_error"].format(weight_sum=weight_sum))
        
        # 2. Check if weight changes are too large
        if previous_weights:
            for g in current_weights:
                if g in previous_weights and abs(current_weights[g] - previous_weights[g]) > 0.3:
                    warnings.append(self.consistency_messages["change_too_large"].format(
                        guideline=g, 
                        prev_weight=previous_weights[g], 
                        curr_weight=current_weights[g]
                    ))
        
        # 3. Check if there are too many guidelines
        if len(current_weights) > 7:
            warnings.append(self.consistency_messages["too_many_guidelines"].format(count=len(current_weights)))
        
        return warnings
    
    def get_position_description(self, guideline: str, position: int, total: int) -> str:
        """Get the description template based on the position of the guideline in the ranking"""
        if position == 0:
            return np.random.choice(self.position_templates["top"]).format(guideline=guideline)
        elif position <= total * 0.3:
            return np.random.choice(self.position_templates["high"]).format(guideline=guideline)
        elif position <= total * 0.7:
            return np.random.choice(self.position_templates["middle"]).format(guideline=guideline)
        else:
            return np.random.choice(self.position_templates["low"]).format(guideline=guideline)
    
    def handle_special_cases(self, guideline: str, current_weight: float, 
                           previous_weights: Optional[Dict[str, float]] = None) -> Optional[str]:
        """Handle special cases"""
        # New guideline
        if previous_weights is not None and guideline not in previous_weights:
            return self.special_case_messages["new_guideline"].format(weight=current_weight)
        
        # Weight reduced to zero
        if previous_weights and guideline in previous_weights and previous_weights[guideline] > 0 and current_weight == 0:
            return self.special_case_messages["abandoned"]
        
        # Extreme weight
        if current_weight > 0.8:
            return self.special_case_messages["core_principle"]
        
        return None
    
    def generate_description(self, current_weights: Dict[str, float], 
                           previous_weights: Optional[Dict[str, float]] = None,
                           include_arrows: bool = True,
                           include_numeric: bool = True) -> str:
        """Generate a complete weight description text"""
        # 1. Check weight rationality
        warnings = self.check_weight_consistency(current_weights, previous_weights)
        for warning in warnings:
            logging.warning(warning)
        
        # 2. Analyze distribution characteristics
        distribution_feature = self.analyze_distribution(current_weights)
        
        # 3. Sort guidelines by weight
        sorted_guidelines = [(g, current_weights[g]) for g in current_weights]
        sorted_guidelines.sort(key=lambda x: x[1], reverse=True)
        
        # 4. Generate opening
        opening = self.opening_templates[distribution_feature]
        
        # 5. Generate core guideline descriptions
        core_descriptions = []
        for i, (g, w) in enumerate(sorted_guidelines[:min(2, len(sorted_guidelines))]):
            # Get strength description
            strength = self.get_strength_level(w)
            
            # Get change description
            change_text = ""
            if previous_weights and g in previous_weights:
                change = self.get_change_description(w, previous_weights[g])
                change_text = f", compare to last round {change['descriptor']}"
                if include_arrows:
                    change_text += f" {self.trend_arrows[change['descriptor']]}"
            
            # Check special cases
            special_case = self.handle_special_cases(g, w, previous_weights)
            if special_case:
                description = f"{g}({special_case})"
            else:
                weight_text = f"(weight{w:.2f})" if include_numeric else ""
                description = f"We{strength['descriptor']}{g}{weight_text}{change_text}"
            
            core_descriptions.append(description)
        
        # 6. Generate secondary guideline descriptions
        secondary_descriptions = []
        for i, (g, w) in enumerate(sorted_guidelines[min(2, len(sorted_guidelines)):]):
            # Get strength description
            strength = self.get_strength_level(w)
            
            # Get change description
            change_text = ""
            if previous_weights and g in previous_weights:
                change = self.get_change_description(w, previous_weights[g])
                change_text = f",{change['descriptor']}"
                if include_arrows:
                    change_text += f" {self.trend_arrows[change['descriptor']]}"
            
            # Check special cases
            special_case = self.handle_special_cases(g, w, previous_weights)
            if special_case:
                description = f"{g}({special_case})"
            else:
                weight_text = f"(weight:{w:.2f})" if include_numeric else ""
                if w < 0.1:  # Simplified processing for very low weights
                    description = self.low_weight_template.format(
                        guideline=g,
                        weight_text=weight_text,
                        change_text=change_text
                    )
                else:
                    description = self.general_guideline_template.format(
                        guideline=g,
                        strength=strength['descriptor'],
                        weight_text=weight_text,
                        change_text=change_text
                    )
            
            secondary_descriptions.append(description)
        
        # 7. Generate summary
        if distribution_feature == "concentrated":
            top_guideline = sorted_guidelines[0][0]
            summary = self.summary_templates[distribution_feature].format(top_guideline=top_guideline)
        elif distribution_feature == "polarized" and len(sorted_guidelines) >= 2:
            top_two = f"{sorted_guidelines[0][0]} and {sorted_guidelines[1][0]}"
            summary = self.summary_templates[distribution_feature].format(top_two_guidelines=top_two)
        else:
            summary = self.summary_templates[distribution_feature]
        
        # Add trend summary
        if previous_weights:
            # Calculate overall trend
            increases = sum(1 for g in current_weights if g in previous_weights and current_weights[g] > previous_weights[g])
            decreases = sum(1 for g in current_weights if g in previous_weights and current_weights[g] < previous_weights[g])
            
            if increases > decreases:
                summary += self.trend_descriptions["increase"]
            elif decreases > increases:
                summary += self.trend_descriptions["decrease"]
            else:
                summary += self.trend_descriptions["stable"]
        
        summary += self.trend_descriptions["conclusion"]
        
        # 8. Combine full description
        core_section = self.description_structure["core_section"].format(content=' '.join(core_descriptions))
        full_description = f"{opening}\n\n{core_section}\n\n"
        
        if secondary_descriptions:
            secondary_section = self.description_structure["secondary_section"].format(
                content=' '.join(secondary_descriptions)
            )
            full_description += f"{secondary_section}\n\n"
        
        summary_section = self.description_structure["summary_section"].format(content=summary)
        full_description += summary_section
        
        return full_description


def generate_weight_prompt(current_weights: Dict[str, float], 
                          guidelines: Dict[str, str], 
                          culture: str,
                          previous_weights: Optional[Dict[str, float]] = None,
                          round_num: int = 1,
                          language: str = 'zh') -> str:
    """
    生成用于LLM的权重描述prompt
    
    参数:
        current_weights: 当前准则权重
        guidelines: 准则内容字典 {准则ID: 准则详细描述}
        culture: 玩家代表的文化
        previous_weights: 上一轮准则权重(可选)
        round_num: 当前轮次
        language: 使用的语言,'zh'表示中文,'en'表示英文
    
    返回:
        用于LLM的prompt字符串
    """
    # 实例化权重描述生成器
    generator = WeightDescriptionGenerator(language)
    
    # 生成权重描述
    weight_description = generator.generate_description(
        current_weights=current_weights,
        previous_weights=previous_weights,
        include_arrows=True,
        include_numeric=True
    )
    
    # 构建完整的准则描述
    guidelines_text = "\n".join([f"- {g_id}: {g_text}" for g_id, g_text in guidelines.items()])
    
    # 构建prompt
    prompt = GUIDELINE_WEIGHT_DESC_PROMPT[language].format(
        guidelines_text=guidelines_text,
        weight_description=weight_description,
        culture=culture,
        round_num=round_num
    )

    return prompt


# 示例用法
if __name__ == "__main__":
    # 示例主题
    topic = "文化遗产保护与现代化发展平衡"
    
    # 示例准则
    guidelines = {
        "传统保护": "保护传统文化遗产是维系文化认同的基础",
        "多样性": "促进文化多样性是社会和谐的重要保障",
        "少数权益": "保障少数族群文化权利是多元社会的基本要求",
        "创新发展": "推动文化创新是文化生命力的源泉"
    }
    
    # 当前轮次权重
    current_weights = {
        "传统保护": 0.45,
        "多样性": 0.30,
        "少数权益": 0.15,
        "创新发展": 0.10
    }
    
    # 上一轮权重
    previous_weights = {
        "传统保护": 0.35,
        "多样性": 0.40,
        "少数权益": 0.15,
        "创新发展": 0.10
    }
    
    # 生成prompt
    prompt = generate_weight_prompt(
        current_weights=current_weights,
        guidelines=guidelines,
        previous_weights=previous_weights,
        culture="A",
        round_num=3
    )
    
    print("生成的Prompt:")
    print("="*80)
    print(prompt)
    print("="*80)
    
    # 直接生成权重描述(不包含完整prompt)
    generator = WeightDescriptionGenerator()
    description = generator.generate_description(current_weights, previous_weights)
    
    print("\n生成的权重描述:")
    print("-"*80)
    print(description)
    print("-"*80)

    # 测试英文版本
    generator_en = WeightDescriptionGenerator('en')
    description_en = generator_en.generate_description(current_weights, previous_weights)
    
    print("\nEnglish Weight Description:")
    print("-"*80)
    print(description_en)
    print("-"*80)