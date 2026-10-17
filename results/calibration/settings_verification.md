# Task 12 verification record

Checked on 14 October 2026. Settings remain pending team review.

- All three shared checkpoint hashes match the published release.
- All three shared models scored exactly 1,024 validation images for both heads.
- All six shared-head validation AUROCs reproduce checkpoint metadata within 0.0001.
- Platt scaling has the lowest patient-grouped cross-validation log loss for all twelve head/seed pairs.
- Independent sklearn ROC checks confirm each selected threshold maximizes the specified weighted objective.
- Independent confusion matrices confirm threshold-only and uncertainty-inclusive referral counts.
- All twelve uncertainty bands contain 52 validation eyes, approximately 5.08%.
- Out-of-fold predictions contain 12,288 rows; each patient stays in one held-out fold within each run.
- Independent sklearn log-loss and Brier calculations match the saved cross-validation metrics.
- Seventeen calibration/provenance/decision-rule tests passed.
- Changed Python scripts compile and the tracked diff passes whitespace checks.
- API tests could not be collected because fastapi is absent from the active environment. The mock cutoffs were restored to develop values; real settings were not connected to the app.
- No new holdout, internal-test or external-test evaluation was run. The holdout evaluator is prepared but has not been run with real frozen settings.

## Shared AUROC reproduction

| Seed | Head | Checkpoint | Local CPU | Difference |
|---|---|---|---|---|
| 42 | cataract | 0.988130168045 | 0.988152396195 | +0.00002223 |
| 42 | glaucoma | 0.925341663413 | 0.925315631915 | -0.00002603 |
| 43 | cataract | 0.977349515426 | 0.977349515426 | +0.00000000 |
| 43 | glaucoma | 0.909670701549 | 0.909670701549 | +0.00000000 |
| 44 | cataract | 0.978083044367 | 0.978083044367 | +0.00000000 |
| 44 | glaucoma | 0.914903032670 | 0.914955095666 | +0.00005206 |

Small differences are recorded rather than called exact matches. Precision/device effects are a possible explanation, not a confirmed diagnosis.

## Decision still needed

The proposed 1.5 sensitivity weighting is a tradeoff, not a minimum-sensitivity constraint. Shared glaucoma sensitivity including uncertain referrals ranges from 79.5% to 94.9%. Review whether this satisfies the project objective before freezing. Use validation data only for any policy revision.

Each checkpoint/head has separate calibration, cutoff and uncertainty settings. Do not average seeds or substitute a different checkpoint without a separately validated policy.
