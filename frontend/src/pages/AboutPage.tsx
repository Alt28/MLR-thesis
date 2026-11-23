export function AboutPage() {
  return <article className="methodology">
    <span className="eyebrow">ABOUT THE RESEARCH</span>
    <h1>How it works</h1>
    <p className="intro">An interface for demonstrating enhanced Multiple Linear Regression for train and bus waiting-time prediction.</p>
    <ol className="how-it-works">
      <li><h2>Upload transportation data</h2><p>On Training, upload a CSV or XLSX file containing the six predictors and recorded Actual Waiting Time. Review the source declarations and model settings, then select Train & evaluate. Both models are fitted and evaluated on held-out recorded observations.</p></li>
      <li><h2>Review unusual observations when needed</h2><p>The training workflow checks the data. If observations need a researcher decision, retain, correct, or exclude them before continuing.</p></li>
      <li><h2>Compare Traditional and Enhanced MLR</h2><p>The main comparison uses reviewed data for both models. An additional original-data baseline separates the effects of review decisions and interactions. All three experiments use the same test observations. Bus and Train datasets use separate fitted models.</p></li>
      <li><h2>View predicted waiting time</h2><p>On Test & Predict, upload rows with blank or omitted actual waits, select a compatible trained model, and choose Generate predictions. The Prediction comparison shows Traditional and Enhanced estimates side by side. Actual Waiting Time stays blank; predictions have their own columns. Without recorded actual waits, those rows have no measurable MSE, RMSE, or prediction error. For evaluated data, View Details shows the accuracy comparison.</p></li>
      <li><h2>Interpret station condition</h2><p>The Multi-Factor Threshold-Based Classification framework combines predicted waiting time with all six transportation factors. Station summaries group observations by Station / Stop and preserve unresolved classifications.</p></li>
    </ol>
    <p>The Three SOP solutions section on Training links each research problem to its implementation and current evidence: IQR review for SOP 1, interaction terms and controlled comparisons for SOP 2, and seven-factor station scores and thresholds for SOP 3.</p>
    <details className="disclosure">
      <summary>Methodology and research decisions</summary>
      <div className="disclosure-body">
        <h2>What is preserved</h2>
        <p>The six predictors are Passenger Volume, Vehicle Frequency, Station / Stop, Time of Day, Day of Week, and Month of Year. Actual Waiting Time is required for evaluation; Test & Predict accepts predictor rows without it for prediction using saved models. A blank-target file uploaded on Training is moved to Test & Predict without replacing the saved training dataset.</p>
        <p>The default split is random 80/20 with seed 42 and is fixed before fitting IQR bounds, categorical encodings, or severity quartiles. IQR flags are retained unless the researcher explicitly corrects or excludes them. When repeated stations make a random assignment optimistic, Model settings offers a grouped split that keeps every observation of one station identifier in a single partition; a chronological design would still need a separately approved implementation.</p>
        <p>Traditional MLR uses main effects. Enhanced MLR keeps those main effects and adds selected pairwise and higher-order interactions. The main B vs C comparison uses the same reviewed training rows and test rows. Arm A uses the original training rows; A vs B examines recorded review decisions. Lower MSE and RMSE indicate smaller prediction errors; improvement is not assumed.</p>
        <h2>Station classification</h2>
        <p>Each of the six predictors and enhanced predicted waiting time receives a severity score: Normal = 0, Minor = 1, Moderate = 2, Severe = 3. The multi-factor score is their sum divided by seven.</p>
        <p>The supplied implementation brief defines waiting-time bands at 15, 20, and 25 minutes and overall-score boundaries at 0.75, 1.50, and 2.25. The PDF describes the framework without fully specifying these rules. Applied values are recorded in Model settings and exported with the results.</p>
        <p>For each station in the held-out data, the optional summary averages classifiable observation scores and reports unresolved counts. It describes the analyzed test observations; it is not a real-time station condition or independently validated classification.</p>
        <h2>Research evidence</h2>
        <p>Prototype or simulated data tests software behavior. It does not establish real-world predictive performance. Source declarations and researcher notes are preserved in exports. Each model is restricted to its declared transport mode.</p>
        <h2>Requires Researcher Decision</h2>
        <ul>
          <li>The revised seven-factor classifier is pending documented approval. Station / Stop, Time of Day, Day of Week, and Month of Year have no automatic severity scores. Only explicit approved mappings are applied. Numerical quartiles use reviewed training data; constant factors remain unresolved. Regression predictions remain available independently.</li>
          <li>Vehicle Frequency means actual recorded operations per hour; Passenger Volume counts recorded passengers in a documented observation window. Use the observation definition and units recorded in the selected dataset's research documentation; the application does not infer or convert units.</li>
          <li>The three-arm protocol includes an original-data baseline (A), reviewed Traditional MLR (B), and reviewed Enhanced MLR (C). If no records change, the system reports that no correction/exclusion benefit was demonstrated. Document this protocol in the thesis before interpreting its results.</li>
          <li>The thesis does not fully specify factor thresholds, score weights, or the overall cutoffs; document and justify the actual configured rules before claiming operational validity.</li>
          <li>Raw negative predictions remain in MSE and RMSE. The existing implementation uses zero for classification only; this rule must be documented in the thesis.</li>
        </ul>
        <p>Source: supplied thesis, Sections 1.3, 1.5, 3.1–3.4 and 4.1–4.3, together with the explicit implementation brief. The web interface is an implementation choice, not the research contribution.</p>
      </div>
    </details>
  </article>
}
