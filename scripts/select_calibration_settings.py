"""Calculate reviewable validation-only settings for all nine Task 11 models.

The shared models have two heads, giving twelve calibrated head/seed pairs.
No test or holdout images are read, and settings are not frozen automatically.
"""

import csv
import json
import math
from pathlib import Path

import numpy as np
import torch
from sklearn.model_selection import StratifiedGroupKFold

from calibrate_models import (
    PROJECT_ROOT, SEEDS, LABELS_FILE, file_sha256, load_validation_labels,
    fit_platt_scaling, fit_temperature, calculate_log_loss, verify_prediction_metadata,
)
from check_calibration_cv import read_predictions, metrics
from calibrate_shared_models import read_shared_predictions, source_hashes

OUTPUT = PROJECT_ROOT / "results/calibration"


def validate_vectors(probabilities, labels):
    """Reject invalid values before selecting decisions."""
    p, y = np.asarray(probabilities, dtype=float), np.asarray(labels)
    if p.ndim != 1 or p.shape != y.shape or not len(p):
        raise ValueError("Expected matching nonempty vectors")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probabilities must be finite and between zero and one")
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("Both binary label classes are required")
    return p, y


def select_threshold(probabilities, labels):
    """Meet 90% sensitivity, then maximize specificity and the cutoff."""
    p, y = validate_vectors(probabilities, labels)
    positives, negatives = int(y.sum()), int((y == 0).sum())
    thresholds = np.unique(np.r_[0.0, p, np.nextafter(p.max(), np.inf)])
    candidates = []
    for threshold in thresholds:
        referred = p >= threshold
        tp = int(np.sum(referred & (y == 1)))
        tn = int(np.sum(~referred & (y == 0)))
        # Integer comparison means 35/39 does not round up to 90%.
        if 10 * tp >= 9 * positives:
            candidates.append((tn, float(threshold)))
    tn, threshold = max(candidates)
    return threshold, tn / negatives


def choose_margin(probabilities, threshold, fraction=0.05):
    """Include the nearest ceil(fraction*n) scores and all boundary ties."""
    p = np.asarray(probabilities, dtype=float)
    if p.ndim != 1 or len(p) == 0 or not np.isfinite(p).all():
        raise ValueError("Expected finite nonempty probability vector")
    if not 0 < fraction < 1 or not np.isfinite(threshold):
        raise ValueError("Invalid uncertainty policy")
    k = math.ceil(fraction * len(p))
    return float(np.partition(np.abs(p - threshold), k - 1)[k - 1])


def decision_metrics(probabilities, labels, threshold, margin=None):
    """Count uncertain referrals separately and include them in total referrals."""
    p, y = validate_vectors(probabilities, labels)
    uncertain = np.zeros(len(p), dtype=bool) if margin is None else np.abs(p - threshold) <= margin
    ordinary = (p >= threshold) & ~uncertain
    refer = ordinary | uncertain
    tp, fp = int(np.sum(refer & (y == 1))), int(np.sum(refer & (y == 0)))
    fn, tn = int(np.sum(~refer & (y == 1))), int(np.sum(~refer & (y == 0)))
    return dict(tp=tp, fp=fp, tn=tn, fn=fn, sensitivity=tp/(tp+fn),
                specificity=tn/(tn+fp), referral_count=tp+fp, referral_rate=float(refer.mean()),
                uncertain_count=int(uncertain.sum()), uncertain_rate=float(uncertain.mean()),
                ordinary_referral_count=int(ordinary.sum()), no_concern_count=int((~refer).sum()))


def compare_methods(logits, labels, groups):
    """Compare calibration on held-out patients within validation."""
    outputs = {"uncalibrated": logits.clone(), "temperature": torch.empty_like(logits),
               "platt": torch.empty_like(logits)}
    assignment = np.full(len(labels), -1)
    folds = []
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    for fold, (fit, held) in enumerate(splitter.split(np.zeros(len(labels)), labels.numpy(), groups)):
        if set(groups[fit]) & set(groups[held]) or (assignment[held] != -1).any():
            raise ValueError("Invalid patient-grouped folds")
        if labels[fit].unique().numel() != 2 or labels[held].unique().numel() != 2:
            raise ValueError("Both classes required in every fold")
        assignment[held] = fold
        temperature = fit_temperature(logits[fit], labels[fit])
        if not np.isfinite(temperature) or temperature <= 0:
            raise ValueError("Invalid temperature")
        scale, offset = fit_platt_scaling(logits[fit], labels[fit])
        outputs["temperature"][held] = logits[held] / temperature
        outputs["platt"][held] = scale * logits[held] + offset
        folds.append(dict(fold=fold, temperature=temperature, scale=scale, offset=offset))
    if (assignment < 0).any():
        raise ValueError("Missing held-out patient scores")
    comparison = {}
    for name, scores in outputs.items():
        if not torch.isfinite(scores).all():
            raise ValueError("Invalid out-of-fold scores")
        comparison[name] = metrics(scores, labels)[0]
    return comparison, outputs, assignment, folds


def main():
    torch.set_num_threads(4)
    rows = load_validation_labels()
    groups = np.array([r["patient_id"] for r in rows])
    sources = source_hashes(rows)
    runs, table, oof_rows = [], [], []
    shared = {seed: read_shared_predictions(seed, rows, sources) for seed in SEEDS}
    for model_kind in ("single", "shared"):
        for disease in ("cataract", "glaucoma"):
            labels = torch.tensor([r[disease] for r in rows], dtype=torch.float64)
            for seed in SEEDS:
                if model_kind == "shared":
                    logits, metadata = shared[seed][0][disease], shared[seed][1]
                else:
                    logits, _ = read_predictions(seed, rows, disease)
                    metadata = verify_prediction_metadata(disease, seed)
                cv, outputs, assignment, folds = compare_methods(logits, labels, groups)
                scale, offset = fit_platt_scaling(logits, labels)
                probabilities = torch.sigmoid(scale * logits + offset).numpy()
                threshold, objective = select_threshold(probabilities, labels.numpy())
                margin = choose_margin(probabilities, threshold)
                base = decision_metrics(probabilities, labels.numpy(), threshold)
                combined = decision_metrics(probabilities, labels.numpy(), threshold, margin)
                run = dict(model_kind=model_kind, disease=disease, seed=seed,
                           checkpoint=metadata["checkpoint"], checkpoint_sha256=metadata["checkpoint_sha256"],
                           prediction_sha256=metadata["prediction_sha256"],
                           method="platt", scale=scale, offset=offset, threshold=threshold,
                           uncertain_margin=margin, uncertainty_fraction_target=0.05,
                           selected_specificity=objective, sensitivity_floor=0.90,
                           calibration_cv=cv, cv_fold_parameters=folds,
                           best_cv_method=min(cv, key=lambda m: cv[m]["log_loss"]),
                           fit_log_loss=calculate_log_loss(scale*logits+offset, labels),
                           threshold_only=base, including_uncertainty=combined)
                runs.append(run)
                table.append(dict(model_kind=model_kind, disease=disease, seed=seed,
                                  threshold=threshold, margin=margin, **combined))
                for i, row in enumerate(rows):
                    oof_rows.append(dict(model_kind=model_kind, disease=disease, seed=seed,
                                         filename=row["filename"], patient_id=row["patient_id"],
                                         fold=int(assignment[i]), label=row[disease],
                                         **{m: float(torch.sigmoid(v[i])) for m, v in outputs.items()}))
                print(f"{model_kind} {disease} seed {seed}: threshold={threshold:.8f}, "
                      f"margin={margin:.8f}, referred={combined['referral_count']}/{len(rows)}, "
                      f"best CV method={run['best_cv_method']}", flush=True)
    settings = dict(status="pending_team_review", frozen=False, fit_split="validation",
                    sample_count=len(rows), positive_counts={d:sum(r[d] for r in rows) for d in ("cataract","glaucoma")},
                    labels_sha256=file_sha256(LABELS_FILE),
                    selection_script_sha256=file_sha256(Path(__file__)),
                    calibration_source_sha256={name:file_sha256(PROJECT_ROOT/"scripts"/name)
                                               for name in ("select_calibration_settings.py", "calibrate_models.py",
                                                            "check_calibration_cv.py", "calibrate_shared_models.py")},
                    policy={"calibration":"Positive-scale Platt fit per model, head and seed",
                            "threshold":"Sensitivity >= 0.90 before uncertainty; maximize specificity",
                            "tie_break":"Higher specificity, then higher threshold",
                            "uncertainty":"abs(p-threshold) <= kth nearest distance; k=ceil(0.05*n); include ties",
                            "referral":"Uncertain OR p >= threshold",
                            "aggregation":"No seed averaging or ensemble. Separate parameters for every checkpoint/head."},
                    limitations=["Validation reused for checkpoint and setting selection; not independent test performance.",
                                 "The 90% validation floor and 5% margin target are not clinical guarantees.",
                                 "Earlier single-model holdout results already exist; they were not used by this script.",
                                 "Team approval is required before freezing. Deployment must use settings for its exact checkpoint/head."], runs=runs)
    (OUTPUT / "settings_review.json").write_text(json.dumps(settings, indent=2, allow_nan=False)+"\n")
    for name, records in (("settings_review.csv",table),("settings_review_oof.csv",oof_rows)):
        with (OUTPUT/name).open("w",newline="") as file:
            writer=csv.DictWriter(file,fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    lines = ["# Task 12 settings for review", "", "Not frozen. Validation selection results, not independent test performance.",
             "", "Each model/head/seed has its own cutoff. Sensitivity and specificity below include uncertain referrals.",
             "", "| Model | Disease | Seed | Threshold | Margin | Sensitivity | Specificity | Referred | Uncertain |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        lines.append(f"| {r['model_kind']} | {r['disease']} | {r['seed']} | {r['threshold']:.8f} | "
                     f"{r['margin']:.8f} | {r['sensitivity']:.1%} | {r['specificity']:.1%} | "
                     f"{r['referral_count']}/{len(rows)} | {r['uncertain_count']}/{len(rows)} |")
    lines += ["", "Use the full precision JSON values, not rounded table values.", "",
              "Next: team review of the policy and settings, commit frozen values, then run the 21-eye holdout check without tuning."]
    (OUTPUT/"settings_review.md").write_text("\n".join(lines)+"\n")


if __name__ == "__main__":
    main()
