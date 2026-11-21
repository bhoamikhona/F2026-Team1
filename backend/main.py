"""Dual Eye Q FastAPI backend."""

import os

from contextlib import asynccontextmanager
from typing import Annotated, Literal, Optional

import psycopg

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware

from . import db, reports, service
from .auth import (
    COOKIE,
    SESSION_HOURS,
    PostgresCurrentUser,
    new_postgres_session,
    session_token,
    verify_password,
)
from .schemas import (
    DashboardSummary,
    Eye,
    Image,
    LoginIn,
    LoginOut,
    ModelVersion,
    Patient,
    PatientDetail,
    PatientIn,
    PatientSummary,
    Screening,
    ScreeningIn,
    ScreeningSummary,
    User,
)


MAX_UPLOAD_MB = 20

ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DUAL_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

PgDb = Annotated[
    psycopg.Connection,
    Depends(db.get_postgres_db),
]


# ---------- Cookie Configuration ----------

def cross_site_cookies():
    """Determine whether cross-site session cookies are enabled."""

    return os.environ.get(
        "DUAL_CROSS_SITE_COOKIES"
    ) == "1"


def set_session_cookie(response: Response, token: str):
    """Set the authenticated browser session cookie."""

    cross_site = cross_site_cookies()

    response.set_cookie(
        key=COOKIE,
        value=token,
        httponly=True,
        secure=cross_site,
        samesite="none" if cross_site else "lax",
        max_age=SESSION_HOURS * 3600,
        path="/",
    )


def clear_session_cookie(response: Response):
    """Clear the same cookie created during login."""

    cross_site = cross_site_cookies()

    response.delete_cookie(
        key=COOKIE,
        httponly=True,
        secure=cross_site,
        samesite="none" if cross_site else "lax",
        path="/",
    )


# ---------- Application Startup ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize model-version metadata at startup."""

    with db.connect_postgres() as conn:
        service.ensure_model_version(conn)
        conn.commit()

    yield


app = FastAPI(
    title="DUAL API",
    version="0.1.0",
    lifespan=lifespan,
    description=(
        "Backend for the DUAL ocular disease screening tool. "
        "DUAL supports screening triage, not diagnosis. "
        "Current inference scores come from a MOCK model."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix=service.API_PREFIX)


# ---------- Session ----------

@api.post(
    "/session",
    response_model=LoginOut,
    status_code=201,
    tags=["session"],
)
def create_session(
    body: LoginIn,
    response: Response,
    conn: PgDb,
):
    """Authenticate a clinician and create a PostgreSQL session."""

    row = conn.execute(
        """
        SELECT *
        FROM users
        WHERE email = %s
        """,
        (body.email.strip().lower(),),
    ).fetchone()

    if row is None or not verify_password(
        body.password,
        row["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Wrong email or password",
        )

    token = new_postgres_session(
        conn,
        row["id"],
    )

    conn.commit()

    set_session_cookie(response, token)

    return {
        "user": {
            key: row[key]
            for key in (
                "id",
                "name",
                "role",
                "email",
            )
        },
        "token": token,
    }


@api.delete(
    "/session",
    status_code=204,
    tags=["session"],
)
def delete_session(
    response: Response,
    request: Request,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Revoke the current session and clear its cookie."""

    token = session_token(request)

    if token:
        conn.execute(
            """
            DELETE FROM sessions
            WHERE token = %s
            """,
            (token,),
        )

        conn.commit()

    clear_session_cookie(response)


@api.get(
    "/session",
    response_model=User,
    tags=["session"],
)
def current_session(user: PostgresCurrentUser):
    """Return the currently authenticated clinician."""

    return user


# ---------- Patients ----------

@api.get(
    "/patients",
    response_model=list[PatientSummary],
    tags=["patients"],
)
def patients(
    conn: PgDb,
    user: PostgresCurrentUser,
    search: Optional[str] = None,
):
    """Retrieve patients with optional search filtering."""

    return service.list_patients(
        conn,
        search,
    )


@api.post(
    "/patients",
    response_model=Patient,
    status_code=201,
    tags=["patients"],
)
def add_patient(
    body: PatientIn,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Create a patient."""

    patient = service.create_patient(
        conn,
        body.model_dump(),
        created_by=user["id"],
    )

    conn.commit()

    return patient


@api.get(
    "/patients/{patient_id}",
    response_model=PatientDetail,
    tags=["patients"],
)
def patient(
    patient_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Retrieve a patient and their latest screenings."""

    return service.patient_detail(
        conn,
        patient_id,
    )


@api.get(
    "/patients/{patient_id}/screenings",
    response_model=list[ScreeningSummary],
    tags=["patients"],
)
def patient_screenings(
    patient_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
    date: Optional[str] = None,
):
    """Retrieve screening history for a patient."""

    service.get_patient(conn, patient_id)

    return service.list_screenings(
        conn,
        patient_id=patient_id,
        date=date,
    )


@api.get(
    "/patients/{patient_id}/report",
    tags=["patients"],
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/pdf": {}
            }
        }
    },
)
def patient_report(
    patient_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Export a patient dossier as PDF."""

    detail = service.patient_detail(
        conn,
        patient_id,
    )

    screenings = service.list_screenings(
        conn,
        patient_id=patient_id,
    )

    pdf = reports.patient_pdf(
        detail,
        screenings,
    )

    return _pdf_response(
        pdf,
        f"{patient_id}_dossier.pdf",
    )


# ---------- Images ----------

@api.post(
    "/images",
    response_model=Image,
    status_code=201,
    tags=["images"],
)
async def upload_image(
    conn: PgDb,
    user: PostgresCurrentUser,
    file: Annotated[UploadFile, File()],
    patient_id: Annotated[str, Form()],
    eye: Annotated[Eye, Form()],
):
    """Upload a fundus image and save its metadata.

    Storage uploads are cleaned up if the PostgreSQL
    transaction fails before it can be committed.
    """

    maximum_bytes = MAX_UPLOAD_MB * 1024 * 1024

    data = await file.read(
        maximum_bytes + 1
    )

    if len(data) > maximum_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Photo is larger than "
                f"{MAX_UPLOAD_MB} MB"
            ),
        )

    image = service.save_image(
        conn,
        patient_id,
        eye,
        data,
    )

    try:
        conn.commit()

    except Exception:
        conn.rollback()

        # Only readable images produce Storage objects.
        # Unreadable images store metadata without files.
        if image["url"] is not None:
            image_id = image["id"]

            service.cleanup_storage_objects([
                (
                    "fundus-images",
                    f"{image_id}.jpg",
                ),
                (
                    "processed-images",
                    f"{image_id}_512.jpg",
                ),
            ])

        raise

    return image


@api.get(
    "/images/{image_id}/processed",
    tags=["images"],
    response_class=Response,
)
def image_512(
    image_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Return the processed 512px fundus image."""

    return Response(
        service.image_file(
            conn,
            image_id,
        ),
        media_type="image/jpeg",
    )


@api.get(
    "/images/{image_id}/original",
    tags=["images"],
    response_class=Response,
)
def image_original(
    image_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Return the original fundus image."""

    return Response(
        service.image_file(
            conn,
            image_id,
            original=True,
        ),
        media_type="image/jpeg",
    )


@api.delete(
    "/images/{image_id}",
    status_code=204,
    tags=["images"],
)
def discard_image(
    image_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Delete an unscreened image."""

    service.delete_image(
        conn,
        image_id,
    )

    conn.commit()


@api.get(
    "/heatmaps/{heatmap_id}",
    tags=["images"],
    response_class=Response,
)
def heatmap(
    heatmap_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Return a generated screening heatmap."""

    return Response(
        service.heatmap_file(
            conn,
            heatmap_id,
        ),
        media_type="image/jpeg",
    )


# ---------- Screenings ----------

@api.post(
    "/screenings",
    response_model=Screening,
    status_code=201,
    tags=["screenings"],
)
def screen(
    body: ScreeningIn,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Create a screening and commit the results.

    Generated heatmaps are cleaned up if the
    PostgreSQL transaction fails before committing.
    """

    screening_id = service.create_screening(
        conn,
        user["id"],
        body.patient_id,
        body.eye,
        body.image_id,
        body.skipped,
        body.skip_reason,
    )

    # The heatmap metadata is visible inside the
    # current transaction before commit.
    # Skipped screenings will have no heatmaps.
    heatmap_rows = conn.execute(
        """
        SELECT h.stored_path
        FROM heatmaps h
        JOIN condition_results cr
            ON cr.id = h.condition_result_id
        WHERE cr.screening_id = %s
        """,
        (screening_id,),
    ).fetchall()

    uploaded_heatmaps = [
        (
            "heatmaps",
            row["stored_path"],
        )
        for row in heatmap_rows
    ]

    try:
        conn.commit()

    except Exception:
        conn.rollback()

        if uploaded_heatmaps:
            service.cleanup_storage_objects(
                uploaded_heatmaps
            )

        raise

    return service.screening_detail(
        conn,
        screening_id,
    )


@api.get(
    "/screenings",
    response_model=list[ScreeningSummary],
    tags=["screenings"],
)
def history(
    conn: PgDb,
    user: PostgresCurrentUser,
    search: Optional[str] = None,
    patient_id: Optional[str] = None,
    date: Optional[str] = None,
    eye: Optional[Eye] = None,
    result: Optional[
        Literal["no_concern", "refer"]
    ] = None,
):
    """Retrieve screening history with optional filters."""

    return service.list_screenings(
        conn,
        search,
        patient_id,
        date,
        eye,
        result,
    )


@api.get(
    "/screenings/{screening_id}",
    response_model=Screening,
    tags=["screenings"],
)
def screening(
    screening_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Retrieve complete screening results."""

    return service.screening_detail(
        conn,
        screening_id,
    )


@api.get(
    "/screenings/{screening_id}/report",
    tags=["screenings"],
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/pdf": {}
            }
        }
    },
)
def screening_report(
    screening_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Export a screening summary as PDF."""

    detail = service.screening_detail(
        conn,
        screening_id,
    )

    pdf = reports.screening_pdf(
        detail,
    )

    return _pdf_response(
        pdf,
        f"{screening_id}_summary.pdf",
    )


# ---------- Users ----------

def own_records(user_id, user):
    """Allow users to read only their own records."""

    if user_id != user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own records",
        )


@api.get(
    "/users/{user_id}/patients",
    response_model=list[PatientSummary],
    tags=["users"],
)
def user_patients(
    user_id: int,
    conn: PgDb,
    user: PostgresCurrentUser,
    search: Optional[str] = None,
):
    """Patients the user added or screened, with the latest result per eye."""

    own_records(user_id, user)

    return service.list_patients(
        conn,
        search,
        user_id,
    )


@api.get(
    "/users/{user_id}/screenings",
    response_model=list[ScreeningSummary],
    tags=["users"],
)
def user_screenings(
    user_id: int,
    conn: PgDb,
    user: PostgresCurrentUser,
    search: Optional[str] = None,
    patient_id: Optional[str] = None,
    date: Optional[str] = None,
    eye: Optional[Eye] = None,
    result: Optional[
        Literal["no_concern", "refer"]
    ] = None,
):
    """Screenings run by the user, newest first."""

    own_records(user_id, user)

    return service.list_screenings(
        conn,
        search,
        patient_id,
        date,
        eye,
        result,
        user_id,
    )


@api.get(
    "/users/{user_id}/summary",
    response_model=DashboardSummary,
    tags=["users"],
)
def user_summary(
    user_id: int,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Today's counts, patients to follow up, eyes to rescreen and this week's results for the user."""

    own_records(user_id, user)

    return service.dashboard_summary(
        conn,
        user_id,
    )


# ---------- Model Versions ----------

@api.get(
    "/model-versions/{version_id}",
    response_model=ModelVersion,
    tags=["model versions"],
)
def model_version(
    version_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    """Retrieve a model version and its thresholds."""

    return service.model_version(
        conn,
        version_id,
    )


# ---------- System ----------

@app.get(
    "/health",
    tags=["system"],
)
def health():
    """Health check endpoint."""

    return {
        "status": "ok"
    }


# ---------- Routes ----------

app.include_router(api)


# ---------- PDF Response ----------

def _pdf_response(pdf, filename):
    """Return PDF bytes as a downloadable response."""

    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )