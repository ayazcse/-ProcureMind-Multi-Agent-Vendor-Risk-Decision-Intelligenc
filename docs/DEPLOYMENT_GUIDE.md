# Deployment Guide

## Status check (honest)

Docker build configuration is written and reviewed (`backend/Dockerfile`,
`frontend/Dockerfile`, `docker-compose.yml`, `docker-compose.postgres.yml`)
but **`docker compose up` was not executed in this sandboxed build
environment** (no Docker daemon available here). Review the configs below
before relying on them for a live demo, and budget time to debug on first
run — that's normal for any Docker setup not yet exercised.

## Local Docker Compose (SQLite, zero external services)

```bash
cd ProcureMind
cp backend/.env.example backend/.env
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173 (proxies `/api` to the backend container)

## Local Docker Compose with PostgreSQL

```bash
cp backend/.env.example backend/.env
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

This adds a `postgres:16-alpine` container and points `DATABASE_URL` at
it. Default credentials (change for anything beyond local testing):
`procuremind` / `procuremind` / db `procuremind`.

## Free / low-cost hosting options (disclosed costs and limits)

**Backend (FastAPI + SQLite or Postgres):**
- **Railway** — free trial credits, then usage-based (~$5/mo minimum for
  always-on). Easiest Docker deploy path; supports a managed Postgres
  add-on if you don't want SQLite in production.
- **Render** — free tier available for web services, but free-tier
  services **spin down after 15 minutes of inactivity** and cold-start on
  the next request (several seconds delay) — fine for a portfolio demo
  link, not for a live interview unless you ping it beforehand. Managed
  Postgres free tier expires after 90 days.
- **Fly.io** — free allowance covers small always-on instances; requires
  a credit card on file even for free usage.

**Frontend (static React build):**
- **Vercel** or **Netlify** — both have generous free tiers for static
  sites, effectively free for a portfolio project. Point either at
  `frontend/`, build command `npm run build`, output dir `dist`.
- Set the frontend's API target via `VITE_API_URL` at build time (Vercel/
  Netlify environment variable) to your deployed backend's URL, since the
  Nginx-proxy approach in `docker-compose.yml` only applies when frontend
  and backend share a Docker network.

**Important disclosure:** SQLite is a single file on local disk — most
free-tier hosts (Render, Railway's default filesystem) do **not**
guarantee persistent disk storage across deploys/restarts unless you
attach a persistent volume (often a paid feature) or switch to the
Postgres override above with the host's managed Postgres add-on. For
anything beyond a short demo session, use Postgres in production.

## Environment variables needed in production

Copy `backend/.env.example`, and at minimum set:
```
DATABASE_URL=<your production database URL>
SECRET_KEY=<a real random string, not the dev default>
CORS_ORIGINS=<your deployed frontend URL>
```
Add `LLM_PROVIDER` + the matching API key only if you want LLM-augmented
explanations live (optional — see README.md).

## Deployment verification checklist

Before telling an interviewer "it's deployed," confirm:
- [ ] `GET /api/health` returns `200` on the deployed backend URL
- [ ] The deployed frontend successfully calls the deployed backend (check
      browser dev tools network tab for CORS errors)
- [ ] `POST /api/requests/{id}/evaluate` completes on the deployed
      instance, not just locally — cold-start timeouts on free tiers can
      cause this specific endpoint to time out since it's the slowest call
- [ ] Data persists across a backend restart (if using SQLite without a
      persistent volume, it will NOT — see disclosure above)

**This checklist was not run against a live deployment in this build** —
do not claim "deployed and verified" in an interview until you've actually
walked through it yourself.
