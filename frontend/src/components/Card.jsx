import "../styles/card.css";

function Card({ title, aside, children }) {
  return (
    <section className="card">
      {(title || aside) && (
        <header className="card__header">
          {title && <h2 className="card__title label-mono">{title}</h2>}
          {aside && <div className="card__aside mono-meta">{aside}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export default Card;
