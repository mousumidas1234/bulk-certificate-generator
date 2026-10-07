def test_create_job_starts_bulk_processing(client, payload):
    response = client[0].post("/api/jobs", json=payload)
    data = response.json()
    assert response.status_code == 202
    assert data["job_id"] > 0
    assert data["total"] == 2
    assert data["successful"] == 0


def test_missing_job_returns_404(client):
    response = client[0].get("/api/jobs/9999")
    assert response.status_code == 404
