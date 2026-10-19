import "../styles/risk-ring.css";

const TONES = {
  no_concern: "success",
  refer: "danger",
  uncertain: "warning",
};

function RiskRing({ value, result }) {
  const percent = Math.round(Math.min(Math.max(value, 0), 1) * 100);

  return (
    <div
      className={`risk-ring risk-ring--${TONES[result]}`}
      role="img"
      aria-label={`Calibrated risk ${percent} percent`}
    >
      <svg className="risk-ring__svg" viewBox="0 0 36 36" aria-hidden="true">
        <circle className="risk-ring__track" cx="18" cy="18" r="16.4" />
        {percent > 0 && (
          <circle
            className="risk-ring__arc"
            cx="18"
            cy="18"
            r="16.4"
            pathLength="100"
            strokeDasharray={`${percent} 100`}
          />
        )}
      </svg>
      <span className="risk-ring__value label-mono" aria-hidden="true">
        {percent}%
      </span>
    </div>
  );
}

export default RiskRing;
