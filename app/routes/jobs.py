from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import Certificate, GenerationJob, JobStatus
from app.schemas import CertificateResponse, JobCreateRequest, JobResponse
from app.services.certificate_generator import process_job_async

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _certificate_response(certificate: Certificate, request: Request) -> CertificateResponse:
    download_url = None
    if certificate.status == "success":
        download_url = str(request.url_for("get_certificate", certificate_id=certificate.id))
    return CertificateResponse(
        id=certificate.id,
        recipient_name=certificate.recipient_name,
        recipient_email=certificate.recipient_email,
        status=certificate.status,
        error_message=certificate.error_message,
        download_url=download_url,
    )


def _job_response(job: GenerationJob, request: Request, include_certificates: bool = True) -> JobResponse:
    processed = job.successful + job.failed
    progress = round(processed * 100 / job.total) if job.total else 100
    return JobResponse(
        job_id=job.id,
        status=job.status,
        total=job.total,
        successful=job.successful,
        failed=job.failed,
        processed=processed,
        progress=progress,
        created_at=job.created_at,
        completed_at=job.completed_at,
        certificates=[_certificate_response(c, request) for c in job.certificates] if include_certificates else [],
    )


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(payload: JobCreateRequest, background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    job = GenerationJob(
        event_name=payload.event_name,
        event_date=payload.event_date,
        status=JobStatus.PENDING.value,
        total=len(payload.recipients),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(process_job_async, job.id, payload.recipients, Path(request.app.state.generated_dir), SessionLocal)
    return _job_response(job, request, include_certificates=False)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, request: Request, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return _job_response(job, request)


@router.get("/{job_id}/certificates", response_model=list[CertificateResponse])
async def get_job_certificates(job_id: int, request: Request, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return [_certificate_response(c, request) for c in job.certificates]
