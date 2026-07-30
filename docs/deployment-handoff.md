# Deployment handoff

The application has two runtime components and both must be deployed:

1. `frontend/`: the Vite/React interface.
2. `backend/`: the FastAPI planning, data, chat and report API.

A frontend-only Vercel deployment can render the interface but cannot analyze a
sample profile. The button calls `POST /api/v1/recommendations`, so a reachable
FastAPI deployment is required.

## Recommended production layout

Deploy the backend first with the repository `Dockerfile` on a persistent
container platform. Then deploy `frontend/` to Vercel and connect it to that
backend.

### Backend

Required checks:

```text
GET /api/health
GET /ready
GET /api/v1/demo/default-request
POST /api/v1/recommendations
```

Recommended environment variables:

```text
AQ_ENV=production
AQ_CORS_ORIGINS=https://demo-ui-aof.vercel.app
AQ_MARKET_DATA_AUTO_REFRESH=false
LLM_PROVIDER=ollama
OLLAMA_MODEL=gpt-oss:120b
OLLAMA_BASE_URL=https://ollama.com/api
OLLAMA_API_KEY=<secret configured on the backend platform>
```

For a public demonstration without accounts:

```text
AQ_AUTH_REQUIRED=false
AQ_ALLOW_REGISTRATION=false
```

For an authenticated deployment, set `AQ_AUTH_REQUIRED=true`, provide a strong
`AQ_AUTH_SECRET`, and use persistent PostgreSQL through `DATABASE_URL`.

### Vercel frontend

Project settings:

```text
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
```

Environment variable:

```text
VITE_API_BASE_URL=https://<public-fastapi-domain>
```

Do not append `/api` and do not add a trailing slash. Redeploy the frontend
after changing a `VITE_*` variable because Vite embeds it at build time.

## Acceptance check

After both deployments are ready:

1. `https://<backend>/api/health` returns HTTP 200.
2. The frontend header no longer shows `API CHƯA KẾT NỐI`.
3. Click `Dùng hồ sơ mẫu`.
4. The recommendation request returns HTTP 200 and displays three scenarios.
5. Open the browser network panel and confirm API calls target the backend
   origin configured by `VITE_API_BASE_URL`.

No API key belongs in Git or in a `VITE_*` variable. LLM keys are backend-only
secrets.
