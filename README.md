# VideoSpark Workspace

This repo now contains the backend-first launch scaffold for the VideoSpark project.

## Layout
- `scripts/` and the root `package.json`: operational helpers, including Supabase migration support.
- `docs/`: current integration handoff for Lovable.
- `backend/`: FastAPI + single-worker backend, intended to sit behind a Supabase-authenticated UI and run the video pipeline.
- `deploy/ec2/`: production compose and reverse-proxy scaffolding for a small EC2 deployment.
- `supabase/`: repo-owned SQL migrations and seed data for the launch schema.

## Local Development
1. Copy `backend/.env.example` to `backend/.env` and provide local secrets or placeholders.
2. Apply SQL in `supabase/migrations/` and `supabase/seed/` to your Supabase project.
3. Start backend services:
   - `cd backend`
   - `docker compose up --build`
4. Point your Lovable/Supabase frontend at the backend API URL and send the Supabase session token as `Authorization: Bearer <token>`.
5. Use `docs/lovable-integration-prompt.md` as the handoff prompt for the frontend builder.

## EC2 Deployment
1. Copy `backend/.env.example` to `backend/.env` on the EC2 box and fill real production values.
2. Copy `deploy/ec2/.env.example` to `deploy/ec2/.env` and set `APP_DOMAIN` plus `BACKEND_ENV_FILE`.
3. Start the production stack from the repo root:
   - `docker compose -f deploy/ec2/docker-compose.yml up --build -d`
4. Verify:
   - `curl -k https://api.yourdomain.com/health`
5. Use `deploy/ec2/README.md` as the step-by-step operator guide.
6. Use `docs/github-ec2-lovable-rollout.md` for the GitHub -> EC2 -> Lovable handoff flow.

## Notes
- Auth is Supabase-first. The browser authenticates with Supabase Auth, and the backend verifies the Supabase JWT before using the service-role key server-side.
- The active product path is backend-first: external UI -> Supabase Auth -> FastAPI API -> worker -> Supabase DB/storage.
- Launch scope is intentionally narrow: prompt/script inputs, ai-video only, status polling, ElevenLabs narration, and an ffmpeg-oriented assembly path.
- Active public endpoints for the MVP are `GET /health`, `POST /api/v1/render`, `POST /api/v1/calculate-credits`, `GET /api/v1/status`, and `GET /api/v1/projects`.
- Avatar is intentionally disabled in the MVP surface.
- Payments, teams, and the older Clerk/Next-only assumptions are not part of the active v1 path and are intentionally removed from the launch surface.
