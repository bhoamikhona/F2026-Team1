import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import Chip from "./Chip";
import ResultChip from "./ResultChip";
import "../styles/table-cell.css";

const DATE_FORMAT = { month: "short", day: "numeric", year: "numeric" };

function TableCell({ column, row, href }) {
  const value = row[column.key];

  switch (column.type) {
    case "date":
      return new Date(value).toLocaleDateString("en-US", DATE_FORMAT);
    case "link":
      return href ? (
        <Link to={href} className="table-cell__link mono-reference">
          {value}
        </Link>
      ) : (
        value
      );
    case "person":
      return (
        <>
          <span className="table-cell__id mono-meta">{row[column.idKey]}</span>{" "}
          <span className="table-cell__name body-semibold">{value}</span>
        </>
      );
    case "result":
      return value ? (
        <ResultChip result={value} />
      ) : (
        <span className="table-cell__empty">—</span>
      );
    case "chip":
      return <Chip mono>{column.labels?.[value] ?? value}</Chip>;
    case "chevron":
      return <ChevronRight size={16} aria-hidden="true" />;
    default:
      return value;
  }
}

export default TableCell;
