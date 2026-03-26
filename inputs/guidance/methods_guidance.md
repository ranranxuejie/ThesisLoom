## I. Cross-Domain Universal Underlying Logic and Framework Patterns

### 1. Narrative Logic Chain Breakdown: The Reproducibility Framework

Top-tier Methods sections universally follow a **"Chronological + Hierarchical"** logic, enabling independent replication. The structure aligns with discipline-specific reporting standards:

| Order | Functional Module | Proportion | Core Writing Goal | Typical Content |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Study Design & Ethical Compliance** | 10-15% | Establish the overall research framework and confirm ethical/regulatory approval. | Study type, approval numbers, consent procedures, compliance statements. |
| **2** | **Subjects/Materials/Data Sources** | 20-25% | Define what was studied with complete specification for replication. | Participant criteria, cell lines, reagents, datasets, equipment specifications. |
| **3** | **Procedures/Algorithms/Data Collection** | 40-50% | Detail how the study was conducted with step-by-step precision. | Experimental protocols, algorithm architecture, measurement procedures, intervention details. |
| **4** | **Data Processing & Statistical Analysis** | 15-20% | Explain how data were transformed, analyzed, and validated. | Preprocessing steps, statistical tests, software versions, significance thresholds. |
| **5** | **Validation & Quality Control** | 5-10% | Demonstrate methodological rigor and reliability checks. | Replication numbers, calibration procedures, sensitivity analyses, blinding methods. |

### 2. Core Functional Module Division

*   **Essential Information**:
    *   **Ethical Approval**: IRB/ethics committee approval numbers, informed consent documentation, animal care protocols.
    *   **Complete Specifications**: Manufacturer names, locations, catalog numbers, software versions, parameter settings.
    *   **Inclusion/Exclusion Criteria**: Clear definitions of what was included/excluded and why.
    *   **Statistical Power**: Sample size justification, power calculations, effect size expectations.
    *   **Reproducibility Details**: Number of replicates, independent experiments, randomization procedures.

*   **Absolute Taboos**:
    *   **Results in Methods**: Do not present findings, outcomes, or interpretive statements.
    *   **Vague Descriptions**: Avoid "standard protocols," "as described previously" without complete citation or supplementary details.
    *   **Proprietary Black Boxes**: Cannot withhold critical methodological details that prevent replication.
    *   **Post-Hoc Decisions**: Do not describe analytical decisions made after seeing the data without explicit acknowledgment.

### 3. General Language and Narrative Norms

*   **Tense Selection**:
    *   **Procedures Performed**: Simple Past ("Samples *were collected*...", "We *analyzed*...").
    *   **Established Protocols**: Simple Present ("The protocol *follows*...").
    *   **Software/Equipment Capabilities**: Simple Present ("The software *calculates*...").

*   **Voice Preference**:
    *   **Passive Voice Dominant**: Traditional preference for objectivity ("Samples *were processed*...", "Data *were analyzed*...").
    *   **Active Voice Increasing**: Modern trend for clarity ("We *collected*...", "Our algorithm *computes*...").
    *   **Consistency**: Maintain consistent voice throughout subsections.

*   **Structural Norms**:
    *   **Subheadings**: Use descriptive subheadings for each major methodological component.
    *   **Paragraph Structure**: One procedure/concept per paragraph; topic sentence states the purpose.
    *   **Logical Flow**: Follow the chronological order of how the research was actually conducted.
    *   **Cross-Referencing**: Link to supplementary materials for extended protocols ("See Supplementary Methods").

---

## II. Differentiated Writing Patterns by Research Type

### 1. Specific Norms by Research Type

#### A. Experimental Basic Science (Biology/Chemistry/Materials/Environmental)
*   **Reporting Standard**: ARRIVE (animals), MIAME (microarrays), MIAPE (proteomics)
*   **Focus**: Reagent specifications, environmental conditions, equipment calibration, replication details.
*   **Key Feature**: Complete catalog numbers, lot numbers, manufacturer locations, buffer compositions, incubation conditions.
*   **Sentence Style**: "Cells *were cultured* in DMEM supplemented with 10% FBS at 37°C with 5% CO₂."

#### B. Clinical/Public Health Medical Research
*   **Reporting Standard**: CONSORT (RCTs), STROBE (observational), PRISMA (systematic reviews)
*   **Focus**: Participant recruitment, randomization, blinding, intervention protocols, safety monitoring.
*   **Key Feature**: Trial registration numbers, inclusion/exclusion criteria, primary/secondary outcomes definition, adverse event reporting.
*   **Sentence Style**: "Participants *were randomized* 1:1 using computer-generated sequences with allocation concealment."

#### C. Computer Science/AI/Algorithm/Big Data Empirical Research
*   **Reporting Standard**: NeurIPS reproducibility checklist, ACM artifacts
*   **Focus**: Dataset specifications, model architecture, hyperparameters, computational resources, code availability.
*   **Key Feature**: GPU/CPU specifications, training time, learning rates, batch sizes, random seeds, public repository links.
*   **Sentence Style**: "The model *was trained* for 100 epochs with batch size 256 using Adam optimizer (lr=0.001)."

#### D. Social Sciences/SSCI Empirical & Quantitative Research
*   **Reporting Standard**: SRMP (Survey Research), APA standards
*   **Focus**: Sampling strategy, measurement instruments, validity/reliability, survey protocols.
*   **Key Feature**: Scale citations, Cronbach's alpha, response rates, weighting procedures, missing data handling.
*   **Sentence Style**: "Survey items *were adapted* from the validated X scale (α=0.89) with 5-point Likert responses."

#### E. Engineering Numerical Simulation & Physical Experiment Research
*   **Reporting Standard**: ASME standards, IEEE standards
*   **Focus**: Boundary conditions, mesh specifications, validation against benchmarks, error analysis.
*   **Key Feature**: Grid independence tests, convergence criteria, calibration against known standards, uncertainty quantification.
*   **Sentence Style**: "Simulations *employed* a mesh of 2.5M elements with y+<1 for wall-bounded regions."

### 2. Core Differences Comparison Table

| Dimension | Basic Science | Clinical/Medical | CS/AI/Tech | Social Sciences (SSCI) | Engineering |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Key Identifier** | Reagent specs, conditions | Trial registration, consent | Code, hyperparameters | Scale validity, sampling | Boundary conditions, validation |
| **Ethical Focus** | Animal/human subject approval | Informed consent, IRB | Data privacy, IRB (if human data) | IRB, consent, anonymity | Safety protocols |
| **Replication Detail** | Lot numbers, temperatures | Randomization, blinding | Random seeds, versions | Response rates, weights | Mesh, convergence criteria |
| **Statistical Detail** | N numbers, replicates | Power calculation, ITT analysis | Metrics, test/train splits | Reliability coefficients, CI | Error bounds, uncertainty |
| **Supplementary Needs** | Extended protocols | Full protocol, CONSORT flow | Code repository, full logs | Survey instruments, code | CAD files, input decks |

---

## III. Reusable Top-Tier Sentence Template Library

### 1. Standard Templates by Functional Module

| Functional Module | English Standard Template | Chinese Meaning | Applicable Scenario | Tense/Voice |
| :--- | :--- | :--- | :--- | :--- |
| **Study Design & Ethics** | "This study was approved by the [Institution] Ethics Committee (Protocol #XXX)." | 本研究经 [机构] 伦理委员会批准（方案号 XXX）。 | All human/animal studies | Past/Passive |
| | "All participants provided written informed consent prior to enrollment." | 所有参与者在入组前提供书面知情同意书。 | Human subjects research | Past/Active |
| | "This trial was registered at [Registry] (Identifier: XXX)." | 本试验注册于 [注册平台]（识别号：XXX）。 | Clinical trials | Past/Passive |
| **Subjects/Materials/Data** | "[Sample type] were obtained from [Source] between [Date Range]." | [样本类型] 于 [日期范围] 从 [来源] 获取。 | Sample collection | Past/Passive |
| | "Inclusion criteria comprised: (1)..., (2)..., (3)..." | 纳入标准包括：(1)..., (2)..., (3)... | Participant selection | Past/Active |
| | "The [Dataset Name] dataset contains [N] samples with [Features]." | [数据集名称] 数据集包含 [N] 个样本，具有 [特征]。 | ML/Data research | Present/Active |
| **Procedures/Algorithms** | "Samples were processed according to [Protocol] with modifications." | 样本根据 [方案] 进行处理，略有修改。 | Lab protocols | Past/Passive |
| | "The algorithm consists of [N] stages: (1)..., (2)..." | 该算法由 [N] 个阶段组成：(1)..., (2)... | Algorithm description | Present/Active |
| | "Intervention was administered as [Dose] via [Route] for [Duration]." | 干预以 [剂量] 通过 [途径] 给予，持续 [时长]。 | Clinical intervention | Past/Passive |
| **Data Processing & Statistics** | "Statistical analyses were performed using [Software] (Version X.X)." | 统计分析使用 [软件]（X.X 版）进行。 | All quantitative studies | Past/Passive |
| | "Differences were assessed using [Test] with significance at p<0.05." | 差异使用 [检验方法] 评估，显著性水平为 p<0.05。 | Hypothesis testing | Past/Passive |
| | "Data were normalized using [Method] to account for [Factor]." | 数据使用 [方法] 归一化，以考虑 [因素]。 | Data preprocessing | Past/Passive |
| **Validation & QC** | "All experiments were repeated independently at least [N] times." | 所有实验独立重复至少 [N] 次。 | Experimental research | Past/Passive |
| | "Blinding was maintained throughout [Procedure] until analysis completion." | 在 [程序] 期间保持盲法直至分析完成。 | Clinical/Lab research | Past/Passive |
| | "Model performance was validated using [Method] with [Metric]." | 模型性能使用 [方法] 与 [指标] 进行验证。 | ML/Computational | Past/Passive |

### 2. Exclusive Templates by Research Type

*   **Clinical**: "Randomization was stratified by [Factor] using permuted blocks of size [N]."
*   **Basic Science**: "Antibodies were used at dilutions of 1:[X] for [Application] (Catalog #, Manufacturer)."
*   **CS/AI**: "We used [N] GPUs ([Model]) for training, completing in [X] hours."
*   **Social Science**: "Missing data were handled using [Method] (e.g., multiple imputation, FIML)."
*   **Engineering**: "Grid independence was verified with mesh densities ranging from [X] to [Y] elements."

### 3. Rigorous Wording Norms

*   **Prohibited Vague Descriptions**:
    *   ❌ "standard protocol" → ✅ "protocol as described in [Citation] with the following modifications:..."
    *   ❌ "appropriate statistical tests" → ✅ "one-way ANOVA with Tukey's post-hoc correction"
    *   ❌ "several times" → ✅ "three independent replicates"
    *   ❌ "commercially available" → ✅ "purchased from [Company], [City, Country] (Catalog #)"
    *   ❌ "significant results" → ✅ "results with p<0.05 after [correction method]"

*   **Compliant Precision Paradigms**:
    *   **Quantification**: Always specify numbers, concentrations, temperatures, times, dimensions.
    *   **Sourcing**: Manufacturer + City + Country + Catalog Number + Lot Number (when critical).
    *   **Software**: Name + Version + Company/Developer + URL (if applicable).
    *   **Statistics**: Test name + assumptions checked + correction methods + exact p-values.

*   **Methodological Limitation Statements**:
    *   "We acknowledge that [Limitation] may affect [Aspect], however..."
    *   "This approach, while [Advantage], has the constraint of [Limitation]."
    *   "Future studies should address [Limitation] through [Suggestion]."
