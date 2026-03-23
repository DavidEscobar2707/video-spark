from __future__ import annotations

from app.utils import storage


def test_upload_to_storage_uses_string_upsert(monkeypatch):
    captured: dict[str, object] = {}

    class _FakeBucket:
        def upload(self, path, data, options):
            captured["path"] = path
            captured["data"] = data
            captured["options"] = options

        def get_public_url(self, path):
            return f"https://storage.example.com/{path}"

    class _FakeStorage:
        def from_(self, bucket_name):
            captured["bucket"] = bucket_name
            return _FakeBucket()

    class _FakeClient:
        storage = _FakeStorage()

    monkeypatch.setattr(storage, "get_supabase_client", lambda: _FakeClient())

    public_url = storage.upload_to_storage(
        "renders/job/final.mp4",
        b"video-bytes",
        "video/mp4",
        bucket="videos",
    )

    assert public_url == "https://storage.example.com/renders/job/final.mp4"
    assert captured["bucket"] == "videos"
    assert captured["options"] == {"content-type": "video/mp4", "upsert": "true"}
