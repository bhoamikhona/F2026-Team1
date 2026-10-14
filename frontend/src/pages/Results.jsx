import { useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import BackLink from "../components/BackLink.jsx";
import Banner from "../components/Banner.jsx";
import Button from "../components/Button.jsx";
import ConditionCard from "../components/ConditionCard.jsx";
import InfoNote from "../components/InfoNote.jsx";
import ResultChip from "../components/ResultChip.jsx";
import SummaryStrip from "../components/SummaryStrip.jsx";
import HeatmapPanel from "../components/results/HeatmapPanel.jsx";
import RiskSummary from "../components/results/RiskSummary.jsx";
import { SCREENING_RECORDS } from "../data/screeningRecords.js";
import "../styles/results/results.css";

const EYE_LABELS = { right: "Right eye, OD", left: "Left eye, OS" };
const CONDITION_LABELS = { cataract: "Cataract", glaucoma: "Glaucoma" };
const UNCERTAIN_MESSAGE =
  "Low image quality or the model is uncertain. Please refer for a full eye examination.";

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function Results() {
  const { id } = useParams();
  const screening = SCREENING_RECORDS[id];

  if (!screening) {
    return (
      <main className="main results">
        <div className="results__back">
          <BackLink to="/history">Back to History</BackLink>
        </div>
        <p className="body-md">Screening {id} was not found.</p>
      </main>
    );
  }

  const { patient, eye, image, conditions, model_version } = screening;

  return (
    <main className="main results">
      <div className="results__back">
        <Button variant="secondary" icon={ArrowLeft} to="/upload">
          New screening
        </Button>
        <BackLink to="/history" arrow={false}>
          or back to History
        </BackLink>
      </div>

      <Banner title="Triage, not diagnosis">
        This screening tool assists qualified practitioners in prioritizing
        clinical evaluations. It does not provide definitive diagnostic
        findings.
      </Banner>

      <SummaryStrip
        variant="panel"
        items={[
          { label: "Patient", value: `${patient.full_name}, ${patient.id}` },
          { label: "Eye", value: EYE_LABELS[eye] },
          { label: "Date", value: formatDate(screening.created_at) },
          { label: "Screening ID", value: screening.id, tag: true },
        ]}
        asideLabel="Overall result:"
      >
        <ResultChip result={screening.overall_result} />
      </SummaryStrip>

      <div className="results__layout">
        <HeatmapPanel photoUrl={image.url} conditions={conditions} />

        <div className="results__conditions">
          {conditions.map((item) => (
            <ConditionCard
              key={item.condition}
              condition={CONDITION_LABELS[item.condition]}
              result={item.result}
            >
              {item.result === "uncertain" ? (
                <InfoNote variant="tile">{UNCERTAIN_MESSAGE}</InfoNote>
              ) : (
                <RiskSummary
                  score={item.calibrated_score}
                  threshold={item.threshold}
                  result={item.result}
                  isExample={model_version.is_mock}
                />
              )}
            </ConditionCard>
          ))}
        </div>
      </div>
    </main>
  );
}

export default Results;
