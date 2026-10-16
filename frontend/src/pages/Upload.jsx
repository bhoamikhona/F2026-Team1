import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Alert from "../components/Alert.jsx";
import FundusPreview from "../components/upload/FundusPreview.jsx";
import InfoNote from "../components/InfoNote.jsx";
import PageHeader from "../components/PageHeader.jsx";
import ScreeningForm from "../components/upload/ScreeningForm.jsx";
import { apiDelete, apiGet, apiPost, apiUpload } from "../services/api.js";
import "../styles/upload.css";

const EYE_TO_API = { OD: "right", OS: "left" };

function Upload() {
  const navigate = useNavigate();

  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState("");
  const [eye, setEye] = useState("OD");
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [imageId, setImageId] = useState(null);
  const [qualityReason, setQualityReason] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  useEffect(() => {
    let ignore = false;

    apiGet("/patients")
      .then((data) => {
        if (ignore) return;

        setPatients(
          data.map((p) => ({ id: p.id, name: p.full_name, age: p.age })),
        );
        setPatientId((current) => current || data[0]?.id || "");
      })
      .catch((error) => {
        if (!ignore) setSubmitError(error.message);
      });

    return () => {
      ignore = true;
    };
  }, []);

  const canSubmit = Boolean(
    patientId && file && !qualityReason && !isSubmitting,
  );

  function discardImage() {
    if (imageId) apiDelete(`/images/${imageId}`).catch(() => {});
    setImageId(null);
  }

  function handleFileChange(newFile) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);

    discardImage();
    setFile(newFile);
    setPreviewUrl(newFile ? URL.createObjectURL(newFile) : null);
    setQualityReason(null);
    setSubmitError(null);
  }

  function handleReset() {
    handleFileChange(null);
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("patient_id", patientId);
      formData.append("eye", EYE_TO_API[eye]);

      const image = await apiUpload("/images", formData);
      setImageId(image.id);

      if (image.quality_status === "failed") {
        setQualityReason(image.quality_reason);
        return;
      }

      const screening = await apiPost("/screenings", {
        patient_id: patientId,
        eye: EYE_TO_API[eye],
        image_id: image.id,
      });

      navigate(`/results/${screening.id}`);
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="main">
      <PageHeader eyebrow="Clinical triage intake" title="New screening" />

      {submitError && (
        <Alert title="Could not screen this photo">{submitError}</Alert>
      )}

      <div className="upload__grid">
        <div className="upload__left">
          <FundusPreview src={previewUrl} />
          <InfoNote>
            DUAL flags eyes that may need a specialist review for cataract or
            glaucoma. It does not diagnose. Every Refer or Uncertain result
            needs a full eye examination.
          </InfoNote>
        </div>

        <ScreeningForm
          patients={patients}
          patientId={patientId}
          onPatientChange={setPatientId}
          eye={eye}
          onEyeChange={setEye}
          file={file}
          onFileChange={handleFileChange}
          qualityReason={qualityReason}
          onReset={handleReset}
          canSubmit={canSubmit}
          onSubmit={handleSubmit}
        />
      </div>
    </main>
  );
}

export default Upload;
