# Final low-quality holdout check

Run date: 17 October 2026. Frozen settings committed first in `2920a71`.

The approved settings were applied to 21 low-quality eyes from 19 patients. No calibration or threshold fitting was performed on these images. Earlier single-model observations are preserved separately; this is not claimed to be a previously untouched check set.

| Model | Seed | Output | Uncertain | Ordinary referrals | Total referrals |
|---|---|---|---|---|---|
| single | 42 | cataract | 2/21 | 7/21 | 9/21 |
| single | 42 | glaucoma | 3/21 | 13/21 | 16/21 |
| single | 42 | either_eye_result | 4/21 | 15/21 | 19/21 |
| single | 43 | cataract | 3/21 | 5/21 | 8/21 |
| single | 43 | glaucoma | 3/21 | 3/21 | 6/21 |
| single | 43 | either_eye_result | 6/21 | 5/21 | 11/21 |
| single | 44 | cataract | 3/21 | 6/21 | 9/21 |
| single | 44 | glaucoma | 7/21 | 12/21 | 19/21 |
| single | 44 | either_eye_result | 10/21 | 10/21 | 20/21 |
| shared | 42 | cataract | 3/21 | 6/21 | 9/21 |
| shared | 42 | glaucoma | 6/21 | 7/21 | 13/21 |
| shared | 42 | either_eye_result | 8/21 | 7/21 | 15/21 |
| shared | 43 | cataract | 2/21 | 7/21 | 9/21 |
| shared | 43 | glaucoma | 0/21 | 4/21 | 4/21 |
| shared | 43 | either_eye_result | 2/21 | 9/21 | 11/21 |
| shared | 44 | cataract | 4/21 | 3/21 | 7/21 |
| shared | 44 | glaucoma | 2/21 | 7/21 | 9/21 |
| shared | 44 | either_eye_result | 6/21 | 5/21 | 11/21 |

For the combined eye result, uncertain means either head is uncertain. Total referral means either head requests referral. The same eye is counted once. Ordinary combined referrals exclude any eye already counted as uncertain.

These counts describe referral behavior. The low-quality eyes do not have reliable disease-negative labels, so no sensitivity, specificity or safety claim is made from this check.

Frozen settings SHA-256: `d1d97e58e25d32892527db0ad459a7b9d555391e5abda924ff33f1700f14db71`.
The JSON report contains all 252 per-head observations. Independent recounting verified all 18 summary rows and all six combined eye summaries.
