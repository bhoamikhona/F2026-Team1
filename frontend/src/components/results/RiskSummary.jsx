import RiskRing from "../RiskRing";
import "../../styles/results/risk-summary.css";

function RiskSummary({ score, threshold, result, isExample = false }) {
  const percent = Math.round(score * 100);
  const thresholdLabel = `${isExample ? "example threshold" : "threshold"} ${threshold.toFixed(2)}`;
  const comparison =
    result === "refer"
      ? "At or above the referral threshold"
      : "Below the referral threshold";

  return (
    <div className="risk-summary">
      <RiskRing value={score} result={result} />
      <div>
        <p className="body-semibold">
          Risk score {score.toFixed(2)} ({percent}%)
        </p>
        <p
          className={`risk-summary__note risk-summary__note--${result} caption-rg`}
        >
          {comparison} ({thresholdLabel})
        </p>
      </div>
    </div>
  );
}

export default RiskSummary;
