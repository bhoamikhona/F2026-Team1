import { useState } from "react";
import PageHeader from "../components/PageHeader";
import Select from "../components/Select";
import Table from "../components/Table";
import { SCREENING_COLUMNS } from "../data/screeningColumns.js";
import { useApi } from "../hooks/useApi.js";
import "../styles/history/history.css";

function History() {
  const [patientId, setPatientId] = useState("");

  const { data: patients } = useApi("/patients");
  const {
    data: screenings,
    error,
    isLoading,
  } = useApi(
    patientId
      ? `/screenings?patient=${encodeURIComponent(patientId)}`
      : "/screenings",
  );

  const patientOptions = [
    { value: "", label: "All patients" },
    ...(patients ?? []).map((patient) => ({
      value: patient.id,
      label: patient.full_name,
    })),
  ];

  function renderContent() {
    if (isLoading) {
      return <p className="history__empty body-md">Loading screenings…</p>;
    }

    if (error) {
      return (
        <p className="history__empty body-md">
          Could not load screenings. {error.message}
        </p>
      );
    }

    if (screenings.length === 0) {
      return (
        <p className="history__empty body-md">
          No screenings for this patient yet.
        </p>
      );
    }

    return (
      <>
        <Table
          label="Past screenings"
          columns={SCREENING_COLUMNS}
          rows={screenings}
          rowHref={(row) => `/results/${row.id}`}
        />
        <p className="history__count mono-meta">
          Showing {screenings.length}{" "}
          {screenings.length === 1 ? "screening" : "screenings"}
        </p>
      </>
    );
  }

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
              options={patientOptions}
            />
          </div>
        }
      />

      {renderContent()}
    </main>
  );
}

export default History;
