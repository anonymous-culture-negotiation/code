# A Game-Theoretic Negotiation Framework for Cross-Cultural Consensus
## Abstract
Large language models (LLMs) are shaping global values, yet they frequently exhibit a pronounced WEIRD (Western, Educated, Industrialized, Rich, Democratic) cultural bias, marginalizing diverse viewpoints and posing challenges for reconciling diverse populations with varying cultural backgrounds and value systems. In this work, we move beyond simple alignment methods to propose a new paradigm for cross-cultural fairness. We introduce a \textit{Nash Consensus Negotiation} framework under the formulation of cross-cultural consensus as a Nash Equilibrium. Each LLM iteratively proposes and refines natural-language guidelines, guided by a utility function balancing self-consistency with mutual acceptance, while penalizing redundancy. The process expands the proposal space and converges to a consensus, yielding fair and interpretable consensus outcomes. We evaluate our framework against baselines using quantitative metrics, qualitative analysis, and large-scale human studies. Experiments demonstrate that our framework generates higher-quality and more balanced consensus, effectively mitigating assimilation toward WEIRD values. Furthermore, negotiation data finetunes diverse LLM architectures via preference optimization and supervised reasoning, reducing cultural distances by up to 95.53%. Overall, our work offers a principled and systematic path to mitigate cultural bias in LLMs by guiding them toward stable, mutually-acceptable equilibria.

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
