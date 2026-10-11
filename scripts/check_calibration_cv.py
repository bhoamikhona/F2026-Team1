"""Compare disease calibration on held-out validation patients only.

This is a trial method comparison, not an independent test-set evaluation.
The base models already used validation data for checkpoint selection.
No thresholds or final calibration parameters are frozen here.
"""

import argparse
import csv
import hashlib
import json

import numpy as np
import torch
from sklearn.model_selection import StratifiedGroupKFold

from dual.config import SEED, set_seed
from calibrate_models import (
    PROJECT_ROOT, SEEDS, load_validation_labels,
    fit_temperature, fit_platt_scaling, calculate_log_loss,
)


def read_predictions(seed, rows, disease="glaucoma"):
    """Align saved predictions by filename and verify their validation labels."""
    path = PROJECT_ROOT / "results" / "calibration" / f"{disease}_seed_{seed}_validation.csv"
    with path.open(newline="", encoding="utf-8") as file:
        predictions = list(csv.DictReader(file))
    by_name = {row["filename"]: row for row in predictions}
    if len(by_name) != len(predictions) or set(by_name) != {r["filename"] for r in rows}:
        raise ValueError(f"Missing, extra or duplicate validation filenames for seed {seed}")
    if any(int(by_name[r["filename"]][disease]) != r[disease] for r in rows):
        raise ValueError(f"Incorrect validation labels for seed {seed}")
    logits = torch.tensor(
        [float(by_name[r["filename"]]["logit"]) for r in rows], dtype=torch.float64
    )
    if not torch.isfinite(logits).all():
        raise ValueError(f"Nonfinite scores for seed {seed}")
    return logits, hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(logits, labels, disease="glaucoma"):
    """Calculate pooled out-of-fold metrics and ten equal-width probability bins."""
    probabilities = torch.sigmoid(logits)
    bins = []
    ece = 0.0
    for i in range(10):
        lower, upper = i / 10, (i + 1) / 10
        mask = (probabilities >= lower) & (
            (probabilities <= upper) if i == 9 else (probabilities < upper)
        )
        count = int(mask.sum())
        predicted = float(probabilities[mask].mean()) if count else None
        actual = float(labels[mask].mean()) if count else None
        if count:
            ece += count / len(labels) * abs(predicted - actual)
        bins.append(dict(lower=lower, upper=upper, count=count,
                         **{f"{disease}_count": int(labels[mask].sum())},
                         mean_probability=predicted, observed_rate=actual))
    return {
        "log_loss": calculate_log_loss(logits, labels),
        "brier_score": float(((probabilities - labels) ** 2).mean()),
        "ece_10_equal_width_bins": ece,
        "mean_probability": float(probabilities.mean()),
        "observed_rate": float(labels.mean()),
    }, bins


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disease", choices=("glaucoma", "cataract"), default="glaucoma")
    disease = parser.parse_args().disease
    set_seed()
    rows = load_validation_labels()
    labels = torch.tensor([r[disease] for r in rows], dtype=torch.float64)
    groups = np.array([r["patient_id"] for r in rows])
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    splits = list(splitter.split(np.zeros(len(rows)), labels.numpy(), groups))
    assignment = np.full(len(rows), -1, dtype=int)
    folds = []
    for fold, (train, held) in enumerate(splits):
        if set(groups[train]) & set(groups[held]):
            raise ValueError("Patient leakage across calibration folds")
        if labels[train].unique().numel() != 2 or labels[held].unique().numel() != 2:
            raise ValueError("Each fitting and held-out fold must contain both classes")
        if (assignment[held] != -1).any():
            raise ValueError("Repeated held-out prediction")
        assignment[held] = fold
        folds.append({"fold": fold + 1, "fit_images": len(train),
                      "held_out_images": len(held),
                      "fit_patients": len(set(groups[train])),
                      "held_out_patients": len(set(groups[held])),
                      f"held_out_{disease}_cases": int(labels[held].sum())})
    if (assignment < 0).any():
        raise ValueError("Some validation photos were not held out")

    summary = {
        "status": "trial", "frozen": False, "split": "validation",
        "method": "5-fold stratified patient-grouped cross-validation",
        "random_seed": SEED, "sample_count": len(rows),
        "patient_count": len(set(groups)), "folds": folds,
        "limitations": [
            "Calibration fits exclude each held-out patient's eyes.",
            "Base models previously used validation data for checkpoint selection.",
            "Method comparison uses validation data and is not a final test estimate.",
            f"Only {int(labels.sum())} {disease} eyes; sparse probability bins have high uncertainty.",
        ],
        "decision_threshold": None, "abstention_cutoff": None, "runs": [],
    }
    prediction_rows, bin_rows = [], []
    for seed in SEEDS:
        logits, digest = read_predictions(seed, rows, disease)
        outputs = {"uncalibrated": logits.clone(),
                   "temperature": torch.empty_like(logits),
                   "platt": torch.empty_like(logits)}
        parameters = []
        for fold, (train, held) in enumerate(splits):
            temperature = fit_temperature(logits[train], labels[train])
            scale, offset = fit_platt_scaling(logits[train], labels[train])
            if not np.isfinite(temperature) or temperature <= 0:
                raise ValueError("Invalid fitted temperature")
            outputs["temperature"][held] = logits[held] / temperature
            outputs["platt"][held] = scale * logits[held] + offset
            parameters.append(dict(fold=fold + 1, temperature=temperature,
                                   platt_scale=scale, platt_offset=offset))
        run = {"seed": seed, "prediction_sha256": digest,
               "fold_parameters": parameters, "metrics": {}}
        for method, adjusted in outputs.items():
            if not torch.isfinite(adjusted).all():
                raise ValueError("Nonfinite out-of-fold scores")
            result, bins = metrics(adjusted, labels, disease)
            run["metrics"][method] = result
            bin_rows.extend(dict(seed=seed, method=method, **b) for b in bins)
            print(f"Seed {seed}, {method}: held-out log loss {result['log_loss']:.6f}, "
                  f"Brier {result['brier_score']:.6f}", flush=True)
        summary["runs"].append(run)
        probabilities = {k: torch.sigmoid(v).tolist() for k, v in outputs.items()}
        for i, row in enumerate(rows):
            prediction_rows.append({"seed": seed, "fold": int(assignment[i]) + 1,
                                    "patient_id": row["patient_id"],
                                    "filename": row["filename"], disease: row[disease],
                                    **{k: v[i] for k, v in probabilities.items()}})

    output = PROJECT_ROOT / "results" / "calibration"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{disease}_calibration_cv_trial.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    for name, records in [("predictions", prediction_rows), ("bins", bin_rows)]:
        with (output / f"{disease}_calibration_cv_trial_{name}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    print("Saved patient-grouped cross-validation trials. No settings frozen.")


if __name__ == "__main__":
    main()
