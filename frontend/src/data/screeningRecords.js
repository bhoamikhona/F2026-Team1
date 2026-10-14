import eyePhoto from "../assets/images/eye.png";
import cataractHeatmap from "../assets/images/cataractHeatmap.png";
import glaucomaHeatmap from "../assets/images/glaucomaHeatmap.png";

const MODEL_VERSION = { id: "v0-mock", is_mock: true };

export const SCREENING_RECORDS = {
  "SCR-0006": {
    id: "SCR-0006",
    created_at: "2026-10-09T22:44:18-04:00",
    patient: { id: "P-004", full_name: "David Brown" },
    eye: "right",
    overall_result: "no_concern",
    image: { url: eyePhoto },
    conditions: [
      {
        condition: "cataract",
        calibrated_score: 0.145,
        threshold: 0.35,
        result: "no_concern",
        heatmap_url: cataractHeatmap,
      },
      {
        condition: "glaucoma",
        calibrated_score: 0.016,
        threshold: 0.5,
        result: "no_concern",
        heatmap_url: glaucomaHeatmap,
      },
    ],
    model_version: MODEL_VERSION,
  },

  "SCR-0007": {
    id: "SCR-0007",
    created_at: "2026-10-09T22:44:18-04:00",
    patient: { id: "P-003", full_name: "Aisha Patel" },
    eye: "left",
    overall_result: "refer",
    image: { url: eyePhoto },
    conditions: [
      {
        condition: "cataract",
        calibrated_score: 0.381,
        threshold: 0.35,
        result: "uncertain",
        heatmap_url: cataractHeatmap,
      },
      {
        condition: "glaucoma",
        calibrated_score: 0.321,
        threshold: 0.5,
        result: "no_concern",
        heatmap_url: glaucomaHeatmap,
      },
    ],
    model_version: MODEL_VERSION,
  },

  "SCR-0008": {
    id: "SCR-0008",
    created_at: "2026-10-09T22:44:18-04:00",
    patient: { id: "P-001", full_name: "Maria Lopez" },
    eye: "right",
    overall_result: "refer",
    image: { url: eyePhoto },
    conditions: [
      {
        condition: "cataract",
        calibrated_score: 0.417,
        threshold: 0.35,
        result: "refer",
        heatmap_url: cataractHeatmap,
      },
      {
        condition: "glaucoma",
        calibrated_score: 0.735,
        threshold: 0.5,
        result: "refer",
        heatmap_url: glaucomaHeatmap,
      },
    ],
    model_version: MODEL_VERSION,
  },
};
