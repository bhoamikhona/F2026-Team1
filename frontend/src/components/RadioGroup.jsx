import "../styles/radio-group.css";

function RadioGroup({ name, options, value, onChange, ...rest }) {
  return (
    <div className="radio-group" role="radiogroup" {...rest}>
      {options.map((option) => (
        <label key={option.value} className="radio-group__option body-md">
          <input
            className="radio-group__input sr-only"
            type="radio"
            name={name}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          <span className="radio-group__dot" aria-hidden></span>
          {option.label}
        </label>
      ))}
    </div>
  );
}

export default RadioGroup;
