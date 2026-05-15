# ContextNews — Comprehensive Deployment Guide

Backend → **Render** (free web service). Frontend → **Vercel** (free).
Both pull from a **GitHub** repo. Total cost: $0.

> Read the **two caveats** in §6 before you start — they affect whether your
> data survives and how fast the app feels on free tier.

---

## 0. Prerequisites (one-time)

- Accounts (free): [github.com](https://github.com), [render.com](https://render.com), [vercel.com](https://vercel.com).
  Sign up for Render and Vercel **with your GitHub account** — it makes repo
  connection one click.
- Git installed locally (already is — repo is committed).
- Your API keys are in `backend/.env` locally. **They are NOT in Git**
  (`.gitignore` excludes `.env`). You will paste them into the Render
  dashboard by hand in §2. Never commit them.

Values you'll need (from your local `backend/.env`, do not share publicly):

```
NEWSAPI_KEY      = (the value in backend/.env)
GEMINI_API_KEY   = (the value in backend/.env)
```

---

## 1. Push code to GitHub

Create an **empty** repo at <https://github.com/new> — name it `contextnews`,
no README/gitignore/license (the repo already has them).

Then locally:

```powershell
cd C:\Users\manha\ContextNews
git remote add origin https://github.com/<YOUR_USERNAME>/contextnews.git
git branch -M main
git push -u origin main
```

If `git push` asks for credentials, use your GitHub username and a
**Personal Access Token** as the password (github.com → Settings → Developer
settings → Personal access tokens → Tokens (classic) → Generate, scope `repo`).

Verify: refresh the GitHub repo page — you should see `backend/`, `frontend/`,
`render.yaml`, `DEPLOY.md`. Confirm there is **no `.env`** anywhere in the repo.

---

## 2. Deploy the backend to Render

The repo root has `render.yaml`, so Render can deploy it as a **Blueprint**.

1. Render Dashboard → **New +** → **Blueprint**.
2. Connect GitHub, select the `contextnews` repo → **Connect**.
3. Render parses `render.yaml` and shows a service named **`contextnews-api`**.
4. It will ask for the env vars marked `sync: false`. Fill them:

   | Key | Value |
   |---|---|
   | `NEWSAPI_KEY` | *(from your local `backend/.env`)* |
   | `GEMINI_API_KEY` | *(from your local `backend/.env`)* |
   | `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` |

   These are already set for you by `render.yaml` (don't change):
   `GEMINI_MODEL=gemini-2.5-flash`, `GEMINI_FALLBACK_MODEL=gemini-flash-latest`,
   `RSS_FETCH_INTERVAL_HOURS=2`, `NEWSAPI_FETCH_INTERVAL_HOURS=6`,
   `DAILY_ANALYSIS_LIMIT=10`, `JWT_SECRET` (auto-generated).

5. Click **Apply** / **Create**. First build takes ~3–6 min (installs
   `requirements.txt`, including `google-generativeai`).
6. When live, copy the service URL, e.g.
   `https://contextnews-api.onrender.com`. **This is your BACKEND_URL.**

**Smoke-test the backend** (browser or curl):

```
https://<BACKEND_URL>/api/health
```
Expected JSON: `{"status":"ok","newsapi_configured":true,"gemini_configured":true}`
Also open `https://<BACKEND_URL>/docs` — the FastAPI Swagger UI should load.

If `newsapi_configured` or `gemini_configured` is `false`, the env var didn't
save — fix in Render → service → **Environment** → save (auto-redeploys).

---

## 3. Deploy the frontend to Vercel

1. Vercel → **Add New…** → **Project** → import the `contextnews` repo.
2. **Root Directory**: click **Edit** → select **`frontend`**. (Critical —
   the repo is a monorepo; Vercel must build only `frontend/`.)
3. Framework Preset auto-detects **Vite** (from `frontend/vercel.json`).
   Leave build command (`npm run build`) and output (`dist`) as detected.
4. **Environment Variables** → add:

   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://<BACKEND_URL>` *(your Render URL, no trailing slash)* |

   ⚠️ Vite inlines env vars **at build time**. If you change `VITE_API_URL`
   later you must **redeploy** the frontend, not just edit the var.
5. **Deploy**. ~1–2 min.
6. Copy the production URL, e.g. `https://contextnews.vercel.app`.
   **This is your FRONTEND_URL.**

---

## 4. Final CORS wiring (do not skip)

The browser will block all API calls until the backend allows the Vercel
origin.

1. Render → `contextnews-api` → **Environment** → edit `ALLOWED_ORIGINS` to:

   ```
   http://localhost:5173,http://localhost:3000,https://<FRONTEND_URL>
   ```
   (exact scheme + host, **no trailing slash**, no path, comma-separated, no spaces)

2. **Save Changes** → Render auto-redeploys (~1–2 min).

> Vercel **preview** deployments get unique URLs (`contextnews-git-*.vercel.app`)
> that won't be in this list and will hit CORS errors. Only the **production**
> domain works. If you need previews too, ask and I'll switch the backend to
> `allow_origin_regex` for `*.vercel.app`.

---

## 5. End-to-end test

Open your **FRONTEND_URL** in a browser. Open DevTools → Network/Console.

| Check | How | Pass criteria |
|---|---|---|
| Frontend ↔ backend | Load the site | No CORS errors in console; lands on Auth screen |
| Signup | Create account `you@example.com` / `secret1` | Redirects to onboarding |
| Onboarding | Complete 3 screens, Finish | Lands on Home |
| News fetch | Click **Refresh** | Cards appear (RSS + NewsAPI); ~250+ articles |
| Ranking | Look at Top tab | IDSA/PIB-sourced items rank high |
| Gemini | Open a card → **Run AI deep analysis** | Summary + causal timeline + lecturette render; "X analyses remaining" decrements |
| Enrichment | (in the analysis) | Timeline has deep historical roots (years back) |
| Login | Log out → log back in | Returns to Home, onboarded |
| Signals | 👎 a card | Card disappears; stays gone in Personalised |

Backend-only quick check (no browser):
```bash
curl https://<BACKEND_URL>/api/health
curl -X POST https://<BACKEND_URL>/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"t@t.com","password":"secret1"}'
```

---

## 6. Free-tier caveats — READ THIS

**(a) Render free web services sleep after 15 min idle.**
First request after sleep takes ~50s (cold start). The in-process scheduler
(APScheduler) resets on every wake, so automated 2h/6h fetching is not
reliable on free tier — use the **Refresh** button, or upgrade Render, or add
an external cron (e.g. cron-job.org) hitting `/api/health` to keep it warm.

**(b) Render free has an ephemeral filesystem.**
The SQLite file (`contextnews.db`) is **wiped on every deploy, restart, and
sleep**. Users, articles, analyses, and learned signals do **not** persist.
Fine for a demo/portfolio. For real persistence (still free) use external
Postgres:

1. Create a free Postgres at [neon.tech](https://neon.tech) (or Supabase).
   Copy its connection string.
2. In `backend/requirements.txt` add: `psycopg2-binary==2.9.10`
3. Commit & push (`git add -A && git commit -m "add postgres driver" && git push`).
4. Render → service → Environment → add
   `DATABASE_URL = postgresql+psycopg2://<user>:<pass>@<host>/<db>?sslmode=require`
5. Save → redeploy. Tables auto-create on startup (`init_db()`).

(No code change needed — `config.py`/`database.py` already read `DATABASE_URL`.)

---

## 7. Post-deploy hardening (recommended)

- **Rotate keys** if they were ever pasted into chat: regenerate
  `NEWSAPI_KEY` (newsapi.org) and `GEMINI_API_KEY` (aistudio.google.com),
  update them in Render → Environment.
- Keep `ALLOWED_ORIGINS` to exactly localhost + your real Vercel domain —
  don't use `*`.
- `JWT_SECRET` is Render-generated and never leaves the dashboard — good.
- To use the spec's `gemini-2.0-flash`, enable billing on Google AI and set
  `GEMINI_MODEL=gemini-2.0-flash` in Render. Until then `gemini-2.5-flash`
  (preset) is correct — the free tier has zero quota for 2.0-flash.

---

## 8. Redeploys

- **Code change**: `git push` → Render and Vercel auto-redeploy from `main`.
- **Backend env change**: edit in Render dashboard → auto-redeploy.
- **`VITE_API_URL` change**: edit in Vercel → **must trigger a redeploy**
  (Deployments → ⋯ → Redeploy) because Vite bakes it in at build time.

---

## Quick reference

| Thing | Value |
|---|---|
| BACKEND_URL | `https://contextnews-api.onrender.com` *(yours after §2)* |
| FRONTEND_URL | `https://contextnews.vercel.app` *(yours after §3)* |
| Backend health | `BACKEND_URL/api/health` |
| API docs | `BACKEND_URL/docs` |
| Render env to set | `NEWSAPI_KEY`, `GEMINI_API_KEY`, `ALLOWED_ORIGINS` |
| Vercel env to set | `VITE_API_URL` |
