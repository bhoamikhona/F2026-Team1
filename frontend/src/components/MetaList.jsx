import "../styles/meta-list.css";

function getValueClass(item) {
  if (item.tag) return "meta-list__value--tag mono-meta";
  if (item.mono) return "meta-list__value--mono mono-meta";
  return "body-md";
}

function MetaList({ items }) {
  return (
    <dl className="meta-list">
      {items.map((item) => (
        <div key={item.label} className="meta-list__item">
          <dt className="label-mono">{item.label}</dt>
          <dd className={getValueClass(item)}>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export default MetaList;
