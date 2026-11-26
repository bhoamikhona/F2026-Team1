import { useState } from "react";
import { Link } from "react-router-dom";
import { UserPlus } from "lucide-react";
import Breadcrumbs from "../components/Breadcrumbs.jsx";
import Button from "../components/Button.jsx";
import PageHeader from "../components/PageHeader.jsx";
import SearchBar from "../components/SearchBar.jsx";
import Table from "../components/Table.jsx";
import { PATIENT_COLUMNS } from "../data/patientColumns.js";
import { useApi } from "../hooks/useApi.js";
import useAuth from "../hooks/useAuth.js";
import "../styles/patients/patients.css";

const BREADCRUMBS = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "My patients" },
];

const GENDER_LABELS = { male: "Male", female: "Female", other: "Other" };

function getInitials(name) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function getOverall(patient) {
  const statuses = [patient.right_status, patient.left_status];

  if (statuses.includes("uncertain")) return "uncertain";
  if (statuses.includes("refer")) return "refer";
  if (statuses.includes("no_concern")) return "no_concern";
  return null;
}

function toRow(patient) {
  return {
    ...patient,
    name: (
      <span className="patients__person">
        <span className="patients__avatar caption-semibold" aria-hidden>
          {getInitials(patient.full_name)}
        </span>
        <span className="patients__who">
          <Link
            to={`/patients/${patient.id}`}
            className="table-cell__link patients__name body-semibold"
          >
            {patient.full_name}
          </Link>
          <span className="patients__id mono-meta">{patient.id}</span>
        </span>
      </span>
    ),
    gender: GENDER_LABELS[patient.sex] ?? patient.sex,
    phone: patient.phone ?? "—",
    email: patient.email ?? "—",
    overall: getOverall(patient),
  };
}

function Patients() {
  const { user } = useAuth();

  const [query, setQuery] = useState("");

  const basePath = `/users/${user.id}/patients`;
  const path = query
    ? `${basePath}?query=${encodeURIComponent(query)}`
    : basePath;

  const { data: patients, error, isLoading } = useApi(path);

  const allPatients = patients ?? [];

  const rows = [...allPatients]
    .sort((a, b) => a.full_name.localeCompare(b.full_name))
    .map(toRow);

  function renderContent() {
    if (isLoading) {
      return <p className="patients__empty body-md">Loading patients…</p>;
    }

    if (error) {
      return (
        <p className="patients__empty body-md">
          Could not load patients. {error.message}
        </p>
      );
    }

    if (allPatients.length === 0) {
      return (
        <p className="patients__empty body-md">
          {query
            ? "No patients match your search."
            : "You haven't added or screened any patients yet."}
        </p>
      );
    }

    return (
      <>
        <Table label="My patients" columns={PATIENT_COLUMNS} rows={rows} />
        <p className="patients__count mono-meta">
          Showing {rows.length} {rows.length === 1 ? "patient" : "patients"}
        </p>
      </>
    );
  }

  return (
    <main className="main patients">
      <Breadcrumbs items={BREADCRUMBS} />

      <PageHeader
        title="My patients"
        subtitle="Everyone you have added or screened"
      />

      <div className="patients__toolbar">
        <div className="patients__search">
          <SearchBar
            id="patients-search"
            label="Search patients"
            placeholder="Search by patient name or patient ID"
            onSearch={setQuery}
          />
        </div>

        <Button to="/patients/new" icon={UserPlus}>
          Add new patient
        </Button>
      </div>

      {renderContent()}
    </main>
  );
}

export default Patients;
