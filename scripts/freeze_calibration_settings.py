"""Verify the reviewed CSV on validation scores and save immutable final settings.

Does not open holdout or test images. Commit the output before holdout evaluation.
"""

import csv
import json
from pathlib import Path

import numpy as np
import torch

from calibrate_models import PROJECT_ROOT, LABELS_FILE, file_sha256, load_validation_labels
from check_calibration_cv import read_predictions
from calibrate_shared_models import read_shared_predictions, source_hashes
from select_calibration_settings import select_threshold, choose_margin, decision_metrics


def main():
    root = PROJECT_ROOT / "results/calibration"
    destination = root / "frozen_settings.json"
    if destination.exists() and json.loads(destination.read_text()).get("frozen"):
        raise ValueError("Settings are already frozen; do not overwrite them")
    source = root / "approved_settings_90pct_floor.csv"
    with source.open(newline="") as file:
        approved = list(csv.DictReader(file))
    expected = {(kind,d,seed) for kind in ("single","shared")
                for d in ("cataract","glaucoma") for seed in (42,43,44)}
    keys = [(r["model"],r["disease"],int(r["seed"])) for r in approved]
    if len(keys) != 12 or set(keys) != expected:
        raise ValueError("Expected twelve unique approved settings")
    previous = json.loads((root/"settings_review.json").read_text())
    prior = {(r["model_kind"],r["disease"],r["seed"]):r for r in previous["runs"]}
    rows = load_validation_labels()
    if len(rows) != 1024 or previous["labels_sha256"] != file_sha256(LABELS_FILE):
        raise ValueError("Validation labels differ from reviewed inputs")
    sources = source_hashes(rows)
    shared = {seed:read_shared_predictions(seed,rows,sources) for seed in (42,43,44)}
    runs = []
    for record in approved:
        kind,disease,seed = record["model"],record["disease"],int(record["seed"])
        old = prior[(kind,disease,seed)]
        if kind == "shared":
            logits = shared[seed][0][disease]
            digest = shared[seed][1]["prediction_sha256"]
        else:
            logits,digest = read_predictions(seed,rows,disease)
        if digest != old["prediction_sha256"]:
            raise ValueError("Predictions differ from reviewed calibration")
        if file_sha256(PROJECT_ROOT/old["checkpoint"]) != old["checkpoint_sha256"]:
            raise ValueError("Checkpoint differs from reviewed model")
        scale,offset = float(record["platt_scale"]),float(record["platt_offset"])
        if not np.isfinite([scale,offset]).all() or scale <= 0:
            raise ValueError("Invalid Platt parameters")
        if not np.allclose([scale,offset],[old["scale"],old["offset"]],rtol=1e-5,atol=1e-8):
            raise ValueError("Approved calibration differs materially from reviewed fit")
        p = torch.sigmoid(scale*logits+offset).numpy()
        labels = np.array([r[disease] for r in rows])
        t,m = float(record["threshold"]),float(record["uncertain_margin"])
        calculated,_ = select_threshold(p,labels)
        if not np.allclose([t,m],[calculated,choose_margin(p,t)],rtol=1e-12,atol=1e-14):
            raise ValueError("Approved values do not reproduce the agreed rule")
        base = decision_metrics(p,labels,t)
        final = decision_metrics(p,labels,t,m)
        for key,csv_key in (("tp","found"),("referral_count","referred_of_1024"),
                            ("uncertain_count","uncertain_of_1024")):
            if final[key] != int(record[csv_key]):
                raise ValueError("Approved referral counts do not reproduce")
        if int(labels.sum()) != int(record["positives"]):
            raise ValueError("Positive count mismatch")
        for key in ("sensitivity","specificity"):
            if not np.isclose(final[key],float(record[key]),rtol=0,atol=1e-12):
                raise ValueError("Approved metric mismatch")
        runs.append(dict(model_kind=kind,disease=disease,seed=seed,method="platt",
                         checkpoint=old["checkpoint"],checkpoint_sha256=old["checkpoint_sha256"],
                         prediction_sha256=digest,scale=scale,offset=offset,threshold=t,
                         uncertain_margin=m,threshold_only=base,including_uncertainty=final))
    settings = dict(status="frozen",frozen=True,date_frozen="2026-10-17",
                    review_reference="https://github.com/htmw/F2026-Team1/pull/43",
                    approval_note="Reviewer approved the attached 90% floor CSV; user authorized completion on 17 October 2026.",
                    fit_split="validation",sample_count=len(rows),labels_sha256=file_sha256(LABELS_FILE),
                    approved_csv_sha256=file_sha256(source),
                    freeze_script_sha256=file_sha256(Path(__file__)),
                    selection_script_sha256=file_sha256(PROJECT_ROOT/"scripts/select_calibration_settings.py"),
                    deployment=dict(model_kind="shared",seed=42,selection_split="validation",
                                    checkpoint=runs[6]["checkpoint"]),
                    policy=dict(threshold="Sensitivity >= 0.90 before uncertainty; fewest false positives; highest threshold breaks ties",
                                uncertainty="Distance band containing ceil(0.05*N) nearest scores, including ties",
                                referral="Uncertain OR probability >= threshold",
                                calibration="Use exact reviewed Platt parameters for each checkpoint and head",
                                scope="All 12 head/seed pairs retained for reporting; shared seed 42 selected for the app before external testing"),
                    limitations=["Validation selection results are not independent test estimates.",
                                 "External sensitivity is not guaranteed to reach 90%.",
                                 "Earlier single-model holdout observations exist and were not used to select these settings."],runs=runs)
    settings["deployment"]["checkpoint"] = next(r["checkpoint"] for r in runs if r["model_kind"]=="shared" and r["seed"]==42)
    destination.write_text(json.dumps(settings,indent=2,allow_nan=False)+"\n")
    print("Verified and froze all twelve approved settings. Commit before holdout evaluation.")


if __name__ == "__main__":
    main()
