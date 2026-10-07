def test_missing_certificate_returns_404(client):
    response = client[0].get("/api/certificates/9999")
    assert response.status_code == 404


def test_certificate_download_endpoint(client, payload):
    job = client[0].post("/api/jobs", json=payload).json()
    certificates = client[0].get(f"/api/jobs/{job['job_id']}/certificates").json()
    response = client[0].get(f"/api/certificates/{certificates[0]['id']}")
    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"
