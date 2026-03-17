# ExamGuard Pro

AI-powered exam proctoring system with real-time monitoring, face detection, OCR analysis, NLP-based plagiarism detection, and automated risk scoring.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy (async), PostgreSQL / SQLite |
| Frontend | React 19, Vite, React Router v7 |
| AI/ML | MediaPipe, YOLOv8, Tesseract OCR, Sentence-Transformers |
| Extension | Chrome Manifest V3 |
| Deployment | Docker, Docker Compose |

## Project Structure

```
├── server/                  # FastAPI backend
│   ├── api/                 # Organized API endpoints
│   ├── auth/                # JWT authentication
│   ├── models/              # SQLAlchemy models
│   ├── routers/             # Route handlers
│   ├── scoring/             # Risk score engine
│   ├── services/            # ML services (16 modules)
│   │   ├── face_detection   # MediaPipe face mesh
│   │   ├── gaze_tracking    # Eye gaze analysis
│   │   ├── ocr              # Tesseract screenshot analysis
│   │   ├── similarity       # Text plagiarism detection
│   │   ├── anomaly          # Behavior anomaly detection
│   │   ├── object_detection # YOLOv8 object detection
│   │   ├── biometrics       # Biometric verification
│   │   ├── pipeline         # Real-time analysis pipeline
│   │   └── realtime         # WebSocket event manager
│   ├── tasks/               # Background task queue
│   └── utils/               # Shared utilities
├── react-frontend/          # React dashboard (Vite)
│   └── src/components/      # Dashboard, Sessions, Alerts,
│                            # Analytics, Reports, Students
├── extension/               # Chrome extension (Manifest V3)
│   ├── background.js        # Service worker
│   ├── content.js           # Page monitoring
│   ├── webcam.js            # Webcam capture
│   └── popup/               # Extension popup UI
├── transformer/             # Custom NLP model
│   ├── model/               # Transformer architecture
│   ├── data/                # Tokenizer & datasets
│   ├── checkpoints/         # Trained model weights
│   ├── train_examguard.py   # Model training
│   └── train_similarity.py  # Similarity model training
└── deployment/              # Docker configuration
    ├── Dockerfile           # Multi-stage build (Node + Python)
    ├── docker-compose.yml   # Backend + PostgreSQL
    └── .env.example         # Environment template
```

## Quick Start

### Local Development

```bash
# 1. Backend
cd server
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 2. Frontend (separate terminal)
cd react-frontend
npm install
npm run dev                   # http://localhost:3000
```

### Docker Deployment (Self-hosted)

```bash
cd deployment
copy .env.example .env        # Edit with production secrets
docker-compose --env-file .env up --build -d
```

### Render Deployment (Recommended for Remote Access)

1. **Push to GitHub** — Push this repo to a GitHub repository

2. **Create a Render Web Service**
   - Go to [render.com](https://render.com) → **New** → **Web Service**
   - Connect your GitHub repo
   - Set **Root Directory** to `server`
   - Set **Build Command**: `chmod +x build.sh && ./build.sh`
   - Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Choose **Python 3** runtime

3. **Add Environment Variables** in Render dashboard:
   | Variable | Value |
   |----------|-------|
   | `PG_HOST` | `db.fpnopsvzvfqwvyqmhgei.supabase.co` |
   | `PG_PASSWORD` | Your Supabase DB password |
   | `SUPABASE_URL` | `https://fpnopsvzvfqwvyqmhgei.supabase.co` |
   | `SUPABASE_KEY` | Your Supabase anon key |
   | `SUPABASE_DB_PASSWORD` | Your Supabase DB password |
   | `SECRET_KEY` | Generate a random string |
   | `CORS_ORIGINS` | `*` |

4. **Deploy** — Render builds and gives you a URL like `https://examguard-api.onrender.com`

5. **Update Chrome Extension** — In `extension/background.js`, change:
   ```js
   API_BASE: 'https://examguard-api.onrender.com/api',
   WS_URL: 'wss://examguard-api.onrender.com/ws/student',
   ```

6. **Update React Frontend** — In `react-frontend/src/config.js`, the URLs auto-detect in production. For local dev pointing to Render:
   ```js
   export const API_BASE = 'https://examguard-api.onrender.com/api';
   ```

Access points after deployment:
- **API** — `https://examguard-api.onrender.com`
- **API Docs** — `https://examguard-api.onrender.com/docs`
- **WebSocket** — `wss://examguard-api.onrender.com/ws/dashboard`

### Chrome Extension

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `extension/` folder
4. Click the ExamGuard icon → enter exam session details

> For production, update `API_BASE` and `WS_URL` in `extension/background.js` to your server domain.

## Features

### Real-Time Monitoring
- Tab switch & window blur detection
- Copy/paste event tracking
- Periodic screenshot capture (3s interval)
- Webcam frame capture (5s interval)
- WebSocket-based live dashboard updates

### AI Analysis Pipeline
- **Face Detection** — MediaPipe face mesh for presence verification
- **Gaze Tracking** — Eye movement analysis for engagement scoring
- **OCR Analysis** — Tesseract-based forbidden content detection (ChatGPT, Chegg, etc.)
- **Object Detection** — YOLOv8 for unauthorized device detection
- **Text Similarity** — Sentence-transformer plagiarism detection
- **Anomaly Detection** — ML-based suspicious behavior identification
- **Audio Analysis** — Environment sound monitoring
- **Browser Forensics** — Domain categorization & browsing pattern analysis

### Risk Scoring
- Weighted event scoring with dynamic risk levels (Safe / Review / Suspicious)
- Cumulative risk analysis with timeline visualization
- Per-student and per-session risk breakdowns

### Reporting
- PDF report generation with risk timelines
- JSON data export
- Session analytics and trend charts

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/login` | JWT authentication |
| `GET /api/students` | List students |
| `POST /api/sessions` | Create exam session |
| `POST /api/events` | Log monitoring event |
| `POST /api/uploads/screenshot` | Upload screenshot for OCR |
| `POST /api/uploads/webcam` | Upload webcam frame |
| `GET /api/analysis/{session_id}` | Get AI analysis results |
| `GET /api/reports/{session_id}` | Generate session report |
| `WS /ws/dashboard` | Dashboard real-time events |
| `WS /ws/student/{id}` | Student monitoring channel |

Full interactive docs available at `/docs` when the server is running.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | Full DB connection string (auto-detected on Render) |
| `PG_HOST` | — | Supabase PostgreSQL host |
| `PG_USER` | `postgres` | PostgreSQL username |
| `PG_PASSWORD` | — | PostgreSQL password |
| `PG_DB` | `postgres` | PostgreSQL database name |
| `SUPABASE_URL` | — | Supabase project URL |
| `SUPABASE_KEY` | — | Supabase anon/public key |
| `SUPABASE_DB_PASSWORD` | — | Supabase database password |
| `SECRET_KEY` | — | App secret for sessions |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

> If no `DATABASE_URL` or `PG_HOST` is set, falls back to local SQLite (`examguard.db`).

## License

MIT
