"""Prepare validation labels for Task 12 calibration.

Calibration and cutoff fitting will be added when Task 11 predictions are
available. Internal test, external test, and holdout eyes must not be used
to choose these settings.
"""

import csv
from pathlib import Path
import torch
import numpy as np
from glaucoma_model import GlaucomaNet
from torch.utils.data import DataLoader
from fundus_dataset import FundusDataset, get_validation_transform


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LABELS_FILE = PROJECT_ROOT / "labels" / "eye_labels_task7.csv"
IMAGE_DIR = PROJECT_ROOT / "Preprocessed" / "ODIR"

# Saved glaucoma models from Task 11
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints" / "task11" / "glaucoma"
SEEDS = (42, 43, 44)


def load_validation_labels(labels_file=LABELS_FILE):
    """Read and validate the ODIR validation answer sheets."""
    with labels_file.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"filename", "patient_id", "cataract", "glaucoma", "split"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing label columns: {sorted(missing)}")
        rows = [row for row in reader if row["split"] == "validation"]

    if not rows:
        raise ValueError("No validation rows found")

    filenames = set()
    for row in rows:
        filename = row["filename"]
        if not filename or filename in filenames:
            raise ValueError(f"Empty or duplicate validation filename: {filename}")
        filenames.add(filename)
        for condition in ("cataract", "glaucoma"):
            if row[condition] not in {"0", "1"}:
                raise ValueError(f"Invalid {condition} label for {filename}")
            row[condition] = int(row[condition])

    return rows

def find_glaucoma_checkpoints():
    """Check that all three saved glaucoma models are available."""
    checkpoints = {}

    for seed in SEEDS:
        path = CHECKPOINT_DIR / f"glaucoma_seed_{seed}_best.pt"

        if not path.is_file():
            raise FileNotFoundError(f"Missing model file:{path}")
        
        checkpoints[seed] = path

    return checkpoints    


def load_glaucoma_checkpoint(path, expected_seed):
     """Open a saved glaucoma model file and check its contents."""
      # Allow the NumPy number types used in these checkpoints.
     with torch.serialization.safe_globals([
        np._core.multiarray.scalar,
        np.dtype,
        np.dtypes.Float64DType,
     ]):
        checkpoint = torch.load(
            path,
            map_location="cpu",
            weights_only=True,
        )
     if checkpoint.get("model_type") != "glaucoma_only":
        raise ValueError(f"Wrong model type in {path.name}")

     if checkpoint.get("seed") != expected_seed:
        raise ValueError(f"Wrong seed in {path.name}")

     if "model_state_dict" not in checkpoint:
        raise ValueError(f"Missing model weights in {path.name}")

     return checkpoint

def load_glaucoma_model(path, expected_seed):
    """Create the glaucoma model and load its saved weights."""
    checkpoint = load_glaucoma_checkpoint(path, expected_seed)

    model = GlaucomaNet(pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.eval()

    return model

def make_validation_loader():
    """Load validation photos in small batches without random changes."""
    dataset = FundusDataset(
        labels_csv=LABELS_FILE,
        image_dir=IMAGE_DIR,
        split="validation",
        transform=get_validation_transform(),
    )

    return DataLoader(
        dataset,
        batch_size=8,
        shuffle=False,
        num_workers=0,
    )

def collect_glaucoma_predictions(model, loader):
    """Collect raw glaucoma scores and correct labels for validation photos."""
    predictions = []
    model.eval()

    with torch.inference_mode():
        for batch in loader:
            logits = model(batch["image"]).reshape(-1)

            for filename, logit, label in zip(
                batch["filename"],
                logits.tolist(),
                batch["glaucoma"].tolist(),
            ):
             predictions.append({
                    "filename": filename,
                    "logit": logit,
                    "glaucoma": int(label),
                })

    return predictions


def save_glaucoma_predictions(predictions, seed):
    """Save one model's validation scores and correct labels."""
    output_dir = PROJECT_ROOT / "results" / "task12"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"glaucoma_seed_{seed}_validation.csv"

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["filename", "logit", "glaucoma"],
        )
        writer.writeheader()
        writer.writerows(predictions)

    print(f"Saved: {output_file}")


def main():
    rows = load_validation_labels()

    validation_loader = make_validation_loader()
    print(f"Validation batches: {len(validation_loader)}")

    checkpoints = find_glaucoma_checkpoints()

    for seed, path in checkpoints.items():
        model = load_glaucoma_model(path, seed)
        print(f"Collecting predictions for seed {seed}...", flush=True)

        predictions = collect_glaucoma_predictions(
            model, validation_loader
        )

        if len(predictions) != len(rows):
            raise ValueError("Prediction count does not match validation labels")

        print(f"Seed {seed}: {len(predictions)} predictions collected")

        save_glaucoma_predictions(predictions, seed)

        del model

    print(f"Validation images: {len(rows)}")
    for condition in ("cataract", "glaucoma"):
        print(f"{condition.capitalize()} cases: {sum(row[condition] for row in rows)}")
    print("Preparation only: no calibration or cutoffs have been fitted.")


if __name__ == "__main__":
    main()
