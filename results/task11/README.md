# Task 11 runs

All nine Task 11 models: cataract-only, glaucoma-only and shared two-head,
three seeds each (SCRUM-55, SCRUM-69, SCRUM-70).

## Settings

Same for all nine runs.

- Backbone: ResNet-50, ImageNet weights
- Optimizer: Adam, learning rate 1e-4
- Batch size: 8
- Max epochs: 30, early stopping patience 5
- Loss: BCE with pos_weight (negatives / positives, training split)
- Labels: labels/eye_labels_task7.csv (SHA-256 67d7d8bb...e6ce7)
- Images: Preprocessed/ODIR, 4,807 train and 1,024 validation
- Stopping metric: validation AUROC of the model's own disease.
  The shared model uses the mean of its cataract and glaucoma AUROCs.

## Runs

AUROC is on the validation split at the best epoch. Validation was also
used to pick that epoch, so these are not test results.

| Model | Seed | Best epoch | Cataract AUROC | Glaucoma AUROC | Checkpoint SHA-256 |
|---|---:|---:|---:|---:|---|
| Cataract-only | 42 | 1 | 0.986196 | | 8379604cfed3ccbe2c65e1997139dc94a617bd5f22062e514aa9bc6c9102c32e |
| Cataract-only | 43 | 7 | 0.985396 | | 7806ca48ec1ab1905f88da0dca4b640e3194a075a4fcb5c11762953c9d156b63 |
| Cataract-only | 44 | 7 | 0.982040 | | c5be475f4e8fb32e684493cd88bd92f24037b6506f90713b633237cbbeaa7a31 |
| Glaucoma-only | 42 | 8 | | 0.891136 | 28e6d6839dcd8c34cb4a3de372e22ec2bbca4081419331954c5aa74c03483259 |
| Glaucoma-only | 43 | 3 | | 0.916608 | 132a11163f4e43a131b56610cad54c12087b8cf683340f34b66625676cb90da7 |
| Glaucoma-only | 44 | 10 | | 0.925966 | 9e47544f36b8f6a6c5dc76b07dc2e5b52ae7203997dc437b75b1b444ea84c992 |
| Shared two-head | 42 | 7 | 0.988130 | 0.925342 | 9c4b9e7b4de308dd428af3f22a1eae0b5f3d857aa91464067c7e287b7dc910c7 |
| Shared two-head | 43 | 5 | 0.977350 | 0.909671 | ab1be7650397e95f9da0236526fb84f38ee151c232a12b2cf2e58f7d19c1f83d |
| Shared two-head | 44 | 14 | 0.978083 | 0.914903 | 809fe9d70a23e42c417b579bc7792f5d7de5dd36efe6c21bda640d8d170aeffe |

## Checkpoints

Checkpoints are not in the repo. Download them from the releases into
checkpoints/task11/cataract/, checkpoints/task11/glaucoma/ and
checkpoints/task11/shared/.

- Cataract-only: https://github.com/htmw/F2026-Team1/releases/tag/task11-cataract-checkpoints
- Glaucoma-only: https://github.com/htmw/F2026-Team1/releases/tag/task11-glaucoma-checkpoints
- Shared two-head: https://github.com/htmw/F2026-Team1/releases/tag/task11-shared-checkpoints

Check a download against the table:

    shasum -a 256 checkpoints/task11/*/*.pt

Cataract seed 42 was retrained and replaced on 12 October 2026 (best epoch
11 became 1). Only the hash above is the final version.

## Files

- cataract_results.csv, cataract_training_history.csv, cataract_training_summary.md
- glaucoma_results.csv, glaucoma_training_history.csv, glaucoma_training_summary.md
- shared_results.csv, shared_training_history.csv, task11_1_shared_training_summary.md

Training scripts: scripts/train_cataract.py, scripts/train_glaucoma.py,
scripts/train_dual_task11.py. Smoke tests: scripts/test_train_cataract.py,
scripts/test_train_glaucoma.py, scripts/test_train_dual_task11.py.

The script SHA-256 in shared_results.csv (64ab51...) is for the copy run on
Kaggle, which had Windows line endings. The repo file has the same code.
