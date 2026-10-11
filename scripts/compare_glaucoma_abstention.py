"""Explore threshold-margin abstention on validation data; freeze nothing."""

import csv
import hashlib
import json
import math

import numpy as np
import torch

from calibrate_models import PROJECT_ROOT, SEEDS, load_validation_labels
from check_calibration_cv import read_predictions


def summarize(labels, probabilities, threshold, margin):
    """Count three outcomes; uncertain eyes are always referred."""
    uncertain = (np.abs(probabilities - threshold) <= margin
                 if margin is not None else np.zeros(len(labels), dtype=bool))
    ordinary_refer = (probabilities >= threshold) & ~uncertain
    no_concern = (probabilities < threshold) & ~uncertain
    referred = ordinary_refer | uncertain
    retained = ~uncertain
    errors = ((probabilities >= threshold) != labels) & retained
    return {
        "uncertain_count": int(uncertain.sum()),
        "uncertain_glaucoma": int((uncertain & (labels == 1)).sum()),
        "ordinary_refer_count": int(ordinary_refer.sum()),
        "no_concern_count": int(no_concern.sum()),
        "coverage": float(retained.mean()),
        "retained_error_rate": float(errors.sum() / retained.sum()) if retained.any() else None,
        "total_referred": int(referred.sum()),
        "glaucoma_referred": int((referred & (labels == 1)).sum()),
        "glaucoma_missed": int((no_concern & (labels == 1)).sum()),
        "non_glaucoma_referred": int((referred & (labels == 0)).sum()),
    }


def main():
    output = PROJECT_ROOT / "results" / "task12"
    calibration_path = output / "glaucoma_calibration_trial.json"
    comparison_path = output / "glaucoma_threshold_comparison_trial.csv"
    calibration = json.loads(calibration_path.read_text())
    if calibration.get("frozen") is not False or calibration.get("fit_split") != "validation":
        raise ValueError("Expected validation-only trial calibration")
    with comparison_path.open(newline="") as file:
        operating_points = list(csv.DictReader(file))
    expected = {(seed, target) for seed in SEEDS for target in (0.9, 0.95, 1.0)}
    keys = [(int(r["seed"]), float(r["target_sensitivity"])) for r in operating_points]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("Expected nine distinct trial operating points")
    rows = load_validation_labels()
    labels = np.array([r["glaucoma"] for r in rows])
    runs = {run["seed"]: run for run in calibration["runs"]}
    results = []
    for seed in SEEDS:
        logits, digest = read_predictions(seed, rows)
        run = runs[seed]
        if digest != run["prediction_sha256"]:
            raise ValueError("Prediction source changed; regenerate calibration")
        scale, offset = run["platt"]["scale"], run["platt"]["offset"]
        if not np.isfinite(scale) or scale <= 0 or not np.isfinite(offset):
            raise ValueError("Invalid calibration parameters")
        probabilities = torch.sigmoid(scale * logits + offset).numpy()
        for point in (r for r in operating_points if int(r["seed"]) == seed):
            threshold = float(point["threshold"])
            if point["status"] != "trial" or not np.isfinite(threshold):
                raise ValueError("Expected finite trial threshold")
            baseline = summarize(labels, probabilities, threshold, None)
            if (baseline["glaucoma_referred"] != int(point["tp"])
                    or baseline["non_glaucoma_referred"] != int(point["fp"])):
                raise ValueError("Stale threshold comparison; regenerate it first")
            distances = np.sort(np.abs(probabilities - threshold))
            for fraction in (0.0, 0.05, 0.10, 0.20):
                # Include ties: actual uncertain count may exceed requested fraction.
                margin = float(distances[math.ceil(fraction * len(rows)) - 1]) if fraction else None
                result = summarize(labels, probabilities, threshold, margin)
                results.append({
                    "seed": seed, "target_sensitivity": float(point["target_sensitivity"]),
                    "threshold": threshold, "requested_uncertain_fraction": fraction,
                    "margin": margin, **result,
                    "additional_referrals": result["total_referred"] - baseline["total_referred"],
                })
    destination = output / "glaucoma_abstention_comparison_trial.csv"
    with destination.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    metadata = {
        "status": "trial", "frozen": False, "selected_rule": None,
        "split": "validation", "sample_count_per_seed": len(rows),
        "rule": "Uncertain, refer if abs(Platt probability - disease threshold) <= margin; otherwise refer if probability >= threshold.",
        "margin_selection": "Order statistic covering at least 5%, 10%, or 20% of validation eyes; include ties. Zero is a no-abstention baseline.",
        "sources_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (calibration_path, comparison_path)},
        "limitations": [
            "Exploratory fractions and sensitivity targets are project comparisons, not clinical standards.",
            "Distance from the decision boundary is a heuristic, not proven uncertainty or photo quality detection.",
            "Same validation data fit calibration and select thresholds and margins; these are not independent test results.",
            "Retained error rate is dominated by the majority class; inspect missed glaucoma and referral burden as well.",
            "No holdout or external images used. No cataract or combined-head rule evaluated.",
        ],
    }
    (output / "glaucoma_abstention_comparison_trial.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n"
    )
    print(f"Saved {len(results)} trial comparisons: {destination}")
    print("No uncertainty cutoff selected or frozen.")


if __name__ == "__main__":
    main()
