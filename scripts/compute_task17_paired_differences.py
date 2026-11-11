"""Compare saved single/shared predictions using paired bootstrap AUROC differences."""

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from compute_internal_auc_ci import (
    bootstrap_patient_indices, make_arrays, prepare_data, validate_source_manifest,
)
from external_metrics import bootstrap_indices

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (42, 43, 44)
REPLICATES = 2000


def read_csv(path):
    """Read a saved result without modifying it."""
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def paired_result(labels, single, shared, draws):
    """Subtract AUROCs within each shared resample, not interval endpoints."""
    labels, single, shared = map(np.asarray, (labels, single, shared))
    if labels.ndim != 1 or single.shape != labels.shape or shared.shape != labels.shape:
        raise ValueError("Prediction vectors must be aligned")
    if set(np.unique(labels)) != {0, 1} or not np.isfinite([single, shared]).all():
        raise ValueError("Expected binary labels and finite scores")
    if not len(draws):
        raise ValueError("Bootstrap draws are required")
    points = [roc_auc_score(labels, score) for score in (single, shared)]
    samples = np.array([[roc_auc_score(labels[index], score[index])
                         for score in (single, shared)] for index in draws])
    interval = np.quantile(samples[:, 1] - samples[:, 0], [0.025, 0.975])
    individual = np.quantile(samples, [0.025, 0.975], axis=0)
    return dict(single_auroc=points[0], shared_auroc=points[1],
                difference=points[1] - points[0], ci_low=interval[0], ci_high=interval[1],
                single_ci_low=individual[0, 0], single_ci_high=individual[1, 0],
                shared_ci_low=individual[0, 1], shared_ci_high=individual[1, 1])


def check_reference(result, single, shared, low, high):
    """Require reproduction of both models' original AUROC and intervals."""
    for kind, reference in (("single", single), ("shared", shared)):
        for output, source in (("auroc", "auroc"), ("ci_low", low), ("ci_high", high)):
            if not np.isclose(result[f"{kind}_{output}"], float(reference[source]),
                              rtol=0, atol=1e-10):
                raise ValueError(f"Original {kind} {output} was not reproduced")


def align_external(rows):
    """Align by image path in the original reference order; reject missing/duplicate eyes."""
    groups = {}
    for kind in ("single", "shared"):
        for seed in SEEDS:
            selected = [r for r in rows if r["model_kind"] == kind and int(r["seed"]) == seed]
            paths = [r["path"] for r in selected]
            if not paths or len(paths) != len(set(paths)):
                raise ValueError("Missing predictions or duplicate image paths")
            groups[kind, seed] = {r["path"]: r for r in selected}
    paths = list(groups["single", 42])
    labels = np.array([int(groups["single", 42][p]["label"]) for p in paths])
    arrays = {}
    for run, records in groups.items():
        if set(records) != set(paths):
            raise ValueError("Paired image sets differ")
        if not np.array_equal(labels, [int(records[p]["label"]) for p in paths]):
            raise ValueError("Paired labels differ")
        arrays[run] = np.array([float(records[p]["raw_logit"]) for p in paths])
    return labels, arrays


def main():
    """Reproduce original intervals, then save paired differences and input fingerprints."""
    internal = ROOT / "results/task13/internal_test"
    external = ROOT / "results/external/frozen_run_20261030"
    source = validate_source_manifest(internal)
    patients, arrays = make_arrays(prepare_data(internal, source))
    labels_by_disease = {d: arrays["single", d, 42][0] for d in ("cataract", "glaucoma")}
    draws, attempts = bootstrap_patient_indices(patients, labels_by_disease, REPLICATES, 42, 10000)
    reference = {(r["model_kind"], r["disease"], int(r["seed"])): r for r in
                 read_csv(ROOT / "results/task13/internal_auc_ci/per_seed_auc_ci.csv")}
    results = []
    for disease, labels in labels_by_disease.items():
        for seed in SEEDS:
            result = paired_result(labels, arrays["single", disease, seed][1],
                                   arrays["shared", disease, seed][1], draws)
            check_reference(result, reference["single", disease, seed],
                            reference["shared", disease, seed], "ci_lower_95", "ci_upper_95")
            results.append(dict(dataset="ODIR internal", disease=disease, seed=seed,
                                resampling_unit="patient", replicates=len(draws), attempts=attempts, **result))
        print(f"Verified internal {disease}", flush=True)
    predictions = read_csv(external / "predictions.csv")
    metrics = {(r["dataset"], r["disease"], r["model_kind"], int(r["seed"])): r
               for r in read_csv(external / "metrics.csv") if r["policy"] == "threshold_only"}
    for dataset in ("ORIGA", "DRISHTI-GS", "ACRIMA", "retina_dataset_2016"):
        disease = "glaucoma"
        selected = [r for r in predictions if r["dataset"] == dataset and r["disease"] == disease]
        labels, scores = align_external(selected)
        draws, attempts = bootstrap_indices(labels, REPLICATES, 42)
        for seed in SEEDS:
            result = paired_result(labels, scores["single", seed], scores["shared", seed], draws)
            check_reference(result, metrics[dataset, disease, "single", seed],
                            metrics[dataset, disease, "shared", seed], "auroc_ci_low", "auroc_ci_high")
            results.append(dict(dataset=dataset, disease=disease, seed=seed,
                                resampling_unit="image", replicates=len(draws), attempts=attempts, **result))
        print(f"Verified external {dataset}", flush=True)
    output = ROOT / "results/task17"
    output.mkdir(exist_ok=True)
    with (output / "paired_auroc_differences.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    inputs = list(internal.glob("*.csv")) + [external / "predictions.csv", external / "metrics.csv",
             ROOT / "results/task13/internal_auc_ci/per_seed_auc_ci.csv"]
    manifest = dict(replicates=REPLICATES, random_seed=42, interval="paired percentile 95%",
                    original_intervals_reproduced=True,
                    source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in inputs})
    (output / "paired_analysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
