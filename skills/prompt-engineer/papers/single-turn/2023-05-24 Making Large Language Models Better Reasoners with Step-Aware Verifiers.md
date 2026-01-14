# Abstract

Few-shot learning is a challenging task that requires language models to generalize from limited examples. Large language models like GPT-3 and PaLM have made impressive progress in this area, but they still face difficulties in reasoning tasks such as GSM8K, a benchmark for arithmetic problems. To improve their reasoning skills, previous work has proposed to guide the language model with prompts that elicit a series of reasoning steps before giving the final answer, achieving a significant improvement on GSM8K from ```latex $17.9\%$ ``` to ```latex $58.1\%$ ``` in problem-solving rate. In this paper, we present DiVeRSe (Diverse Verifier on Reasoning Step), a novel approach that further enhances the reasoning capability of language models. DiVeRSe has three main components: first, it generates diverse prompts to explore different reasoning paths for the same question; second, it uses a verifier to filter out incorrect answers based on a weighted voting scheme; and third, it verifies each reasoning step individually instead of the whole chain. We evaluate DiVeRSe on the latest language model *code-davinci-002* and show that it achieves new state-of-the-art results on six of eight reasoning benchmarks (e.g., GSM8K ```latex $74.4\% \to 83.2\%$ ```).

# Introduction

Large pretrained language models (PLMs) have shown remarkable performance on various natural language processing tasks, either by few-shot learning with prompts [radford2019language; le2021many; jin-etal-2022-good] or by fine-tuning [houlsby2019parameter; hu2021lora; he2022towards]. However, despite the increasing size and capacity of PLMs such as GPT-3 with 175B parameters [brown2020language] and PaLM with 540B parameters [chowdhery2022palm], their reasoning abilities are still limited and often require multiple steps to produce correct answers, especially for tasks involving arithmetic, commonsense, or inductive reasoning [cobbe2021training].

Recent works [wei2022chain; least2most; fewshotreason2022; lampinen2022can] have demonstrated that PLMs possess some latent reasoning capabilities, but they need carefully designed prompts to activate them. For instance, wei2022chain proposed chain-of-thought reasoning, which inserts multi-step reasoning paths before generating the final answers, and achieved significant improvement on the GSM8K arithmetic benchmark [cobbe2021training]. selfconsistency further introduced a voting mechanism to select the most consistent answer among different reasoning paths, and achieved state-of-the-art results on several reasoning benchmarks using the PaLM model [chowdhery2022palm]. Building on these successes, this paper continues this line of research and advances the reasoning capabilities of PLMs in three aspects.

[IMAGE: figures/ours.pdf - Our proposed method, DiVeRSe (Diverse Verifier on Reasoning Step).]

**Chain-of-thought reasoning example for GSM8K math word problem:**

**Q**: If there are 3 cars in the parking lot and 2 more cars arrive, how many cars are in the parking lot?

**A**: There are 3 cars in the parking lot already. 2 more arrive. Now there are 3 + 2 = 5 cars. The answer is 5.

...

**Q**: Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder for $2 per egg. How much does she make every day?

**A**: She has 16 - 3 - 4 = 9 eggs left. So she makes ```latex $2 * 9=$ ```18 per day. The answer is 18.

The prompt is colored black and the reasoning path produced by the language model is colored teal. This reasoning path contains two reasoning steps.

First, we propose to increase the diversity of reasoning paths by not only sampling from a single prompt, but also varying the prompt itself. We hypothesize that different prompts can elicit different ways of thinking, while the correct answer should be robust to these variations. Second, we propose to use a verifier to score the quality of each reasoning path and guide the voting mechanism. We argue that not all reasoning paths are equally good or reliable, and some may contain errors or inconsistencies that can be detected by the verifier. Third, we propose to assign a fine-grained label to each step of the reasoning path and use a step-aware verifier to attribute the correctness or wrongness of the final answer to each step. We conjecture that some steps may be correct but followed by wrong steps or vice versa, and identifying these cases can help diagnose and improve the reasoning process.

We name our method as DiVeRSe (diverse verifier on reasoning step) and evaluate it on eight reasoning benchmarks that require different types of reasoning skills. We use three OpenAI PLMs (*davinci*, *text-davinci-002*, and *code-davinci-002*) and compare our results with recent state-of-the-art methods. We find that DiVeRSe can consistently and significantly improve the performance of PLMs on these tasks, and achieve new state-of-the-art results on six of them: GSM8K (```latex $74.4\% \to 83.2\%$ ```), AsDiv (```latex $81.9\% \to 88.7\%$ ```), MultiArith (```latex $99.3\% \to 99.8\%$ ```), SVAMP(```latex $86.6\% \to 87.0\%$ ```), SingleEq (```latex $79.5\% \to 94.9\%$ ```), and CLUTRR (```latex $67.0\%\to 95.9\%$ ```).

Our data is publicly available at <https://github.com/microsoft/DiVeRSe>.

# Diverse Verifier on Reasoning Step

The overview of DiVeRSe has three key insights: (1) leveraging *diverse prompts* to induce more diverse reasoning paths from the language models; (2) training a *voting verifier* to better derive the final answers from multiple reasoning paths; (3) leveraging *step correctness* to further boost the voting verifier.

## Diverse Prompts

To reason effectively, it is beneficial to explore diverse reasoning paths, following the idea that "*All Roads lead to Rome*". selfconsistency proposed to generate various reasoning paths from language models by *sampling decoding*. However, their method relies on a fixed set of exemplars for all prompts, which may introduce bias and limit the diversity of the generated reasoning paths. To address this issue, we randomly select ```latex $M_1$ ``` different prompts for each question, and then sample ```latex $M_2$ ``` reasoning paths for each prompt using sampling decoding. This way, we obtain ```latex $M=M_1\times M_2$ ``` diverse reasoning paths for each question. Our main experiments use ```latex $M_1=5$ ``` and ```latex $M_2=20$ ```.

## Voting Verifier

#### Verifier.

The verifier takes a question and a candidate reasoning path as input, and outputs the probability that the reasoning path leads to the correct answer. We use *deberta-v3-large* [he2021deberta] as the backbone model, with a small scalar head that outputs predictions on the **[CLS]** token.

#### Training the verifier.

For each training question, we generate multiple candidate reasoning paths using chain-of-thought reasoning. We regard the reasoning paths that match the ground truth final answer as positive, and the others as negative.

#### Voting Verifier.

selfconsistency use *majority voting* to aggregate the predictions of different reasoning paths. This method may fail when the majority of the reasoning paths are misled, while the minority of the reasoning paths are reasonable. We propose *voting verifier*, which leverages both *voting* and *verifier*:

```latex
$$\begin{equation}
\hat{\mathbf{y}}=\underset{\mathbf{y}}{\arg\max}\sum_{i=1}^M{\mathbbm{1}_{\mathbf{y}_i=\mathbf{y}}\cdot f(\mathbf{x}_i,\mathbf{z}_i,\mathbf{y}_i)},
\end{equation}$$
```

where ```latex $\mathbbm{1}_{\mathbf{y}_i=\mathbf{y}}$ ``` is an indicator function that returns 1 (or 0) if ```latex $\mathbf{y}_i=\mathbf{y}$ ``` (or not), and ```latex $f(\cdot)$ ``` is the probability produced by the verifier.

[IMAGE: figures/stepwise.pdf - How step-level labels are extracted. This figure shows four reasoning paths for a math word problem: the first two are positive and the bottom two are negative. The path 7 -> 9 -> 18 means that the first step calculates 7, the second step calculates 9, and the third step calculates the final answer 18. For the last path, the third step (which calculates 8) has never occurred in any positive reasoning paths, thus we regard this step and all steps after it as negative steps.]

## Step-aware Voting Verifier

Each reasoning path consists of several steps. We hypothesize that not all the steps in an incorrect reasoning path are equally wrong, and some steps may still be useful for reasoning. To exploit this, we extend the voting verifier to a step-aware voting verifier by introducing an extended loss function:

```latex
$$\begin{equation}
\begin{split}
\mathcal{L} & = \mathcal{L}_0 + \alpha\cdot\mathcal{L}_1, \\
\mathcal{L}_1 = \sum_{i=1}^{|\hat{D}|}\sum_{j=1}^{|S_i|}&\text{BCE}(\text{label}_{i,j}, f'(\text{input}_i, j)).
\end{split}
\end{equation}$$
```

```latex $\alpha$ ``` is a hyperparameter to balance the original loss ```latex $\mathcal{L}_0$ ``` and the step-level auxiliary loss ```latex $\mathcal{L}_1$ ```; ```latex $S_{i,1}, S_{i,2}, ..., S_{i,|S_i|}$ ``` are the steps in ```latex $\mathbf{z}_i$ ```; ```latex $\text{label}_{i,j}$ ``` indicates whether ```latex $S_{i,j}$ ``` is correct or not; ```latex $f'(\text{input}_i, j)$ ``` represents the probability of the positive label for ```latex $S_{i,j}$ ```. Specifically, ```latex $f'(\text{input}_i, j)$ ``` is predicted from the hidden state of the last token of ```latex $S_{i,j}$ ``` in deberta-v3-large, similar to token classification tasks.

**To obtain the step-level labels** (i.e., ```latex $\text{label}_{i,j}$ ```) for negative training data with wrong answers, we design an algorithm that compares intermediate results among steps in positive/negative reasoning paths. This algorithm can not only work on math word problems, but also generalize to other reasoning tasks: we use an off-the-shelf natural language inference model, *roberta-large-mnli* [liu2019roberta], to check whether two reasoning steps are semantically equivalent or not. Given a reasoning step, if we cannot find any semantically equivalent step in the positive reasoning paths, we label it and all the subsequent steps as negative steps.

# Experimental Setup

## Reasoning Tasks

#### Arithmetic Reasoning.

Following selfconsistency, we use AsDiv [miao2020diverse], SingleEq [koncel2015parsing], MultiArith [roy2015solving], SVAMP [patel2021nlp], and GSM8K [cobbe2021training].

#### Commonsense Reasoning.

Following selfconsistency, we use CommonsenseQA [talmor2019commonsenseqa] and StrategyQA [geva2021did].

#### Inductive Reasoning.

We use CLUTRR [sinha2019clutrr], a diagnostic benchmark for inductive reasoning, requiring inferring kinship relations between characters in short stories.

## Details

#### Language Models.

We use three OpenAI language models: *davinci*, *text-davinci-002* and *code-davinci-002*. We use the default parameters except a temperature of ```latex $0.5$ ``` in sampling.

#### Exemplars.

For arithmetic/commonsense/inductive reasoning, each prompt contains ```latex $5/7/7$ ``` exemplars. For DiVeRSe, each question has ```latex $5$ ``` different prompts, and ```latex $20$ ``` reasoning paths are sampled from the language model for each prompt. For arithmetic reasoning, the exemplars are randomly sampled from the training dataset of GSM8K; for CLUTRR, the exemplars are sampled from its training dataset, with reasoning paths synthesized by handcraft rules; for StrategyQA and CommonsenseQA, their original datasets do not contain enough exemplars with well-annotated reasoning paths, so we construct ```latex $1,000$ ``` pseudo exemplars by "self-teaching" from "seed" exemplars provided by wei2022chain.

#### Training Datasets.

For each task, we sample ```latex $1,000$ ``` question-answer pairs from the training dataset to train the verifier.

#### Verifier.

We fine-tune *deberta-v3-large* [he2021deberta] with learning rate ```latex $1\times 10^{-5}$ ``` and batch size ```latex $128$ ```. For the step-aware verifier, we select the best ```latex $\alpha$ ``` among ```latex $0.0/0.1/0.2/0.3$ ```.

# Main Results

We mainly compare DiVeRSe with two baselines: (1) greedily decoding a single reasoning path [wei2022chain], referred to as *Greedy Decode*; (2) sampling ```latex $100$ ``` reasoning paths, then select the final answer via majority voting [selfconsistency], referred to as *Self-Consistency*.

## Effectiveness

Experimental results clearly demonstrate that DiVeRSe can bring significant and consistent improvements over recent strong baselines. The improvements are across different models (*davinci*, *text-davinci-002* and *code-davinci-002*) as well as different reasoning skills (eight tasks in three reasoning skills). Taking GSM8K as an example, compared to *Greedy Decoding* and *Self-Consistency*, DiVeRSe brings improvements of ```latex $22.2\%/12.0\%$ ``` on *davinci*, ```latex $33.1\%/12.0\%$ ``` on *text-davinci-002*, and ```latex $27.0\%/5.6\%$ ``` on *code-davinci-002*. Compared to *Self-Consistency*, DiVeRSe achieves average improvements of ```latex $5.6\%/5.1\%/54.3\%$ ``` on the three reasoning skills, respectively.

## Comparing to Previous SOTAs

We also compare DiVeRSe with: (1) previous SOTA results based on fine-tuning; (2) recent SOTA results [wei2022chain] based on PaLM [chowdhery2022palm], a gigantic language model with 540 billion parameters. DiVeRSe can also be applied to PaLM, but PaLM is not publicly available.

On all the five arithmetic reasoning tasks, DiVeRSe (with *code-davinci-002*) achieves new SOTA results, with an average improvement of ```latex $6.2\%$ ```. On the two commonsense reasoning tasks, the performance of DiVeRSe is slightly lower (```latex $-1.9\%$ ```) than that of PaLM-based self-consistency. We speculate that the reason might be: these two commonsense reasoning tasks are multiple-choice tasks rather than open-ended generation tasks, resulting in more false-positive exemplars in the pseudo exemplar base. Regarding inductive reasoning, DiVeRSe achieves a surprisingly good performance of ```latex $95.9\%$ ``` on the CLUTRR task, outperforming (```latex $+28.9\%$ ```) previous SOTA result with fine-tuning [sinha2019clutrr]. sinha2019clutrr also introduced a method with ```latex $100\%$ ``` accuracy. We do not take it into the comparison, as this method requires a domain-specific system with complicated rules to extract a knowledge graph for each input text.

# Case Study

An example of step-level scores given by the step-aware verifier shows that steps in the correct reasoning path have relatively high scores, while the scores in the wrong reasoning path show where the path starts to be wrong. This indicates that besides improving the performance, the step-aware verifier can also bring interpretability to show the step-level correctness.

# Analysis

We also conduct ablation experiments and analysis to investigate the keys to the success of DiVeRSe.

## The Effectiveness of Diverse Prompts

By diversifying both prompts and reasoning paths (```latex $\langle M_1=5, M_2=20\rangle$ ```), we consistently improve performance over the sampling decoding approach (```latex $\langle M_1=1, M_2=100\rangle$ ```) of selfconsistency. Both methods use majority voting. Further analysis reveals that neither only using diverse prompts nor only using sampling is optimal. In other words, *the best performance is achieved by combining diverse prompts and sampling*. Moreover, *diverse prompts lead to more diverse reasoning paths*. We hypothesize that this diversity contributes to the performance improvement by: (1) making correct results more distinguishable from varied errors during inference; and (2) providing more diverse negative samples for enhancing the verifier's generalizability during training.

[IMAGE: Diverse prompts increase the diversity of GSM8K reasoning paths and their final answers. This is beneficial for the voting verifier. Left: the average number of distinct reasoning paths per question. Right: the average number of distinct final answers per question.]

## The Effectiveness of Voting Verifier

We compare three algorithms to conclude the agreement from diverse reasoning paths: majority voting, verifier, and voting verifier. *Compared to majority voting, our voting verifier can significantly and consistently boost reasoning performance across different tasks and different language models*. Verifier without voting often outperforms majority voting, but extending it to voting verifier can further boost the performance.

[IMAGE: Human evaluation on GSM8K shows the effectiveness of the step-aware mechanism for verifier.]

## The Effectiveness of Step-aware Verifier

We evaluate the impact of incorporating step-level information into the voting verifier of DiVeRSe. We find that *using the step-aware verifier improves the performance in most of the experiments*. The only exception is *code-davinci-002* on GSM8K, where the step-aware verifier slightly lowers the performance. We hypothesize that *code-davinci-002* is more capable of generating high-quality reasoning paths, and thus does not benefit much from the step-level information.

#### Detailed Human Evaluation of Reasoning Steps.

We further analyze the quality of generated reasoning steps, by asking human annotators to judge whether the GSM8K reasoning steps produced by DiVeRSe (with/without step-aware mechanism) are good or not. Here "good" means not only correct formulas and calculation results but also textual fluency and logical coherence.

We further examine the quality of the reasoning steps generated by DiVeRSe (with/without step-aware mechanism) for GSM8K, by asking human annotators to rate them based on correctness, fluency, and coherence. For each test question, we compare three reasoning paths produced by *code-davinci-002*: the one with the highest verifier score, the one with the highest step-aware verifier score, and a randomly chosen one. The annotators (master students) label any incorrect or unsatisfactory reasoning steps in each path (single-blind) and explain why. We collect annotations for 200 test questions, half of which have correct final answers from all three paths, and half of which have incorrect final answers from all three paths.

We find that **all the reasoning paths with correct final answers are also correct in every intermediate step**, which shows that *code-davinci-002* can reliably generate accurate reasoning steps, not just lucky guesses. However, we also find that **many of the correct reasoning paths have unnecessary steps**. Analysis shows that ```latex $40\%$ ``` of the random paths have redundant steps, and the verifier can lower this percentage to ```latex $31\%$ ```. We also find that **the step-aware verifier can further eliminate redundant reasoning steps** from ```latex $31\%$ ``` to ```latex $20\%$ ```.

[IMAGE: figures/step_error_type_analysis.pdf - The distribution of error types in incorrect reasoning steps.]

Furthermore, for the incorrect reasoning paths, we find that **the step-aware mechanism helps produce more correct steps before making mistakes**. For each failed test question, we compare the number of correct steps in the path with the highest verifier score and the path with the highest step-aware verifier score (by human evaluation). For ```latex $33\%$ ```/```latex $17\%$ ``` of the failed test cases, the step-aware verifier generates more/fewer correct steps than the verifier without the step-aware mechanism.

#### Step Error Types.

Analysis shows the distribution of error types in the incorrect reasoning steps. We see that ```latex $95\%$ ``` of the errors are caused by incorrect formulations (i.e., using wrong intermediate results or operators and generating invalid formulas, which lead to incorrect answers). We also see that, although *code-davinci-002* often makes division calculation errors (e.g., ```latex $10/3=3$ ```), both the verifier and the step-aware verifier can effectively assign low scores to such paths, thus improving the performance.

## How Many Diverse Outputs Do We Need?

Analysis shows the accuracy at different ```latex $M$ ``` values, where ```latex $M$ ``` is the number of reasoning paths sampled from the ```latex $100$ ``` generated paths for each question. We observe that: (1) the accuracy increases with more reasoning paths, but the improvement becomes marginal at ```latex $M\geq50$ ```; (2) DiVeRSe outperforms self-consistency significantly and consistently at different ```latex $M$ ``` values.

## How Many Training Data Do We Need?

DiVeRSe requires a dataset with reasoning paths for training the verifier. Analysis shows how the size of this dataset affects the performance. We observe that: the performance is only reduced by about ```latex $2\%$ ```, even if the size of training data is cut by ```latex $75\%$ ``` (from ```latex $1,000$ ``` to ```latex $250$ ```). With the same reasoning paths, voting verifier performs better than majority voting, while verifier without voting causes significant performance drops.

[IMAGE: figures/num_of_diverse_outputs_jun13.pdf - GSM8K accuracy at different M values (how many reasoning paths are used for each question).]

## The Impact of the Number of Exemplars

We conduct experiments for ```latex $k=3/5/8$ ``` (```latex $k$ ``` is the number of exemplars used in each prompt) on GSM8K. We observe that: *using 8 exemplars in each prompt can further boost the accuracy of GSM8K to ```latex $83.2\%$ ```.*

[IMAGE: figures/repo_size_lyf.pdf - DiVeRSe performance (code-davinci-002) on GSM8K with different sizes of the training dataset (without labeled reasoning paths).]

# Related Work

#### Reasoning Skills.

Researchers in the literature have proposed many benchmarks requiring various reasoning skills, including commonsense reasoning [zellers-etal-2018-swag; talmor2019commonsenseqa; geva2021did], numerical reasoning [dua-etal-2019-drop], multi-hop reasoning [yang-etal-2018-hotpotqa], arithmetic reasoning [koncel2015parsing; roy2015solving; miao2020diverse; patel2021nlp; cobbe2021training], logical reasoning, inductive reasoning [sinha2019clutrr] and tabular reasoning [chen-etal-2020-hybridqa].

#### Reasoning with Symbolic Systems.

Much research in the literature enhances the reasoning capabilities of machine learning systems by exploiting symbolic systems, including knowledge graphs [mihaylov-frank-2018-knowledgeable; bauer-etal-2018-commonsense; kundu-etal-2019-exploiting; lin-etal-2019-kagnet; ding-etal-2019-cognitive; wang2022multi-level], or question taxonomies [dua-etal-2019-drop; andor-etal-2019-giving; hu-etal-2019-multi; wang-etal-2022-logic]. Although these methods work well on specific benchmarks, they usually require domain-specific designs and human efforts, thus limiting the generalizability.

#### Reasoning via Language Models.

This line of work aims to address reasoning tasks in a general sequence-to-sequence manner, empowered by reasoning-aware pre-training or fine-tuning of language models. For example, deng-etal-2021-reasonbert proposed to train the language model with crawled data from the internet; asai-hajishirzi-2020-logic proposed a logic-guided data augmentation method to pre-train the language model; shen2021generate [cobbe2021training] proposed to train a verifier to rank solutions sampled from fine-tuned language models; geva-etal-2020-injecting [yoran-etal-2022-turning; campagna-etal-2020-zero; wang-etal-2022-logic] proposed to equip language models with reasoning abilities by generating training examples with human-designed templates; pi2022reasoning proposed to inject reasoning capabilities into language models by continual pre-training on program execution data.

[IMAGE: figures/num_of_exemplars.pdf - DiVeRSe performance (code-davinci-002) on GSM8K when each prompt contains 3/5/8 exemplars.]

#### Reasoning via Prompting Gigantic Language Models.

Gigantic language models like GPT-3 [brown2020language] have demonstrated impressive few-shot learning capabilities in many tasks and have attracted many research interests on making gigantic language models better few-shot learners [liu-etal-2022-makes]. However, these methods struggle to address tasks requiring reasoning skills. To mitigate this, recently there is a line of research that focuses on unleashing the reasoning capabilities of gigantic language models via better prompting strategies. wei2022chain proposed *chain-of-thought reasoning*, of which the key insight is the insertion of multi-step reasoning paths before generating the final answers; selfconsistency proposed to improve chain-of-thought reasoning via *self-consistency*, of which the key insight is to conclude the most consistent answer from different reasoning paths sampled from the language model; least2most proposed to leverage gigantic language models to decompose questions into sub-questions, thereby addressing them in an iterative manner; fewshotreason2022 proposed that gigantic language models can even be good zero-shot reasoners, by designing prompts that can induce language models to do reasoning step-by-step; lampinen2022can proposed building a prompt by selecting examples and explanations together, thus substantially improving performance over selecting examples alone. Despite their great successes, these works come with their limitations. This paper is a continuation of this line of research, focusing on diverse verifier on reasoning steps.

# Conclusion and Future Work

In this paper, we present DiVeRSe, a novel and general method to enhance the reasoning abilities of large language models. Our method builds on the idea of prompting language models with multi-step reasoning paths, but introduces three key innovations: diverse prompts, voting verifier, and stepwise verifier. The latter is especially novel and effective, as it verifies each reasoning step separately and we provides a detailed analysis of the model's behavior in each step. We demonstrate the superiority of DiVeRSe through extensive experiments. For instance, using *code-davinci-002*, our method achieves state-of-the-art performance on most reasoning tasks, surpassing the 540B PaLM model with previous prompting techniques.

There are many directions for our future work. (1) We will continue to investigate how to reduce or recognize false positive pseudo exemplars. (2) We plan to investigate mechanisms to produce better diverse prompts than simple sampling. (3) We will extend DiVeRSe to other tasks and continue to design better prompting techniques to elicit the power of gigantic language models.

# Limitations

#### Computing Resources.

Despite the surprising performance it achieves, our framework needs to be applied to large language models like GPT-3 or PaLM. Inference with these models costs more time and budgets than fine-tuning models like RoBERTa [liu2019roberta].

#### Faithfulness.

Although DiVeRSe can significantly improve the accuracy of final answers, we still cannot guarantee that the reasoning paths produced by the language models are 100 percent faithful. This is the key challenge and future direction for this line of research (chain-of-thought reasoning).

#### More Training Data.

DiVeRSe needs more labeled data with well-annotated reasoning paths to construct diverse prompts, and it also needs a training dataset for supervising the verifier. However, from another point of view, this limitation can also be regarded as a contribution that studies how chain-of-thought reasoning can be further improved if we have more training data than just a few exemplars.

#### Human Evaluation of Reasoning Steps.

We use human evaluation to measure the quality of the intermediate steps in reasoning paths since few current works provide reliable frameworks to evaluate the quality of reasoning steps.

# Appendix

## Preliminaries

#### Prompting.

Prompting means prepending a few exemplars to the task input ```latex $\mathbf{x}$ ``` and generating the output ```latex $\mathbf{y}$ ``` from the pretrained language model:

```latex
$$\begin{equation}
    p(\mathbf{y}|C,\mathbf{x}) = \prod_{t=1}^{|\mathbf{y}|} p_{\text{LM}}(y_t | C, \mathbf{x}, y_{<t}),
\end{equation}$$
```

where ```latex $C$ ``` is the concatenation of ```latex $K$ ``` exemplars:

```latex
$$\begin{equation}
C = (\overline{\mathbf{x}}_1,\overline{\mathbf{y}}_1);(\overline{\mathbf{x}}_2,\overline{\mathbf{y}}_2);...;(\overline{\mathbf{x}}_K,\overline{\mathbf{y}}_K).
\end{equation}$$
```

We denote **prompt** as the concatenation of the exemplars ```latex $C$ ``` and the input ```latex $\mathbf{x}$ ```.

#### Reasoning Paths.

For reasoning tasks that aim to generate an answer ```latex $\mathbf{y}$ ``` for a question ```latex $\mathbf{x}$ ```, wei2022chain proposed the insertion of a reasoning path ```latex $\mathbf{z}$ ``` before generating the answer ```latex $\mathbf{y}$ ```:

```latex
$$\begin{equation}
C'=(\overline{\mathbf{x}}_1,\overline{\mathbf{z}}_1,\overline{\mathbf{y}}_1);...;(\overline{\mathbf{x}}_K,\overline{\mathbf{z}}_K,\overline{\mathbf{y}}_K),
\end{equation}$$
```

where ```latex $\mathbf{z}_i$ ``` is a text **reasoning path** of how the answer ```latex $\mathbf{y}_i$ ``` is reasoned step-by-step for question ```latex $\mathbf{x}_i$ ```.

Then, during inference, a reasoning path ```latex $\mathbf{z}$ ``` will be generated before the answer ```latex $\mathbf{y}$ ```:

```latex
$$\begin{equation}
    p(\mathbf{y}|C',\mathbf{x}) = p(\mathbf{z}|C',\mathbf{x})\cdot p(\mathbf{y}|C',\mathbf{x}, \mathbf{z}).
\end{equation}$$
```

**Prompting example for GSM8K arithmetic reasoning:**

**Q**: If there are 3 cars in the parking lot and 2 more cars arrive, how many cars are in the parking lot?

**A**: There are 3 cars in the parking lot already. 2 more arrive. Now there are 3 + 2 = 5 cars. The answer is 5.

...

**Q**: Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder for $2 per egg. How much does she make every day?

**A**: [Sample 1] She has 16 - 3 - 4 = 9 eggs left. So she makes ```latex $2 * 9=$ ```18 per day. The answer is 18. [Sample 2] This means she uses 3 + 4 = 7 eggs every day. So in total she sells 7 * ```latex $2=$ ```14 per day. The answer is 14. [Sample 3] She eats 3 for breakfast, so she has 16 - 3 = 13 left. Then she bakes muffins, so 13 - 4 = 9 eggs left. She makes 9 * $2 = $18. The answer is 18.

This demonstrates prompting large language models to generate different reasoning paths, then selecting the final answer via majority voting [selfconsistency].

## Data Statistics

| Dataset | N | Example Question |
|---------|---|------------------|
| GSM8K | 1319 | James decides to run 3 sprints 3 times a week. He runs 60 meters each sprint. How many total meters does he run a week? |
| AsDiv | 2096 | Seven red apples and two green apples are in the basket. How many apples are in the basket? |
| MultiArith | 600 | The school cafeteria ordered 42 red apples and 7 green apples for students lunches. But, if only 9 students wanted fruit, how many extra did the cafeteria end up with? |
| SVAMP | 1000 | Paco had 26 salty cookies and 17 sweet cookies. He ate 14 sweet cookies and 9 salty cookies. How many salty cookies did Paco have left? |
| SingleEq | 508 | Terez has 44 cows on his farm. 50 percent of the cows are female, and 50 percent of the females are pregnant. How many pregnant female cows does Terez have? |
| CommonsenseQA | 3387 | Sammy wanted to go to where the people were. Where might he go? Options: (a) race track (b) populated areas (c) desert (d) apartment (e) roadblock |
| StrategyQA | 2280 | Could you go to New York Public Library and the Six Flags Great Escape in the same day? |
| CLUTRR | 447 | Kelly and her mother Ernest made breakfast together. Constance and her husband Ernest wanted a child badly What kind of relative is Kelly to Constance? The possible relationships are: sister, son, aunt, granddaughter, father, grandfather, grandmother, mother-in-law, uncle, niece, mother, brother, daughter, nephew, grandson, son-in-law, father-in-law, daughter-in-law. |

## Boosting Reasoning Paths via Self-Teaching

### Self Teaching

A critical issue of DiVeRSe is **how to provide diverse prompts**. selfconsistency tried an ensemble-based approach, i.e., to permutate exemplars in the original prompt. However, this strategy does not increase diversity in terms of exemplars. Supposing that there is an exemplar base ```latex $E$ ```, we can sample ```latex $K$ ``` exemplars from it to construct a prompt, and repeat this ```latex $M_1$ ``` times independently to construct ```latex $M_1$ ``` prompts with diverse exemplars.

For scenarios that do not have sufficient exemplars (i.e., ```latex $|E| < K * M_1$ ```), we propose to **bootstrap the diversity of prompts by "self-teaching"**, i.e., generating pseudo reasoning paths from a few exemplars and some question-answer pairs without reasoning paths. This is motivated by zelikman2022star. Suppose that ```latex $D$ ``` is a dataset without reasoning paths, consisting of ```latex $(\mathbf{x}, \mathbf{y}^*)$ ``` pairs. Given the small exemplar base ```latex $E$ ```, for each ```latex $(\mathbf{x,y^*})\in D$ ```, we can use prompting to generate a reasoning path ```latex $\mathbf{z}$ ``` and the predicted answer ```latex $\mathbf{y}$ ```. We define the pseudo exemplar base ```latex $E'$ ``` as:

```latex
$$\begin{equation}
E' = \{(\mathbf{x}, \mathbf{z}, \mathbf{y})|(\mathbf{x},\mathbf{y}^*)\in D, \mathbf{y}=\mathbf{y}^*\},
\end{equation}$$
```

then ```latex $E\cup E'$ ``` can be regarded as the new exemplar base for generating diverse prompts.

### Noises in Multiple Choice Tasks

In our experimental setup, StrategyQA and CommonsenseQA are more challenging than other tasks, as they use pseudo exemplars generated through "self-teaching".

"Self-teaching" may lead to bad exemplars, whose reasoning paths are invalid but happen to yield answers coinciding with the ground truth. Questions in StrategyQA/CommonsenseQA are two-choice/four-choice questions, respectively. Therefore, such noise would be more serious in StrategyQA than in CommonsenseQA. This somehow explains why DiVeRSe can achieve comparable performance (```latex $-0.8\%$ ```) as the PaLM-based SOTA on CommonsenseQA, while it sees a ```latex $3.0\%$ ``` performance decline to PaLM on StrategyQA, which has only two choices. In other words, it is easier for StrategyQA to yield a right answer but a misleading reasoning path.

## Data Statistics Details

For GSM8K, AsDiv, MultiArith, SVAMP, SingleEq, and CommonsenseQA, we use the same test sets as wei2022chain.

For StrategyQA, there are ```latex $2,290$ ``` test cases (i.e., questions paired with TRUE/FALSE labels), but there is no other case that can be leveraged by DiVeRSe to construct diverse exemplars. To address this problem, we randomly divide these ```latex $2,290$ ``` test cases into two equal parts (denoted as ```latex $T_1$ ``` and ```latex $T_2$ ```). For each DiVeRSe experiment of SQA, we conduct two runs: using ```latex $T_1$ ``` to construct diverse exemplars and ```latex $T_2$ ``` as the test set, and vice versa. The final reported solve rate is the average solve rate of these two runs.

For CLUTRR, sinha2019clutrr provided several versions: *clean*, *supporting*, *irrelevant*, and *disconnected*. The *clean* version is the basic dataset, while the others are the perturbed variations of it. Our experiments are conducted on the *clean* version.

## Our Changes to CLUTRR

In our experiments, two changes are applied to the CLUTRR benchmark: (1) appending candidate answers to each question; (2) constructing reasoning paths based on rules.

#### Candidate Answers.

Besides the original questions (e.g., "*Mary, a female, took her husband who is a male, Roy, out for lunch. Ernest bought to dress for his father Roy. What kind of relative is Ernest to Mary?*"), we also provide all the candidate answers (i.e., "*The possible relationships are: sister, son, aunt, granddaughter, father, grandfather, grandmother, mother-in-law, uncle, niece, mother, brother, daughter, nephew, grandson, son-in-law, father-in-law, daughter-in-law*") in the input sequence. Our preliminary experiments show that, the gigantic language models cannot reach more than ```latex $50\%$ ``` accuracy without the sequence of candidate answers.

#### Reasoning Paths.

For each question, sinha2019clutrr also provided a knowledge graph that formulates the relations directly mentioned in the question. Each knowledge graph consists of several ```latex $\langle e_1, r, e_2\rangle$ ``` triplets, which means there is a relation ```latex $r$ ``` from ```latex $e_1$ ``` to ```latex $e_2$ ```. Take the aforementioned question as an example, the knowledge graph consists of two triplets: ```latex $\langle \text{Mary}, \text{husband}, \text{Roy}\rangle$ ``` and ```latex $\langle \text{Ernest}, \text{father}, \text{Roy}\rangle$ ```.

For each question, we construct the reasoning path based on its knowledge graph. We first topologically sort all triplets in the knowledge graph. For each triplet, we convert it to a reasoning step using the template "*{$e_2$} is the {$r$} of {$e_1$}*". After that, we can get the reasoning path by concatenating these reasoning steps. Take the aforementioned question as an example, the reasoning path is: "*Roy is the husband of Mary. Roy is the father of Ernest. Thus, Ernest is the son of Mary.*"
