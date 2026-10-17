"""Checks for accidentally reusing scores from a replaced checkpoint."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import calibrate_models as calibration


@pytest.fixture
def saved_scores(tmp_path, monkeypatch):
    monkeypatch.setattr(calibration, "PROJECT_ROOT", tmp_path)
    labels = tmp_path / "labels.csv"
    labels.write_text("validation labels")
    monkeypatch.setattr(calibration, "LABELS_FILE", labels)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("cataract_model.py", "resnet_backbone.py", "fundus_dataset.py", "preprocess_images.py"):
        (scripts / name).write_text("source")
    checkpoint = tmp_path / "checkpoints/task11/cataract/cataract_seed_42_best.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"original checkpoint")
    prediction = tmp_path / "results/calibration/cataract_seed_42_validation.csv"
    prediction.parent.mkdir(parents=True)
    prediction.write_text("filename,logit,cataract\na.jpg,0.5,1\n")
    calibration.save_prediction_metadata("cataract", 42)
    return checkpoint, prediction, labels


def test_original_scores_are_accepted(saved_scores):
    assert calibration.verify_prediction_metadata("cataract", 42)["seed"] == 42


@pytest.mark.parametrize("changed", [0, 1, 2])
def test_replaced_checkpoint_scores_or_labels_are_rejected(saved_scores, changed):
    saved_scores[changed].write_bytes(b"changed")
    with pytest.raises(ValueError):
        calibration.verify_prediction_metadata("cataract", 42)


def test_saved_comparisons_can_run_without_local_checkpoint(saved_scores):
    saved_scores[0].unlink()
    calibration.verify_prediction_metadata("cataract", 42)


def test_missing_provenance_is_rejected(saved_scores):
    saved_scores[1].with_suffix(".meta.json").unlink()
    with pytest.raises(ValueError, match="Missing prediction provenance"):
        calibration.verify_prediction_metadata("cataract", 42)


def test_empty_thresholds_do_not_erase_existing_results(tmp_path, monkeypatch):
    import json
    import compare_glaucoma_thresholds as thresholds

    output = tmp_path / "results/calibration"
    output.mkdir(parents=True)
    (output / "glaucoma_calibration_trial.json").write_text(json.dumps({
        "frozen": False, "fit_split": "validation", "runs": [],
    }))
    destination = output / "glaucoma_threshold_candidates_trial.csv"
    destination.write_text("existing results")
    monkeypatch.setattr(thresholds, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(thresholds, "SEEDS", ())
    monkeypatch.setattr(thresholds, "load_validation_labels", lambda: [{"glaucoma": 1}])
    monkeypatch.setattr(sys, "argv", ["compare_glaucoma_thresholds.py"])
    with pytest.raises(RuntimeError, match="No threshold candidates"):
        thresholds.main()
    assert destination.read_text() == "existing results"
