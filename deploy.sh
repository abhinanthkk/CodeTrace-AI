#!/bin/bash
# CodeTrace AI — Deployment Script
# Run this after setting up Cloudflare and Render accounts.

set -e

echo "=== CodeTrace AI Deployment ==="
echo ""

# ── Frontend: Cloudflare Pages ──────────────────────────────────────────
echo "📦 Building frontend..."
cd frontend

# Set the backend URL before building.
# Replace with your actual Render backend URL after deploying it.
if [ -z "$VITE_API_URL" ]; then
  echo ""
  echo "⚠️  VITE_API_URL not set."
  echo "   The build will use localhost — update it after deploying the backend."
  echo "   Example: export VITE_API_URL=https://codetrace-backend.onrender.com/api"
  echo ""
fi

npm run build

echo ""
echo "🚀 Deploying frontend to Cloudflare Pages..."
echo ""
echo "   Option A — Dashboard (easiest):"
echo "   1. Go to https://dash.cloudflare.com/pages"
echo "   2. Connect your GitHub repo (abhinanthkk/CodeTrace-AI)"
echo "   3. Settings:"
echo "      - Framework preset: Vite"
echo "      - Root directory: frontend"
echo "      - Build command: npm run build"
echo "      - Output directory: dist"
echo "      - Env var: VITE_API_URL = <your-render-backend-url>/api"
echo ""
echo "   Option B — wrangler CLI:"
echo "   npx wrangler pages publish dist --project-name=codetrace-ai"
echo ""

# ── Backend: Render ─────────────────────────────────────────────────────
echo "🔧 Backend deployment via Render Blueprint..."
echo ""
echo "   1. Go to https://dashboard.render.com"
echo "   2. Click 'New' → 'Blueprint'"
echo "   3. Connect your GitHub repo (abhinanthkk/CodeTrace-AI)"
echo "   4. Render auto-detects render.yaml and deploys"
echo ""
echo "   Or deploy manually:"
echo "   - New Web Service → Docker"
echo "   - Repo: abhinanthkk/CodeTrace-AI"
echo "   - Dockerfile: backend/Dockerfile"
echo "   - Env vars:"
echo "     EXECUTION_MODE=subprocess"
echo "     ALLOWED_ORIGINS=https://codetrace-ai.pages.dev"
echo ""

echo "=== Done ==="
echo "After both are deployed, update ALLOWED_ORIGINS on Render"
echo "with your Cloudflare Pages URL."
