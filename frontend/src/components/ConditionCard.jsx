import Card from "./Card.jsx";
import ResultChip from "./ResultChip.jsx";
import "../styles/condition-card.css";

function ConditionCard({
  condition,
  eyebrow = "Condition screener",
  result,
  children,
}) {
  return (
    <Card>
      <header className="condition-card__header">
        <div>
          <p className="label-mono condition-card__eyebrow">{eyebrow}</p>
          {condition && <h2 className="h2">{condition}</h2>}
        </div>

        <ResultChip result={result} />
      </header>

      {children}
    </Card>
  );
}

export default ConditionCard;
