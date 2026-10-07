from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, CertificateStatus

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.get("/{certificate_id}", name="get_certificate")
async def get_certificate(certificate_id: int, request: Request, db: Session = Depends(get_db)):
    certificate = db.get(Certificate, certificate_id)
    if certificate is None or certificate.status != CertificateStatus.SUCCESS.value or not certificate.file_path:
        raise HTTPException(status_code=404, detail="Certificate not found")
    file_path = Path(certificate.file_path).resolve()
    generated_dir = Path(request.app.state.generated_dir).resolve()
    if generated_dir not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Certificate file not found")
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"certificate-{certificate.id}.pdf",
    )
