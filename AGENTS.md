# VideoSpark MVP Operator Guide

## Active Architecture
- Frontend: Lovable project using Supabase Auth.
- Backend API: FastAPI service in `backend/app/main.py`.
- Worker: single long-running worker in `backend/app/worker.py`.
- Data and storage: Supabase Postgres + Supabase Storage.
- Video pipeline: Gemini Veo clips + ElevenLabs narration/timestamps + ffmpeg assembly.

## Launch Scope
- Supported endpoints:
  - `GET /health`
  - `POST /api/v1/render`
  - `POST /api/v1/calculate-credits`
  - `GET /api/v1/status`
  - `GET /api/v1/projects`
- Supported workflows:
  - `prompt-to-video`
  - `script-to-video`
- Supported media:
  - `ai-video`
- Supported output:
  - `9:16`
  - `720p` or `1080p`
- Unsupported at launch:
  - article URL ingestion
  - moving-image mode
  - music
  - team management
  - payments
  - direct browser calls to provider APIs
  - avatar-to-video
  - user-uploaded avatar selection

## Auth Contract
- Production requires `AUTH_ENABLED=true`.
- The frontend must send `Authorization: Bearer <supabase_access_token>`.
- Never expose `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`, or `ELEVENLABS_API_KEY` to the browser.
- Tenant resolution is backend-owned; the frontend does not send `tenant_id`.

## Job Lifecycle
- `/render` creates a server-owned project and job.
- The worker processes stages in this order:
  - `generating_script`
  - `voice_ready`
  - `building_captions`
  - `generating_clips`
  - `assembling_video`
  - `uploading_output`
  - `completed` or `failed`
- A job is only considered complete when `output_video_url` is present in `/status`.
- `/status` returns browser-safe metadata only: stage label, worker id, clip count, and download readiness.

## Deployment Invariants
- Run exactly one worker for the MVP.
- Use the production compose in `deploy/ec2/docker-compose.yml` for EC2, not the dev compose in `backend/docker-compose.yml`.
- Put HTTPS in front of the API with Caddy or another reverse proxy.
- Set `FRONTEND_URL`, `APP_BASE_URL`, and `CORS_ORIGINS` to production values before launch.
- Upload outputs to Supabase Storage; do not rely on local container paths for delivery.

## Smoke Tests
- Local API boot:
  - `cd backend`
  - `docker compose up --build`
- Health check:
  - `curl http://localhost:8000/health`
- Full render:
  - submit `POST /api/v1/render`
  - poll `GET /api/v1/status?pid=...`
  - confirm `output_video_url` is non-null
- Provider smoke tests:
  - `docker compose exec -e RUN_LIVE_VEO_TESTS=1 api uv run pytest tests/test_video_provider.py -m live_veo`
  - `docker compose exec -e RUN_LIVE_ELEVENLABS_TESTS=1 api uv run pytest tests/test_voice.py -m live_elevenlabs`
