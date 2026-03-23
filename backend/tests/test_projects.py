from __future__ import annotations


def test_status_rejects_malformed_uuid(client):
    response = client.get("/api/v1/status", params={"pid": "not-a-uuid"})

    assert response.status_code == 422
