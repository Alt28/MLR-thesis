# Verified reference guide

Checked 4 November 2026 using web search, publisher/documentation pages, and GitHub's repository connector. These sources support related work or implementation choices; none validates the proposed seven-factor station thresholds or guarantees that interaction-enhanced MLR will outperform the baseline. The thesis bibliography has not been fully audited.

## Method and software sources

1. **NIST/SEMATECH. _e-Handbook of Statistical Methods_, section 7.1.6, “What are outliers in the data?”** [Official handbook](https://www.itl.nist.gov/div898/handbook/prc/section1/prc16.htm). Defines IQR and the 1.5-IQR inner fences. Useful for the screening equations. Its worked example uses a particular percentile convention; this implementation explicitly uses pandas linear interpolation. A flag is evidence to investigate, not proof of a recording error.

2. **Scikit-learn developers. _LinearRegression_ API documentation.** [Official documentation](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html). Describes ordinary least squares and coefficient/intercept attributes. This is the implementation used for both models, with no penalty term or coefficient constraints.

3. **Scikit-learn developers. _Linear Models_, polynomial regression and basis functions.** [Official guide](https://scikit-learn.org/stable/modules/linear_model.html#polynomial-regression-extending-linear-models-with-basis-functions). Supports extending a linear model through transformed features while retaining linear estimation in its coefficients. The present implementation constructs only the researcher-selected interaction terms, rather than every polynomial combination.

4. **Scikit-learn developers. _Common pitfalls and recommended practices_, data leakage.** [Official guide](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage). Supports splitting before learned preprocessing and deriving preprocessing information only from training data. Relevant to encoding, IQR bounds, and classification quartiles.

5. **Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. _Journal of Machine Learning Research, 12_(85), 2825–2830.** [Journal article](https://www.jmlr.org/papers/v12/pedregosa11a.html). Appropriate academic citation for the library. Cite the software version used in the experiment as well.

6. **Scikit-learn developers. _mean_squared_error_.** [Official API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_squared_error.html). Implementation reference for MSE. This project computes RMSE as the square root of MSE and evaluates raw OLS predictions.

## Transportation related work

7. **Feng, S., Wu, H., Sun, X., & Li, Z. (2016). Factors on perceived waiting time and implications on passengers’ satisfaction with waiting time. _Promet – Traffic & Transportation, 28_(2), 155–163.** [Journal record and full-text link](https://hrcak.srce.hr/en/156726) · [DOI](https://doi.org/10.7307/ptt.v28i2.1726). Uses multiple linear regression to investigate perceived waiting time. Useful as a transportation regression precedent, but perceived waiting time is a different outcome from actual recorded waiting time, and its predictors are not your six-variable specification.

8. **Zhang, Q., Ma, Z., Zhang, P., Ling, Y., & Jenelius, E. (2026; first published online 26 June 2024). Real-time bus arrival delays analysis using seemingly unrelated regression model. _Transportation, 53_, 571–602.** [Publisher article](https://link.springer.com/article/10.1007/s11116-024-10507-3) · [DOI](https://doi.org/10.1007/s11116-024-10507-3). Examines how explanatory effects differ across bus stops using Stockholm operational data. Relevant background for context-dependent transportation relationships. It uses SURE and real-time operational inputs, so it is **related work, not the algorithm implemented here**.

## GitHub references

9. **scikit-learn/scikit-learn.** [Official repository](https://github.com/scikit-learn/scikit-learn) · [README inspected](https://github.com/scikit-learn/scikit-learn/blob/main/README.rst). The primary implementation reference and dependency, distributed under the BSD 3-Clause license. Prefer its supported API over copying an unrelated student project.

10. **jknific123/Linear-regression.** [Repository](https://github.com/jknific123/Linear-regression) · [README inspected](https://github.com/jknific123/Linear-regression/blob/master/README.md) · [Estimator code inspected](https://github.com/jknific123/Linear-regression/blob/master/linear.py). A bus-arrival forecasting project describing a December 2012 prediction task. Its estimator uses numerical optimization and includes an optional L2 penalty parameter. Therefore it is useful for examining an existing bus-regression project, **not a drop-in implementation of this thesis**. The repository root inspected did not list a license file; no code or data was copied.

## How to use these in the thesis

Additional web implementation references checked on 4 November 2026:

- [FastAPI: Request Files](https://fastapi.tiangolo.com/tutorial/request-files/) documents multipart uploads and `UploadFile`, used for CSV/Excel input.
- [FastAPI official GitHub repository](https://github.com/fastapi/fastapi) is the backend framework's source reference.
- [Vite: Getting Started](https://vite.dev/guide/) documents frontend scaffolding and local development/build workflows. This implementation uses the pinned Vite 7 version in `frontend/package-lock.json`; the current documentation may describe a later major version.

These support the web implementation, not the thesis's statistical claims.

Use transportation papers in related literature/studies, NIST for the IQR equations, and the official regression documentation plus Pedregosa et al. for implementation. Label GitHub examples as software references, not peer-reviewed evidence. Cite the specific source that supports each claim, rather than attaching a generic homepage.

The seven equal severity weights, the waiting-time cutoffs, quartile severity assignments, and station-score bands come from the supplied implementation notes. Document them as researcher-defined rules that require operational justification and evaluation. The sources above do not establish them as transportation standards.

Do not transplant another project's target, predictor meanings, or reported metrics into your experiment. Arrival delay, journey time, perceived waiting time, and actual passenger waiting time are distinct outcomes. None of the inspected sources was established to provide a ready-to-use dataset containing all six required predictors plus actual waiting time.
