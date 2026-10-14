# Task 12 settings for review

Not frozen. Validation selection results, not independent test performance.

Each model/head/seed has its own cutoff. Sensitivity and specificity below include uncertain referrals.

| Model | Disease | Seed | Threshold | Margin | Sensitivity | Specificity | Referred | Uncertain |
|---|---|---|---|---|---|---|---|---|
| single | cataract | 42 | 0.03000240 | 0.01067165 | 97.8% | 88.2% | 160/1024 | 52/1024 |
| single | cataract | 43 | 0.02433586 | 0.00680830 | 97.8% | 87.4% | 168/1024 | 52/1024 |
| single | cataract | 44 | 0.02587683 | 0.01296876 | 97.8% | 87.1% | 171/1024 | 52/1024 |
| single | glaucoma | 42 | 0.02779689 | 0.00161432 | 87.2% | 74.6% | 284/1024 | 52/1024 |
| single | glaucoma | 43 | 0.03318691 | 0.00723468 | 87.2% | 83.9% | 193/1024 | 52/1024 |
| single | glaucoma | 44 | 0.03055845 | 0.00413170 | 89.7% | 75.8% | 273/1024 | 52/1024 |
| shared | cataract | 42 | 0.02827741 | 0.01853742 | 97.8% | 89.4% | 149/1024 | 52/1024 |
| shared | cataract | 43 | 0.05228055 | 0.02817344 | 91.3% | 91.4% | 126/1024 | 52/1024 |
| shared | cataract | 44 | 0.08257842 | 0.05152550 | 93.5% | 92.4% | 117/1024 | 52/1024 |
| shared | glaucoma | 42 | 0.03662686 | 0.00661679 | 84.6% | 83.9% | 192/1024 | 52/1024 |
| shared | glaucoma | 43 | 0.08014794 | 0.02548987 | 79.5% | 90.1% | 129/1024 | 52/1024 |
| shared | glaucoma | 44 | 0.01911136 | 0.00145132 | 94.9% | 68.2% | 350/1024 | 52/1024 |

Use the full precision JSON values, not rounded table values.

Next: team review of the policy and settings, commit frozen values, then run the 21-eye holdout check without tuning.
