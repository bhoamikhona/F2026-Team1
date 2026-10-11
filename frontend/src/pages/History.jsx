import { useState } from "react";
import PageHeader from "../components/PageHeader";
import Select from "../components/Select";
import Table from "../components/Table";
import { SCREENING_COLUMNS } from "../data/screeningColumns.js";
import { SCREENINGS } from "../data/screenings.js";
import { PATIENTS } from "../data/patients.js";
import "../styles/history/history.css";

const PATIENT_OPTIONS = [
  { value: "", label: "All patients" },
  ...PATIENTS.map((patient) => ({
    value: patient.id,
    label: patient.full_name,
  })),
];

function History() {
  const [patientId, setPatientId] = useState("");

  const screenings = patientId
    ? SCREENINGS.filter((screening) => screening.patient_id === patientId)
    : SCREENINGS;

  return (
    <main className="main">
      <PageHeader
        title="History"
        subtitle="Past screenings for your patients, most recent first"
        actions={
          <div className="history__filter">
            <label
              htmlFor="patient-filter"
              className="history__filter-label label-mono"
            >
              Filter:
            </label>
            <Select
              id="patient-filter"
              value={patientId}
              onChange={(event) => setPatientId(event.target.value)}
              options={PATIENT_OPTIONS}
            />
          </div>
        }
      />

      {screenings.length === 0 ? (
        <p className="history__empty body-md">
          No screenings for this patient yet.
        </p>
      ) : (
        <Table
          label="Past screenings"
          columns={SCREENING_COLUMNS}
          rows={screenings}
          rowHref={(row) => `/history/${row.id}`}
        />
      )}

      <p className="history__count mono-meta">
        Showing {screenings.length}{" "}
        {screenings.length === 1 ? "screening" : "screenings"}
      </p>
    </main>
  );
}

export default History;
