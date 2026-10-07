def test_valid_input_creates_job(client, payload):
    response = client[0].post("/api/jobs", json=payload)
    assert response.status_code == 202
    assert response.json()["total"] == 2


def test_blank_recipient_name_is_rejected(client, payload):
    payload["recipients"][0]["name"] = "  "
    response = client[0].post("/api/jobs", json=payload)
    assert response.status_code == 422


def test_invalid_email_is_rejected(client, payload):
    payload["recipients"][0]["email"] = "not-an-email"
    response = client[0].post("/api/jobs", json=payload)
    assert response.status_code == 422


def test_empty_recipient_list_is_rejected(client, payload):
    payload["recipients"] = []
    response = client[0].post("/api/jobs", json=payload)
    assert response.status_code == 422


def test_blank_event_name_is_rejected(client, payload):
    payload["event_name"] = ""
    response = client[0].post("/api/jobs", json=payload)
    assert response.status_code == 422
