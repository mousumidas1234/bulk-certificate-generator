from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Certificate, CertificateStatus, GenerationJob, JobStatus
from app.schemas import RecipientInput
from app.templates.certificate_template import create_certificate_pdf

logger = logging.getLogger(__name__)


def process_job(job_id: int, recipients: list[RecipientInput], generated_dir: Path, session_factory) -> None:
    """Generate every certificate independently so one failure cannot abort the job."""
    db: Session = session_factory()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            logger.error("Cannot process missing generation job %s", job_id)
            return
        job.status = JobStatus.PROCESSING.value
        db.commit()

        for recipient in recipients:
            certificate_id = None
            try:
                certificate = Certificate(
                    job_id=job.id,
                    recipient_name=recipient.name,
                    recipient_email=str(recipient.email),
                    status=CertificateStatus.PENDING.value,
                )
                db.add(certificate)
                db.flush()
                certificate_id = certificate.id
                output_path = generated_dir / str(job.id) / f"{uuid.uuid4().hex}.pdf"
                create_certificate_pdf(output_path, recipient.name, job.event_name, job.event_date)
                certificate.status = CertificateStatus.SUCCESS.value
                certificate.file_path = str(output_path)
                job.successful += 1
                db.commit()
            except Exception:
                logger.exception("Certificate generation failed for job %s certificate %s", job.id, certificate_id)
                db.rollback()

                # Rollback may remove the original row, so recreate a safe
                # failed result in a fresh transaction before continuing.
                try:
                    job = db.get(GenerationJob, job_id)
                    if job is None:
                        logger.error("Generation job %s disappeared during processing", job_id)
                        continue
                    failed_certificate = Certificate(
                        job_id=job.id,
                        recipient_name=recipient.name,
                        recipient_email=str(recipient.email),
                        status=CertificateStatus.FAILED.value,
                        error_message="Certificate generation failed.",
                    )
                    db.add(failed_certificate)
                    job.failed += 1
                    db.commit()
                except Exception:
                    logger.exception("Could not persist failure for job %s recipient %s", job_id, recipient.email)
                    db.rollback()

        job.status = (
            JobStatus.COMPLETED_WITH_ERRORS.value if job.failed else JobStatus.COMPLETED.value
        )
        job.completed_at = datetime.now(UTC)
        db.commit()
    except Exception:
        logger.exception("Unexpected failure while processing job %s", job_id)
        job = db.get(GenerationJob, job_id)
        if job is not None:
            job.status = JobStatus.FAILED.value
            job.completed_at = datetime.now(UTC)
            db.commit()
    finally:
        db.close()


async def process_job_async(job_id: int, recipients: list[RecipientInput], generated_dir: Path, session_factory) -> None:
    """Async adapter used by FastAPI so in-process background execution is awaitable."""
    process_job(job_id, recipients, generated_dir, session_factory)
