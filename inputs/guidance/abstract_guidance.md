## I. Cross-Domain Universal Underlying Patterns of the Abstract Module

### 1. Logical Framework Breakdown: The Narrative Chain
Analysis of papers such as *Nature* (AlphaFold, DNA circuits), *The Lancet* (Autism health), and *PRL* (Gravitational waves) reveals that top-tier abstracts strictly follow an **"Inverted Pyramid + Linear Progression"** logic:

| Order | Functional Module | Proportion | Core Writing Goal | Typical Sentence Patterns (Based on Sources) |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Background/Gap** | 10-15% | Establish the grand significance of the field or identify a critical bottleneck in current technology/knowledge. | "A major challenge for... is to find..." (*Nature* 2025); "Deep generative models have had less of an impact, due to..." (*GANs*) |
| **2** | **Approach/Strategy** | 20-25% | Briefly describe the core innovation (new model, mechanism, or cohort), emphasizing "how" the problem is solved. | "Here we show that..." (*Nature*); "We propose a new framework..." (*GANs*); "In this study, we have made inferences..." (*Lancet*) |
| **3** | **Key Results** | 40-50% | **The Soul of the Abstract**. Support arguments with specific data, performance metrics, or qualitative findings to demonstrate significance. | "achieves 3.57% error..." (*ResNet*); "scored 77%... against..." (*AlphaGo*); "LoRA matches or exceeds the fine-tuning baseline..." (*LoRA*) |
| **4** | **Implication** | 15-20% | Articulate the broad impact, generalizability, or driving force for future developments in the field. | "Our strategy enables diverse systems to be powered by..." (*Nature* 2025); "This result won the 1st place..." (*ResNet*) |

### 2. Core Functional Module Division
*   **Essential Information**:
    *   **Problem Definition**: Must clearly state the specific problem being addressed (e.g., protein structure prediction, healthcare access for autistic adults).
    *   **Quantitative Evidence**: Top-tier abstracts reject vague adjectives (e.g., "good performance"). They must include specific numbers (e.g., "up to 10,000× reduction", "mAP of 55.7%").
    *   **Comparison Baseline**: Clearly state what is being outperformed (e.g., "outperforms... by a substantial margin", "matches or exceeds full fine-tuning").
*   **Absolute Taboos**:
    *   **Citations**: Reference numbers are strictly prohibited in abstracts.
    *   **Undefined Abbreviations**: Unless universal (e.g., DNA, AI), abbreviations should be defined upon first use. However, in very short abstracts, *Nature* series tend to use common terms directly or avoid obscure abbreviations.
    *   **Future Plans**: Phrases like "Future work will..." are forbidden. The abstract should only state completed, definite achievements.

### 3. General Language and Narrative Norms
*   **Tense Selection**:
    *   **Background/Truths**: Simple Present ("Metabolism enables life...", "Deep networks naturally integrate...").
    *   **Current Study Actions**: Simple Present ("Here we show...", "We propose...") or Present Perfect ("We have made inferences..."), emphasizing current validity.
    *   **Specific Experimental Results**: Simple Past ("achieved", "scored", "observed"), describing findings from specific experiments.
*   **Voice Preference**:
    *   **Active Voice Dominant**: Enhances strength and clarity. E.g., "*Nature* 2025: Here **we show** that heat can restore...", "*GANs*: **We propose** a new framework".
    *   **Passive Voice Secondary**: Used only to emphasize the object over the actor, or for objective description in methods.
*   **Sentence Length**:
    *   Adopt a **mix of long and short sentences**. Background sentences can be slightly longer to set context; result sentences must be compact and powerful. Average sentence length should be controlled at 20-25 words, avoiding complex clause stacking exceeding 40 words.

---

## II. Differentiated Writing Patterns by Research Type

### 1. Observational Cohort Studies (Public Health/Clinical Direction)
*Representative Sources: The Lancet (Autism health), J. Technol. Behav. Sci. (Social media)*

*   **Exclusive Norms**:
    *   **Population Definition Upfront**: The target population must be clearly defined in the methods section (e.g., "autistic and matched comparison participants", "n=538 adults").
    *   **Data Rigor**: Statistical significance, confidence intervals, or effect sizes must be mentioned (often simplified in abstracts to "significant differences", "higher rates").
    *   **Hinting at Limitations**: Some medical top journals (like *The Lancet*) allow a brief mention of inferential limitations at the end of the abstract (e.g., "Based on the present findings, we cannot tease apart..."), reflecting scientific prudence.
*   **Exclusive Sentence Patterns**:
    *   "The key limitation of the study is that..." (Used in Discussion, often converted to cautious conclusions in abstracts).
    *   "Participants were asked to self-report..." (Method description).
    *   "Scores range from... with higher scores indicating..." (Variable definition).

### 2. Experimental Basic Research (Synthetic Biology/Computational Science/AI Direction)
*Representative Sources: Nature (AlphaFold, DNA circuits), ResNet, GANs, LoRA, Transformer*

*   **Exclusive Norms**:
    *   **SOTA Orientation**: Emphasize breaking records or surpassing State-of-the-Art methods right from the start.
    *   **Mechanism Brief**: Summarize the core technical principle in one sentence (e.g., "residual learning framework", "adversarial process", "low-rank adaptation").
    *   **Generalizability Statement**: Emphasize that the method is not only applicable to the current task but has broad transferability (e.g., "generally applicable to any neural networks", "diverse systems").
*   **Exclusive Sentence Patterns**:
    *   "We present a [Method Name] to ease the training of..."
    *   "Experiments demonstrate the potential of the framework through..."
    *   "Our approach gave state-of-the-art results in [Number] of [Total] tasks..."

### 3. Core Writing Differences Between the Two Types

| Dimension | Observational/Clinical Research | Experimental/Computational Research |
| :--- | :--- | :--- |
| **Core Focus** | **Association & Authenticity**: Emphasize sample representativeness, statistical associations, and clinical significance. | **Performance & Innovation**: Emphasize algorithmic efficiency, accuracy improvement, and architectural innovation. |
| **Result Expression** | Tends to use "associated with", "higher/lower rates", "inferences about". | Tends to use "outperforms", "achieves", "reduces error by", "dominates". |
| **Conclusion Sublimation** | Focuses on implications for public policy, clinical practice, or disease understanding. | Focuses on breakthroughs in technical bottlenecks and universality of future applications. |
| **Tone Style** | Cautious, objective, reserved (Cautious). | Confident, decisive, emphasizing breakthroughs (Assertive). |

---

## III. Reusable Sentence Template Library

### 1. General Standard Sentences by Functional Module

| Functional Module | English Standard Template | Chinese Meaning | Applicable Scenario/Replaceable Parts | Voice Norm |
| :--- | :--- | :--- | :--- | :--- |
| **Background/Gap** | "A major challenge for [Field] is to [Problem]." | A major challenge for [Field] is to [Problem]. | Replace Field and Problem | Active |
| | "Despite extensive efforts, we still lack [Solution/Resource]." | Despite extensive efforts, we still lack [Solution/Resource]. | Emphasizing existing research gaps | Active |
| **Method/Proposal** | "Here we show that [Mechanism] can [Action]." | Here we show that [Mechanism] can [Action]. | *Nature* style, emphasizing discovery | Active |
| | "We propose a new [Framework/Method] that [Function]." | We propose a new [Framework/Method] that [Function]. | Standard opening for CS/AI papers | Active |
| **Results/Performance** | "[Method] achieves [Metric] on [Dataset], outperforming [Baseline]." | [Method] achieves [Metric] on [Dataset], outperforming [Baseline]. | Must fill in specific numbers | Active |
| | "Experiments demonstrate that [Method] matches/exceeds [Benchmark]." | Experiments demonstrate that [Method] matches/exceeds [Benchmark]. | Emphasizing competitiveness | Active |
| **Conclusion/Impact** | "Our strategy enables [Applications] without [Limitation]." | Our strategy enables [Applications] without [Limitation]. | Emphasizing advantages and prospects | Active |
| | "This work provides a foundation for [Future Direction]." | This work provides a foundation for [Future Direction]. | Macro sublimation | Active |

### 2. Exclusive Sentence Templates by Research Type

*   **Clinical/Observational**:
    *   "In this [Study Type], we analyzed data from [Population] to investigate [Variable]."
    *   "We observed significant differences in [Outcome] between [Group A] and [Group B]."
    *   "These findings suggest that [Implication for Practice]."
*   **Computational/Experimental**:
    *   "By leveraging [Technique], we reduce [Cost/Time] by [Factor] while maintaining [Quality]."
    *   "Unlike previous approaches that require [Constraint], our method [Advantage]."
    *   "Scaling laws indicate that performance follows a [Trend] with [Resource]."

### 3. Rigorous Wording Norms for Results and Conclusions

*   **Prohibited List of Absolute Statements**:
    *   ❌ "proves" → ✅ "demonstrates", "suggests", "indicates"
    *   ❌ "perfect", "flawless" → ✅ "highly accurate", "robust"
    *   ❌ "first ever" (unless absolutely certain) → ✅ "to our knowledge, the first..."
*   **Compliant Expression Paradigms**:
    *   **Comparatives**: Use "substantial margin", "consistent improvement", "comparable to".
    *   **Causal Inference**: Use "partly from", "inferences about", "linked to" instead of absolute "caused by" (unless it is a randomized controlled trial with solid evidence).
