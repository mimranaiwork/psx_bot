# Deploying the PSX AI Insights Bot

Two pieces: the FastAPI backend (`api/`) and the React frontend (`web/`).
Deploy the backend first — the frontend needs its URL.

The backend persists to a SQLite file (`data/psx_bot.db`) and pickled
model files (`data/models/`). **Without a persistent disk/volume, every
redeploy wipes that data** and you're back to zero loaded symbols. Both
guides below cover attaching one.

## 1. Backend — Render (config-as-code, `render.yaml` already in the repo)

1. [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint** → connect the `psx_bot` GitHub repo. Render reads `render.yaml` from the repo root automatically.
2. It provisions a web service on the **Starter** plan (Render's free tier doesn't support persistent disks, and this app needs one) with a 1GB disk mounted at `data/`.
3. Set the `ANTHROPIC_API_KEY` env var in the Render dashboard if you want the live LLM rationale layer (optional — falls back to a template without it, per `models/llm_synthesis.py`).
4. Leave `ALLOWED_ORIGINS` blank for now — come back and set it after the frontend is deployed (step 3 below).
5. Deploy. Your backend URL will be `https://psx-ai-bot-api.onrender.com` (or whatever Render assigns).
6. Sanity check: `curl https://<your-render-url>/health` → `{"status":"ok"}`.

## 1b. Backend — Railway (alternative)

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → pick `psx_bot`. Railway auto-detects Python via `requirements.txt`/`runtime.txt` and reads `railway.json`/`Procfile` for the start command.
2. **Attach a volume** (Settings → Volumes → New Volume) mounted at `/app/data` — this isn't expressible in `railway.json`, it's a dashboard/CLI step (`railway volume create`).
3. Set `ANTHROPIC_API_KEY` under Variables if wanted (optional, same as above).
4. Deploy. Railway gives you a `*.up.railway.app` URL (or generate a custom domain under Settings → Networking).
5. Sanity check: `curl https://<your-railway-url>/health` → `{"status":"ok"}`.

## 2. Load some data before using the UI

A fresh deploy has an empty database. Either:
- Hit the pipeline endpoints from the deployed API (e.g. `POST /symbols/OGDC/load-prices` with `{"yf_ticker": "OGDC.KA"}`) via `curl` or the web portal's own pipeline controls once it's live, or
- Load a batch the same way this session did locally, pointed at the deployed API instead of localhost.

## 3. Frontend — Vercel

1. [vercel.com](https://vercel.com) → **Add New** → **Project** → import the `psx_bot` repo.
2. Set **Root Directory** to `web` (Vercel auto-detects the Vite framework preset once you do; `web/vercel.json` handles the build command, output dir, and SPA routing rewrites for React Router).
3. Add an environment variable: `VITE_API_BASE_URL` = your Render/Railway URL from step 1 (no trailing slash).
4. Deploy. Vercel gives you a `*.vercel.app` URL.

## 4. Close the loop: lock down CORS

Go back to Render/Railway and set `ALLOWED_ORIGINS` to your Vercel URL
(e.g. `https://psx-bot.vercel.app`) — comma-separated if you have more
than one (e.g. a preview URL too). Redeploy the backend for it to take
effect. `api/main.py` reads this env var alongside the hardcoded
localhost dev origins, so local development keeps working unchanged.

## Gotchas

- **SQLite + multiple instances don't mix.** If you scale the backend to more than one instance on Render/Railway, they'd each see a different (or locked) SQLite file. Fine at one instance; if you need to scale out, migrate to Postgres first (the schema in `db/schema.sql` is plain SQL, not SQLite-specific syntax beyond `AUTOINCREMENT`).
- **Free tiers sleep.** Render's free web services (not used here, since disks need Starter) and some Railway free-tier behavior spin down on idle — the first request after a while will be slow (cold start). Not an issue on Render Starter, which doesn't sleep.
- **`ANTHROPIC_API_KEY` is optional everywhere.** Without it, `models/llm_synthesis.py` transparently falls back to the deterministic template rationale — nothing breaks.
