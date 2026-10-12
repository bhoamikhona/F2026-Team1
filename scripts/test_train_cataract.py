
import math

import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

from cataract_model import CataractOnlyNet
from fundus_dataset import (
    FundusDataset,
    get_train_transform,
    get_validation_transform,
)
from train_cataract import (
    LABELS_CSV,
    IMAGE_DIR,
    calculate_cataract_weight,
    train_one_epoch,
    validate,
)
from dual.config import set_seed


def main():
    # Use the shared project seed for reproducibility.
    set_seed(42)

    print(
        "Task 11 Cataract Training Smoke Test"
    )

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print("Device:", device)

    train_dataset = FundusDataset(
        labels_csv=LABELS_CSV,
        image_dir=IMAGE_DIR,
        split="train",
        transform=get_train_transform(),
    )

    validation_dataset = FundusDataset(
        labels_csv=LABELS_CSV,
        image_dir=IMAGE_DIR,
        split="validation",
        transform=get_validation_transform(),
    )

    print(
        "Full training split:",
        len(train_dataset),
    )

    print(
        "Full validation split:",
        len(validation_dataset),
    )

    # Select a small training subset containing
    # both cataract-positive and cataract-negative examples.
    train_labels = pd.read_csv(LABELS_CSV)

    train_labels = train_labels[
        train_labels["split"] == "train"
    ].reset_index(drop=True)

    train_positive = (
        train_labels.index[
            train_labels["cataract"] == 1
        ]
        .tolist()[:20]
    )

    train_negative = (
        train_labels.index[
            train_labels["cataract"] == 0
        ]
        .tolist()[:20]
    )

    train_indices = (
        train_positive
        + train_negative
    )

    train_subset = Subset(
        train_dataset,
        train_indices,
    )

    # Validation subset must contain both classes
    # so that AUROC can be calculated.
    validation_labels = pd.read_csv(
        LABELS_CSV
    )

    validation_labels = validation_labels[
        validation_labels["split"]
        == "validation"
    ].reset_index(drop=True)

    validation_positive = (
        validation_labels.index[
            validation_labels["cataract"] == 1
        ]
        .tolist()[:20]
    )

    validation_negative = (
        validation_labels.index[
            validation_labels["cataract"] == 0
        ]
        .tolist()[:20]
    )

    validation_indices = (
        validation_positive
        + validation_negative
    )

    validation_subset = Subset(
        validation_dataset,
        validation_indices,
    )

    # Assert that both classes are present
    # in training and validation subsets.
    assert len(train_positive) > 0, (
        "No positive training examples"
    )

    assert len(train_negative) > 0, (
        "No negative training examples"
    )

    assert len(validation_positive) > 0, (
        "No positive validation examples"
    )

    assert len(validation_negative) > 0, (
        "No negative validation examples"
    )

    assert len(train_subset) > 0, (
        "Training subset is empty"
    )

    assert len(validation_subset) > 0, (
        "Validation subset is empty"
    )

    print(
        "Smoke training positives:",
        len(train_positive),
    )

    print(
        "Smoke training negatives:",
        len(train_negative),
    )

    print(
        "Smoke validation positives:",
        len(validation_positive),
    )

    print(
        "Smoke validation negatives:",
        len(validation_negative),
    )

    # Explicitly seed the training DataLoader
    # to match the final Task 11 training script.
    generator = torch.Generator()
    generator.manual_seed(42)

    train_loader = DataLoader(
        train_subset,
        batch_size=8,
        shuffle=True,
        num_workers=0,
        generator=generator,
    )

    validation_loader = DataLoader(
        validation_subset,
        batch_size=8,
        shuffle=False,
        num_workers=0,
    )

    assert len(train_loader) > 0, (
        "Training DataLoader is empty"
    )

    assert len(validation_loader) > 0, (
        "Validation DataLoader is empty"
    )

    cataract_weight = (
        calculate_cataract_weight(
            LABELS_CSV
        )
    )

    assert math.isfinite(cataract_weight), (
        "Cataract positive weight is not finite"
    )

    assert cataract_weight > 0, (
        "Cataract positive weight must be positive"
    )

    print(
        f"Cataract positive weight: "
        f"{cataract_weight:.4f}"
    )

    pos_weight = torch.tensor(
        [cataract_weight],
        dtype=torch.float32,
        device=device,
    )

    loss_fn = nn.BCEWithLogitsLoss(
        pos_weight=pos_weight
    )

    # pretrained=False prevents an unnecessary
    # ImageNet download during the smoke test.
    model = CataractOnlyNet(
        pretrained=False
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=1e-4,
    )

    # Call the actual Task 11 training function.
    train_loss = train_one_epoch(
        model=model,
        loader=train_loader,
        optimizer=optimizer,
        loss_fn=loss_fn,
        device=device,
    )

    # Call the actual Task 11 validation function.
    (
        validation_loss,
        validation_auroc,
    ) = validate(
        model=model,
        loader=validation_loader,
        loss_fn=loss_fn,
        device=device,
    )

    # Verify numerical correctness of the outputs.
    assert math.isfinite(train_loss), (
        "Training loss is not finite"
    )

    assert math.isfinite(validation_loss), (
        "Validation loss is not finite"
    )

    assert math.isfinite(validation_auroc), (
        "Validation AUROC is not finite"
    )

    assert train_loss >= 0, (
        "Training loss is negative"
    )

    assert validation_loss >= 0, (
        "Validation loss is negative"
    )

    assert 0.0 <= validation_auroc <= 1.0, (
        "Validation AUROC is outside [0, 1]"
    )

    print(
        f"Smoke training loss: "
        f"{train_loss:.4f}"
    )

    print(
        f"Smoke validation loss: "
        f"{validation_loss:.4f}"
    )

    print(
        f"Smoke validation cataract AUROC: "
        f"{validation_auroc:.4f}"
    )

    print(
        "Training batches:",
        len(train_loader),
    )

    print(
        "Validation batches:",
        len(validation_loader),
    )

    print(
        "Cataract Task 11 smoke test passed."
    )


if __name__ == "__main__":
    main()
