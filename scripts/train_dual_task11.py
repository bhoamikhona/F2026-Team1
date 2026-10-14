
"""Task 11.1: Shared ResNet-50 training for cataract and glaucoma.

The repository is cloned into Kaggle, while this script may be
uploaded separately through Kaggle's Add Input / Dataset feature.

Run from the repository root with scripts and src on PYTHONPATH.
"""

import argparse
import hashlib
import math
import subprocess
from pathlib import Path

import pandas as pd
import torch
from sklearn.metrics import roc_auc_score
from torch import nn
from torch.utils.data import DataLoader

from dual.config import set_seed
from dual_model import DualNet
from fundus_dataset import (
    FundusDataset,
    get_train_transform,
    get_validation_transform,
)


LABELS_CSV = Path("labels/eye_labels_task7.csv")
IMAGE_DIR = Path("Preprocessed/ODIR")

CHECKPOINT_DIR = Path("checkpoints/task11/shared")
RESULTS_CSV = Path("results/task11/shared_results.csv")
HISTORY_CSV = Path("results/task11/shared_training_history.csv")

SEEDS = (42, 43, 44)
BATCH_SIZE = 8
MAX_EPOCHS = 30
LEARNING_RATE = 1e-4
PATIENCE = 5


def git_revision():
    """Get the cloned repository commit, not uploaded script authorship."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    )
    commit = result.stdout.strip()

    if len(commit) != 40 or any(
        c not in "0123456789abcdef" for c in commit
    ):
        raise RuntimeError("Cannot determine repository commit")

    return commit


def file_sha256(path):
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024), b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def validate_labels():
    df = pd.read_csv(LABELS_CSV)
    required = {"filename", "split", "cataract", "glaucoma"}

    if not required.issubset(df.columns):
        raise ValueError(
            f"Missing label columns: {sorted(required - set(df.columns))}"
        )

    for split in ("train", "validation"):
        subset = df[df["split"] == split]

        if subset.empty:
            raise ValueError(f"Empty {split} split")

        for disease in ("cataract", "glaucoma"):
            if (
                not subset[disease].isin([0, 1]).all()
                or subset[disease].nunique() != 2
            ):
                raise ValueError(
                    f"{split} must contain both binary classes "
                    f"for {disease}"
                )

    return df


def loss_functions(df, device):
    train = df[df["split"] == "train"]
    functions = []

    for disease in ("cataract", "glaucoma"):
        positives = int(train[disease].sum())
        negatives = len(train) - positives

        weight = torch.tensor(
            [negatives / positives],
            dtype=torch.float32,
            device=device,
        )

        functions.append(
            nn.BCEWithLogitsLoss(pos_weight=weight)
        )

    return tuple(functions)


def train_epoch(model, loader, optimizer, losses, device):
    model.train()
    total = 0.0
    count = 0

    for batch in loader:
        images = batch["image"].to(device)
        cataract = batch["cataract"].to(device).unsqueeze(1)
        glaucoma = batch["glaucoma"].to(device).unsqueeze(1)

        optimizer.zero_grad()

        cataract_logits, glaucoma_logits = model(images)

        loss = (
            losses[0](cataract_logits, cataract)
            + losses[1](glaucoma_logits, glaucoma)
        )

        loss.backward()
        optimizer.step()

        total += float(loss.item())
        count += 1

    if count == 0:
        raise RuntimeError("No training batches")

    return total / count


def evaluate(model, loader, losses, device):
    model.eval()

    total = 0.0
    count = 0

    cataract_labels = []
    cataract_probs = []
    glaucoma_labels = []
    glaucoma_probs = []

    with torch.no_grad():
        for batch in loader:
            images = batch["image"].to(device)
            cataract = batch["cataract"].to(device).unsqueeze(1)
            glaucoma = batch["glaucoma"].to(device).unsqueeze(1)

            cataract_logits, glaucoma_logits = model(images)

            loss = (
                losses[0](cataract_logits, cataract)
                + losses[1](glaucoma_logits, glaucoma)
            )

            total += float(loss.item())
            count += 1

            cataract_labels.extend(
                cataract.flatten().cpu().tolist()
            )
            glaucoma_labels.extend(
                glaucoma.flatten().cpu().tolist()
            )

            cataract_probs.extend(
                torch.sigmoid(cataract_logits)
                .flatten().cpu().tolist()
            )
            glaucoma_probs.extend(
                torch.sigmoid(glaucoma_logits)
                .flatten().cpu().tolist()
            )

    if count == 0:
        raise RuntimeError("No validation batches")

    if (
        len(set(cataract_labels)) != 2
        or len(set(glaucoma_labels)) != 2
    ):
        raise ValueError(
            "Validation must contain both classes for each disease"
        )

    cataract_auc = float(
        roc_auc_score(cataract_labels, cataract_probs)
    )
    glaucoma_auc = float(
        roc_auc_score(glaucoma_labels, glaucoma_probs)
    )
    mean_auc = float((cataract_auc + glaucoma_auc) / 2)

    values = (
        total / count,
        cataract_auc,
        glaucoma_auc,
        mean_auc,
    )

    if not all(math.isfinite(value) for value in values):
        raise ValueError("Non-finite validation metric")

    return values


def upsert_csv(path, record, key):
    path.parent.mkdir(parents=True, exist_ok=True)

    new = pd.DataFrame([record])

    if path.exists():
        old = pd.read_csv(path)

        if set(old.columns) != set(new.columns):
            raise ValueError(
                f"Unexpected existing CSV columns in {path}"
            )

        mask = pd.Series(True, index=old.index)

        for column in key:
            mask &= (
                old[column].astype(str)
                == str(record[column])
            )

        new = pd.concat(
            [old.loc[~mask], new],
            ignore_index=True,
        )

    new.sort_values(list(key), inplace=True)
    new.to_csv(
        path,
        index=False,
        float_format="%.17g",
    )


def verify_checkpoint(path, seed, epoch, mean_auc):
    checkpoint = torch.load(
        path,
        map_location="cpu",
        weights_only=True,
    )

    if (
        checkpoint["seed"] != seed
        or checkpoint["epoch"] != epoch
    ):
        raise AssertionError("Checkpoint seed/epoch mismatch")

    if not math.isclose(
        checkpoint["mean_validation_auroc"],
        mean_auc,
        rel_tol=0,
        abs_tol=1e-12,
    ):
        raise AssertionError("Checkpoint AUROC mismatch")

    reloaded = DualNet(pretrained=False).cpu()

    reloaded.load_state_dict(
        checkpoint["model_state_dict"],
        strict=True,
    )

    return reloaded


def train_seed(
    seed,
    device,
    commit,
    script_hash,
    labels,
    labels_hash,
):
    set_seed(seed)

    generator = torch.Generator().manual_seed(seed)

    train_data = FundusDataset(
        LABELS_CSV,
        IMAGE_DIR,
        "train",
        get_train_transform(),
    )
    val_data = FundusDataset(
        LABELS_CSV,
        IMAGE_DIR,
        "validation",
        get_validation_transform(),
    )

    train_loader = DataLoader(
        train_data,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
        generator=generator,
    )
    val_loader = DataLoader(
        val_data,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    losses = loss_functions(labels, device)

    model = DualNet(pretrained=True).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    checkpoint_path = (
        CHECKPOINT_DIR / f"shared_seed_{seed}_best.pt"
    )

    if checkpoint_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite checkpoint: {checkpoint_path}"
        )

    for path in (HISTORY_CSV, RESULTS_CSV):
        if path.exists():
            existing = pd.read_csv(path)

            if seed in existing["seed"].tolist():
                raise FileExistsError(
                    f"Seed {seed} already recorded in {path}"
                )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    best = -math.inf
    best_epoch = 0
    wait = 0

    for epoch in range(1, MAX_EPOCHS + 1):
        train_loss = train_epoch(
            model,
            train_loader,
            optimizer,
            losses,
            device,
        )

        (
            val_loss,
            cataract_auc,
            glaucoma_auc,
            mean_auc,
        ) = evaluate(
            model,
            val_loader,
            losses,
            device,
        )

        if not math.isfinite(train_loss):
            raise ValueError("Non-finite training loss")

        print(
            f"Seed {seed}, epoch {epoch}/{MAX_EPOCHS}: "
            f"train={train_loss:.10f}, "
            f"val={val_loss:.10f}, "
            f"cataract_auc={cataract_auc:.10f}, "
            f"glaucoma_auc={glaucoma_auc:.10f}, "
            f"mean_auc={mean_auc:.10f}",
            flush=True,
        )

        upsert_csv(
            HISTORY_CSV,
            {
                "model_type": "shared_two_head",
                "seed": seed,
                "epoch": epoch,
                "train_loss": train_loss,
                "validation_loss": val_loss,
                "cataract_validation_auroc": cataract_auc,
                "glaucoma_validation_auroc": glaucoma_auc,
                "mean_validation_auroc": mean_auc,
                "git_commit": commit,
                "labels_sha256": labels_hash,
                "script_sha256": script_hash,
            },
            ("seed", "epoch"),
        )

        if mean_auc > best:
            best = mean_auc
            best_epoch = epoch
            wait = 0

            torch.save(
                {
                    "model_type": "shared_two_head",
                    "seed": int(seed),
                    "epoch": int(epoch),
                    "cataract_validation_auroc": float(
                        cataract_auc
                    ),
                    "glaucoma_validation_auroc": float(
                        glaucoma_auc
                    ),
                    "mean_validation_auroc": float(mean_auc),
                    "model_state_dict": {
                        key: value.detach().cpu()
                        for key, value in model.state_dict().items()
                    },
                    "learning_rate": float(LEARNING_RATE),
                    "batch_size": int(BATCH_SIZE),
                    "max_epochs": int(MAX_EPOCHS),
                    "patience": int(PATIENCE),
                    "git_commit": commit,
                    "labels_sha256": labels_hash,
                    "script_sha256": script_hash,
                },
                checkpoint_path,
            )

            verify_checkpoint(
                checkpoint_path,
                seed,
                epoch,
                mean_auc,
            )
        else:
            wait += 1

        if wait >= PATIENCE:
            print(
                f"Seed {seed}: early stopping at epoch {epoch}",
                flush=True,
            )
            break

    best_model = verify_checkpoint(
        checkpoint_path,
        seed,
        best_epoch,
        best,
    )

    (
        best_val_loss,
        best_cataract_auc,
        best_glaucoma_auc,
        best_mean_auc,
    ) = evaluate(
        best_model,
        val_loader,
        loss_functions(labels, torch.device("cpu")),
        torch.device("cpu"),
    )

    if not math.isclose(
        best_mean_auc,
        best,
        rel_tol=0,
        abs_tol=1e-4,
    ):
        raise AssertionError(
            "Reloaded checkpoint AUROC mismatch: "
            f"{best_mean_auc} vs {best}"
        )

    upsert_csv(
        RESULTS_CSV,
        {
            "model_type": "shared_two_head",
            "seed": seed,
            "best_epoch": best_epoch,
            "best_cataract_validation_auroc": best_cataract_auc,
            "best_glaucoma_validation_auroc": best_glaucoma_auc,
            "best_mean_validation_auroc": best_mean_auc,
            "checkpoint": str(checkpoint_path),
            "checkpoint_sha256": file_sha256(checkpoint_path),
            "git_commit": commit,
            "labels_sha256": labels_hash,
            "script_sha256": script_hash,
            "learning_rate": LEARNING_RATE,
            "batch_size": BATCH_SIZE,
            "max_epochs": MAX_EPOCHS,
            "patience": PATIENCE,
        },
        ("seed",),
    )

    print(
        f"Seed {seed} complete: "
        f"best epoch={best_epoch}, "
        f"mean AUROC={best_mean_auc:.6f}",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--seed",
        type=int,
        choices=SEEDS,
        required=True,
        help="Run exactly one seed",
    )

    args = parser.parse_args()

    commit = git_revision()

    if not LABELS_CSV.is_file() or not IMAGE_DIR.is_dir():
        raise FileNotFoundError(
            "Approved labels or preprocessed ODIR directory missing"
        )

    labels = validate_labels()

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    script_hash = file_sha256(
        Path(__file__).resolve()
    )

    print(
        f"Repository commit: {commit}; "
        f"script SHA-256: {script_hash}; "
        f"device: {device}; seed: {args.seed}",
        flush=True,
    )

    train_seed(
        args.seed,
        device,
        commit,
        script_hash,
        labels,
        file_sha256(LABELS_CSV),
    )


if __name__ == "__main__":
    main()
