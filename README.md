# A Game-Theoretic Negotiation Framework for Cross-Cultural Consensus in LLMs
## Abstract
The increasing prevalence of large language models (LLMs) is influencing global value systems. However, these models frequently exhibit a pronounced WEIRD (Western, Educated, Industrialized, Rich, Democratic) cultural bias due to lack of attention to minority values. This monocultural perspective may reinforce dominant values and marginalize diverse cultural viewpoints,  posing challenges for the development of equitable and inclusive AI systems. In this work, we introduce a systematic framework designed to boost fair and robust cross-cultural consensus among LLMs. We model consensus as a Nash Equilibrium and employ a game-theoretic negotiation method based on Policy-Space Response Oracles (PSRO) to simulate an organized cross-cultural negotiation process. To evaluate this approach, we construct regional cultural agents using data transformed from the World Values Survey (WVS). Beyond the conventional model-level evaluation method, We further propose two quantitative metrics, Perplexity-based Acceptence and Values Self-Consistency, to assess consensus outcomes. Experimental results indicate that our approach generates consensus of higher quality while ensuring more balanced compromise compared to baselines. Overall, it mitigates WEIRD bias by guiding agents toward convergence through fair and gradual negotiation steps.

## Installation
Clone the source code from GitHub, then setup a conda environment:
```
conda env create -f environment.yml
```

## Cross-Cultural Negotiation

Edit script `script/debate/run_debate.sh` to run our cross-cultural negotiation method or 2 baselines method(debate/consultancy). Then run:
```
bash script/debate/run_debate.sh
```

## Evaluation

### Evaluation on our Regional value agents

### Consensus Evaluation
Edit script `script/eval/consensus_eval.sh`, run:
```
bash script/eval/consensus_eval.sh
```
