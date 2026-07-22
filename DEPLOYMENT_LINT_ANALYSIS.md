# Deployment Lint Analysis — "LINT UNAVAILABLE" Root Cause Report

---

## Root Cause

The `"LINT UNAVAILABLE"` message is displayed when the frontend's `POST /api/lint` request fails. Multiple independent issues contribute, but the **primary root cause** is that the frontend cannot reach the backend API in production.

**The chain of failure:**

1. The frontend defaults `VITE_API_URL` to `"/api"` (relative path) when the environment variable is not set
2. Vercel's `vercel.json` routes **every path** (including `/api/lint`) to `index.html` (SPA fallback)
3. Axios receives HTML instead of JSON, throws a parse error
4. The `useLiveLint` hook's catch block sets `lintStatus` to `"unavailable"`
5. `LiveStatus` renders `"LINT UNAVAILABLE"` in gray

Even when `VITE_API_URL` IS set correctly, a **secondary root cause** guarantees the same symptom on Render's free tier: the 5-second lint API timeout is too short to survive Render's 30-60 second cold start.

---

## Evidence

### Issue 1: `VITE_API_URL` Not Configured on Vercel

**File:** `frontend/src/services/lintApi.js` — line 3
```javascript
const BACKEND_URL = import.meta.env.VITE_API_URL || '/api';
```

- If `VITE_API_URL` is not set in the Vercel dashboard, this falls back to `'/api'`
- All lint requests go to `https://codetrace-ai.vercel.app/api/lint` (same origin)

**File:** `frontend/vercel.json` — lines 5-8
```json
"routes": [
    { "handle": "filesystem" },
    { "src": "/.*", "dest": "/index.html" }
]
```

- Every unmatched route returns `index.html`
- There is **no rewrite or proxy** for `/api/*`
- The response is a full HTML document

**Result:** Axios receives HTML, cannot parse it as JSON, and throws an error.

### Issue 2: 5-Second Lint Timeout vs Render Cold Start

**File:** `frontend/src/services/lintApi.js` — line 7
```javascript
const lintClient = axios.create({
  baseURL: BACKEND_URL,
  timeout: 5000,  // 5 seconds
  headers: { 'Content-Type': 'application/json' },
});
```

- 5 seconds is too short for Render's free tier cold start (~30-60s)
- Compare with the execute endpoint timeout (15 seconds):

**File:** `frontend/src/services/api.js` — line 8
```javascript
const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 15000,  // 15 seconds
  headers: { 'Content-Type': 'application/json' },
});
```

- The execute endpoint (15s timeout) may survive a cold start while lint (5s timeout) will not
- This explains why the user might see "Analyze" work but lint show "UNAVAILABLE"

### Issue 3: Backend Hardcodes `ruff_available=True`

**File:** `backend/app/api/lint.py` — line 56
```python
return LintResponse(
    status="success",
    diagnostics=diagnostics,
    ruff_available=True,  # HARDCODED — always True regardless of actual ruff status
)
```

- The frontend receives `ruff_available: true` even when Ruff fails silently
- This prevents the frontend from distinguishing "ruff is not installed" from other errors
- The `check_ruff_available()` function is only called for empty code (line 46), never for real lint requests

### Issue 4: `ruffAvailable` Frontend State Is Dead Code

**File:** `frontend/src/hooks/useLiveLint.js` — lines 17, 48, 97
```javascript
const [ruffAvailable, setRuffAvailable] = useState(true);  // line 17
setRuffAvailable(result.ruff_available !== false);           // line 48
// ...
return {
    diagnostics,
    lintStatus,
    ruffAvailable,  // line 97 — returned but never consumed
    runLint,
};
```

**File:** `frontend/src/pages/DebuggerPage.jsx` — line 29
```javascript
const { diagnostics, lintStatus, runLint } = useLiveLint(code);
// Note: ruffAvailable is NOT destructured — it is dead code
```

### Issue 5: `unavailable` Status Is Only Set on HTTP/Network Errors

**File:** `frontend/src/hooks/useLiveLint.js` — lines 57-65
```javascript
} catch (err) {
    if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') return;
    if (currentId !== requestIdRef.current) return;

    setDiagnostics([]);
    setLintStatus('unavailable');  // <-- ONLY path to "LINT UNAVAILABLE"
    setRuffAvailable(false);
}
```

The `'unavailable'` status is **exclusively** set in the catch block. It is never triggered by the response body (e.g., from `ruff_available: false`).

### Issue 6: CORS Configuration Defaults to Localhost

**File:** `backend/app/config.py` — lines 22-25
```python
ALLOWED_ORIGINS: str = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173",  # Default — NOT valid in production
)
```

- If the user deploys to Render without setting `ALLOWED_ORIGINS`, it defaults to `http://localhost:5173`
- The production Vercel URL will be blocked by CORS
- This causes ALL API calls (lint AND execute) to fail with network errors

---

## Required Fixes

### Fix 1: Set `VITE_API_URL` on Vercel (Highest Priority)

In the Vercel dashboard → Project → Settings → Environment Variables, add:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://codetrace-backend.onrender.com/api` |

### Fix 2: Increase Lint Timeout

**File:** `frontend/src/services/lintApi.js` — line 7

Change:
```javascript
timeout: 5000,
```
To:
```javascript
timeout: 30000,
```

### Fix 3: Return Actual `ruff_available` From Backend

**File:** `backend/app/api/lint.py` — line 56

Change:
```python
ruff_available=True,
```
To:
```python
ruff_available=check_ruff_available(),
```

### Fix 4: Report `ruff_available` in the Frontend When Ruff Is Unavailable

**File:** `frontend/src/hooks/useLiveLint.js` — lines 50-55

After:
```javascript
const diags = result.diagnostics || [];
setDiagnostics(diags);
setRuffAvailable(result.ruff_available !== false);
```

Add logic to show `'unavailable'` when `ruff_available` is false:
```javascript
if (result.ruff_available === false) {
    setLintStatus('unavailable');
    return;
}
```

### Fix 5: Update `ALLOWED_ORIGINS` on Render

In the Render dashboard, set:

| Key | Value |
|-----|-------|
| `ALLOWED_ORIGINS` | `https://codetrace-ai.vercel.app` |

### Fix 6: Add API Proxy to `vercel.json`

**File:** `frontend/vercel.json` — add a rewrite before the SPA fallback:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "routes": [
    { "src": "/api/(.*)", "dest": "https://codetrace-backend.onrender.com/api/$1" },
    { "handle": "filesystem" },
    { "src": "/.*", "dest": "/index.html" }
  ]
}
```

> **Note:** This approach exposes the backend URL. It is simpler and more reliable to set `VITE_API_URL` instead.

---

## Deployment Fixes

| Step | Action | Where |
|------|--------|-------|
| 1 | Set `VITE_API_URL` to Render backend URL | Vercel dashboard → Environment Variables |
| 2 | Set `ALLOWED_ORIGINS` to Vercel frontend URL | Render dashboard → Environment Variables |
| 3 | Set `EXECUTION_MODE` to `subprocess` | Render dashboard → Environment Variables |
| 4 | Redeploy both frontend and backend | Trigger via `git push` or dashboard |

---

## Verification Steps

### Local Verification

```bash
# 1. Test lint endpoint directly
curl -s -X POST http://localhost:8000/api/lint \
  -H "Content-Type: application/json" \
  -d '{"code": "x = 1\nprint(y)"}' | python3 -m json.tool
# Expected: status "success", diagnostics with F821, ruff_available true

# 2. Test with empty code
curl -s -X POST http://localhost:8000/api/lint \
  -H "Content-Type: application/json" \
  -d '{"code": ""}' | python3 -m json.tool
# Expected: status "success", empty diagnostics, ruff_available true/false

# 3. Simulate production environment locally
cd frontend && VITE_API_URL="" npm run build
# Verify build output references '/api' as fallback
grep -r '"api"' dist/
```

### Production Verification

```bash
# 1. Verify backend health
curl https://codetrace-backend.onrender.com/api/health

# 2. Verify lint endpoint
curl -X POST https://codetrace-backend.onrender.com/api/lint \
  -H "Content-Type: application/json" \
  -d '{"code": "x = 1\nprint(y)"}'

# 3. Open the deployed frontend URL in a browser
# Open https://codetrace-ai.vercel.app
# Type Python code — lint status should show "LIVE" or "CHECKING"
# The initial code has an undefined variable — should show "1 ISSUE"

# 4. Check browser DevTools → Network tab
# Verify POST /api/lint returns HTTP 200 with valid JSON
```

---

## Confidence Level

| Issue | Likelihood | Confidence | Impact |
|-------|-----------|------------|--------|
| `VITE_API_URL` not set on Vercel | **High** — most common deployment mistake | 90% | Lint and all API calls fail |
| 5s timeout vs cold start | **High** — guaranteed on first access | 85% | Lint fails until backend is warm |
| `ruff_available=True` hardcoded | **Certain** — verified in source | 100% | Masks ruff availability issues |
| `ruffAvailable` dead code | **Certain** — verified in source | 100% | No impact on current behavior |
| `ALLOWED_ORIGINS` default to localhost | **Medium** — depends on user config | 70% | All API calls fail in prod |

**Most probable primary cause:** `VITE_API_URL` is missing or misconfigured on Vercel, causing all API requests to hit the SPA origin instead of the Render backend.

**Most probable secondary cause:** Even when `VITE_API_URL` is correct, the 5-second lint timeout is insufficient for Render's free tier cold start, causing the first several lint requests to fail with timeout errors.
