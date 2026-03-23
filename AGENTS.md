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
  - `GET /api/v1/voices`
  - `GET /api/v1/caption-presets`
  - `POST /api/v1/generate-script`
  - `POST /api/v1/render`
  - `POST /api/v1/image-story-render`
  - `POST /api/v1/calculate-credits`
  - `GET /api/v1/status`
  - `GET /api/v1/projects`
  - `GET /api/v1/projects/{pid}`
  - `POST /api/v1/projects/{pid}/rerender`
  - `GET /api/v1/assets`
  - `POST /api/v1/assets/upload`
- Supported workflows:
  - `prompt-to-video`
  - `script-to-video`
  - `image-story-to-video`
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
  - partial scene regeneration
  - direct social publishing

## Auth Contract
- Production requires `AUTH_ENABLED=true`.
- The frontend must send `Authorization: Bearer <supabase_access_token>`.
- Never expose `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`, or `ELEVENLABS_API_KEY` to the browser.
- Tenant resolution is backend-owned; the frontend does not send `tenant_id`.

## Job Lifecycle
- `/render` creates a server-owned project and job.
- `/image-story-render` creates a server-owned image-story project and job.
- `/projects/{pid}/rerender` creates a new job version under the same project.
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

## Editor And Assets
- `GET /api/v1/projects/{pid}` returns project config, latest job, and recent versions for the editor screen.
- `POST /api/v1/projects/{pid}/rerender` rerenders the whole video as a new version; it does not do per-scene regeneration.
- `GET /api/v1/voices` provides the frontend voice picker.
- `GET /api/v1/caption-presets` provides the supported caption designs.
- `POST /api/v1/generate-script` provides an edit-first script suggestion flow.
- `POST /api/v1/assets/upload` accepts image uploads as JSON with a base64 payload and stores them in Supabase Storage plus `public.assets`.
- `GET /api/v1/assets` lists uploaded assets, optionally filtered by `projectId`.

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
