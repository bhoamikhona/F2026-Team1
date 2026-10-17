"""List trial referral thresholds without selecting or freezing one.

Uses full-validation Platt fits, so these are descriptive selection results,
not independent performance estimates. No abstention rule is applied.
"""

import argparse
import csv
import hashlib
import json

import numpy as np
import torch

from calibrate_models import PROJECT_ROOT, SEEDS, load_validation_labels
from check_calibration_cv import read_predictions


def select_operating_points(results):
    """Compare exploratory targets, minimizing false referrals at each target."""
    comparison = []
    for seed in SEEDS:
        for target in (0.90, 0.95, 1.0):
            eligible = [r for r in results
                        if r["seed"] == seed and r["sensitivity"] >= target]
            # Highest specificity first; highest threshold breaks identical decisions.
            chosen = max(eligible, key=lambda r: (r["specificity"], r["threshold"]))
            comparison.append({"target_sensitivity": target, **chosen})
    return comparison


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disease", choices=("glaucoma", "cataract"), default="glaucoma")
    disease = parser.parse_args().disease
    output = PROJECT_ROOT / "results" / "calibration"
    source = output / f"{disease}_calibration_trial.json"
    trial = json.loads(source.read_text(encoding="utf-8"))
    if trial.get("frozen") is not False or trial.get("fit_split") != "validation":
        raise ValueError("Expected unfrozen validation calibration trials")
    rows = load_validation_labels()
    labels = np.array([r[disease] for r in rows])
    runs = {run["seed"]: run for run in trial["runs"]}
    results = []
    for seed in SEEDS:
        logits, digest = read_predictions(seed, rows, disease)
        run = runs[seed]
        if digest != run["prediction_sha256"]:
            raise ValueError("Predictions changed since calibration; rerun the trial")
        scale, offset = run["platt"]["scale"], run["platt"]["offset"]
        if not np.isfinite(scale) or scale <= 0 or not np.isfinite(offset):
            raise ValueError("Invalid Platt parameters")
        probabilities = torch.sigmoid(scale * logits + offset).numpy()
        # Include all score boundaries, plus refer-all and refer-none endpoints.
        thresholds = np.unique(np.r_[0.0, probabilities, 1.0,
                                    np.nextafter(probabilities.max(), np.inf)])
        for threshold in thresholds:
            refer = probabilities >= threshold
            tp = int(np.sum(refer & (labels == 1)))
            fp = int(np.sum(refer & (labels == 0)))
            fn = int(np.sum(~refer & (labels == 1)))
            tn = int(np.sum(~refer & (labels == 0)))
            results.append({
                "status": "trial", "seed": seed, "threshold": float(threshold),
                "tp": tp, "fp": fp, "tn": tn, "fn": fn,
                "sensitivity": tp / (tp + fn),
                "specificity": tn / (tn + fp),
                "precision": tp / (tp + fp) if tp + fp else None,
                "referral_count": tp + fp, "referral_rate": (tp + fp) / len(rows),
            })
    if not results:
        raise RuntimeError("No threshold candidates generated")

    destination = output / f"{disease}_threshold_candidates_trial.csv"
    with destination.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    metadata = {
        "status": "trial", "disease": disease, "frozen": False, "method": "platt",
        "split": "validation", "sample_count_per_seed": len(rows),
        "rule": "Refer when calibrated probability >= threshold",
        "abstention_applied": False, "selected_thresholds": None,
        "calibration_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "limitations": "Same validation data used for calibration and candidate comparison; not independent test results.",
    }
    (output / f"{disease}_threshold_candidates_trial.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    comparison = select_operating_points(results)
    with (output / f"{disease}_threshold_comparison_trial.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(comparison[0]))
        writer.writeheader()
        writer.writerows(comparison)
    for row in comparison:
        print(f"Seed {row['seed']}, target {row['target_sensitivity']:.0%}: "
              f"caught {row['tp']}/{int(labels.sum())}, missed {row['fn']}, "
              f"false referrals {row['fp']}, total referrals {row['referral_count']}")
    print(f"Saved {len(results)} threshold candidates for three seeds: {destination}")
    print("No cutoff selected. Sensitivity target and abstention rule remain undecided.")


if __name__ == "__main__":
    main()
