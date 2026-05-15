# ContextNews

Personalised, AI-analysed defence & current-affairs news for Indian armed forces
aspirants. React + Tailwind frontend, FastAPI + SQLite backend, multi-source
ingestion (9 RSS feeds + NewsAPI + GDELT context), Gemini 2.0 Flash deep analysis.
Zero running cost — all free tiers.

## Layout

```
ContextNews/
├── backend/      FastAPI, SQLite, RSS+NewsAPI+GDELT, auth, rate limiting
├── frontend/     React (Vite) + Tailwind, dark-mode UI
├── render.yaml   Backend deploy (Render)
└── frontend/vercel.json  Frontend deploy (Vercel)
```

## Local setup

### Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# copy .env.example -> .env and fill keys
uvicorn main:app --reload --port 8000
```
`backend/.env`: `NEWSAPI_KEY`, `GEMINI_API_KEY`, `JWT_SECRET` (long random),
`DAILY_ANALYSIS_LIMIT` (default 10). Docs at http://localhost:8000/docs

### Frontend
```powershell
cd frontend
npm install
npm run dev
```
Runs at http://localhost:5173 (`frontend/.env` -> `VITE_API_URL`).

## How it works

- **Ingestion:** RSS feeds (BBC, Reuters, Al Jazeera, The Hindu, Indian Express,
  PIB, Indian Defence Review, The Print Defence, ANI, IDSA, Hindustan Times,
  NDTV) every 2h with browser headers; bad feeds are logged and skipped (never
  crash). NewsAPI reserved for 4 search queries every 6h. De-duplicated by
  **token-set Jaccard similarity** (≥ 0.6).
- **GDELT** supplies related prior coverage to ground Gemini's causal timeline,
  plus a one-shot **12-month historic backfill** for day-one causal depth.
- **Gemini** uses a model-fallback chain (`GEMINI_MODEL` → `GEMINI_FALLBACK_MODEL`)
  so a single model's rate-limit doesn't fail analysis; output is **Pydantic-
  validated** before it's persisted.
- **Feed cache:** list responses cached in SQLite (TTL `FEED_CACHE_TTL_SECONDS`),
  invalidated on refresh/backfill.
- **Export:** any analysed article downloads as a Markdown lecturette brief, or
  Print / Save-as-PDF from the detail view.

### Three-layer feed ranking

1. **Source credibility** — every article stores a `source_priority` (0–10:
   IDSA/PIB 10, The Print/IDR 9, The Hindu/Reuters 8, BBC/ANI 7, HT/NDTV/AJ 6).
   Top & Defence tabs sort by this, then recency.
2. **Topic relevance** — the Gemini system prompt ranks defence-aspirant topics
   (armed forces ops > border tensions > acquisitions > … ) and deprioritises
   entertainment/sport/weather, shaping `relevance` & `impact_level`.
3. **Personal behaviour** — opening an article = a `click` signal, 👎 = a `down`
   signal (stored per user in SQLite). The Personalised tab ranks by
   `source_priority + 1.5·category_clicks − category_downs`, and hides
   downvoted articles. The feed learns per-user over time.
- **Auth:** email/password (bcrypt + JWT). Each user gets `DAILY_ANALYSIS_LIMIT`
  Gemini deep analyses/day; counter resets at **midnight IST**. Cached analyses
  are free and don't consume quota.
- **Onboarding (3 screens):** profile (Defence Aspirant active; Business Owner /
  Student / Professional greyed) → defence details + 6 weak areas → news scope +
  notifications. Saved per-user in SQLite.
- **Home:** dark, three tabs (Top Stories / Defence Specific / Personalised For
  You), search, infinite scroll, skeleton loaders, "X analyses remaining today".
- **News detail:** 2-sentence summary, horizontal causal timeline with clickable
  node popups (past = solid blue, current = solid orange, future = dashed grey),
  "What this means for you", a 5-part lecturette, and key-term glossary.

## Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/signup` / `/api/auth/login` | JWT auth |
| GET/PUT | `/api/preferences` | onboarding prefs (auth) |
| GET | `/api/news?tab=&q=&limit=&offset=` | paginated feed + search |
| GET | `/api/news/{id}` | article + cached analysis |
| POST | `/api/news/{id}/analyze` | Gemini deep analysis (rate-limited) |
| GET | `/api/usage` | analyses used/remaining today |
| POST | `/api/news/refresh` | manual RSS + NewsAPI fetch |

## Deploy

- **Backend → Render:** `render.yaml` at repo root; set `NEWSAPI_KEY`,
  `GEMINI_API_KEY`, `ALLOWED_ORIGINS` (Vercel URL). `JWT_SECRET` auto-generated.
- **Frontend → Vercel:** import `frontend/`, set `VITE_API_URL` to Render URL.

## Notes

- NewsAPI free tier: 100 req/day, ~24h delay, dev use only — hence RSS is primary.
- Some govt RSS feeds (MoD/PIB) rate-limit or change format; ingestion skips
  unreadable feeds gracefully.
- Gemini analysis is cached per article so each is processed at most once.
