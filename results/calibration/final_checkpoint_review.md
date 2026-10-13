# Final-checkpoint calibration review (13 October 2026)

Status: trial. No settings frozen. Only validation data used.

Cataract seed 42 has been refreshed from the final release. All final checkpoint hashes were verified. The three glaucoma tensor sets and cataract seeds 43/44 are unchanged.

## Patient-grouped calibration comparison

| Disease | Seed | Original loss | Temperature loss | Platt loss |
|---|---:|---:|---:|---:|
| glaucoma | 42 | 0.385794 | 0.357187 | 0.113016 |
| glaucoma | 43 | 1.040601 | 0.674834 | 0.105839 |
| glaucoma | 44 | 0.202151 | 0.190837 | 0.103184 |
| cataract | 42 | 0.297270 | 0.285883 | 0.059151 |
| cataract | 43 | 0.121435 | 0.124362 | 0.059805 |
| cataract | 44 | 0.114798 | 0.114238 | 0.063394 |

Platt has the lowest held-out calibration loss among these methods for every seed. This supports proposing Platt for the available single-disease models. This is not independent model testing: the base checkpoints already used validation for selection.

## Exploratory 95% sensitivity target

| Disease | Seed | Disease caught | Missed | Other eyes referred | Total referred |
|---|---:|---:|---:|---:|---:|
| glaucoma | 42 | 38 | 1 | 627 | 665 |
| glaucoma | 43 | 38 | 1 | 415 | 453 |
| glaucoma | 44 | 38 | 1 | 360 | 398 |
| cataract | 42 | 44 | 2 | 72 | 116 |
| cataract | 43 | 44 | 2 | 65 | 109 |
| cataract | 44 | 44 | 2 | 83 | 127 |

This target is a project candidate, not specified by the brief or a clinical standard. Compare referral burden across all seeds before agreement; do not select only the best seed.

## Adding a 5% boundary-distance uncertainty band

| Disease | Seed | Uncertain eyes | Additional referrals | Disease still missed |
|---|---:|---:|---:|---:|
| glaucoma | 42 | 52 | 28 | 1 |
| glaucoma | 43 | 52 | 32 | 1 |
| glaucoma | 44 | 52 | 25 | 0 |
| cataract | 42 | 52 | 32 | 1 |
| cataract | 43 | 52 | 36 | 1 |
| cataract | 44 | 52 | 26 | 1 |

Boundary distance is a heuristic, not a proven detector of poor photos or wrong predictions. These are fitting/selection results, not independent performance estimates. The 21 low-quality holdout eyes have not been used.

## Before freezing

- Obtain or clarify the three shared two-head checkpoints required by the brief.
- Agree the referral sensitivity objective and uncertainty objective; apply one documented policy across seeds.
- Record the small AUROC reproduction differences (glaucoma 43 and cataract 42) without claiming an unverified cause.
- Freeze exact parameters with checkpoint provenance, then run the 21-eye check without retuning.

Seven targeted tests passed for prediction provenance and preservation of existing results when threshold candidates are empty.
