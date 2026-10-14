"""Check threshold optimization and uncertainty referral accounting."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from select_calibration_settings import select_threshold, choose_margin, decision_metrics
from evaluate_calibration_holdout import verify_settings


def test_sensitivity_weight_changes_operating_point():
    # Catching the second positive costs one false positive; 1.5x weighting prefers it.
    p, y = np.array([0.9, 0.8, 0.7, 0.1]), np.array([1, 0, 1, 0])
    threshold, objective = select_threshold(p, y)
    assert threshold == 0.7
    assert objective == pytest.approx(0.8)


def test_exhaustive_objective_matches_independent_reference():
    rng = np.random.default_rng(42)
    for _ in range(10):
        p, y = rng.random(30), np.r_[np.ones(7), np.zeros(23)]
        threshold, score = select_threshold(p, y)
        reference = []
        for t in np.r_[0, p, np.nextafter(max(p), np.inf)]:
            sensitivity = np.mean(p[y == 1] >= t)
            specificity = np.mean(p[y == 0] < t)
            reference.append(0.6*sensitivity + 0.4*specificity)
        assert score == pytest.approx(max(reference))
        assert threshold in np.r_[0, p, np.nextafter(max(p), np.inf)]


def test_margin_includes_boundary_ties():
    p = np.array([0.0, 0.25, 0.75, 1.0])
    margin = choose_margin(p, 0.5, fraction=0.25)
    assert margin == 0.25
    # One requested eye becomes two because both are equally close.
    assert np.sum(np.abs(p-0.5) <= margin) == 2


def test_uncertain_cases_below_cutoff_are_referred():
    p, y = np.array([0.25, 0.5, 0.75, 0.0]), np.array([1, 1, 0, 0])
    base = decision_metrics(p,y,0.5)
    result = decision_metrics(p,y,0.5,0.25)
    assert base["fn"] == 1
    assert result["fn"] == 0
    assert result["uncertain_count"] == 3
    assert result["ordinary_referral_count"] == 0
    assert result["referral_count"] == 3
    assert result["no_concern_count"] == 1


@pytest.mark.parametrize("p,y", [([np.nan,0.5],[0,1]),([0.2,1.2],[0,1]),
                                  ([0.1,0.5],[0,0]),([0.5],[0,1])])
def test_invalid_selection_inputs_fail(p,y):
    with pytest.raises(ValueError):
        select_threshold(p,y)


def test_holdout_rejects_unfrozen_settings_before_loading_images(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"status":"pending_team_review","frozen":false}')
    with pytest.raises(ValueError, match="Review and freeze"):
        verify_settings(path)


def test_holdout_requires_review_reference(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"status":"frozen","frozen":true}')
    with pytest.raises(ValueError, match="review reference"):
        verify_settings(path)
