# Single-disease and shared-model comparison

## Purpose

This comparison examines whether sharing one ResNet-50 backbone
for cataract and glaucoma improves performance compared with
training a separate model for each disease.

## Internal test results

The table uses the existing ODIR internal-test results.
Each model was trained with seeds 42, 43, and 44.
Values show mean AUROC and sample standard deviation across these seeds.

| Disease | Single model: mean AUROC ± SD | Shared model: mean AUROC ± SD | Shared minus single |
|---|---:|---:|---:|
| Cataract | 0.9910 ± 0.0036 | 0.9948 ± 0.0004 | +0.0038 |
| Glaucoma | 0.9241 ± 0.0178 | 0.9309 ± 0.0125 | +0.0068 |

The shared model has a slightly higher average AUROC for both diseases.
These differences alone do not establish a statistically significant improvement.

Source: [Internal test results](../task13/internal_results.md).


## External glaucoma results

These results use the frozen calibration and thresholds.
Values show mean AUROC and sample standard deviation across
seeds 42, 43, and 44.

| Dataset | Single model: mean AUROC ± SD | Shared model: mean AUROC ± SD | Shared minus single |
|---|---:|---:|---:|
| ORIGA | 0.7687 ± 0.0158 | 0.7487 ± 0.0156 | -0.0200 |
| DRISHTI-GS | 0.8846 ± 0.0205 | 0.8820 ± 0.0117 | -0.0026 |
| ACRIMA | 0.4078 ± 0.0952 | 0.5551 ± 0.0752 | +0.1473 |
| retina_dataset_2016 | 0.7411 ± 0.0541 | 0.7521 ± 0.0453 | +0.0110 |

The shared model has higher average AUROC on ACRIMA and
retina_dataset_2016, and lower average AUROC on ORIGA and DRISHTI-GS.
There is no consistent improvement across all external datasets.

Source: [External test results](../external/frozen_run_20261030/external_results.md).

## Internal versus external glaucoma AUROC

Values are means across the three seeds. Drop is internal minus external
AUROC, calculated from the displayed means. These comparisons describe
different test populations, not paired observations across datasets.

| Dataset | Model | Internal AUROC | External AUROC | Drop |
|---|---|---:|---:|---:|
| ORIGA | single | 0.9241 | 0.7687 | 0.1554 |
| ORIGA | shared | 0.9309 | 0.7487 | 0.1822 |
| DRISHTI-GS | single | 0.9241 | 0.8846 | 0.0395 |
| DRISHTI-GS | shared | 0.9309 | 0.8820 | 0.0489 |
| ACRIMA | single | 0.9241 | 0.4078 | 0.5163 |
| ACRIMA | shared | 0.9309 | 0.5551 | 0.3758 |
| retina_dataset_2016 | single | 0.9241 | 0.7411 | 0.1830 |
| retina_dataset_2016 | shared | 0.9309 | 0.7521 | 0.1788 |

Both model types have lower mean glaucoma AUROC on every external dataset
than on ODIR. The largest drop is on ACRIMA. This does not identify the
cause of the change.

## Paired differences

Each value is shared minus single AUROC for the same training seed.
Both models use the same 2,000 bootstrap samples (random seed 42).
The 95% intervals are the 2.5th and 97.5th percentiles of the paired
differences, not differences between separate interval endpoints.

| Test | Seed 42 [95% CI] | Seed 43 [95% CI] | Seed 44 [95% CI] | Mean ± SD |
|---|---:|---:|---:|---:|
| ODIR internal, cataract | +0.0078 [+0.0017, +0.0149] | +0.0011 [-0.0025, +0.0056] | +0.0026 [-0.0014, +0.0073] | +0.0038 ± 0.0035 |
| ODIR internal, glaucoma | +0.0041 [-0.0366, +0.0453] | +0.0005 [-0.0341, +0.0302] | +0.0159 [-0.0413, +0.0805] | +0.0068 ± 0.0081 |
| ORIGA, glaucoma | -0.0131 [-0.0517, +0.0252] | -0.0341 [-0.0700, +0.0013] | -0.0129 [-0.0466, +0.0187] | -0.0200 ± 0.0122 |
| DRISHTI-GS, glaucoma | +0.0028 [-0.0579, +0.0667] | -0.0161 [-0.0576, +0.0255] | +0.0055 [-0.0617, +0.0709] | -0.0026 ± 0.0118 |
| ACRIMA, glaucoma | +0.1954 [+0.1553, +0.2363] | +0.1370 [+0.0946, +0.1787] | +0.1094 [+0.0775, +0.1412] | +0.1473 ± 0.0439 |
| retina_dataset_2016, glaucoma | -0.0117 [-0.0703, +0.0503] | +0.0201 [-0.0246, +0.0661] | +0.0247 [-0.0342, +0.0827] | +0.0110 ± 0.0198 |

Intervals describe test-sample uncertainty for each fitted model pair; SD describes
variation in the point differences across training seeds. An interval containing
zero is not evidence that the models are equivalent. These are individual 95%
intervals without adjustment for multiple comparisons.

Source: [Paired AUROC differences](paired_auroc_differences.csv).
Reproduce with `python scripts/compute_task17_paired_differences.py`.
Input hashes and settings: [analysis manifest](paired_analysis_manifest.json).

## Conclusion

Sharing one backbone did not give a consistent improvement across the tests.
Internally, the shared model had higher AUROC for both diseases in all three
seeds, but five of the six paired intervals include zero; only cataract seed 42
has an interval entirely above zero. Externally, shared glaucoma AUROC was
lower on ORIGA in all seeds, although all three intervals include zero.
On ACRIMA, shared AUROC was higher in all seeds and all three intervals exclude
zero, but its mean AUROC was still only 0.5551, compared with 0.4078 for the
single model. On DRISHTI-GS and retina_dataset_2016, the direction changed
across seeds and all intervals include zero. The results therefore show a
clearer advantage on ACRIMA for these fitted models, but not a general advantage
from sharing the backbone. These individual intervals are not adjusted for
multiple comparisons, and intervals containing zero do not prove equivalence.

## Evaluation notes

- We used the saved test results without retraining the models.
- We kept the calibration and thresholds fixed.
- The standard deviation shows how much results varied across seeds.
- Paired internal confidence intervals resample patients and retain both eyes.
  Paired external intervals resample images because patient IDs were unavailable.
  Possible dependence between fellow eyes may make external intervals too narrow.
- Both models use identical resamples within each comparison. The analysis
  reproduced the original individual-model AUROCs and intervals before saving
  paired results. Calibration and thresholds were not refitted.
- The datasets contain different images and patient groups.
  We cannot tell from these results alone why performance changed.
