import TableCell from "./TableCell";
import "../styles/table-row.css";

function getCellClass(column) {
  let className = "table-row__cell body-md";
  if (column.align === "end") className += " table-row__cell--end";
  if (column.hidden) className += " table-row__cell--unlabeled";
  return className;
}

function TableRow({ row, columns, href }) {
  return (
    <div className="table-row" role="row">
      {columns.map((column) => (
        <div key={column.key} role="cell" className={getCellClass(column)}>
          <span className="table-row__label label-mono" aria-hidden="true">
            {column.label}
          </span>
          <span className="table-row__value">
            <TableCell column={column} row={row} href={href} />
          </span>
        </div>
      ))}
    </div>
  );
}

export default TableRow;
