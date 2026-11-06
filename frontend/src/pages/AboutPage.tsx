export function AboutPage() {
  return <article className="methodology">
    <span className="eyebrow">ABOUT THE RESEARCH</span>
    <h1>How it works</h1>
    <p className="intro">An interface for demonstrating enhanced Multiple Linear Regression for train and bus waiting-time prediction.</p>
    <ol className="how-it-works">
      <li><h2>Upload transportation data</h2><p>Choose a CSV or XLSX file containing the six transportation predictors and actual waiting time.</p></li>
      <li><h2>Review unusual observations when needed</h2><p>Analyze Dataset checks the data. If observations need a researcher decision, retain, correct, or exclude them before continuing.</p></li>
      <li><h2>Compare Traditional and Enhanced MLR</h2><p>The main comparison uses reviewed data for both models. An additional original-data baseline separates the effects of review decisions and interactions. All three experiments use the same test observations. Bus/train metrics are reported as subsets of the pooled model evaluation.</p></li>
      <li><h2>View predicted waiting time</h2><p>The enhanced prediction is the main result. Choose a held-out observation to compare its prediction with the recorded actual value, or use View Details to predict new rows without actual waiting times.</p></li>
      <li><h2>Interpret station condition</h2><p>The Multi-Factor Threshold-Based Classification framework combines predicted waiting time with all six transportation factors. A station summary is available when Station ID or Station metadata is present.</p></li>
    </ol>
    <details className="disclosure">
      <summary>Methodology and research decisions</summary>
      <div className="disclosure-body">
        <h2>What is preserved</h2>
        <p>The six predictors are Traffic Condition, Weather Condition, Passenger Volume, Route Distance, Vehicle Frequency, and Time of Day. Actual Waiting Time is required for evaluation; a separate prediction-only workflow accepts predictor rows without it.</p>
        <p>The default split is random 80/20 with seed 42 and is fixed before fitting IQR bounds, categorical encodings, or severity quartiles. IQR flags are retained unless the researcher explicitly corrects or excludes them. Repeated trips or time-dependent records may need a separately approved grouped or chronological evaluation design.</p>
        <p>Traditional MLR uses main effects. Enhanced MLR keeps those main effects and adds selected pairwise and higher-order interactions. The main B vs C comparison uses the same reviewed training rows and test rows. Arm A uses the original training rows; A vs B examines recorded review decisions. Lower MSE and RMSE indicate smaller prediction errors; improvement is not assumed.</p>
        <h2>Station classification</h2>
        <p>Each of the six predictors and enhanced predicted waiting time receives a severity score: Normal = 0, Minor = 1, Moderate = 2, Severe = 3. The multi-factor score is their sum divided by seven.</p>
        <p>The supplied implementation brief defines waiting-time bands at 15, 20, and 25 minutes and overall-score boundaries at 0.75, 1.50, and 2.25. The PDF describes the framework without fully specifying these rules. Applied values are recorded in Advanced Settings and exported with the results.</p>
        <p>For each station in the held-out data, the optional summary averages classifiable observation scores and reports unresolved counts. It describes the analyzed test observations; it is not a real-time station condition or independently validated classification.</p>
        <h2>Research evidence</h2>
        <p>Prototype or simulated data tests software behavior. It does not establish real-world predictive performance. Source declarations and researcher notes are preserved in exports. Mode metrics are computed for bus/train subsets of one pooled model, not separately fitted mode-specific models.</p>
        <h2>Requires Researcher Decision</h2>
        <ul>
          <li>Category means are compared with reviewed-training Actual Waiting Time quartiles unless a configured mapping overrides them. Unspecified numerical directions use the training Pearson correlation sign. Constant variables or collapsed quartiles remain unclassified; missing mappings and units require a researcher decision.</li>
          <li>The selected system protocol defines Vehicle Frequency as observed service frequency in vehicles/hour, while original thesis Table 3.1 says number of available vehicles. Reconcile this change with the adviser-approved thesis. The application does not infer or convert units.</li>
          <li>The three-arm protocol includes an original-data baseline (A), reviewed Traditional MLR (B), and reviewed Enhanced MLR (C). If no records change, the system reports that no correction/exclusion benefit was demonstrated. Document this protocol in the thesis before interpreting its results.</li>
          <li>The thesis does not fully specify factor thresholds, score weights, or the overall cutoffs; document and justify the actual configured rules before claiming operational validity.</li>
          <li>Raw negative predictions remain in MSE and RMSE. The existing implementation uses zero for classification only; this rule must be documented in the thesis.</li>
        </ul>
        <p>Source: supplied thesis, Sections 1.3, 1.5, 3.1–3.4 and 4.1–4.3, together with the explicit implementation brief. The web interface is an implementation choice, not the research contribution.</p>
      </div>
    </details>
  </article>
}
