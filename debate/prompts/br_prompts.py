# ========================= BR Generator Prompts =========================

# Guideline template format description
GUIDELINE_TEMPLATE: dict = {
    'en': """
Each new guideline must strictly follow the format below, and ensure different guidelines are separated by "---next---" (no other symbols should appear):
Guideline: [guideline content, not exceeding 8 words, concise and clear, without punctuation marks]
Reason: [why this guideline effectively addresses the other party's weaknesses]
Description: [detailed explanation of the guideline]

Please begin your answer using the following format:
---next---
Guideline: [guideline content]
Reason: [reason]
Description: [detailed description]
"""
}

# Opponent strategy weakness analysis prompt
WEAKNESS_ANALYSIS_PROMPT: dict = {
    'en': """
Please analyze the potential weaknesses or limitations of the following cultural guidelines from the other party:

{high_weight_guidelines}

Please identify:
1. Internal contradictions
2. Possible application boundaries
3. Potential value conflicts
4. Implementation difficulties

Please analyze in detail the weaknesses of each guideline and summarize the limitations of the other party's overall strategy.
"""
}

# Coverage gaps analysis prompt
COVERAGE_GAPS_PROMPT: dict = {
    'en': """
Based on the following guidelines from the other party:

{all_guidelines}

Please analyze important areas or value dimensions that these guidelines may ignore or inadequately cover.
Identify 3-5 blind spots or weak links in the other party's guideline system.
"""
}

# Counter guideline generation prompt
COUNTER_GUIDELINE_PROMPT: dict = {
    'en': """
Based on the following weakness analysis of the other party's guidelines:

{weakness_analysis}

Generate 2 cultural guidelines that specifically challenge these weaknesses, with the following requirements:
- Specific and clear
- Reasonable and feasible
- Maximally weakens the effectiveness of the other party's guidelines

{guideline_template}
"""
}

# Gap guideline generation prompt
GAP_GUIDELINE_PROMPT: dict = {
    'en': """
The other party's guidelines do not adequately cover the following areas:

{coverage_gaps}

Generate 2 cultural guidelines that can occupy these uncovered areas, with the following requirements:
- Reasonable and feasible
- Brings unique advantages to our side
- Difficult for the other party to directly refute

{guideline_template}
"""
}

# Innovation guideline generation prompt
INNOVATION_GUIDELINE_PROMPT: dict = {
    'en': """
Beyond the current discussion framework, generate 1 innovative cultural guideline with the following requirements:
- Introduces a completely new perspective or value dimension
- Can restructure the basis of discussion
- Attractive to both parties but more advantageous to our side

{guideline_template}
"""
}