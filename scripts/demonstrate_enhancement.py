"""Known-answer demonstration of what the enhanced MLR workflow can and cannot detect.

Run from the project root:
    .\\.venv\\Scripts\\python.exe scripts\\demonstrate_enhancement.py

Every dataset here is SIMULATED with a known true equation. This is a method-verification
(simulation) check: it shows that the software recovers effects that truly exist and does not
invent effects that do not. It is NOT evidence about real train or bus waiting times.
"""
from pathlib import Path
import shutil
import sys
import warnings

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
warnings.simplefilter("ignore")

from src.config import ResearchConfig, TARGET  # noqa: E402
from src.data_loader import split_dataset, validate_data  # noqa: E402
from src.experiment import prepare_experiment, run_experiment  # noqa: E402
from src.export import export_experiment  # noqa: E402

TRUE_INTERACTION = -0.003  # minutes per (passenger × vehicle/hour)
TRUE_PEAK_INTERACTION = -0.002  # extra effect of the same product during peak periods (higher-order term)
OUTPUT = ROOT / "outputs" / "enhancement_demonstration"
CONFIG = dict(vehicle_frequency_unit="vehicles/hour (simulated)", route_distance_unit="km (simulated)",
              research_notes={"source_type": "simulated"})


def simulate(n=500, interaction=0.0, peak_interaction=0.0, seed=11):
    rng = np.random.default_rng(seed)
    traffic = rng.choice(["Light", "Moderate", "Heavy"], n, p=[.35, .4, .25])
    weather = rng.choice(["Clear", "Cloudy", "Rain", "Heavy Rain"], n, p=[.4, .3, .2, .1])
    time = rng.choice(["Off-Peak", "Mid-Day", "Peak Morning", "Peak Evening"], n)
    peak = np.isin(time, ["Peak Morning", "Peak Evening"])
    passengers = np.round(rng.uniform(20, 280, n) + 60 * peak)
    frequency = rng.integers(2, 16, n).astype(float)
    distance = np.round(rng.uniform(3, 30, n), 1)
    # The base of 25 minutes keeps every simulated wait positive, so no value has to be clipped.
    wait = (25 + pd.Series(traffic).map({"Light": 0, "Moderate": 2.5, "Heavy": 6}).to_numpy()
            + pd.Series(weather).map({"Clear": 0, "Cloudy": .8, "Rain": 2.5, "Heavy Rain": 5}).to_numpy()
            + 0.045 * passengers + 0.08 * distance - 0.45 * frequency
            + interaction * passengers * frequency          # crowding hurts more when vehicles are infrequent
            + peak_interaction * passengers * frequency * peak  # ... and differently again in peak periods
            + rng.normal(0, 2, n))
    if (wait <= 0).any():
        raise ValueError("Simulation produced a non-positive wait; adjust the base value.")
    return validate_data(pd.DataFrame({
        "Traffic Condition": traffic, "Weather Condition": weather, "Passenger Volume": passengers,
        "Route Distance": distance, "Vehicle Frequency": frequency, "Time of Day": time,
        TARGET: np.round(wait, 2),
    }))


def summarize(name, result, truth_note):
    v = result.validation
    arms = result.study["metrics"].set_index("Arm")
    heldout = v["heldout_significance"]
    cv = v["cv_summary"].set_index("Metric")
    cv_test = v["cv_significance"].iloc[0]
    coef = result.models.coefficients()
    enhanced = coef[coef.Model == "Enhanced MLR"].set_index("Term")
    peak_terms = [t for t in enhanced.index if t.startswith("Passenger Volume × Vehicle Frequency × Time of Day") and "Peak" in t]

    def p(comparison):
        row = heldout[(heldout.Comparison == comparison) & (heldout.Test == "Wilcoxon signed-rank")].iloc[0]
        return "n/a (identical)" if pd.isna(row["p-value"]) else f"{row['p-value']:.4g}"

    def describe(term):
        r = enhanced.loc[term]
        return f"{r.Coefficient:.5f} (95% CI {r['95% CI Lower']:.5f} to {r['95% CI Upper']:.5f}, p = {r['p-value']:.3g})"

    lines = [
        f"## {name}", "", truth_note, "",
        "| Arm | Model | MSE | RMSE | MAE | R² |", "|---|---|---|---|---|---|",
        *[f"| {arm} | {row.Model} | {row.MSE:.3f} | {row.RMSE:.3f} | {row.MAE:.3f} | {row.R2:.3f} |" for arm, row in arms.iterrows()],
        "",
        f"- Held-out Wilcoxon p-value: B vs C = {p('B vs C')}; A vs B = {p('A vs B')}.",
        f"- Cross-validation MSE (mean ± SD): Traditional {cv.loc['MSE', 'Baseline Mean']:.3f} ± {cv.loc['MSE', 'Baseline SD']:.3f}; "
        f"Enhanced {cv.loc['MSE', 'Enhanced Mean']:.3f} ± {cv.loc['MSE', 'Enhanced SD']:.3f}; "
        f"Enhanced better in {cv.loc['MSE', 'Folds Where Enhanced Is Better (%)']:.0f}% of {int(cv_test.Folds)} folds; "
        f"corrected t-test p = {cv_test['p-value']:.4g} ({cv_test.Result}).",
        f"- Pairwise Passenger Volume × Vehicle Frequency coefficient (Mid-Day reference): {describe('Passenger Volume × Vehicle Frequency')}.",
        *[f"- Higher-order {term.split(' × ')[-1]} coefficient: {describe(term)}." for term in peak_terms],
        f"- Station classification agreement (actual vs predicted wait): "
        f"{v['classification_agreement'].set_index('Measure').Value['Exact agreement (%)']:.1f}% exact.",
        "",
    ]
    return lines


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = [
        "# Known-answer demonstration of the enhanced MLR workflow", "",
        "All three datasets are **simulated** from equations whose true effects are known, so the software's "
        "answers can be checked against the truth. This verifies that the method works as designed; it says nothing "
        "about real waiting times. Real conclusions require the recorded dataset.", "",
    ]

    config = ResearchConfig(**CONFIG)
    interacting = run_experiment(prepare_experiment(simulate(interaction=TRUE_INTERACTION, peak_interaction=TRUE_PEAK_INTERACTION), config))
    report += summarize("1. Real pairwise and higher-order interactions exist", interacting,
                        f"True equation: Passenger Volume × Vehicle Frequency coefficient {TRUE_INTERACTION} in off-peak periods, "
                        f"plus an extra {TRUE_PEAK_INTERACTION} for the same product during Peak Morning and Peak Evening "
                        "(a three-way Passenger Volume × Vehicle Frequency × Time of Day effect). Expected: Enhanced MLR (C) "
                        "clearly beats Traditional MLR (B), the tests are significant, and the estimates are close to the truth "
                        "(Mid-Day is the reference category; Off-Peak should be near 0).")

    additive = run_experiment(prepare_experiment(simulate(interaction=0.0), config))
    report += summarize("2. No interaction exists (control)", additive,
                        "True equation is purely additive (interaction coefficient 0). Expected: no meaningful or "
                        "significant improvement, and a confidence interval that contains 0. This shows the system "
                        "does not invent an enhancement.")
    first, second = (r.models.coefficients().query("Model == 'Enhanced MLR'").set_index("Term").Coefficient
                     for r in (interacting, additive))
    truth = {"Passenger Volume × Vehicle Frequency": TRUE_INTERACTION,
             'Passenger Volume × Vehicle Frequency × Time of Day["Off-Peak"]': 0.0,
             'Passenger Volume × Vehicle Frequency × Time of Day["Peak Evening"]': TRUE_PEAK_INTERACTION,
             'Passenger Volume × Vehicle Frequency × Time of Day["Peak Morning"]': TRUE_PEAK_INTERACTION}
    report += ["### Exact check: case 1 minus case 2", "",
               "Cases 1 and 2 use the same random noise and differ only by the built-in interaction effects, so the "
               "difference between their estimated coefficients must equal the true effects.", "",
               "| Interaction term | Estimated difference | True effect |", "|---|---|---|",
               *[f"| {term} | {first[term] - second[term]:.5f} | {value:.5f} |" for term, value in truth.items()], ""]

    clean = simulate(interaction=TRUE_INTERACTION, seed=23)
    training_ids, _ = split_dataset(clean, config)
    errors = training_ids.index[:12]
    corrupted = clean.copy()
    corrupted.loc[errors, TARGET] = corrupted.loc[errors, TARGET] * 10  # e.g. 18.5 typed as 185
    prepared = prepare_experiment(corrupted, config)
    flagged = set(prepared.flags["Record ID"])
    decisions = {rid: {"action": "exclude", "reason": "Data-entry error: value is ten times the source record.", "corrections": {}}
                 for rid in errors if rid in flagged}
    decisions.update({rid: {"action": "retain", "reason": "Verified unusual but valid observation.", "corrections": {}}
                      for rid in flagged - set(decisions)})
    reviewed = run_experiment(prepared, decisions)
    report += summarize("3. Data-entry errors in the training data (IQR review)", reviewed,
                        f"Twelve training waits were multiplied by 10. IQR flagged {len(flagged)} training rows and caught "
                        f"{len(decisions) - len(flagged - set(errors))} of the 12 errors; those were excluded with a reason and "
                        "every other flagged row was retained. Expected: Arm B (reviewed) clearly beats Arm A (original).")

    for folder, result in (("1_real_interaction", interacting), ("2_no_interaction", additive), ("3_iqr_review", reviewed)):
        target = OUTPUT / folder
        if target.exists():
            shutil.rmtree(target)
        export_experiment(result, target)
    report += ["Full bundles (Excel, figures, METHODOLOGY.md) for each case are in the numbered folders next to this file.", ""]
    (OUTPUT / "DEMONSTRATION.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    main()
