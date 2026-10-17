"""Collect both shared-model heads on validation only, with file provenance."""

import argparse
import csv
import json

import torch
from sklearn.metrics import roc_auc_score

from calibrate_models import (
    PROJECT_ROOT, LABELS_FILE, IMAGE_DIR, SEEDS, file_sha256,
    load_validation_labels, make_validation_loader,
)
from dual_model import DualNet

OUTPUT = PROJECT_ROOT / "results/calibration/shared"
DISEASES = ("cataract", "glaucoma")
RELEASE_HASHES = {
    42: "9c4b9e7b4de308dd428af3f22a1eae0b5f3d857aa91464067c7e287b7dc910c7",
    43: "ab1be7650397e95f9da0236526fb84f38ee151c232a12b2cf2e58f7d19c1f83d",
    44: "809fe9d70a23e42c417b579bc7792f5d7de5dd36efe6c21bda640d8d170aeffe",
}


def checkpoint_path(seed):
    """Locate one released shared checkpoint."""
    return PROJECT_ROOT / f"checkpoints/task11/shared/shared_seed_{seed}_best.pt"


def source_hashes(rows):
    """Fingerprint validation inputs, including the actual preprocessed photos."""
    sources = [LABELS_FILE] + [PROJECT_ROOT / "scripts" / name for name in (
        "dual_model.py", "resnet_backbone.py", "fundus_dataset.py",
        "preprocess_images.py", "calibrate_shared_models.py",
    )] + [IMAGE_DIR / row["filename"] for row in rows]
    return {p.relative_to(PROJECT_ROOT).as_posix(): file_sha256(p) for p in sources}


def load_model(seed):
    """Check the release fingerprint and safely load both heads."""
    path = checkpoint_path(seed)
    if file_sha256(path) != RELEASE_HASHES[seed]:
        raise ValueError(f"Shared seed {seed} differs from the reviewed release")
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint.get("model_type") != "shared_two_head" or checkpoint.get("seed") != seed:
        raise ValueError("Wrong shared checkpoint identity")
    model = DualNet(pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    return model.eval(), checkpoint


def read_shared_predictions(seed, rows, expected_sources=None):
    """Verify saved scores and align both heads to the validation labels."""
    path = OUTPUT / f"shared_seed_{seed}_validation.csv"
    metadata = json.loads(path.with_suffix(".meta.json").read_text())
    if (metadata["seed"], metadata["split"], metadata["model_type"]) != (
        seed, "validation", "shared_two_head"
    ):
        raise ValueError("Wrong saved shared prediction identity")
    if metadata["checkpoint_sha256"] != RELEASE_HASHES[seed]:
        raise ValueError("Saved scores belong to another checkpoint")
    if checkpoint_path(seed).exists() and file_sha256(checkpoint_path(seed)) != RELEASE_HASHES[seed]:
        raise ValueError("Local shared checkpoint has changed")
    if metadata["prediction_sha256"] != file_sha256(path):
        raise ValueError("Shared predictions changed")
    if metadata["input_source_sha256"] != (expected_sources or source_hashes(rows)):
        raise ValueError("Shared prediction inputs changed; recollect predictions")
    with path.open(newline="") as file:
        records = list(csv.DictReader(file))
    by_name = {r["filename"]: r for r in records}
    if len(by_name) != len(records) or set(by_name) != {r["filename"] for r in rows}:
        raise ValueError("Missing, duplicate or extra shared validation predictions")
    output = {}
    for disease in DISEASES:
        if any(int(by_name[r["filename"]][disease]) != r[disease] for r in rows):
            raise ValueError("Shared validation labels do not match")
        values = torch.tensor([float(by_name[r["filename"]][f"{disease}_logit"])
                               for r in rows], dtype=torch.float64)
        if not torch.isfinite(values).all():
            raise ValueError("Nonfinite shared predictions")
        output[disease] = values
    return output, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", choices=SEEDS, default=SEEDS)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("threads must be positive")
    torch.set_num_threads(args.threads)
    rows = load_validation_labels()
    sources = source_hashes(rows)
    loader = make_validation_loader()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for seed in args.seeds:
        path = OUTPUT / f"shared_seed_{seed}_validation.csv"
        if path.exists() and path.with_suffix(".meta.json").exists():
            read_shared_predictions(seed, rows, sources)
            print(f"Shared seed {seed}: verified saved predictions", flush=True)
            continue
        model, checkpoint = load_model(seed)
        predictions = []
        with torch.inference_mode():
            for batch_number, batch in enumerate(loader, 1):
                cataract, glaucoma = model(batch["image"])
                if not torch.isfinite(cataract).all() or not torch.isfinite(glaucoma).all():
                    raise ValueError("Nonfinite model output")
                for name, c, g, yc, yg in zip(
                    batch["filename"], cataract.reshape(-1).tolist(),
                    glaucoma.reshape(-1).tolist(), batch["cataract"].tolist(),
                    batch["glaucoma"].tolist(), strict=True,
                ):
                    predictions.append(dict(filename=name, cataract_logit=c,
                                            glaucoma_logit=g, cataract=int(yc), glaucoma=int(yg)))
                if batch_number % 16 == 0:
                    print(f"Shared seed {seed}: {len(predictions)}/{len(rows)} photos", flush=True)
        if [r["filename"] for r in predictions] != [r["filename"] for r in rows]:
            raise ValueError("Unexpected validation ordering")
        reproduction = {}
        for disease in DISEASES:
            if [r[disease] for r in predictions] != [r[disease] for r in rows]:
                raise ValueError("Validation labels mismatch")
            # Match training's float32 sigmoid when checking reported AUROC.
            probabilities = torch.sigmoid(torch.tensor(
                [r[f"{disease}_logit"] for r in predictions], dtype=torch.float32)).numpy()
            auc = float(roc_auc_score([r[disease] for r in rows], probabilities))
            expected = float(checkpoint[f"{disease}_validation_auroc"])
            reproduction[disease] = dict(observed=auc, reported=expected, difference=auc-expected)
            if abs(auc - expected) > 1e-4:
                raise ValueError(f"Investigate {disease} AUROC mismatch: {auc} vs {expected}")
        with path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(predictions[0]))
            writer.writeheader()
            writer.writerows(predictions)
        metadata = dict(seed=seed, model_type="shared_two_head", split="validation",
                        checkpoint=checkpoint_path(seed).relative_to(PROJECT_ROOT).as_posix(),
                        checkpoint_sha256=RELEASE_HASHES[seed], prediction_sha256=file_sha256(path),
                        input_source_sha256=sources, batch_size=8, device="cpu", shuffle=False,
                        torch_version=str(torch.__version__), auroc_reproduction=reproduction)
        path.with_suffix(".meta.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"Shared seed {seed}: saved both heads; AUROC reproduction checked", flush=True)


if __name__ == "__main__":
    main()
