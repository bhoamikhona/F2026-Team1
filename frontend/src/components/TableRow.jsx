import TableCell from "./TableCell";
import "../styles/table-row.css";

function TableRow({ row, columns, href }) {
  return (
    <div className="table-row" role="row">
      {columns.map((column) => (
        <div
          key={column.key}
          role="cell"
          className={
            column.align === "end"
              ? "table-row__cell table-row__cell--end body-md"
              : "table-row__cell body-md"
          }
        >
          <TableCell column={column} row={row} href={href} />
        </div>
      ))}
    </div>
  );
}

export default TableRow;
