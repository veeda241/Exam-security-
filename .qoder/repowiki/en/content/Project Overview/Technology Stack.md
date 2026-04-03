# Technology Stack

<cite>
**Referenced Files in This Document**
- [Dockerfile](file://Dockerfile)
- [render.yaml](file://render.yaml)
- [server/main.py](file://server/main.py)
- [server/config.py](file://server/config.py)
- [server/requirements.txt](file://server/requirements.txt)
- [server/supabase_client.py](file://server/supabase_client.py)
- [server/services/face_detection.py](file://server/services/face_detection.py)
- [server/services/object_detection.py](file://server/services/object_detection.py)
- [server/services/ocr.py](file://server/services/ocr.py)
- [server/services/transformer_analysis.py](file://server/services/transformer_analysis.py)
- [transformer/requirements.txt](file://transformer/requirements.txt)
- [transformer/config.py](file://transformer/config.py)
- [examguard-pro/package.json](file://examguard-pro/package.json)
- [examguard-pro/src/main.tsx](file://examguard-pro/src/main.tsx)
- [extension/manifest.json](file://extension/manifest.json)
- [extension/background.js](file://extension/background.js)
- [extension/content.js](file://extension/content.js)
- [extension/capture.js](file://extension/capture.js)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document provides a comprehensive technology stack overview for ExamGuard Pro. It covers backend technologies (FastAPI, Python 3.10+, Supabase/PostgreSQL, asyncpg), frontend technologies (React 19, Vite, Tailwind CSS, Lucide Icons), AI/ML technologies (MediaPipe, YOLOv8, Tesseract OCR, Sentence-transformers-style Transformers), Chrome extension technologies (Manifest V3, WebRTC, background scripts), and deployment technologies (Docker, Render). It also includes version compatibility information and rationale for technology choices.

## Project Structure
The repository is organized into modular components:
- server: FastAPI backend with routers, services, and AI/ML modules
- examguard-pro: React 19 dashboard built with Vite
- extension: Chrome extension (Manifest V3) with background and content scripts
- transformer: Custom Transformer models and training utilities
- deployment: Docker and Render configuration

```mermaid
graph TB
subgraph "Server (FastAPI)"
S_MAIN["server/main.py"]
S_CONF["server/config.py"]
S_SUPA["server/supabase_client.py"]
S_FACE["server/services/face_detection.py"]
S_OBJ["server/services/object_detection.py"]
S_OCR["server/services/ocr.py"]
S_TRANS["server/services/transformer_analysis.py"]
end
subgraph "Frontend (React 19)"
F_PKG["examguard-pro/package.json"]
F_MAIN["examguard-pro/src/main.tsx"]
end
subgraph "Chrome Extension"
E_MAN["extension/manifest.json"]
E_BG["extension/background.js"]
E_CT["extension/content.js"]
E_CP["extension/capture.js"]
end
subgraph "Transformer Models"
T_REQ["transformer/requirements.txt"]
T_CFG["transformer/config.py"]
end
subgraph "Deployment"
D_DOCK["Dockerfile"]
D_REND["render.yaml"]
end
F_MAIN --> S_MAIN
E_BG --> S_MAIN
E_CT --> E_BG
E_CP --> E_BG
S_MAIN --> S_FACE
S_MAIN --> S_OBJ
S_MAIN --> S_OCR
S_MAIN --> S_TRANS
S_MAIN --> S_SUPA
S_MAIN --> S_CONF
D_DOCK --> S_MAIN
D_REND --> S_MAIN
T_REQ --> S_TRANS
T_CFG --> S_TRANS
```

**Diagram sources**
- [server/main.py:1-647](file://server/main.py#L1-L647)
- [server/config.py:1-205](file://server/config.py#L1-L205)
- [server/supabase_client.py:1-22](file://server/supabase_client.py#L1-L22)
- [server/services/face_detection.py:1-109](file://server/services/face_detection.py#L1-L109)
- [server/services/object_detection.py:1-147](file://server/services/object_detection.py#L1-L147)
- [server/services/ocr.py:1-121](file://server/services/ocr.py#L1-L121)
- [server/services/transformer_analysis.py:1-549](file://server/services/transformer_analysis.py#L1-L549)
- [transformer/requirements.txt:1-8](file://transformer/requirements.txt#L1-L8)
- [transformer/config.py:1-75](file://transformer/config.py#L1-L75)
- [examguard-pro/package.json:1-40](file://examguard-pro/package.json#L1-L40)
- [examguard-pro/src/main.tsx:1-11](file://examguard-pro/src/main.tsx#L1-L11)
- [extension/manifest.json:1-73](file://extension/manifest.json#L1-L73)
- [extension/background.js:1-1998](file://extension/background.js#L1-L1998)
- [extension/content.js:1-473](file://extension/content.js#L1-L473)
- [extension/capture.js:1-352](file://extension/capture.js#L1-L352)
- [Dockerfile:1-55](file://Dockerfile#L1-L55)
- [render.yaml:1-36](file://render.yaml#L1-L36)

**Section sources**
- [Dockerfile:1-55](file://Dockerfile#L1-L55)
- [render.yaml:1-36](file://render.yaml#L1-L36)
- [server/main.py:1-647](file://server/main.py#L1-L647)
- [server/config.py:1-205](file://server/config.py#L1-L205)
- [server/requirements.txt:1-34](file://server/requirements.txt#L1-L34)
- [server/supabase_client.py:1-22](file://server/supabase_client.py#L1-L22)
- [server/services/face_detection.py:1-109](file://server/services/face_detection.py#L1-L109)
- [server/services/object_detection.py:1-147](file://server/services/object_detection.py#L1-L147)
- [server/services/ocr.py:1-121](file://server/services/ocr.py#L1-L121)
- [server/services/transformer_analysis.py:1-549](file://server/services/transformer_analysis.py#L1-L549)
- [transformer/requirements.txt:1-8](file://transformer/requirements.txt#L1-L8)
- [transformer/config.py:1-75](file://transformer/config.py#L1-L75)
- [examguard-pro/package.json:1-40](file://examguard-pro/package.json#L1-L40)
- [examguard-pro/src/main.tsx:1-11](file://examguard-pro/src/main.tsx#L1-L11)
- [extension/manifest.json:1-73](file://extension/manifest.json#L1-L73)
- [extension/background.js:1-1998](file://extension/background.js#L1-L1998)
- [extension/content.js:1-473](file://extension/content.js#L1-L473)
- [extension/capture.js:1-352](file://extension/capture.js#L1-L352)

## Core Components
- Backend (FastAPI): Provides REST APIs, WebSocket endpoints, real-time monitoring, and integrates AI/ML services. It mounts the React build and serves it as a SPA.
- Frontend (React 19): Dashboard UI with routing, charts, and UI components.
- Chrome Extension (Manifest V3): Monitors behavior, captures screen/webcam, performs WebRTC signaling, and communicates with the backend via WebSocket and HTTP.
- AI/ML Services: Face detection (MediaPipe), object detection (YOLOv8), OCR (Tesseract), and custom Transformer models for URL classification, behavioral anomaly detection, and screen content classification.
- Database: Supabase-managed PostgreSQL with asyncpg for Python connections.
- Deployment: Docker multi-stage build and Render configuration.

**Section sources**
- [server/main.py:170-186](file://server/main.py#L170-L186)
- [server/config.py:16-42](file://server/config.py#L16-L42)
- [server/requirements.txt:1-34](file://server/requirements.txt#L1-L34)
- [server/services/face_detection.py:27-109](file://server/services/face_detection.py#L27-L109)
- [server/services/object_detection.py:16-147](file://server/services/object_detection.py#L16-L147)
- [server/services/ocr.py:20-121](file://server/services/ocr.py#L20-L121)
- [server/services/transformer_analysis.py:178-549](file://server/services/transformer_analysis.py#L178-L549)
- [transformer/requirements.txt:1-8](file://transformer/requirements.txt#L1-L8)
- [transformer/config.py:10-75](file://transformer/config.py#L10-L75)
- [examguard-pro/package.json:13-28](file://examguard-pro/package.json#L13-L28)
- [extension/manifest.json:1-73](file://extension/manifest.json#L1-L73)
- [Dockerfile:1-55](file://Dockerfile#L1-L55)
- [render.yaml:1-36](file://render.yaml#L1-L36)

## Architecture Overview
The system comprises three primary layers:
- Frontend: React SPA served by the backend
- Backend: FastAPI with WebSocket real-time channels and REST endpoints
- Extension: Chrome extension performing client-side monitoring and live streaming

```mermaid
graph TB
UI["React Dashboard<br/>spa_fallback and static mount"] --> API["FastAPI Server<br/>REST + WebSockets"]
EXT["Chrome Extension<br/>background/content/capture"] --> API
API --> DB["Supabase PostgreSQL<br/>asyncpg"]
API --> VISION["Vision Engines<br/>MediaPipe + YOLO + Tesseract"]
API --> TRANS["Transformer Analyzer<br/>custom models"]
TRANS --> MODELS["Transformer Checkpoints<br/>tokenizer.json"]
```

**Diagram sources**
- [server/main.py:510-634](file://server/main.py#L510-L634)
- [server/config.py:16-42](file://server/config.py#L16-L42)
- [server/services/face_detection.py:27-109](file://server/services/face_detection.py#L27-L109)
- [server/services/object_detection.py:16-147](file://server/services/object_detection.py#L16-L147)
- [server/services/ocr.py:20-121](file://server/services/ocr.py#L20-L121)
- [server/services/transformer_analysis.py:178-549](file://server/services/transformer_analysis.py#L178-L549)
- [transformer/config.py:10-75](file://transformer/config.py#L10-L75)

## Detailed Component Analysis

### Backend (FastAPI)
- Application lifecycle manages vision engines, real-time manager, and analysis pipeline.
- CORS middleware configured for broad compatibility during development and extension support.
- WebSocket endpoints for dashboard, proctor, and student communication.
- SPA fallback for React Router compatibility.
- Health and stats endpoints expose pipeline and AI module status.

```mermaid
sequenceDiagram
participant Client as "Client App"
participant API as "FastAPI Server"
participant Vision as "SecureVision"
participant Pipe as "Analysis Pipeline"
participant RT as "Realtime Manager"
Client->>API : GET /api/health-check
API-->>Client : JSON status
API->>Vision : Initialize face detection
API->>Pipe : Start pipeline
API->>RT : Start heartbeat
Client->>API : WebSocket /ws/dashboard
API->>RT : Connect dashboard
RT-->>Client : Stats and events
```

**Diagram sources**
- [server/main.py:109-165](file://server/main.py#L109-L165)
- [server/main.py:228-237](file://server/main.py#L228-L237)
- [server/main.py:274-342](file://server/main.py#L274-L342)
- [server/main.py:548-584](file://server/main.py#L548-L584)

**Section sources**
- [server/main.py:109-165](file://server/main.py#L109-L165)
- [server/main.py:192-222](file://server/main.py#L192-L222)
- [server/main.py:248-474](file://server/main.py#L248-L474)
- [server/main.py:548-584](file://server/main.py#L548-L584)

### Database and ORM (Supabase/asyncpg)
- Database URL resolution supports DATABASE_URL, Supabase config, or SQLite fallback.
- Environment-driven configuration for host, port, user, and password.
- Supabase client initialization and retrieval utility.

```mermaid
flowchart TD
Start(["Startup"]) --> CheckEnv["Check DATABASE_URL or Supabase env vars"]
CheckEnv --> HasURL{"DATABASE_URL present?"}
HasURL --> |Yes| Normalize["Normalize postgres:// to postgresql+asyncpg://"]
HasURL --> |No| SupabaseCfg["Use PG_* env vars"]
SupabaseCfg --> BuildURL["Build asyncpg URL"]
Normalize --> BuildURL
BuildURL --> InitDB["Initialize asyncpg engine"]
InitDB --> End(["Ready"])
```

**Diagram sources**
- [server/config.py:29-42](file://server/config.py#L29-L42)
- [server/supabase_client.py:10-21](file://server/supabase_client.py#L10-L21)

**Section sources**
- [server/config.py:16-42](file://server/config.py#L16-L42)
- [server/supabase_client.py:1-22](file://server/supabase_client.py#L1-L22)

### AI/ML Services

#### Face Detection (MediaPipe)
- Uses MediaPipe Tasks API with a downloaded face landmarker model if available; falls back to Haar cascades.
- Detects multiple faces, absent face violations, and pose-related anomalies.

```mermaid
classDiagram
class SecureVision {
+landmarker
+haar_cascade
+profile_cascade
+analyze_frame(frame) Dict
-_analyze_tasks(frame, results) Dict
-_analyze_haar(frame, results) Dict
}
```

**Diagram sources**
- [server/services/face_detection.py:27-109](file://server/services/face_detection.py#L27-L109)

**Section sources**
- [server/services/face_detection.py:1-109](file://server/services/face_detection.py#L1-L109)

#### Object Detection (YOLOv8)
- Loads a YOLO model and detects forbidden objects (phone, book, laptop, watch, remote, TV, mouse, keyboard).
- Applies CLAHE for low-light enhancement and throttles processing for stability.

```mermaid
flowchart TD
A["Receive Frame"] --> B["Enhance with CLAHE"]
B --> C["Run YOLO inference"]
C --> D{"Objects detected?"}
D --> |No| E["Return no risk"]
D --> |Yes| F["Aggregate risk by class"]
F --> G["Cache result and throttle"]
G --> H["Return forbidden_detected, objects, risk_score"]
```

**Diagram sources**
- [server/services/object_detection.py:65-137](file://server/services/object_detection.py#L65-L137)

**Section sources**
- [server/services/object_detection.py:1-147](file://server/services/object_detection.py#L1-L147)

#### OCR (Tesseract)
- Extracts text from screenshots and flags forbidden keywords.
- Provides a fallback when Tesseract is unavailable.

```mermaid
flowchart TD
Start(["Analyze Screenshot"]) --> CheckTess["Tesseract available?"]
CheckTess --> |No| Fallback["Return warning and zero risk"]
CheckTess --> |Yes| LoadImg["Open image"]
LoadImg --> OCR["pytesseract.image_to_string"]
OCR --> KW["Scan for forbidden keywords"]
KW --> Risk["Compute risk score"]
Risk --> End(["Return text, keywords, risk"])
```

**Diagram sources**
- [server/services/ocr.py:29-84](file://server/services/ocr.py#L29-L84)

**Section sources**
- [server/services/ocr.py:1-121](file://server/services/ocr.py#L1-L121)

#### Transformer-based Analysis
- Loads three models: URL classifier, behavioral anomaly detector, and screen content classifier.
- Tokenizers are loaded from checkpoint directories; models run on GPU if available.
- Provides risk scores mapped to categories.

```mermaid
classDiagram
class TransformerAnalyzer {
+url_model
+behavior_model
+screen_model
+url_tokenizer
+screen_tokenizer
+classify_url(url) Dict
+predict_behavior_risk(events) Dict
+classify_screen_content(text) Dict
+get_status() Dict
}
class BehavioralAnomalyDetector
class ScreenContentClassifier
class URLClassifier
TransformerAnalyzer --> BehavioralAnomalyDetector : "loads"
TransformerAnalyzer --> ScreenContentClassifier : "loads"
TransformerAnalyzer --> URLClassifier : "loads"
```

**Diagram sources**
- [server/services/transformer_analysis.py:178-549](file://server/services/transformer_analysis.py#L178-L549)

**Section sources**
- [server/services/transformer_analysis.py:1-549](file://server/services/transformer_analysis.py#L1-L549)
- [transformer/requirements.txt:1-8](file://transformer/requirements.txt#L1-L8)
- [transformer/config.py:10-75](file://transformer/config.py#L10-L75)

### Chrome Extension (Manifest V3)
- Background script manages session lifecycle, retries, WebRTC signaling, and periodic sync.
- Content script monitors behavior, detects overlays/iframes, and sends alerts.
- Capture script handles screen/webcam capture, MediaRecorder streaming, and WebRTC offer/answer.

```mermaid
sequenceDiagram
participant User as "User"
participant Ext as "Extension"
participant BG as "Background Script"
participant CT as "Content Script"
participant CP as "Capture Script"
participant API as "FastAPI Server"
User->>Ext : Click extension action
Ext->>BG : START_EXAM
BG->>API : POST /api/sessions/create
API-->>BG : session_id
BG->>CT : START_SCREEN_CAPTURE
BG->>CP : startAll()
CP->>API : MediaRecorder binary chunks via WS
CT->>BG : LOG_EVENT / BEHAVIOR_ALERT
BG->>API : HTTP sync
User->>Ext : Stop exam
BG->>API : Cleanup and status
```

**Diagram sources**
- [extension/background.js:683-747](file://extension/background.js#L683-L747)
- [extension/content.js:367-381](file://extension/content.js#L367-L381)
- [extension/capture.js:175-203](file://extension/capture.js#L175-L203)
- [server/main.py:393-474](file://server/main.py#L393-L474)

**Section sources**
- [extension/manifest.json:1-73](file://extension/manifest.json#L1-L73)
- [extension/background.js:1-1998](file://extension/background.js#L1-L1998)
- [extension/content.js:1-473](file://extension/content.js#L1-L473)
- [extension/capture.js:1-352](file://extension/capture.js#L1-L352)

### Frontend (React 19 + Vite)
- React 19 with strict mode and root rendering.
- Vite build pipeline with TypeScript and Tailwind CSS integration.
- UI components under src/components and routing via react-router-dom.

```mermaid
graph LR
VITE["Vite Build"] --> DIST["dist/"]
DIST --> SPA["SPA Fallback in FastAPI"]
MAIN["src/main.tsx"] --> APP["App.tsx"]
PKG["package.json deps"] --> VITE
```

**Diagram sources**
- [examguard-pro/src/main.tsx:1-11](file://examguard-pro/src/main.tsx#L1-L11)
- [examguard-pro/package.json:1-40](file://examguard-pro/package.json#L1-L40)
- [server/main.py:611-634](file://server/main.py#L611-L634)

**Section sources**
- [examguard-pro/src/main.tsx:1-11](file://examguard-pro/src/main.tsx#L1-L11)
- [examguard-pro/package.json:1-40](file://examguard-pro/package.json#L1-L40)

### Deployment (Docker + Render)
- Docker multi-stage build:
  - Node stage builds the React frontend
  - Python stage installs system dependencies (Tesseract, FFmpeg), Python packages, and copies built frontend assets
  - Uvicorn runs the FastAPI app
- Render configuration sets Python 3.11, environment variables for Supabase and PostgreSQL, and start/build commands.

```mermaid
flowchart TD
A["Node Stage: npm install + build"] --> B["Copy dist/ to /app/server/dist"]
B --> C["Python Stage: apt-get install system deps"]
C --> D["pip install requirements-deploy.txt"]
D --> E["Copy project files"]
E --> F["Expose PORT and run uvicorn"]
F --> G["Render: build/start commands"]
```

**Diagram sources**
- [Dockerfile:1-55](file://Dockerfile#L1-L55)
- [render.yaml:1-36](file://render.yaml#L1-L36)

**Section sources**
- [Dockerfile:1-55](file://Dockerfile#L1-L55)
- [render.yaml:1-36](file://render.yaml#L1-L36)

## Dependency Analysis
- Backend depends on:
  - FastAPI for routing and ASGI server
  - asyncpg for async PostgreSQL connectivity
  - Supabase client for managed database access
  - MediaPipe, Ultralytics YOLO, Tesseract for AI/ML
  - Transformers analyzer module for NLP tasks
- Frontend depends on:
  - React 19, Vite, Tailwind CSS, Lucide Icons
- Extension depends on:
  - Manifest V3 permissions and service worker
  - WebRTC for peer-to-peer streaming
  - MediaRecorder for live streaming

```mermaid
graph TB
REQ["server/requirements.txt"] --> FAST["FastAPI"]
REQ --> ASYNC["asyncpg"]
REQ --> MP["mediapipe"]
REQ --> ULTR["ultralytics"]
REQ --> TESS["pytesseract"]
REQ --> SUPA["supabase"]
PKG["examguard-pro/package.json"] --> REACT["React 19"]
PKG --> VITE["Vite"]
PKG --> TAIL["Tailwind CSS"]
PKG --> ICON["Lucide Icons"]
MAN["extension/manifest.json"] --> BG["background.js"]
MAN --> CT["content.js"]
MAN --> CP["capture.js"]
BG --> RT["WebRTC"]
CT --> MR["MediaRecorder"]
```

**Diagram sources**
- [server/requirements.txt:1-34](file://server/requirements.txt#L1-L34)
- [examguard-pro/package.json:13-28](file://examguard-pro/package.json#L13-L28)
- [extension/manifest.json:1-73](file://extension/manifest.json#L1-L73)

**Section sources**
- [server/requirements.txt:1-34](file://server/requirements.txt#L1-L34)
- [examguard-pro/package.json:13-28](file://examguard-pro/package.json#L13-L28)
- [extension/manifest.json:1-73](file://extension/manifest.json#L1-L73)

## Performance Considerations
- Vision engines:
  - MediaPipe Tasks API preferred; fallback to Haar cascades for environments without the Tasks model
  - YOLO inference throttled to ~10 FPS to maintain stability
  - CLAHE preprocessing improves low-light detection
- OCR:
  - Tesseract path configured for Windows; fallback mode when unavailable
- Transformer models:
  - CUDA-capable device preferred; otherwise CPU inference
  - Tokenizers loaded from checkpoints to avoid dynamic vocab generation overhead
- Extension:
  - MediaRecorder configured for VP8 and moderate bitrate to balance quality and bandwidth
  - WebRTC ICE candidates and SDP exchange for efficient streaming
- Backend:
  - Matplotlib backend set to Agg to avoid GUI/X11 issues in containers
  - SPA fallback ensures efficient asset serving

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
- Missing Tesseract:
  - Symptom: OCR returns a warning and zero risk
  - Resolution: Install Tesseract and configure the path
- MediaPipe Tasks model download failure:
  - Symptom: Falls back to Haar cascade
  - Resolution: Ensure network access and disk space for model download
- YOLO model not found:
  - Symptom: Object detection disabled
  - Resolution: Place the YOLO weights file at the expected path
- Supabase credentials missing:
  - Symptom: Warning printed and client remains None
  - Resolution: Set SUPABASE_URL and SUPABASE_KEY environment variables
- Render WebSocket timeouts:
  - Symptom: Periodic ping/pong required; heartbeat task scheduled
  - Resolution: Keep Render alive with periodic messages; verify CORS settings

**Section sources**
- [server/services/ocr.py:75-84](file://server/services/ocr.py#L75-L84)
- [server/services/face_detection.py:16-26](file://server/services/face_detection.py#L16-L26)
- [server/services/object_detection.py:23-26](file://server/services/object_detection.py#L23-L26)
- [server/supabase_client.py:12-17](file://server/supabase_client.py#L12-L17)
- [server/main.py:134-137](file://server/main.py#L134-L137)

## Conclusion
ExamGuard Pro leverages a modern, modular stack combining FastAPI, React 19, and a Chrome extension to deliver a comprehensive proctoring solution. Backend services integrate MediaPipe, YOLO, Tesseract, and custom Transformers for robust AI/ML capabilities. The system is containerized and deployable on Render with environment-driven configuration for Supabase and PostgreSQL. The architecture balances performance, scalability, and developer experience across frontend, backend, and extension layers.