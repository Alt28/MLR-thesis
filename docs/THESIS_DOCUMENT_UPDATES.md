# Updating the manuscript to match the implemented system

Prepared 13 November 2026 for the decision to treat the implemented system as the reference methodology and to revise the document accordingly. Page numbers are PDF pages of `Raymart (3).pdf`, with the printed page in parentheses. Nothing here is adviser approval: every amendment below still needs your adviser's review, and no amendment creates research evidence.

Each run of the system now exports **`METHODOLOGY.md` ("Methodology as implemented")** from Export Results. It prints the applied split, IQR fences, encoding, interaction terms, OLS arms, classification thresholds, label distribution, environment, and limitations with the actual numbers of that run. Use that file as the source of the values you paste into Chapters 3 and 4, so the document and the software cannot drift apart.

---

## A. Internal inconsistencies to fix first

These are contradictions inside the current document, independent of the software.

| # | Location | Problem | Fix |
| --- | --- | --- | --- |
| A1 | List of Tables, PDF 5 | Table 3.1 is listed on page 44, but Dataset Variables actually appears on PDF 35 (printed 30). Tables 3.2 and 3.3 are listed as 38 and 39. | Regenerate the list of tables after final pagination. |
| A2 | List of Figures, PDF 4 vs PDF 14 | The list names Figure 1.2 "Effect of Constant Linear Relationships on Multiple Linear Regression"; the caption in the body reads "Effect of Interaction Effects on Multiple Linear Regression Prediction". | Choose one title and use it in both places. The body caption matches the content. |
| A3 | Table of Contents, PDF 3 vs PDF 45 | The contents list "3.4 Theories" and "3.4.1 Theories"; the body heading is "3.4 Theories, Methods, and Tools". | Use "3.4 Theories, Methods, and Tools" in both. |
| A4 | 1.6 Definition of Terms, PDF 21 (16) | Two different definitions coexist: "Threshold-Based Station Classification" categorizes **predicted waiting time** into conditions, while "Multi-Factor Threshold-Based Station Classification" evaluates **all seven factors**. Figure 1.3 (PDF 16) also shows wait-time-only classification. | Keep one framework name. See B6 for replacement wording; the system implements the multi-factor version, in which predicted waiting time is one of seven factors. |
| A5 | Figure 1.1 (PDF 13) vs Section 4.1 (PDF 51) | Figure 1.1 defines the baseline as having **no** preprocessing or irregularity detection, but 4.1 proposes evaluating the irregularity-detection effect against "the baseline model", which elsewhere shares the reviewed data. | Adopt the three-arm wording in B5. It makes "baseline" unambiguous. |
| A6 | Table 3.1 (PDF 35) vs dataset | Table 3.1 calls the dependent variable "Wait Time"; the algorithm steps and the system use "Actual Waiting Time". | Use "Actual Waiting Time" everywhere; it is the required column name. |
| A7 | 1.6, PDF 21 (16) | "Train and Bus Waiting Time ... between the arrival of passengers at a station and the arrival of the next available train or bus." The system's measurement protocol ends the interval at **boarding**, which differs when a passenger cannot board a full vehicle. | Replace with the wording in B1. |

---

## B. Chapter 3 amendments (methodology as implemented)

### B1. Table 3.1, Dataset Variables — PDF 35 (printed 30)

Current entries give no units and define Vehicle Frequency as "Number of available vehicles". Replace the table with the measured definitions the software requires. The system refuses to issue a station condition until the Vehicle Frequency and Route Distance units are declared.

| Variable | Operational definition | Unit |
| --- | --- | --- |
| Traffic Condition | Observed level of road traffic congestion at the station at the passenger arrival time, recorded with a fixed category list | Category |
| Weather Condition | Observed weather state at the station at the passenger arrival time, recorded with a fixed category list | Category |
| Passenger Volume | Number of passengers observed arriving for the same service, stop, and direction during the 60 minutes before the sampled passenger's arrival | Passengers per 60-minute window |
| Route Distance | Total length of the selected service route in the observed direction | Kilometres (km) |
| Vehicle Frequency | Observed number of vehicle events serving the selected stop, route, and direction during the 60 minutes before the passenger's arrival, expressed as a rate | Vehicles per hour |
| Time of Day | Observation period derived from the passenger arrival timestamp using boundaries fixed before evaluation | Category |
| Actual Waiting Time | Elapsed time between the sampled passenger's arrival at the designated waiting area and boarding the selected service, including waiting caused by inability to board a full vehicle | Minutes |

Add below the table:

> Vehicle Frequency is measured as `60 × N / W`, where `N` is the number of serving vehicle events observed in a completed window and `W` is that window's length in minutes; this study fixes `W = 60`. Fleet availability, scheduled headway, and published arrival predictions are not substituted for this observed rate. Units are declared per dataset in the system configuration and are never inferred from the recorded values.

This supersedes "number of available vehicles". State the change explicitly in the document so the revision is traceable.

### B2. Section 3.1, Research Design — PDF 34 (29)

Add after the existing description of the quantitative experimental design:

> The dataset is partitioned once into training and test observations before any screening, encoding, or threshold is estimated. The study uses an 80/20 holdout with a fixed random seed of 42. Two partition designs are supported: random assignment of observations, and a grouped assignment in which every observation sharing a station identifier is placed entirely in one partition. The grouped design is used when repeated observations at the same station would otherwise appear in both partitions. The applied design, fraction, seed, grouping column, and resulting partition sizes are recorded with every run.

State which design your final run used, and why.

### B3. Section 3.2.1, Step 2 (Solution 1) — PDF 37 (32)

The implemented rule matches the document; add the decisions and their traceability:

> Quartiles and fences are computed only on the training partition, for Passenger Volume, Route Distance, Vehicle Frequency, and Actual Waiting Time, using IQR = Q3 − Q1, Lower Bound = Q1 − 1.5(IQR), and Upper Bound = Q3 + 1.5(IQR). Every flagged training observation requires an explicit recorded decision of retain, correct, or exclude together with a written source-based reason. No observation is removed automatically, valid unusual transportation events are retained, the source file is never modified, and the test partition is never screened or reviewed. The flag counts, each decision, and each reason are exported with the results.

### B4. Section 3.2.1, Steps 3–4 (Solution 2) — PDF 38–39 (33–34)

Add the exact specification actually fitted:

> Categorical predictors are represented by reference-category indicator variables fitted on the training partition; the alphabetically first observed training category is the reference. The enhanced model retains all six main effects and adds only the explicitly selected interaction terms: Passenger Volume × Vehicle Frequency (pairwise) and Passenger Volume × Vehicle Frequency × Time of Day (higher-order). Interactions involving a categorical predictor are formed by multiplying each of its non-reference indicators with the remaining selected columns. No exhaustive search over possible interactions is performed, and higher-order terms do not automatically introduce their lower-order components. The specification is fixed and approved before the test partition is evaluated.

Replace the two example terms if your approved specification differs; the list must match the exported `selected_interactions` table.

### B5. New subsection, "Controlled comparison arms" — insert in 3.2.1 after Step 6, PDF 40 (35)

This resolves A5.

> Three regression arms are estimated by Ordinary Least Squares and evaluated on the same held-out test observations. Arm A is the traditional additive model fitted on the original training observations before any review correction or exclusion. Arm B is the traditional additive model fitted on the reviewed training observations. Arm C is the enhanced model with the selected interaction terms, fitted on the same reviewed training observations as Arm B. The comparison A versus B isolates the effect of the recorded irregularity-review decisions, B versus C isolates the effect of the interaction specification, and A versus C describes the combined workflow. If the review changes no training record, the study reports that no benefit from correction or exclusion was demonstrated.

Also amend the Figure 1.1 discussion (PDF 13) to say that the baseline process analysed in the study corresponds to Arm A.

### B6. Section 3.2.1, Step 7 (Solution 3) and Section 3.4.2 — PDF 40–41 (35–36), PDF 47 (42)

Replace "predefined operational thresholds" with the implemented rules. These are researcher-defined decision-support rules and must be justified, not presented as validated operational standards.

> Each of the seven factors receives a severity score of Normal = 0, Minor = 1, Moderate = 2, or Severe = 3, and each carries equal weight 1/7. The Multi-Factor Station Score is the sum of the seven severity scores divided by seven and is evaluated without rounding. The overall station condition is Normal Operation for scores in [0, 0.75), Minor Delay in [0.75, 1.50), Moderate Delay in [1.50, 2.25), and Severe Delay in [2.25, 3].
>
> The predicted waiting time produced by Arm C is scored using fixed operational bands: 0 for 15 minutes or less, 1 for more than 15 up to 20, 2 for more than 20 up to 25, and 3 for more than 25 minutes.
>
> Numerical predictors are scored against their first, second, and third quartiles computed with linear interpolation on the reviewed training partition. For increasing severity, a value receives 0 at or below Q1, 1 above Q1 up to Q2, 2 above Q2 up to Q3, and 3 above Q3; reverse severity assigns 3 minus that score. The severity direction is taken from an explicitly documented researcher configuration when one is provided; otherwise it follows the sign of the Pearson correlation between that predictor and Actual Waiting Time in the reviewed training partition. This correlation is a descriptive association in the training sample and is not a test of significance or causation.
>
> Categorical predictors are scored by comparing each category's mean Actual Waiting Time in the reviewed training partition with the training waiting-time quartiles, using increasing severity. A documented researcher mapping overrides the derived score.
>
> A factor receives no score when its training values are constant or effectively constant, when its quartiles collapse, when a category was never observed in training and has no documented mapping, or when the direction cannot be resolved. When any of the seven factors or a required measurement unit is unresolved, the observation is reported as Requires Researcher Decision. The framework never averages the remaining factors, substitutes zero, or assigns a default Normal condition. Unresolved observations remain in the reported denominator and their specific reasons are exported.
>
> Negative predicted waiting times are retained unchanged in the error metrics; only the value entering classification is floored at zero, and such predictions are flagged as unsuitable for direct waiting-time interpretation.

Also update the Figure 1.3 discussion (PDF 16) so the figure describes the multi-factor framework rather than classification of the predicted waiting time alone, and align the 1.6 definitions (A4).

### B7. New subsection, "Station-level summary" — insert after Step 7, or in 4.3

The system reports this and the current document does not define it.

> When the dataset contains a `Station ID` or `Station` field, the held-out observations are additionally grouped by that identifier. For each station the study reports the number of test records, the number of classifiable and unresolved records, the mean Multi-Factor Station Score over classifiable records only, and the condition label obtained from the same score boundaries. This is a descriptive summary of the analysed test observations for that station. It is not a real-time station state and is not independently validated.

Omit this subsection only if you also stop reporting station summaries.

### B8. Section 3.2.1, Step 8, "Return the Result" — PDF 42 (37)

Extend the returned outputs to match the implementation:

> The framework returns the estimated regression coefficients, the predicted waiting times of each arm, the MSE and RMSE of each arm with their differences, the seven per-factor severity scores, the Multi-Factor Station Score, the overall station condition of each test observation with the reasons for any unresolved classification, the optional station-level summary, the recorded review decisions, and the configuration and diagnostic records required to reproduce the run.

### B9. Section 3.2.2, System Architecture (IPO) — PDF 42 (37)

Add the review step and the unresolved output so the diagram matches the software:

> The process stage additionally includes the recorded researcher review of flagged training observations and the measurement-unit declarations required before classification. The output stage includes Requires Researcher Decision as a possible classification outcome.

### B10. Table 3.3, Software Requirements — PDF 44–45 (39–40)

The current table lists Jupyter Notebook and Python 3.12 and omits the web application. Replace with what the system actually uses:

| Software | Purpose |
| --- | --- |
| Windows 11 (64-bit) | Operating system |
| Python 3.12 or later (3.13 used) | Programming language and research engine |
| Visual Studio Code | Integrated development environment |
| pandas | Dataset handling and quartile computation |
| NumPy | Numerical computation and interaction-term construction |
| scikit-learn | Ordinary Least Squares estimation, train/test partitioning, MSE and RMSE |
| Matplotlib | Figures for prediction and model comparison |
| openpyxl | Excel dataset reading and workbook export |
| joblib | Saving fitted models for reproducibility |
| FastAPI and Uvicorn | Local research application interface |
| React, Vite, TypeScript, Node.js | Compiled browser interface for the local application |
| pytest and Playwright | Software verification of the implementation |
| Microsoft Excel | Dataset inspection and validation |

Add one sentence: the browser interface is an implementation choice for operating the research engine locally and is not itself the research contribution. Remove Jupyter Notebook unless you actually used it.

### B11. Section 3.4.2, Methods and Tools — PDF 47 (42)

Append the reproducibility rule:

> Every completed run exports the configuration, the training and test membership, the review decisions with reasons, the fitted models, the learned classification rules, the applied measurement units, the software environment, and source-code hashes. A generated methodology record states the split design, fences, encoding, interaction terms, arms, thresholds, and limitations actually applied in that run.

---

## C. Chapter 4 reporting structure

Report only what a completed run produced; take the numbers from `METHODOLOGY.md` and the exported tables.

- **4.1 Effect of IQR-based irregularity detection.** Report training and test sizes, the fences per screened variable, the flag count, and the retain/correct/exclude counts with their reasons. Then report Arm A versus Arm B MSE and RMSE. If no training record changed, state plainly that no benefit from correction or exclusion was demonstrated; do not present a flag count as an improvement.
- **4.2 Evaluation of interaction terms.** Report the selected terms with their coefficients, the feature counts, the design-rank and conditioning diagnostics, and the Arm B versus Arm C comparison. Report an increase in error honestly if that is the outcome. Arm A versus Arm C is the combined workflow, not isolated evidence about interactions.
- **4.3 Multi-Factor Threshold-Based Station Classification.** Report the applied units, thresholds, derived category mappings and their training means, the per-factor severity scores, and the count and proportion of observations in each condition. Include unresolved observations in the denominator and explain why they are unresolved. Include the station-level summary if you kept B7.
- **4.4 Result of thesis.** Summarise all three arms, separate prediction accuracy from decision-support classification, and state the data provenance, sampling coverage, test size, split design, and limitations.

Table 4.1 should contain the arms, their training and test row counts, and their MSE and RMSE, so the baseline definition stays unambiguous.

---

## D. Chapter 1 and 5 adjustments

- **1.5 Scope and Limitations, PDF 18–19 (13–14).** Add: evaluation uses a single fixed holdout rather than cross-validation or significance testing; the station condition is a researcher-defined decision-support rule and is not independently validated; results apply only to the sampled stations, routes, and observation period.
- **1.6 Definition of Terms, PDF 19–21 (14–16).** Fix A4 and A7, then add entries for: Multi-Factor Station Score; Requires Researcher Decision; Comparison Arms A, B, and C; Grouped Partitioning; and Reviewed Training Observations.
- **Chapter 5, PDF 54 onward.** Conclusions must follow the actual measured outcome of the three arms, including an outcome in which the enhanced model does not reduce error. Recommendations can then include collecting observation-level recorded data, validating the classification thresholds against independent operational references, and testing a time-based partition.

---

## E. What the document must not claim

The software cannot supply these, and the current bundled datasets are synthetic:

1. Real-world predictive accuracy, until recorded observation-level data is collected under the B1 definitions.
2. Statistical significance, confidence intervals, or causal effects; the design is one descriptive holdout.
3. Validated operational station conditions; the thresholds are researcher-defined decision-support rules.
4. Real-time monitoring, dispatching, or scheduling capability, consistent with the existing 1.5 scope statement.

---

## F. Checklist before submission

1. Run the final dataset, then download **Export Results > Methodology as implemented**.
2. Copy its split design, fences, interaction terms, arm metrics, thresholds, category mappings, and label distribution into Sections 3.1–3.4 and Chapter 4.
3. Apply amendments A1–A7 so the document no longer contradicts itself.
4. Confirm Table 3.1 units match the declared units in the run, and that both declared units appear in the exported configuration.
5. Have your adviser approve the Vehicle Frequency redefinition (B1), the three-arm design (B5), the classification rules (B6), and the station summary (B7) before presenting any result.
