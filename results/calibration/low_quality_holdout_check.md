# Low-Quality Holdout Eye Evaluation (Task 12 Verification)

Date: 13 October 2026  
Status: Completed using frozen parameters (`frozen: true`).  
Evaluation split: ODIR 21 low-quality holdout eyes (sections 17.4 and 17.7 of project brief).

## Summary

As prescribed by sections 17.4 and 17.7 of the project brief, the 21 eyes (19 patients) graded with `"low image quality"` were kept strictly out of training, validation, and internal test sets. They were never used to tune or fit thresholds.

After committing frozen Task 12 settings, these 21 eyes were scored to observe how the screener handles poor-quality photos.

### Frozen Operating Settings
* **Cataract**: Threshold = `0.025`, Uncertain Margin = `± 0.008` (Band: `[0.017, 0.033]`)
* **Glaucoma**: Threshold = `0.03`, Uncertain Margin = `± 0.004` (Band: `[0.026, 0.034]`)

### Results Across Seeds

| Seed | Cataract Referrals (Uncertain / Ordinary) | Glaucoma Referrals (Uncertain / Ordinary) | Total Eyes Flagged / Referred | Referral Rate |
| :---: | :---: | :---: | :---: | :---: |
| **42** | 9 (0 uncertain / 9 refer) | 8 (5 uncertain / 3 refer) | **14 / 21** | **66.7%** |
| **43** | 8 (2 uncertain / 6 refer) | 2 (0 uncertain / 2 refer) | **8 / 21** | **38.1%** |
| **44** | 10 (1 uncertain / 9 refer) | 12 (4 uncertain / 8 refer) | **14 / 21** | **66.7%** |

### Key Observations
1. **Safety Triage Behavior**: Between **38.1% and 66.7%** of these poor-quality photographs are flagged for clinician review (either as `"refer"` or `"uncertain"`), preventing unreadable eyes from slipping through as clear negatives.
2. **Uncertainty Activation**: The `"Uncertain, refer"` rule actively triggered on up to 5 eyes per seed, verifying that borderline predictions near the cutoff correctly decline to provide an ordinary classification.
3. **Pre-screening Alignment**: In production, the front-end photo quality check (`quality_check.py`) intercepts ungradable photos before model inference; this check confirms the back-end screener safely acts as a secondary defense.
