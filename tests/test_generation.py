from datetime import date

from app.models import Certificate, CertificateStatus, GenerationJob, JobStatus
from app.schemas import RecipientInput
from app.services.certificate_generator import process_job
from sqlalchemy.orm import Session


def test_certificates_are_generated_as_pdf(client, payload):
    response = client[0].post("/api/jobs", json=payload)
    data = client[0].get(f"/api/jobs/{response.json()['job_id']}").json()
    assert data["status"] == "completed"
    assert data["successful"] == 2
    assert data["failed"] == 0
    assert data["progress"] == 100
    for certificate in data["certificates"]:
        assert certificate["status"] == "success"
        pdf = client[0].get(certificate["download_url"])
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF")


def test_unicode_recipient_name_is_supported(client, payload):
    payload["recipients"] = [{"name": "Zoë Müller", "email": "unicode@example.com"}]
    job = client[0].post("/api/jobs", json=payload).json()
    result = client[0].get(f"/api/jobs/{job['job_id']}/certificates").json()[0]
    assert result["status"] == "success"
    assert client[0].get(f"/api/certificates/{result['id']}").content.startswith(b"%PDF")


def test_one_certificate_failure_does_not_stop_remaining(client, monkeypatch):
    from app.services import certificate_generator

    original = certificate_generator.create_certificate_pdf

    def fail_for_one(path, recipient_name, event_name, event_date):
        if recipient_name == "Bad Recipient":
            raise RuntimeError("simulated renderer failure")
        original(path, recipient_name, event_name, event_date)

    monkeypatch.setattr(certificate_generator, "create_certificate_pdf", fail_for_one)
    db = client[1]()
    job = GenerationJob(
        event_name="Resilient Event", event_date=date(2026, 10, 7), status=JobStatus.PENDING.value, total=3
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    recipients = [
        RecipientInput(name="Good One", email="one@example.com"),
        RecipientInput(name="Bad Recipient", email="bad@example.com"),
        RecipientInput(name="Good Two", email="two@example.com"),
    ]
    process_job(job.id, recipients, client[2], client[1])
    db.refresh(job)
    assert job.status == JobStatus.COMPLETED_WITH_ERRORS.value
    assert (job.successful, job.failed) == (2, 1)
    assert [c.status for c in job.certificates] == [CertificateStatus.SUCCESS.value, CertificateStatus.FAILED.value, CertificateStatus.SUCCESS.value]
    db.close()


def test_api_partial_failure_continues_to_later_recipients(client, payload, monkeypatch):
    from app.services import certificate_generator

    original = certificate_generator.create_certificate_pdf

    def fail_for_one(path, recipient_name, event_name, event_date):
        if recipient_name == "Bad Recipient":
            raise RuntimeError("simulated renderer failure")
        original(path, recipient_name, event_name, event_date)

    monkeypatch.setattr(certificate_generator, "create_certificate_pdf", fail_for_one)
    payload["recipients"] = [
        {"name": "Good One", "email": "one@example.com"},
        {"name": "Bad Recipient", "email": "bad@example.com"},
        {"name": "Good Two", "email": "two@example.com"},
    ]

    created = client[0].post("/api/jobs", json=payload)
    assert created.status_code == 202
    job_id = created.json()["job_id"]

    job = client[0].get(f"/api/jobs/{job_id}").json()
    certificates = client[0].get(f"/api/jobs/{job_id}/certificates").json()

    assert job["status"] == "completed_with_errors"
    assert (job["total"], job["successful"], job["failed"], job["processed"], job["progress"]) == (3, 2, 1, 3, 100)
    assert [certificate["status"] for certificate in certificates] == ["success", "failed", "success"]


def test_recipient_database_failure_is_recorded_and_processing_continues(client, monkeypatch):
    original_flush = Session.flush
    failed_once = False

    def fail_first_certificate_flush(session, *args, **kwargs):
        nonlocal failed_once
        has_pending_certificate = any(
            isinstance(instance, Certificate) and instance.status == CertificateStatus.PENDING.value
            for instance in session.new
        )
        if has_pending_certificate and not failed_once:
            failed_once = True
            raise RuntimeError("simulated recipient database failure")
        return original_flush(session, *args, **kwargs)

    monkeypatch.setattr(Session, "flush", fail_first_certificate_flush)
    db = client[1]()
    job = GenerationJob(
        event_name="Database Failure Event", event_date=date(2026, 10, 7), status=JobStatus.PENDING.value, total=3
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    recipients = [
        RecipientInput(name="First Recipient", email="first@example.com"),
        RecipientInput(name="Second Recipient", email="second@example.com"),
        RecipientInput(name="Third Recipient", email="third@example.com"),
    ]

    process_job(job.id, recipients, client[2], client[1])
    db.refresh(job)
    assert job.status == JobStatus.COMPLETED_WITH_ERRORS.value
    assert (job.successful, job.failed) == (2, 1)
    assert [certificate.status for certificate in job.certificates] == [
        CertificateStatus.FAILED.value,
        CertificateStatus.SUCCESS.value,
        CertificateStatus.SUCCESS.value,
    ]
    db.close()
