import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DbSession
from app.models.content import GeneratedContent as GeneratedContentModel
from app.models.export import ExportJob as ExportJobModel
from app.schemas.export import ExportJob, ExportRequest
from app.services import export_render

logger = logging.getLogger("app")

router = APIRouter(prefix="/export", tags=["export"])

_MEDIA_TYPES = {
    "export.pdf": "application/pdf",
    "export.csv": "text/csv",
    "export.png": "image/png",
    "export.zip": "application/zip",
}


@router.post("", response_model=ExportJob)
def create_job(request: ExportRequest, current_user: CurrentUser, db: DbSession) -> ExportJobModel:
    items = (
        db.query(GeneratedContentModel)
        .filter(
            GeneratedContentModel.id.in_(request.content_ids),
            GeneratedContentModel.clinic_id == current_user.clinic_id,
        )
        .all()
    )
    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "None of the selected content was found.")

    job = ExportJobModel(
        clinic_id=current_user.clinic_id,
        format=request.format,
        content_ids=[item.id for item in items],
        status="processing",
    )
    db.add(job)
    db.flush()

    try:
        export_render.render(request.format, items, current_user.clinic_id, job.id)
        job.status = "completed"
        job.download_url = f"export/{job.id}/download"
    except Exception:
        logger.exception("Export rendering failed for job %s", job.id)
        job.status = "failed"

    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[ExportJob])
def list_jobs(current_user: CurrentUser, db: DbSession) -> list[ExportJobModel]:
    return (
        db.query(ExportJobModel)
        .filter(ExportJobModel.clinic_id == current_user.clinic_id)
        .order_by(ExportJobModel.created_at.desc())
        .all()
    )


@router.get("/{job_id}/download")
def download_job(job_id: str, current_user: CurrentUser, db: DbSession) -> FileResponse:
    job = (
        db.query(ExportJobModel)
        .filter(ExportJobModel.id == job_id, ExportJobModel.clinic_id == current_user.clinic_id)
        .first()
    )
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Export job not found.")
    if job.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Export job is {job.status}, not ready to download.")

    directory = export_render.job_dir(current_user.clinic_id, job.id)
    for filename, media_type in _MEDIA_TYPES.items():
        candidate = directory / filename
        if candidate.exists():
            download_name = f"dentalpilot-export-{job.id[:8]}{candidate.suffix}"
            return FileResponse(candidate, media_type=media_type, filename=download_name)

    raise HTTPException(status.HTTP_404_NOT_FOUND, "Export file is missing.")
