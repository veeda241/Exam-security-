# ExamGuard Pro - AI-Powered Proctoring System

ExamGuard Pro is an advanced, real-time exam monitoring and proctoring system that leverages AI to ensure academic integrity. It features multi-modal analysis including face detection, eye gaze tracking, OCR-based content monitoring, and NLP-based plagiarism detection.

## 🚀 Key Features

- **Real-Time Monitoring**: Tab switches, window blurring, and copy/paste event tracking.
- **AI-Driven Analysis**:
  - **Face Detection**: MediaPipe-powered presence verification.
  - **Gaze Tracking**: Monitors eye movement for suspicious patterns.
  - **OCR Analysis**: Detects forbidden content (e.g., ChatGPT, Chegg) from screen captures.
  - **Object Detection**: YOLOv8-based detection of unauthorized devices (phones, tablets).
  - **Text Similarity**: NLP-based comparison for plagiarism detection.
- **Dynamic Risk Scoring**: Weighted event scoring with live risk levels (Safe, Review, Suspicious).
- **Interactive Dashboard**: Real-time WebSocket updates, student performance metrics, and session timelines.
- **Robust Reporting**: Automated PDF report generation with detailed violation logs.

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Python 3.10+, Supabase (PostgreSQL) |
| **Database** | Supabase (Cloud Database & Real-time) |
| **Frontend** | React 19, Vite, Tailwind CSS, Lucide Icons |
| **AI/ML** | MediaPipe, YOLOv8, Tesseract OCR, Sentence-Transformers |
| **Extension** | Chrome Manifest V3, WebRTC |
| **Deployment** | Render, Docker |

## 📂 Project Structure

```text
├── server/                  # FastAPI backend
│   ├── api/                 # API endpoints & Pydantic schemas
│   ├── auth/                # JWT Authentication & Supabase integration
│   ├── services/            # AI Pipeline (Face, OCR, NLP, Vision)
│   ├── main.py              # Application entry point
│   └── supabase_client.py    # Supabase connection manager
├── react-frontend/          # React Dashboard (Vite)
│   ├── src/components/      # Analytics, Dashboard, Alerts, Reports
│   └── src/context/         # Global AppState & Real-time context
├── extension/               # Chrome Extension (Manifest V3)
│   ├── background.js        # Core logic & backend synchronization
│   ├── content.js           # Page monitoring & event capture
│   └── webcam.js            # Video processing & frame capture
└── deployment/              # Deployment configurations
```

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- Supabase Account (URL & Keys)
- Tesseract OCR installed locally (for dev)

### 2. Backend Setup
```bash
cd server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Create a .env file with your SUPABASE_URL and SUPABASE_KEY
python main.py
```

### 3. Frontend Setup
```bash
cd react-frontend
npm install
npm run dev
```

### 4. Chrome Extension
1. Open `chrome://extensions` in your browser.
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the `extension/` directory.
4. Configure the `BACKEND_URL` in `extension/background.js` if necessary.

## 🚢 Deployment (Render)

1. Connect your repository to **Render**.
2. Create a **Web Service** for the `server/` directory.
3. Configure **Environment Variables**:
   - `SUPABASE_URL`: Your project URL.
   - `SUPABASE_KEY`: Your service role or anon key.
   - `SECRET_KEY`: Random string for JWT.
4. Use the following build command: `pip install -r requirements.txt`.
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`.

## 📄 License
This project is licensed under the MIT License.
