# Running مركز المودة (quality_platform) with Docker

Two containers, orchestrated by Compose:

| Service   | Image base        | Container port | Published (dev) |
|-----------|-------------------|----------------|-----------------|
| backend   | `python:3.11-slim`| 8000           | `8000`          |
| frontend  | `node:20-alpine`  | 3000           | `9000`          |

The backend bundles the Family & Society domain module (`telegram_bot_family.py`),
the Amiri font, and the `templates/` folder, and installs WeasyPrint + Playwright
(chromium) system deps for PDF rendering and JS-site scraping. The frontend is built
as a Next.js **standalone** server.

## 1. Create the runtime env file (required)

Compose reads `quality_platform/.env`. It is **not** committed. Create it from the
template and fill in real values:

```bash
cd quality_platform
cp .env.example .env
```

Fill at minimum:
- `SECRET_KEY` — any long random string (JWT signing)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` — the first admin (created on first boot)
- AWS Bedrock creds — **either** `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`
  **or** `AWS_BEARER_TOKEN_BEDROCK` (needed for AI reports + the awareness campaign)
- `TWITTER_BEARER_TOKEN` — for X/Twitter sources

> The same working values already live in `quality_bot/.env`; you can copy those
> secrets over into `quality_platform/.env`.

## 2. Build & run (local / dev)

```bash
cd quality_platform
docker compose up --build
```

- Frontend → http://localhost:9000
- Backend API + docs → http://localhost:8000/api/health , http://localhost:8000/docs
- Log in with the `ADMIN_USERNAME` / `ADMIN_PASSWORD` you set.

The frontend is built with `NEXT_PUBLIC_API_URL=http://localhost:8000` (baked at
build time), so the browser talks to the published backend port directly.

Stop with `Ctrl+C`, or run detached with `docker compose up --build -d` and stop with
`docker compose down`.

## 3. Data persistence

The SQLite DB is volume-mounted at `./backend/data` on the host
(`/app/quality_platform/backend/data` in the container), so users, usage counters,
articles, and saved reports survive container restarts and rebuilds. Delete that
folder to reset to a clean database.

## 4. Production (VPS behind Nginx)

`docker-compose.prod.yml` publishes backend on `9005` and frontend on `9000`, and
builds the frontend with an **empty** `NEXT_PUBLIC_API_URL` so the browser uses
same-origin relative `/api/...` paths — put Nginx in front to serve the frontend and
proxy `/api/` to the backend.

```bash
cd quality_platform
docker compose -f docker-compose.prod.yml up --build -d
```

## Notes / gotchas

- **First build is slow** (~10+ min): it installs WeasyPrint native libs and a
  Playwright chromium browser. Subsequent builds are cached.
- The awareness-campaign strategy and the magazine call Bedrock with a **600s**
  timeout — the container has no request timeout, so long generations complete fine.
- If AI generation errors with "no credentials", the AWS keys in
  `quality_platform/.env` are missing/empty — Bedrock uses the default credential
  chain inside the container (there is no `.env` file baked into the image).
- Playwright JS-site scraping degrades gracefully to `[]` if chromium is unavailable;
  the backend still runs.
