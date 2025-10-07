# ========================= Weight Description Templates =========================

# Weight strength level descriptions
STRENGTH_LEVELS = {
    'en': [
        {"range": (0.0, 0.1), "level": "very low", "descriptor": "barely consider", 
         "modifiers": ["marginal", "negligible", "minimal"]},
        {"range": (0.1, 0.3), "level": "low", "descriptor": "pay less attention to", 
         "modifiers": ["secondary", "supplementary", "low priority"]},
        {"range": (0.3, 0.5), "level": "medium", "descriptor": "moderately value", 
         "modifiers": ["balanced", "moderate", "partially emphasize"]},
        {"range": (0.5, 0.7), "level": "high", "descriptor": "highly value", 
         "modifiers": ["prioritize", "primary", "significant"]},
        {"range": (0.7, 1.0), "level": "very high", "descriptor": "fundamentally uphold", 
         "modifiers": ["essential", "non-negotiable", "highest priority"]}
    ]
}

# Weight change descriptions
CHANGE_LEVELS = {
    'en': [
        {"range": (-float('inf'), -0.2), "descriptor": "significantly decreased", 
         "templates": ["greatly reduced emphasis on {guideline}", "noticeably diminished the weight of {guideline}"]},
        {"range": (-0.2, -0.05), "descriptor": "slightly decreased", 
         "templates": ["slightly reduced focus on {guideline}", "somewhat lowered the importance of {guideline}"]},
        {"range": (-0.05, 0.05), "descriptor": "remained stable", 
         "templates": ["maintained consistent position on {guideline}", "continued the importance of {guideline}"]},
        {"range": (0.05, 0.2), "descriptor": "slightly increased", 
         "templates": ["slightly enhanced focus on {guideline}", "somewhat raised the priority of {guideline}"]},
        {"range": (0.2, float('inf')), "descriptor": "significantly increased", 
         "templates": ["greatly elevated the core status of {guideline}", "significantly strengthened the weight of {guideline}"]}
    ]
}

# Relative position description templates
POSITION_TEMPLATES = {
    'en': {
        "top": ["The core of our position is {guideline}", "What we value most is {guideline}"],
        "high": ["We also highly focus on {guideline}", "We similarly value {guideline}"],
        "middle": ["In our balanced consideration, we believe {guideline} holds certain importance"],
        "low": ["As a supplementary consideration, we also mention {guideline}", "Lower priority is given to {guideline}"]
    }
}

# Distribution feature description templates
DISTRIBUTION_TEMPLATES = {
    'en': {
        "concentrated": "Our position is highly focused on {top_guideline}",
        "polarized": "Our position mainly revolves around two core guidelines: {top_two_guidelines}",
        "balanced": "We maintain a relatively balanced position among multiple guidelines",
        "gradient": "Our guidelines' importance presents a clear priority gradient"
    }
}

# Opening templates
OPENING_TEMPLATES = {
    'en': {
        "concentrated": "In this round of negotiation, our position is highly concentrated, emphasizing a single core value.",
        "polarized": "In this round of negotiation, our position shows a dual-core structure, focusing on two main aspects.",
        "balanced": "In this round of negotiation, our position presents a relatively balanced feature, considering multiple factors.",
        "gradient": "In this round of negotiation, our position presents a clear priority sequence, with guideline weights decreasing progressively."
    }
}

# Summary templates
SUMMARY_TEMPLATES = {
    'en': {
        "concentrated": "Overall, our position strongly emphasizes the core status of {top_guideline}, with other factors serving only as auxiliary considerations.",
        "polarized": "Overall, our position revolves around two core points: {top_two_guidelines}, seeking balance between these two aspects.",
        "balanced": "Overall, our position reflects a balanced consideration of multiple values, without overemphasizing any single factor.",
        "gradient": "Overall, our position arranges the importance of each guideline according to a clear priority sequence, forming a reasonable gradient."
    }
}

# Trend arrow symbols
TREND_ARROWS = {
    'en': {
        "significantly decreased": "↓↓",
        "slightly decreased": "↓",
        "remained stable": "→",
        "slightly increased": "↑",
        "significantly increased": "↑↑"
    }
}

# Weight consistency check warning messages
CONSISTENCY_WARNING_MESSAGES = {
    'en': {
        "sum_error": "Weight sum is {weight_sum:.2f}, which deviates from the expected 1.0",
        "change_too_large": "Guideline '{guideline}' weight change is too large ({prev_weight:.2f}→{curr_weight:.2f})",
        "too_many_guidelines": "Too many guidelines ({count}), which may affect clarity of expression"
    }
}

# Special case descriptions
SPECIAL_CASE_MESSAGES = {
    'en': {
        "new_guideline": "A newly proposed guideline from our side, with an initial weight of {weight:.2f}",
        "abandoned": "We have completely abandoned our insistence on this guideline",
        "core_principle": "We regard this guideline as an absolute core, non-negotiable principle"
    }
}

# Low weight guideline description template
LOW_WEIGHT_TEMPLATE = {
    'en': "barely consider {guideline}{weight_text}{change_text}"
}

# General guideline description template
GENERAL_GUIDELINE_TEMPLATE = {
    'en': "Regarding {guideline}, we {strength}{weight_text}{change_text}"
}

# Trend change descriptions
TREND_CHANGE_DESCRIPTIONS = {
    'en': {
        "increase": " Compared to the previous round, our overall position shows adjustment and reinforcement.",
        "decrease": " Compared to the previous round, our overall position shows compromise and concession.",
        "stable": " Compared to the previous round, our overall position remains stable.",
        "conclusion": " We look forward to seeking consensus on this basis."
    }
}

# Description structure templates
DESCRIPTION_STRUCTURE = {
    'en': {
        "core_section": "**Core Position**: {content}",
        "secondary_section": "**Secondary Considerations**: {content}",
        "summary_section": "**Summary**: {content}"
    }
}