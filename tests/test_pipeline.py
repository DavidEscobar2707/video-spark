from __future__ import annotations

from pathlib import Path

import pytest

from app.tasks import pipeline


@pytest.mark.asyncio
async def test_run_pipeline_updates_progress_and_marks_local_artifact(monkeypatch, tmp_path):
    states: list[tuple[str, int]] = []

    async def fake_update_job_state(job, **kwargs):
        stage = kwargs.get("stage", job.get("pipeline_state", {}).get("stage", "unknown"))
        progress = kwargs.get("progress", job.get("progress", 0))
        pipeline_state = {**(job.get("pipeline_state") or {}), **(kwargs.get("pipeline_extra") or {})}
        if stage is not None:
            pipeline_state["stage"] = stage
        states.append((stage, progress))
        return {**job, "pipeline_state": pipeline_state, "progress": progress}

    async def fake_mark_job_completed(job, output_url, *, pipeline_extra=None):
        return {
            **job,
            "status": "completed",
            "output_video_url": output_url,
            "pipeline_state": {**(job.get("pipeline_state") or {}), **(pipeline_extra or {}), "stage": "completed"},
        }

    async def fake_generate_script(payload):
        return payload.source.text

    async def fake_split_scenes(script, payload):
        return [
            {"text": script, "visualPrompt": script, "durationSeconds": 4},
            {"text": f"{script} CTA", "visualPrompt": script, "durationSeconds": 4},
        ]

    async def fake_generate_voice(script, voice_config, runtime_config):
        _ = script
        _ = voice_config
        _ = runtime_config
        return {"audioPath": (tmp_path / "voice.mp3").as_posix(), "modelId": "eleven_multilingual_v2"}

    async def fake_build_captions(voice_artifact, captions_config, runtime_config):
        _ = voice_artifact
        _ = captions_config
        _ = runtime_config
        ass_path = tmp_path / "captions.ass"
        srt_path = tmp_path / "captions.srt"
        ass_path.write_text("ass", encoding="utf-8")
        srt_path.write_text("srt", encoding="utf-8")
        return {"assPath": ass_path.as_posix(), "srtPath": srt_path.as_posix()}

    async def fake_generate_scene_clips(scenes, config):
        _ = config
        for index, _scene in enumerate(scenes):
            yield {
                "sceneIndex": index,
                "clipPath": (tmp_path / f"clip-{index}.mp4").as_posix(),
                "operationName": f"operations/{index}",
                "prompt": f"scene {index}",
                "durationSeconds": 4,
            }

    async def fake_compose_video(scenes, media_urls, voice_url, subtitle_ass_path, config):
        _ = scenes
        _ = media_urls
        _ = voice_url
        _ = subtitle_ass_path
        final_path = tmp_path / config["jobId"] / "final.mp4"
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_bytes(b"mp4")
        return final_path.as_posix()

    def fake_upload_final_video(local_path, runtime_config):
        _ = local_path
        return f"https://storage.example.com/{runtime_config['jobId']}/final.mp4"

    monkeypatch.setattr(pipeline, "update_job_state", fake_update_job_state)
    monkeypatch.setattr(pipeline, "mark_job_completed", fake_mark_job_completed)
    monkeypatch.setattr(pipeline, "generate_script", fake_generate_script)
    monkeypatch.setattr(pipeline, "split_scenes", fake_split_scenes)
    monkeypatch.setattr(pipeline, "generate_voice", fake_generate_voice)
    monkeypatch.setattr(pipeline, "build_captions", fake_build_captions)
    monkeypatch.setattr(pipeline, "generate_scene_clips", fake_generate_scene_clips)
    monkeypatch.setattr(pipeline, "compose_video", fake_compose_video)
    monkeypatch.setattr(pipeline, "upload_final_video", fake_upload_final_video)

    job = {
        "job_id": "job-xyz",
        "project_id": "project-xyz",
        "tenant_id": "tenant-xyz",
        "config": {
            "workflow": "script-to-video",
            "source": {"text": "Hook the audience fast."},
            "media": {"type": "ai-video"},
            "voice": {"enabled": True, "voiceId": "voice-123"},
            "captions": {"enabled": True, "preset": "karaoke"},
            "render": {"resolution": "720p"},
            "aspectRatio": "9:16",
        },
        "pipeline_state": {},
    }

    result = await pipeline._run_pipeline(job)

    assert result["status"] == "completed"
    assert result["output_video_url"] == "https://storage.example.com/job-xyz/final.mp4"
    assert result["pipeline_state"]["stage"] == "completed"
    assert Path(result["pipeline_state"]["finalLocalPath"]).exists()
    assert result["pipeline_state"]["subtitleAssPath"].endswith("captions.ass")
    assert [stage for stage, _progress in states] == [
        "generating_script",
        "script_ready",
        "generating_voice",
        "voice_ready",
        "building_captions",
        "captions_ready",
        "generating_clips",
        "generating_clips",
        "generating_clips",
        "clips_ready",
        "assembling_video",
        "uploading_output",
    ]


@pytest.mark.asyncio
async def test_run_avatar_pipeline_uses_avatar_branch_and_preserves_clip_audio(monkeypatch, tmp_path):
    states: list[tuple[str, int]] = []

    async def fake_update_job_state(job, **kwargs):
        stage = kwargs.get("stage", job.get("pipeline_state", {}).get("stage", "unknown"))
        progress = kwargs.get("progress", job.get("progress", 0))
        pipeline_state = {**(job.get("pipeline_state") or {}), **(kwargs.get("pipeline_extra") or {})}
        if stage is not None:
            pipeline_state["stage"] = stage
        states.append((stage, progress))
        return {**job, "pipeline_state": pipeline_state, "progress": progress}

    async def fake_mark_job_completed(job, output_url, *, pipeline_extra=None):
        return {
            **job,
            "status": "completed",
            "output_video_url": output_url,
            "pipeline_state": {**(job.get("pipeline_state") or {}), **(pipeline_extra or {}), "stage": "completed"},
        }

    async def fake_generate_script(payload):
        return payload.source.text

    async def fake_split_avatar_scenes(script, payload):
        _ = payload
        return [
            {"text": f"{script} one", "durationSeconds": 6, "generateAudio": True},
            {"text": f"{script} two", "durationSeconds": 6, "generateAudio": True},
            {"text": f"{script} three", "durationSeconds": 6, "generateAudio": True},
        ]

    async def fake_generate_scene_clips(scenes, config):
        assert config["preserveClipAudio"] is True
        for index, _scene in enumerate(scenes):
            yield {
                "sceneIndex": index,
                "clipPath": (tmp_path / f"avatar-clip-{index}.mp4").as_posix(),
                "operationName": f"operations/{index}",
                "prompt": f"scene {index}",
                "durationSeconds": 6,
            }

    async def fake_compose_video(scenes, media_urls, voice_url, subtitle_ass_path, config):
        _ = scenes
        _ = media_urls
        _ = voice_url
        _ = subtitle_ass_path
        assert config["preserveClipAudio"] is True
        final_path = tmp_path / config["jobId"] / "avatar-final.mp4"
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_bytes(b"mp4")
        return final_path.as_posix()

    def fake_upload_final_video(local_path, runtime_config):
        _ = local_path
        return f"https://storage.example.com/{runtime_config['jobId']}/avatar-final.mp4"

    monkeypatch.setattr(pipeline, "update_job_state", fake_update_job_state)
    monkeypatch.setattr(pipeline, "mark_job_completed", fake_mark_job_completed)
    monkeypatch.setattr(pipeline, "generate_script", fake_generate_script)
    monkeypatch.setattr(pipeline, "split_avatar_scenes", fake_split_avatar_scenes)
    monkeypatch.setattr(pipeline, "generate_scene_clips", fake_generate_scene_clips)
    monkeypatch.setattr(pipeline, "compose_video", fake_compose_video)
    monkeypatch.setattr(pipeline, "upload_final_video", fake_upload_final_video)

    job = {
        "job_id": "avatar-job-xyz",
        "project_id": "avatar-project-xyz",
        "tenant_id": "tenant-xyz",
        "config": {
            "workflow": "avatar-to-video",
            "source": {"text": "Introduce the product with a premium founder message."},
            "media": {"type": "ai-video"},
            "voice": {"enabled": False},
            "captions": {"enabled": False},
            "render": {"resolution": "720p"},
            "aspectRatio": "9:16",
            "avatar": {"enabled": True, "presetId": "default-avatar", "url": "https://example.com/avatar.png"},
        },
        "pipeline_state": {},
    }

    result = await pipeline._run_pipeline(job)

    assert result["status"] == "completed"
    assert result["output_video_url"] == "https://storage.example.com/avatar-job-xyz/avatar-final.mp4"
    assert result["pipeline_state"]["stage"] == "completed"
    assert Path(result["pipeline_state"]["finalLocalPath"]).exists()
    assert [stage for stage, _progress in states] == [
        "planning_avatar_video",
        "avatar_plan_ready",
        "generating_avatar_scene",
        "generating_broll_scenes",
        "generating_broll_scenes",
        "clips_ready",
        "assembling_video",
        "uploading_output",
    ]
