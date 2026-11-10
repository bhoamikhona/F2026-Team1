"""Checks for pairing, image alignment, and reference verification."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compute_task17_paired_differences import align_external, check_reference, paired_result
from external_metrics import bootstrap_indices


def test_identical_models_have_zero_paired_interval():
    y = np.array([0, 1, 0, 1, 0, 1])
    scores = np.array([0.1, 0.7, 0.4, 0.3, 0.2, 0.9])
    draws, _ = bootstrap_indices(y, 40)
    result = paired_result(y, scores, scores, draws)
    assert result["difference"] == result["ci_low"] == result["ci_high"] == 0


def test_swapping_models_reverses_difference_and_interval():
    y = np.array([0, 1, 0, 1, 0, 1])
    a = np.array([0.1, 0.7, 0.4, 0.3, 0.2, 0.9])
    b = np.array([0.2, 0.8, 0.3, 0.6, 0.1, 0.7])
    draws, _ = bootstrap_indices(y, 40)
    forward, reverse = paired_result(y, a, b, draws), paired_result(y, b, a, draws)
    assert reverse["difference"] == pytest.approx(-forward["difference"])
    assert reverse["ci_low"] == pytest.approx(-forward["ci_high"])
    assert reverse["ci_high"] == pytest.approx(-forward["ci_low"])


def example_rows():
    return [dict(path=str(i), model_kind=k, seed=str(s), label=str(i), raw_logit=str(i))
            for k in ("single", "shared") for s in (42, 43, 44) for i in (0, 1)]


def test_alignment_uses_paths_not_row_positions():
    rows = example_rows()
    rows[-2:] = reversed(rows[-2:])
    y, scores = align_external(rows)
    np.testing.assert_array_equal(y, [0, 1])
    np.testing.assert_array_equal(scores["shared", 44], [0, 1])


@pytest.mark.parametrize("problem", ["duplicate", "missing", "label"])
def test_invalid_pairing_is_rejected(problem):
    rows = example_rows()
    if problem == "duplicate":
        rows.append(rows[-1].copy())
    elif problem == "missing":
        rows.pop()
    else:
        rows[-1]["label"] = "0"
    with pytest.raises(ValueError):
        align_external(rows)


def test_wrong_reference_interval_is_rejected():
    result = dict(single_auroc=1, single_ci_low=1, single_ci_high=1)
    reference = dict(auroc=1, lo=0.8, hi=1)
    with pytest.raises(ValueError, match="not reproduced"):
        check_reference(result, reference, reference, "lo", "hi")
