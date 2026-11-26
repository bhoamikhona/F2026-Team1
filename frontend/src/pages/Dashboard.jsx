import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronRight,
  CircleAlert,
  CircleCheck,
  CircleHelp,
  ImageIcon,
  ScanEye,
  UserPlus,
  Users,
} from "lucide-react";
import Card from "../components/Card.jsx";
import PageHeader from "../components/PageHeader.jsx";
import ResultChip from "../components/ResultChip.jsx";
import Table from "../components/Table.jsx";
import TextLink from "../components/TextLink.jsx";
import { useApi } from "../hooks/useApi.js";
import useAuth from "../hooks/useAuth.js";
import { apiGet, assetUrl } from "../services/api.js";
import "../styles/upload/fundus-preview.css";
import "../styles/patients/patients.css";
import "../styles/dashboard/dashboard.css";

const RECENT_SCREENINGS = 3;
const RECENT_PATIENTS = 3;
const TICKS = 20;

const RECENT_COLUMNS = [
  { key: "date", label: "Date", width: "minmax(0, 0.8fr)" },
  { key: "id", label: "Screening", width: "minmax(0, 1fr)", type: "link" },
  {
    key: "patient_name",
    label: "Patient",
    width: "minmax(0, 1.9fr)",
    type: "person",
    idKey: "patient_id",
  },
  {
    key: "eye",
    label: "Eye",
    width: "minmax(0, 0.6fr)",
    type: "chip",
    labels: { right: "OD", left: "OS" },
  },
  {
    key: "overall_result",
    label: "Overall",
    width: "minmax(0, 1.2fr)",
    type: "result",
  },
  {
    key: "open",
    label: "Open record",
    width: "2.4rem",
    type: "chevron",
    align: "end",
    hidden: true,
  },
];

const PATIENT_COLUMNS = [
  { key: "name", label: "Name", width: "minmax(0, 2.2fr)" },
  { key: "gender", label: "Gender", width: "minmax(0, 0.9fr)" },
  { key: "age", label: "Age", width: "minmax(0, 0.6fr)" },
  {
    key: "overall",
    label: "Overall",
    width: "minmax(0, 1.5fr)",
    type: "result",
  },
  {
    key: "open",
    label: "Open patient",
    width: "2.4rem",
    type: "chevron",
    align: "end",
    hidden: true,
  },
];

const STATS = [
  { result: "no_concern", label: "No concern", icon: CircleCheck },
  { result: "refer", label: "Refer", icon: CircleAlert },
  { result: "uncertain", label: "Uncertain", icon: CircleHelp },
];

const QUICK_LINKS = [
  { label: "New screening", to: "/upload", icon: ScanEye },
  { label: "New patient", to: "/patients/new", icon: UserPlus },
  { label: "View patients", to: "/patients", icon: Users },
];

const GENDER_LABELS = { male: "Male", female: "Female", other: "Other" };

const EYE_STATUS_TEXT = {
  skipped: "Skipped",
  not_screened: "Not screened",
};

const EYE_NAMES = { right: "Right eye", left: "Left eye" };

function formatDateTime(value) {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function getResult(screening) {
  if ([screening.cataract, screening.glaucoma].includes("uncertain")) {
    return "uncertain";
  }

  return screening.overall_result;
}

function getInitials(name) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function formatShortDate(value) {
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function getSubtitle(patient) {
  return [
    GENDER_LABELS[patient.sex],
    patient.age !== null && patient.age !== undefined
      ? `${patient.age} years old`
      : null,
  ]
    .filter(Boolean)
    .join(", ");
}

function getOverall(patient) {
  const statuses = [patient.right_status, patient.left_status];

  if (statuses.includes("uncertain")) return "uncertain";
  if (statuses.includes("refer")) return "refer";
  if (statuses.includes("no_concern")) return "no_concern";
  return null;
}

function toPatientRow(patient) {
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
    overall: getOverall(patient),
  };
}

function renderEyeStatus(status) {
  if (EYE_STATUS_TEXT[status]) {
    return (
      <span className="dashboard__eye-text caption-md">
        {EYE_STATUS_TEXT[status]}
      </span>
    );
  }

  return <ResultChip result={status} />;
}

function renderLatestPatient(patient, screening) {
  const findings = [
    {
      label: "Eye",
      value: (
        <span className="dashboard__eye-text caption-md">
          {EYE_NAMES[screening.eye]}
        </span>
      ),
    },
    {
      label: "Cataract",
      value: renderEyeStatus(screening.cataract ?? "skipped"),
    },
    {
      label: "Glaucoma",
      value: renderEyeStatus(screening.glaucoma ?? "skipped"),
    },
  ];

  return (
    <article className="dashboard__patient card">
      <div className="dashboard__patient-head">
        <span className="dashboard__avatar h3" aria-hidden="true">
          {getInitials(patient.full_name)}
        </span>

        <div className="dashboard__patient-who">
          <p className="h3">{patient.full_name}</p>
          <p className="body-rg dashboard__muted">{getSubtitle(patient)}</p>
          <p className="mono-meta dashboard__muted">
            {patient.id} · screened {formatDateTime(screening.created_at)}
          </p>
        </div>

        <Link
          to={`/patients/${patient.id}`}
          className="dashboard__patient-open"
          aria-label={`Open ${patient.full_name}`}
        >
          <ChevronRight size={18} aria-hidden="true" />
        </Link>
      </div>

      <dl className="dashboard__eyes">
        {findings.map((finding) => (
          <div key={finding.label} className="dashboard__eye">
            <dt className="label-mono dashboard__muted">{finding.label}</dt>
            <dd>{finding.value}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function Dashboard() {
  const { user } = useAuth();

  const patientsState = useApi(`/users/${user.id}/patients`);
  const screeningsState = useApi(`/users/${user.id}/screenings`);

  const isLoading = patientsState.isLoading || screeningsState.isLoading;
  const error = patientsState.error || screeningsState.error;

  const patients = patientsState.data ?? [];
  const screenings = screeningsState.data ?? [];
  const completed = screenings.filter((screening) => !screening.skipped);

  const latest = completed[0];
  const latestPatient = patients.find(
    (patient) => patient.id === latest?.patient_id,
  );

  const [latestImage, setLatestImage] = useState(null);

  useEffect(() => {
    if (!latest) return;

    let ignore = false;

    apiGet(`/screenings/${latest.id}`)
      .then((screening) => {
        if (!ignore) setLatestImage(screening.image?.url ?? null);
      })
      .catch(() => {
        if (!ignore) setLatestImage(null);
      });

    return () => {
      ignore = true;
    };
  }, [latest?.id]);

  const fundusSrc = assetUrl(latestImage);

  const recentPatients = patients
    .filter((patient) => patient.last_screening_at)
    .sort((a, b) => b.last_screening_at.localeCompare(a.last_screening_at))
    .slice(0, RECENT_PATIENTS);

  const stats = STATS.map((stat) => {
    const count = completed.filter(
      (screening) => getResult(screening) === stat.result,
    ).length;
    const share = completed.length ? count / completed.length : 0;

    return { ...stat, count, share, filled: Math.round(share * TICKS) };
  });

  function renderContent() {
    if (isLoading) {
      return <p className="dashboard__empty body-md">Loading dashboard…</p>;
    }

    if (error) {
      return (
        <p className="dashboard__empty body-md">
          Could not load your dashboard. {error.message}
        </p>
      );
    }

    return (
      <div className="dashboard__layout">
        <div className="dashboard__latest">
          <Card
            title="Latest screening"
            aside={
              latest && (
                <Link
                  to={`/results/${latest.id}/record`}
                  className="dashboard__aside-link"
                >
                  View full record
                  <ChevronRight size={14} aria-hidden="true" />
                </Link>
              )
            }
          >
            <div className="fundus-preview">
              {latest && fundusSrc ? (
                <img
                  className="fundus-preview__img"
                  src={fundusSrc}
                  alt={`Fundus photograph, ${latest.patient_name}, ${latest.eye} eye`}
                />
              ) : (
                <div className="fundus-preview__empty">
                  <ImageIcon
                    size={32}
                    className="fundus-preview__icon"
                    aria-hidden="true"
                  />
                  <p className="body-md">
                    {latest ? "Image unavailable" : "No screenings yet"}
                  </p>
                  <p className="caption-rg fundus-preview__hint">
                    {latest
                      ? "The fundus photo for this screening could not be loaded"
                      : "Your latest fundus photo will appear here"}
                  </p>
                </div>
              )}
            </div>
          </Card>

          {latestPatient && renderLatestPatient(latestPatient, latest)}
        </div>

        <div className="dashboard__stats">
          {stats.map((stat) => (
            <div
              key={stat.result}
              className={`dashboard__stat dashboard__stat--${stat.result} card`}
            >
              <div className="dashboard__stat-head">
                <span className="dashboard__stat-icon">
                  <stat.icon size={18} aria-hidden="true" />
                </span>
                <span className="label-mono dashboard__muted">
                  {stat.label}
                </span>
              </div>

              <div className="dashboard__stat-row">
                <span className="dashboard__stat-value mono-score">
                  {stat.count}
                </span>
                <span className="dashboard__stat-share mono-reference">
                  {Math.round(stat.share * 100)}%
                </span>
              </div>

              <div
                className="dashboard__ticks"
                role="img"
                aria-label={`${stat.count} of ${completed.length} screenings`}
              >
                {Array.from({ length: TICKS }, (_, i) => (
                  <span
                    key={i}
                    className={i < stat.filled ? "dashboard__tick--on" : ""}
                  ></span>
                ))}
              </div>
            </div>
          ))}
        </div>

        <section className="dashboard__recent">
          <div className="dashboard__section-head">
            <h2 className="h2">Recent screenings</h2>
            <TextLink to="/history" trailingIcon={ChevronRight}>
              View all screenings
            </TextLink>
          </div>

          {completed.length === 0 ? (
            <p className="dashboard__empty body-md">
              You haven't screened anyone yet.
            </p>
          ) : (
            <Table
              label="Recent screenings"
              columns={RECENT_COLUMNS}
              rows={completed.slice(0, RECENT_SCREENINGS).map((screening) => ({
                ...screening,
                date: formatShortDate(screening.created_at),
              }))}
              rowHref={(row) => `/results/${row.id}`}
            />
          )}
        </section>

        <section className="dashboard__patients">
          <div className="dashboard__section-head">
            <h2 className="h2">Recent patients</h2>
            <TextLink to="/patients" trailingIcon={ChevronRight}>
              View all patients
            </TextLink>
          </div>

          <Table
            label="Recent patients"
            columns={PATIENT_COLUMNS}
            rows={recentPatients.map(toPatientRow)}
            rowHref={(row) => `/patients/${row.id}`}
          />
        </section>

        <div className="dashboard__links">
          <Card title="Quick links">
            <ul className="dashboard__link-list">
              {QUICK_LINKS.map((link) => (
                <li key={link.to}>
                  <TextLink
                    to={link.to}
                    leadingIcon={link.icon}
                    trailingIcon={ChevronRight}
                    strong
                  >
                    {link.label}
                  </TextLink>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <main className="main dashboard">
      <PageHeader
        title="Dashboard"
        subtitle="An overview of your screening activity"
      />

      {renderContent()}
    </main>
  );
}

export default Dashboard;
