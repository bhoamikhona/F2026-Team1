import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Check, ChevronDown } from "lucide-react";
import "../styles/dropdown.css";

function getInitials(name) {
  return name
    .replace("Dr. ", "")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2);
}

function DropdownItem({ item, selected, onSelect }) {
  if (item.type === "divider") {
    return <li className="dropdown__divider" role="separator" />;
  }

  if (item.type === "label") {
    return <li className="dropdown__label label-mono">{item.label}</li>;
  }

  const Icon = item.icon;
  const isOption = selected !== undefined;

  const className = [
    "dropdown__item",
    item.tone === "danger" && "dropdown__item--danger",
    selected && "dropdown__item--selected",
  ]
    .filter(Boolean)
    .join(" ");

  const content = (
    <>
      {Icon && <Icon size={16} className="dropdown__icon" aria-hidden />}
      <span className="dropdown__text">
        <span className="body-md">{item.label}</span>
        {item.description && (
          <span className="dropdown__description caption-rg">
            {item.description}
          </span>
        )}
      </span>
      {item.meta && (
        <span className="dropdown__meta mono-meta">{item.meta}</span>
      )}
      {isOption && (
        <span className="dropdown__check" aria-hidden>
          {selected && <Check size={16} />}
        </span>
      )}
    </>
  );

  return (
    <li role="none">
      {item.to ? (
        <Link
          to={item.to}
          role="menuitem"
          className={className}
          onClick={() => onSelect(item)}
        >
          {content}
        </Link>
      ) : (
        <button
          type="button"
          role={isOption ? "option" : "menuitem"}
          aria-selected={isOption ? selected : undefined}
          className={className}
          disabled={item.disabled}
          onClick={() => onSelect(item)}
        >
          {content}
        </button>
      )}
    </li>
  );
}

function Dropdown({
  variant = "button",
  label,
  icon: Icon,
  header,
  items,
  value,
  onChange,
  align = "start",
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const isSelect = value !== undefined;

  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(e) {
      if (!dropdownRef.current.contains(e.target)) setIsOpen(false);
    }

    function handleEscape(e) {
      if (e.key === "Escape") setIsOpen(false);
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen]);

  function handleSelect(item) {
    setIsOpen(false);
    item.onClick?.();
    if (isSelect) onChange?.(item.value);
  }

  const triggerClass = `dropdown__trigger dropdown__trigger--${variant}`;

  return (
    <div
      ref={dropdownRef}
      className={`dropdown dropdown--${align}${isOpen ? " dropdown--open" : ""}`}
    >
      <button
        type="button"
        className={triggerClass}
        aria-haspopup={isSelect ? "listbox" : "menu"}
        aria-expanded={isOpen}
        aria-label={variant === "icon" ? label : undefined}
        onClick={() => setIsOpen((open) => !open)}
      >
        {variant === "user" && (
          <span className="dropdown__avatar caption-semibold" aria-hidden>
            {getInitials(label)}
          </span>
        )}
        {Icon && <Icon size={variant === "icon" ? 20 : 16} aria-hidden />}
        {variant !== "icon" && (
          <span className={variant === "user" ? "caption-md" : "body-md"}>
            {label}
          </span>
        )}
        {variant !== "icon" && (
          <ChevronDown size={16} className="dropdown__chevron" aria-hidden />
        )}
      </button>

      {isOpen && (
        <div className="dropdown__menu">
          {header && (
            <div className="dropdown__header">
              <p className="body-semibold">{header.title}</p>
              {header.subtitle && (
                <p className="dropdown__description caption-rg">
                  {header.subtitle}
                </p>
              )}
            </div>
          )}
          <ul className="dropdown__list" role={isSelect ? "listbox" : "menu"}>
            {items.map((item, index) => (
              <DropdownItem
                key={item.value ?? item.label ?? `${item.type}-${index}`}
                item={item}
                selected={
                  isSelect && item.value !== undefined
                    ? item.value === value
                    : undefined
                }
                onSelect={handleSelect}
              />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default Dropdown;
