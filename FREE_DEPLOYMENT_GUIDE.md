# CodeTrace AI — Free Deployment Guide

Deploy the entire CodeTrace AI stack for **$0/month** using free-tier hosting services.

---

## 1. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User Browser                                              │
│  https://codetrace-ai.vercel.app                           │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Vercel (Frontend)                               FREE      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ React 18 + Vite + Tailwind CSS + Monaco Editor       │  │
│  │ Build: npm run build → dist/                         │  │
│  └────────────────────┬──────────────────────────────────┘  │
└──────────────────────┬┴──────────────────────────────────────┘
                       │ POST /api/execute, /api/lint, /api/fix
                       │ GET  /api/health
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Render (Backend)                                 FREE      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Python 3.12 + FastAPI + Uvicorn                       │  │
│  │ EXECUTION_MODE=subprocess (no Docker on free tier)    │  │
│  │ Optional: OpenAI / Gemini AI explanations             │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key design decisions:**

| Layer | Service | Why |
|-------|---------|-----|
| Frontend | Vercel | Free tier includes SSL, custom domains, auto-deploy from GitHub |
| Backend | Render | Free tier supports Python natively, no Docker required |
| Database | None needed | CodeTrace AI is **stateless** — no database, no storage |
| AI | OpenAI / Gemini | Optional; app works fully without it |

### Why subprocess mode on Render?

Render's free tier does not support Docker. The project includes a `SubprocessExecutionBackend` that runs user code in an isolated OS subprocess instead of a Docker container. Set `EXECUTION_MODE=subprocess`.

> **Security note:** Subprocess mode does NOT provide the same isolation as Docker. It is suitable for a portfolio demonstration. Do not use it for multi-tenant production without additional hardening.

---

## 2. Prerequisites

| Item | Purpose |
|------|---------|
| [GitHub](https://github.com) account | Host the repository, connect to Vercel & Render |
| [Vercel](https://vercel.com) account | Deploy frontend (free tier) |
| [Render](https://render.com) account | Deploy backend (free tier) |
| Git installed locally | Push changes to GitHub |
| (Optional) [OpenAI](https://platform.openai.com) or [Gemini](https://ai.google.dev) API key | Enable AI-powered explanations |

---

## 3. Database Deployment

**No database is required.** CodeTrace AI is a stateless application. Each execution request is processed independently — no user accounts, no sessions, no persistent storage.

If you want to add a database later, the project has no existing schema or migrations to maintain.

---

## 4. Backend Deployment (Render)

### 4.1 Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/CodeTrace-AI.git
git push -u origin main
```

### 4.2 Create Render Web Service

1. Go to [https://dashboard.render.com](https://dashboard.render.com)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure the service:

| Setting | Value |
|---------|-------|
| **Name** | `codetrace-backend` |
| **Region** | Choose the closest (e.g., Oregon) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Root Directory** | `backend` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | **Free** |

> Render automatically detects Python 3.12 from the `python:3.12-slim` Docker base image. The free tier uses Python 3.x (3.11+).

### 4.3 Set Environment Variables

In the Render dashboard, go to **Environment** and add:

| Variable | Value | Notes |
|----------|-------|-------|
| `EXECUTION_MODE` | `subprocess` | Must be subprocess — no Docker on free tier |
| `ALLOWED_ORIGINS` | `https://codetrace-ai.vercel.app` | Replace with your Vercel URL after frontend deploy |
| `PORT` | `8000` | Render sets this automatically via `$PORT` |
| `PYTHON_VERSION` | `3.12.0` | Optional, pins Python version |
| `AI_PROVIDER` | *(leave empty)* | Set to `openai` or `gemini` if you have an API key |
| `AI_API_KEY` | *(leave empty)* | Your API key (leave blank to skip AI) |
| `AI_MODEL` | `gpt-4o` | Only used if `AI_PROVIDER` is set |

### 4.4 Health Check

Render automatically pings the health check endpoint. Configure it in the Render dashboard under **Health Check Path**:

```
/api/health
```

The health endpoint returns:

```json
{
  "status": "healthy",
  "execution_mode": "subprocess",
  "sandbox": "subprocess"
}
```

### 4.5 Verify Backend

After deployment completes, visit:

```
https://codetrace-backend.onrender.com/
```

You should see:

```json
{
  "name": "CodeTrace AI",
  "version": "0.1.0",
  "docs": "/api/docs",
  "health": "/api/health"
}
```

Also verify the health endpoint:

```bash
curl https://codetrace-backend.onrender.com/api/health
```

### 4.6 Common Backend Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: docker` | `docker` Python package imported even in subprocess mode | Check that the code gracefully handles missing Docker. The project already does this — ensure `EXECUTION_MODE=subprocess` is set. |
| `Port binding failed` | Render sets `$PORT` dynamically | Use `--port $PORT` in the start command (already correct above) |
| Application startup crashes | Missing environment variable | Check Render logs for the specific error |
| 502 Bad Gateway | Server took too long to start | Increase the health check grace period in Render dashboard |
| `ruff` not found | Ruff is a Python package, not a system binary | It is installed via `requirements.txt` — verify `pip install` succeeded |

---

## 5. Frontend Deployment (Vercel)

### 5.1 Import Repository into Vercel

1. Go to [https://vercel.com/new](https://vercel.com/new)
2. Click **Import Git Repository**
3. Select your `CodeTrace-AI` repository
4. Configure the project:

| Setting | Value |
|---------|-------|
| **Framework Preset** | `Vite` (auto-detected) |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` (auto-filled) |
| **Output Directory** | `dist` (auto-filled) |

### 5.2 Set Environment Variable

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://codetrace-backend.onrender.com/api` |

This tells the frontend where to find the backend API.

### 5.3 Deploy

Click **Deploy**. Vercel will:

1. Install dependencies (`npm install`)
2. Build the project (`npm run build`)
3. Deploy the `dist` folder to Vercel's CDN

After deployment, your frontend is live at:

```
https://codetrace-ai.vercel.app
```

### 5.4 Verify Frontend

1. Open `https://codetrace-ai.vercel.app`
2. The dark-themed CodeTrace AI editor should load
3. Type Python code, e.g.:

```python
print("hello world")
x = 1 / 0
```

4. Click **Run** — the code should execute and show the error analysis

---

## 6. Environment Variables

| Variable | Required | Example | Used By | Description |
|----------|----------|---------|---------|-------------|
| `EXECUTION_MODE` | Yes | `subprocess` | Backend | Execution backend: `docker` or `subprocess` |
| `HOST` | No | `0.0.0.0` | Backend | Server bind address |
| `PORT` | No | `8000` | Backend | Server port (Render sets this automatically) |
| `ALLOWED_ORIGINS` | Yes | `https://codetrace-ai.vercel.app` | Backend | Comma-separated CORS origins |
| `SANDBOX_IMAGE` | No | `codetrace-sandbox:latest` | Backend | Docker image name (docker mode only) |
| `EXECUTION_TIMEOUT` | No | `5` | Backend | Max execution time in seconds |
| `EXECUTION_MEMORY` | No | `128m` | Backend | Memory limit (docker mode only) |
| `EXECUTION_CPU` | No | `0.5` | Backend | CPU limit (docker mode only) |
| `AI_PROVIDER` | No | `openai` | Backend | AI provider: `openai` or `gemini` |
| `AI_API_KEY` | No | `sk-...` | Backend | API key for AI provider |
| `AI_MODEL` | No | `gpt-4o` | Backend | AI model name |
| `MAX_CODE_SIZE` | No | `65536` | Backend | Max code size in bytes |
| `MAX_INPUT_SIZE` | No | `65536` | Backend | Max stdin size in bytes |
| `MAX_OUTPUT_SIZE` | No | `262144` | Backend | Max output size in bytes |
| `VITE_API_URL` | Yes | `https://codetrace-backend.onrender.com/api` | Frontend | Backend API base URL |

---

## 7. GitHub Auto Deployment

### Vercel (Frontend)

- Every push to `main` triggers an automatic redeployment
- Pull request branches get **Preview Deployments** with unique URLs
- The **Production Deployment** is the `main` branch

### Render (Backend)

- Every push to `main` triggers an automatic redeployment
- Render builds and deploys the `backend/` directory
- No preview deployments on the free tier

### Redeployment on every push

```bash
git add .
git commit -m "Fix something"
git push origin main
# Both Vercel and Render start deploying automatically
```

---

## 8. Domain Configuration

### Default Domains (Free)

| Service | Default Domain |
|---------|---------------|
| Vercel | `https://codetrace-ai.vercel.app` |
| Render | `https://codetrace-backend.onrender.com` |

### Custom Domain (Optional)

**Vercel:**
1. Go to your project → **Settings** → **Domains**
2. Enter your domain (e.g., `codetrace.example.com`)
3. Update your DNS records as instructed by Vercel

**Render:**
1. Go to your Web Service → **Settings** → **Custom Domain**
2. Add your domain
3. Update DNS records

> Free tier on Render supports custom domains with automatic SSL certs.

---

## 9. Troubleshooting

### CORS Errors

```
Access to XMLHttpRequest at 'https://codetrace-backend.onrender.com/api/execute'
from origin 'https://codetrace-ai.vercel.app' has been blocked by CORS policy
```

**Fix:** Update `ALLOWED_ORIGINS` on Render to include your exact Vercel URL:

```
ALLOWED_ORIGINS=https://codetrace-ai.vercel.app
```

Multiple origins (comma-separated):

```
ALLOWED_ORIGINS=https://codetrace-ai.vercel.app,http://localhost:5173
```

### 404 Routes

The frontend is a single-page app (SPA). If you get 404 on direct URL access, ensure Vercel's `vercel.json` is present (it already exists in this project):

```json
{
  "routes": [
    { "handle": "filesystem" },
    { "src": "/.*", "dest": "/index.html" }
  ]
}
```

### 500 Server Errors

Check Render logs:

```bash
# In Render dashboard → Your Service → Logs
```

Common causes:
- Missing `EXECUTION_MODE` environment variable
- `ALLOWED_ORIGINS` not set correctly
- Code execution timeout (default 5 seconds)
- Memory limit exceeded

### Missing Environment Variables

- **Backend missing `EXECUTION_MODE`**: Defaults to `docker`, which tries to use Docker and fails. Always set it to `subprocess` on Render.
- **Frontend missing `VITE_API_URL`**: Defaults to `/api` (Vite proxy for local dev). In production, must be set to the Render backend URL.

### Build Failures

**Frontend:**
- Ensure Vercel root directory is set to `frontend`
- Check `node_modules` cache — Vercel caches it, but sometimes clearing helps

**Backend:**
- Ensure root directory is set to `backend`
- Verify `requirements.txt` is at the root of the specified directory
- If a dependency fails to build (e.g., `docker` package), it's fine — it's not used in `subprocess` mode

### Static Asset Issues

- All assets are bundled by Vite in the `dist` folder
- If images or fonts are missing, verify they are imported correctly in the source code
- The output directory on Vercel must be `dist`

### API Timeout Issues

Render's free tier spins down after 15 minutes of inactivity. The first request after inactivity may take 30–60 seconds to respond (cold start).

**Mitigation:**
- Use a uptime monitoring service (e.g., [cron-job.org](https://cron-job.org) FREE) to ping the health endpoint every 10 minutes
- The health endpoint is lightweight and does not execute user code

---

## 10. Production Checklist

- [ ] **Environment variables configured** — All required vars set on both Vercel and Render
- [ ] **HTTPS enabled** — Vercel and Render provide automatic SSL (enabled by default)
- [ ] **CORS configured** — `ALLOWED_ORIGINS` includes your Vercel domain
- [ ] **EXECUTION_MODE=subprocess** — Set on Render (Docker is unavailable)
- [ ] **Build successful** — Both frontend and backend deploy without errors
- [ ] **API reachable** — `curl https://codetrace-backend.onrender.com/api/health` returns 200
- [ ] **Frontend connected to backend** — The web app loads and code execution works end-to-end
- [ ] **AI configured (optional)** — If using AI, `AI_PROVIDER` and `AI_API_KEY` are set
- [ ] **Timeout configured** — `EXECUTION_TIMEOUT` set appropriately (default 5s is fine)
- [ ] **API docs accessible** — `/api/docs` opens the Swagger UI
- [ ] **Uptime monitor configured** — Optional, but prevents cold-start delays

---

## 11. Maintenance

### Redeploy

Triggered automatically on every push to `main`. To manually redeploy:

- **Vercel**: Dashboard → Project → Deployments → ⋮ → Redeploy
- **Render**: Dashboard → Web Service → Manual Deploy → Deploy latest commit

### View Logs

- **Vercel**: Dashboard → Project → Deployments → Click deployment → Logs
- **Render**: Dashboard → Web Service → Logs (streaming)

### Roll Back Deployments

- **Vercel**: Dashboard → Deployments → Find a working deployment → ⋮ → Promote to Production
- **Render**: Dashboard → Web Service → Manual Deploy → Deploy existing commit → Select a previous commit

### Update Environment Variables

- **Vercel**: Dashboard → Project → Settings → Environment Variables
- **Render**: Dashboard → Web Service → Environment

After changing env vars, a manual redeploy may be required.

### Monitor Usage Limits

- **Vercel**: Dashboard → Usage (100 GB bandwidth, 6000 build minutes/month free)
- **Render**: Dashboard → Account → Usage (750 hours/month = 1 service always-on; 2 services = ~375 hours each)

---

## 12. Free Tier Limitations

### Vercel (Frontend)

| Limit | Value |
|-------|-------|
| Bandwidth | 100 GB / month |
| Build minutes | 6,000 min / month |
| Serverless function execution | 100 GB-hours / month |
| Concurrent builds | 1 |
| Custom domains | Unlimited (with SSL) |
| Team members | Unlimited |
| **Sleep / inactivity** | **Always on** (no spin-down) |

### Render (Backend)

| Limit | Value |
|-------|-------|
| Build minutes | 500 min / month |
| Bandwidth | 100 GB / month |
| RAM | 512 MB |
| CPU | Shared (0.1 vCPU approx) |
| Storage | 1 GB (ephemeral) |
| Custom domains | Yes (with automatic SSL) |
| **Sleep / inactivity** | **Spins down after 15 min of inactivity** |
| Cold start | ~30-60 seconds after sleep |
| Always-on | $7/month to disable sleeping |

> **Important:** Because Render's free service spins down after inactivity, the first API call after a period of no traffic will be slow (~30-60s cold start). The health check endpoint responds quickly even on cold start.

### No Database Required

Since the project is stateless, there are no database limitations to worry about.

---

## 13. Cost Breakdown

| Service | Plan | Features | Cost |
|---------|------|----------|------|
| GitHub | Free | Unlimited private repos, CI/CD | $0 |
| Vercel | Free (Hobby) | 100 GB bandwidth, SSL, custom domains | $0 |
| Render | Free | 512 MB RAM, 500 build min/month, 100 GB bandwidth | $0 |
| OpenAI API (optional) | Pay-as-you-go | ~$0.01-0.03 per explanation if enabled | ~$0 |
| Uptime monitor (optional) | Free (cron-job.org) | Pings every 10 min to prevent cold starts | $0 |
| **Total** | | | **$0 / month** |

---

## 14. Repository-Specific Notes

### Project Structure

```
codetrace/
├── frontend/                      # React + Vite SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── CodeEditor.jsx     # Monaco Editor wrapper
│   │   │   ├── ExecutionTimeline.jsx
│   │   │   ├── VariableInspector.jsx
│   │   │   ├── OutputConsole.jsx
│   │   │   ├── ErrorCard.jsx
│   │   │   └── AIExplanation.jsx
│   │   ├── pages/
│   │   │   └── DebuggerPage.jsx   # Main page
│   │   ├── services/
│   │   │   └── api.js             # Axios API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── vercel.json                # SPA routing config for Vercel
│   └── tailwind.config.js
│
├── backend/                       # FastAPI backend
│   ├── app/
│   │   ├── main.py                # App entry point, CORS, routers
│   │   ├── config.py              # Settings from env vars
│   │   ├── api/
│   │   │   ├── execute.py         # POST /api/execute, GET /api/health
│   │   │   ├── lint.py            # POST /api/lint
│   │   │   └── fix.py             # POST /api/fix
│   │   ├── execution/
│   │   │   ├── executor.py
│   │   │   ├── docker_backend.py  # Docker sandbox (local only)
│   │   │   └── subprocess_backend.py  # Subprocess (Render)
│   │   ├── models/
│   │   │   ├── requests.py        # Pydantic request schemas
│   │   │   └── responses.py       # Pydantic response schemas
│   │   ├── tracing/
│   │   ├── analysis/
│   │   └── ai/
│   ├── requirements.txt
│   ├── Dockerfile                 # Render Docker deployment
│   └── tests/
│
├── sandbox/                       # Docker sandbox image
│   ├── Dockerfile
│   └── runner.py
│
├── .env.example                   # All environment variables documented
├── render.yaml                    # Render Blueprint (auto-deploy config)
├── deploy.sh                      # Helper deployment script
└── docker-compose.yml             # Local dev with Docker
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Root info |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/execute` | Execute Python code with tracing |
| `POST` | `/api/lint` | Run Ruff linting |
| `POST` | `/api/fix` | Generate fix proposals |
| `GET` | `/api/docs` | Swagger UI |
| `GET` | `/api/redoc` | ReDoc UI |

### Versions

| Dependency | Version |
|------------|---------|
| Python | 3.12 (from `python:3.12-slim`) |
| React | ^18.3.1 |
| Vite | ^5.3.1 |
| FastAPI | ^0.111.0 |
| Uvicorn | ^0.30.0 |
| Node.js | 18+ (required by Vite 5) |

### Copy-Paste Quick Start

**Local development:**
```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (another terminal)
cd frontend
npm install
npm run dev
```

**Deploy to production:**
```bash
# Push to GitHub (triggers auto-deploy)
git add .
git commit -m "Deploy"
git push origin main
```

Then configure the env vars on Vercel and Render as described in sections 4 and 5.

### Render Blueprint

The existing `render.yaml` in the repository root can be used for one-click deployment via Render Blueprint:

```yaml
services:
  - type: web
    name: codetrace-backend
    env: docker
    rootDir: backend
    dockerfilePath: backend/Dockerfile
    plan: free
    healthCheckPath: /api/health
    envVars:
      - key: EXECUTION_MODE
        value: subprocess
      - key: ALLOWED_ORIGINS
        value: https://codetrace-ai.vercel.app
```

However, **Render Blueprint with Docker uses the Docker runtime**, which counts against different free tier limits. The native Python runtime (section 4) is recommended for the free tier.

### Vercel Configuration

The `vercel.json` at `frontend/vercel.json` is already configured for SPA fallback routing:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "routes": [
    { "handle": "filesystem" },
    { "src": "/.*", "dest": "/index.html" }
  ]
}
```
