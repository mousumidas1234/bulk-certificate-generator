from datetime import date

from app.models import GenerationJob, JobStatus


def test_job_status_reports_progress_and_results(client, payload):
    create = client[0].post("/api/jobs", json=payload)
    job = client[0].get(f"/api/jobs/{create.json()['job_id']}")
    data = job.json()
    assert job.status_code == 200
    assert data["processed"] == 2
    assert data["progress"] == 100
    assert len(data["certificates"]) == 2


def test_job_certificates_endpoint(client, payload):
    create = client[0].post("/api/jobs", json=payload)
    response = client[0].get(f"/api/jobs/{create.json()['job_id']}/certificates")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_job_status_reports_intermediate_progress(client):
    db = client[1]()
    job = GenerationJob(
        event_name="Progress Event",
        event_date=date(2026, 10, 7),
        status=JobStatus.PROCESSING.value,
        total=10,
        successful=5,
        failed=2,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    response = client[0].get(f"/api/jobs/{job.id}")
    assert response.status_code == 200
    assert response.json()["processed"] == 7
    assert response.json()["progress"] == 70
    db.close()
