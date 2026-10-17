# SCRUM-44: External evaluation metrics and protocol

Owner: External validation and calibration role (Negar)

Version: 1.0, 14 October 2026

Status: Draft for team review. No external model evaluation has been run as part of this document.

## Purpose and scope

Test whether the frozen models work on photos from sources outside ODIR. This
document defines the rules before the external results are seen. SCRUM-44 prepares
the protocol; Task 14 implements and runs the final external evaluation. Task 12
supplies frozen calibration, thresholds and uncertainty margins. Task 17 compares
the shared and single-disease models.

In simple words: agree on the exam and marking rules first, then give every model
the same exam. Do not change the rules after seeing the answers.

The brief requires external AUC with confidence intervals, calibration reporting,
separate dataset results and frozen validation-derived settings. The additional
metric definitions, bootstrap procedure and output schema below are proposed
implementation choices for team review, not requirements quoted from the brief.

## 1. Datasets and labels

Use only the committed CSVs under `labels/external/`. Counts below were checked
against those CSVs, without running inference on the photos.

| Dataset | Label file | Images | Cataract positives / negatives | Glaucoma positives / negatives |
|---|---|---:|---|---|
| ORIGA | `origa_labels.csv` | 650 | Not labeled | 168 / 482 |
| DRISHTI-GS | `drishti_labels.csv` | 101 | Not labeled | 70 / 31 |
| ACRIMA | `acrima_labels.csv` | 705 | Not labeled | 396 / 309 |
| retina_dataset_2016 | `retina_labels.csv` | 601 | 100 / 501 | 101 / 500 |

There are 2,057 unique dataset/path entries. Every row must have `split=test`.
For DRISHTI, both the original Training and Test folders are external test data for
DUAL. Neither folder may be used to train or tune DUAL.

Missing cataract labels in the first three datasets are **unknown**, not zero.
Do not calculate cataract metrics on them. A negative label means negative for the
specified target according to the dataset labels, not a completely healthy eye.
In retina_dataset_2016, other disease folders remain target-negative as defined
by the approved label-building script; do not silently restrict testing to normal
and target-positive folders.

Report ORIGA and DRISHTI separately. ACRIMA gets its own row because the photos
are tightly cropped around the optic disc. Retina gets its own dataset row with
cataract and glaucoma results side by side in the presentation. Machine-readable
tables may use separate disease rows. Do not pool datasets into one headline AUC.

The repository README records Professor Wong's approval for academic use. Retain
the stated provenance limitation for retina_dataset_2016; approval does not supply
missing hospital, camera or grading information.

## 2. Models and the freeze gate

Evaluate seeds 42, 43 and 44 for each applicable model:

- Cataract-only versus the shared cataract head on retina_dataset_2016.
- Glaucoma-only versus the shared glaucoma head on all four datasets.

This produces 30 dataset/disease/model/seed metric rows. Keep every seed; do not
choose the best external seed or average model predictions into an unplanned
ensemble. A summary across seeds is a summary of experiments, not a new model.

Before the run, record the approved protocol commit and a reviewed settings file
whose exact bytes have been committed. It must contain `status=frozen`,
`frozen=true`, a review reference, and settings for the exact checkpoint/head/seed.
Verify the checkpoint SHA-256 hashes, calibration parameters, thresholds, margins,
label hashes and inference code versions. Archive these in the run manifest.

The approved settings are in `results/calibration/frozen_settings.json` (17 October
2026), with shared seed 42 selected for the app. Verify the exact committed file
and checkpoint hashes before external testing. `settings_review.json` and files
under `results/calibration/archive/` are historical proposals, not the final freeze.

No training, early stopping, recalibration, threshold selection, margin adjustment,
dataset rebalancing or preprocessing tuning may use external outcomes. Any choice
of a deployment model must be made before looking at those outcomes.

## 3. Input and inference procedure

1. Verify the dataset manifest, label schemas, expected counts, unique dataset/path
   keys, binary labels, file existence and checkpoint/settings identities.
2. Record contamination-check evidence. The existing
   `scripts/check_dataset_overlap.py` compares exact MD5 file fingerprints between
   ODIR and retina_dataset_2016. It does not detect resized or edited copies and
   does not establish independence of every external dataset. The brief's Task 5
   also calls for thumbnail comparison. Resolve that gap, or record an explicitly
   reviewed deviation and its limitation, before presenting independence claims.
3. Load the already approved 512-by-512 copies from `Preprocessed/`, preserving the
   nested subfolders. Do not identify images by filename alone across datasets.
   For example, `data/External/ORIGA/ORIGA/ORIGA/Images/001.jpg` maps to
   `Preprocessed/ORIGA/ORIGA/ORIGA/Images/001.jpg`. Generally, take the relative path
   below `data/External/<dataset>/` and append it to `Preprocessed/<dataset>/`.
4. Use the same RGB conversion and `get_validation_transform()` as calibration:
   ImageNet normalization, no random augmentation, model evaluation mode and
   inference mode. Reference execution is CPU, batch size 8, no shuffling. Record
   software versions and device. A different implementation needs equivalence
   verification before final testing, not tuning on external outcomes.
5. Run all prescribed models in one preregistered evaluation campaign. Save raw
   logits once, then derive metrics from that immutable prediction artifact.
   Apply each head's frozen Platt scale and offset in float64, matching Task 12.
6. Never silently drop an image because it is blurry, washed out, misclassified or
   uncertain. The primary model benchmark includes all processable labeled eyes.
   It does not apply the app's upload-quality gate as an exclusion filter. If an
   end-to-end app evaluation is added, report quality-gate outcomes separately,
   including counts and reasons, and do not disguise them as negative predictions.
7. Missing files, failed decoding, nonfinite scores or count mismatches stop the
   headline run. Investigate and record the failure. Do not publish a reduced
   denominator without a documented, reviewed exception and an exclusion table.

"Once" means no repeated selection using test results. A deterministic rerun for
verification or a documented software correction may be necessary. Preserve the
original artifacts and reason, obtain review, and report corrected results rather
than selecting whichever run looks better.

## 4. Required metrics and exact meanings

Calculate per dataset, disease, model type and seed. Use calibrated probabilities
on all eligible labeled images for the primary ranking and calibration metrics,
including images that receive an uncertain decision.

| Metric | Definition and reporting rule |
|---|---|
| AUROC, primary ranking metric | ROC area from continuous scores, not binary decisions. Report a 95% bootstrap interval. Retain raw logits for audit. |
| Average precision, secondary | Use non-interpolated average precision (`average_precision_score`), not trapezoidal PR area. Report the dataset's positive fraction as its prevalence baseline. |
| Confusion matrix | TP, FP, TN and FN with actual labels as rows and predicted referral as columns. Include counts, not only percentages. |
| Sensitivity / recall | `TP / (TP + FN)`: share of target-positive eyes referred. |
| Specificity | `TN / (TN + FP)`: share of target-negative eyes not referred. |
| Precision / PPV | `TP / (TP + FP)`: share of referred eyes labeled target-positive. |
| NPV | `TN / (TN + FN)`: share of non-referred eyes labeled target-negative. |
| Balanced accuracy | `(sensitivity + specificity) / 2`; ordinary accuracy alone is not a headline metric. |
| Brier score | Mean `(p - y)^2`; lower is better. Compute before and after frozen calibration. |
| Log loss | Mean binary cross entropy. Use a numerically stable logit implementation, with raw and calibrated logits, rather than taking logs of rounded probabilities. |
| ECE and reliability table | Ten fixed equal-width bins on [0,1]. Lower bound inclusive, upper exclusive except the last includes 1. ECE is `sum(n_bin / N * abs(mean_p - positive_fraction))`. Save bin counts, mean probability and observed fraction. Empty bins have count zero and null means; they contribute zero to ECE. |

Report undefined ratios as null with a reason, not zero. AUROC is undefined when
only one label class is present. For plots and tables, show sparse-bin counts and
do not interpret a low ECE alone as proof of good calibration. External prevalence
can differ from ODIR; measure any calibration deterioration without refitting.

## 5. Referral and uncertainty accounting

For each calibrated probability `p`, use its exact frozen threshold `t` and margin
`m`, without rounding:

```text
uncertain      = abs(p - t) <= m
ordinary_refer = (p >= t) and not uncertain
no_concern     = (p < t) and not uncertain
total_refer    = ordinary_refer or uncertain
```

Publish two operating-point tables:

1. **Threshold only:** classify `p >= t` as positive, without abstention.
2. **Final referral policy:** count uncertain eyes as referrals. Use this policy for
   the main referral sensitivity, specificity, PPV, NPV and total referral rate.

Also report uncertain count/rate, ordinary referral count, no-concern count,
coverage `(N - uncertain_count) / N`, and error rate among retained decisions.
Retained error is the fraction of non-uncertain eyes whose threshold-only decision
disagrees with the target label; it is null if none are retained. Give the retained
denominator and class counts. Never omit uncertain eyes from the primary AUROC,
calibration or final-referral denominators to improve the apparent result.

The margin is fixed from validation. Do not force 5% uncertainty on an external
dataset; its actual uncertainty rate is a result. Report combined "either disease"
referral counts only where both outputs exist. Disease accuracy for an "either
disease" label requires both ground-truth labels, so it is only applicable to
retina_dataset_2016 among these external sets. Per-disease results remain primary.

## 6. Confidence intervals and seed variation

Proposed implementation: 2,000 valid bootstrap replicates, RNG seed 42, percentile
95% interval using the 2.5th and 97.5th percentiles. Freeze this choice before the
run. For each dataset/disease, reuse the same resampling indices across model types
and seeds. Never refit calibration or thresholds inside a test bootstrap.

If verified patient IDs are available, resample patients with replacement and keep
all eyes for each sampled patient. Do not infer patient IDs from filenames without
validated source information. The current external CSVs contain no patient IDs,
so the fallback is image-level resampling, explicitly labeled as assuming
independent images. Possible fellow-eye dependence can make those intervals too
narrow. This limitation must appear beside the results.

Redraw single-class samples for AUROC, with at most 10,000 attempts to obtain
2,000 valid replicates. Record attempts and valid counts. If insufficient, flag
the interval rather than silently changing the method. For other metrics with
undefined denominators, omit only that replicate's undefined metric, report its
valid count, and withhold its interval if fewer than 1,900 valid values remain.

Report intervals for AUROC and, as secondary estimates, AP, sensitivity,
specificity, PPV, NPV, Brier score and referral/uncertainty rates. Report log loss,
ECE and reliability-bin values descriptively. These intervals describe test-sample
uncertainty conditional on a trained model and frozen settings.

Separately show every seed and the mean and sample standard deviation (`ddof=1`)
across the three seeds. Do not treat three seeds as three independent datasets,
average interval endpoints, or call the seed spread a 95% confidence interval.
For Task 17, shared-minus-single AUROC differences use the same bootstrap samples
for the paired models. Report paired differences per seed and the spread across
seeds; do not select an external winner from one favorable seed.

## 7. Saved artifacts and reporting layout

Task 14 should write versioned artifacts under `results/external/<run_id>/`:

| Artifact | Required contents |
|---|---|
| `run_manifest.json` | Protocol/code/settings commits and hashes, checkpoint hashes, label and image-manifest hashes, dataset counts, seeds, transforms, device, package versions, bootstrap parameters, start/end times and failure log. |
| `predictions.csv` | Dataset, image path, model type, seed, disease, target label, raw logit, calibrated probability, threshold, margin, uncertain flag and final decision. One row per applicable image/head/model/seed. |
| `metrics.csv` | Dataset, disease, model type, seed, policy, N, positive/negative counts, TP/FP/TN/FN, metric values, interval bounds, resampling unit and valid replicate counts. |
| `calibration_bins.csv` | Dataset/head/model/seed, raw or calibrated method, fixed bin boundaries, count, mean probability and observed fraction. |
| `external_results.md` | Separate dataset tables, each seed plus mean/sample SD, model comparisons, calibration plots/tables, exclusions, limitations and exact run provenance. |

No external result numbers are filled in now. Compare external AUROC with the
corresponding frozen model's internal-test AUROC once Task 13 is available; do not
substitute validation performance for an independent internal baseline. Report
deterioration and negative findings without changing the frozen model.

The 21 low-quality ODIR eyes are a separate Task 12 check, not an external dataset.
They have unreliable disease negatives: report uncertain and total referrals,
not disease accuracy or specificity. Their earlier single-model evaluation must
remain documented. Haze and heatmap checks belong to Tasks 15 and 16; ACRIMA and
retina_dataset_2016 are excluded from the disc-outline heatmap check.

## 8. Completion and review

SCRUM-44 is ready for review when dataset/head mappings, metrics, confidence
intervals, frozen-setting requirements, uncertainty accounting and output artifacts
are documented. Close it after team review and merge into `main`, following the
team's Jira rule. Running external inference is not required to finish SCRUM-44.

Before Task 14, confirm the frozen settings, accept or revise the proposed
bootstrap choices, record the patient-ID limitation, and resolve the overlap-check
scope. Test the future evaluation implementation on synthetic fixtures for perfect
predictions, ties, one-class input, zero referrals, all-uncertain decisions,
nonfinite predictions and model/label fingerprint mismatches before external use.

## Sources and requirement mapping

- Supplied *Dual Ocular Disease Screener: Team Project Brief and Sprint Plan*
  (`Project_Dual.docx.pdf`): sections 5 and 8.4 (dataset reporting), 9.4 (ablation),
  11.2 (test separation), Tasks 12-14 on page 27 (freeze and testing), Task 17 on
  page 29 (seed comparisons), and sections 17.4/17.7 on pages 32-33 (low-quality check).
- Repository [README](../../README.md): approved data storage, dataset permission
  and holdout decisions. These current decisions supersede the brief's older
  pending approval and Google Drive storage wording.
- [External labels](../../labels/external/),
  [preprocessing](../../scripts/preprocess_images.py),
  [validation transforms](../../scripts/fundus_dataset.py), and
  [Task 12 settings review](../../results/calibration/settings_review.md).
- [Exact-file overlap script](../../scripts/check_dataset_overlap.py): its actual
  scope is stated in section 3; no near-duplicate guarantee is inferred.
