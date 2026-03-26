
## IV. Pitfall Avoidance Guide & Red Lines

### 1. High-Frequency Errors

*   **Error 1: Insufficient Reproducibility Detail**.
    *   *Issue*: Missing critical parameters that prevent independent replication.
    *   *Fix*: Include all numerical parameters, versions, settings. Use supplementary materials for extended details.
    *   *Example*: "trained using default settings" → ✅ "trained with lr=0.001, batch=32, epochs=100, seed=42"

*   **Error 2: Information Imbalance**.
    *   *Issue*: Over-detailing trivial procedures while under-describing critical innovations.
    *   *Fix*: Proportion detail to methodological novelty and importance for replication.
    *   *Example*: Don't spend 3 paragraphs on buffer preparation but 1 sentence on novel algorithm.

*   **Error 3: Logical Chain Breaks**.
    *   *Issue*: Steps in the procedure are missing or out of chronological order.
    *   *Fix*: Follow the actual workflow. Use flowcharts in supplementary materials if complex.
    *   *Example*: Ensure sample collection → processing → analysis order is maintained.

*   **Error 4: Methods-Results Mismatch**.
    *   *Issue*: Results section presents analyses not described in Methods.
    *   *Fix*: Every statistical test and analysis in Results must have a corresponding Methods description.
    *   *Example*: If Results show survival analysis, Methods must describe Cox regression details.

### 2. Adaptation: Comprehensive vs. Specialized Journals

*   **Nature/Science/Cell**:
    *   **Style**: Methods often in supplementary materials; main text has brief "Methods Summary."
    *   **Length**: 1-2 pages in main text, 20+ pages in supplementary.
    *   **Focus**: Emphasize novel methodological contributions; standard protocols can be cited.
    *   **Requirement**: Mandatory data and code availability statements.

*   **Specialized Journals (e.g., *PLOS ONE*, *JAMA*, *IEEE Transactions*)**:
    *   **Style**: Complete methods in main text.
    *   **Length**: Can be 30-40% of total manuscript.
    *   **Focus**: Complete reproducibility within the main document.
    *   **Requirement**: Strict adherence to field-specific reporting checklists (CONSORT, STROBE, etc.).

### 3. Absolute Red Lines (Strictly Forbidden)

*   **Ethical Compliance Gaps**: No IRB approval number, no consent statement, no animal care protocol.
*   **Data Provenance Unclear**: Cannot identify where data/samples originated.
*   **Incomplete Method Description**: Critical steps omitted that prevent replication.
*   **Academic Misconduct Indicators**:
    *   ❌ "data were adjusted to fit expectations"
    *   ❌ "outliers were removed" (without pre-specified criteria)
    *   ❌ "experiments were performed" (when actually simulated or vice versa)
    *   ❌ Copying methods from another paper without attribution
*   **Proprietary Secrecy**: Withholding methods that are essential for scientific verification (unless legally protected with justification).
*   **Results Contamination**: Presenting outcomes, interpretations, or conclusions in the Methods section.
*   **Citation Manipulation**: Citing methods that were not actually used.

---

## V. Top-Tier Methods Section Quality Checklist

Before submission, verify your Methods section against these criteria:

### 1. Reproducibility
- [ ] Could another researcher replicate this study exactly from the description provided?
- [ ] Are all reagents, equipment, and software fully specified (manufacturer, version, location)?
- [ ] Are all numerical parameters explicitly stated (concentrations, temperatures, times, sizes)?
- [ ] Is code/data availability clearly documented with accessible links?
- [ ] Are random seeds, initialization methods, and stochastic elements specified?

### 2. Compliance
- [ ] Is ethical approval documented with committee name and protocol number?
- [ ] Is informed consent status clearly stated (or waiver justification provided)?
- [ ] Does the study adhere to relevant reporting guidelines (CONSORT/STROBE/ARRIVE/etc.)?
- [ ] Are trial registration numbers provided (for clinical trials)?
- [ ] Are data privacy and protection measures described (for human data)?

### 3. Logic
- [ ] Does the order of procedures follow the actual chronological workflow?
- [ ] Are all methods mentioned in Results described in the Methods section?
- [ ] Do subsections flow logically with clear transitions?
- [ ] Is there a clear link between research questions and methodological choices?
- [ ] Are exclusion criteria and missing data handling procedures explained?

### 4. Rigor
- [ ] Are sample size justifications or power calculations provided?
- [ ] Are randomization and blinding procedures clearly described?
- [ ] Are statistical tests appropriate for the data types and distributions?
- [ ] Are multiple testing corrections applied and described?
- [ ] Are quality control and validation procedures documented?
- [ ] Are potential confounders addressed in the design or analysis?

### 5. Norms
- [ ] Is the word count appropriate for the target journal's requirements?
- [ ] Are tenses used correctly (Past for procedures, Present for established methods)?
- [ ] Is voice consistent throughout (passive or active)?
- [ ] Are abbreviations defined at first use?
- [ ] Are supplementary materials properly referenced for extended protocols?
- [ ] Is the language precise without vague qualifiers ("approximately," "about," "standard")?

---

## VI. Supplementary Materials Integration Guidelines

### 1. What Belongs in Supplementary Methods

*   **Extended Protocols**: Step-by-step detailed procedures exceeding main text space limits.
*   **Additional Validations**: Sensitivity analyses, robustness checks, alternative method comparisons.
*   **Complete Parameter Lists**: Full hyperparameter tables, complete reagent lists with lot numbers.
*   **Code Snippets**: Critical algorithm implementations not suitable for main text.
*   **Questionnaire Instruments**: Full survey items, interview protocols, measurement scales.

### 2. Cross-Referencing Standards

*   **In-Text Citation**: "Full protocol details are provided in Supplementary Methods Section S1."
*   **Consistency**: Supplementary methods must not contradict main text methods.
*   **Accessibility**: Supplementary materials must be permanently accessible with the published article.
*   **Versioning**: Clearly indicate version numbers for code and protocols in supplementary materials.
