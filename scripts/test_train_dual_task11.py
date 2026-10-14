
"""Task 11.1 smoke test for shared two-head ResNet-50 checkpoints.

Run from the repository root:
    python scripts/test_train_dual_task11.py

Does not retrain ResNet or modify project artifacts.
Uses a temporary directory for synthetic test artifacts.
Requires the three downloaded Task 11.1 checkpoints at their expected paths.
"""

import hashlib
import math
import tempfile
import sys
from pathlib import Path

import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from dual_model import DualNet  # noqa: E402
import train_dual_task11 as training  # noqa: E402


class SyntheticFundus(Dataset):
    """Small deterministic dataset; does not use ODIR or modify project files."""

    def __len__(self):
        return 8

    def __getitem__(self, index):
        return {
            "image": torch.tensor(
                [float(index % 2), float((index // 2) % 2)]
            ),
            "cataract": torch.tensor(float(index % 2)),
            "glaucoma": torch.tensor(float((index // 2) % 2)),
        }


class TinyDual(nn.Module):
    """Lightweight stand-in to exercise the approved training functions."""

    def __init__(self):
        super().__init__()
        self.shared = nn.Linear(2, 4)
        self.cataract = nn.Linear(4, 1)
        self.glaucoma = nn.Linear(4, 1)

    def forward(self, x):
        hidden = torch.relu(self.shared(x))
        return self.cataract(hidden), self.glaucoma(hidden)


def test_training_pipeline():
    """Exercise real Task 11.1 train/evaluate logic without retraining ResNet."""
    torch.manual_seed(42)
    device = torch.device("cpu")
    model = TinyDual()
    loader = DataLoader(SyntheticFundus(), batch_size=4, shuffle=False)
    losses = (nn.BCEWithLogitsLoss(), nn.BCEWithLogitsLoss())
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    before = [p.detach().clone() for p in model.parameters()]
    train_loss = training.train_epoch(model, loader, optimizer, losses, device)
    assert math.isfinite(train_loss)
    assert any(
        not torch.equal(old, new)
        for old, new in zip(before, model.parameters())
    ), "Training did not update parameters"

    metrics = training.evaluate(model, loader, losses, device)
    val_loss, cataract_auc, glaucoma_auc, mean_auc = metrics
    assert all(math.isfinite(float(v)) for v in metrics)
    assert math.isclose(
        mean_auc, (cataract_auc + glaucoma_auc) / 2, abs_tol=1e-12
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        checkpoint_path = Path(tmpdir) / "synthetic.pt"
        torch.save(
            {
                "seed": 42,
                "epoch": 1,
                "mean_validation_auroc": float(mean_auc),
                "model_state_dict": {
                    key: value.detach().cpu()
                    for key, value in model.state_dict().items()
                },
            },
            checkpoint_path,
        )
        checkpoint = torch.load(
            checkpoint_path, map_location="cpu", weights_only=True
        )
        reloaded = TinyDual()
        reloaded.load_state_dict(checkpoint["model_state_dict"], strict=True)
        reloaded_metrics = training.evaluate(
            reloaded, loader, losses, device
        )
        assert all(
            math.isclose(a, b, rel_tol=0, abs_tol=1e-10)
            for a, b in zip(metrics, reloaded_metrics)
        )

        history_path = Path(tmpdir) / "history.csv"
        record = {"seed": 42, "epoch": 1, "mean_validation_auroc": mean_auc}
        training.upsert_csv(history_path, record, ("seed", "epoch"))
        training.upsert_csv(history_path, record, ("seed", "epoch"))
        assert len(pd.read_csv(history_path)) == 1

    print(
        "PASS: synthetic two-head training/backprop, evaluation, "
        "mean AUROC, reload and CSV upsert"
    )


def main():
    results_path = ROOT / "results/task11/shared_results.csv"
    history_path = ROOT / "results/task11/shared_training_history.csv"

    assert results_path.is_file(), f"Missing: {results_path}"
    assert history_path.is_file(), f"Missing: {history_path}"

    results = pd.read_csv(results_path)
    history = pd.read_csv(history_path)

    assert sorted(results["seed"].tolist()) == [42, 43, 44]

    for seed in (42, 43, 44):
        checkpoint_path = (
            ROOT / f"checkpoints/task11/shared/shared_seed_{seed}_best.pt"
        )
        assert checkpoint_path.is_file(), f"Missing: {checkpoint_path}"

        record = results[results["seed"] == seed]
        assert len(record) == 1
        record = record.iloc[0]

        epochs = history[history["seed"] == seed].sort_values("epoch")
        assert not epochs.empty
        assert not epochs["epoch"].duplicated().any()

        best_row = epochs.loc[epochs["mean_validation_auroc"].idxmax()]

        assert int(record["best_epoch"]) == int(best_row["epoch"])
        assert math.isclose(
            float(record["best_mean_validation_auroc"]),
            float(best_row["mean_validation_auroc"]),
            rel_tol=0,
            abs_tol=1e-5,
        )

        checkpoint = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=True,
        )

        assert checkpoint["seed"] == seed
        assert checkpoint["epoch"] == int(record["best_epoch"])

        assert math.isclose(
            float(checkpoint["mean_validation_auroc"]),
            float(record["best_mean_validation_auroc"]),
            rel_tol=0,
            abs_tol=1e-5,
        )

        with checkpoint_path.open("rb") as checkpoint_file:
            sha256 = hashlib.file_digest(
                checkpoint_file, "sha256"
            ).hexdigest()

        assert sha256 == record["checkpoint_sha256"]

        model = DualNet(pretrained=False)
        model.load_state_dict(
            checkpoint["model_state_dict"],
            strict=True,
        )
        model.eval()

        # Verify the actual two-head ResNet-50 output interface on CPU.
        with torch.inference_mode():
            cataract_logits, glaucoma_logits = model(
                torch.zeros(1, 3, 224, 224)
            )
        assert cataract_logits.shape == (1, 1)
        assert glaucoma_logits.shape == (1, 1)
        assert torch.isfinite(cataract_logits).all()
        assert torch.isfinite(glaucoma_logits).all()

        print(
            f"PASS Seed {seed}: checkpoint, SHA-256, "
            "best epoch, AUROC, architecture"
        )

    test_training_pipeline()
    print("PASS: All Task 11.1 shared-model smoke tests!")


if __name__ == "__main__":
    main()
