"""Prepare validation labels for Task 12 calibration.

Calibration and cutoff fitting will be added when Task 11 predictions are
available. Internal test, external test, and holdout eyes must not be used
to choose these settings.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import warnings

import torch
import numpy as np
from glaucoma_model import GlaucomaNet
from torch.utils.data import DataLoader
from fundus_dataset import FundusDataset, get_validation_transform
from cataract_model import CataractOnlyNet

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
    output_dir = PROJECT_ROOT / "results" / "calibration"
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


def load_saved_glaucoma_predictions(seed):
    """Read saved validation scores and labels for one glaucoma model."""
    path = (
        PROJECT_ROOT / "results" / "calibration"
        / f"glaucoma_seed_{seed}_validation.csv"
    )

    with path.open(newline="", encoding="utf-8") as file:
        predictions = list(csv.DictReader(file))

    logits = torch.tensor(
        [float(row["logit"]) for row in predictions],
        dtype=torch.float64,
    )

    labels = torch.tensor(
        [int(row["glaucoma"]) for row in predictions],
        dtype=torch.float64,
    )

    return logits, labels


def calculate_log_loss(logits, labels):
    """Measure prediction confidence errors; lower is better."""
    loss = torch.nn.functional.binary_cross_entropy_with_logits(
        logits,
        labels,
    )

    return loss.item()


def fit_temperature(logits, labels):
    """Fit a positive temperature using validation log loss."""
    logits = logits.detach()
    labels = labels.detach()

    log_temperature = torch.zeros(
        (), dtype=logits.dtype, requires_grad=True
    )

    optimizer = torch.optim.LBFGS(
        [log_temperature],
        lr=0.1,
        max_iter=100,
        line_search_fn="strong_wolfe",
    )

    def closure():
        optimizer.zero_grad()
        temperature = log_temperature.exp()

        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            logits / temperature,
            labels,
        )

        loss.backward()
        return loss

    optimizer.step(closure)

    return log_temperature.exp().detach().item()


def fit_platt_scaling(logits, labels):
    """Fit a positive scale and offset using validation log loss."""
    logits = logits.detach().to(dtype=torch.float64)
    labels = labels.detach().to(dtype=torch.float64)

    if logits.ndim != 1 or logits.shape != labels.shape or logits.numel() == 0:
        raise ValueError("Scores and labels must be matching nonempty vectors")
    if not torch.isfinite(logits).all() or not torch.isfinite(labels).all():
        raise ValueError("Scores and labels must be finite")
    if not ((labels == 0) | (labels == 1)).all() or labels.unique().numel() != 2:
        raise ValueError("Calibration requires both binary label classes")

    baseline_loss = calculate_log_loss(logits, labels)

    # A positive scale preserves the model's ordering of photos.
    log_scale = torch.zeros((), dtype=logits.dtype, requires_grad=True)
    offset = torch.zeros((), dtype=logits.dtype, requires_grad=True)
    optimizer = torch.optim.LBFGS(
        [log_scale, offset],
        lr=0.1,
        max_iter=200,
        line_search_fn="strong_wolfe",
    )

    def closure():
        optimizer.zero_grad()
        adjusted_logits = log_scale.exp() * logits + offset
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            adjusted_logits, labels
        )
        loss.backward()
        return loss

    optimizer.step(closure)
    scale = log_scale.exp().detach().item()
    bias = offset.detach().item()
    adjusted_logits = scale * logits + bias
    if not np.isfinite(scale) or scale <= 0 or not np.isfinite(bias):
        raise ValueError("Platt scaling produced invalid parameters")
    if not torch.isfinite(adjusted_logits).all():
        raise ValueError("Platt scaling produced invalid scores")

    adjusted_loss = calculate_log_loss(adjusted_logits, labels)
    loss_delta = adjusted_loss - baseline_loss
    if loss_delta > 1e-4:
        raise ValueError(
            "Platt scaling increased validation loss by "
            f"{loss_delta:.6e}; fit is not usable."
        )
    if loss_delta > 0:
        warnings.warn(
            "Platt scaling slightly increased validation loss on the fit split "
            f"by {loss_delta:.6e}. This is usually numerical noise when fitting "
            "on the same validation data; keeping the fit because the increase is "
            "small.",
            RuntimeWarning,
            stacklevel=2,
        )

    return scale, bias


def show_calibration_bins(probabilities, labels, disease="glaucoma"):
    """Compare predicted probabilities with actual rates in ten ranges."""
    for index in range(10):
        lower = index / 10
        upper = (index + 1) / 10

        if index == 9:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)

        count = int(mask.sum().item())

        if count == 0:
            continue

        predicted = probabilities[mask].mean().item()
        actual = labels[mask].mean().item()

        print(
            f"  {lower:.0%}–{upper:.0%}: {count} photos, "
            f"average prediction {predicted:.1%}, "
            f"actual {disease} {actual:.1%}"
        )


def save_trial_calibration(trials, bin_rows, disease="glaucoma"):
    """Save unfrozen settings and descriptive results from the fitting data."""
    output_dir = PROJECT_ROOT / "results" / "calibration"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "status": "trial",
        "frozen": False,
        "model_type": f"{disease}_only",
        "fit_split": "validation",
        "evaluation_split": "validation",
        "evaluation_note": "Same data used for fitting; not an independent test.",
        "decision_threshold": None,
        "abstention_cutoff": None,
        "probability_formulas": {
            "uncalibrated": "sigmoid(logit)",
            "temperature": "sigmoid(logit / temperature)",
            "platt": "sigmoid(scale * logit + offset)",
        },
        "bin_definition": "Ten equal-width bins, lower inclusive, upper exclusive except 1.0.",
        "runs": trials,
    }
    summary_path = output_dir / f"{disease}_calibration_trial.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    bins_path = output_dir / f"{disease}_calibration_trial_bins.csv"
    with bins_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=[
            "status", "seed", "method", "lower", "upper", "count",
            f"{disease}_count", "mean_probability", "observed_rate",
        ])
        writer.writeheader()
        writer.writerows(bin_rows)
    print(f"Saved trial settings and losses: {summary_path}")
    print(f"Saved trial probability bins: {bins_path}")

################### CATARACT #######################

def load_cataract_model(seed):
    """Open a saved cataract model and check that it is the right one."""
    path = (
        PROJECT_ROOT / "checkpoints" / "task11" / "cataract"
        / f"cataract_seed_{seed}_best.pt"
    )

    checkpoint = torch.load(
        path,
        map_location="cpu",
        weights_only=True,
    )

    if checkpoint.get("model_type") != "cataract_only":
        raise ValueError(f"Wrong model type: {path.name}")

    if checkpoint.get("seed") != seed:
        raise ValueError(f"Wrong seed in {path.name}")

    model = CataractOnlyNet(pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.eval()

    return model


def collect_cataract_predictions(model, loader):
    """Collect cataract scores and correct labels for validation photos."""
    predictions = []
    model.eval()

    with torch.inference_mode():
        for batch in loader:
            logits = model(batch["image"]).reshape(-1)

            if not torch.isfinite(logits).all():
                raise ValueError("Model produced an invalid score")

            for filename, logit, label in zip(
                batch["filename"],
                logits.tolist(),
                batch["cataract"].tolist(),
                strict=True,
            ):
                predictions.append({
                    "filename": filename,
                    "logit": logit,
                    "cataract": int(label),
                })

    return predictions


def save_cataract_predictions(predictions, seed):
    """Save one cataract model's validation scores and correct labels."""
    output_dir = PROJECT_ROOT / "results" / "calibration"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"cataract_seed_{seed}_validation.csv"

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["filename", "logit", "cataract"],
        )
        writer.writeheader()
        writer.writerows(predictions)

    print(f"Saved: {output_file}")


def load_saved_predictions(seed, disease, rows):
    """Validate saved scores against the canonical validation labels."""
    path = PROJECT_ROOT / "results" / "calibration" / f"{disease}_seed_{seed}_validation.csv"
    with path.open(newline="", encoding="utf-8") as file:
        predictions = list(csv.DictReader(file))
    by_name = {r["filename"]: r for r in predictions}
    expected = {r["filename"]: r[disease] for r in rows}
    if len(by_name) != len(predictions) or set(by_name) != set(expected):
        raise ValueError("Missing, duplicate, or extra validation predictions")
    if any(int(by_name[name][disease]) != label for name, label in expected.items()):
        raise ValueError("Saved labels do not match validation labels")
    logits = torch.tensor([float(by_name[r["filename"]]["logit"]) for r in rows], dtype=torch.float64)
    labels = torch.tensor([r[disease] for r in rows], dtype=torch.float64)
    if not torch.isfinite(logits).all():
        raise ValueError("Invalid saved scores")
    return logits, labels


def main():
    parser = argparse.ArgumentParser(description="Compare trial calibration using validation only")
    parser.add_argument("--disease", choices=("glaucoma", "cataract"), default="glaucoma")
    parser.add_argument("--collect-predictions", action="store_true",
                        help="Run models and replace saved validation scores before calibration")
    args = parser.parse_args()
    disease = args.disease
    rows = load_validation_labels()
    if args.collect_predictions:
        loader = make_validation_loader()
        for seed in SEEDS:
            print(f"Collecting {disease} predictions for seed {seed}...", flush=True)
            if disease == "cataract":
                model = load_cataract_model(seed)
                predictions = collect_cataract_predictions(model, loader)
                save = save_cataract_predictions
            else:
                model = load_glaucoma_model(CHECKPOINT_DIR / f"glaucoma_seed_{seed}_best.pt", seed)
                predictions = collect_glaucoma_predictions(model, loader)
                save = save_glaucoma_predictions
            if (len(predictions) != len(rows) or
                    {r["filename"]: r[disease] for r in predictions} !=
                    {r["filename"]: r[disease] for r in rows}):
                raise ValueError("Predictions do not match validation labels")
            if not all(np.isfinite(r["logit"]) for r in predictions):
                raise ValueError("Invalid model scores")
            save(predictions, seed)

    trials = []
    bin_rows = []

    for seed in SEEDS:
        logits, labels = load_saved_predictions(seed, disease, rows)

        before_loss = calculate_log_loss(logits, labels)
        temperature = fit_temperature(logits, labels)
        after_loss = calculate_log_loss(logits / temperature, labels)

        print(f"Seed {seed}:")
        print(f"  Temperature: {temperature:.4f}")
        print(f"  Loss before: {before_loss:.6f}")
        print(f"  Loss after:  {after_loss:.6f}")

        before_probabilities = torch.sigmoid(logits)
        after_probabilities = torch.sigmoid(logits / temperature)

        print(f"  Actual {disease} rate: {labels.mean().item():.2%}")
        print(
            f"  Average probability before: "
            f"{before_probabilities.mean().item():.2%}"
        )
        print(
            f"  Average probability after: "
            f"{after_probabilities.mean().item():.2%}"
        )

        scale, offset = fit_platt_scaling(logits, labels)
        platt_logits = scale * logits + offset
        platt_loss = calculate_log_loss(platt_logits, labels)
        platt_probabilities = torch.sigmoid(platt_logits)
        print(f"  Platt scale: {scale:.6f}, offset: {offset:.6f}")
        print(f"  Loss after Platt scaling: {platt_loss:.6f}")
        print(f"  Average probability after Platt: {platt_probabilities.mean().item():.2%}")

        show_calibration_bins(platt_probabilities, labels, disease)

        prediction_path = (
            PROJECT_ROOT / "results" / "calibration"
            / f"{disease}_seed_{seed}_validation.csv"
        )
        trials.append({
            "seed": seed,
            "prediction_file": prediction_path.relative_to(PROJECT_ROOT).as_posix(),
            "prediction_sha256": hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
            "sample_count": len(labels),
            f"{disease}_count": int(labels.sum().item()),
            "observed_rate": labels.mean().item(),
            "uncalibrated": {
                "log_loss": before_loss,
                "mean_probability": before_probabilities.mean().item(),
            },
            "temperature": {
                "temperature": temperature,
                "log_loss": after_loss,
                "mean_probability": after_probabilities.mean().item(),
            },
            "platt": {
                "scale": scale,
                "offset": offset,
                "log_loss": platt_loss,
                "mean_probability": platt_probabilities.mean().item(),
            },
        })
        for method, probabilities in (
            ("uncalibrated", before_probabilities),
            ("temperature", after_probabilities),
            ("platt", platt_probabilities),
        ):
            for index in range(10):
                lower, upper = index / 10, (index + 1) / 10
                mask = (probabilities >= lower) & (
                    (probabilities <= upper) if index == 9 else (probabilities < upper)
                )
                count = int(mask.sum().item())
                bin_rows.append({
                    "status": "trial", "seed": seed, "method": method,
                    "lower": lower, "upper": upper, "count": count,
                    f"{disease}_count": int(labels[mask].sum().item()),
                    "mean_probability": probabilities[mask].mean().item() if count else None,
                    "observed_rate": labels[mask].mean().item() if count else None,
                })

    save_trial_calibration(trials, bin_rows, disease)
    print(f"Validation images: {len(rows)}")
    for condition in ("cataract", "glaucoma"):
        print(f"{condition.capitalize()} cases: {sum(row[condition] for row in rows)}")
    print("Trial calibration fitted on validation data; settings are not frozen.")
    print("These losses use the same data used to fit calibration, not an independent test.")


if __name__ == "__main__":
    main()
