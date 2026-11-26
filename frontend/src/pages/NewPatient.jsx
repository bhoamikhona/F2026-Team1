import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ScanEye, UserPlus } from "lucide-react";
import Alert from "../components/Alert.jsx";
import Breadcrumbs from "../components/Breadcrumbs.jsx";
import Button from "../components/Button.jsx";
import Dropdown from "../components/Dropdown.jsx";
import Input from "../components/Input.jsx";
import PageHeader from "../components/PageHeader.jsx";
import RadioGroup from "../components/RadioGroup.jsx";
import { apiPost } from "../services/api.js";
import "../styles/new-patient/new-patient.css";

const BREADCRUMBS = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "My patients", to: "/patients" },
  { label: "New patient" },
];

const GENDER_OPTIONS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
];

const EYE_CONDITION_OPTIONS = [
  { value: "", label: "Not selected" },
  { value: "None", label: "None" },
  { value: "Cataract", label: "Diagnosed cataract" },
  { value: "Glaucoma", label: "Diagnosed glaucoma" },
  { value: "Cataract and glaucoma", label: "Cataract and glaucoma" },
];

const YES_NO_OPTIONS = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
  { value: "unknown", label: "Not sure" },
];

const EMPTY_FORM = {
  fullName: "",
  dateOfBirth: "",
  gender: "male",
  phone: "",
  email: "",
  eyeConditions: "",
  familyHistory: "unknown",
  diabetes: "unknown",
};

function getAge(dateOfBirth) {
  if (!dateOfBirth) return null;

  const today = new Date();
  const birth = new Date(`${dateOfBirth}T00:00:00`);
  const age = today.getFullYear() - birth.getFullYear();

  const hadBirthday =
    today.getMonth() > birth.getMonth() ||
    (today.getMonth() === birth.getMonth() &&
      today.getDate() >= birth.getDate());

  return hadBirthday ? age : age - 1;
}

function toBoolean(answer) {
  if (answer === "yes") return true;
  if (answer === "no") return false;
  return null;
}

function validate(form) {
  const errors = {};
  const age = getAge(form.dateOfBirth);

  if (!form.fullName.trim()) errors.fullName = "Enter the patient's full name";

  if (!form.dateOfBirth) errors.dateOfBirth = "Enter a date of birth";
  else if (age < 0 || age > 120)
    errors.dateOfBirth = "Enter a date of birth between 0 and 120 years ago";

  return errors;
}

function NewPatient() {
  const navigate = useNavigate();

  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const age = getAge(form.dateOfBirth);
  const today = new Date().toISOString().slice(0, 10);

  function updateField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  }

  async function handleSubmit(e) {
    e.preventDefault();

    const startScreening = e.nativeEvent.submitter?.name === "screen";
    const formErrors = validate(form);

    setErrors(formErrors);
    if (Object.keys(formErrors).length > 0) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const patient = await apiPost("/patients", {
        full_name: form.fullName.trim(),
        date_of_birth: form.dateOfBirth,
        sex: form.gender,
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
        known_eye_conditions: form.eyeConditions || null,
        family_history_glaucoma: toBoolean(form.familyHistory),
        diabetes: toBoolean(form.diabetes),
      });

      if (startScreening)
        navigate("/upload", { state: { patientId: patient.id } });
      else navigate(`/patients/${patient.id}`);
    } catch (error) {
      setSubmitError(error.message);
      setIsSubmitting(false);
    }
  }

  return (
    <main className="main new-patient">
      <div className="new-patient__top">
        <Breadcrumbs items={BREADCRUMBS} />
        <PageHeader
          title="Add new patient"
          subtitle="Create a patient record so you can start screening."
        />
      </div>

      {submitError && (
        <Alert title="Could not save the patient">{submitError}</Alert>
      )}

      <section className="card new-patient__card">
        <form className="new-patient__form" onSubmit={handleSubmit} noValidate>
          <div className="new-patient__section">
            <div className="new-patient__section-info">
              <h2 className="body-semibold">Identity</h2>
              <p className="new-patient__muted caption-rg">
                Name, date of birth and gender. All required.
              </p>
            </div>

            <div className="new-patient__fields">
              <Input
                label="Full name"
                placeholder="e.g. Maria Lopez"
                value={form.fullName}
                onChange={(e) => updateField("fullName", e.target.value)}
                error={errors.fullName}
              />

              <div className="new-patient__row">
                <Input
                  label="Date of birth"
                  type="date"
                  max={today}
                  value={form.dateOfBirth}
                  onChange={(e) => updateField("dateOfBirth", e.target.value)}
                  error={errors.dateOfBirth}
                  hint={
                    age !== null && age >= 0
                      ? `Age is worked out from this: ${age}`
                      : undefined
                  }
                />

                <div className="new-patient__field new-patient__field--beside-input">
                  <p className="input__label body-md" id="gender-label">
                    Gender
                  </p>
                  <RadioGroup
                    name="gender"
                    aria-labelledby="gender-label"
                    options={GENDER_OPTIONS}
                    value={form.gender}
                    onChange={(value) => updateField("gender", value)}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="new-patient__section">
            <div className="new-patient__section-info">
              <h2 className="body-semibold">Contact information</h2>
              <p className="new-patient__muted caption-rg">
                How to reach the patient. Optional.
              </p>
            </div>

            <div className="new-patient__fields">
              <div className="new-patient__row">
                <Input
                  label="Phone"
                  type="tel"
                  placeholder="(555) 000-0000"
                  value={form.phone}
                  onChange={(e) => updateField("phone", e.target.value)}
                />
                <Input
                  label="Email"
                  type="email"
                  placeholder="name@example.com"
                  value={form.email}
                  onChange={(e) => updateField("email", e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="new-patient__section">
            <div className="new-patient__section-info">
              <h2 className="body-semibold">Eye history</h2>
              <p className="new-patient__muted caption-rg">
                Known conditions and risk factors, shown on the patient page
                next to screening results. Optional.
              </p>
            </div>

            <div className="new-patient__fields">
              <div className="new-patient__field">
                <p className="input__label body-md">Known eye conditions</p>
                <Dropdown
                  variant="select"
                  label={
                    EYE_CONDITION_OPTIONS.find(
                      (option) => option.value === form.eyeConditions,
                    ).label
                  }
                  items={EYE_CONDITION_OPTIONS}
                  value={form.eyeConditions}
                  onChange={(value) => updateField("eyeConditions", value)}
                />
              </div>

              <div className="new-patient__row">
                <div className="new-patient__field">
                  <p className="input__label body-md" id="family-label">
                    Family history of glaucoma
                  </p>
                  <RadioGroup
                    name="family-history"
                    aria-labelledby="family-label"
                    options={YES_NO_OPTIONS}
                    value={form.familyHistory}
                    onChange={(value) => updateField("familyHistory", value)}
                  />
                </div>

                <div className="new-patient__field">
                  <p className="input__label body-md" id="diabetes-label">
                    Diabetes
                  </p>
                  <RadioGroup
                    name="diabetes"
                    aria-labelledby="diabetes-label"
                    options={YES_NO_OPTIONS}
                    value={form.diabetes}
                    onChange={(value) => updateField("diabetes", value)}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="new-patient__actions">
            <Button variant="secondary" to="/dashboard">
              Cancel
            </Button>
            <Button
              type="submit"
              name="save"
              variant="secondary"
              icon={UserPlus}
              disabled={isSubmitting}
            >
              Save patient
            </Button>
            <Button
              type="submit"
              name="screen"
              icon={ScanEye}
              disabled={isSubmitting}
            >
              Save and start screening
            </Button>
          </div>
        </form>
      </section>
    </main>
  );
}

export default NewPatient;
