
## I. Cross-Domain Universal Underlying Logic and Framework Patterns

### 1. Narrative Logic Chain Breakdown: The Evidence Hierarchy

Top-tier Results sections universally follow a **"Hierarchical + Logical Flow"** structure, moving from primary findings to supporting evidence. The structure aligns with the hypotheses established in the Introduction and the methods defined in the Methods section:

| Order | Functional Module | Proportion | Core Writing Goal | Typical Content |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Participant/Subject Flow & Baseline** | 10-15% | Establish the study population and confirm comparability. | Recruitment numbers, exclusions, demographic tables, baseline characteristics. |
| **2** | **Primary Outcome/Main Finding** | 40-50% | Directly answer the primary research question/hypothesis. | Main effect sizes, key performance metrics, primary statistical tests. |
| **3** | **Secondary Outcomes/Supporting Evidence** | 20-25% | Provide additional context or corroborating data. | Secondary endpoints, complementary experiments, additional metrics. |
| **4** | **Subgroup/Sensitivity Analyses** | 15-20% | Demonstrate robustness and explore heterogeneity. | Stratified analyses, robustness checks, ablation studies (CS). |
| **5** | **Safety/Adverse Events (If applicable)** | 5-10% | Report harms or negative findings (Critical for Clinical/Engineering). | Side effects, failure rates, error bounds. |

### 2. Core Functional Module Division

*   **Essential Information**:
    *   **Exact Numbers**: N counts, percentages, means, standard deviations, confidence intervals.
    *   **Statistical Metrics**: Exact p-values (e.g., p=0.032), test statistics (t, F, χ² values), effect sizes (Cohen's d, OR, HR).
    *   **Figure/Table References**: Explicit pointers to visual data (e.g., "Figure 1A", "Table 2").
    *   **Direction of Effect**: Clear statement of increase, decrease, or no difference.
    *   **Missing Data**: Acknowledgment of missing data points or exclusions during analysis.

*   **Absolute Taboos**:
    *   **Interpretation**: Do not explain *why* the result occurred (save for Discussion).
    *   **Literature Comparison**: Do not compare results with other studies (save for Discussion).
    *   **Methodological Details**: Do not describe *how* the measurement was done (save for Methods).
    *   **Raw Data Dumping**: Do not list every single data point; summarize using statistics.
    *   **Selective Reporting**: Do not hide non-significant or negative results that were pre-specified.

### 3. General Language and Narrative Norms

*   **Tense Selection**:
    *   **Findings Observed**: Simple Past ("Group A *showed*...", "The model *achieved*...").
    *   **Figure/Table Content**: Simple Present ("Figure 1 *shows*...", "Table 2 *summarizes*...").
    *   **General Truths from Data**: Simple Present ("These data *suggest*..." - use sparingly).

*   **Voice Preference**:
    *   **Active Voice**: Increasingly preferred for clarity ("We *observed*...", "The treatment *reduced*...").
    *   **Passive Voice**: Used for emphasis on the object ("Significant differences *were found*...").
    *   **Consistency**: Maintain consistent voice within paragraphs.

*   **Structural Norms**:
    *   **Subheadings**: Use descriptive subheadings matching the research questions or methods.
    *   **Paragraph Structure**: One key finding per paragraph; start with the main takeaway.
    *   **Logical Flow**: Follow the order of methods -> primary outcome -> secondary -> robustness.
    *   **Text-Figure Integration**: Text should narrate the story; figures should provide the evidence. Do not simply repeat figure captions.

---

## II. Differentiated Writing Patterns by Research Type

### 1. Specific Norms by Research Type

#### A. Clinical/Public Health Observational Research (STROBE/CONSORT)
*   **Focus**: Participant flow, baseline comparability, primary endpoint, safety.
*   **Narrative Rhythm**: CONSORT/STROBE flow diagram -> Baseline Table -> Primary Outcome (with CI) -> Secondary -> Adverse Events.
*   **Key Feature**: Must report Confidence Intervals (CI) alongside p-values. Intention-to-Treat (ITT) vs. Per-Protocol (PP) distinction.
*   **Sentence Style**: "The primary outcome occurred in 15% of the intervention group compared with 22% of the control group (HR 0.68; 95% CI 0.55–0.84; p=0.001)."

#### B. Experimental Basic Science (ARRIVE/MIAME)
*   **Focus**: Representative data, statistical significance, biological replicates.
*   **Narrative Rhythm**: Phenotype description -> Molecular mechanism -> Validation -> Rescue/Control experiments.
*   **Key Feature**: Explicit 'n' numbers per experiment, number of independent replicates, error bars definition (SD vs. SEM).
*   **Sentence Style**: "Protein X levels were significantly elevated in knockout mice compared to wild-type (2.5-fold increase, p<0.01, n=6 per group)."

#### C. Computer Science/AI/Algorithm/Big Data Empirical Research
*   **Focus**: Benchmark performance, ablation studies, efficiency metrics.
*   **Narrative Rhythm**: Main SOTA comparison -> Efficiency analysis -> Ablation study -> Qualitative visualization.
*   **Key Feature**: Standard deviations over multiple seeds, hardware specs for timing, dataset splits.
*   **Sentence Style**: "Our method achieved 95.2% accuracy, outperforming the baseline by 3.4% (±0.5% std dev) on the ImageNet validation set."

#### D. Social Sciences/SSCI Empirical & Quantitative Research
*   **Focus**: Model coefficients, effect sizes, fit indices, robustness checks.
*   **Narrative Rhythm**: Descriptive stats -> Main regression model -> Alternative specifications -> Subgroup analysis.
*   **Key Feature**: Standardized coefficients, R-squared, AIC/BIC, handling of endogeneity.
*   **Sentence Style**: "A one-unit increase in X was associated with a 0.45 SD increase in Y (β=0.45, SE=0.12, p<0.001), controlling for covariates."

#### E. Engineering Numerical Simulation & Physical Experiment Research
*   **Focus**: Simulation vs. Experimental validation, error analysis, performance limits.
*   **Narrative Rhythm**: Simulation results -> Experimental validation -> Comparison/Error analysis -> Parameter sensitivity.
*   **Key Feature**: Error percentages, convergence rates, tolerance limits, physical units.
*   **Sentence Style**: "The simulated stress distribution matched experimental strain gauge data within a 5% margin of error across all load cases."

### 2. Core Differences Comparison Table

| Dimension | Clinical/Public Health | Basic Science | CS/AI/Tech | Social Sciences (SSCI) | Engineering |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Key Metric** | HR, OR, RR, 95% CI | Fold change, p-value, n | Accuracy, F1, Latency | β coefficients, SE, R² | Error %, Efficiency, Load |
| **Visuals** | CONSORT Flow, Kaplan-Meier | Western blots, Microscopy | Confusion Matrix, Curves | Regression Tables, Path Models | Stress Plots, CAD Renders |
| **Statistical Focus** | Significance + Clinical Relevance | Significance + Replicates | Significance + Variance (Seeds) | Significance + Effect Size | Precision + Tolerance |
| **Negative Results** | Must report adverse events | Must report failed replicates | Must report failure cases | Must report null findings | Must report failure limits |
| **Data Availability** | Individual Participant Data (often) | Raw Images/Sequences | Code + Weights + Data | Code + Survey Data | CAD Files + Logs |

---

## III. Reusable Top-Tier Sentence Template Library

### 1. Standard Templates by Functional Module

| Functional Module | English Standard Template | Chinese Meaning | Applicable Scenario | Tense/Voice |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline/Subjects** | "A total of [N] participants were included in the final analysis." | 共 [N] 名参与者纳入最终分析。 | All empirical studies | Past/Passive |
| | "Baseline characteristics were balanced between groups (Table 1)." | 各组间基线特征均衡（表 1）。 | RCT/Observational | Past/Passive |
| **Primary Outcome** | "[Intervention] significantly reduced [Outcome] compared with [Control] ([Value] vs. [Value]; p=[Value])." | 与 [对照] 相比，[干预] 显著降低了 [结果]（[值] vs. [值]；p=[值]）。 | Primary finding | Past/Active |
| | "There was a significant association between [X] and [Y] (β=[Value], 95% CI [Range])." | [X] 与 [Y] 之间存在显著关联（β=[值], 95% CI [范围]）。 | Correlation/Regression | Past/Active |
| **Secondary Outcome** | "Consistent with the primary outcome, [Secondary Measure] also improved..." | 与主要结果一致，[次要指标] 也改善了... | Supporting evidence | Past/Active |
| | "No significant difference was observed in [Outcome] between groups." | 各组间在 [结果] 上未观察到显著差异。 | Null finding | Past/Passive |
| **Subgroup/Sensitivity** | "The effect was consistent across prespecified subgroups (Figure X)." | 效应在预设亚组中保持一致（图 X）。 | Robustness | Past/Passive |
| | "Sensitivity analyses excluding [Criteria] yielded similar results." | 排除 [标准] 的敏感性分析得出相似结果。 | Robustness check | Past/Active |
| **Figure Reference** | "As shown in Figure 1A, [Trend] was observed over time." | 如图 1A 所示，随时间观察到 [趋势]。 | Describing visuals | Present/Passive |
| | "Detailed statistical parameters are provided in Supplementary Table X." | 详细统计参数见补充表 X。 | Supplementary ref | Present/Passive |
| **Statistics** | "Data are presented as mean ± SD (or median [IQR])." | 数据呈现为均值±标准差（或中位数 [四分位距]）。 | Data description | Present/Passive |
| | "Statistical significance was set at α=0.05 (two-tailed)." | 统计显著性设为 α=0.05（双尾）。 | Threshold definition | Past/Passive |

### 2. Exclusive Templates by Research Type

*   **Clinical**: "The Kaplan-Meier estimates of survival at [Time] were [X]% in the intervention group and [Y]% in the control group."
*   **Basic Science**: "Representative images from [N] independent experiments show..."
*   **CS/AI**: "Table 3 summarizes the performance comparison across [N] benchmark datasets."
*   **Social Science**: "Model fit indices indicated a good fit (CFI=0.95, RMSEA=0.05)."
*   **Engineering**: "The maximum deviation between simulation and experiment was recorded at [Condition]."

### 3. Rigorous Wording Norms

*   **Prohibited Absolute/Interpretive Statements**:
    *   ❌ "proves" → ✅ "demonstrates", "shows", "indicates".
    *   ❌ "clearly shows" (Subjective) → ✅ "shows" (Objective).
    *   ❌ "interesting ly" (Subjective) → ✅ Remove adverb.
    *   ❌ "better" (Vague) → ✅ "higher accuracy", "lower error".
    *   ❌ "caused" (Unless RCT) → ✅ "associated with", "linked to".
    *   ❌ "first time" (Unless verified) → ✅ "novel", "previously unreported".

*   **Compliant Precision Paradigms**:
    *   **Exact P-values**: Report exact p-values (e.g., p=0.032) rather than thresholds (p<0.05) unless p<0.001.
    *   **Confidence Intervals**: Always report 95% CI for effect sizes in clinical/observational studies.
    *   **Units**: Always include standard units (e.g., mg/dL, ms, %).
    *   **N-numbers**: Explicitly state 'n' for every experiment/data point cluster.

*   **Handling Null/Negative Results**:
    *   "No statistically significant difference was detected..."
    *   "The trend was in the expected direction but did not reach significance..."
    *   "Contrary to our hypothesis, X did not influence Y..."


## VI. Data Visualization & Text Integration Guidelines

### 1. Text-Figure Complementarity

*   **Text Role**: Narrate the story, highlight key comparisons, state statistical significance.
*   **Figure Role**: Display patterns, distributions, trends, and raw data density.
*   **Rule**: Do not duplicate. If a table lists all values, the text should summarize the trend.
*   **Example**:
    *   *Bad*: "Group A was 10.5, Group B was 12.3, Group C was 11.1 (Table 1)."
    *   *Good*: "Group B showed the highest values, significantly exceeding Group A (p=0.02; Table 1)."

### 2. Supplementary Material Usage

*   **Main Text**: Reserved for primary outcomes and key secondary outcomes supporting the main claim.
*   **Supplementary**: Reserved for extensive robustness checks, additional subgroup analyses, raw data tables, and negative controls.
*   **Referencing**: "See Supplementary Figures S1-S5 for additional sensitivity analyses."
*   **Consistency**: Supplementary results must not contradict main text results.
