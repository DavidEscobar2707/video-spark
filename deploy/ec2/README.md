# VideoSpark EC2 Deployment Guide

This stack is the production launcher for the VideoSpark MVP backend:

- Caddy reverse proxy with HTTPS
- FastAPI API
- one worker

## Prerequisites
- Ubuntu or Debian-based EC2 instance
- inbound ports `80` and `443` open in the security group
- DNS record pointing `api.yourdomain.com` to the EC2 public IP
- Docker and Docker Compose plugin installed

## 1. Install Docker on the instance
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out and back in after adding the user to the `docker` group.

## 2. Clone the repo
```bash
git clone <your-repo-url> videospark
cd videospark
```

## 3. Configure the backend environment
Copy the backend template and fill real values:

```bash
cp backend/.env.example backend/.env
```

Set at minimum:
- `APP_ENV=production`
- `AUTH_ENABLED=true`
- `APP_BASE_URL=https://api.yourdomain.com`
- `FRONTEND_URL=https://<your-lovable-domain>`
- `CORS_ORIGINS=https://<your-lovable-domain>`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWKS_URL`
- `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY`
- `SUPABASE_ASSETS_BUCKET`
- `SUPABASE_VIDEOS_BUCKET`
- `WORKER_ID=ec2-worker-1`

Keep `AUTH_ENABLED=true` in production.

## 4. Configure the EC2 compose env
```bash
cp deploy/ec2/.env.example deploy/ec2/.env
```

Set:
- `APP_DOMAIN=api.yourdomain.com`
- `BACKEND_ENV_FILE=../../backend/.env`

## 5. Launch the stack
From the repo root:

```bash
docker compose -f deploy/ec2/docker-compose.yml up --build -d
```

## 6. Verify the deployment
```bash
docker compose -f deploy/ec2/docker-compose.yml ps
docker compose -f deploy/ec2/docker-compose.yml logs api --tail 100
docker compose -f deploy/ec2/docker-compose.yml logs worker --tail 100
curl -k https://api.yourdomain.com/health
```

Expected health response:

```json
{"status":"ok"}
```

## 7. Smoke-test the MVP API
Test only the launch endpoints:
- `GET /health`
- `POST /api/v1/render`
- `POST /api/v1/calculate-credits`
- `GET /api/v1/status`
- `GET /api/v1/projects`

Avatar is intentionally disabled for the MVP and should not be used.

## 8. Lovable hookup
After the backend is healthy:
- set the Lovable frontend env for the backend base URL to `https://api.yourdomain.com`
- keep Supabase Auth enabled in the frontend
- ensure the frontend sends `Authorization: Bearer <supabase_access_token>`
- expose only the active MVP routes
