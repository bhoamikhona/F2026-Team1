
"""Request and response shapes. FastAPI lists them on the /docs page."""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


Eye = Literal["right", "left"]
Result = Literal["no_concern", "refer", "uncertain"]


class LoginIn(BaseModel):
    email: str
    password: str


class User(BaseModel):
    id: int
    name: str
    role: str
    email: str


class LoginOut(BaseModel):
    user: User
    token: str = Field(
        description="Also set as a cookie; only needed by scripts that cannot keep cookies"
    )


def age_from_birth_date(birth_date: date) -> int:
    today = date.today()

    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


class PatientFields(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=120)
    date_of_birth: Optional[date] = None
    sex: Literal["female", "male", "other"]
    phone: Optional[str] = None
    email: Optional[str] = None
    known_eye_conditions: Optional[str] = Field(None, max_length=200)
    family_history_glaucoma: Optional[bool] = None
    diabetes: Optional[bool] = None


class PatientIn(PatientFields):
    @model_validator(mode="after")
    def validate_identity(self):
        self.full_name = self.full_name.strip()

        if not self.full_name:
            raise ValueError("Full name is required")

        if self.date_of_birth is not None:
            calculated = age_from_birth_date(self.date_of_birth)

            if self.date_of_birth > date.today() or calculated > 120:
                raise ValueError(
                    "Date of birth must give an age between 0 and 120"
                )

            self.age = calculated

        if self.age is None:
            raise ValueError("Date of birth or age is required")

        return self


class Patient(PatientFields):
    age: int = Field(ge=0)
    id: str = Field(examples=["P-001"])
    created_at: str
    created_by: Optional[int] = Field(
        None,
        description="ID of the clinician who added the patient"
    )


EyeStatus = Literal[
    "not_screened",
    "skipped",
    "no_concern",
    "refer",
    "uncertain"
]


class PatientSummary(Patient):
    last_screening_at: Optional[str] = Field(
        description="None when the patient has never been screened"
    )
    screening_count: int
    latest_right: Optional[Literal["no_concern", "refer"]] = Field(
        description="Latest overall result for the right eye; None if not screened or skipped"
    )
    latest_left: Optional[Literal["no_concern", "refer"]] = Field(
        description="Latest overall result for the left eye; None if not screened or skipped"
    )

    right_status: EyeStatus
    left_status: EyeStatus


class NextId(BaseModel):
    id: str = Field(examples=["P-005"])


class Image(BaseModel):
    id: str = Field(examples=["IMG-0001"])
    patient_id: str
    eye: Eye
    file_name: str = Field(examples=["P-001_right.jpg"])
    width: Optional[int]
    height: Optional[int]
    quality_status: Literal["passed", "failed"]
    quality_reason: Optional[
        Literal["unreadable", "too_dark", "not_fundus"]
    ]
    quality_message: Optional[str] = Field(
        description="Alert title for a failed check"
    )
    uploaded_at: str
    url: Optional[str] = Field(
        description="512 x 512 preprocessed photo (Results thumbnail)"
    )
    original_url: Optional[str]


class ConditionResult(BaseModel):
    condition: Literal["cataract", "glaucoma"]
    raw_score: float
    calibrated_score: float = Field(
        description="Risk score 0 to 1; Results hides it when uncertain"
    )
    threshold: float
    result: Result
    flag_reason: str
    heatmap_id: Optional[str]
    heatmap_url: Optional[str]


class ModelVersion(BaseModel):
    id: str = Field(examples=["v0-mock"])
    thresholds: dict[str, float]
    uncertain_margin: float
    commit: Optional[str] = Field(
        description="Set by Task 19; never show a made-up hash"
    )
    is_mock: bool
    released_at: str


class Screening(BaseModel):
    id: str = Field(examples=["SCR-0001"])
    created_at: str
    created_by: str
    patient: Patient
    eye: Eye
    skipped: bool
    skip_reason: Optional[str]
    overall_result: Optional[
        Literal["no_concern", "refer"]
    ] = Field(
        description="None when the eye was skipped"
    )
    image: Optional[Image]
    conditions: list[ConditionResult]
    model_version: Optional[ModelVersion]


class ScreeningIn(BaseModel):
    patient_id: str
    eye: Eye
    image_id: Optional[str] = Field(
        None,
        description="Required unless skipped"
    )
    skipped: bool = False
    skip_reason: Optional[str] = Field(
        None,
        description="Required when skipped"
    )


class ScreeningSummary(BaseModel):
    id: str
    created_at: str
    patient_id: str
    patient_name: str
    eye: Eye
    skipped: bool
    skip_reason: Optional[str]
    overall_result: Optional[Literal["no_concern", "refer"]]
    cataract: Optional[Result]
    glaucoma: Optional[Result]
    created_by: Optional[str] = Field(
        None,
        description="Name of the clinician who ran the screening"
    )


class LatestPerEye(BaseModel):
    right: Optional[Screening]
    left: Optional[Screening]


class PatientDetail(BaseModel):
    patient: Patient
    last_encounter: Optional[str]
    latest: LatestPerEye


class TodayCounts(BaseModel):
    screened: int = Field(
        description="Completed screenings today, skipped eyes not included"
    )
    referred: int = Field(
        description="Overall Refer today, including eyes referred because a condition was Uncertain"
    )
    uncertain: int = Field(
        description="Screenings today with at least one Uncertain condition"
    )
    skipped: int


class FollowUpPatient(BaseModel):
    patient_id: str
    patient_name: str
    right: Optional[Literal["no_concern", "refer"]]
    left: Optional[Literal["no_concern", "refer"]]
    uncertain: bool = Field(
        description="True when a latest result has an Uncertain condition"
    )
    latest_screening_id: str
    latest_screening_at: str


class RescreenEye(BaseModel):
    screening_id: str
    patient_id: str
    patient_name: str
    eye: Eye
    skip_reason: Optional[str]
    skipped_at: str


class WeekCounts(BaseModel):
    refer: int = Field(
        description="Refer with no Uncertain condition"
    )
    uncertain: int = Field(
        description="At least one Uncertain condition"
    )
    no_concern: int
    completed: int


class DashboardSummary(BaseModel):
    today: TodayCounts
    follow_up: list[FollowUpPatient]
    rescreen: list[RescreenEye]
    week: WeekCounts
