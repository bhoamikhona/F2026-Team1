> Historical single-model experiment, superseded for final Task 12 settings. The numerical observations are retained; they do not establish safety.

# Low-Quality Holdout Eye Evaluation (Task 12 Verification)

Date: 13 October 2026  
Status: Completed using frozen parameters (`frozen: true`).  
Evaluation split: ODIR 21 low-quality holdout eyes (sections 17.4 and 17.7 of project brief).

## Summary

As prescribed by sections 17.4 and 17.7 of the project brief, the 21 eyes (19 patients) graded with `"low image quality"` were kept strictly out of training, validation, and internal test sets. They were never used to tune or fit thresholds.

These 21 eyes were scored with the earlier single-model settings. The report does not establish that freezing was committed before evaluation.

### Frozen Operating Settings
* **Cataract**: Threshold = `0.025`, Uncertain Margin = `± 0.008` (Band: `[0.017, 0.033]`)
* **Glaucoma**: Threshold = `0.03`, Uncertain Margin = `± 0.004` (Band: `[0.026, 0.034]`)

### Results Across Seeds

| Seed | Cataract Referrals (Uncertain / Ordinary) | Glaucoma Referrals (Uncertain / Ordinary) | Total Eyes Flagged / Referred | Referral Rate |
| :---: | :---: | :---: | :---: | :---: |
| **42** | 9 (0 uncertain / 9 refer) | 8 (5 uncertain / 3 refer) | **14 / 21** | **66.7%** |
| **43** | 8 (2 uncertain / 6 refer) | 2 (0 uncertain / 2 refer) | **8 / 21** | **38.1%** |
| **44** | 10 (1 uncertain / 9 refer) | 12 (4 uncertain / 8 refer) | **14 / 21** | **66.7%** |

### Interpretation

These are referral counts, not accuracy or safety measurements. Disease grades
for these 21 low-quality eyes are not treated as negative labels. The results
must not be used to choose or adjust calibration, thresholds or margins.
