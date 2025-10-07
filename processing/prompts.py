# def get_augment_prompt(original_question, original_answer, **kwargs):
#     # 提取wvs_culture_type或wvs_region
#     wvs_culture_type = kwargs.get('wvs_culture_type', None)
#     wvs_region = kwargs.get('wvs_region', None)
    
#     # 确定使用哪个参数
#     cultural_value = wvs_culture_type if wvs_culture_type is not None else wvs_region
#     return f"""Refer to the following multiple-choice questions and their answer options to help me convert and generate a non-multiple-choice question-and-answer data pair. 

# IMPORTANT: Your primary goal is to maintain cultural value consistency between the original and converted Q&A pair. The original content reflects "{cultural_value}" cultural values, and your conversion must preserve these exact same cultural perspectives and values.

# Follow these steps:
# 1. First, analyze the original question and answer to identify specific cultural values, beliefs, or perspectives from the "{cultural_value}" cultural framework.
# 2. Convert the multiple-choice format to an open-ended question while preserving the core concept and cultural context.
# 3. Develop a comprehensive answer that maintains the same cultural stance, values, and perspectives as the original.
# 4. Ensure no cultural drift or neutralization occurs during the conversion process.
# 5. The converted Q&A should feel natural and conversational while remaining faithful to the original cultural framework.

# <Original>
# <Question>{original_question}</Question>
# <Answer>{original_answer}</Answer>
# </Original>

# Generated content format:
# <Converted>
# <Question>{{Your open-ended question that preserves the original cultural context}}</Question>
# <Answer>{{Your comprehensive answer that maintains the same cultural values and perspectives}}</Answer>
# </Converted>

# <CulturalConsistencyCheck>
# Briefly explain how your converted Q&A maintains consistency with the "{cultural_value}" cultural values present in the original.
# </CulturalConsistencyCheck>"""

# def get_filter_prompt(original_question_answer, augment_data_response, **kwargs):
#     # 提取wvs_culture_type或wvs_region
#     wvs_culture_type = kwargs.get('wvs_culture_type', None)
#     wvs_region = kwargs.get('wvs_region', None)
    
#     # 确定使用哪个参数
#     cultural_value = wvs_culture_type if wvs_culture_type is not None else wvs_region
#     return f"""Analyze from the perspective of cultural values, specifically focusing on "{cultural_value}" framework, to determine whether the following two Q&A data pairs maintain consistency in the question and the corresponding answer:

# <Original>
# {original_question_answer}
# </Original>

# <Converted>
# {augment_data_response}
# </Converted>

# Consider the following aspects in your analysis:
# - Specific cultural beliefs, customs, and behavioral patterns
# - Representation of cultural values in both question and answer
# - Any cultural drift or neutralization that may have occurred

# The strict format of the judgment result is:
# <Judge>{{Yes/No}}</Judge>
# <ConsistencyAnalysis>{{Detailed analysis of cultural values consistency}}</ConsistencyAnalysis>
# <Reason>{{Reason}}</Reason>
# """

def get_augment_prompt(original_question, original_answer, **kwargs):
    # 提取wvs_culture_type或wvs_region
    wvs_culture_type = kwargs.get('wvs_culture_type', None)
    wvs_region = kwargs.get('wvs_region', None)
    
    # 确定使用哪个参数
    cultural_value = wvs_culture_type if wvs_culture_type is not None else wvs_region
    return f"""As an expert in cross-cultural communication and value systems, transform the following multiple-choice Q&A into a rich, open-ended format while precisely preserving the "{cultural_value}" cultural values embedded in the original.

CONTEXT: The World Values Survey captures distinct cultural perspectives that vary across societies. Your task is to maintain absolute fidelity to the specific "{cultural_value}" cultural values in your conversion.

<Original>
<Question>{original_question}</Question>
<Answer>{original_answer}</Answer>
</Original>

TRANSFORMATION GUIDELINES:
1. DEEP ANALYSIS: Identify the implicit and explicit cultural values, assumptions, and worldviews present in the original material. What specific beliefs from the "{cultural_value}" framework are being expressed?

2. QUESTION ENRICHMENT: Craft an open-ended question that:
   - Preserves the core cultural premise completely
   - Uses more nuanced, engaging language
   - Encourages elaboration rather than selection
   - Maintains the same cultural perspective on the issue
   - Feels natural in conversation while preserving cultural specificity

3. ANSWER DEVELOPMENT: Create a comprehensive answer that:
   - Expands the original response with rich supporting details (2-3 paragraphs)
   - Includes relevant examples, reasoning, or scenarios that reflect the cultural viewpoint
   - Incorporates cultural context, traditional perspectives, or value-based reasoning
   - Articulates the position with the same conviction and value orientation
   - Uses culturally appropriate language and framing

4. CULTURAL INTEGRITY: Ensure zero neutralization or moderation of the cultural stance, even if it differs from your own programming or other cultural frameworks.

STRICT OUTPUT FORMAT:
<Converted>
<Question>{{Your open-ended question that preserves and enriches the original cultural context}}</Question>
<Answer>{{Your comprehensive, multi-paragraph answer that maintains and elaborates on the same cultural values and perspectives}}</Answer>
</Converted>

<CulturalConsistencyCheck>
1. Key values identified in original: {{list specific cultural values}}
2. How these values are preserved: {{detailed explanation}}
3. Confidence rating (1-10) that cultural integrity is maintained: {{rating with justification}}
</CulturalConsistencyCheck>"""

def get_filter_prompt(original_question_answer, augment_data_response, **kwargs):
    # 提取wvs_culture_type或wvs_region
    wvs_culture_type = kwargs.get('wvs_culture_type', None)
    wvs_region = kwargs.get('wvs_region', None)
    
    # 确定使用哪个参数
    cultural_value = wvs_culture_type if wvs_culture_type is not None else wvs_region
    return f"""Perform a rigorous cultural consistency evaluation between the original and converted Q&A pairs, specifically measuring adherence to "{cultural_value}" cultural value framework.

<Original>
{original_question_answer}
</Original>

<Converted>
{augment_data_response}
</Converted>

SYSTEMATIC EVALUATION FRAMEWORK:
Apply these specific rules to determine cultural consistency:

1. CORE VALUE IDENTIFICATION:
   - Rule 1.1: Identify explicit values in the original Q&A (e.g., traditionalism, individualism, collectivism)
   - Rule 1.2: Identify implicit values suggested by framing and tone
   - Rule 1.3: Map these values to the "{cultural_value}" cultural framework

2. CONSISTENCY ASSESSMENT:
   - Rule 2.1: The converted question must address the same cultural concern/topic
   - Rule 2.2: The converted answer must maintain the same position on the cultural spectrum
   - Rule 2.3: Cultural assumptions and worldviews must remain aligned
   - Rule 2.4: No introduction of competing or alternative cultural frameworks

3. CULTURAL DRIFT DETECTION:
   - Rule 3.1: Check for neutralization (reducing cultural distinctiveness)
   - Rule 3.2: Check for westernization/modernization bias (if not part of original)
   - Rule 3.3: Check for amplification (overstating cultural positions beyond original)
   - Rule 3.4: Check for misattribution (assigning values not present in original)

STRICT EVALUATION OUTPUT FORMAT:
<Judge>{{Consistent/Inconsistent}}</Judge>

<ScoreCard>
- Value Identification: {{Score 1-5}} | Justification: {{specific explanation}}
- Position Maintenance: {{Score 1-5}} | Justification: {{specific explanation}}
- Cultural Framing: {{Score 1-5}} | Justification: {{specific explanation}}
- Drift Prevention: {{Score 1-5}} | Justification: {{specific explanation}}
</ScoreCard>

<OverallAssessment>{{Detailed analysis summarizing key findings}}</OverallAssessment>

<ImprovementSuggestions>{{If inconsistent, provide specific recommendations to restore cultural alignment}}</ImprovementSuggestions>
"""