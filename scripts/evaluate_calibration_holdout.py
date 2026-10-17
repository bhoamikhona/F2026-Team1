"""Report low-quality holdout referrals after reviewed settings are frozen and committed.

Example: python scripts/evaluate_calibration_holdout.py --settings path/to/settings.json
This command never fits calibration or chooses thresholds.
"""

import argparse
import csv
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from calibrate_models import (
    PROJECT_ROOT, LABELS_FILE, IMAGE_DIR, SEEDS, file_sha256,
    load_cataract_model, load_glaucoma_model,
)
from calibrate_shared_models import load_model
from fundus_dataset import get_validation_transform


def verify_settings(path):
    """Require frozen, reviewed, committed settings tied to exact checkpoints."""
    settings = json.loads(path.read_text())
    if settings.get("frozen") is not True or settings.get("status") != "frozen":
        raise ValueError("Review and freeze settings before evaluating holdout")
    if not settings.get("review_reference"):
        raise ValueError("Record the team review reference before holdout evaluation")
    relative = path.resolve().relative_to(PROJECT_ROOT).as_posix()
    committed = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=PROJECT_ROOT,
                               capture_output=True, check=True).stdout
    if committed != path.read_bytes():
        raise ValueError("Commit the exact frozen settings before evaluating holdout")
    if settings["labels_sha256"] != file_sha256(LABELS_FILE):
        raise ValueError("Label file differs from calibration inputs")
    expected = {(kind, disease, seed) for kind in ("single", "shared")
                for disease in ("cataract", "glaucoma") for seed in SEEDS}
    keys = [(r["model_kind"], r["disease"], r["seed"]) for r in settings["runs"]]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("Expected exactly twelve head/seed settings")
    for run in settings["runs"]:
        if file_sha256(PROJECT_ROOT / run["checkpoint"]) != run["checkpoint_sha256"]:
            raise ValueError("Checkpoint differs from frozen settings")
        values = [run[k] for k in ("scale", "offset", "threshold", "uncertain_margin")]
        if not np.isfinite(values).all() or run["scale"] <= 0 or run["uncertain_margin"] < 0:
            raise ValueError("Invalid frozen numerical settings")
    return settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", required=True, type=Path)
    args = parser.parse_args()
    settings = verify_settings(args.settings)
    torch.set_num_threads(4)
    with LABELS_FILE.open(newline="") as file:
        rows = [r for r in csv.DictReader(file) if r["split"] == "holdout"
                and "low image quality" in r["diagnosis_text"].lower()]
    if len(rows) != 21 or len({r["filename"] for r in rows}) != 21:
        raise ValueError("Expected 21 unique low-quality holdout eyes")
    transform = get_validation_transform()
    images = []
    for row in rows:
        with Image.open(IMAGE_DIR / row["filename"]) as image:
            images.append(transform(image.convert("RGB")))
    runs = {(r["model_kind"], r["disease"], r["seed"]):r for r in settings["runs"]}
    summaries, per_image = [], []
    for kind in ("single", "shared"):
        for seed in SEEDS:
            models = ([load_model(seed)[0]] if kind == "shared" else [
                load_cataract_model(seed),
                load_glaucoma_model(PROJECT_ROOT/runs[(kind,"glaucoma",seed)]["checkpoint"],seed)])
            scores = {d:[] for d in ("cataract","glaucoma")}
            with torch.inference_mode():
                for start in range(0,len(images),8):
                    batch = torch.stack(images[start:start+8])
                    outputs = models[0](batch) if kind == "shared" else tuple(m(batch) for m in models)
                    for disease, logits in zip(scores,outputs,strict=True):
                        if not torch.isfinite(logits).all():
                            raise ValueError("Nonfinite holdout prediction")
                        scores[disease].extend(logits.reshape(-1).tolist())
            any_uncertain, any_referred = np.zeros(21,dtype=bool), np.zeros(21,dtype=bool)
            for disease, raw in scores.items():
                run = runs[(kind,disease,seed)]
                p = torch.sigmoid(run["scale"]*torch.tensor(raw,dtype=torch.float64)+run["offset"]).numpy()
                uncertain = np.abs(p-run["threshold"]) <= run["uncertain_margin"]
                ordinary = (p >= run["threshold"]) & ~uncertain
                referred = ordinary | uncertain
                any_uncertain |= uncertain
                any_referred |= referred
                summaries.append(dict(model_kind=kind,seed=seed,disease=disease,
                                      uncertain_count=int(uncertain.sum()),
                                      ordinary_referrals=int(ordinary.sum()),
                                      total_referrals=int(referred.sum()),sample_count=21))
                for i,row in enumerate(rows):
                    per_image.append(dict(model_kind=kind,seed=seed,disease=disease,
                                          filename=row["filename"],probability=float(p[i]),
                                          result="Uncertain, refer" if uncertain[i] else
                                          ("Refer" if ordinary[i] else "No concern")))
            summaries.append(dict(model_kind=kind,seed=seed,disease="either_eye_result",
                                  uncertain_count=int(any_uncertain.sum()),
                                  ordinary_referrals=int((any_referred & ~any_uncertain).sum()),
                                  total_referrals=int(any_referred.sum()),sample_count=21))
    destination = PROJECT_ROOT/"results/calibration/final_holdout_report.json"
    record = dict(settings_sha256=file_sha256(args.settings),sample_count=21,
                  patient_count=len({r["patient_id"] for r in rows}),summary=summaries,
                  note="Observed referral counts, not disease accuracy or proof of safety. No fitting was performed.",
                  historical_note="These eyes were previously examined in a single-model experiment.",
                  per_image=per_image)
    destination.write_text(json.dumps(record,indent=2,allow_nan=False)+"\n")
    print(f"Saved: {destination}")


if __name__ == "__main__":
    main()
