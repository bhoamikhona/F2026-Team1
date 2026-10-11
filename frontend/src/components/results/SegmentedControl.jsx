import "../../styles/results/segmented-control.css";

function SegmentedControl({ label, name, options, value, onChange }) {
  return (
    <div className="segmented-control" role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <label key={option.value} className="segmented-control__option">
          <input
            className="segmented-control__input sr-only"
            type="radio"
            name={name}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          <span className="segmented-control__label body-md">
            {option.label}
          </span>
        </label>
      ))}
    </div>
  );
}

export default SegmentedControl;
