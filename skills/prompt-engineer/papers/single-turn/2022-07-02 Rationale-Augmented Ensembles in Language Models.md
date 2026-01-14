# Abstract

Recent research has shown that _rationales_, or step-by-step chains of thought, can be used to improve performance in multi-step reasoning tasks. We reconsider rationale-augmented prompting for few-shot in-context learning, where (input `latex $\rightarrow$ ` output) prompts are expanded to (input, _rationale_ `latex $\rightarrow$ ` output) prompts. For rationale-augmented prompting we demonstrate how existing approaches, which rely on manual prompt engineering, are subject to sub-optimal rationales that may harm performance. To mitigate this brittleness, we propose a unified framework of _rationale-augmented ensembles_, where we identify _rationale sampling_ in the _output_ space as the key component to robustly improve performance. This framework is general and can easily be extended to common natural language processing tasks, even those that do not traditionally leverage intermediate steps, such as question answering, word sense disambiguation, and sentiment analysis. We demonstrate that rationale-augmented ensembles achieve more accurate and interpretable results than existing prompting approaches---including standard prompting without rationales and rationale-based chain-of-thought prompting---while simultaneously improving interpretability of model predictions through the associated rationales.

# Introduction

Recent progress on improving few-shot in-context learning in pretrained large language models has been achieved by expanding prompt exemplars with rationales, delivering successes in a variety of natural language reasoning tasks [wei2022chain; palm; explanation_deepmind; selection_inference; step_by_step; maieutic_prompting]. These prompting-based approaches typically adopt manually-written rationales and therefore rely on the quality of prompt engineering, which usually does not ensure optimal rationales are provided for a given task. Previous work has also shown that "rationales" can be useful for _supervised learning_ in natural language tasks when added in the training data [zaidan-etal-2007-using; ling-etal-2017-program; cobbe2021training; star], but it remains unclear whether such rationales can be reliably useful in few-shot in-context learning [ye2022unreliability].

In this paper, we investigate the role of _rationales_ in few-shot in-context learning by conducting a systematic study over a wide range of NLP tasks. In particular, we seek to answer the following questions: (1) Why do rationales sometimes hurt task performance in few-shot learning? and (2) How can one reliably leverage rationales in few-shot learning for general natural language tasks?

Below we show that, when shifting from the simpler paradigm of (input `latex $\rightarrow$ ` output) prompts to expanded (input, _rationale_ `latex $\rightarrow$ ` output) prompts, there is indeed a large variance in final task performance for few-shot in-context learning. We identify the primary source of sensitivity as the _sub-optimality_ of the rationales used for prompting. To overcome such sub-optimality, we develop a unified framework of **rationale-augmented ensembles**, where the idea is to aggregate over multiple rationales generated from the language model to reduce the brittleness of the results. Ensemble aggregation can be achieved in a few different ways depending on how randomness over the rationales is introduced in the input or the output space, including (1) self-consistency, where existing work [self_consistency] has shown that task performance can be improved by sampling multiple language model outputs for ensembling, (2) prompt-order ensembling, where previous work [Lu2021FantasticallyOP; pmlr-v139-zhao21c] has shown that task performance is sensitive to the order of the exemplars in the prompts, and (3) input-rationale ensembling, where human-written rationales can be replaced by model-generated rationales, leveraging the ability of language models to generate high-quality explanations [wiegreffe2021reframing]. Figure 1 provides an overview of rationale-augmented ensembling approaches.

[IMAGE: An overview of different ways of composing rationale-augmented ensembles, depending on how the randomness of rationales is introduced. Here q, a, r correspond to question, answer, and rationale, respectively. Rationales are human-written unless specified as model-generated.]

A key finding of this study is that _rationale sampling_ in the _output_ space is a central aspect of rationale-augmented ensembles contributing to their success. That is, regardless of how the input or the prompt vary, task performance is best improved when sufficient diversity is introduced by sampling rationales from the language model's decoder. We also find that rationale-augmented ensembles reliably outperform existing rationale-based few-shot and zero-shot prompting methods [wei2022chain; step_by_step] across a variety of natural language processing tasks. Moreover, in cases where human-written rationales hurt task performance due to the sub-optimality of the rationales, rationale-augmented ensembling is able to fill the gap and reliably outperform standard few-shot prompting [brown2020language] on most tasks.

Perhaps surprisingly, we also find that the proposed framework can be used to improve few-shot learning in common natural language processing tasks, even including tasks where explicit intermediate steps might not be necessary, such as question answering [BoolQ; clark2019boolq], word sense disambiguation [WiC; pilehvar-camacho-collados-2019-wic], sentiment analysis [SST-2; socher-etal-2013-recursive], and paraphrase identification [QQP; WinNT]. We conjecture that, in principle, any natural language processing task can be usefully augmented with "rationales" that represent the thought processes needed to achieve accurate and interpretable results in few-shot in-context learning.

Existing work on interpretability usually focuses on improving the explanation of model predictions via supervised learning, which requires large amounts of human labeled explanations to be collected [zaidan-etal-2007-using; esnli; rajani-etal-2019-explain; wt5], while remaining agnostic to improving final task performance. In contrast, we show that the framework proposed in this paper can leverage very few human-written rationales (as `latex $K$ `-shot exemplars where `latex $K$ ` is usually very small, e.g., 3 to 6) and still generate ensembles that can improve task performance significantly. The proposed framework does not require additional fine-tuning [thoppilan2022lamda; star], verifiers [cobbe2021training], calibrators [ye2022unreliability], or any use of an auxiliary dataset [star; better_reasoner], making it applicable to any off-the-shelf large language model. As a general approach to obtaining more accurate and more interpretable natural language understanding, rationale-augmented ensembles also provide more accurate assessments of the performance gains contributed by rationales in few-shot in-context learning.

# Rationale-Augmented Ensembles in Language Models

We investigate the role of rationales in few-shot in-context learning, first interrogating the sensitivity of final performance to rationale quality, then developing a unified perspective on rationale-augmented ensembles that seek to reduce sensitivity and improve final performance.

## Optimality of the rationales in few-shot learning

Given that rationale-augmented prompting has been shown to exhibit variable performance [wei2022chain; ye2022unreliability], we first investigate the sensitivity of task performance to rationale quality across a range of natural language tasks, including e-SNLI [esnli], BoolQ [clark2019boolq], WiC [pilehvar-camacho-collados-2019-wic], and SST-2 [socher-etal-2013-recursive], finding that human-generated rationales can indeed be sub-optimal.

For each task, we choose `latex $K$ ` (4 to 6) exemplars from the training set, manually produce a set of rationales for each exemplar, then use these as seeds to generate additional rationales from the language model: we leave one question from the exemplars out, and use the rest of the exemplars with human-written rationales as prompts, then we can sample from the language model's decoder to obtain a large number of generated rationales for this question. Each new prompt is then composed as follows: for each of the `latex $K$ ` exemplars, we replace its human-written rationale with a random sample from the generated rationales, while keeping the rationales of the other `latex $K-1$ ` exemplars fixed. We repeat this for every exemplar and report the final task performance using the new prompts in Figure 2 (denoted as sampled-r-`latex $k$ ` if the `latex $k$ `-th rationale is replaced).

[IMAGE: Performance varies depending on which rationales are used in the prompts for few-shot in-context learning across e-SNLI, BoolQ, WiC, and SST-2. The exemplars in the prompts are exactly the same, only the rationales differ. The performance is evaluated with accuracy on the greedy decoded output using PaLM-540B.]

First, one can observe that compared with standard few-shot prompting ("no-rationale"), the addition of human-written rationales does not always yield better performances. Moreover, the performance induced by sampled-rationales exhibits substantial variance, implying that the quality of the rationales in the prompts has a significant effect on final performance. Often the sampled rationales exhibit better performance than the human-written ones, indicating that manually provided rationales can be far from "optimal" in terms of task performance. Table 1 shows examples of human-written rationales and two model-generated rationales for the same question, demonstrating that the model is able to generate diverse but reasonable rationales using its pre-trained knowledge.

**Example rationales:**

**[e-SNLI]** _Premise: "Children smiling and waving at camera." Based on this premise, can we conclude the hypothesis "The kids are frowning." is true?_

- **Human-written rationale (crowd-sourced)**: One cannot be smiling and frowning at the same time.
- **Model-generated rationale**: Smiling and waving is not frowning. || 'Smiling' and 'frowning' are opposites.

**[BoolQ]** _can you use oyster card at epsom station?_

- **Human-written rationale**: Epsom railway station serves the town of Epsom in Surrey and is not in the London Oyster card zone.
- **Model-generated rationale**: Epsom Station is not currently a part of the Oyster Card Network. || 'Oyster card' is a pre-pay card for public transport in London. Epsom Station is in Surrey.

**[WiC]** _Approach a task. To approach the city. Q: Is the word "approach" used in the same way in the two sentences above?_

- **Human-written rationale**: The first "approach" means "deal with", the second "approach" means "come near".
- **Model-generated rationale**: 1) To tackle or deal with a task. 2) To come near. || 'To approach the city' means "to get close to the city". 'Approach a task' means "to deal with a task".

**[QQP]** _Is the following question "What can one do after MBBS?" the same as "What do i do after my MBBS?"_

- **Human-written rationale**: Both are asking what can a person do after MBBS.
- **Model-generated rationale**: 'One' means the same as 'I'. || 'What can one do' and 'what do I do' mean the same thing in the context of the question.

**[SST-2]** _What is the sentiment of the following sentence? "contains no wit , only labored gags"_

- **Human-written rationale**: "contains no wit" is clearly a negative sentiment.
- **Model-generated rationale**: "no wit" and "labored gags" both mean negative sentiments. || 'no wit' indicates something negative and "only labored gags" is also negative.

#### Simply including a rationale does not always improve task performance.

From Figure 2 one can also see that, due to the sub-optimality of the rationales used, task performance can degrade when rationales are added to prompts in few-shot in-context learning. For example, on e-SNLI, WiC and SST-2, the performance achieved by written-rationales is significantly worse than standard few-shot prompting without rationales, consistent with the findings in [ye2022unreliability].

## Rationale-augmented ensembles

Given that determining "optimal" rationales for few-shot in-context learning is difficult, it is natural to consider the use of **rationale-augmented ensembles** that can automatically aggregate across diverse rationales to overcome the brittleness of performance to sub-optimal human-written rationales.

**Table 1: Methods for generating rationale-augmented ensembles in language models.**

| Rationale-augmented ensembles                                    | Input/Prompt | Output         |
| ---------------------------------------------------------------- | ------------ | -------------- |
| Self-consistency [self_consistency]                              | fixed        | sampled        |
| Prompt-order ensemble [Lu2021FantasticallyOP; pmlr-v139-zhao21c] | shuffled     | greedy/sampled |
| Input-rationale ensemble, adapted from [wiegreffe2021reframing]  | sampled      | greedy/sampled |

We define a rationale-augmented ensemble as introducing an additional latent variable (the "rationales") that can be sampled and ultimately marginalized out (see Figure 1 for examples). Depending on the stage where the sampling occurs, the approaches to rationale ensembling can be categorized as follows:

- Self-consistency [self_consistency], where the input/prompt is fixed, and multiple rationales are sampled from the language model's decoder.

- Prompt-order ensemble: Given that task performance has been observed to be sensitive to prompt ordering [Lu2021FantasticallyOP; pmlr-v139-zhao21c], the order of exemplars in prompts can be permuted to elicit multiple rationales in the decoder.

- Input-rationale ensemble: Leveraging the ability of large language models to generate high-quality explanations [wiegreffe2021reframing], model-generated rationales can replace human-written rationales in the input prompts (e.g., via the process described in Section 2.1), which can then be used to elicit multiple rationales in the decoder.

For each of these ensembling approaches, the model couples the generation of rationales and answers before taking a majority vote (more precisely, a plurality vote) to produce the final ensemble answer. For both prompt-order ensembling and input-rationale ensembling, since the randomness is introduced in the _input_ space, one can either decode an output greedily with a rationale, or sample an output with a rationale in the _output_ space for each new prompt. Interestingly, below we find that _rationale sampling_ in the _output_ space is the most important component in the overall rationale-augmented ensemble framework. In particular, regardless of how the input/prompt varies, sampling in the output space is the key to achieving better task performance across a variety of natural language processing tasks. With this key component, we find that rationale-ensembling can significantly improve results over both standard prompting [brown2020language] and rationale-based prompting [wei2022chain; step_by_step] on common NLP tasks; the framework also provides rationales at no additional cost that can be used to better interpret model predictions.

# Experiments

We conducted a series of experiments to compare the performance of rationale-augmented ensembles against existing approaches, across a variety of natural language processing tasks. Overall, the results demonstrate that rationale-augmented ensembles can robustly improve task performance across alternative language models and model scales.

## Experiment setup

#### Tasks and datasets.

We considered a set of natural language tasks from GLUE [wang-etal-2018-glue], SuperGLUE [superglue], and other natural language processing benchmarks. These tasks can be categorized as follows:

- **Question Answering**: For question answering, we include BoolQ [clark2019boolq], HotpotQA [yang-etal-2018-hotpotqa], and OpenBookQA [openbookqa].

- **Natural Language Inference**: For these tasks, we include ANLI [nie-etal-2020-adversarial] with the three subsets (R1, R2, R3), e-SNLI [esnli], MNLI (matched/mis-matched) [mnli], and RTE [dagan2005pascal; bar2006second; giampiccolo2007third; bentivogli2009fifth].

- **Word Sense Disambiguation**: Here we use Word-in-Context [WiC; pilehvar-camacho-collados-2019-wic].

- **Sentiment Analysis**: we use the Stanford Sentiment Treebank v2 [SST-2; socher-etal-2013-recursive].

- **Paraphrase Identification**: Here we use Quora Question Pairs [QQP; WinNT].

- **Reasoning**. For reasoning tasks, we consider the AI2 Reasoning Challenge (ARC) [Clark2018ThinkYH] for open-domain question answering with commonsense reasoning, as well as the grade-school math problems [GSM8K; cobbe2021training] for arithmetic reasoning.

#### Language models and prompts.

To investigate whether rationale-augmented ensembles can robustly improve performance across language models, we evaluated the framework with two dense left-to-right, decoder-only transformer language models with varying scale: (1) PaLM-540B, a language model with 540-billion parameters [palm] and (2) the public GPT-3 model with 175-billion parameters [brown2020language; instructGPT].

All experiments are conducted in the few-shot setting except the zero-shot CoT baseline [step_by_step], without any fine-tuning. For each task, we randomly choose `latex $K$ ` examples from the training set as `latex $K$ `-shot prompts, while maintaining a balanced label distribution and manually providing a set of rationales as the initial prompts; see Appendix 6.1 for the full set of initial prompts and rationales used in each experiment. We use the exact same exemplars in the few-shot prompts for all baselines and rationale-augmented ensembles. For standard few-shot prompting we omit the rationales.

#### Parameter settings.

Across all tasks, each rationale-augmented ensemble is generated by ensembling `latex $m=40$ ` outputs from the language model. For sampling in the language model, we use temperature sampling [ACKLEY1985147; ficler-goldberg-2017-controlling] with temperature `latex $T=0.7$ `. The maximum number of decoded steps is set to `latex $128$ ` in every case, except for GSM8K where we use `latex $256$ ` to accommodate longer rationales needed to express extended reasoning chains.

## Results

The results for the PaLM-540B model are shown in Table 2, Table 3 and Table 5, and give a comparison to two baseline approaches: (1) standard few-shot prompting without rationales [brown2020language], and (2) rationale-based prompting, including few-shot chain-of-thought (CoT) prompting [wei2022chain], and zero-shot CoT [step_by_step] where the model is prompted with "Let's think step by step" to generate initial rationales then prompted with "Therefore, the answer is" to obtain the final answer.

For each of the rationale-augmented ensembles, we specify the inputs as "fixed", "shuffled" (for prompt-order ensemble), or "sampled" (for input-rationale ensemble); and the outputs as "greedy" or "sampled" depending on whether we decode the outputs greedily or sample the outputs from the language model's decoder. Based on the results shown in the tables, a few key observations follow:

- For each rationale-augmented ensemble strategy, the "output-sampled" version yields better final performance than the "output-greedy" version for almost every task. This remains true regardless of whether randomness is introduced in the input space (i.e., whether the exemplars are shuffled in a prompt-order ensemble, or whether rationales in the exemplars are sampled in an input-rationale ensemble). Although self-consistency has an "output-sampled" only version, given that the input/prompt is fixed, it also achieves comparable performance to the "output-sampled" versions of the other ensembling approaches. These findings indicate that _rationale sampling_ in the _output_ space is the critical component for improving task performance, more so than the specific ensembling method used.

- The "output-sampled" version of each rationale-ensembling method almost always improves performance over standard prompting [brown2020language] without rationales, as well as rationale-based few-shot and zero-shot prompting [wei2022chain; step_by_step]. There are a few exceptions, including MNLI-m/mm, SST-2, and QQP, from GLUE [wang-etal-2018-glue], where standard-prompting still exhibits the best performance. We conjecture that the questions and answers in these tasks already appear frequently in the pre-training corpus, which allows simple memorization to perform well, whereas forcing the model to additionally provide rationales slightly degrades performance.

- Simply adding rationales as in [wei2022chain; step_by_step] can sometimes degrade task performance compared to standard prompting (also observed in [ye2022unreliability]), but rationale-augmented ensembling reliably boosts performance beyond both rationale-based and standard prompting in most tasks. This finding suggests that rationale-augmented ensembles provide a reliable approach to improving the final task performance of **rationale-based few-shot in-context learning**. Interpretability of model predictions is also enhanced by the presence of generated rationales in the model outputs.

**Table 2: Performance comparison over natural language inference tasks, on PaLM-540B.**

| Method                              | Input    | Output  | ANLI R1 / R2 / R3              | e-SNLI   | RTE      | MNLI-m/mm           |
| ----------------------------------- | -------- | ------- | ------------------------------ | -------- | -------- | ------------------- |
| Zero-shot CoT [step_by_step]        | fixed    | greedy  | 49.7 / 45.1 / 44.8             | 70.4     | 72.2     | 60.0 / 62.2         |
| Standard-prompting (no-rationale)   | fixed    | greedy  | 69.1 / 55.8 / 55.8             | 85.8     | 84.8     | **82.7** / **81.5** |
| CoT-prompting [wei2022chain]        | fixed    | greedy  | 68.8 / 58.9 / 60.6             | 81.0     | 79.1     | 72.0 / 74.0         |
| Prompt-order ensemble               | shuffled | greedy  | 72.0 / 60.7 / 61.3             | 84.2     | 78.0     | 74.5 / 75.7         |
| Prompt-order ensemble               | shuffled | sampled | **78.7** / **64.9** / **66.0** | **89.0** | **84.8** | 80.3 / 81.2         |
| Input-rationale ensemble            | sampled  | greedy  | 70.1 / 60.1 / 61.1             | 87.1     | 79.1     | 73.4 / 75.9         |
| Input-rationale ensemble            | sampled  | sampled | **78.3** / **64.5** / **64.3** | **88.8** | **85.2** | 78.8 / 81.0         |
| Self-consistency [self_consistency] | fixed    | sampled | **78.5** / **64.5** / **63.4** | **88.4** | **86.3** | 79.5 / 80.5         |

We explain these experiments in more detail. Table 2 shows the results obtained across a range of natural language inference tasks. One can see that the three rationale-augmented ensembling strategies ("output-sampled") all achieve significantly higher accuracy than chain-of-thought prompting with human-written rationales [wei2022chain]. On e-SNLI, RTE, and MNLI, the chain-of-thought approach produces worse performance than standard prompting, while rationale-augmented ensembling is able to boost the performance significantly, outperforming chain-of-thought prompting in every case, and outperforming standard prompting in all cases except MNLI.

**Table 3: Performance comparison over question answering tasks on PaLM-540B.**

| Method                              | Input    | Output  | BoolQ (q only) | BoolQ (w/ passage) | HotpotQA (q only, EM/F1) | OpenBookQA (q only) |
| ----------------------------------- | -------- | ------- | -------------- | ------------------ | ------------------------ | ------------------- |
| Zero-shot CoT [step_by_step]        | fixed    | greedy  | 55.4           | 71.7               | 17.1 / 23.0              | 67.6                |
| Standard-prompting (no-rationale)   | fixed    | greedy  | 71.3           | 89.7               | 27.1 / 36.8              | 84.4                |
| CoT-prompting [wei2022chain]        | fixed    | greedy  | 74.2           | 85.4               | 28.9 / 39.8              | 86.4                |
| Prompt-order ensemble               | shuffled | greedy  | 73.3           | 87.4               | 30.3 / 41.3              | 87.6                |
| Prompt-order ensemble               | shuffled | sampled | **78.0**       | **91.0**           | **34.7** / **45.4**      | **91.0**            |
| Input-rationale ensemble            | sampled  | greedy  | 75.0           | 86.5               | 30.9 / 41.7              | 87.4                |
| Input-rationale ensemble            | sampled  | sampled | **78.6**       | **90.9**           | **32.4 / 43.7**          | **90.0**            |
| Self-consistency [self_consistency] | fixed    | sampled | **78.4**       | **90.6**           | **33.8 / 44.6**          | **90.0**            |

Similarly, Table 3 shows the results obtained in four question answering tasks. For BoolQ, we conducted an evaluation in both the closed-book setting (the model is given a question only, without providing a relevant passage), as well as the setting where both the question and a relevant passage are provided. In both settings, rationale-augmented ensembling ("output-sampled") outperforms standard and chain-of-thought prompting. For HotpotQA, we conducted the evaluation in the closed-book setting, where rationale-augmented ensembling achieves a higher EM and F1 score compared to both baselines. An important question for open-domain question answering in the closed-book setting is how to utilize a language model to retrieve relevant knowledge and compose the final answer [roberts-etal-2020-much]. Our results show that rationale-augmented ensembling is an effective technique for encouraging a language model to retrieve _multiple_ relevant facts for a given question. To illustrate this phenomenon, Table 4 demonstrates some of the retrieved facts used to yield final answers.

**Table 4: Examples of how the language model retrieves multiple relevant facts and composes rationales for open-domain question-answering in the closed-book setting.**

| Task / Question                                                                                                                                   | Golden passage                                                                                      | Retrieved facts and composed rationales from the language model                                                                                            |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[BoolQ]** can u drive in canada with us license (answer: yes)                                                                                   | Persons driving into Canada must have their vehicle's registration document and proof of insurance. | Yes, you can drive in Canada with a U.S. licence. You need to have a signed letter from your car rental company.                                           |     | 49 U.S. states and 6 Canadian provinces have a reciprocal agreement for the recognition of driver licensing. As long as you have a valid U.S. driver's license, you may drive in Canada. The answer is yes.                                   |
| **[HotpotQA]** What government position was held by the woman who portrayed Corliss Archer in the film Kiss and Tell? (answer: Chief of Protocol) | Kiss and Tell is ... starring then 17-year-old Shirley Temple as Corliss Archer.                    | Shirley Temple Black played Corliss Archer in Kiss and Tell. Black was the United States Ambassador to Ghana and Czechoslovakia. The answer is Ambassador. |     | Corliss Archer was a fictional character. Actress Shirley Temple portrayed Corliss Archer in the film Kiss and Tell. In 1967, Shirley Temple became the first female Chief of Protocol in the United States. The answer is Chief of Protocol. |

**Table 5: Performance comparison over other common NLP tasks, on PaLM-540B.**

| Method                              | Input    | Output  | WiC             | SST-2    | QQP      | ARC-e    | ARC-c    | GSM8K    |
| ----------------------------------- | -------- | ------- | --------------- | -------- | -------- | -------- | -------- | -------- |
| Zero-shot CoT [step_by_step]        | fixed    | greedy  | 54.1            | 76.8     | 55.8     | 87.0     | 79.6     | 43.0     |
| Standard-prompting (no-rationale)   | fixed    | greedy  | 67.6            | **94.6** | **84.1** | 95.9     | 87.1     | 17.9     |
| CoT-prompting [wei2022chain]        | fixed    | greedy  | 65.2            | 87.8     | 75.6     | 95.3     | 85.2     | 56.5     |
| Prompt-order ensemble               | shuffled | greedy  | 62.1            | 88.1     | 76.6     | 94.5     | 85.6     | 59.6     |
| Prompt-order ensemble               | shuffled | sampled | 62.5            | 91.2     | 80.9     | **96.4** | **88.5** | **75.4** |
| Input-rationale ensemble            | sampled  | greedy  | 66.5 / **72.1** | 92.3     | 76.6     | 95.5     | 86.6     | 58.9     |
| Input-rationale ensemble            | sampled  | sampled | 65.2 / **70.8** | 93.1     | 81.2     | **96.7** | **88.6** | **73.8** |
| Self-consistency [self_consistency] | fixed    | sampled | 66.9            | 91.1     | 78.9     | **96.4** | **88.7** | **74.4** |

Finally, Table 5 provides results for other common natural language processing tasks. Interestingly, for tasks that do not require explicit intermediate steps, such as SST-2 and QQP, adding manual rationales to prompts can degrade performance significantly. Yet, in these cases, rationale-augmented ensembles ("output-sampled") are able to significantly close the gap. For WiC, ARC-easy/challenge and GSM8K, rationale-augmented ensembling outperforms both standard and chain-of-thought prompting by a large margin. Here, for WiC, we evaluated an alternative variant of the input-rationale ensemble: instead of replacing one rationale in each prompt, we replace every original rationales by a generated one in each prompt. This variant generally yields similar or slightly worse performance compared to replacing one rationale at a time, but on the WiC task we observed a performance improvement (70.8% versus 65.2% when only one rationale is replaced), which indicates that this task might require greater rationale diversity to support strong task performance.

## Results on GPT-3

To control for the effects of the language model and aid reproducibility, we repeat the above studies with the publicly available GPT-3 model [brown2020language; instructGPT]. Once again, we find similar outcomes where rationale-augmented ensembling robustly improves performance across natural language tasks. Here we use the code-davinci-002 engine [chen2021evaluating], which has been observed to yield slightly better performance than text-davinci-002. The results of this study are given in Table 6, showing that rationale-augmented ensembles with GPT-3 obtain similar improvements to those obtained with PaLM-540B above. Once again, human-written rationales in few-shot learning can sometimes degrade performance compared to standard prompting (e.g., on RTE, OpenBookQA, WiC, ARC-challenge), while rationale-augmented ensembling with sampling in the output space ("output-sampled") reliably improves performance over both baselines. Similarly, for WiC, introducing greater diversity in sampled rationales improves performance (67.6%) compared to sampling a single rationale for each prompt (57.4%). These results reinforce the finding that the improvements are robust to the specific language model, provided it is of sufficient size/quality.

**Table 6: Performance comparison on GPT-3 (code-davinci-002 engine).**

| Method                              | Input    | Output  | RTE      | BoolQ    | OpenBookQA | WiC             | ARC-c    |
| ----------------------------------- | -------- | ------- | -------- | -------- | ---------- | --------------- | -------- |
| Standard-prompting (no-rationale)   | fixed    | greedy  | 85.2     | 69.9     | 81.4       | 65.5            | 85.9     |
| CoT-prompting [wei2022chain]        | fixed    | greedy  | 84.1     | 73.5     | 80.4       | 55.5            | 83.6     |
| Prompt-order ensemble               | shuffled | greedy  | 83.0     | 74.2     | 83.4       | 56.4            | 84.0     |
| Prompt-order ensemble               | shuffled | sampled | **88.8** | **78.5** | **87.8**   | 56.7            | **88.2** |
| Input-rationale ensemble            | sampled  | greedy  | 85.2     | 75.0     | 85.4       | 57.1 / **68.0** | 84.7     |
| Input-rationale ensemble            | sampled  | sampled | **87.4** | **78.4** | **87.0**   | 57.4 / **67.6** | **87.6** |
| Self-consistency [self_consistency] | fixed    | sampled | 85.6     | **78.2** | **88.4**   | 55.6            | **87.5** |

## Additional Studies

#### Effect of K in K-shot in-context learning.

In Table 7, we provide an ablation study that examines the effect of choosing different `latex $K$ ` in `latex $K$ `-shot in-context learning. While increasing the number of exemplars `latex $K$ ` generally improves performance, rationale-augmented ensembling robustly improves performance over standard and chain-of-thought prompting for all values of `latex $K$ `.

**Table 7: Performance comparison on ANLI-R1 using PaLM-540B, with varying K and templates.**

| Method                              | Input    | Output  | 3-shot | 6-shot/T-1 | 9-shot | T-2  | T-3  |
| ----------------------------------- | -------- | ------- | ------ | ---------- | ------ | ---- | ---- |
| Standard-prompting (no-rationale)   | fixed    | greedy  | 67.9   | 69.1       | 69.3   | 66.1 | 66.4 |
| CoT-prompting [wei2022chain]        | fixed    | greedy  | 71.6   | 68.8       | 72.2   | 67.9 | 68.3 |
| Prompt-order ensemble               | shuffled | sampled | 76.0   | 78.7       | 80.1   | 78.4 | 75.6 |
| Input-rationale ensemble            | sampled  | sampled | 76.1   | 78.3       | 78.4   | 77.8 | 76.0 |
| Self-consistency [self_consistency] | fixed    | sampled | 77.9   | 78.5       | 78.7   | 76.6 | 76.9 |

#### Effect of templates and verbalizers.

We also investigate whether rationale-augmented ensembling is robust to different templates or verbalizers, since previous work has shown that templates or verbalizers can have a significant effect on final performance [bach2022promptsource]. Here we choose three alternative templates from PromptSource for the NLI task, as follows:

- Template-1: _Premise:[newline]{premise}"[newline]Based on this premise, can we conclude the hypothesis "{hypothesis}" ... is true?[newline]options_

- Template-2: _"{premise}"[newline]Does it follow that "{hypothesis}"?[newline]options_

- Template-3: _Suppose "premise"[newline]Can we infer that "hypothesis"?[newline]options_

The results in Table 7 reveal that, although different templates can induce variable performance, rationale-augmented ensembling outperforms standard and chain-of-thought prompting under all three templates.

#### Effect of using existing explanations vs newly-written ones in the prompts.

To control for the bias of manually written rationales, we also investigate performance on the e-SNLI dataset using crowd-sourced rationales [esnli]. As shown in Table 2, the improvement of rationale-augmented ensemble appears to be stable regardless of whether the rationales are crowd-sourced or author-supplied.

Note that in this paper, we focus on the role of "rationales", and conduct the studies in a manner that fixes other factors that might affect task performance. Due to the large performance variance across alternative set-ups, it is clear that a rigorous evaluation of few-shot in-context learning requires the specification of all these factors, including (1) the exact prompts used, including the specific exemplars, templates/verbalizers, instructions, or rationales/explanations used; and (2) the exact prompt order and the number of exemplars `latex $K$ ` used.

# Related work

#### Rationalization and interpretability in NLP.

One relevant line of work tries to improve rationalization and interpretability in natural language processing models, for example, by extracting rationales using task-specific approaches [xu-etal-2021-exploiting-reasoning; Asai2020Learning; DBLP:journals/corr/abs-1910-02610]. In the supervised learning setting, one typically fine-tunes a model using human-annotated rationales as training data [zaidan-etal-2007-using; ling-etal-2017-program; wt5; cobbe2021training]. [star] propose to use prompting to augment a training dataset with rationales, then fine-tune a language model using this dataset to further improve reasoning ability. [better_reasoner] propose to sample "diverse" prompts from the training set augmented by rationales, plus an additional voting verifier to improve model performance on reasoning tasks. However, the use of an additional training set is closer to the fine-tuning setting rather than the few-shot setting. Compared to these approaches, rationale-augmented ensembles focus more on the few-shot setting, where there is no additional training or fine-tuning, hence no human annotation nor training/development datasets are required.

Recent work has also considered _prompting_ language models with human-written rationales to further improve performance, such as [wei2022chain; step_by_step; self_consistency; maieutic_prompting]. [explanation_deepmind] show that hand-tuned explanations can improve task performance substantially. By contrast, rationale-augmented ensembling requires no hand-tuning on rationales. Instead, we leverage the language model to automatically sample rationales to overcome the sub-optimality of manually provided rationales.

#### Prompt optimization and ensembles in language models.

Previous work has shown that the prompt order [Lu2021FantasticallyOP], how each task is verbalized [bach2022promptsource], and the distribution of labels in the prompts [pmlr-v139-zhao21c] can all affect final task performance. In this paper, we find that, when shifting from the paradigm of (input `latex $\rightarrow$ ` output) pairs to (input, _rationale_ `latex $\rightarrow$ ` output) pairs, there is also a large variance in the final task performance when the _rationales_ used in the prompts differ. Recent work has also proposed ways to further improve a model's reasoning ability under specific constraints. For example, when the final label is binary, [maieutic_prompting] induce a tree of explanations, then use an SAT solver and an NLI verifier to infer the satisfiability of each explanation. For commonsense reasoning tasks, [liu-etal-2022-generated] generate relevant knowledge as additional inputs to the model, to improve the performance. Another line of work proposes to better retrieve prompts closer to the target question to further improve task performance [liu-etal-2022-makes; learning_to_retrieve].

#### Learn to execute programs with intermediate computations.

Although much of the work on rationales has come from the natural language processing literature, there has been growing interest in similar mechanisms in the area of program synthesis. [scratchpad] use pretrained language models to execute a program by predicting the intermediate states of a program behaviour line-by-line. This work shows that eliciting step-by-step reasoning described by a formal language can dramatically improve the execution prediction accuracy. Other recent work [pi2022reasoning] pre-trains language models as program executors and shows that this can improve reasoning task performance.

# Conclusion

In this paper, we have presented a unified framework for rationale-augmented ensembles, and found that rationale sampling in the output space is a key component for achieving improved performance in natural language processing tasks. By sampling diverse rationales and ensembling the results, we have shown that rational-ensembling methods in the proposed framework can reliably outperform standard prompting and rationale-based few-shot prompting, across a wide range of natural language tasks and alternative language models. Overall, rationale-augmented ensembling appears to be a reliable way to shift from the paradigm of (input `latex $\rightarrow$ ` output) pairs to (input, _rationale_ `latex $\rightarrow$ ` output) pairs to achieve more accurate and interpretable natural language processing.

Although the proposed framework mitigates sensitivity to human-written rationales, some human-written seed rationales are still required, which could still bias generation of output rationales. We have observed that patterns expressed in the written rationales can affect a model's generated rationales. For example, if all seed rationales are written in a similar style, like "The first...the second...", subsequently generated rationales will tend to follow the same pattern. Therefore, some diversity in seed rationales still appears to be important for inducing sufficient diversity in generated rationales.

Overall, through this study, we hope to motivate more research on understanding how language models respond differently to variations in few-shot exemplars, which can lead to the development of more robust and autonomous approaches for generating effective prompts for a given target task.

# Appendix

## Full Sets of Prompts

**Few-shot exemplars for RTE:**

Premise: "No Weapons of Mass Destruction Found in Iraq Yet."
Based on this premise, can we conclude the hypothesis "Weapons of Mass Destruction Found in Iraq." is true?
**A:** "No Weapons of Mass Destruction Found" contradicts "Weapons of Mass Destruction Found". The answer is no.

Premise: "A place of sorrow, after Pope John Paul II died, became a place of celebration, as Roman Catholic faithful gathered in downtown Chicago to mark the installation of new Pope Benedict XVI."
Based on this premise, can we conclude the hypothesis "Pope Benedict XVI is the new leader of the Roman Catholic Church." is true?
**A:** "installation of new Pope Benedict XVI." means "Pope Benedict XVI is the new leader". The answer is yes.

Premise: "A man is due in court later charged with the murder 26 years ago of a teenager whose case was the first to be featured on BBC One's Crimewatch. Colette Aram, 16, was walking to her boyfriend's house in Keyworth, Nottinghamshire, on 30 October 1983 when she disappeared. Her body was later found in a field close to her home. Paul Stewart Hutchinson, 50, has been charged with murder and is due before Nottingham magistrates later."
Based on this premise, can we conclude the hypothesis "Paul Stewart Hutchinson is accused of having stabbed a girl." is true?
**A:** The premise does not say Paul Stewart Hutchinson "stabbed" this girl. The answer is no.

Premise: "Herceptin was already approved to treat the sickest breast cancer patients, and the company said, Monday, it will discuss with federal regulators the possibility of prescribing the drug for more breast cancer patients."
Based on this premise, can we conclude the hypothesis "Herceptin can be used to treat breast cancer." is true?
**A:** "Herceptin was approved to treat breast cancer" implies that "Herceptin can be used to treat breast cancer". The answer is yes.

**Few-shot exemplars for ARC easy/challenge:**

**Q:** George wants to warm his hands quickly by rubbing them. Which skin surface will produce the most heat? (a) dry palms. (b) wet palms. (c) palms covered with oil. (d) palms covered with lotion.
**A:** Dry surfaces will more likely cause more friction via rubbing than other smoother surfaces, hence dry palms will produce the most heat. The answer is (a).

**Q:** Which factor will most likely cause a person to develop a fever? (a) a leg muscle relaxing after exercise. (b) a bacterial population in the bloodstream. (c) several viral particles on the skin. (d) carbohydrates being digested in the stomach.
**A:** Option (b), bacterial population is the most likely cause for a person developing fever. The answer is (b).

**Q:** Which change in the state of water particles causes the particles to become arranged in a fixed position? (a) boiling. (b) melting. (c) freezing. (d) evaporating.
**A:** When water is freezed, the particles are arranged in a fixed position; the particles are still moving for all other options. The answer is (c).

**Q:** When a switch is used in an electrical circuit, the switch can (a) cause the charge to build. (b) increase and decrease the voltage. (c) cause the current to change direction. (d) stop and start the flow of current.
**A:** The function of a switch is to start and stop the flow of a current. The answer is (d).

**Few-shot exemplars for NLI tasks, including ANLI and MNLI:**

Premise: "Conceptually cream skimming has two basic dimensions - product and geography."
Based on this premise, can we conclude the hypothesis "Product and geography are what make cream skimming work." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** Based on "cream skimming has two basic dimensions" we can't infer that these two dimensions are what make cream skimming work. The answer is it is not possible to tell.

Premise: "One of our member will carry out your instructions minutely."
Based on this premise, can we conclude the hypothesis "A member of my team will execute your orders with immense precision." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** "one of" means the same as "a member of", "carry out" means the same as "execute", and "minutely" means the same as "immense precision". The answer is yes.

Premise: "Fun for adults and children."
Based on this premise, can we conclude the hypothesis "Fun for only children." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** "adults and children" contradicts "only children". The answer is no.

Premise: "He turned and smiled at Vrenna."
Based on this premise, can we conclude the hypothesis "He smiled at Vrenna who was walking slowly behind him with her mother." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** the premise does not say anything about "Vrenna was walking". The answer is it is not possible to tell.

Premise: "well you see that on television also"
Based on this premise, can we conclude the hypothesis "You can see that on television, as well." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** "also" and "as well" mean the same thing. The answer is yes.

Premise: "Vrenna and I both fought him and he nearly took us."
Based on this premise, can we conclude the hypothesis "Neither Vrenna nor myself have ever fought him." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** "Vrenna and I both" contradicts "neither Vrenna nor myself". The answer is no.

**Few-shot exemplars for e-SNLI (the rationales are crowd-sourced annotations from the original dataset):**

Premise: "A person on a horse jumps over a broken down airplane."
Based on this premise, can we conclude the hypothesis "A person is training his horse for a competition." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** The person is not necessarily training his horse. The answer is it is not possible to tell.

Premise: "A person on a horse jumps over a broken down airplane."
Based on this premise, can we conclude the hypothesis "A person is at a diner, ordering an omelette." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** One jumping horse cannot be in a diner ordering food. The answer is no.

Premise: "A person on a horse jumps over a broken down airplane."
Based on this premise, can we conclude the hypothesis "A person is outdoors, on a horse." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** A broken down airplane is outdoors. The answer is yes.

Premise: "Children smiling and waving at camera."
Based on this premise, can we conclude the hypothesis "They are smiling at their parents." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** Just because they are smiling and waving at a camera does not imply their parents or anyone is anyone behind it. The answer is it is not possible to tell.

Premise: "Children smiling and waving at camera."
Based on this premise, can we conclude the hypothesis "The kids are frowning." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** One cannot be smiling and frowning at the same time. The answer is no.

Premise: "Children smiling and waving at camera."
Based on this premise, can we conclude the hypothesis "There are children present." is true?
OPTIONS: - yes - no - it is not possible to tell
**A:** The children must be present to see them smiling and waving. The answer is yes.

**Few-shot exemplars for BoolQ (closed-book setting):**

**Q:** does system of a down have 2 singers?
**A:** System of a Down currently consists of Serj Tankian, Daron Malakian, Shavo Odadjian and John Dolmayan. Serj and Daron do vocals, so the band does have two singers. The answer is yes.

**Q:** do iran and afghanistan speak the same language?
**A:** Iran and Afghanistan both speak the Indo-European language Persian. The answer is yes.

**Q:** is a cello and a bass the same thing?
**A:** The cello is played sitting down with the instrument between the knees, whereas the double bass is played standing or sitting on a stool. The answer is no.

**Q:** can you use oyster card at epsom station?
**A:** Epsom railway station serves the town of Epsom in Surrey and is not in the London Oyster card zone. The answer is no.

**Few-shot exemplars for BoolQ (with passage provided):**

**Q:** System of a Down, sometimes shortened to System and abbreviated as SOAD, is an Armenian-American heavy metal band from Glendale, California, formed in 1994. The band currently consists of Serj Tankian (lead vocals, keyboards), Daron Malakian (vocals, guitar), Shavo Odadjian (bass, backing vocals) and John Dolmayan (drums).
Based on the above text, does system of a down have 2 singers?
**A:** System of a Down currently consists of Serj Tankian, Daron Malakian, Shavo Odadjian and John Dolmayan. Serj and Daron do vocals, so the band does have two singers. The answer is yes.

**Q:** Persian, also known by its endonym Farsi, is one of the Western Iranian languages within the Indo-Iranian branch of the Indo-European language family. It is primarily spoken in Iran, Afghanistan, and Tajikistan, and some other regions which historically were Persianate societies and considered part of Greater Iran.
Based on the above text, do iran and afghanistan speak the same language?
**A:** Iran and Afghanistan both speak the Indo-European language Persian. The answer is yes.

**Q:** Both the violin and viola are played under the jaw. The viola, being the larger of the two instruments, has a playing range that reaches a perfect fifth below the violin's. The cello is played sitting down with the instrument between the knees, and its playing range reaches an octave below the viola's. The double bass is played standing or sitting on a stool, with a range that typically reaches a minor sixth, an octave or a ninth below the cello's.
Based on the above text, is a cello and a bass the same thing?
**A:** The cello is played sitting down with the instrument between the knees, whereas the double bass is played standing or sitting on a stool. The answer is no.

**Q:** Epsom railway station serves the town of Epsom in Surrey. It is located off Waterloo Road and is less than two minutes' walk from the High Street. It is not in the London Oyster card zone unlike Epsom Downs or Tattenham Corner stations. The station building was replaced in 2012/2013 with a new building with apartments above the station.
Based on the above text, can you use oyster card at epsom station?
**A:** Epsom railway station serves the town of Epsom in Surrey and is not in the London Oyster card zone. The answer is no.

**Few-shot exemplars for HotpotQA (closed-book setting):**

**Q:** Which magazine was started first Arthur's Magazine or First for Women?
**A:** Arthur's Magazine started in 1844. First for Women started in 1989. So Arthur's Magazine was started first. The answer is Arthur's Magazine.

**Q:** The Oberoi family is part of a hotel company that has a head office in what city?
**A:** The Oberoi family is part of the hotel company called The Oberoi Group. The Oberoi Group has its head office in Delhi. The answer is Delhi.

**Q:** What nationality was James Henry Miller's wife?
**A:** James Henry Miller's wife is June Miller. June Miller is an American. The answer is American.

**Q:** The Dutch-Belgian television series that "House of Anubis" was based on first aired in what year?
**A:** "House of Anubis" is based on the Dutch--Belgian television series Het Huis Anubis. Het Huis Anubis is first aired in September 2006. The answer is 2006.

**Few-shot exemplars for OpenBookQA:**

**Q:** Poison causes harm to which of the following? (a) a Tree (b) a robot (c) a house (d) a car
**A:** Poison will harm living things, only a tree is a living thing. The answer is (a).

**Q:** As you look deeper into a Marbel you can see (a) the future (b) minut defects (c) colors (d) the other side
**A:** Marbel is not transparent, so you can not see the other side. Marbel does not necessarily have multiple colors. You will see minut defects. The answer is (b).

**Q:** When food is reduced in the stomach (a) the mind needs time to digest (b) take a second to digest what I said (c) nutrients are being deconstructed (d) reader's digest is a body of works
**A:** The food is being deconstructed in the stomach during digestion. The answer is (c).

**Q:** The sun is responsible for (a) puppies learning new tricks (b) children growing up and getting old (c) flowers wilting in a vase (d) plants sprouting, blooming and wilting
**A:** The sun can affect the growing of living things, like plants. The answer is (d).

**Few-shot exemplars for WiC:**

Do you want to come over to my place later?
A political system with no place for the less prominent groups.
**Q:** Is the word "place" used in the same way in the two sentences above?
**A:** The first "place" means "home", the second "place" means "room". The answer is no.

Approach a task.
To approach the city.
**Q:** Is the word "approach" used in the same way in the two sentences above?
**A:** The first "approach" means "deal with", the second "approach" means "come near". The answer is no.

The general ordered the colonel to hold his position at all costs.
Hold the taxi.
**Q:** Is the word "hold" used in the same way in the two sentences above?
**A:** Both "hold" mean "keep" or "detain". The answer is yes.

We like to summer in the Mediterranean.
We summered in Kashmir.
**Q:** Is the word "summer" used in the same way in the two sentences above?
**A:** Both "summer" mean "spend the summer". The answer is yes.

**Few-shot exemplars for SST-2:**

What is the sentiment of the following sentence?
"that loves its characters and communicates something rather beautiful about human nature"
**A:** "loves its characters" indicates positive sentiment. The answer is positive.

What is the sentiment of the following sentence?
"hide new secretions from the parental units"
**A:** If people are hiding something, it means the sentiment is on the negative side. The answer is negative.

What is the sentiment of the following sentence?
"the greatest musicians"
**A:** By saying someone being the "greatest", it means positive sentiment. The answer is positive.

What is the sentiment of the following sentence?
"contains no wit , only labored gags"
**A:** "contains no wit" is clearly a negative sentiment. The answer is negative.

What is the sentiment of the following sentence?
"demonstrates that the director of such hollywood blockbusters as patriot games can still turn out a small , personal film with an emotional wallop ."
**A:** "can still turn out a small , personal film with an emotional wallop ." indicates sentiment on the positive side. The answer is positive.

What is the sentiment of the following sentence?
"that 's far too tragic to merit such superficial treatment"
**A:** "far too tragic" and "to merit such superficial treatment" both mean negative sentiments. The answer is negative.

**Few-shot exemplars for QQP:**

Is the following question "What causes stool color to change to yellow?" the same as "What can cause stool to come out as little balls?"
**A:** "change to yellow" and "come out as little balls" mean different things. The answer is no.

Is the following question "What can one do after MBBS?" the same as "What do i do after my MBBS?"
**A:** Both are asking what can a person do after MBBS. The answer is yes.

Is the following question "How is air traffic controlled?" the same as "How do you become an air traffic controller?"
**A:** "How is air traffic controlled" means differently as "how to become a controller". The answer is no.

Is the following question "How do I control my horny emotions?" the same as "How do you control your horniness?"
**A:** "horny emotions" means the same as "horniness". The answer is yes.

---

**Notes:**

1. Specifically, we sample 1,024 rationales for each exemplar and only keep those where the final answer is consistent with the ground truth answer.

2. A line of existing work uses a train/validation set to determine the optimal prompts (either discrete or continuous), e.g., [lester-etal-2021-power; gao-etal-2021-making]. Such a setting is closer to fine-tuning rather than few-shot learning, due to the use of an additional dataset for performance validation.

3. We use the test split for all tasks if the test split is available and has labels for evaluation, otherwise we use the dev split. Specifically, test split: ANLI, e-SNLI, OpenBookQA, ARC; dev/validation split: MNLI, RTE, BoolQ, Hotpot-QA, WiC, SST-2, QQP. In addition, some of the datasets are too large to run large language models on, so we used the first 1,000 data points for HotpotQA, e-SNLI, MNLI, and QQP for evaluation.

4. We have found the zero-shot CoT approach yields slightly less controlled responses compared to few-shot based approaches, i.e., the model is less likely to generate a desired fixed answer like "yes/no", "(a)-(e)" even when we add guided prompts like "The answer (yes or no) is", "among options (a) through (e)".

5. https://github.com/bigscience-workshop/promptsource
