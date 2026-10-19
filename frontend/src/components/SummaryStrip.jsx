import MetaList from "./MetaList.jsx";
import "../styles/summary-strip.css";

function SummaryStrip({ items, asideLabel, children }) {
  return (
    <div className="summary-strip">
      <MetaList items={items} />

      {children && (
        <div className="summary-strip__aside">
          {asideLabel && (
            <span className="summary-strip__aside-label label-mono">
              {asideLabel}
            </span>
          )}
          {children}
        </div>
      )}
    </div>
  );
}

export default SummaryStrip;
