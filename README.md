# ExamGuard Pro - AI-Powered Proctoring System

ExamGuard Pro is an advanced, real-time exam monitoring and proctoring system that leverages AI to ensure academic integrity. It features multi-modal analysis including face detection, eye gaze tracking, OCR-based content monitoring, and intelligent page/site classification.

## 🚀 Key Features

- **Real-Time Monitoring**: Tab switches, window blurring, and copy/paste event tracking via the Chrome extension.
- **AI-Driven Analysis** (async Celery workers):
  - **Face Detection**: MediaPipe-powered presence & multi-face verification.
  - **Gaze Tracking**: Eye/attention monitoring with the MediaPipe Face Landmarker.
  - **OCR Analysis**: Detects forbidden content (e.g., ChatGPT, Chegg) from screen captures with Tesseract.
  - **Object Detection**: YOLOv8n-based detection of unauthorized devices (phones, tablets).
  - **Page Classification**: Heuristics + custom Transformer models to classify visited URLs/pages and student behavior.
  - **Text Similarity**: Sentence-Transformers based plagiarism detection.
- **Dynamic Risk Scoring**: Weighted event scoring (`core/risk_engine.py`) with live risk levels (Safe, Review, Suspicious), configurable at runtime by admins.
- **Real-Time Dashboard**: WebSocket updates via a Redis event bus, live session monitoring, and session timelines.
- **Background Processing**: Celery workers (face, object, gaze, OCR, NLP, report) with Redis queues.
- **Robust Reporting**: Automated PDF report generation (WeasyPrint) uploaded to Supabase Storage.

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Python 3.11, Pydantic v2 |
| **Database** | Supabase (PostgreSQL) with in-memory / SQLite fallback for local dev |
| **Async Tasks** | Celery + Redis |
| **Frontend** | React 19, Vite, Tailwind CSS 4, TanStack Query, Zustand, Recharts |
| **AI/ML** | MediaPipe, YOLOv8 (ultralytics), Tesseract OCR, Sentence-Transformers, custom Transformer (PyTorch) |
| **Extension** | Chrome Manifest V3 (plain JS — no build step) |
| **Testing** | Pytest (backend), Vitest (frontend), Ruff (lint) |
| **Deployment** | Render (`render.yaml`, `build.sh`, `start.sh`), Docker Compose |

## 📂 Project Structure

```text
├── main.py                  # Root entry point (delegates to server/main.py — used by Render)
├── build.sh / start.sh      # Render build & start scripts (build dashboard, launch API)
├── render.yaml              # Render blueprint (web service definition)
├── docker-compose.yml       # Local full stack: API + Redis + Celery worker + beat
├── requirements.txt         # Root shim → server/requirements.txt
├── server/                  # FastAPI backend
│   ├── main.py              # Application entry point (app, CORS, rate limiting)
│   ├── config.py            # Pydantic settings (env-driven)
│   ├── api/                 # Routers: auth, exams, sessions, events, reports, ws
│   ├── auth/                # JWT auth, role-based access, refresh tokens
│   ├── core/                # Event bus (Redis), risk engine, rate limiting, lifespan
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # AI pipeline: face_detection, gaze_tracking, ocr,
│   │   └── agents/          #   object_detection, page_classifier, transformer_analysis,
│   │                        #   and site-classification agents
│   ├── workers/             # Celery workers: face, object, gaze, ocr, nlp, report, cleanup
│   ├── migrations/          # SQL schema (supabase_schema.sql, 0001_init.sql)
│   ├── tests/               # Pytest suite (Supabase mocked)
│   ├── setup_database.py    # Schema bootstrap + admin seeding
│   ├── create_admin.py      # Create/seed admin users
│   └── supabase_client.py   # Supabase connection manager
├── examguard-pro/           # React 19 + Vite dashboard
│   └── src/                 # components/, pages/, context/, api/, store/, hooks/
├── extension/               # Chrome Extension (Manifest V3) — load unpacked, no build
│   ├── background.js        # Service worker: events, uploads, page-context analysis
│   ├── content.js           # Page monitoring & event capture
│   ├── content_agent_patch.js # Page-context signals for site classification
│   └── popup/               # Consent flow, session controls, live stats
└── scripts/                 # Helper scripts (PowerShell + Python)
    ├── start-dev.ps1        # One-shot API dev server (creates venv)
    ├── start-redis.ps1      # Redis via Docker
    ├── start-worker.ps1     # Celery worker for local dev
    ├── start-docker.ps1     # Full stack via docker compose
    ├── setup-supabase.ps1   # DB schema setup + admin seed
    └── ws_load_test.py      # WebSocket load-test helper
```

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.10+ (3.11 recommended)
- Node.js 20+
- Tesseract OCR installed locally (for OCR analysis)
- Redis (optional — needed for Celery workers and real-time WebSocket events)
- Supabase account (optional — the API falls back to in-memory storage / SQLite without it)

### 2. Backend Setup
```bash
cd server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Optional: configure .env (copy from .env.example) with SUPABASE_URL,
# SUPABASE_KEY (service_role), and PG_* pooler credentials.
python setup_database.py --seed-admin   # or paste migrations/supabase_schema.sql in the Supabase SQL Editor
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The API is now live at http://127.0.0.1:8000 — interactive docs at `/docs`.

> Windows shortcut: `.\scripts\start-dev.ps1` creates the venv, installs deps, and starts the API.

### 3. Run Celery Workers (optional)
AI analysis (face, gaze, OCR, object detection, similarity) runs in background workers:
```bash
# Terminal 1 — Redis (Docker)
docker run -p 6379:6379 redis:7-alpine    # or .\scripts\start-redis.ps1

# Terminal 2 — worker (from server/ with venv active)
celery -A workers.celery_app worker --loglevel=info -Q face,object,gaze,ocr,nlp,report,default -c 2
```
Or run the whole stack with one command: `docker compose up --build` (API + Redis + worker + beat).

### 4. Frontend Setup
```bash
cd examguard-pro
npm install
npm run dev      # http://localhost:3000 — proxies /api and /ws to 127.0.0.1:8000
# Production build:
npm run build    # outputs examguard-pro/dist/ (serve as a static site)
```
Other scripts: `npm run test` (Vitest), `npm run lint` (TypeScript check).

### 5. Chrome Extension
1. Open `chrome://extensions` in your browser.
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the `extension/` directory — no build step required.
4. The backend URL defaults to `http://127.0.0.1:8000` (see `BACKEND_URL` in `extension/background.js`).

## 🧪 Testing
```bash
cd server && python -m pytest tests/ -v     # backend (Supabase mocked, no services needed)
cd examguard-pro && npm run test            # frontend
cd server && ruff check . --ignore E501     # lint
```

## 🚢 Deployment (Render)

The repo ships a Render blueprint (`render.yaml`) — a single Python web service that builds the dashboard and serves the API:

1. Connect your repository to **Render** and create a **Blueprint** (or a Web Service) from it.
2. Build command: `bash build.sh` — installs Python deps, builds the dashboard, pre-downloads YOLO weights.
3. Start command: `bash start.sh` — runs `uvicorn main:app` from the repo root on `$PORT`.
4. Configure environment variables (secrets should be set in the Render dashboard, not committed):
   - `SUPABASE_URL`, `SUPABASE_KEY` (service role recommended)
   - `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_DB`, `PG_PASSWORD` (Supabase pooler, for direct DB access)
   - `SECRET_KEY` (auto-generated by the blueprint)
   - `CORS_ORIGINS` (comma-separated allowed origins)
5. For workers on Render, deploy a second service from `server/` running the Celery command above (needs a Redis instance, e.g. Render Redis with `REDIS_URL` / `CELERY_BROKER_URL` set).

### Local full stack (Docker)
```bash
docker compose up --build    # API :8000, Redis :6379, worker, beat
```

## 🔌 Default Ports
| Service | URL |
|---------|-----|
| API | http://127.0.0.1:8000 |
| API docs | http://127.0.0.1:8000/docs |
| Dashboard (dev) | http://localhost:3000 |
| Redis | redis://localhost:6379/0 |

## 📄 License
This project is licensed under the MIT License.
