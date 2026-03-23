# VideoSpark GitHub, EC2, and Lovable Rollout

## 1. Create the GitHub repository
Create a new empty GitHub repository from the web UI.

Recommended name:
- `videospark`

Recommended visibility:
- `private`

Do not add:
- README
- `.gitignore`
- license

This local repo is already initialized with `main`.

## 2. Push this repo to GitHub
From the repo root on your machine:

```bash
git add .
git commit -m "Initial VideoSpark MVP backend"
git remote add origin https://github.com/<your-user-or-org>/videospark.git
git push -u origin main
```

If you prefer SSH:

```bash
git remote add origin git@github.com:<your-user-or-org>/videospark.git
git push -u origin main
```

## 3. Recommended storage sizing
There are two different storage concerns:

### EC2 disk
This is for:
- Docker images
- build cache
- temporary Veo clips
- ffmpeg working files
- logs

Recommended starting size:
- `40 GB gp3`

Safe minimum if you want to be aggressive:
- `30 GB`

Do not start below `25 GB` unless this is strictly temporary internal testing.

### Supabase Storage buckets
Use separate buckets:
- `assets`
- `videos`

Recommended starting target:
- `assets`: `5 GB`
- `videos`: `50 GB`

Reasoning:
- a single final render can easily be tens of megabytes
- the `videos` bucket grows continuously unless you delete old outputs
- `assets` usually grows much slower than final renders

If this is an internal MVP with low volume, you can start smaller:
- `assets`: `2 GB`
- `videos`: `20 GB`

If this is customer-facing from day one, start with:
- `assets`: `10 GB`
- `videos`: `100 GB`

## 4. Clone and deploy on EC2
SSH into the instance, then:

```bash
git clone https://github.com/<your-user-or-org>/videospark.git
cd videospark
```

Create the backend env:

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Set at minimum:
- `APP_ENV=production`
- `AUTH_ENABLED=true`
- `APP_BASE_URL=https://api.yourdomain.com`
- `FRONTEND_URL=https://your-lovable-domain.com`
- `CORS_ORIGINS=https://your-lovable-domain.com`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWKS_URL`
- `SUPABASE_ASSETS_BUCKET=assets`
- `SUPABASE_VIDEOS_BUCKET=videos`
- `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY`
- `WORKER_ID=ec2-worker-1`

Create the EC2 compose env:

```bash
cp deploy/ec2/.env.example deploy/ec2/.env
nano deploy/ec2/.env
```

Set:
- `APP_DOMAIN=api.yourdomain.com`
- `BACKEND_ENV_FILE=../../backend/.env`

Start the stack:

```bash
docker compose -f deploy/ec2/docker-compose.yml up --build -d
```

Verify:

```bash
docker compose -f deploy/ec2/docker-compose.yml ps
docker compose -f deploy/ec2/docker-compose.yml logs api --tail 100
docker compose -f deploy/ec2/docker-compose.yml logs worker --tail 100
curl -k https://api.yourdomain.com/health
```

## 5. How Lovable should consume output
Lovable should not call provider APIs or Supabase service-role APIs directly.

Lovable should:
1. authenticate with Supabase Auth
2. call `POST /api/v1/render`
3. poll `GET /api/v1/status?pid=...`
4. read `output_video_url`
5. render the returned MP4 URL in the UI

That means the frontend should consume the backend response, not construct bucket paths itself.

Use:
- `output_video_url` from `/status`

Do not use:
- local worker paths
- guessed storage paths
- direct Gemini or ElevenLabs calls

## 6. Operational recommendation
For the first production deploy:
- keep only one worker
- use `720p` as the default frontend selection
- keep avatar hidden
- keep auth enabled
- test one real render end to end before sharing the app publicly
