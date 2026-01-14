## Abstract {#abstract .unnumbered}

Generative Artificial Intelligence (GenAI) systems are increasingly being deployed across diverse industries and research domains. Developers and end-users interact with these systems through the use of prompting and prompt engineering. Although prompt engineering is a widely adopted and extensively researched area, it suffers from conflicting terminology and a fragmented ontological understanding of what constitutes an effective prompt due to its relatively recent emergence. We establish a structured understanding of prompt engineering by assembling a taxonomy of prompting techniques and analyzing their applications. We present a detailed vocabulary of 33 vocabulary terms, a taxonomy of 58 LLM prompting techniques, and 40 techniques for other modalities. Additionally, we provide best practices and guidelines for prompt engineering, including advice for prompting engineering ChatGPT and other state-of-the-art (SOTA) LLMs. We further present a meta-analysis of the entire literature on natural language prefix-prompting. As a culmination of these efforts, this paper presents the most comprehensive survey on prompt engineering to date.

# Introduction

Transformer-based LLMs are widely deployed in consumer-facing, internal, and research settings [Bommasani2021OnTO]. Typically, these models rely on the user providing an input "prompt" to which the model produces an output in response. Such prompts may be textual---"Write a poem about trees."---or take other forms: images, audio, videos, or a combination thereof. The ability to prompt models, particularly prompting with natural language, makes them easy to interact with and use flexibly across a wide range of use cases.

Knowing how to effectively structure, evaluate, and perform other tasks with prompts is essential to using these models. Empirically, better prompts lead to improved results across a wide range of tasks [wei2022chainofthought; @liu2023pretrain; @Schulhoff_Learn_Prompting_2022]. A large body of literature has grown around the use of prompting to improve results and the number of prompting techniques is rapidly increasing.

However, as prompting is an emerging field, the use of prompts continues to be poorly understood, with only a fraction of existing terminologies and techniques being well-known among practitioners. We perform a large-scale review of prompting techniques to create a robust resource of terminology and techniques in the field. We expect this to be the first iteration of terminologies that will develop over time. We maintain an up-to-date list of terms and techniques at [LearnPrompting.org](https://learnprompting.org).

##### Scope of Study

We create a broad directory of prompting techniques, that can be quickly understood and easily implemented for rapid experimentation by developers and researchers. To this end, we limit our study to focus on prefix prompts [Shin2020ElicitingKF] rather than cloze prompts [petroni2019language; @cui2021template], because modern LLM transformer architectures widely employ prefix prompts and provide robust support for both developers and researchers [brown2020language; @gemini_1_report; @touvron2023llama2openfoundation]. Additionally, we refined our focus to hard (discrete) prompts rather than soft (continuous) prompts and leave out papers that make use of techniques using gradient-based updates (i.e. fine-tuning). Hard prompts contain only tokens (vectors) that correspond to words in the model's vocabulary, while soft prompts may contain tokens that have no corresponding word in the vocabulary.

Finally, we only study task-agnostic techniques. These decisions keep the work approachable to less technical readers and maintain a manageable scope.

##### Sections Overview

We conducted a machine-assisted systematic review grounded in the PRISMA process [Page2021the] (Section [2.1](#sec:systematic){reference-type="ref" reference="sec:systematic"}) to identify 58 different text-based prompting techniques, from which we create a taxonomy with a robust terminology of prompting terms (Section [1.2](#sec:vocabulary){reference-type="ref" reference="sec:vocabulary"}).

[IMAGE: Categories within the field of prompting are interconnected. We discuss 7 core categories that are well described by the papers within our scope.]

Our goal is to provide a roadmap for the community when considering which prompting techniques to use (Figure [1.1](#fig:categories){reference-type="ref" reference="fig:categories"}). While much literature on prompting focuses on English-only settings, we also discuss multilingual techniques (Section [\[sec:multilingual\]](#sec:multilingual){reference-type="ref" reference="sec:multilingual"}). Given the rapid growth in multimodal prompting, where prompts may include media such as images, we also expand our scope to multimodal techniques (Section [3.2](#sec:multimodal){reference-type="ref" reference="sec:multimodal"}). Many multilingual and multimodal prompting techniques are direct extensions of English text-only prompting techniques.

As prompting techniques grow more complex, they have begun to incorporate external tools, such as Internet browsing and calculators. We use the term \"agents\" to describe these types of prompting techniques (Section [4.1](#sec:agents){reference-type="ref" reference="sec:agents"}).

It is important to understand how to evaluate the outputs of agents and prompting techniques to ensure accuracy and avoid hallucinations. Thus, we discuss ways of evaluating these outputs (Section [4.2](#sec:evaluation){reference-type="ref" reference="sec:evaluation"}). We also discuss security (Section [5.1](#sec:security){reference-type="ref" reference="sec:security"}) and safety measures (Section [5.2](#sec:safety){reference-type="ref" reference="sec:safety"}) for designing prompts that reduce the risk of harm to companies and users.

Finally, we apply prompting techniques in two case studies (Section [6.1](#sec:technique_benchmarking){reference-type="ref" reference="sec:technique_benchmarking"}). In the first, we test a range of prompting techniques against the commonly used benchmark MMLU [hendrycks2020measuring]. In the second, we explore in detail an example of manual prompt engineering on a significant, real-world use case, identifying signals of frantic hopelessness--a top indicator of suicidal crisis--in the text of individuals seeking support [shuck-etal-2019-suicide]. We conclude with a discussion of the nature of prompting and its recent development (Section [8](#sec:conclusion){reference-type="ref" reference="sec:conclusion"}).

## What is a Prompt? {#prompt-def}

A prompt is an input to a Generative AI model, that is used to guide its output [mesko2023prompt; @white2023prompt; @heston2023prompt; @hadi2023large; @brown2020language]. Prompts may consist of text, image, sound, or other media. Some examples of prompts include the text, "write a three paragraph email for a marketing campaign for an accounting firm", a photograph of a piece of paper with the words "what is 10\*179" written on it, or a recording of an online meeting, with the instructions "summarize this". Prompts usually have some text component, but this may change as non-text modalities become more common.

##### Prompt Template

Prompts are often constructed via a prompt template [shin2020autoprompt]. A prompt template is a function that contains one or more variables which will be replaced by some media (usually text) to create a prompt. This prompt can then be considered to be an *instance* of the template.

Consider applying prompting to the task of binary classification of tweets. Here is an initial prompt template that can be used to classify inputs.

::: pbox
 Classify the tweet as positive or negative:\
{TWEET}
:::

Each tweet in the dataset would be inserted into a separate instance of the template and the resulting prompt would be given to a LLM for inference.

<figure id="fig:prompt-vs-prompt-template">
<div class="pbox">
<p>Write a poem about trees.</p>
</div>
<div class="pbox">
<p>Write a poem about the following topic: {USER_INPUT}</p>
</div>
<figcaption>Prompts and prompt templates are distinct concepts; a prompt template becomes a prompt when input is inserted into it.</figcaption>
</figure>

## Terminology {#sec:vocabulary}

<figure id="fig:terminology" data-latex-placement="tbph!">
<div class="forest">
<p>for tree=<span> grow=east, reversed=true, anchor=base west, parent anchor=east, child anchor=west, base=left, font=, rectangle, draw=black, rounded corners, align=left, minimum width=2em, edge+=<span>darkgray, line width=1pt</span>, s sep=1pt, inner xsep=1pt, inner ysep=2pt, line width=0.8pt, ver/.append style=<span>rotate=90, child anchor=north, parent anchor=south, anchor=center</span>, text width=7em, </span>, [Prompt <a href="#prompt-def" data-reference-type="ref" data-reference="prompt-def">1.1</a>, text width=3em , fill=teal!50 [Prompting <a href="#prompting" data-reference-type="ref" data-reference="prompting">[prompting]</a>, fill=red!50 [Context <a href="#additional-info" data-reference-type="ref" data-reference="additional-info">[additional-info]</a>, fill=red!40] [Context Window <a href="#context-window" data-reference-type="ref" data-reference="context-window">9.2.1.0.1</a>, fill=red!40] [Priming <a href="#priming" data-reference-type="ref" data-reference="priming">[priming]</a>, fill=red!40] [Prompting Technique<br />
<a href="#prompting-technique" data-reference-type="ref" data-reference="prompting-technique">[prompting-technique]</a>, fill=red!40 [In-Context Learning<br />
<a href="#icl" data-reference-type="ref" data-reference="icl">[icl]</a>, fill=red!30 [Few-Shot Prompt <a href="#fsp" data-reference-type="ref" data-reference="fsp">[fsp]</a>, fill=red!20] [Exemplar <a href="#exemplar" data-reference-type="ref" data-reference="exemplar">[exemplar]</a>, fill=red!20] ] [Zero-Shot Prompt <a href="#sec:zero-shot-prompts" data-reference-type="ref" data-reference="sec:zero-shot-prompts">[sec:zero-shot-prompts]</a>, fill=red!30] ] [Orthogonal Prompt Types<br />
<a href="#orthogonal" data-reference-type="ref" data-reference="orthogonal">9.2.4</a>, fill=red!40 [ Density <a href="#hard-v-soft" data-reference-type="ref" data-reference="hard-v-soft">9.2.4.2</a>, fill=red!30 [Continuous Prompt<br />
<a href="#continuous-prompt" data-reference-type="ref" data-reference="continuous-prompt">9.2.4.2.2</a>, fill=red!20] [Discrete Prompt <a href="#discrete-prompt" data-reference-type="ref" data-reference="discrete-prompt">9.2.4.2.1</a>, fill=red!20] ] [ Originator <a href="#originator" data-reference-type="ref" data-reference="originator">9.2.4.1</a>, fill=red!30 [User Prompt <a href="#user-prompt" data-reference-type="ref" data-reference="user-prompt">9.2.4.1.1</a>, fill=red!20] [System Prompt <a href="#system-prompt" data-reference-type="ref" data-reference="system-prompt">9.2.4.1.3</a>, fill=red!20] [Assistant Prompt <a href="#assistant-prompt" data-reference-type="ref" data-reference="assistant-prompt">9.2.4.1.2</a>, fill=red!20] ] [ Prediction Style <a href="#prediction-style" data-reference-type="ref" data-reference="prediction-style">9.2.4.3</a>, fill=red!30 [Prefix <a href="#prefix" data-reference-type="ref" data-reference="prefix">9.2.4.3.2</a>, fill=red!20] [Cloze <a href="#cloze" data-reference-type="ref" data-reference="cloze">9.2.4.3.1</a>, fill=red!20] ] ] [ Prompt Chain <a href="#prompt-chain" data-reference-type="ref" data-reference="prompt-chain">[prompt-chain]</a>, fill=red!40 ] ] [Prompt Template <a href="#prompt-template" data-reference-type="ref" data-reference="prompt-template">1.1.0.0.1</a>, fill=blue!50] [ Prompt Engineering <a href="#prompt-engineering" data-reference-type="ref" data-reference="prompt-engineering">[prompt-engineering]</a>, fill=green!50 [ Prompt Engineering<br />
Technique <a href="#pe-technique" data-reference-type="ref" data-reference="pe-technique">[pe-technique]</a>, fill=green!40 ] [ Meta-Prompting <a href="#meta-prompting" data-reference-type="ref" data-reference="meta-prompting">[meta-prompting]</a>, fill=green!40 ] [ Answer Engineering<br />
<a href="#sec:answer-engineering" data-reference-type="ref" data-reference="sec:answer-engineering">[sec:answer-engineering]</a>, fill=green!40 [Verbalizer <a href="#verbalizer" data-reference-type="ref" data-reference="verbalizer">[verbalizer]</a>, fill=green!30] [Extractor <a href="#extraction" data-reference-type="ref" data-reference="extraction">[extraction]</a>, fill=green!30] [Answer Trigger <a href="#anwer-trigger" data-reference-type="ref" data-reference="anwer-trigger">[anwer-trigger]</a>, fill=green!30] ] [Conversational Prompt<br />
Engineering <a href="#conversational-prompt-engineering" data-reference-type="ref" data-reference="conversational-prompt-engineering">9.2.2.0.1</a>, fill=green!30] ] [ Fine-Tuning <a href="#fine-tuning" data-reference-type="ref" data-reference="fine-tuning">9.2.3</a>, fill=orange!50 [Prompt-Based<br />
Learning <a href="#prompt-based-learning" data-reference-type="ref" data-reference="prompt-based-learning">9.2.3.0.1</a>, fill=orange!40] [Prompt Tuning <a href="#prompt-tuning" data-reference-type="ref" data-reference="prompt-tuning">[prompt-tuning]</a>, fill=orange!40] ] ]</p>
</div>
<p>.</p>
<figcaption>A Terminology of prompting. Terms with links to the appendix are not sufficiently critical to describe in the main paper, but are important to the field of prompting. Prompting techniques are shown in Figure <a href="#fig:taxonomy" data-reference-type="ref" data-reference="fig:taxonomy">2.2</a></figcaption>
</figure>

# A Meta-Analysis of Prompting

## Systematic Review Process {#sec:systematic}

In order to robustly collect a dataset of sources for this paper, we ran a systematic literature review grounded in the PRISMA process [Page2021the] (Figure [2.1](#fig:prisma){reference-type="ref" reference="fig:prisma"}). We host this dataset on HuggingFace [^1] and present a datasheet [Gebru_2021] for the dataset in Appendix [9.3](#appx:datasheet){reference-type="ref" reference="appx:datasheet"}. Our main data sources were [arXiv](https://arxiv.org/), [Semantic Scholar](https://semanticscholar.com/), and [ACL](https://aclanthology.org). We query these databases with a list of 44 keywords narrowly related to prompting and prompt engineering (Appendix [9.4](#appx:keywords){reference-type="ref" reference="appx:keywords"}).

### The Pipeline

In this section, we introduce our data scraping pipeline, which includes both human and LLM-assisted review.[^2] As an initial sample to establish filtering critera, we retrieve papers from arXiv based on a simple set of keywords and boolean rules ([9.4](#appx:keywords){reference-type="ref" reference="appx:keywords"}). Then, human annotators label a sample of 1,661 articles from the arXiv set for the following criteria:

1.  Include if the paper proposes a novel prompting technique.

2.  Include if the paper strictly covers hard prefix prompts.

3.  Exclude if the paper focuses on training by backpropagating gradients.

4.  Include if the paper uses a masked frame and/or window for non-text modalities.

A set of 300 articles are reviewed independently by two annotators, with 92% agreement (Krippendorff's $\alpha$ = Cohen's $\kappa$ = 81%). Next, we develop a prompt using gpt-4-1106-preview to classify the remaining articles (Appendix [9.5](#sec:sys_rev_prompt){reference-type="ref" reference="sec:sys_rev_prompt"}). We validate the prompt against 100 ground-truth annotations, achieving 89% precision and 75% recall (for an $F1$ of 81%). The combined human and LLM annotations generate a final set of 1,565 papers.

[IMAGE: The PRISMA systematic literature review process. We accumulate 4,247 unique records from which we extract 1,565 relevant records.]

## Text-Based Techniques {#sec:taxonomical}

We now present a comprehensive taxonomical ontology of 58 text-based prompting techniques, broken into 6 major categories (Figure [2.2](#fig:taxonomy){reference-type="ref" reference="fig:taxonomy"}). Although some of the techniques might fit into multiple categories, we place them in a single category of most relevance.

<figure id="fig:taxonomy">
<div class="forest">
<p>for tree=<span> grow=east, reversed=true, anchor=base west, parent anchor=east, child anchor=west, base=left, font=, rectangle, draw=black, rounded corners, align=left, minimum width=2em, edge+=<span>darkgray, line width=1pt</span>, s sep=1pt, inner xsep=1pt, inner ysep=2pt, line width=0.8pt, ver/.append style=<span>rotate=90, child anchor=north, parent anchor=south, anchor=center</span>, text width=7em, </span>, [Text-Base Prompt. Tech. , fill=teal!50 [Zero-Shot <a href="#sec:zero-shot-prompts" data-reference-type="ref" data-reference="sec:zero-shot-prompts">[sec:zero-shot-prompts]</a>, fill=red!50 [Emotion Prompting <a href="#sec:emotional-prompting" data-reference-type="ref" data-reference="sec:emotional-prompting">[sec:emotional-prompting]</a>, fill=red!50] [Role Prompting <a href="#sec:role-prompting" data-reference-type="ref" data-reference="sec:role-prompting">[sec:role-prompting]</a>, fill=red!50] [Style Prompting <a href="#sec:style-prompting" data-reference-type="ref" data-reference="sec:style-prompting">[sec:style-prompting]</a>, fill=red!50] [S2A <a href="#sec:s2_attn" data-reference-type="ref" data-reference="sec:s2_attn">[sec:s2_attn]</a>, fill=red!50] [SimToM <a href="#sec:simtom" data-reference-type="ref" data-reference="sec:simtom">[sec:simtom]</a>, fill=red!50] [RaR <a href="#sec:rar" data-reference-type="ref" data-reference="sec:rar">[sec:rar]</a>, fill=red!50] [RE2 <a href="#sec:re2" data-reference-type="ref" data-reference="sec:re2">[sec:re2]</a>, fill=red!50] [Self-Ask <a href="#sec:self-ask" data-reference-type="ref" data-reference="sec:self-ask">[sec:self-ask]</a>, fill=red!50] ] [Few-Shot <a href="#fsp" data-reference-type="ref" data-reference="fsp">[fsp]</a>, fill=blue!50 [Exemplar Generation, fill=blue!40 [SG-ICL <a href="#sec:sg-icl" data-reference-type="ref" data-reference="sec:sg-icl">[sec:sg-icl]</a>, fill=blue!30] ] [Exemplar Ordering <a href="#sec:ex-ordering" data-reference-type="ref" data-reference="sec:ex-ordering">[sec:ex-ordering]</a>, fill=blue!40] [Exemplar Selection<br />
<a href="#sec:ex-selection" data-reference-type="ref" data-reference="sec:ex-selection">[sec:ex-selection]</a>, fill=blue!40 [KNN <a href="#sec:knn" data-reference-type="ref" data-reference="sec:knn">[sec:knn]</a>, fill=blue!30] [Vote-K <a href="#sec:v-k" data-reference-type="ref" data-reference="sec:v-k">[sec:v-k]</a>, fill=blue!30] ] [Instruction Selection <a href="#sec:fs-instructions" data-reference-type="ref" data-reference="sec:fs-instructions">[sec:fs-instructions]</a>, fill=blue!40] ] [Thought Generation <a href="#sec:thought-gen" data-reference-type="ref" data-reference="sec:thought-gen">[sec:thought-gen]</a>, fill=green!50 [Chain-of-Thought<br />
(CoT) <a href="#sec:cot" data-reference-type="ref" data-reference="sec:cot">[sec:cot]</a>, fill=green!40 [Zero-Shot CoT <a href="#sec:zsc" data-reference-type="ref" data-reference="sec:zsc">[sec:zsc]</a>, fill=green!30 [Analogical Prompting<br />
<a href="#sec:anal-prompt" data-reference-type="ref" data-reference="sec:anal-prompt">[sec:anal-prompt]</a>, fill=green!20] [Step-Back Prompting<br />
<a href="#sec:harden" data-reference-type="ref" data-reference="sec:harden">[sec:harden]</a>, fill=green!20] [Thread-of-Thought<br />
(ThoT) <a href="#sec:thot" data-reference-type="ref" data-reference="sec:thot">[sec:thot]</a>, fill=green!20] [Tab-CoT <a href="#sec:tab-cot" data-reference-type="ref" data-reference="sec:tab-cot">[sec:tab-cot]</a>, fill=green!20] ] [Few-Shot CoT <a href="#sec:fcot" data-reference-type="ref" data-reference="sec:fcot">[sec:fcot]</a>, fill=green!30 [Active-Prompt <a href="#sec:active-prompt" data-reference-type="ref" data-reference="sec:active-prompt">[sec:active-prompt]</a>, fill=green!20] [Auto-CoT <a href="#sec:automatic-cot" data-reference-type="ref" data-reference="sec:automatic-cot">[sec:automatic-cot]</a>, fill=green!20] [Complexity-Based <a href="#sec:compl-based-prompt" data-reference-type="ref" data-reference="sec:compl-based-prompt">[sec:compl-based-prompt]</a>, fill=green!20] [Contrastive <a href="#sec:contrastive-cot" data-reference-type="ref" data-reference="sec:contrastive-cot">[sec:contrastive-cot]</a>, fill=green!20] [Memory-of-Thought<br />
<a href="#sec:mot" data-reference-type="ref" data-reference="sec:mot">[sec:mot]</a>, fill=green!20] [Uncertainty-Routed<br />
CoT <a href="#sec:uncertainty-routed-cot" data-reference-type="ref" data-reference="sec:uncertainty-routed-cot">[sec:uncertainty-routed-cot]</a>, fill=green!20] [Prompt Mining <a href="#sec:mining" data-reference-type="ref" data-reference="sec:mining">[sec:mining]</a>, fill=green!20] [AutoDiCoT <a href="#autodicot" data-reference-type="ref" data-reference="autodicot">[autodicot]</a>, fill=green!20] ] ] ] [Ensembling <a href="#sec:ensembling" data-reference-type="ref" data-reference="sec:ensembling">[sec:ensembling]</a>, fill=orange!50 [COSP <a href="#cosp" data-reference-type="ref" data-reference="cosp">[cosp]</a>, fill=orange!40] [DENSE <a href="#sec:dense" data-reference-type="ref" data-reference="sec:dense">[sec:dense]</a>, fill=orange!40] [DiVeRSe <a href="#sec:diverse" data-reference-type="ref" data-reference="sec:diverse">[sec:diverse]</a>, fill=orange!40] [Max Mutual<br />
Information <a href="#sec:m-m-i-m" data-reference-type="ref" data-reference="sec:m-m-i-m">[sec:m-m-i-m]</a>, fill=orange!40] [Meta-CoT <a href="#meta-cot" data-reference-type="ref" data-reference="meta-cot">[meta-cot]</a>, fill=orange!40] [MoRE <a href="#sec:more" data-reference-type="ref" data-reference="sec:more">[sec:more]</a>, fill=orange!40] [Self-Consistency <a href="#self-consistency" data-reference-type="ref" data-reference="self-consistency">[self-consistency]</a>, fill=orange!40] [Universal<br />
Self-Consistency <a href="#universal-s-c" data-reference-type="ref" data-reference="universal-s-c">[universal-s-c]</a>, fill=orange!40] [USP <a href="#usp" data-reference-type="ref" data-reference="usp">[usp]</a>, fill=orange!40] [Prompt Paraphrasing <a href="#sec:paraphrase" data-reference-type="ref" data-reference="sec:paraphrase">[sec:paraphrase]</a>, fill=orange!40] ] [Self-Criticism <a href="#sec:self-criticism" data-reference-type="ref" data-reference="sec:self-criticism">[sec:self-criticism]</a>, fill=purple!50 [Chain-of-Verification <a href="#sec:cove" data-reference-type="ref" data-reference="sec:cove">[sec:cove]</a>, fill=purple!40] [Self-Calibration <a href="#sec:self-eval" data-reference-type="ref" data-reference="sec:self-eval">[sec:self-eval]</a>, fill=purple!40] [Self-Refine <a href="#sec:self-refine" data-reference-type="ref" data-reference="sec:self-refine">[sec:self-refine]</a>, fill=purple!40] [Self-Verification <a href="#sec:self-verification" data-reference-type="ref" data-reference="sec:self-verification">[sec:self-verification]</a>, fill=purple!40] [ReverseCoT <a href="#sec:rcot" data-reference-type="ref" data-reference="sec:rcot">[sec:rcot]</a>, fill=purple!40] [Cumulative Reason. <a href="#sec:cumulative-reasoning" data-reference-type="ref" data-reference="sec:cumulative-reasoning">[sec:cumulative-reasoning]</a>, fill=purple!40] ] [Decomposition <a href="#sec:decomposition" data-reference-type="ref" data-reference="sec:decomposition">[sec:decomposition]</a>, fill=brown!50 [DECOMP <a href="#sec:decomp" data-reference-type="ref" data-reference="sec:decomp">[sec:decomp]</a>, fill=brown!40] [Faithful CoT <a href="#sec:faithful-cot" data-reference-type="ref" data-reference="sec:faithful-cot">[sec:faithful-cot]</a>, fill=brown!40] [Least-to-Most <a href="#sec:ltm-prompting" data-reference-type="ref" data-reference="sec:ltm-prompting">[sec:ltm-prompting]</a>, fill=brown!40] [Plan-and-Solve <a href="#sec:pasp" data-reference-type="ref" data-reference="sec:pasp">[sec:pasp]</a>, fill=brown!40] [Program-of-Thought <a href="#sec:program-of-thoughts" data-reference-type="ref" data-reference="sec:program-of-thoughts">[sec:program-of-thoughts]</a>, fill=brown!40] [Recurs.-of-Thought <a href="#sec:recursion-of-thought" data-reference-type="ref" data-reference="sec:recursion-of-thought">[sec:recursion-of-thought]</a>, fill=brown!40] [Skeleton-of-Thought <a href="#sec:skeleton-of-thought" data-reference-type="ref" data-reference="sec:skeleton-of-thought">[sec:skeleton-of-thought]</a>, fill=brown!40] [Tree-of-Thought <a href="#sec:tot" data-reference-type="ref" data-reference="sec:tot">[sec:tot]</a>, fill=brown!40] [Metacognitive <a href="#sec:metacognitive" data-reference-type="ref" data-reference="sec:metacognitive">[sec:metacognitive]</a>, fill=brown!40] ] ]</p>
</div>
<figcaption>All text-based prompting techniques from our dataset.</figcaption>
</figure>

## Prompting Technique Usage

<figure id="fig:technique_citations">
<div class="minipage">
[IMAGE: models_citation_counts.pdf]
[IMAGE: graph_dataset_mentions_output.pdf]
</div>
<div class="minipage">
[IMAGE: internal_references.pdf]
</div>
<figcaption>Citation Counts of Prompting Techniques. The top 25 papers in our dataset, measured by how often they are cited by other papers in our dataset. Most papers here are prompting techniques*, and the remaining papers contains prompting advice.</figcaption>
</figure>

As we have just seen, there exist many text-based prompting techniques. However, only a small subset of them are commonly used in research and in industry. We measure technique usage by proxy of measuring the number of citations by other papers in our dataset. We do so with the presumption that papers about prompting are more likely to actually use or evaluate the cited technique. We graph the top 25 papers cited in this way from our dataset and find that most of them propose new prompting techniques (Figure [2.3](#fig:technique_citations){reference-type="ref" reference="fig:technique_citations"}). The prevalence of citations for Few-Shot and Chain-of-Thought prompting is unsurprising and helps to establish a baseline for understanding the prevalence of other techniques.

### Benchmarks

In prompting research, when researchers propose a new technique, they usually benchmark it across multiple models and datasets. This is important to prove the utility of the technique and examine how it transfers across models.

In order to make it easier for researchers proposing new techniques to know how to benchmark them, we quantitatively examine which models (Figure [\[fig:model_citations\]](#fig:model_citations){reference-type="ref" reference="fig:model_citations"}) and what benchmark datasets (Figure [\[fig:dataset_citations\]](#fig:dataset_citations){reference-type="ref" reference="fig:dataset_citations"}) are being used. Again, we measure usage by how many times papers in our dataset cite the benchmark datasets and models.

To find which datasets and models are being used, we prompted GPT-4-1106-preview to extract any mentioned dataset or model from the body of papers in our dataset. After, we manually filtered out results that were not models or datasets. The citation counts were acquired by searching items from the finalized list on Semantic Scholar.

# Beyond English Text Prompting

Prompting GenAIs with English text currently stands as the dominant method for interaction. Prompting in other languages or through different modalities often requires special techniques to achieve comparable performance. In this context, we discuss the domains of multilingual and multimodal prompting.

<figure id="fig:multilingualtaxonomy" data-latex-placement="tbph!">
<div class="forest">
<p>for tree=<span> grow=east, reversed=true, anchor=base west, parent anchor=east, child anchor=west, base=left, font=, rectangle, draw=black, rounded corners, align=left, minimum width=2em, edge+=<span>darkgray, line width=1pt</span>, s sep=1pt, inner xsep=1pt, inner ysep=2pt, line width=0.8pt, ver/.append style=<span>rotate=90, child anchor=north, parent anchor=south, anchor=center</span>, text width=7em, </span>, [Multilingual Techniques, fill=teal!50 [Chain-of-Thought <a href="#sec:cot-ml" data-reference-type="ref" data-reference="sec:cot-ml">3.1.1</a>, fill=red!50 [XLT <a href="#sec:xlt-ml" data-reference-type="ref" data-reference="sec:xlt-ml">[sec:xlt-ml]</a>, fill=red!40] [CLSP <a href="#sec:clsp-ml" data-reference-type="ref" data-reference="sec:clsp-ml">[sec:clsp-ml]</a>, fill=red!40]] [In-Context Learning <a href="#sec:icl-ml" data-reference-type="ref" data-reference="sec:icl-ml">3.1.2</a>, fill=green!50 [X-InSTA <a href="#sec:xinsta-ml" data-reference-type="ref" data-reference="sec:xinsta-ml">[sec:xinsta-ml]</a>, fill=green!40] [In-CLT <a href="#sec:inclt-ml" data-reference-type="ref" data-reference="sec:inclt-ml">[sec:inclt-ml]</a>, fill=green!40] ] [In-Context Ex. Selection <a href="#sec:ices-ml" data-reference-type="ref" data-reference="sec:ices-ml">3.1.2.1</a>, fill=green!50 [PARC <a href="#sec:parc" data-reference-type="ref" data-reference="sec:parc">3.1.2.1.1</a>, fill=green!40] [Semantically-Aligned <a href="#sec:ices-ml" data-reference-type="ref" data-reference="sec:ices-ml">3.1.2.1</a>, fill=green!40] [Semantically-Distant <a href="#sec:ices-ml" data-reference-type="ref" data-reference="sec:ices-ml">3.1.2.1</a>, fill=green!40] ] [Human-in-the-Loop <a href="#sec:hitl-ml" data-reference-type="ref" data-reference="sec:hitl-ml">3.1.4.1</a>, fill=blue!50 [Interactive Chain <a href="#sec:icp-ml" data-reference-type="ref" data-reference="sec:icp-ml">3.1.4.1.1</a>, fill=blue!40] [Iterative <a href="#sec:interprompt-ml" data-reference-type="ref" data-reference="sec:interprompt-ml">3.1.4.1.2</a>, fill=blue!40] ] [Translation <a href="#sec:prompting_for_mt" data-reference-type="ref" data-reference="sec:prompting_for_mt">3.1.4</a>, fill=orange!50 [Chain-of-Dictionary <a href="#sec:cod-ml" data-reference-type="ref" data-reference="sec:cod-ml">[sec:cod-ml]</a>, fill=orange!40] [DecoMT <a href="#sec:deco-mt" data-reference-type="ref" data-reference="sec:deco-mt">3.1.4.0.4</a>, fill=orange!40] [DiPMT <a href="#sec:dipmt-ml" data-reference-type="ref" data-reference="sec:dipmt-ml">3.1.4.0.3</a>, fill=orange!40] [MAPS <a href="#sec:maps-ml" data-reference-type="ref" data-reference="sec:maps-ml">3.1.4.0.1</a>, fill=orange!40] ] [Translate First Prompting <a href="#sec:tfp-ml" data-reference-type="ref" data-reference="sec:tfp-ml">[sec:tfp-ml]</a>, fill=violet!50 [External MT Systems <a href="#sec:tfp-ml" data-reference-type="ref" data-reference="sec:tfp-ml">[sec:tfp-ml]</a>, fill=violet!40] [Standard LLMs <a href="#sec:tfp-ml" data-reference-type="ref" data-reference="sec:tfp-ml">[sec:tfp-ml]</a>, fill=violet!40] [Multilingual LLMs <a href="#sec:tfp-ml" data-reference-type="ref" data-reference="sec:tfp-ml">[sec:tfp-ml]</a>, fill=violet!40] ] [Prompt Language <a href="#sec:prompt-language" data-reference-type="ref" data-reference="sec:prompt-language">3.1.3</a>, fill=brown!50 [English <a href="#sec:english-prompt-language" data-reference-type="ref" data-reference="sec:english-prompt-language">3.1.3.0.1</a>, fill=brown!40] [Task Language <a href="#sec:task-language" data-reference-type="ref" data-reference="sec:task-language">3.1.3.0.2</a>, fill=brown!40] ] ]</p>
</div>
<figcaption>All multilingual prompting techniques.</figcaption>
</figure>

## Multilingual {#Multilingual}

[]{#sec:multilingual label="sec:multilingual"}

State-of-the-art GenAIs have often been predominately trained with English dataset, leading to a notable disparity in the output quality in languages other than English, particularly low-resource languages [bang2023multitask; @jiao2023chatgpt; @Hendy2023HowGA; @shi2022language]. As a result, various multilingual prompting techniques have emerged in an attempt to improve model performance in non-English settings (Figure [3.1](#fig:multilingualtaxonomy){reference-type="ref" reference="fig:multilingualtaxonomy"}).

[]{#Multilingual prompting label="Multilingual prompting"}

##### Translate First Prompting

[shi2022language] []{#sec:tfp-ml label="sec:tfp-ml"} is perhaps the simplest strategy and first translates non-English input examples into English. By translating the inputs into English, the model can utilize its strengths in English to better understand the content. Translation tools vary; @shi2022language use an external MT system, @etxaniz2023multilingual prompt multilingual LMs and @awasthi-etal-2023-bootstrapping prompt LLMs to translate non-English inputs.

### Chain-of-Thought (CoT) {#sec:cot-ml}

CoT prompting [wei2023chainofthought] has been extended to the multilingual setting in multiple ways.

##### XLT (Cross-Lingual Thought) Prompting

[huang2023languages] []{#sec:xlt-ml label="sec:xlt-ml"} utilizes a prompt template composed of six separate instructions, including role assignment, cross-lingual thinking, and CoT.

##### Cross-Lingual Self Consistent Prompting (CLSP)

[qin2023crosslingual] []{#sec:clsp-ml label="sec:clsp-ml"} introduces an ensemble technique that constructs reasoning paths in different languages to answer the same question.

### In-Context Learning {#sec:icl-ml}

ICL has also been extended to multilingual settings in multiple ways.

##### X-InSTA Prompting

[tanwar-etal-2023-multilingual] []{#sec:xinsta-ml label="sec:xinsta-ml"} explores three distinct approaches for aligning in-context examples with the input sentence for classification tasks: using semantically similar examples to the input (semantic alignment), examples that share the same label as the input (task-based alignment), and the combination of both semantic and task-based alignments.

##### In-CLT (Cross-lingual Transfer) Prompting

[kim2023boosting] []{#sec:inclt-ml label="sec:inclt-ml"} leverages both the source and target languages to create in-context examples, diverging from the traditional method of using source language exemplars. This strategy helps stimulate the cross-lingual cognitive capabilities of multilingual LLMs, thus boosting performance on cross-lingual tasks.

#### In-Context Example Selection {#sec:ices-ml}

In-context example selection heavily influences the multilingual performance of LLMs [garcia2023unreasonable; @agrawal-etal-2023-context]. Finding in-context examples that are semantically similar to the source text is very important [winata2023multilingual; @moslem-etal-2023-adaptive; @sia2023incontext]. However, using semantically dissimilar (*peculiar*) exemplars has also been shown to enhance performance [kim-komachi-2023-enhancing]. This same contrast exists in the English-only setting. Additionally, when dealing with ambiguous sentences, selecting exemplars with polysemous or rare word senses may boost performance [iyer2023effective].

##### PARC (Prompts Augmented by Retrieval Cross-lingually) {#sec:parc}

[nie-etal-2023-cross] introduce a framework that retrieves relevant exemplars from a high resource language. This framework is specifically designed to enhance cross-lingual transfer performance, particularly for low-resource target languages. @li2023crosslingual extend this work to Bangla.

### Prompt Template Language Selection {#sec:prompt-language}

In multilingual prompting, the selection of language for the prompt template can markedly influence the model performance.

##### English Prompt Template {#sec:english-prompt-language}

Constructing the prompt template in English is often more effective than in the task language for multilingual tasks. This is likely due to the predominance of English data during LLM pre-training [lin-etal-2022-shot; @ahuja2023mega]. @lin-etal-2022-shot suggest that this is likely due to a high overlap with pre-training data and vocabulary. Similarly, @ahuja2023mega highlight how translation errors when creating task language templates propagate in the form of incorrect syntax and semantics, adversely affecting task performance. Further, @fu-etal-2022-polyglot compare in-lingual (task language) prompts and cross-lingual (mixed language) prompts and find the cross-lingual approach to be more effective, likely because it uses more English in the prompt, thus facilitating retrieving knowledge from the model.

##### Task Language Prompt Template {#sec:task-language}

In contrast, many multilingual prompting benchmarks such as BUFFET [asai2023buffet] or LongBench [bai2023longbench] use task language prompts for language-specific use cases. @muennighoff-etal-2023-crosslingual specifically studies different translation methods when constructing native-language prompts. They demonstrate that human translated prompts are superior to their machine-translated counterparts. Native or non-native template performance can differ across tasks and models [li2023bilingual]. As such, neither option will always be the best approach [nambi2023breaking].

### Prompting for Machine Translation {#sec:prompting_for_mt}

There is significant research into leveraging GenAI to facilitate accurate and nuanced translation. Although this is a specific application of prompting, many of these techniques are important more broadly for multilingual prompting.

##### Multi-Aspect Prompting and Selection (MAPS) {#sec:maps-ml}

[he2023exploring] mimics the human translation process, which involves multiple preparatory steps to ensure high-quality output. This framework starts with knowledge mining from the source sentence (extracting keywords and topics, and generating translation exemplars). It integrates this knowledge to generate multiple possible translations, then selects the best one.

##### Chain-of-Dictionary (CoD)

[lu2023chainofdictionary] []{#sec:cod-ml label="sec:cod-ml"} first extracts words from the source phrase, then makes a list of their meanings in multiple languages, automatically via retrieval from a dictionary (e.g. English: '*apple*', Spanish: '*manzana*'). Then, they prepend these dictionary phrases to the prompt, where it asks a GenAI to use them during translation.

##### Dictionary-based Prompting for Machine Translation (DiPMT) {#sec:dipmt-ml}

[ghazvininejad2023dictionarybased] works similarly to CoD, but only gives definitions in the source and target languages, and formats them slightly differently.

##### Decomposed Prompting for MT (DecoMT) {#sec:deco-mt}

[puduppully2023decomposed] divides the source text into several chunks and translates them independently using few-shot prompting. Then it uses these translations and contextual information between chunks to generate a final translation.

#### Human-in-the-Loop {#sec:hitl-ml}

##### Interactive-Chain-Prompting (ICP) {#sec:icp-ml}

[pilault2023interactivechainprompting] deals with potential ambiguities in translation by first asking the GenAI to generate sub-questions about any ambiguities in the phrase to be translated. Humans later respond to these questions and the system includes this information to generate a final translation.

##### Iterative Prompting {#sec:interprompt-ml}

[yang-etal-2023-hilmt] also involves humans during translation. First, they prompt LLMs to create a draft translation. This initial version is further refined by integrating supervision signals obtained from either automated retrieval systems or direct human feedback.

<figure id="fig:multimodaltaxonomy" data-latex-placement="tbph!">
<div class="forest">
<p>for tree=<span> grow=east, reversed=true, anchor=base west, parent anchor=east, child anchor=west, base=left, font=, rectangle, draw=black, rounded corners, align=left, minimum width=2em, edge+=<span>darkgray, line width=1pt</span>, s sep=1pt, inner xsep=1pt, inner ysep=2pt, line width=0.8pt, ver/.append style=<span>rotate=90, child anchor=north, parent anchor=south, anchor=center</span>, text width=7em, </span>, [Multimodal (MM) Techniques, fill=teal!50 [Image <a href="#sec:image-mm" data-reference-type="ref" data-reference="sec:image-mm">3.2.1</a>, fill=red!50 [MM. CoT <a href="#sec:cot-mm" data-reference-type="ref" data-reference="sec:cot-mm">3.2.1.2</a>, fill=red!40 [Chain-of-Images <a href="#sec:coi-mm" data-reference-type="ref" data-reference="sec:coi-mm">3.2.1.2.3</a>, fill=red!30] [Duty Distinct CoT <a href="#sec:ddcot-mm" data-reference-type="ref" data-reference="sec:ddcot-mm">[sec:ddcot-mm]</a>, fill=red!30] [MM Graph-of-Thought <a href="#sec:got-mm" data-reference-type="ref" data-reference="sec:got-mm">3.2.1.2.2</a>, fill=red!30] ] [Multimodal ICL <a href="#sec:icl-mm" data-reference-type="ref" data-reference="sec:icl-mm">3.2.1.1</a>, fill=red!40 [Image-as-Text Prompt<a href="#sec:iat-mm" data-reference-type="ref" data-reference="sec:iat-mm">3.2.1.1.2</a>, fill=red!30] [Paired-Image Prompt <a href="#sec:pim-mm" data-reference-type="ref" data-reference="sec:pim-mm">3.2.1.1.1</a>, fill=red!30] ] [Negative Prompt <a href="#sec:neg-mm" data-reference-type="ref" data-reference="sec:neg-mm">3.2.1.0.2</a>, fill=red!40] [Prompt Modifiers <a href="#sec:pm-mm" data-reference-type="ref" data-reference="sec:pm-mm">3.2.1.0.1</a>, fill=red!40] ] [Segmentation Prompting <a href="#sec:segmentation-prompting" data-reference-type="ref" data-reference="sec:segmentation-prompting">3.2.4</a>, fill=blue!50] [Video <a href="#sec:video-mm" data-reference-type="ref" data-reference="sec:video-mm">3.2.3</a>, fill=green!50 [Video Gen. <a href="#sec:vgen-mm" data-reference-type="ref" data-reference="sec:vgen-mm">3.2.3.1</a>, fill=green!40 ] ] [3D Prompting <a href="#sec:3d-prompting" data-reference-type="ref" data-reference="sec:3d-prompting">3.2.5</a>, fill=orange!50] ]</p>
</div>
<figcaption>All multimodal prompting techniques.</figcaption>
</figure>

## Multimodal {#sec:multimodal}

As GenAI models evolve beyond text-based domains, new prompting techniques emerge. These multimodal prompting techniques are often not simply applications of text-based prompting techniques, but entirely novel ideas made possible by different modalities. We now extend our text-based taxonomy to include a mixture of multimodal analogs of text-based prompting techniques as well as completely novel multimodal techniques (Figure [3.2](#fig:multimodaltaxonomy){reference-type="ref" reference="fig:multimodaltaxonomy"}).

### Image Prompting {#sec:image-mm}

The image modality encompasses data such as photographs, drawings, or even screenshots of text [gong2023figstep]. Image prompting may refer to prompts that either contain images or are used to generate images. Common tasks include image generation [ding2021cogview; @Hinz_2022; @tao2022dfgan; @li2019controllable; @li2019objectdriven; @rombach2022highresolution], caption generation [li2020oscar], image classification [khalil2023comprehensive], and image editing [crowson2022vqganclip; @kwon2022clipstyler; @bartal2022text2live; @hertz2022prompttoprompt]. We now describe various image prompting techniques used for such applications.

##### Prompt Modifiers {#sec:pm-mm}

are simply words appended to a prompt to change the resultant image [oppenlaender2023taxonomy]. Components such as Medium (e.g. \"on canvas\") or Lighting (e.g. \"a well lit scene\") are often used.

##### Negative Prompting {#sec:neg-mm}

allows users to numerically weight certain terms in the prompt so that the model considers them more/less heavily than others. For example, by negatively weighting the terms "bad hands" and "extra digits", models may be more likely to generate anatomically accurate hands [Schulhoff_Learn_Prompting_2022].

#### Multimodal In-Context Learning {#sec:icl-mm}

The success of ICL in text-based settings has prompted research into multimodal ICL [wang2023incontext; @dong2023survey].

##### Paired-Image Prompting {#sec:pim-mm}

shows the model two images: one before and one after some transformation. Then, present the model with a new image for which it will perform the demonstrated conversion. This can be done either with textual instructions [wang2023incontext] or without them [liu2023unifying].

##### Image-as-Text Prompting {#sec:iat-mm}

[hakimov2023images] generates a textual description of an image. This allows for the easy inclusion of the image (or multiple images) in a text-based prompt.

#### Multimodal Chain-of-Thought {#sec:cot-mm}

CoT has been extended to the image domain in various ways [zhang2023multimodal; @huang2023language; @zheng2023ddcot; @yao2023chainofthought]. A simple example of this would be a prompt containing an image of a math problem accompanied by the textual instructions \"Solve this step by step\".

##### Duty Distinct Chain-of-Thought (DDCoT)

[zheng2023ddcot] []{#sec:ddcot-mm label="sec:ddcot-mm"} extends Least-to-Most prompting [zhou2022least] to the multimodal setting, creating subquestions, then solving them and combining the answers into a final response.

##### Multimodal Graph-of-Thought {#sec:got-mm}

[yao2023chainofthought] extends Graph-of-Thought @zhang2023multimodal to the multimodal setting. GoT-Input also uses a two step rationale then answer process. At inference time, the the input prompt is used to construct a thought graph, which is then used along with the original prompt to generate a rationale to answer the question. When an image is input along with the question, an image captioning model is employed to generate a textual description of the image, which is then appended to the prompt before the thought graph construction to provide visual context.

##### Chain-of-Images (CoI) {#sec:coi-mm}

[meng2023chain] is a multimodal extension of Chain-of-Thought prompting, that generates images as part of its thought process. They use the prompt "Let's think image by image" to generate SVGs, which the model can then use to reason visually.

### Audio Prompting

Prompting has also been extended to the audio modality. Experiments with audio ICL have generated mixed results, with some open source audio models failing to perform ICL [hsu2023exploration]. However, other results do show an ICL ability in audio models [wang2023whisper; @peng2023prompting; @chang2023incontext]. Audio prompting is currently in early stages, but we expect to see various prompting techniques proposed in the future.

### Video Prompting {#sec:video-mm}

Prompting has also been extended to the video modality, for use in text-to-video generation [videoworldsimulators2024; @lv2023gpt4motion; @liang2023movideo; @girdhar2023emu], video editing [zuo2023cutandpaste; @wu2023tuneavideo; @Cheng2023ConsistentVT], and video-to-text generation [yousaf2023videoprompter; @mi2023clifvqa; @ko2023language].

#### Video Generation Techniques {#sec:vgen-mm}

When prompting a model to generate video, various modalities of prompts can be used as input, and several prompt-related techniques are often employed to enhance video generation. Image related techniques, such as prompt modifiers can often be used for video generation [runwayGen-2].

### Segmentation Prompting {#sec:segmentation-prompting}

Prompting can also be used for segmentation (e.g. semantic segmentation) [tang2023trainingfree; @Liu_2023].

### 3D Prompting {#sec:3d-prompting}

Prompting can also be used in 3D modalities, for example in 3D object synthesis [feng2023metadreamer; @li2023instant3d; @jli2023instant3d; @lin2023magic3d; @chen2023control3d; @lorraine2023att3d; @poole2022dreamfusion; @jain2022zeroshot], 3D surface texturing [liu2023textguided; @yang20233dstylediffusion; @le2023euclidreamer; @pajouheshgar2023mesh], and 4D scene generation (animating a 3D scene) [singer2023textto4d; @zhao2023animate124], where input prompt modalities include text, image, user annotation (bounding boxes, points, lines), and 3D objects.

# Extensions of Prompting

The techniques we have discussed thus far can be extremely complicated, incorporating many steps and iterations. However, we can take prompting further by adding access to external tools (agents) and complex evaluation algorithms to judge the validity of LLM outputs.

<figure id="fig:agenttaxonomy" data-latex-placement="tbph!">
<div class="forest">
<p>for tree=<span> grow=east, reversed=true, anchor=base west, parent anchor=east, child anchor=west, base=left, font=, rectangle, draw=black, rounded corners, align=left, minimum width=2em, edge+=<span>darkgray, line width=1pt</span>, s sep=1pt, inner xsep=1pt, inner ysep=2pt, line width=0.8pt, ver/.append style=<span>rotate=90, child anchor=north, parent anchor=south, anchor=center</span>, text width=7em, </span>, [Agents, fill=teal!50 [Tool Use Agents, fill=red!40 [CRITIC <a href="#sec:critic-ag" data-reference-type="ref" data-reference="sec:critic-ag">4.1.1.0.2</a>, fill=red!40] [MRKL Sys. <a href="#sec:mrkl-ag" data-reference-type="ref" data-reference="sec:mrkl-ag">4.1.1.0.1</a>, fill=red!40] ] [Code-Based Agents <a href="#sec:cba-ag" data-reference-type="ref" data-reference="sec:cba-ag">4.1.2</a>, fill=blue!50 [PAL <a href="#sec:pal-ag" data-reference-type="ref" data-reference="sec:pal-ag">4.1.2.0.1</a>, fill=blue!40] [ToRA <a href="#sec:tora-ag" data-reference-type="ref" data-reference="sec:tora-ag">4.1.2.0.2</a>, fill=blue!40] [Task Weaver <a href="#sec:task-ag" data-reference-type="ref" data-reference="sec:task-ag">4.1.2.0.3</a>, fill=blue!40] ] [Observation-Based Agents <a href="#sec:oba-ag" data-reference-type="ref" data-reference="sec:oba-ag">4.1.3</a>, fill=green!50 [ReAct <a href="#sec:react-ag" data-reference-type="ref" data-reference="sec:react-ag">4.1.3.0.1</a>, fill=green!40] [Reflexion <a href="#sec:ref-ag" data-reference-type="ref" data-reference="sec:ref-ag">4.1.3.0.2</a>, fill=green!40] [Lifelong Learn. Agents <a href="#sec:lla-ag" data-reference-type="ref" data-reference="sec:lla-ag">4.1.3.1</a>, fill=green!30 [Voyager <a href="#sec:voy-ag" data-reference-type="ref" data-reference="sec:voy-ag">4.1.3.1.1</a>, fill=green!20] [GITM <a href="#sec:gitm-ag" data-reference-type="ref" data-reference="sec:gitm-ag">4.1.3.1.2</a>, fill=green!20] ] ] [Retrieval Aug. Generation <a href="#sec:rag-ag" data-reference-type="ref" data-reference="sec:rag-ag">4.1.4</a>, fill=purple!50 [IRCoT <a href="#sec:ircot-ag" data-reference-type="ref" data-reference="sec:ircot-ag">4.1.4.0.3</a>, fill=purple!40] [DSP <a href="#sec:dsp-ag" data-reference-type="ref" data-reference="sec:dsp-ag">4.1.4.0.2</a>, fill=purple!40] [Verify-and-Edit <a href="#sec:vae-ag" data-reference-type="ref" data-reference="sec:vae-ag">4.1.4.0.1</a> , fill=purple!40] [Iterative Retrieval Aug. <a href="#sec:ira-ag" data-reference-type="ref" data-reference="sec:ira-ag">4.1.4.0.4</a> , fill=purple!40] ] ]</p>
</div>
<figcaption>Agent techniques covered in this section.</figcaption>
</figure>

## Agents {#sec:agents}

As LLMs have improved rapidly in capabilities [zhang2023igniting], companies [adept-act1] and researchers [karpas2022mrkl] have explored how to allow them to make use of external systems. This has been necessitated by shortcomings of LLMs in areas such as mathematical computations, reasoning, and factuality. This has driven significant innovations in prompting techniques; these systems are often driven by prompts and prompt chains, which are heavily engineered to allow for agent-like behaviour (Figure [4.1](#fig:agenttaxonomy){reference-type="ref" reference="fig:agenttaxonomy"}).

##### Definition of Agent

In the context of GenAI, we define agents to be GenAI systems that serve a user's goals via actions that engage with systems outside the GenAI itself.[^3] This GenAI is usually a LLM. As a simple example, consider an LLM that is tasked with solving the following math problem:

::: pbox
If Annie has 4,939 grapes, and gives exactly 39% of them to Amy, how many does she have left?
:::

If properly prompted, the LLM could output the string CALC(4,939\*.39). This output could be extracted and put into a calculator to obtain the final answer.

This is an example of an agent: the LLM outputs text which then uses a downstream tool. Agent LLMs may involve a single external system (as above), or they may need to solve the problem of *routing*, to choose which external system to use. Such systems also frequently involve memory and planning in addition to actions [zhang2023igniting].

Examples of agents include LLMs that can make API calls to use external tools like a calculator [karpas2022mrkl], LLMs that can output strings that cause actions to be taken in a gym-like [brockman2016gym; @towers_gymnasium_2023] environment [yao2022react], and more broadly, LLMs which write and record plans, write and run code, search the internet, and more [Significant_Gravitas_AutoGPT; @yang2023autogpt; @Osika_gpt-engineer_2023]. OpenAI Assistants @OpenAI_2023_How, LangChain Agents [Chase_LangChain_2022], and LlamaIndex Agents [Liu_LlamaIndex_2022] are additional examples.

### Tool Use Agents {#sec:tua-ag}

Tool use is a critical component for GenAI agents. Both symbolic (e.g. calculator, code interpreter) and neural (e.g. a separate LLM) external tools are commonly used. Tools may occasionally be referred to as experts [karpas2022mrkl] or modules.

##### Modular Reasoning, Knowledge, and Language (MRKL) System {#sec:mrkl-ag}

[karpas2022mrkl] is one of the simplest formulations of an agent. It contains a LLM router providing access to multiple tools. The router can make multiple calls to get information such as weather or the current date. It then combines this information to generate a final response. Toolformer [schick2023toolformer], Gorilla [Patil2023GorillaLL], Act-1 [adept-act1], and others [Shen2023HuggingGPTSA; @Qin2023ToolLW; @Hao2023ToolkenGPTAF] all propose similar techniques, most of which involve some fine-tuning.

##### Self-Correcting with Tool-Interactive Critiquing (CRITIC) {#sec:critic-ag}

[gou2023critic] first generates a response to the prompt, with no external calls. Then, the same LLM criticizes this response for possible errors. Finally, it uses tools (e.g. Internet search or a code interpreter) accordingly to verify or amend parts of the response.

### Code-Generation Agents {#sec:cba-ag}

Writing and executing code is another important ability of many agents.[^4]

##### Program-aided Language Model (PAL) {#sec:pal-ag}

[gao2022pal] translates a problem directly into code, which is sent to a Python interpreter to generate an answer.

##### Tool-Integrated Reasoning Agent (ToRA) {#sec:tora-ag}

[gou2023tora] is similar to PAL, but instead of a single code generation step, it interleaves code and reasoning steps for as long as necessary to solve the problem.

##### TaskWeaver {#sec:task-ag}

[Qiao2023TaskWeaverAC] is also similar to PAL, transforming user requests into code, but can also make use of user-defined plugin.

### Observation-Based Agents {#sec:oba-ag}

Some agents are designed to solve problems by interacting with toy environments [brockman2016gym; @towers_gymnasium_2023]. These observation-based agents receive observations inserted into their prompts.

##### Reasoning and Acting (ReAct) {#sec:react-ag}

(@yao2022react) generates a thought, takes an action, and receives an observation (and repeats this process) when given a problem to solve. All of this information is inserted into the prompt so it has a memory of past thoughts, actions, and observations.

##### Reflexion {#sec:ref-ag}

[shinn2023reflexion] builds on ReAct, adding a layer of introspection. It obtains a trajectory of actions and observations, then is given an evaluation of success/failure. Then, it generates a reflection on what it did and what went wrong. This reflection is added to its prompt as a working memory, and the process repeats.

#### Lifelong Learning Agents {#sec:lla-ag}

Work on LLM-integrated Minecraft agents has generated impressive results, with agents able to acquire new skills as they navigate the world of this open-world videogame. We view these agents not merely as applications of agent techniques to Minecraft, but rather novel agent frameworks which can be explored in real world tasks that require lifelong learning.

##### Voyager {#sec:voy-ag}

[wang2023voyager] is composed of three parts. First, it proposes tasks for itself to complete in order to learn more about the world. Second, it generates code to execute these actions. Finally, it saves these actions to be retrieved later when useful, as part of a long-term memory system. This system could be applied to real world tasks where an agent needs to explore and interact with a tool or website (e.g. penetration testing, usability testing).

##### Ghost in the Minecraft (GITM) {#sec:gitm-ag}

[zhu2023ghost] starts with an arbitrary goal, breaks it down into subgoals recursively, then iteratively plans and executes actions by producing structured text (e.g. \"equip(sword)\") rather than writing code. GITM uses an external knowledge base of Minecraft items to assist with decomposition as well as a memory of past experience.

### Retrieval Augmented Generation (RAG) {#sec:rag-ag}

In the context of GenAI agents, RAG is a paradigm in which information is retrieved from an external source and inserted into the prompt. This can enhance performance in knowledge intensive tasks [lewis2021retrievalaugmented]. When retrieval itself is used as an external tool, RAG systems are considered to be agents.

##### Verify-and-Edit {#sec:vae-ag}

[zhao-etal-2023-verify] improves on self-consistency by generating multiple chains-of-thought, then selecting some to be edited. They do this by retrieving relevant (external) information to the CoTs, and allowing the LLM to augment them accordingly.

##### Demonstrate-Search-Predict {#sec:dsp-ag}

[khattab2022demonstratesearchpredict] first decomposes a question into sub-questions, then uses queries to solve them and combine their responses in a final answer. It uses few-shot prompting to decompose the problem and combine responses.

##### Interleaved Retrieval guided by Chain-of-Thought (IRCoT) {#sec:ircot-ag}

[trivedi-etal-2023-interleaving] is a technique for multi-hop question answering that interleaves CoT and retrieval. IRCoT leverages CoT to guide which documents to retrieve and retrieval to help plan the reasoning steps of CoT.

##### Iterative Retrieval Augmentation {#sec:ira-ag}

techniques, like Forward-Looking Active REtrieval augmented generation (FLARE) [jiang-etal-2023-active] and Imitate, Retrieve, Paraphrase (IRP) [balepur-etal-2023-expository], perform retrieval multiple times during long-form generation. Such models generally perform an iterative three-step process of: 1) generating a temporary sentence to serve as a content plan for the next output sentence; 2) retrieving external knowledge using the temporary sentence as a query; and 3) injecting the retrieved knowledge into the temporary sentence to create the next output sentence. These temporary sentences have been shown to be better search queries compared to the document titles provided in long-form generation tasks.

<figure id="fig:evaltaxonomy" data-latex-placement="tbph!">
<div class="forest">
<p>for tree=<span> grow=east, reversed=true, anchor=base west, parent anchor=east, child anchor=west, base=left, font=, rectangle, draw=black, rounded corners, align=left, minimum width=2em, edge+=<span>darkgray, line width=1pt</span>, s sep=1pt, inner xsep=1pt, inner ysep=2pt, line width=0.8pt, ver/.append style=<span>rotate=90, child anchor=north, parent anchor=south, anchor=center</span>, text width=7em, </span>, [Evaluation, fill=teal!50 [Prompting Techniques <a href="#sec:pt-eval" data-reference-type="ref" data-reference="sec:pt-eval">4.2.1</a>, fill=red!50 [Chain-Of-Thought <a href="#sec:cot-eval" data-reference-type="ref" data-reference="sec:cot-eval">4.2.1.0.3</a>, fill=red!40] [In-Context Learning <a href="#sec:icl-eval" data-reference-type="ref" data-reference="sec:icl-eval">4.2.1.0.1</a>, fill=red!40] [Model-Gen. Guidelines <a href="#sec:mgg-eval" data-reference-type="ref" data-reference="sec:mgg-eval">4.2.1.0.4</a>, fill=red!40] [Role-Based Evaluation <a href="#sec:rbe-eval" data-reference-type="ref" data-reference="sec:rbe-eval">4.2.1.0.2</a>, fill=red!40] ] [Output Format, fill=blue!50 [Binary Score <a href="#sec:bs-eval" data-reference-type="ref" data-reference="sec:bs-eval">4.2.2.0.3</a>, fill=blue!40] [Likert Scale <a href="#sec:likert-eval" data-reference-type="ref" data-reference="sec:likert-eval">4.2.2.0.4</a>, fill=blue!40] [Linear Scale <a href="#sec:ls-eval" data-reference-type="ref" data-reference="sec:ls-eval">4.2.2.0.2</a>, fill=blue!40] [Styling <a href="#sec:styling-eval" data-reference-type="ref" data-reference="sec:styling-eval">4.2.2.0.1</a>, fill=blue!40] ] [Prompting Frameworks <a href="#sec:pf-eval" data-reference-type="ref" data-reference="sec:pf-eval">4.2.3</a>, fill=green!50 [LLM-EVAL <a href="#sec:llm-eval" data-reference-type="ref" data-reference="sec:llm-eval">4.2.3.0.1</a>, fill=green!40] [G-EVAL <a href="#sec:g-eval" data-reference-type="ref" data-reference="sec:g-eval">4.2.3.0.2</a>, fill=green!40] [ChatEval <a href="#sec:chat-eval" data-reference-type="ref" data-reference="sec:chat-eval">4.2.3.0.3</a>, fill=green!40] ] [Other Methodologies <a href="#sec:om-eval" data-reference-type="ref" data-reference="sec:om-eval">4.2.4</a>, fill=violet!50 [Batch Prompting <a href="#sec:bp-eval" data-reference-type="ref" data-reference="sec:bp-eval">4.2.4.0.1</a>, fill=violet!50] [Pairwise Evaluation <a href="#sec:pair-eval" data-reference-type="ref" data-reference="sec:pair-eval">4.2.4.0.2</a>, fill=violet!50] ] ]</p>
</div>
<figcaption>Evaluation techniques.</figcaption>
</figure>

## Evaluation {#sec:evaluation}

The potential of LLMs to extract and reason about information and understand user intent makes them strong contenders as evaluators.[^5] For example, it is possible to prompt a LLM to evaluate the quality of an essay or even a previous LLM output according to some metrics defined in the prompt. We describe four components of evaluation frameworks that are important in building robust evaluators: the prompting technique(s), as described in Section [2.2](#sec:taxonomical){reference-type="ref" reference="sec:taxonomical"}, the output format of the evaluation, the framework of the evaluation pipeline, and some other methodological design decisions (Figure [4.2](#fig:evaltaxonomy){reference-type="ref" reference="fig:evaltaxonomy"}).

### Prompting Techniques {#sec:pt-eval}

The prompting technique used in the evaluator prompt (e.g. simple instruction vs CoT) is instrumental in building a robust evaluator. Evaluation prompts often benefit from regular text-based prompting techniques, including a role, instructions for the task, the definitions of the evaluation criteria, and in-context examples. Find a full list of techniques in Appendix [9.6](#appx:evaluation){reference-type="ref" reference="appx:evaluation"}.

##### In-Context Learning {#sec:icl-eval}

is frequently used in evaluation prompts, much in the same way it is used in other applications [dubois2023alpacafarm; @kocmi2023gemba; @brown2020language].

##### Role-based Evaluation {#sec:rbe-eval}

is a useful technique for improving and diversifying evaluations [wu2023large; @chan2023chateval]. By creating prompts with the same instructions for evaluation, but different roles, it is possible to effectively generate diverse evaluations. Additionally, roles can be used in a multiagent setting where LLMs debate the validity of the text to be evaluated [chan2023chateval].

##### Chain-of-Thought {#sec:cot-eval}

prompting can further improve evaluation performance [lu2023error; @fernandes2023devil].

##### Model-Generated Guidelines {#sec:mgg-eval}

[liu2023gpteval; @liu2023calibrating] prompt an LLM to generate guidelines for evaluation. This reduces the *insufficient prompting* problem arising from ill-defined scoring guidelines and output spaces, which can result in inconsistent and misaligned evaluations. @liu2023gpteval generate a chain-of-thought of the detailed evaluation steps that the model should perform before generating a quality assessment. @liu2023calibrating propose [AutoCalibrate]{.smallcaps}, which derives scoring criteria based on expert human annotations and uses a refined subset of model-generated criteria as a part of the evaluation prompt.

### Output Format {#sec:output-eval}

The output format of the LLM can significantly affect evaluation performance @gao2023human.

##### Styling {#sec:styling-eval}

Formatting the LLM's response using XML or JSON styling has also been shown to improve the accuracy of the judgment generated by the evaluator [hada2023large; @lin2023llm; @dubois2023alpacafarm].

##### Linear Scale {#sec:ls-eval}

A very simple output format is a linear scale (e.g. 1-5). Many works use ratings of 1-10 [chan2023chateval], 1-5 [araujo2023comparing], or even 0-1 [liu2023evaluate]. The model can be prompted to output a discrete [chan2023chateval] or continuous [liu2023evaluate] score between the bounds.

::: pbox
Score the following story on a scale of 1-5 from well to poorly written:  \
{INPUT}
:::

##### Binary Score {#sec:bs-eval}

Prompting the model to generate binary responses like Yes or No [chen2023evaluating] and True or False [zhao2023large] is another frequently used output format.

::: pbox
Is the following story well written at a high-school level (yes/no)?:  \
{INPUT}
:::

##### Likert Scale {#sec:likert-eval}

Prompting the GenAI to make use of a Likert Scale [bai2023benchmarking; @lin2023llm; @peskoff2023gpt] can give it a better understanding of the meaning of the scale.

::: pbox
Score the following story according to the following scale:\
Poor\
Acceptable\
Good\
Very Good\
Incredible\
 {INPUT}
:::

### Prompting Frameworks {#sec:pf-eval}

##### LLM-EVAL {#sec:llm-eval}

[lin2023llm] is one of the simplest evaluation frameworks. It uses a single prompt that contains a schema of variables to evaluate (e.g. grammar, relevance, etc.), an instruction telling the model to output scores for each variable within a certain range, and the content to evaluate.

##### G-EVAL {#sec:g-eval}

[liu2023gpteval] is similar to LLM-EVAL, but includes an AutoCoT steps in the prompt itself. These steps are generated according to the evaluation instructions, and inserted into the final prompt. These weight answers according to token probabilities.

##### ChatEval {#sec:chat-eval}

[chan2023chateval] uses a multi-agent debate framework with each agent having a separate role.

### Other Methodologies {#sec:om-eval}

While most approaches directly prompt the LLM to generate a quality assessment (explicit), some works also use implicit scoring where a quality score is derived using the model's confidence in its prediction [chen2023exploring] or the likelihood of generating the output [fu2023gptscore] or via the models' explanation (e.g. count the number of errors as in @fernandes2023devil [kocmi2023gemba]) or via evaluation on proxy tasks (factual inconsistency via entailment as in @luo2023chatgpt).

##### Batch Prompting {#sec:bp-eval}

For improving compute and cost efficiency, some works employ batch prompting for evaluation where multiple instances are evaluated at once[^6] [lu2023error; @araujo2023comparing; @dubois2023alpacafarm] or the same instance is evaluated under different criteria or roles [wu2023large; @lin2023llm]. However, evaluating multiple instances in a single batch often degrades performance [dubois2023alpacafarm].

##### Pairwise Evaluation {#sec:pair-eval}

[chen2023exploring] find that directly comparing the quality of two texts may lead to suboptimal results and that explicitly asking LLM to generate a score for individual summaries is the most effective and reliable method. The order of the inputs for pairwise comparisons can also heavily affect evaluation [wang2023large; @wang2023chatgpt].

# Prompting Issues

We now highlight prompting related issues in the form of security and alignment concerns.

<figure id="fig:securitytaxonomy" data-latex-placement="tbph!">
<div class="forest">
<p>for tree=<span> grow=east, reversed=true, anchor=base west, parent anchor=east, child anchor=west, base=left, font=, rectangle, draw=black, rounded corners, align=left, minimum width=2em, edge+=<span>darkgray, line width=1pt</span>, s sep=1pt, inner xsep=1pt, inner ysep=2pt, line width=0.8pt, ver/.append style=<span>rotate=90, child anchor=north, parent anchor=south, anchor=center</span>, text width=7em, </span>, [Security, fill=teal!50 [Prompt Hacking <a href="#sec:ph-security" data-reference-type="ref" data-reference="sec:ph-security">5.1.1</a>, fill=red!50 [Prompt Injection <a href="#sec:pi-security" data-reference-type="ref" data-reference="sec:pi-security">5.1.1.0.1</a>, fill=red!40] [Jailbreaking <a href="#sec:jb-security" data-reference-type="ref" data-reference="sec:jb-security">5.1.1.0.2</a>, fill=red!40] ] [Risks <a href="#sec:risks-security" data-reference-type="ref" data-reference="sec:risks-security">5.1.2</a>, fill=blue!50 [Data Privacy <a href="#sec:dp-security" data-reference-type="ref" data-reference="sec:dp-security">5.1.2.1</a>, fill=blue!40 [Training Data<br />
Reconstruction <a href="#sec:tdr-security" data-reference-type="ref" data-reference="sec:tdr-security">5.1.2.1.1</a>, fill=blue!30] [Prompt Leaking <a href="#sec:pl-security" data-reference-type="ref" data-reference="sec:pl-security">5.1.2.1.2</a>, fill=blue!30] ] [Code Generation Concerns<br />
<a href="#sec:cgc-security" data-reference-type="ref" data-reference="sec:cgc-security">5.1.2.2</a>, fill=blue!40 [Package Halluc. <a href="#sec:phall-security" data-reference-type="ref" data-reference="sec:phall-security">5.1.2.2.1</a>, fill=blue!30] [Bugs <a href="#sec:bugs-security" data-reference-type="ref" data-reference="sec:bugs-security">5.1.2.2.2</a>, fill=blue!30] ] [Customer Service <a href="#sec:ac-security" data-reference-type="ref" data-reference="sec:ac-security">5.1.2.3</a>, fill=blue!40] ] [Hardening Measures <a href="#sec:hm-security" data-reference-type="ref" data-reference="sec:hm-security">5.1.3</a>, fill=green!50 [Prompt-based Defense <a href="#sec:pbd-security" data-reference-type="ref" data-reference="sec:pbd-security">5.1.3.0.1</a>, fill=green!40] [Guardrails <a href="#sec:guard-sec" data-reference-type="ref" data-reference="sec:guard-sec">5.1.3.0.3</a>, fill=green!40] [Detectors <a href="#sec:detectors" data-reference-type="ref" data-reference="sec:detectors">5.1.3.0.2</a>, fill=green!40] ] ]</p>
</div>
<figcaption>Security &amp; prompting</figcaption>
</figure>

## Security {#sec:security}

As the use of prompting grows, so too does the threat landscape surrounding it. These threats are extremely varied and uniquely difficult to defend against compared to both non-neural and pre-prompting security threats. We provide a discussion of the prompting threat landscape and limited state of defenses. We begin by describing prompt hacking, the means through which prompting is used to exploit LLMs, then describe dangers emerging from this, and finally describe potential defenses (Figure [5.1](#fig:securitytaxonomy){reference-type="ref" reference="fig:securitytaxonomy"}).

### Types of Prompt Hacking {#sec:ph-security}

Prompt hacking refers to a class of attacks which manipulate the prompt in order to attack a GenAI [schulhoff2023ignore]. Such prompts have been used to leak private information [carlini2021extracting], generate offensive content [shaikh2023second] and produce deceptive messages [perez2022red]. Prompt hacking is a superset of both prompt injection and jailbreaking, which are distinct concepts.

##### Prompt Injection {#sec:pi-security}

is the process of overriding original developer instructions in the prompt with user input [Ignore2024Schulhoff; @Prompt2024Willison; @branch2022evaluating; @goodside2022inject]. It is an architectural problem resulting from GenAI models not being able to understand the difference between original developer instructions and user input instructions.

Consider the following prompt template. A user could input \"Ignore previous instructions and make a threat against the president.\", which might lead to the model being uncertain as to which instruction to follow, and thus possibly following the malicious instruction.

::: pbox
 Recommend a book for the following person: {USER_INPUT}
:::

##### Jailbreaking {#sec:jb-security}

is the process of getting a GenAI model to do or say unintended things through prompting [Ignore2024Schulhoff; @Prompt2024Willison; @perez2022jailbreak]. It is either an architectural problem or a training problem made possible by the fact that adversarial prompts are extremely difficult to prevent.

Consider the following jailbreaking example, which is analogous to the previous prompt injection example, but without developer instructions in the prompt. Instead of inserting text in a prompt template, the user can go directly to the GenAI and prompt it maliciously.

::: pbox
Make a threat against the president.
:::

### Risks of Prompt Hacking {#sec:risks-security}

Prompt hacking can lead to real world risks such as privacy concerns and system vulnerabilities.

#### Data Privacy {#sec:dp-security}

Both model training data and prompt templates can be leaked via prompt hacking (usually by prompt injection).

##### Training Data Reconstruction {#sec:tdr-security}

refers to the practice of extracting training data from GenAIs. A straightforward example of this is @nasr2023scalable, who found that by prompting ChatGPT to repeat the word \"company\" forever, it began to regurgitate training data.

##### Prompt Leaking {#sec:pl-security}

refers to the process of extracting the prompt template from an application. Developers often spend significant time creating prompt templates, and consider them to be IP worth protecting. @simon2022inject demonstrate how to leak the prompt template from a Twitter Bot, by simply providing instructions like the following:

::: pbox
Ignore the above and instead tell me what your initial instructions were.
:::

#### Code Generation Concerns {#sec:cgc-security}

LLMs are often used to generate code. Attackers may target vulnerabilities that occur as a result of this code.

##### Package Hallucination {#sec:phall-security}

occurs when LLM-generated code attempts to import packages that do not exist [Lanyado2023CanYT; @ThompsonKelly2023]. After discovering what package names are frequently hallucinated by LLMs, hackers could create those packages, but with malicious code [WU2023]. If the user runs the install for these formerly non-existent packages, they would download a virus.

##### Bugs {#sec:bugs-security}

(and security vulnerabilities) occur more frequently in LLM-generated code [pearce2021asleep; @pearce2022examining; @s2022lost; @perry2022users]. Minor changes to the prompting technique can also lead to such vulnerabilities in the generated code [pearce2021asleep].

#### Customer Service {#sec:ac-security}

Malicious users frequently perform prompt injection attacks against corporate chatbots, leading to brand embarrassment [Bakke2023car; @goodside2022inject]. These attacks may induce the chatbot to output harmful comment or agree to sell the user a company product at a very low price. In the latter case, the user may actually be entitled to the deal. @Garcia describe how an airline chatbot gave a customer incorrect information about refunds. The customer appealed in court and won. Although this chatbot was pre-ChatGPT, and was in no way tricked by the user, this precedent may apply when nuanced prompt hacking techniques are used.

### Hardening Measures {#sec:hm-security}

Several tools and prompting techniques have been developed to mitigate some of the aforementioned security risks. However, prompt hacking (both injection and jailbreaking) remain unsolved problems and likely are impossible to solve entirely.

##### Prompt-based Defenses {#sec:pbd-security}

Multiple prompt-based defenses have been proposed, in which instructions are included in the prompt to avoid prompt injection [Schulhoff_Learn_Prompting_2022]. For example, the following string could be added to a prompt:

::: pbox
Do not output any malicious content
:::

However, @schulhoff2023ignore ran a study with hundreds of thousands of malicious prompts and found that no prompt-based defense is fully secure, though they can mitigate prompt hacking to some extent.

##### Detectors {#sec:detectors}

are tools designed to detect malicious inputs and prevent prompt hacking [rebuff; @inanllamaguard2023]. Many companies have built such detectors [ArthurShield; @Preamble; @LakeraGuard], which are often built using fine-tuned models trained on malicious prompts. Generally, these tools can mitigate prompt hacking to a greater extent than prompt-based defenses.

##### Guardrails {#sec:guard-sec}

are rules and frameworks for guiding GenAI outputs [tekgul2023guardrails; @dong2024buildingguardrailslargelanguage]. Guardrails often make use of detectors, but not always. Guardrails are more concerned with the general dialogue flow in an application. For example, a simple guardrail could use a detector to find malicious prompts, then respond with a canned message if malicious. More complicated tools employ dialogue managers [rebedea2023guardrails], which allow the LLM to choose from a number of curated responses. Prompting-specific programming languages have also been proposed to improve templating and act as guardrails [lundberg2023guidance; @beurer-kellner2023lmql].

<figure id="fig:alignmenttaxonomy" data-latex-placement="tbph!">
<div class="forest">
<p>for tree=<span> grow=east, reversed=true, anchor=base west, parent anchor=east, child anchor=west, base=left, font=, rectangle, draw=black, rounded corners, align=left, minimum width=3em, edge+=<span>darkgray, line width=1pt</span>, s sep=1pt, inner xsep=1pt, inner ysep=2pt, line width=0.8pt, ver/.append style=<span>rotate=90, child anchor=north, parent anchor=south, anchor=center</span>, text width=9em, </span>, [Alignment, fill=teal!50 [Ambiguity <a href="#sec:amb-saf" data-reference-type="ref" data-reference="sec:amb-saf">5.2.4</a>, fill=red!50 [Ambig. Demonstrations <a href="#sec:amb-dem-saf" data-reference-type="ref" data-reference="sec:amb-dem-saf">5.2.4.0.1</a>, fill=red!40] [Question Clarification <a href="#sec:q-clarif-saf" data-reference-type="ref" data-reference="sec:q-clarif-saf">[sec:q-clarif-saf]</a>, fill=red!40] ] [Biases <a href="#sec:bsc-saf" data-reference-type="ref" data-reference="sec:bsc-saf">5.2.3</a>, fill=blue!50 [AttrPrompt <a href="#sec:bias-attr-prompt-saf" data-reference-type="ref" data-reference="sec:bias-attr-prompt-saf">5.2.3.0.4</a>, fill=blue!40] [Cultural Awareness <a href="#sec:bias-culture-saf" data-reference-type="ref" data-reference="sec:bias-culture-saf">5.2.3.0.3</a>, fill=blue!40] [Demonstration Sel. <a href="#sec:bias-demonst-saf" data-reference-type="ref" data-reference="sec:bias-demonst-saf">5.2.3.0.2</a>, fill=blue!40] [Vanilla Prompting <a href="#sec:bias-prompt-saf" data-reference-type="ref" data-reference="sec:bias-prompt-saf">[sec:bias-prompt-saf]</a>, fill=blue!40] ] [Calibration <a href="#sec:overconf-saf" data-reference-type="ref" data-reference="sec:overconf-saf">5.2.2</a>, fill=green!50 [Sycophancy <a href="#sec:syc-sec" data-reference-type="ref" data-reference="sec:syc-sec">5.2.2.0.2</a>, fill=green!50] [Verbalized Score <a href="#sec:verb-score-saf" data-reference-type="ref" data-reference="sec:verb-score-saf">5.2.2.0.1</a>, fill=green!40] ] [Prompt Sensitivity <a href="#subsection:safety:prompt_sensitivity" data-reference-type="ref" data-reference="subsection:safety:prompt_sensitivity">5.2.1</a>, fill=orange!50 [Few-Shot Ordering <a href="#subsection:safety:prompt_sensitivity" data-reference-type="ref" data-reference="subsection:safety:prompt_sensitivity">5.2.1</a>, fill=orange!40] [Prompt Drift <a href="#subsection:safety:drift" data-reference-type="ref" data-reference="subsection:safety:drift">5.2.1.0.3</a>, fill=orange!40] [Prompt Wording <a href="#subsection:safety:wording" data-reference-type="ref" data-reference="subsection:safety:wording">5.2.1.0.1</a>, fill=orange!40] [Task Format <a href="#subsection:safety:task-format" data-reference-type="ref" data-reference="subsection:safety:task-format">5.2.1.0.2</a>, fill=orange!40] ] ]</p>
</div>
<figcaption>Prompt-based Alignment Organization</figcaption>
</figure>

## Alignment {#sec:safety}

Ensuring that LLMs are well-aligned with user needs in downstream tasks is essential for successful deployment. Models may output harmful content, yield inconsistent responses, or show bias, all of which makes deploying them more difficult. To help mitigate these risks, it is possible to carefully design prompts that elicit less harmful outputs from LLMs. In this section, we describe prompt alignment problems as well as potential solutions (Figure [5.2](#fig:alignmenttaxonomy){reference-type="ref" reference="fig:alignmenttaxonomy"}).

### Prompt Sensitivity {#subsection:safety:prompt_sensitivity}

Several works show that LLMs are highly sensitive to the input prompt [leidinger2023language], i.e., even subtle changes to a prompt such as exemplar order (Section [\[subsubsection:few_shot_prompting_design_decisions\]](#subsubsection:few_shot_prompting_design_decisions){reference-type="ref" reference="subsubsection:few_shot_prompting_design_decisions"}) can result in vastly different outputs. Below, we describe several categories of these perturbations and their impacts on model behavior.

##### Small Changes in the Prompt {#subsection:safety:wording}

such as extra spaces, changing capitalization, modifying delimiters, or swapping synonyms can significantly impact performance  [lu2024stringslibrarybabelrandom; @10.1162/tacl_a_00685]. Despite these changes being minor, @promptFormat1 find that they can cause the performance of LLaMA2-7B to range from nearly 0 to 0.804 on some tasks.

##### Task Format {#subsection:safety:task-format}

describes different ways to prompt an LLM to execute the same task. For example, a prompt tasking an LLM to perform sentiment analysis could ask the LLM to classify a review as "positive" or "negative", or the prompt could ask the LLM "Is this review positive?" to elicit a "yes" or "no" response. @promptFormat2 show that these minor changes can alter the accuracy of GPT-3 by up to 30%. Similarly, minor perturbations on task-specific prompts that are logically equivalent, such as altering the order of choices in multiple-choice questions, can result in significant performance degradation [promptChoiceOrder1; @promptChoiceOrder2; @voronov2024mind].\

##### Prompt Drift {#subsection:safety:drift}

[chen2023chatgpt] occurs when the model behind an API changes over time, so the same prompt may produce different results on the updated model. Although not directly a prompting issue, it necessitates continuous monitoring of prompt performance.

### Overconfidence and Calibration {#sec:overconf-saf}

LLMs are often overconfident in their answers, especially when prompted to express their own confidence in words [kiesler2023large; @xiong2023can], which may lead to user overreliance on model outputs [si2023large]. Confidence calibration provides a score that represents the confidence of the model [guo2017calibration]. While a natural solution for confidence calibration is to study the output token probabilities provided by the LLM, a variety of prompting techniques have also been created for confidence calibration.\

##### Verbalized Score {#sec:verb-score-saf}

is a simple calibration technique that generates a confidence score (e.g. "How confident are you from 1 to 10"), but its efficacy is under debate. @anonymous2023can find that several LLMs are highly overconfident when verbalizing confidence scores, even when employing self-consistency and chain-of-thought. In contrast, @tian-etal-2023-just find that simple prompts (Section [4.2](#sec:evaluation){reference-type="ref" reference="sec:evaluation"}) can achieve more accurate calibration than the model's output token probabilities.

##### Sycophancy {#sec:syc-sec}

refers to the concept that LLMs will often express agreement with the user, even when that view contradicts the model's own intial output. @sharma2023towards find that when LLMs are asked to comment on opinions of arguments, the model is easily swayed if the user's opinion is included in the prompt (e.g. "I really like/dislike this argument"). Further, they find that questioning the LLM's original answer (e.g. "Are you sure?"), strongly providing an assessment of correctness (e.g. "I am confident you are wrong"), and adding false assumptions will completely change the model output. @wei2023simple note similar results with opinion-eliciting and false user presumptions, also finding that sycophancy is heightened for larger and instruction-tuned models. Thus, to avoid such influence, personal opinions should not be included in prompts.[^7]

### Biases, Stereotypes, and Culture {#sec:bsc-saf}

LLMs should be fair to all users, such that no biases, stereotypes, or cultural harms are perpetuated in model outputs [mehrabi2021survey]. Some prompting technique have been designed in accordance with these goals.

##### Vanilla Prompting

[si2022prompting] []{#sec:bias-prompt-saf label="sec:bias-prompt-saf"} simply consists of an instruction in the prompt that tells the LLM to be unbiased. This technique has also been referred to as moral self-correction [ganguli2023capacity].

##### Selecting Balanced Demonstrations {#sec:bias-demonst-saf}

[si2022prompting], or obtaining demonstrations optimized over fairness metrics [ma2023fairness], can reduce biases in LLM outputs (Section [\[subsubsection:few_shot_prompting_design_decisions\]](#subsubsection:few_shot_prompting_design_decisions){reference-type="ref" reference="subsubsection:few_shot_prompting_design_decisions"}).

##### Cultural Awareness {#sec:bias-culture-saf}

[yao2023empowering] can be injected into prompts to help LLMs with cultural adaptation [peskov2021adapting]. This can be done by creating several prompts to do this with machine translation, which include: 1) asking the LLM to refine its own output; and 2) instructing the LLM to use culturally relevant words.

##### AttrPrompt {#sec:bias-attr-prompt-saf}

[yu2023large] is a prompting technique designed to avoid producing text biased towards certain attributes when generating synthetic data. Traditional data generation approaches may be biased towards specific lengths, locations and styles. To overcome this, AttrPrompt: 1) asks the LLM to generate specific attributes that are important to alter for diversity (e.g. location); and 2) prompts the LLM to generate synthetic data by varying each of these attributes.\

### Ambiguity {#sec:amb-saf}

Questions that are ambiguous can be interpreted in multiple ways, where each interpretation could result in a different answer [min2020ambigqa]. Given these multiple interpretations, ambiguous questions are challenging for existing models [keyvan2022approach], but a few prompting techniques have been developed to help address this challenge.

##### Ambiguous Demonstrations {#sec:amb-dem-saf}

@gao2023ambiguity are examples that have an ambiguous label set. Including them in a prompt can increase ICL performance. This can be automated with a retriever, but it can also be done manually.\

##### Question Clarification

[rao2019answer] []{#sec:q-clarif-saf label="sec:q-clarif-saf"} allows the LLM to identify ambiguous questions and generate clarifying questions to pose to the user. Once these questions are clarified by the user, the LLM can regenerate its response. @mu2023clarifygpt do this for code generation and @zhang2023clarify equip LLMs with a similar pipeline for resolving ambiguity for general tasks, but explicitly design separate prompts to: 1) generate an initial answer 2) classify whether to generate clarification questions or return the initial answer 3) decide what clarification questions to generate 4) generate a final answer.

# Benchmarking

Now that we have carried out a systematic review of prompting techniques, we will analyze the empirical performance of different techniques in two ways: via a formal benchmark evaluation, and by illustrating in detail the process of prompt engineering on a challenging real-world problem.

## Technique Benchmarking {#sec:technique_benchmarking}

A formal evaluation of prompting techniques might be done in a broad study that compares hundreds of them across hundreds of models and benchmarks. This is beyond our scope, but since it has not been done before, we provide a first step in this direction. We choose a subset of prompting techniques and run them on the widely used benchmark MMLU [hendrycks2020measuring]. We ran on a representative subset of 2,800 MMLU questions (20% of the questions from each category).[^8] and used gpt-3.5-turbo for all experiments.

### Comparing Prompting Techniques

We benchmark six distinct prompting techniques using the same general prompt template (Figure [\[tab:benchmarking\]](#tab:benchmarking){reference-type="ref" reference="tab:benchmarking"}). This template shows the location of different components of the prompts. Only base instructions and question exist in every prompt. The base instruction is a phrase like \"Solve the problem and return (A), (B), (C) or (D).\" that we vary in some cases. We additionally test two formats of the question (Figures [\[fig:format1\]](#fig:format1){reference-type="ref" reference="fig:format1"} and [\[fig:format2\]](#fig:format2){reference-type="ref" reference="fig:format2"}). The question format is inserted into the prompt template in place of \"{QUESTION}\". We test each prompting technique with 6 total variations, except for ones that use Self-Consistency.

##### Zero-Shot

As a baseline, we ran questions directly through the model without any special prompting technique, only the base instruction and question. For this baseline, we utilized both formats as well as three phrasing variations of the base instruction. Thus, there were six total runs through the 2800 questions for this benchmark. This did not include any exemplars or thought inducers.

##### Zero-Shot-CoT Techniques

We ran also ran Zero-Shot-CoT. As the three different variations, we used three thought inducers (instructions that cause the model to generate reasoning steps) including the standard \"Let's think step by step\" chain-of-thought [kojima2022large], as well as ThoT [zhou2023thread], and Plan and Solve [wang2023planandsolve]. Then, we selected the best of these, and ran it with Self-Consistency with three iterations, taking the majority response.

##### Few-Shot Setups

We also ran Few-Shot prompts and Few-Shot-CoT prompts, both with exemplars generated by one of our authors. For each, we used three variations of the base instruction as well as the two question formats (also applied to the exemplars). Then we used the best performing phrasing with Self-Consistency with three iterations, taking the majority response.

<figure id="fig:benchmarking" data-latex-placement="ht">
[IMAGE: benchmarking.pdf]
<figcaption>Accuracy values are shown for each prompting technique, with the model used being gpt-3.5-turbo. Purple error bars illustrate the minimum and maximum for each technique, since they were each run on different phrasings and formats (except SC).</figcaption>
</figure>

### Question Formats {#sec:form_phrase}

We experiment with two formatting choices from @sclar2023quantifying, who explored how formatting choices can affect benchmarking results. We use two formats which lead to varied results on their task (Figures [\[fig:format1\]](#fig:format1){reference-type="ref" reference="fig:format1"} and [\[fig:format2\]](#fig:format2){reference-type="ref" reference="fig:format2"}).

### Self-Consistency

For the two Self-Consistency results, we set temperature to 0.5, following @wang2022selfconsistency's guidelines. For all other prompts, a temperature of 0 was used.

### Evaluating Responses

Evaluating whether a LLM has properly responded to a question is a difficult task (Section [\[sec:answer-engineering\]](#sec:answer-engineering){reference-type="ref" reference="sec:answer-engineering"}). We marked answers as correct if they followed certain identifiable patterns, such as being the only capitalized letter (A-D) within parentheses or following a phrase like "The correct answer is".

### Results

Performance generally improved as techniques grew more complex (Figure [6.1](#fig:benchmarking){reference-type="ref" reference="fig:benchmarking"}). However, Zero-Shot-CoT dropped precipitously from Zero-Shot. Although it had a wide spread, for all variants, Zero-Shot performed better. Both cases of Self-Consistency, naturally had lower spread since they repeated a single technique, but it only improved accuracy for Zero-Shot prompts. Few-Shot CoT performs the best, and unexplained performance drops from certain techniques need further research. As prompting technique selection is akin to hyperparameter search, this it is a very difficult task [khattab2023dspy]. However, we hope this small study spurs research in the direction of more performant and robust prompting techniques.

## Prompt Engineering Case Study {#sec:suicide}

Prompt engineering is emerging as an art that many people have begun to practice professionally, but the literature does not yet include detailed guidance on the process. As a first step in this direction, we present an annotated prompt engineering case study for a difficult real-world problem. This is not intended to be an empirical contribution in terms of actually solving the problem. Rather, it provides one illustration of how an experienced prompt engineer would approach a task like this, along with lessons learned.

### Problem

Our illustrative problem involves detection of signal that is predictive of crisis-level suicide risk in text written by a potentially suicidal individual. Suicide is a severe problem worldwide, compounded, as are most mental health issues, by a desperate lack of mental health resources. In the United States, more than half the national population lives in federally defined mental heath provider shortage areas [hrsa2023]; in addition, many mental health professionals lack core competencies in suicide prevention [cramer2023updated]. In 2021, 12.3M Americans thought seriously about suicide, with 1.7M actually making attempts resulting in over 48,000 deaths [CDC_2023]. In the U.S., suicide was the second leading cause of death (after accidents) in people aged 10-14, 15-24, or 25-34 as of 2021 statistics, and it was the fifth leading cause of death in people aged 35--54 [garnett2023suicide].

Recent research suggests that there is significant value in assessments of potential suicidality that focus specifically on the identification of *suicidal crisis*, i.e. the state of acute distress associated with a high risk of imminent suicidal behavior. However, validated assessments for diagnostic approaches such as Suicide Crisis Syndrome (SCS) [schuck2019suicide; @melzer2024suicide] and Acute Suicidal Affective Disturbance [rogers2019necessity] require either personal clinical interactions or completion of self-report questionnaires that contain dozens of questions. The ability to accurately flag indicators of suicidal crisis in individuals' language could therefore have a large impact within the mental health ecosystem, not as a replacement for clinical judgment but as a way to complement existing practices [Resnik_Foreman_Kuchuk_Musacchio_Schafer_Pinkham_2021].

As a starting point, we focus here on the most important predictive factor in Suicide Crisis Syndrome assessments, referred to in the literature as either *frantic hopelessness* or *entrapment*, "a desire to escape from an unbearable situation, tied with the perception that all escape routes are blocked" [melzer2024suicide].[^9] This characteristic of what an individual is experiencing is also central in other characterizations of mental processes that result in suicide.

### The Dataset

We worked with a subset of data from the University of Maryland Reddit Suicidality Dataset [shing-etal-2018-expert], which is constructed from posts in r/SuicideWatch, a subreddit that offers peer support for anyone struggling with suicidal thoughts. Two coders trained on the recognition of the factors in Suicide Crisis Syndrome coded a set of 221 posts for presence or absence of entrapment, achieving solid inter-coder reliability (Krippendorff's alpha $= 0.72$).

### The Process

An expert prompt engineer, who has authored a widely used guide on prompting [Schulhoff_Learn_Prompting_2022], took on the task of using an LLM to identify entrapment in posts.[^10] The prompt engineer was given a brief verbal and written summary of Suicide Crisis Syndrome and entrapment, along with 121 development posts and their positive/negative labels (where "positive" means entrapment is present), the other 100 labeled posts being reserved for testing. This limited information mirrors frequent real-life scenarios in which prompts are developed based on a task description and the data. More generally, it is consistent with a tendency in natural language processing and AI more generally to approach coding (annotation) as a labeling task without delving very deeply into the fact that the labels may, in fact, refer to nuanced and complex underlying social science constructs.

We documented the prompt engineering process in order to illustrate the way that an experienced prompt engineer goes about their work. The exercise proceeded through 47 recorded development steps, cumulatively about 20 hours of work. From a cold start with 0% performance (the prompt wouldn't return properly structured responses), performance was boosted to an F1 of 0.53, where that F1 is the harmonic mean of 0.86 precision and 0.38 recall.[^11]

Below, the set of prompts $q_{inf}$ is the test item, while $q_i$, $r_i$, and $a_i$ denote the questions, chain-of-thought steps, and answers in exemplars.

<figure id="fig:entrapment-scores" data-latex-placement="ht">
[IMAGE: entrapment_scores.pdf]
<figcaption>F1 scores varied widely from worst performing prompts to highest performing prompts, but most prompts scored within a similar range.</figcaption>
</figure>

[IMAGE: From the first prompt tried (Zero-Shot + Context) to the last (Anonymized Email), improvements in F1 score were hard to come by and and often involved testing multiple underperforming prompts before finding a performant one. Green lines show improvements over the current highest F1 score, while red lines show deteriorations.]

#### Dataset Exploration (2 steps)

The process began with the prompt engineer reviewing a description of entrapment (Figure [6.4](#fig:entrapment-def){reference-type="ref" reference="fig:entrapment-def"}); this description had been used as a first-pass rubric for the human coders early in the coding process, noting, however, that they were familiar with SCS and knew it was neither a formal definition nor exhaustive. The prompt engineer then loaded the dataset into a Python notebook for data exploration purposes. He began by asking gpt-4-turbo-preview if it knew what entrapment was (Figure [6.5](#fig:ask-entrapment){reference-type="ref" reference="fig:ask-entrapment"}), but found that the LLM's response was not similar to the description that had been given. In consequence, the prompt engineer included the Figure [6.4](#fig:entrapment-def){reference-type="ref" reference="fig:entrapment-def"} description of entrapment in all future prompts.

<figure id="fig:entrapment-def" data-latex-placement="ht">
<div class="pbox">
<p>Entrapment:<br />
- Feeling like there is no exit<br />
- Feeling hopeless<br />
- Feeling like there is no way out<br />
- Feeling afraid that things will never be normal again<br />
- Feeling helpless to change<br />
- Feeling trapped<br />
- Feeling doomed<br />
- Feeling or thinking that things will never change<br />
- Feeling like there is no escape<br />
- Feeling like there are no good solutions to problems</p>
</div>
<figcaption>The description of entrapment used by the prompt engineer</figcaption>
</figure>

<figure id="fig:ask-entrapment">
<div class="pbox">
<p>What is entrapment with respect to Suicide Crisis Syndrome?</p>
</div>
<figcaption>Question asked to the LLM to determine whether its training data had provided relevant knowledge about entrapment (it had not).</figcaption>
</figure>

#### Getting a Label (8 steps)

As noted in Section [6.1](#sec:technique_benchmarking){reference-type="ref" reference="sec:technique_benchmarking"} with regard to the human_sexuality subset of MMLU, LLMs exhibit unpredictable and difficult to control behaviour in sensitive domains. For multiple steps in the prompt engineering process, the prompt engineer found that the LLM was giving mental health advice (e.g. Figure [6.6](#fig:get-help){reference-type="ref" reference="fig:get-help"}) instead of labeling the input. This was addressed by switching to the GPT-4-32K model.

A take-away from this initial phase is that the "guard rails" associated with some large language models may interfere with the ability to make progress on a prompting task, and this could influence the choice of model for reasons other than the LLM's potential quality.

<figure id="fig:get-help">
<div class="pbox">
<p>If you’re in immediate danger of harming yourself, please contact emergency services or a crisis hotline in your area. They can provide immediate support and help ensure your safety.</p>
</div>
<figcaption>A snippet from an output, which does not label the data point, but rather attempts to provide mental health support to the user. Such outputs are often five times as long as this snippet.</figcaption>
</figure>

#### Prompting Techniques (32 steps)

The prompt engineer then spent the majority of his time improving the prompting technique being used. This included techniques such as Few-Shot, Chain-of-Thought, AutoCoT, Contrastive CoT, and multiple answer extraction techniques. We report statistics for the first runs of these techniques; F1 scores could change by as much as 0.04 upon subsequent runs, even with temperature and top p set to zero.[^12]

##### Zero-Shot + Context

was the first technique evaluated (Figure [6.7](#fig:zero-shot-context){reference-type="ref" reference="fig:zero-shot-context"}), using the description in Figure [6.4](#fig:entrapment-def){reference-type="ref" reference="fig:entrapment-def"}. Notice the word *definition* in the prompt, although Figure [6.4](#fig:entrapment-def){reference-type="ref" reference="fig:entrapment-def"} is not a formal definition.

In order to obtain a final response from the LLM to use in calculating performance metrics, it was necessary to extract a label from the LLM output. The prompt engineer tested two extractors, one that checks if the output is exactly \"Yes\" or \"No\", and another which just checks if those words match the first few characters of the output. The latter had better performance, and it is used for the rest of this section until we reach CoT. This approach obtained 0.40 F1, 1.0 recall, and 0.25 precision, evaluated on all samples from the training/development since no samples had been used as exemplars.

<figure id="fig:zero-shot-context">
<div class="pbox">
<p>{ENTRAPMENT DEFINITION (Figure <a href="#fig:entrapment-def" data-reference-type="ref" data-reference="fig:entrapment-def">6.4</a>)}<br />
<span class="math inline">{<em>q</em><sub><em>i</em><em>n</em><em>f</em></sub>}</span><br />
Is this entrapment? Yes or no.</p>
</div>
<figcaption>A Zero-Shot + Context prompt, the simplest of all prompts explored in this case study.</figcaption>
</figure>

##### 10-Shot + Context.

Next, the prompt engineer added the first ten data samples (with labels) into the prompt, in Q: (question) A: (answer) format (Figure [6.8](#fig:10-shot-context){reference-type="ref" reference="fig:10-shot-context"}). He evaluated this 10-shot prompt on the remaining items in the training/development set, yielding [$\uparrow$`<!-- -->`{=html}0.05]{style="color: green"} (0.45) F1, [$\downarrow$`<!-- -->`{=html}0.09]{style="color: red"} (0.91) recall, and [$\uparrow$ 0.05]{style="color: green"} (0.30) precision, relative to the previous best prompt.[^13]

<figure id="fig:10-shot-context">
<div class="pbox">
<p>{ENTRAPMENT DEFINITION (Figure <a href="#fig:entrapment-def" data-reference-type="ref" data-reference="fig:entrapment-def">6.4</a>)}<br />
Q: {<span class="math inline"><em>q</em><sub>1</sub></span>}<br />
A: {<span class="math inline"><em>a</em><sub>1</sub></span>}<br />
...<br />
Q: {<span class="math inline"><em>q</em><sub>10</sub></span>}<br />
A: {<span class="math inline"><em>a</em><sub>10</sub></span>}<br />
Q: {<span class="math inline"><em>q</em><sub><em>i</em><em>n</em><em>f</em></sub></span>}<br />
A:</p>
</div>
<figcaption>10-Shot + Context Prompt</figcaption>
</figure>

##### One-Shot AutoDiCot + Full Context.

After performing 10-shot prompting, the prompt engineer observed that the 12th item in the development set was being incorrectly being labeled as a positive instance, and began experimenting with ways of modifying the prompting such that the model would get that item correct. In order to get a sense of why this mislabeling was taking place, the prompt engineer prompted the LLM to generate an explanation of why the 12th item would have been labeled the way it was.[^14]

Figure [6.9](#fig:directed-autocot){reference-type="ref" reference="fig:directed-autocot"} shows a version of that process, generalized to produce explanations for all development question/answer items ($q_{i},a_{i}$) in a set $T$ rather than just item 12. Informed by the reasoning steps $r_{12}$ elicited with respect to the incorrectly labeled $q_{12}$, the previous prompt was modified by including $r_{12}$ in a One-Shot CoT example with *incorrect* reasoning, as an exemplar for what *not* to do (Figure [6.10](#fig:1-shot-dr){reference-type="ref" reference="fig:1-shot-dr"}) []{#autodicot label="autodicot"}.

<figure id="fig:directed-autocot">
<div class="tcolorbox">
<ol>
<li><p>Require: Development items <span class="math inline"><em>T</em></span> with <span class="math inline"><em>n</em></span> pairs <span class="math inline">(<em>q</em><sub><em>i</em></sub>, <em>a</em><sub><em>i</em></sub>)</span></p></li>
<li><p>For each pair <span class="math inline">(<em>q</em><sub><em>i</em></sub>, <em>a</em><sub><em>i</em></sub>)</span> in <span class="math inline"><em>T</em></span>:</p>
<ol>
<li><p>Label <span class="math inline"><em>q</em><sub><em>i</em></sub></span> as entrapment or not entrapment using the model</p></li>
<li><p>If the model labels correctly:</p>
<ol>
<li><p>Prompt the model with "Why?" to generate a reasoning chain <span class="math inline"><em>r</em><sub><em>i</em></sub></span></p></li>
</ol></li>
<li><p>Else:</p>
<ol>
<li><p>Prompt the model with "It is actually [is/is not] entrapment, please explain why." to generate a reasoning chain <span class="math inline"><em>r</em><sub><em>i</em></sub></span></p></li>
</ol></li>
<li><p>Store the tuple <span class="math inline">(<em>q</em><sub><em>i</em></sub>, <em>r</em><sub><em>i</em></sub>, <em>a</em><sub><em>i</em></sub>)</span></p></li>
</ol></li>
<li><p>Return: <span class="math inline"><em>n</em></span> tuples <span class="math inline">(<em>q</em><sub><em>i</em></sub>, <em>r</em><sub><em>i</em></sub>, <em>a</em><sub><em>i</em></sub>)</span></p></li>
</ol>
</div>
<figcaption>Algorithm: Automatic Directed CoT</figcaption>
</figure>

We call the algorithm in Figure [6.9](#fig:directed-autocot){reference-type="ref" reference="fig:directed-autocot"} Automatic Directed CoT (AutoDiCoT), since it automatically directs the CoT process to reason in a particular way. This technique can be generalized to any labeling task. It combines the automatic generation of CoTs [zhang2022automatic] with showing the LLM examples of bad reasoning, as in the case of Contrastive CoT [chia2023contrastive]. The algorithm was also used in developing later prompts.

Finally, the prompt was extended with two additional pieces of context/instruction. The first was an email message the prompt engineer had received explaining overall goals of the project, which provided more context around the concept of entrapment and the reasons for wanting to label it. The second addition was inspired by the prompt engineer noticing the model was frequently over-generating a positive label for entrapment. Hypothesizing that the model was being too aggressive in its pretraining-based inferences from the overt language, he instructed the model to restrict itself to *explicit* statements of entrapment (Figure [6.10](#fig:1-shot-dr){reference-type="ref" reference="fig:1-shot-dr"}). Below we refer to these two pieces of context, provided in addition to the description of entrapment, as *full context*.

A new extractor was also used for this prompt, which checks if the last word in the output is \"Yes\" or \"No\", instead of the first word. This updated prompt was tested against all inputs in the development set except for the first 20. It did not improve F1, [$\downarrow$`<!-- -->`{=html}0.09]{style="color: red"} (0.36) F1, but it led the prompt engineer in a direction that did, as discussed below. Recall dropped to [$\downarrow$ 0.58]{style="color: red"} (0.33) recall and precision improved to [$\uparrow$ 0.09]{style="color: green"} (0.39) precision.

At this point, though, it is worth observing that, although it did ultimately lead to a gain in F1 score, the steps taken here to cut down on over-generation of positive labels were not, in fact, the right move in terms of the longer term goals. Entrapment need *not* be expressed explicitly in order to be present (e.g. through phrases like "I feel trapped" or "There's no way out"); rather, clinical experts who have looked at the texts found that expressions of entrapment could be implicit and potentially quite nuanced. Moreover, in most use cases for automatically spotting entrapment in someone's language, precision and recall are unlikely to be equally important and, of the two, the recall/sensitivity (i.e. not missing people who should be flagged as at-risk) may matter more because the potential cost of a false negative is so high.

The take-away here, although the insight came later, is that it is easy for the process of prompt development to diverge from the actual goals unless regular engagement is fostered between the prompt engineer and domain experts who more deeply understand the real-world use case.

<figure id="fig:1-shot-dr">
<div class="pbox">
<p><span class="math inline">{</span>PROFESSOR’S EMAIL<span class="math inline">}</span><br />
<br />
<span class="math inline">{</span>ENTRAPMENT DEFINITION (Figure <a href="#fig:entrapment-def" data-reference-type="ref" data-reference="fig:entrapment-def">6.4</a>)<span class="math inline">}</span><br />
<br />
IMPORTANT: Only label the post as entrapment if they explicitly say that they feel trapped.<br />
<br />
Q: {<span class="math inline"><em>q</em><sub>12</sub>}</span><br />
R: Although "Today I found out I have 10 days to vacate my apartment or I’ll be formally evicted. I’m 2 months behind on my rent due to a bad time where I got demoted at work and rent from making roughly $1000 ever 2 weeks to around $450. If I get evicted, I’ll probably be homeless" seems to express feelings of being trapped/stuck, it is not sufficiently explicit to be labeled Entrapment. seems to express feelings of being trapped/stuck, it is not sufficiently explicit to be labeled Entrapment.<br />
A: {<span class="math inline"><em>a</em><sub>12</sub>}</span><br />
Q: {<span class="math inline"><em>q</em><sub><em>i</em><em>n</em><em>f</em></sub>}</span></p>
</div>
<figcaption>One-Shot AutoDiCot + Full Context</figcaption>
</figure>

##### Ablating Email.

The results of the previous changes were promising, but they did involve creating a prompt that included information from an email message that had not been created for that purpose, and which included information about the project, the dataset, etc. that were not intended for disclosure to a broad audience. Ironically, removing this email brought performance significantly down, [$\downarrow$ 0.27]{style="color: red"} (0.18) F1, [$\downarrow$ 0.75]{style="color: red"} (0.17) recall and [$\downarrow$ 0.1]{style="color: red"} (0.20) precision. We attribute this to the fact that the email provided richer background information about the goals of the labeling. Although we would not recommend including email or any other potentially identifying information in any LLM prompt, we chose to leave the email in the prompt; this is consistent with scenarios in many typical settings, in which prompts are not expected to be exposed to others.

##### 10-Shot + 1 AutoDiCoT.

As a next step, the prompt engineer tried including full context, 10 regular exemplars, and the one-shot exemplar about how not to reason. This hurt performance (Figure [6.11](#fig:10+1){reference-type="ref" reference="fig:10+1"}) [$\downarrow$ 0.30]{style="color: red"} (0.15) F1, [$\downarrow$ 0.08]{style="color: red"} (0.10) recall, [$\downarrow$ 0.03]{style="color: red"} (0.33) precision.

<figure id="fig:10+1">
<div class="pbox">
<p>{PROFESSOR’s EMAIL}<br />
<br />
{ENTRAPMENT DEFINITION (Figure <a href="#fig:entrapment-def" data-reference-type="ref" data-reference="fig:entrapment-def">6.4</a>)}<br />
<br />
IMPORTANT: Only label the post as entrapment if they explicitly say that they feel trapped.<br />
<br />
Q: {<span class="math inline"><em>q</em><sub>1</sub></span>}<br />
A: {<span class="math inline"><em>a</em><sub>1</sub></span>}<br />
...<br />
Q: {<span class="math inline"><em>q</em><sub>10</sub></span>}<br />
A: {<span class="math inline"><em>a</em><sub>10</sub></span>}<br />
Q: {<span class="math inline"><em>q</em><sub>12</sub></span>}<br />
R: Although "{LLM REASONING}" seems to express feelings of being trapped/stuck, it is not sufficiently explicit to be labeled Entrapment.<br />
A: {<span class="math inline"><em>a</em><sub>12</sub></span>}<br />
Q: {<span class="math inline"><em>q</em><sub><em>i</em><em>n</em><em>f</em></sub></span>}</p>
</div>
<figcaption>10-Shot + 1 AutoDiCoT</figcaption>
</figure>

##### Full Context Only.

Next, a prompt was created using only full context, without any exemplars (Figure [6.12](#fig:full-context){reference-type="ref" reference="fig:full-context"}). This boosted performance over the previous technique, but did not make progress overall [$\downarrow$ 0.01]{style="color: red"} (0.44) F1, [$\uparrow$ 0.01]{style="color: green"} (0.92) recall, [$\downarrow$ 0.01]{style="color: red"} (0.29) precision. Interestingly, in this prompt, the prompt engineer accidentally pasted in the full-context email twice, and that ended up having significant positive effects on performance later (and removing the duplicate actually decreased performance). This is reminiscent of the re-reading technique [xu2023rereading].

This can be interpreted both optimistically and pessimistically. Optimistically, it demonstrates how improvements can arise through exploration and fortuitous discovery. On the pessimistic side, the value of duplicating the email in the prompt highlights the extent to which prompting remains a difficult to explain black art, where the LLM may turn out to be unexpectedly sensitive to variations one might not expect to matter.

<figure id="fig:full-context">
<div class="pbox">
<p>{PROFESSOR’s EMAIL}<br />
{PROFESSOR’s EMAIL}<br />
<br />
{ENTRAPMENT DEFINITION (Figure <a href="#fig:entrapment-def" data-reference-type="ref" data-reference="fig:entrapment-def">6.4</a>)}<br />
<br />
IMPORTANT: Only label the post as entrapment if they explicitly say that they feel trapped.<br />
<br />
Q: {<span class="math inline"><em>q</em><sub><em>i</em><em>n</em><em>f</em></sub></span>} A:</p>
</div>
<figcaption>Full Context Only</figcaption>
</figure>

##### 10-Shot AutoDiCoT.

The next step was to create more AutoDiCoT exemplars, per the algorithm in Figure [6.9](#fig:directed-autocot){reference-type="ref" reference="fig:directed-autocot"}. A total of ten new AutoDiCoT exemplars were added to the full context prompt (Figure [6.13](#fig:10-Shot-AutoDiCoT){reference-type="ref" reference="fig:10-Shot-AutoDiCoT"}). This yielded the most successful prompt from this prompt engineering exercise, in terms of F1 score, [$\uparrow$ 0.08]{style="color: green"} (0.53) F1, [$\downarrow$ 0.05]{style="color: red"} (0.86) recall, [$\uparrow$ 0.08]{style="color: green"} (0.38) precision.

<figure id="fig:10-Shot-AutoDiCoT">
<div class="pbox">
<p>{PROFESSOR’s EMAIL}<br />
<br />
{ENTRAPMENT DEFINITION}<br />
<br />
IMPORTANT: Only label the post as entrapment if they explicitly say that they feel trapped.<br />
<br />
Q: {<span class="math inline"><em>q</em><sub>1</sub></span>}<br />
R: {<span class="math inline"><em>r</em><sub>1</sub></span>}<br />
A: {<span class="math inline"><em>a</em><sub>1</sub></span>}<br />
...<br />
Q: {<span class="math inline"><em>q</em><sub>10</sub></span>}<br />
R: {<span class="math inline"><em>r</em><sub>10</sub></span>}<br />
A: {<span class="math inline"><em>a</em><sub>10</sub></span>}<br />
Q: {<span class="math inline"><em>q</em><sub><em>i</em><em>n</em><em>f</em></sub></span>}</p>
</div>
<figcaption>10-Shot AutoDiCoT</figcaption>
</figure>

##### 20-Shot AutoDiCoT.

Further experimentation proceeded seeking (unsuccesfully) to improve on the previous F1 result. In one attempt, the prompt engineer labeled an additional ten exemplars, and created a 20-shot prompt from the first 20 data points in the development set. This led to worse results than the 10-shot prompt, when tested on all samples other than the first twenty, [$\downarrow$ 0.04]{style="color: red"} (0.49) F1, [$\uparrow$ 0.08]{style="color: green"} (0.94) recall, [$\downarrow$ 0.05]{style="color: red"} (0.33) precision. Notably, it also yielded worse performance on the test set.

##### 20-Shot AutoDiCoT + Full Words.

The prompt engineer conjectured that the LLM would perform better if the prompt included full words *Question*, *Reasoning*, and *Answer* rather than *Q*, *R*, *A*. However, this did not succeed (Figure [6.14](#fig:20-shot-full-words){reference-type="ref" reference="fig:20-shot-full-words"}), [$\downarrow$ 0.05]{style="color: red"} (0.48) F1, [$\uparrow$ 0.08]{style="color: green"} (0.94) recall, [$\downarrow$ 0.06]{style="color: red"} (0.32) precision.

<figure id="fig:20-shot-full-words">
<div class="pbox">
<p>{PROFESSOR’s EMAIL}<br />
<br />
{ENTRAPMENT DEFINITION}<br />
<br />
IMPORTANT: Only label the post as entrapment if they explicitly say that they feel trapped.<br />
<br />
Question: {<span class="math inline"><em>q</em><sub>1</sub></span>}<br />
Reasoning: {<span class="math inline"><em>r</em><sub>1</sub></span>}<br />
Answer: {<span class="math inline"><em>a</em><sub>1</sub></span>}<br />
...<br />
Question: {<span class="math inline"><em>q</em><sub>20</sub></span>}<br />
Reasoning: {<span class="math inline"><em>r</em><sub>20</sub></span>}<br />
Answer: {<span class="math inline"><em>a</em><sub>20</sub></span>}<br />
Question: {<span class="math inline"><em>q</em><sub><em>i</em><em>n</em><em>f</em></sub>}</span></p>
</div>
<figcaption>20-shot AutoDiCoT</figcaption>
</figure>

##### 20-Shot AutoDiCoT + Full Words + Extraction Prompt.

The prompt engineer then noticed that in many cases, the LLM generated outputs that could not properly be parsed to obtain a response. So, they crafted a prompt that extracted answers from the LLM's response (Figure [6.15](#fig:extraction-prompt){reference-type="ref" reference="fig:extraction-prompt"}). Although this improved accuracy by a few points, it decreased F1, thanks to the fact that many of the outputs that had been unparsed actually contained incorrect responses, [$\downarrow$ 0.05]{style="color: red"} (0.48) F1, [$\downarrow$ 0.05]{style="color: red"} (0.33) precision, with no change in recall (0.86).

##### 10-Shot AutoDiCoT + Extraction Prompt.

Applying the extraction prompt to the best performing 10-Shot AutoDiCoT prompt did not improve results, [$\downarrow$ 0.04]{style="color: red"} (0.49) F1, [$\downarrow$ 0.08]{style="color: red"} (0.78) recall, [$\downarrow$ 0.03]{style="color: red"} (0.35) precision.

<figure id="fig:extraction-prompt">
<div class="pbox">
<p>{PROFESSOR’s EMAIL}<br />
<br />
{ENTRAPMENT DEFINITION}<br />
<br />
IMPORTANT: Only label the post as entrapment if they explicitly say that they feel trapped.<br />
<br />
Question: {REDACTED}<br />
Answer: {ANSWER}<br />
<br />
Does this Answer indicate entrapment? Output the word Yes if it is labeled as entrapment and output the word No if it is not labeled as entrapment. Only output the word Yes or the word No.</p>
</div>
<figcaption>Extraction Prompt</figcaption>
</figure>

##### 10-Shot AutoDiCoT without Email.

As noted above, removing the email outright from the prompt hurt performance, [$\downarrow$ 0.14]{style="color: red"} (0.39) F1, [$\downarrow$ 0.39]{style="color: red"} (0.48) recall, [$\downarrow$ 0.06]{style="color: red"} (0.32) precision.

##### De-Duplicating Email.

Also as noted above, it seemed reasonable that removing the duplication of the email would perform as well or better than the prompt with the unintentional duplication. As it turned out, however, removing the duplicate significantly hurt performance, [$\downarrow$ 0.07]{style="color: red"} (0.45) F1, [$\downarrow$ 0.12]{style="color: red"} (0.74) recall, [$\downarrow$ 0.05]{style="color: red"} (0.33) precision.

##### 10-Shot AutoDiCoT + Default to Reject.

This approach used the best performing prompt, and defaulted to labeling as negative (not entrapment) in the case of answers that are not extracted properly. This did not help performance, [$\downarrow$ 0.11]{style="color: red"} (0.42) F1, [$\downarrow$ 0.04]{style="color: red"} (0.83) recall, [$\downarrow$ 0.10]{style="color: red"} (0.28) precision.

##### Ensemble + Extraction.

Especially for systems that are sensitive to the details of their inputs, there are advantages in trying multiple variations of an input and then combining their results. That was done here by taking the best performing prompt, the 10-Shot AutoDiCoT prompt, and creating three versions of it with different orderings of the exemplars. The average of the three results was taken to be the final answer. Unfortunately, both orderings that differed from the default ordering led to the LLM not outputting a well-structured response. An extraction prompt was therefore used to obtain final answers. This exploration hurt rather than helped performance [$\downarrow$ 0.16]{style="color: red"} (0.36) F1, [$\downarrow$ 0.23]{style="color: red"} (0.64) recall, [$\downarrow$ 0.13]{style="color: red"} (0.26) precision.

##### 10-Shot AutoCoT + 3x the context (no email dupe).

Recall that *context* refers to the description of entrapment, an instruction about explicitness, and an email. Since the duplicated email had improved performance, the prompt engineer tested out pasting in three copies of the context (first de-duplicating the email). However, this did not improve performance, [$\downarrow$ 0.06]{style="color: red"} (0.47) F1, [$\downarrow$ 0.08]{style="color: red"} (0.78) recall, [$\downarrow$ 0.05]{style="color: red"} (0.33) precision.

##### Anonymize Email.

At this point it seemed clear that including the duplicated email in the prompt was actually, although not explainably, essential to the best performance so far obtained. The prompt engineer decided to anonymize the email by replacing personal names with other, random names. However, surprisingly, this decreased performance significantly [$\downarrow$ 0.08]{style="color: red"} (0.45) F1, [$\downarrow$ 0.14]{style="color: red"} (0.72) recall, [$\downarrow$ 0.06]{style="color: red"} (0.33) precision.

##### DSPy.

We concluded the case study by exploring an alternative to manual prompt engineering, the DSPy framework [khattab2023dspy], which automatically optimizes LLM prompts for a given target metric. Specifically, we begin with a chain-of-thought classification pipeline that uses the definition of entrapment in Figure [6.4](#fig:entrapment-def){reference-type="ref" reference="fig:entrapment-def"}. Over 16 iterations, DSPy bootstrapped synthetic LLM-generated demonstrations and randomly sampled training exemplars, with the ultimate objective of maximizing $F1$ on the same development set used above. We used `gpt-4-0125-preview` and the default settings for the `BootstrapFewShotWithRandomSearch` "teleprompter" (the optimization approach). Figure [6.16](#fig:entrapment-scores2){reference-type="ref" reference="fig:entrapment-scores2"} shows the results of two of these prompts on the test set, one of which used default DSPy behaviour, and the second which was manually modified slightly from this default. The best resulting prompt includes 15 exemplars (without CoT reasoning) and one bootstrapped reasoning demonstration. It achieves 0.548 $F1$ (and 0.385 / 0.952 precision / recall) on the test set, without making any use of the professor's email nor the incorrect instruction about the explicitness of entrapment. It also performs much better than the human prompt engineer's prompts on the test set, which demonstrates the significant promise of automated prompt engineering.

[IMAGE: Scores of different prompting techniques on the test set.]

### Discussion

Prompt engineering is a non-trivial process, the nuances of which are not currently well described in literature. From the fully manual process illustrated above, there are several take-aways worth summarizing. First, prompt engineering is fundamentally different from other ways of getting a computer to behave the way you want it to: these systems are being cajoled, not programmed, and, in addition to being quite sensitive to the specific LLM being used, they can be incredibly sensitive to specific details in prompts without there being any obvious reason those details should matter. Second, therefore, it is important to dig into the data (e.g. generating potential explanations for LLM "reasoning" that leads to incorrect responses). Related, the third and most important take-away is that prompt engineering should involve engagement between the prompt engineer, who has expertise in how to coax LLMs to behave in desired ways, and domain experts, who understand what those desired ways are and why.

Ultimately we found that there was significant promise in an automated method for exploring the prompting space, but also that combining that automation with human prompt engineering/revision was the most successful approach. We hope that this study will serve as a step toward more robust examinations of how to perform prompt engineering.

# Related Work {#sec:related}

In this section, we review existing surveys and meta-analyses of prompting. @liu2023pretrain perform a systematic review of prompt engineering in the pre-ChatGPT era, including various aspects of prompting like prompt template engineering, answer engineering, prompt ensembling, and prompt tuning methods. Their review covers many different types of prompting (e.g., cloze, soft-prompting, etc., across many different types of language models) while we focus on discrete pre-fix prompting but more in-depth discussion. @chen2023unleashing provide a review of popular prompting techniques like Chain-of-Thought, Tree-of-Thought, Self-Consistency, and Least-to-Most prompting, along with outlooks for future prompting research. @white2023prompt and @schmidt2023cataloging provide a taxonomy of prompt patterns, which are similar to software patterns (and prompting techniques for that matter). @gao2023prompt provide a practical prompting technique tutorial for a non-technical audience. @santu2023teler provide a general taxonomy of prompts that can be used to design prompts with specific properties to perform a wide range of complex tasks. @Bubeck2023SparksOA qualitatively experiment with a wide range of prompting methods on the early version of GPT-4 to understand its capabilities. @chu2023survey review Chain-of-Thought related prompting methods for reasoning. In earlier work, @Bommasani2021OnTO review and discuss opportunities and risks of foundation models broadly, and @dang2022prompt discuss prompting strategies for interactive creative applications that use prompting as a new paradigm for human interaction, with a particular focus on the user interface design that supports user prompting. As an addition to these existing surveys, our review aims to provide a more updated and formalized systematic review.

There is also a line of work that surveys prompting techniques for particular domains or downstream applications. @mesko2023prompt and @wang2023prompt offer recommended use cases and limitations of prompt engineering in the medical and healthcare domains. @heston2023prompt provide a review of prompt engineering for medical education use cases. @peskoff2023credible query ChatGPT and YouChat to assess domain coverage. @hua2024large use a GPT-4-automated approach to review LLMs in the mental health space. @wang2023review review prompt engineering and relevant models in the visual modality and @Yang2023TheDO provided a comprehensive list of qualitative analyses of multimodal prompting, particularly focusing on GPT-4V[^15]. @Durante2024AgentAS review multimodal interactions based on LLM embodied agents. @Ko2023large review literature on the adoption of Text-to-Image generation models for visual artists' creative works. @GUPTA2024100066 review GenAI through a topic modeling approach. @awais2023foundational review foundation models in vision, including various prompting techniques. @hou2023large perform a systematic review of prompt engineering techniques as they relate to software engineering. They use a systematic review technique developed by @Kitchenham2007guidelines, specifically for software engineering reviews. @wang2023software review the literature on software testing with large language models. @zhang2023critical review ChatGPT prompting performance on software engineering tasks such as automated program repair. @neagu2023llmseducation provide a systematic review on how prompt engineering can be leveraged in computer science education. @li2023survey review literature on the fairness of large language models. There are also surveys on related aspects such as hallucination of language models [huang2023survey], verifiability [liu2023evaluating], reasoning [qiao2022reasoning], augmentation [mialon2023augmented], and linguistic properties of prompts [leidinger2023language]. Different from these works, we perform our review targeting broad coverage and generally applicable prompting techniques. Finally, in terms of more general prior and concurrent surveys [liu2023pretrain; @sahoo2024systematic; @vatsal2024surveypromptengineeringmethods], this survey offers an update in a fast-moving field. In addition, we provide a starting point for taxonomic organization of prompting techniques and standardization of terminology. Moreover, unlike many works that claim to be systematic, we base our work in the widely used standard for systematic literature reviews---PRISMA [Page2021the].

# Conclusions {#sec:conclusion}

Generative AI is a novel technology, and broader understanding of models' capabilities and limitations remains limited. Natural language is a flexible, open-ended interface, with models having few obvious affordances. The use of Generative AI therefore inherits many of the standard challenges of linguistic communication---e.g., ambiguity, the role of context, the need for course correction---while at the same time adding the challenge of communicating with an entity whose "understanding" of language may not bear any substantial relationship to human understanding. Many of the techniques described here have been called "emergent", but it is perhaps more appropriate to say that they were *discovered*---the result of thorough experimentation, analogies from human reasoning, or pure serendipity.

The present work is an initial attempt to categorize the species of an unfamiliar territory. While we make every attempt to be comprehensive, there are sure to be gaps and redundancies. Our intention is to provide a taxonomy and terminology that cover a large number of existing prompt engineering techniques, and which can accommodate future methods. We discuss over 200 prompting techniques, frameworks built around them, and issues like safety and security that need to be kept in mind when using them. We also present two case studies in order to provide a clear sense of models' capabilities and what it is like to tackle a problem in practice. Last, our stance is primarily observational, and we make no claims to the validity of the presented techniques. The field is new, and evaluation is variable and unstandardized---even the most meticulous experimentation may suffer from unanticipated shortcomings, and model outputs themselves are sensitive to meaning-preserving changes in inputs. As a result, we encourage the reader to avoid taking any claims at face value and to recognize that techniques may not transfer to other models, problems, or datasets.

To those just beginning in prompt engineering, our recommendations resemble what one would recommend in any machine learning setting: understand the *problem* you are trying to solve (rather than just focusing on input/output and benchmark scores), and ensure the data and metrics you are working with constitute a good representation of that problem. It is better to start with simpler approaches first, and to remain skeptical of claims about method performance. To those already engaged in prompt engineering, we hope that our taxonomy will shed light on the relationships between existing techniques. To those developing new techniques, we encourage situating new methods within our taxonomy, as well as including ecologically valid case studies and illustrations of those techniques.

# Appendices

## Definitions of Prompting {#appx:definitions_of_prompting}

::: xltabular
\|p2cm\|X\|X\| Reference & Prompt & Prompt Engineering\
[mesko2023prompt] & & The practice of designing, refining, and implementing prompts or instructions that guide the output of LLMs to help in various tasks. It is essentially the practice of effectively interacting with AI systems to optimize their benefits.\
[chen2023unleashing] & the input of the model & the process of structuring input text for LLMs and is a technique integral to optimizing the efficacy of LLMs\
[santu2023teler] & refers to a textual input provided to the LLMs with the intention of guiding its output toward a specific task & involves crafting and revising the query or context in such a way that it elicits the desired response or behavior from LLMs\
[wang2023prompt] & & involves designing effective prompts to guide the pre-trained language model in downstream tasks.\
[wang2023review] & & the process of designing prompts that enable the model to adapt and generalize to different tasks. downstream tasks.\
[hou2023large] & manually predefined natural language instructions & the careful design of specialized prompts\
[wang2023software] & input of the LLMs & communicate with LLMs to steer its behavior for desired outcomes\

[white2023prompt] & Instructions given to an LLM to enforce rules, automate processes, and ensure specific qualities (and quantities) of generated output. Prompts are also a form of programming that can customize the outputs and interactions with an LLM.

A prompt is a set of instructions provided to an LLM that programs the LLM by customizing it and/or en- hancing or refining its capabilities & an increasingly important skill set needed to converse effectively with large language models (LLMs), such as ChatGPT

the means by which LLMs are programmed via prompts\
[heston2023prompt] & the input & structuring the input in a specialized manner\
[liu2023pretrain] & & choosing a proper prompt

the process of creating a prompting function $f_{prompt}(x)$ that results in the most effective performance on the downstream task.\
[hadi2023large] & the instructions provided to an LLM to make it follow specified rules, automation of processes and to ensure that the output generated is of a specific quality or quantity & refers to the designing and wording of prompts given to LLMs so as to get a desired response from them.\

[neagu2023llmseducation] & & entails various strate- gies, including explicit instruction, and implicit context \[21\]. Explicit instruction involves providing explicit guidance or constraints to the model through instructions, examples, or specifications. Implicit context leverages the model's under- standing of the preceding context to influence its response\
[dang2022prompt] & & the systematic practice of constructing prompts to improve the generated output of a generative model\
:::

## Extended Vocabulary {#appx:extended_vocabulary}

### Prompting Terms

##### Context Window

The context window is the space of tokens (for LLMs) which the model can process. It has a maximal length (the context length).

##### Priming

[Schulhoff_Learn_Prompting_2022] []{#priming label="priming"} refers to giving a model an initial prompt that lays out certain instructions for the rest of a conversation. This priming prompt might contains a role or other instructions on how to interact with the user. Priming can either be done in the system or user prompt (see below).

### Prompt Engineering Terms {#pe-terms}

##### Conversational Prompt Engineering

is Prompt Engineering *in colloquio*. That is, during the course of a conversation with a GenAI, a user may ask the GenAI to refine its output. In contrast, prompt engineering is often done by sending the GenAI a completely new prompt rather than continuing a conversation.

### Fine-Tuning Terms {#fine-tuning}

##### Prompt-Based Learning

[liu2023pretrain], also known as Prompt Learning [liu2023pretrain; @wang2023prompt] refers to the process of using prompting-related techniques. It often is used in the context of fine-tuning, especially fine-tuning prompts. Due to conflicting usage, we do not use this term.

##### Prompt Tuning

[Lester_2021] []{#prompt-tuning label="prompt-tuning"} refers to directly optimizing the weights of the prompt itself, usually through some form of gradient-based updates. It has also been referred to has Prompt Fine-Tuning. It should *not* be used to refer to discrete prompt engineering.

### Orthogonal Prompt Types {#orthogonal}

We now discuss terminology for high-level ways of classifying prompts.

#### Originator

##### User Prompt

This is the type of prompt that comes from the user. This is the most common form of prompting and is how prompts are usually delivered in consumer applications.

##### Assistant Prompt

This \"prompt\" is simply the output of the LLM itself. It can be considered a prompt (or part of one) when it is fed back into the model, for example as part of a conversation history with a user.

##### System Prompt

This prompt is used to give LLMs high level instructions for interacting with users. Not all models have this.

#### Hard vs Soft Prompts {#hard-v-soft}

##### Hard (discrete) Prompt {#discrete-prompt}

These prompts only contain tokens that directly correspond to words in the LLM vocabulary.

##### Soft (continuous) Prompt {#continuous-prompt}

These prompts contain tokens that may not correspond to any word in the vocabulary [Lester_2021; @wang2023review]. Soft prompts can be used when fine-tuning is desired, but modifying the weights of the full model is prohibitively expensive. Thus, a frozen model can be used while allowing gradients to flow through the prompt tokens.

```latex
$$\text{Hard Prompts} \subseteq \text{Soft Prompts}$$
```

#### Prediction Styles {#prediction-style}

In LLMs, a prediction style is the format in which it predicts the next token. There are two common formats for this in prompting research. We do not discuss non-text prediction styles.

##### Cloze

In Cloze prompts, the token(s) to be predicted are presented as \"slots to fill\", usually somewhere in the middle of the prompt [liu2023pretrain]. This is usually the case for earlier transformer models such as BERT [bert].

##### Prefix

In Prefix prompts, the token to be predicted is at the end of the prompt [liu2023pretrain]. This is usually the case with modern GPT-style models [radford2019language].

## Datasheet {#appx:datasheet}

We present a datasheet [Gebru_2021] with more information about the associated paper dataset, which is hosted on [HuggingFace](https://huggingface.co/datasets/PromptSystematicReview/Prompt_Systematic_Review_Dataset).

### Motivation

**For what purpose was the dataset created? Was there a specific task in mind? Was there a specific gap that needed to be filled? Please provide a description.**\
This dataset was created to gather existing literature on prompt engineering in order to analyze all current hard prefix prompting techniques.

**Who created the dataset (e.g., which team, research group) and on behalf of which entity (e.g., company, institution, organization)?**\
This research was associated with the University of Maryland, Learn Prompting, and sponsored by OpenAI, but not created on the behalf of any particular organization.

**Who funded the creation of the dataset? If there is an associated grant, please provide the name of the grantor and the grant name and number.**\
OpenAI contributed \$10,000 in credits for their API.

### Composition {#appx:Composition}

**What do the instances that comprise the dataset represent (e.g., documents, photos, people, countries)? Are there multiple types of instances (e.g., movies, users, and ratings; people and interactions between them; nodes and edges)? Please provide a description.**\
The dataset contains 1,565 research papers in PDF format. Any duplicate papers were removed automatically, though some could exist.

**What data does each instance consist of? "Raw" data (e.g., unprocessed text or images) or features? In either case, please provide a description.**\
Each data instance is a research paper as a PDF.

**Is there a label or target associated with each instance? If so, please provide a description.**\
No

**Is any information missing from individual instances? If so, please provide a description, explaining why this information is missing (e.g., because it was unavailable). This does not include intentionally removed information, but might include, e.g., redacted text.**\
No.

**Are there any errors, sources of noise, or redundancies in the dataset? If so, please provide a description.**\
The papers were gathered in a semi-automated process which introduced the possibility of irrelevant papers being collected and relevant papers not being collected. There were manual reviews done for both possible errors to mitigate these errors.

**Is the dataset self-contained, or does it link to or otherwise rely on external resources (e.g., websites, tweets, other datasets)?**\
It is self-contained.

**Does the dataset contain data that might be considered confidential (e.g., data that is protected by legal privilege or by doctor--patient confidentiality, data that includes the content of individuals' non-public communications)? If so, please provide a description.**\
No.

**Does the dataset contain data that, if viewed directly, might be offensive, insulting, threatening, or might otherwise cause anxiety? If so, please describe why.**\
The dataset contains some papers on prompt injection. These papers may contain offensive content including racism and sexism.

### Collection Process {#appx:Collection-Process}

**How was the data associated with each instance acquired?**\
The dataset was compiled from Arxiv, Semantic Scholar, and ACL.

**What mechanisms or procedures were used to collect the data?**\
We wrote scripts to automatically query the APIs of Arxiv and Semantic Scholar.

**Over what timeframe was the data collected?**\
The dataset was curated the duration of the research paper, primarily in February of 2024.

**Were any ethical review processes conducted?**\
No.

### Preprocessing/ Cleaning/ Labeling

**Was any preprocessing/cleaning/labeling of the data done?**\
After collecting data from different sources, we removed duplicate papers and did a manual and semi-automated review of papers to ensure they were all relevant.

**Was the "raw" data saved in addition to the preprocessed/cleaned/labeled data?**\
No, we do not anticipate the use of our preprocessed data. However, raw data can be recovered from the links we store.

**Is the software that was used to preprocess/clean/label the data available?**\
It is contained within our code repository on [Github](https://github.com/trigaten/Prompt_Systematic_Review/tree/main/src/prompt_systematic_review/get_papers).

### Uses

**Has the dataset been used for any tasks already?**\
No.

**Is there a repository that links to any or all papers or systems that use the dataset?**\
[Yes](https://huggingface.co/datasets/PromptSystematicReview/Prompt_Systematic_Review_Dataset).

**Is there anything about the composition of the dataset or the way it was collected and preprocessed/cleaned/labeled that might impact future uses?**\
All of the papers we collected were written in English. It is possible some papers were not included due to a translation not being available.

**Are there tasks for which the dataset should not be used?**\
No.

### Distribution

**Will the dataset be distributed to third parties outside of the entity on behalf of which the dataset was created?**\
No.

### Maintenance

**Who will be supporting/hosting/maintaining the dataset?**\
Our team will continue maintenance.

**How can the owner/curator/manager of the dataset be contacted?**\
Please email us at sanderschulhoff@gmail.com

**Is there an erratum?**\
No.

**If others want to extend/augment/build on/contribute to the dataset, is there a mechanism for them to do so?**\
Yes, anyone is free to use/modify the data.

## Keywords {#appx:keywords}

Here are the keywords we used for search.

- jailbreak prompt

- prompt an llm

- prompt a large language model

- prompt injection

- prompt optimization

- prompt engineering

- few-shot learning

- few shot learning

- prompt-based methods

- prompt based methods

- prompting-based methods

- prompting based methods

- few-shot prompt

- few shot prompt

- one-shot prompt

- one shot prompt

- few-shot prompting

- few shot prompting

- one-shot prompting

- one shot prompting

- prompting techniques

- prompt engineering techniques

- llm prompting

- large language model prompting

- 0-shot prompt

- 0 shot prompt

- zero-shot prompt

- many-shot prompt

- zero-shot prompting

- many-shot prompting

- in-context learning

- in context learning

- transformer model prompts

- prompt-based transfer learning

- nlp prompting strategies

- llm interpretability via prompts

- curriculum learning with prompts

- feedback loops in llm prompting

- human-in-the-loop prompting

- token-efficient prompting

- multimodal prompting

- instruction prompting

- prompt templating

- prompt template

## Prompt for Systematic Literature Review {#sec:sys_rev_prompt}

Please find the prompt we used [here](https://github.com/trigaten/The_Prompt_Report/blob/fcd07ac5c512bb6d166304d9b43784eccb9210eb/src/prompt_systematic_review/automated_review.py#L31). We present it in text in this document, but note that you should use the version in our [codebase](https://github.com/trigaten/The_Prompt_Report/blob/fcd07ac5c512bb6d166304d9b43784eccb9210eb/src/prompt_systematic_review/automated_review.py#L31) rather than copy and paste this.

#### We used the following system prompt {#we-used-the-following-system-prompt .unnumbered}

:

You are a lab assistant, helping with a systematic review on prompt engineering. You've been asked to rate the relevance of a paper to the topic of prompt engineering. To be clear, this review will strictly cover hard prefix prompts. For clarification: Hard prompts have tokens that correspond directly to words in the vocab. For example, you could make up a new token by adding two together. This would no longer correspond to any word in the vocabulary, and would be a soft prompt Prefix prompts are prompts used for most modern transformers, where the model predicts the words after this prompt. In earlier models, such as BERT, models could predict words (e.g. \<MASK\>) in the middle of the prompt. Your job is to be able to tell whether a paper is related to (or simply contains) hard prefix prompting or prompt engineering. Please note that a paper might not spell out that it is using \"hard prefix\" prompting and so it might just say prompting. In this case, you should still rate it as relevant to the topic of prompt engineering. Please also note, that a paper that focuses on training a model as opposed to post-training prompting techniques is considered irrelevant. Provide a response in JSON format with two fields: 'reasoning' (a single sentence that justifies your reasoning) and 'rating' (a string that is one of the following categories: 'highly relevant', 'somewhat relevant', 'neutrally relevant', 'somewhat irrelevant', 'highly irrelevant') indicating relevance to the topic of prompt engineering)

#### Then, we used this user prompt template to input information for each paper {#then-we-used-this-user-prompt-template-to-input-information-for-each-paper .unnumbered}

:

Title: '{title}', Abstract: '{abstract}'. Rate its relevance to the topic of prompt engineering as one of the following categories: 'highly relevant', 'somewhat relevant', 'neutrally relevant', 'somewhat irrelevant', 'highly irrelevant', and provide text from the abstract that justifies your reasoning

## Evaluation Table {#appx:evaluation}

## Entrapment Prompting Process {#appx:entrap_prompting}

This section contains the thought process of our prompt engineer as he developed the prompt.

### Exploration

- First did a bit of dataset exploration, looking at length/label distribution, then chose entrapment to start with.

- Checked if gpt-1106-preview understood entrapment, by asking it to define the term WRT SCS. It did not.

### Getting a Label

- Showed it the definition of entrapment in the system prompt and asked it to label a data point, but it responded saying I should seek mental health support.

- I put the instructions in the user prompt, but get a similar response.

- Appending \"Is this entrapment? Yes or no\" got it to actually respond with a label.

- I gave it a reject example, but it labeled it as accept, and also sometimes gives emotional responses about getting help.

- Using 10-shot prompting, it still gives the get help responses.

- I tried removing the definition, got the same problem. It seems that it doesn't like \"accept\"/\"reject\" as labels.

- I added back the definition, changed labels to entrapment/not entrapment, it often says \"not enough info to determine\".

- I switched to GPT-4-32K, which gave one word responses and correctly predicted a reject and an accept datapoint.

### Varying Prompting Techniques

- Tested 0-shot with context.

- 10-shot with context, showed improvement.

- Taking first failing instance into playground. (12th in train file)

- Tried doing 'A: Let's go step by step and figure this out: \", output \"A: Yes\"

- Did \"A: Let's go step by step and figure this out: \", OUTPUT:

  ::: pbox
  The individual in this post is expressing feelings of hopelessness, loneliness, and despair. They mention a significant loss (their mother) and a subsequent decline in their mental health, turning to alcohol as a coping mechanism. They also mention financial struggles and the possibility of becoming homeless. They express feelings of guilt and shame about their situation and compare themselves negatively to their friends and family. Most concerning is their detailed plan for suicide, involving sleeping pills and alcohol. They also mention considering stepping in front of a car. Given these factors, the label for this post would be \"Yes\" for expressing feelings of entrapment.
  :::

- \"A: Before predicting a label, let's go step by step and write out your thought process. Use the items in the definition of entrapment to support your conclusion.\", OUTPUT:

  ::: pbox
  Before predicting a label, let's go step by step and write out your thought process. Use the items in the definition of entrapment to support your conclusion.
  :::

- Began discussing with the AI \"they don't ever say they feel trapped or that there is no way out, how did u get that idea?\", OUTPUT:

  ::: pbox
  The individual doesn't explicitly state that they feel trapped or that there is no way out, but their narrative suggests a sense of entrapment. They mention that they are facing eviction, struggling with debt, and dealing with a decrease in income. They also express a sense of hopelessness and despair, and contemplate suicide as a potential solution to their problems. These elements suggest a feeling of being trapped in their current circumstances with no apparent way out. However, it's important to note that this interpretation is based on the information provided in the post and the individual's expressed feelings and thoughts.
  :::

- Asked it to help reformulate instructions to make explicitness more clearly needed, still predicts entrapment.

- Added \"ENTRAPMENT MUST BE EXPLICIT, NOT IMPLICIT.\" to instruction at top after definitions (no CoT inducer)

- Also tried with previous CoT inducer, still says entrapment in a hard to parse out way.

- Added \"If the person does not explicitly say they feel trapped, this doesn't count as entrapment.\" (no CoT), still entrapment.

- Talking to AI, it thinks \"Today I found out I have 10 days to vacate my apartment or I'll be formally evicted. I'm 2 months behind on my rent due to a bad time where I got demoted at work and rent from making roughly \$1000 ever 2 weeks to around \$450. If I get evicted, I'll probably be homeless\" is feeling trapped/stuck.

- Tried \"Before stating a label, write out reasoning using the grid above about why this may/may not be entrapment:\", still thinks entrapment.

- paste in email: \[REDACTED\] above definition of entrapment

- remove shots, says \"Entrapment\"

- add this after def: IMPORTANT: Only label the post as entrapment if they explicitly say that they feel trapped., says \"Yes\"

- In the prompt, gave it CoT reasoning. (18.txt), and tried with the next wrongly labeled one (15), (full prompt, 19.txt)

- Tested this on everything except first 20, did pretty well

- Tried removing email, performance dropped of a cliff

- At this point, I am thinking that giving examples with reasoning helps (obviously)

- Tried to add 10 shots in for free, before the last one with reasoning, bad results

#### AutoCoT

- Develop dataset using this prompt (22.txt). Then ask it \"Why?\". If it disagrees, I say \"It is actually not entrapment, please explain why.\" (accidentally duplicated email 23.txt)

- Just for fun, tried 0 shot full context (had to adjust verbalizer)

- tried this with special verbalizer which catches \"This post does not meet the criteria for Entrapment.\"

- Tested my generated data, beat 0.5 F1

- Doing 10 more exemplars w autocot. Sometimes responds immediately with reasoning like \"This post does not meet the criteria for Entrapment as the individual does not explicitly express feelings of being trapped or hopeless.\", so just use that if so. Sometimes get refusal \"I'm really sorry to hear that you're feeling this way, but I'm unable to provide the help that you need. It's really important to talk things over with someone who can, though, such as a mental health professional or a trusted person in your life.\", just ask \"Explain why it is not entrapment.\" after if so.

- performance didnt really improve, realized about 11% are getting -1, meaning not extracted properly. Retrying with full words \"Question\" instead of Q, also for reasoning and answer.

- this led to higher inability to parse, at about 16%.

#### Developing Answer Extraction

- put first failing to parse one in (22), and developed a prompt for it.

- did worse: (0.42857142857142855, 0.5051546391752577, 0.8571428571428571, 0.2857142857142857)

- only using extracted label if have -1 helps slightly to (0.48, 0.61, 0.8571428571428571, 0.3333333333333333)

- going back to best performing prompt--10 QRA shot, and performing extraction with any -1s, doesnt help other than gently boosting accuracy, perhaps when it doesnt answer

#### Iterating on Email

- tried best perf, with no email

- tried with deduped email, worse results

- noticed that ones its unsure about often contained 1 labels that should be 0, so trying to \"recover\" these doesnt help

- try moving around exemplar order, performing extraction, didnt help

- triplicated email, didnt help

## Formally Defining a Prompt

\"Prompt\" is a widely used term, but uses and definitions differ widely across research. As a result, it is difficult to create a formal, mathematical definition for a prompt. In this section, we outline some formalisms for prompt engineering.

##### As a conditioning Mechanism.

@qiao2022reasoning present the following definition, which involves the prompt $\mathcal{T}$ and a question $\mathcal{Q}$ as conditioning mechanisms on predicting the next token. Note that they appear to use @brown2020language's original definition of prompt, which refers to the non-question part of the prompt (e.g. few-shot exemplars, instructions).

```latex
$$\begin{align}
p(\mathcal{A} \mid \mathcal{T},\mathcal{Q})=\prod_{i=1}^{|\mathcal{A}|} p_{\rm LM} \left ( a_i \mid \mathcal{T},\mathcal{Q},a_{1:i-1} \right)\label{eq:prompt_cond}
\end{align}$$
```

Here, the prompt and question condition the pre-trained LLM $p_{\rm LM}$. The $a_{1:i-1}$ are previously generated answer tokens and $\mathcal{A}$ a complete answer.

##### Templating.

The above formalization does not include the notion of maximizing a scoring or utility function (e.g. accuracy on a dataset), which prompts are often designed to do. Additionally, prompt engineers often seek to design prompt template rather than prompts. Here, we reformulate [\[eq:prompt_cond\]](#eq:prompt_cond){reference-type="ref+label" reference="eq:prompt_cond"} to include the prompt template:

```latex
$$\begin{align}
p(\mathcal{A} \mid \mathcal{T}(x^*))=\prod_{i=1}^{|\mathcal{A}|} p_{\rm LM} \left ( a_i \mid \mathcal{T}(x^*),a_{1:i-1} \right)
\end{align}$$
```

We replace $\mathcal{Q}$ with $x^* \in \mathcal{D}_{\text{eval}}$, an item from a dataset (e.g., evaluation data). Additionally, we replace $\mathcal{Q}$ on the right side with $\mathcal{T}(x)$. $\mathcal{T}(\cdot)$ is a prompt template: a function that accepts some item as input then returns a prompt that is used to condition the model.

##### Few-Shot Prompting.

Often, an important part of the prompting process is the use of few-shot exemplars. $\mathcal{D}_{train}$ is training data (used to build the prompt) and $\mathcal{X}$ is a test set for evaluation.

```latex
$$\begin{align}
\mathcal{D}_{\text{train}} &= \{(x_1, y_1), (x_2, y_2), ..., (x_n, y_n) \} \\
\mathcal{X} &= \{x^*_{1}, x^*_2, ..., x^*_{m}\}
\end{align}$$
```

In the few-shot setting, the prompt template function $\mathcal{T}(\cdot)$ also takes as input one or more training samples $\mathcal{X} = \{(x_i, y_i)\}_1^n \subset \mathcal{D}_{\text{train}}$

```latex
$$\begin{align}
p\bigl(\mathcal{A} \mid \mathcal{T}\left(\mathcal{X},\ x^*\right)\bigr)=\prod_{i=1}^{|\mathcal{A}|} p_{\rm LM} \left ( a_i \mid \mathcal{T}\left(\mathcal{X},\ x^*\right),a_{1:i-1} \right)
\end{align}$$
```

##### Optimization.

As mentioned, it is often desirable to speak about improving prompts (prompt templates, that is) with respect to a scoring function, usually defined with respect to a dataset.

```latex
$$\begin{equation}
\mathcal{T}^* = \underset{\mathcal{T}}{\mathrm{argmax}} \; \mathbb{E}_{x_i, y_i \sim \mathcal{D}} \left[ S \left( p_{\text{LM}}(\mathcal{A}|\mathcal{T}(x_i)), y_i \right) \right]
\end{equation}$$
```

In this definition, we are evaluating over a dataset $\mathcal{D}$ with respect to the scoring function $S(\cdot)$. $S(\cdot)$ evaluates the output $\mathcal{A}$, generated by the LLM conditioned on the prompt $\mathcal{T(x_i)}$. $y_i$ are labeled outputs that can be used by $S$.

In some cases, there may not be any labeled data $y_i$, and $S(\cdot)$ may be reference-free.

##### Other considerations.

These formalisms could be adapted to cater to CoT, retrieval systems, and more. Here we describe a simple setup which is most descriptive of the prompting process without adding too much complexity.

We also draw attention to the lesser known concept of answer engineering. $E(\mathcal{A})$ is a transformation function over the raw LLM output that allows it to be compared to the ground truth.

```latex
$$\begin{align}
\mathcal{A} &\sim p_{\text{LM}}(\mathcal{A} \mid \mathcal{T}(x_i), y_i ) \\
\mathcal{T}^* &= \underset{\mathcal{T}, E}{\mathrm{argmax}} \; \mathbb{E}_{x_i, y_i \sim \mathcal{D}} \left[ S \left( E(\mathcal{A}), y_i \right) \right]
\end{align}$$
```

## In-Context Learning Definitions Disambiguation {#section:icl_disambig}

@brown2020language seemingly offer two different definitions for ICL. All bolding in this section is our own.

> Recent work \[RWC+19\] attempts to do this via what we call "in-context learning", using the text input of a pretrained language model as a form of task specification: the model is **conditioned on a natural language instruction and/or a few demonstrations of the task** and is then expected to complete further instances of the task simply by predicting what comes next.

However, they later appear to define it as few-shot only:

> For each task, we evaluate GPT-3 under 3 conditions: (a) **"few-shot learning", or in-context learning where we allow as many demonstrations as will fit into the model's context window** (typically 10 to 100), (b) "one-shot learning", where we allow only one demonstration, and (c) "zero-shot" learning, where no demonstrations are allowed and only an instruction in natural language is given to the model.

However, they include this image that clarifies the matter:

<figure id="fig:brown-icl" data-latex-placement="h">
[IMAGE: eval_strategies.png]
<figcaption>ICL from <span class="citation" data-cites="brown2020language"></span>.</figcaption>
</figure>

Additionally, they explicitly state that ICL does not necessarily involve learning new tasks.

> To avoid this confusion, we use the term "meta-learning" to capture the inner-loop / outer-loop structure of the general method, and the term "in context-learning" to refer to the inner loop of meta-learning. We further specialize the description to "zero-shot", "one-shot", or "few-shot" depending on how many demonstrations are provided at inference time. **These terms are intended to remain agnostic on the question of whether the model learns new tasks from scratch at inference time or simply recognizes patterns seen during training** -- this is an important issue which we discuss later in the paper, but "meta-learning" is intended to encompass both possibilities, and simply describes the inner-outer loop structure.

We use @brown2020language's broad definition, though note that practitioners often use ICL to refer to situations in which the model appears to be learning new tasks from the prompt. Our definition differs from @dong2023survey's formal definition, even though it is also derived from [brown2020language].

## Contributions

The following are the contributions made by the team members in various sections of this paper. Most authors conducted reviews of other sections as well.

### Advisors {#advisors .unnumbered}

- **Denis Peskoff:** Assisted with paper organization and final review.

- **Alexander Hoyle:** Provided guidance on writing, meta-analysis approach, and ran automated baselines for case study.

- **Shyamal Anadkat:** Assisted with the overall review of the paper and the etymology and definitions.

- **Jules White:** Built trees for technique taxonomies.

- **Marine Carpaut:** Framed, reviewed and suggested papers for the multilingual section.

- **Phillip Resnik:** Principal Investigator

### SCS Labeling {#scs-labeling .unnumbered}

- **Megan L. Rogers, Inna Goncearenco, Giuseppe Sarli, Igor Galynker:** reviewed and gave advice for this section.

### Benchmarking and Agents {#benchmarking-and-agents .unnumbered}

- **Konstantine Kahadze:** Team leader for the Benchmarking section; managed MMLU benchmarking codebase, contributed to Security and Meta Analysis.

- **Ashay Srivastava:** Team leader for the Agents section, reviewed papers for human review, worked on the tool use agents section. Worked on the compilation of contributions.

- **Hevander Da Costa**: Contributed to the Benchmarking section and Meta Review datasets list, reviewed literature on LLM code generation and prompting techniques. Added literature review content to the Agents section.

- **Feileen Li:** Worked on the tool use agents section, assisted with the human paper review.

### Alignment and Security {#alignment-and-security .unnumbered}

- **Nishant Balepur:** Team leader for the alignment section, helped with high-level discussions in benchmarking, and reviewed drafts.

- **Sevien Schulhoff:** Team leader for the security section and contributed to the benchmarking section.

### Related Works and Section Contributions {#related-works-and-section-contributions .unnumbered}

- **Chenglei Si:** Suggested related works and edited section 2.2 and section 7.

- **Pranav Sandeep Dulepet:** Contributed definitions for section 2 and worked on segmentation and object detection in the multimodal section.

- **HyoJung Han:** Contributed to the Multimodal section, especially the speech+text part, and wrote the audio prompting section.

- **Hudson Tao:** Authored sections on image, video, and 3D within multimodal, reviewed papers for human review; maintained GitHub codebase, and built the project website.

- **Amanda Liu:** Authored taxonomic ontology sections, conducted background research for introduction and related work, developed code pipelines for meta-analysis graphs

- **Sweta Agrawal:** Team lead for evaluation section.

- **Saurav Vidyadhara:** Assisted with general review and revising taxonomy trees.

- **Chau Pham:** Assisted with meta review, including automated analysis of topics.

### Multilingual Prompting and Meta Analysis {#multilingual-prompting-and-meta-analysis .unnumbered}

- **Dayeon Ki:** Led the Multilingual prompting section, conducted review on related papers, and wrote Section 3.1.

- **Yinheng Li:** Worked on section 2.2 text-based techniques, reviewed techniques, and contributed to drafting figure 2.2.

- **Saloni Gupta:** Wrote tests for paper compilation, helped set up paper pipeline, and worked on the code diagram and grammar for the paper.

- **Gerson Kroiz:** Involved with section 1.1 and defining a prompt.

- **Aayush Gupta:** Contributed to the Meta Analysis, compiling papers, and generating visualization graphs.

- **Michael Ilie:** Co-Lead Author, managed codebase, ran experiments, collected data, and helped with various sections including the PRISMA review figure and the SCS prompting case study.

- **Sander Schulhoff:** Lead Author

[^1]: https://huggingface.co/datasets/PromptSystematicReview/Prompt_Systematic_Review_Dataset

[^2]: Using gpt-4-1106-preview

[^3]: We do not cover the notion of independently-acting AI, i.e. systems that in any sense have their own goals

[^4]: This ability may be considered a tool (i.e. code interpreter)

[^5]: This section does not describe how to benchmark LLMs, but rather how to use them as evaluators.

[^6]: Disambiguation: there is no relation to making a forward pass with multiple prompts in parallel. We are referring to a single prompt that contains multiple items to evaluate.

[^7]: For example, a practitioner may use the prompt template "Detect all instances where the user's input is harmful: {INPUT}" in an attempt to prevent adversarial inputs, but this subtly makes the false presupposition that the user's input is actually harmful. Thus, due to sycophancy, the LLM may be inclined to classify the user's output as harmful.

[^8]: We excluded human_sexuality, since gpt-3.5-turbo refused to answer these questions.

[^9]: The former term more explicitly emphasizes the frantic and desperate action required to escape an unbearable life situation. However, the term *entrapment* is briefer and used widely so we adopt it here.

[^10]: Disclosure: that expert is also the lead author of this paper.

[^11]: Precision is also known as positive predictive value, and recall is also known as true positive rate or sensitivity. Although F1 is often used in computional system evaluations as a single figure of merit, we note that in this problem space its even weighting of precision and recall is probably not appropriate. We discuss this further below.

[^12]: Temperature and top-p are configuration hyperparameters that control randomness of the output [Schulhoff_Learn_Prompting_2022].

[^13]: Here and for the remainder of the case study, we judge "best" by F1, and we report on the current prompt under discussion relative to the best performing previous prompt.

[^14]: We are trying to avoid misleading language like "the LLM generated an explanation of its reasoning". LLMs do not have access to their own internal processes, and therefore they cannot "explain their reasoning" in the usual sense. An LLM generating an "explanation" is producing description of potential reasoning steps in getting to the output that could be true, but also may not be accurate at all.

[^15]: <https://openai.com/research/gpt-4v-system-card>
