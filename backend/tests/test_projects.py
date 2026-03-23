from __future__ import annotations

from app.routes import projects as project_routes


def test_status_rejects_malformed_uuid(client):
    response = client.get("/api/v1/status", params={"pid": "not-a-uuid"})

    assert response.status_code == 422


def test_get_project_returns_detail_payload(client, monkeypatch):
    async def fake_get_project_detail(tenant_id: str, pid: str):
        assert tenant_id == "dev-user"
        assert pid == "11111111-1111-1111-1111-111111111111"
        return {
            "id": pid,
            "title": "Launch Ad",
            "status": "completed",
            "workflow": "script-to-video",
            "output_video_url": "https://example.com/final.mp4",
            "thumbnail_url": None,
            "duration_seconds": 20,
            "created_at": "2026-03-23T00:00:00Z",
            "updated_at": "2026-03-23T00:05:00Z",
            "config": {"workflow": "script-to-video"},
            "latest_job": {
                "id": "job-1",
                "status": "completed",
                "progress": 100,
                "output_video_url": "https://example.com/final.mp4",
                "metadata": {"stageLabel": "completed"},
            },
            "versions": [
                {
                    "id": "job-1",
                    "status": "completed",
                    "progress": 100,
                    "output_video_url": "https://example.com/final.mp4",
                    "metadata": {"stageLabel": "completed"},
                }
            ],
        }

    monkeypatch.setattr(project_routes, "get_project_detail", fake_get_project_detail)

    response = client.get("/api/v1/projects/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["latest_job"]["id"] == "job-1"
    assert len(payload["versions"]) == 1


def test_rerender_existing_project_queues_new_version(client, monkeypatch):
    async def fake_rerender_project(user, pid: str, payload):
        assert user.tenant_id == "dev-user"
        assert pid == "11111111-1111-1111-1111-111111111111"
        assert payload.workflow.value == "script-to-video"
        return {
            "project_id": pid,
            "workflow": "script-to-video",
            "webhook_url": None,
        }

    monkeypatch.setattr(project_routes, "rerender_project", fake_rerender_project)

    response = client.post(
        "/api/v1/projects/11111111-1111-1111-1111-111111111111/rerender",
        json={
            "workflow": "script-to-video",
            "source": {"text": "Refresh this launch ad"},
            "media": {"type": "ai-video", "quality": "pro"},
            "voice": {"enabled": True},
            "captions": {"enabled": True, "preset": "karaoke-clean", "position": "middle"},
            "render": {"resolution": "720p"},
            "aspectRatio": "9:16",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pid"] == "11111111-1111-1111-1111-111111111111"
    assert payload["workflow"] == "script-to-video"
