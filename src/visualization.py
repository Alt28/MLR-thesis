"""Exportable Matplotlib figures; no invented observations or performance values."""
from pathlib import Path
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from .config import TARGET, LABELS, ROW_ID

BLUE = "#2563a6"
TEAL = "#0b877c"


def new_chart(title, xlabel="", ylabel=""):
    figure = Figure(figsize=(8, 5), layout="constrained")
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    axis.set(title=title, xlabel=xlabel, ylabel=ylabel)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", alpha=.18)
    axis.set_axisbelow(True)
    return figure, axis


def create_figures(result, dark=False):
    figures = {}
    p = result.predictions
    blue, teal = ("#8dacf0", "#72d9b7") if dark else (BLUE, TEAL)
    for prefix, color in [("Baseline", blue), ("Enhanced", teal)]:
        figure, ax = new_chart(f"Actual vs {prefix} MLR predicted wait", "Actual waiting time (minutes)", "Raw predicted waiting time (minutes)")
        y = p[f"{prefix} Predicted Waiting Time"]
        ax.scatter(p[TARGET], y, color=color, alpha=.7, s=27)
        lo, hi = min(p[TARGET].min(), y.min()), max(p[TARGET].max(), y.max())
        if lo == hi: hi = lo + 1
        ax.plot([lo, hi], [lo, hi], color="#777777", linestyle="--", label="Perfect agreement")
        ax.legend(frameon=False)
        figures[f"actual_vs_{prefix.lower()}"] = figure
    for metric, unit in [("MSE", "minutes squared"), ("RMSE", "minutes")]:
        figure, ax = new_chart(f"Held-out {metric} comparison", ylabel=f"{metric} ({unit})")
        bars = ax.bar(result.metrics.Model, result.metrics[metric], color=[blue, teal], width=.55)
        ax.bar_label(bars, fmt="%.4g", padding=4)
        ax.margins(y=.18)
        figures[metric.lower()] = figure
    figure, ax = new_chart("Station classifications on held-out observations", ylabel="Observation count")
    categories = [*LABELS, "Pending configuration"]
    counts = p["Overall Station Classification"].value_counts().reindex(categories, fill_value=0)
    bars = ax.bar([x.replace(" ", "\n", 1) for x in categories], counts, color=[teal, "#d6b353", "#d48947", "#bd5555", "#9da5b0"])
    ax.bar_label(bars, padding=3)
    ax.margins(y=.15)
    figures["station_classifications"] = figure
    figure, ax = new_chart("IQR screening of original training observations", ylabel="Unique observation count")
    flagged = result.prepared.flags[ROW_ID].nunique()
    bars = ax.bar(["Not flagged", "Flagged for review"], [len(result.prepared.training) - flagged, flagged], color=[teal, "#c18446"])
    ax.bar_label(bars, padding=3)
    ax.margins(y=.15)
    figures["iqr_screening"] = figure
    x = result.models.features.transform(result.training, enhanced=True)
    coefficient_rows = result.models.coefficients()
    interaction_rows = coefficient_rows[(coefficient_rows.Model == "Enhanced MLR") & coefficient_rows.Type.isin(["pairwise", "higher-order"])]
    for number, (_, row) in enumerate(interaction_rows.iterrows(), 1):
        figure, ax = new_chart(f"Interaction term {number}: fitted contribution", "Observed training interaction product", "Term contribution to wait (minutes)")
        ax.scatter(x[row.Term], x[row.Term] * row.Coefficient, color=teal, s=24, alpha=.65)
        figure.text(.5, .015, row.Term + "\nOne fitted term only; not a causal effect or total predicted wait.", ha="center", fontsize=8, wrap=True)
        figure.get_layout_engine().set(rect=(0, .1, 1, .9))
        figures[f"interaction_{number:02d}"] = figure
    if dark:
        from matplotlib.text import Text
        for figure in figures.values():
            figure.set_facecolor("#161d26")
            for ax in figure.axes:
                ax.set_facecolor("#161d26")
                ax.tick_params(colors="#a1b0bf")
                for spine in ax.spines.values(): spine.set_color("#526174")
                ax.grid(axis="y", color="#91a4b8", alpha=.15)
            for text in figure.findobj(match=Text): text.set_color("#dce6f0")
    return figures


def save_figures(result, directory, dark=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    names = []
    for name, figure in create_figures(result, dark=dark).items():
        path = directory / f"{name}.png"
        figure.savefig(path, dpi=180)
        names.append(path.name)
        figure.clear()
    return names
