from __future__ import annotations

from app.routes import assets as asset_routes


def test_get_assets_returns_filtered_asset_list(client, monkeypatch):
    async def fake_list_assets(tenant_id: str, project_id: str | None):
        assert tenant_id == "dev-user"
        assert project_id == "11111111-1111-1111-1111-111111111111"
        return [
            {
                "id": "asset-1",
                "type": "image",
                "url": "https://example.com/image.png",
                "project_id": project_id,
                "metadata": {"filename": "image.png"},
                "created_at": "2026-03-23T00:00:00Z",
            }
        ]

    monkeypatch.setattr(asset_routes, "list_assets", fake_list_assets)

    response = client.get(
        "/api/v1/assets",
        params={"projectId": "11111111-1111-1111-1111-111111111111"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "asset-1"
    assert body[0]["project_id"] == "11111111-1111-1111-1111-111111111111"


def test_upload_asset_accepts_base64_payload(client, monkeypatch):
    async def fake_upload_asset(user, payload):
        assert user.tenant_id == "dev-user"
        assert payload.filename == "image.png"
        assert payload.content_type == "image/png"
        assert payload.project_id == "11111111-1111-1111-1111-111111111111"
        return {
            "id": "asset-1",
            "type": "image",
            "url": "https://example.com/image.png",
            "project_id": payload.project_id,
            "metadata": {"filename": payload.filename},
            "created_at": "2026-03-23T00:00:00Z",
        }

    monkeypatch.setattr(asset_routes, "upload_asset", fake_upload_asset)

    response = client.post(
        "/api/v1/assets/upload",
        json={
            "filename": "image.png",
            "contentType": "image/png",
            "dataBase64": "aGVsbG8=",
            "projectId": "11111111-1111-1111-1111-111111111111",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "asset-1"
    assert body["metadata"]["filename"] == "image.png"
