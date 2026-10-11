# Task 12 cutoff decisions for review

Status: trial. No decision thresholds or abstention settings are frozen.

The supplied project brief, section 15.2, Task 12, requires calibration,
disease thresholds and an "Uncertain, refer" cutoff to use validation data
only, with final values committed and frozen before internal or external tests.
It does not specify a numerical sensitivity target or an uncertainty measure.
Sections 17.4 and 17.7 reserve the 21 low-quality eyes for a check after fitting.

## Prepared evidence

- `glaucoma_calibration_cv_trial.json`: calibration comparison using held-out
  validation patients. Platt scaling improved log loss and Brier score for all
  three seeds compared with original scores and temperature scaling.
- `glaucoma_threshold_candidates_trial.csv`: every distinct referral decision
  boundary for the full-validation Platt fits, with false negatives, false
  positives, sensitivity, specificity, precision and referral rate.
- The threshold table uses `probability >= threshold`. No abstention is applied.
  It includes refer-all and refer-none endpoints. Blank precision means no
  images were referred, so precision is undefined.

These are validation selection results, not independent performance claims.
Base models already used validation data for checkpoint selection. Glaucoma
has only 39 positive validation eyes, so one missed positive changes measured
sensitivity by about 2.56 percentage points.

## Decisions still needed

1. Disease threshold objective: specify the sensitivity target and how to
   choose among qualifying thresholds, or agree another explicit objective.
   Do not silently assume a probability cutoff of 0.5.
2. Uncertainty definition: specify the score used to abstain and the objective
   for choosing its cutoff, including the tradeoff with how many images receive
   an ordinary decision. Proximity to 0.5 and proximity to the disease decision
   threshold are different definitions.
3. Shared model behavior: specify how the two heads combine their abstention
   decisions into the screening result.
4. Confirm the final checkpoint versions and apply the same selection protocol
   to each required model and disease head. Resolve the small glaucoma seed 43
   reproduction difference before finalizing provenance.

The 21 low-quality holdout eyes must not choose the uncertainty rule or cutoff.
After settings are fixed, report the number receiving "Uncertain, refer".

## Referral comparison

Exploratory targets are 90%, 95%, and 100% sensitivity. These are comparison
choices for this project, not requirements from the brief or clinical standards.
For each seed and target, choose the threshold with highest specificity among
those meeting the target; break identical-decision ties with highest threshold.
The script saves all nine operating points in
`glaucoma_threshold_comparison_trial.csv`, including exact thresholds.

| Target | Glaucoma eyes caught (of 39) | Missed | Non-glaucoma eyes referred (of 985), seeds 42 / 43 / 44 |
|---|---:|---:|---|
| 90% | 36 | 3 | 368 / 273 / 295 |
| 95% | 38 | 1 | 627 / 415 / 360 |
| 100% | 39 | 0 | 751 / 816 / 378 |

With only 39 positive eyes, the achieved sensitivities are 92.31%, 97.44%,
and 100%, respectively. These are empirical validation results, not guarantees
on new images. Non-glaucoma labels do not establish that an eye is healthy
with respect to other conditions.

The 95% target is a useful middle candidate for discussion: it misses one
validation positive per seed, but refers 398–665 of all 1,024 eyes. Moving
from the 90% target to 95% catches two additional positives at a cost of
259 / 142 / 65 additional false referrals for seeds 42 / 43 / 44.
This substantial and seed-dependent cost should be reported, not hidden by
averaging seeds or picking the most favorable seed. No final target is selected.

Next, define and compare an uncertainty rule separately. A referral threshold
alone does not establish when to say "Uncertain, refer". Keep all settings
unfrozen until the required model comparisons and review are complete.

## Trial uncertainty comparison

`compare_glaucoma_abstention.py` now compares a boundary-distance heuristic:
mark an eye "Uncertain, refer" when its calibrated probability is within a
margin of the disease threshold. Otherwise retain the ordinary decision.
Fit each margin to include at least 5%, 10%, or 20% of validation eyes, including
ties, and compare against no abstention. All three sensitivity targets are
included; none is selected. The saved numeric margin, rather than a new batch
percentile, would be applied to future images if this rule were eventually frozen.

At the exploratory 95% sensitivity target:

| Uncertain fraction | Uncertain eyes | Extra referrals, seeds 42 / 43 / 44 | Glaucoma still missed, seeds 42 / 43 / 44 |
|---|---:|---|---|
| None | 0 | 0 / 0 / 0 | 1 / 1 / 1 |
| 5% | 52 | 28 / 32 / 25 | 1 / 1 / 0 |
| 10% | 103 | 58 / 66 / 50 | 1 / 1 / 0 |
| 20% | 205 | 114 / 124 / 123 | 1 / 1 / 0 |

These results do not support automatically increasing the uncertainty band:
the wider bands add referrals without catching additional glaucoma cases at
this target on this validation set. Near-boundary uncertainty also fails to
catch the missed positive for seeds 42 and 43. It cannot be assumed to detect
every incorrect prediction or low-quality photo. This is an exploratory result,
not a finalized uncertainty policy or independent performance estimate.

The CSV includes coverage (fraction receiving an ordinary decision), error rate
among those ordinary decisions, and total referral burden. Class imbalance
makes overall retained error alone insufficient for selecting a rule.
The 21 holdout eyes remain unused. Cataract and combined-head behavior remain
to be evaluated before completing Task 12.
