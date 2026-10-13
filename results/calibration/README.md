# Validation calibration work

These are trial comparisons, not frozen deployment settings or independent
test results. Work is on `develop`; no merge into `main` is performed here.

## Reproduce the comparisons

From the repository root with the project environment active:

```bash
python scripts/calibrate_models.py --disease cataract
python scripts/check_calibration_cv.py --disease cataract
python scripts/compare_glaucoma_thresholds.py --disease cataract
python scripts/compare_glaucoma_abstention.py --disease cataract
```

Use `--disease glaucoma` in the same commands for glaucoma. The two comparison
scripts retain their historical filenames but support both diseases.
These commands use saved validation scores, without opening test or holdout photos.

If a checkpoint changes, regenerate the affected predictions first, for example:

```bash
python scripts/calibrate_models.py --disease cataract --collect-predictions --collect-seeds 42
```

Then rerun the other three commands above. Omitting `--collect-seeds` refreshes
all three seeds. Calibration still compares all three seeds after collection.

## Checkpoint update on 13 October 2026

- The final cataract and glaucoma training PRs are merged into `develop`.
- Final release files were checked against GitHub's SHA-256 digests.
- Cataract seed 42 was rerun by its author: its best epoch is now 1, replacing
  the earlier epoch-11 checkpoint. Its 1,024 validation predictions and all downstream trial reports were regenerated.
- All three glaucoma checkpoint tensors are exactly equal to the earlier
  versions; their checkpoint metadata changed. Cataract seeds 43 and 44 are unchanged.
- `checkpoint_release_audit.json` records original and final checkpoint hashes
  and the outcome of the tensor-by-tensor comparison.
- `*.meta.json` records checkpoint, label/source and prediction hashes. Existing
  compatible scores have an explicit migration note; this does not claim their
  provenance was recorded at their original collection time.
- Comparison runs check these records. A different local checkpoint or input
  requires regeneration. If checkpoints are absent, saved-score analysis can
  still run; it checks recorded inputs and scores but cannot verify a local model.

## Evaluation settings

All six single-disease comparisons use the same 1,024 validation images,
batch size 8, no shuffling, evaluation mode, the shared validation transform,
and preprocessed ODIR images. These match the training validation setup.
Inference here uses CPU. Small glaucoma seed-43 and refreshed cataract seed-42 AUROC differences
are recorded in `validation_reproduction_check.json`; CPU/GPU precision is a possible,
unconfirmed explanation. Original training predictions were not retained by
the model author.

Calibration cross-validation holds out whole patients. Base-model checkpoint
selection already used validation, so these results are not independent tests.
Referral and uncertainty comparisons are descriptive choices on validation,
not guarantees about future patients. The Platt tolerance accepts fitting-loss
increases up to 0.0001 with a warning and stops for larger increases; a warning
still needs inspection and does not prove the cause is rounding.

## Remaining Task 12 work

1. Obtain or confirm the requirement for the three shared two-head checkpoints.
   The available releases currently contain only six single-disease models.
2. Agree a consistent calibration, referral and uncertainty selection policy,
   based on the validation comparisons, and apply it to all required models.
3. Record and commit frozen numerical settings with their checkpoint provenance.
4. Only afterward score the 21 low-quality holdout eyes and report uncertain
   referrals and total referrals separately. Do not tune on these eyes or
   treat their missing disease grades as known negative labels.

The trial scripts intentionally do not mark Task 12 complete or freeze settings.
