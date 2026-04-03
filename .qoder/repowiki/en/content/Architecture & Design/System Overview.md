# System Overview

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [server/main.py](file://server/main.py)
- [server/services/realtime.py](file://server/services/realtime.py)
- [server/services/pipeline.py](file://server/services/pipeline.py)
- [server/services/face_detection.py](file://server/services/face_detection.py)
- [server/services/transformer_analysis.py](file://server/services/transformer_analysis.py)
- [extension/background.js](file://extension/background.js)
- [extension/content.js](file://extension/content.js)
- [extension/capture.js](file://extension/capture.js)
- [transformer/model/transformer.py](file://transformer/model/transformer.py)
- [transformer/inference.py](file://transformer/inference.py)
- [examguard-pro/src/App.tsx](file://examguard-pro/src/App.tsx)
- [examguard-pro/src/hooks/useWebSocket.ts](file://examguard-pro/src/hooks/useWebSocket.ts)
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
ExamGuard Pro is an AI-powered exam proctoring system designed to monitor online examinations through multi-modal analysis. It combines a FastAPI backend, a React dashboard, a Chrome extension, and AI/ML components to provide real-time monitoring, risk scoring, and alerts. The system ensures academic integrity by detecting suspicious activities such as tab switching, copy/paste, unauthorized device presence, and potentially plagiarized content.

The system’s purpose is to serve as a central coordinator (FastAPI backend) that orchestrates:
- Real-time monitoring manager (WebSocket-based)
- Analysis pipeline (multi-modal AI/ML processing)
- Secure vision engine (face detection and anomalies)
- Transformer-based NLP analysis (text and URL classification)
- Chrome extension for browser event capture and live streaming
- React dashboard for real-time visualization and control

## Project Structure
The repository is organized into four primary areas:
- server/: FastAPI backend with API endpoints, services, and real-time monitoring
- examguard-pro/: React dashboard with routing, context providers, and WebSocket integration
- extension/: Chrome extension (Manifest V3) for capturing browser events, webcam/screen streams, and WebRTC signaling
- transformer/: Custom Transformer models and training infrastructure for NLP tasks

```mermaid
graph TB
subgraph "Backend (FastAPI)"
A_main["server/main.py"]
A_rt["server/services/realtime.py"]
A_pipe["server/services/pipeline.py"]
A_vision["server/services/face_detection.py"]
A_trans["server/services/transformer_analysis.py"]
end
subgraph "Frontend (React)"
F_app["examguard-pro/src/App.tsx"]
F_ws["examguard-pro/src/hooks/useWebSocket.ts"]
end
subgraph "Chrome Extension"
E_bg["extension/background.js"]
E_ct["extension/content.js"]
E_cap["extension/capture.js"]
end
subgraph "AI/ML"
T_model["transformer/model/transformer.py"]
T_inf["transformer/inference.py"]
end
E_bg --> A_main
E_ct --> E_bg
E_cap --> E_bg
A_main --> A_rt
A_main --> A_pipe
A_main --> A_vision
A_main --> A_trans
A_pipe --> A_trans
A_rt --> F_app
F_app --> F_ws
A_trans --> T_model
A_trans --> T_inf
```

**Diagram sources**
- [server/main.py:1-647](file://server/main.py#L1-L647)
- [server/services/realtime.py:1-642](file://server/services/realtime.py#L1-L642)
- [server/services/pipeline.py:1-342](file://server/services/pipeline.py#L1-L342)
- [server/services/face_detection.py:1-109](file://server/services/face_detection.py#L1-L109)
- [server/services/transformer_analysis.py:1-549](file://server/services/transformer_analysis.py#L1-L549)
- [extension/background.js:1-1998](file://extension/background.js#L1-L1998)
- [extension/content.js:1-473](file://extension/content.js#L1-L473)
- [extension/capture.js:1-352](file://extension/capture.js#L1-L352)
- [transformer/model/transformer.py:1-606](file://transformer/model/transformer.py#L1-L606)
- [transformer/inference.py:1-159](file://transformer/inference.py#L1-L159)
- [examguard-pro/src/App.tsx:1-92](file://examguard-pro/src/App.tsx#L1-L92)
- [examguard-pro/src/hooks/useWebSocket.ts:1-110](file://examguard-pro/src/hooks/useWebSocket.ts#L1-L110)

**Section sources**
- [README.md:1-92](file://README.md#L1-L92)

## Core Components
- FastAPI Backend (server/main.py): Central coordinator that initializes the secure vision engine, gaze service, real-time monitoring manager, and analysis pipeline. It exposes REST endpoints and WebSocket endpoints for real-time communication with the dashboard and extension.
- Real-time Monitoring Manager (server/services/realtime.py): Manages WebSocket connections, rooms, event broadcasting, and live video streaming. It integrates AI callbacks for frame extraction and anomaly detection.
- Analysis Pipeline (server/services/pipeline.py): Processes events asynchronously, performs transformer-based analysis, updates session risk scores, and pushes real-time updates to dashboards.
- Secure Vision Engine (server/services/face_detection.py): Provides face detection and anomaly detection using MediaPipe Tasks API or Haar cascades.
- Transformer Analyzer (server/services/transformer_analysis.py): Loads and runs trained Transformer models for URL classification, behavioral anomaly detection, and screen content classification.
- React Dashboard (examguard-pro/src/App.tsx, hooks/useWebSocket.ts): Provides routing, layout, and real-time WebSocket integration for live monitoring and alerts.
- Chrome Extension (extension/background.js, content.js, capture.js): Captures browser events, screen/webcam streams, and manages WebRTC signaling to the backend.

**Section sources**
- [server/main.py:110-165](file://server/main.py#L110-L165)
- [server/services/realtime.py:102-138](file://server/services/realtime.py#L102-L138)
- [server/services/pipeline.py:9-53](file://server/services/pipeline.py#L9-L53)
- [server/services/face_detection.py:27-50](file://server/services/face_detection.py#L27-L50)
- [server/services/transformer_analysis.py:178-206](file://server/services/transformer_analysis.py#L178-L206)
- [examguard-pro/src/App.tsx:67-91](file://examguard-pro/src/App.tsx#L67-L91)
- [examguard-pro/src/hooks/useWebSocket.ts:18-78](file://examguard-pro/src/hooks/useWebSocket.ts#L18-L78)
- [extension/background.js:12-19](file://extension/background.js#L12-L19)
- [extension/content.js:34-73](file://extension/content.js#L34-L73)
- [extension/capture.js:6-24](file://extension/capture.js#L6-L24)

## Architecture Overview
The system follows a multi-layered architecture:
- Backend layer: FastAPI application with middleware, routers, and WebSocket endpoints.
- Real-time layer: WebSocket-based event broadcasting and room management.
- AI/ML layer: Secure vision engine, object detection, and transformer-based NLP analysis.
- Frontend layer: React dashboard with real-time updates and controls.
- Extension layer: Chrome extension capturing browser events, screen/webcam streams, and WebRTC signaling.

```mermaid
graph TB
subgraph "Client Layer"
D_board["React Dashboard<br/>Real-time Updates"]
Ext["Chrome Extension<br/>Browser Events & Streams"]
end
subgraph "Backend Layer"
API["FastAPI App<br/>REST + WebSockets"]
RTM["RealtimeMonitoringManager<br/>Rooms & Broadcast"]
PIPE["AnalysisPipeline<br/>Async Processing"]
VISION["SecureVision<br/>Face Detection"]
TRANS["TransformerAnalyzer<br/>NLP Models"]
end
subgraph "AI/ML Layer"
MP["MediaPipe Tasks API"]
YOLO["YOLO Object Detection"]
TRFM["Custom Transformer Models"]
end
D_board --> |"WebSocket"| API
Ext --> |"WebSocket"| API
API --> RTM
API --> PIPE
API --> VISION
API --> TRANS
PIPE --> TRANS
VISION --> MP
PIPE --> YOLO
TRANS --> TRFM
```

**Diagram sources**
- [server/main.py:248-484](file://server/main.py#L248-L484)
- [server/services/realtime.py:102-138](file://server/services/realtime.py#L102-L138)
- [server/services/pipeline.py:74-96](file://server/services/pipeline.py#L74-L96)
- [server/services/face_detection.py:27-50](file://server/services/face_detection.py#L27-L50)
- [server/services/transformer_analysis.py:178-206](file://server/services/transformer_analysis.py#L178-L206)

## Detailed Component Analysis

### Backend Coordinator (FastAPI)
The backend initializes the secure vision engine, gaze service, real-time monitoring manager, and analysis pipeline during application startup. It registers authentication and API routers, mounts static files for uploads, and exposes health checks and statistics endpoints. WebSocket endpoints handle connections for dashboards, proctors, and students, enabling real-time alerts and live streaming.

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "FastAPI App"
participant RTM as "RealtimeMonitoringManager"
participant PIPE as "AnalysisPipeline"
participant EXT as "Chrome Extension"
Client->>API : "Connect WebSocket /ws/dashboard"
API->>RTM : "connect_dashboard()"
RTM-->>Client : "Connection accepted"
Client->>API : "Connect WebSocket /ws/student/{student_id}"
API->>RTM : "connect_student(student_id, session_id)"
RTM-->>Client : "Connection accepted"
EXT->>API : "WebSocket /ws/student (binary chunks)"
API->>RTM : "broadcast_binary(session_id, data)"
RTM->>PIPE : "Queue event for analysis"
PIPE-->>RTM : "Processed result"
RTM-->>Client : "Real-time alert"
```

**Diagram sources**
- [server/main.py:274-473](file://server/main.py#L274-L473)
- [server/services/realtime.py:213-273](file://server/services/realtime.py#L213-L273)
- [server/services/pipeline.py:44-66](file://server/services/pipeline.py#L44-L66)

**Section sources**
- [server/main.py:110-165](file://server/main.py#L110-L165)
- [server/main.py:248-484](file://server/main.py#L248-L484)

### Real-time Monitoring Manager
The real-time monitoring manager handles multi-room WebSocket connections, broadcasts events to dashboards and proctors, and manages live video streaming. It integrates AI callbacks for frame extraction and anomaly detection, updating session risk levels and pushing alerts to clients.

```mermaid
classDiagram
class RealtimeMonitoringManager {
+connect_dashboard(websocket)
+connect_proctor(websocket, session_id)
+connect_student(websocket, student_id, session_id)
+broadcast_event(event_type, student_id, session_id, data, alert_level)
+broadcast_to_session(session_id, message)
+broadcast_binary(session_id, data)
+send_alert(alert_type, message, student_id, session_id, severity, data)
+start_heartbeat(interval)
+get_stats()
}
class RoomManager {
+join_room(session_id, websocket)
+leave_room(session_id, websocket)
+get_room_members(session_id)
}
RealtimeMonitoringManager --> RoomManager : "uses"
```

**Diagram sources**
- [server/services/realtime.py:102-138](file://server/services/realtime.py#L102-L138)
- [server/services/realtime.py:81-100](file://server/services/realtime.py#L81-L100)

**Section sources**
- [server/services/realtime.py:102-138](file://server/services/realtime.py#L102-L138)
- [server/services/realtime.py:334-403](file://server/services/realtime.py#L334-L403)

### Analysis Pipeline
The analysis pipeline processes events asynchronously, routes them to appropriate handlers, and updates session risk scores. It performs transformer-based analysis for text and URL events, updates database records, and pushes real-time updates to dashboards.

```mermaid
flowchart TD
Start([Event Received]) --> Route["Route to Handler"]
Route --> TextEvt{"Text Event?"}
TextEvt --> |Yes| TextAnalyze["Transformer Screen Content Analysis"]
TextEvt --> |No| NavEvt{"Navigation Event?"}
NavEvt --> |Yes| UrlClassify["URL Visit Classification"]
NavEvt --> |No| VisionEvt{"Vision Event?"}
VisionEvt --> |Yes| UpdateRisk["Update Session Risk"]
VisionEvt --> |No| FocusEvt{"Focus Event?"}
FocusEvt --> |Yes| UpdateRisk
FocusEvt --> |No| Done([Done])
TextAnalyze --> PushDash["Push to Dashboard"]
UrlClassify --> UpdateRisk
UpdateRisk --> PushDash
PushDash --> Done
```

**Diagram sources**
- [server/services/pipeline.py:74-96](file://server/services/pipeline.py#L74-L96)
- [server/services/pipeline.py:97-148](file://server/services/pipeline.py#L97-L148)
- [server/services/pipeline.py:149-220](file://server/services/pipeline.py#L149-L220)
- [server/services/pipeline.py:246-277](file://server/services/pipeline.py#L246-L277)

**Section sources**
- [server/services/pipeline.py:9-53](file://server/services/pipeline.py#L9-L53)
- [server/services/pipeline.py:74-96](file://server/services/pipeline.py#L74-L96)

### Secure Vision Engine
The secure vision engine provides face detection and anomaly detection using MediaPipe Tasks API or Haar cascades. It detects multiple faces, absence of faces, and generates violations with integrity impact scores.

```mermaid
classDiagram
class SecureVision {
+analyze_frame(frame) Dict
-_analyze_tasks(frame, results) Dict
-_analyze_haar(frame, results) Dict
}
```

**Diagram sources**
- [server/services/face_detection.py:27-50](file://server/services/face_detection.py#L27-L50)

**Section sources**
- [server/services/face_detection.py:27-50](file://server/services/face_detection.py#L27-L50)

### Transformer-based NLP Analysis
The transformer analyzer loads trained models for URL classification, behavioral anomaly detection, and screen content classification. It provides risk scores and confidence levels for each classification.

```mermaid
classDiagram
class TransformerAnalyzer {
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
- [server/services/transformer_analysis.py:178-206](file://server/services/transformer_analysis.py#L178-L206)
- [server/services/transformer_analysis.py:54-90](file://server/services/transformer_analysis.py#L54-L90)
- [server/services/transformer_analysis.py:92-138](file://server/services/transformer_analysis.py#L92-L138)
- [server/services/transformer_analysis.py:116-138](file://server/services/transformer_analysis.py#L116-L138)

**Section sources**
- [server/services/transformer_analysis.py:178-206](file://server/services/transformer_analysis.py#L178-L206)
- [server/services/transformer_analysis.py:332-394](file://server/services/transformer_analysis.py#L332-L394)
- [server/services/transformer_analysis.py:400-468](file://server/services/transformer_analysis.py#L400-L468)
- [server/services/transformer_analysis.py:474-523](file://server/services/transformer_analysis.py#L474-L523)

### React Dashboard
The React dashboard provides routing, layout, and real-time WebSocket integration. It subscribes to specific exam rooms and displays alerts and analytics in real-time.

```mermaid
sequenceDiagram
participant UI as "React Dashboard"
participant WS as "WebSocket Hook"
participant API as "FastAPI WebSocket"
UI->>WS : "connect()"
WS->>API : "WebSocket /ws/dashboard"
API-->>WS : "Connection accepted"
WS->>API : "subscribe : {roomId}"
API-->>WS : "Subscribed"
API-->>WS : "Event data"
WS-->>UI : "Update state"
```

**Diagram sources**
- [examguard-pro/src/App.tsx:67-91](file://examguard-pro/src/App.tsx#L67-L91)
- [examguard-pro/src/hooks/useWebSocket.ts:18-78](file://examguard-pro/src/hooks/useWebSocket.ts#L18-L78)

**Section sources**
- [examguard-pro/src/App.tsx:67-91](file://examguard-pro/src/App.tsx#L67-L91)
- [examguard-pro/src/hooks/useWebSocket.ts:18-78](file://examguard-pro/src/hooks/useWebSocket.ts#L18-L78)

### Chrome Extension
The Chrome extension captures browser events, screen/webcam streams, and manages WebRTC signaling. It communicates with the background script to synchronize session state and send alerts to the backend.

```mermaid
sequenceDiagram
participant BG as "Background Script"
participant CT as "Content Script"
participant CAP as "Capture Module"
participant API as "FastAPI WebSocket"
BG->>CT : "START_EXAM"
CT->>CAP : "startAll()"
CAP->>BG : "STREAM_CHUNK (binary)"
BG->>API : "WebSocket /ws/student (binary)"
CT->>BG : "BEHAVIOR_ALERT"
BG->>API : "WebSocket /ws/student (event)"
```

**Diagram sources**
- [extension/background.js:52-166](file://extension/background.js#L52-L166)
- [extension/content.js:367-381](file://extension/content.js#L367-L381)
- [extension/capture.js:175-203](file://extension/capture.js#L175-L203)
- [server/main.py:393-473](file://server/main.py#L393-L473)

**Section sources**
- [extension/background.js:12-19](file://extension/background.js#L12-L19)
- [extension/content.js:34-73](file://extension/content.js#L34-L73)
- [extension/capture.js:6-24](file://extension/capture.js#L6-L24)
- [server/main.py:393-473](file://server/main.py#L393-L473)

## Dependency Analysis
The system exhibits clear separation of concerns:
- Backend depends on real-time manager and analysis pipeline for orchestration.
- Real-time manager depends on frame extractor and AI engines for live analysis.
- Analysis pipeline depends on transformer analyzer and database for updates.
- React dashboard depends on WebSocket hook for real-time updates.
- Chrome extension depends on background script for coordination and on capture module for media.

```mermaid
graph TB
BG["extension/background.js"] --> API["server/main.py"]
CT["extension/content.js"] --> BG
CAP["extension/capture.js"] --> BG
API --> RTM["server/services/realtime.py"]
API --> PIPE["server/services/pipeline.py"]
API --> VISION["server/services/face_detection.py"]
API --> TRANS["server/services/transformer_analysis.py"]
PIPE --> TRANS
TRANS --> TRFM["transformer/model/transformer.py"]
DASH["examguard-pro/src/App.tsx"] --> WS["examguard-pro/src/hooks/useWebSocket.ts"]
WS --> API
```

**Diagram sources**
- [extension/background.js:12-19](file://extension/background.js#L12-L19)
- [server/main.py:248-484](file://server/main.py#L248-L484)
- [server/services/realtime.py:102-138](file://server/services/realtime.py#L102-L138)
- [server/services/pipeline.py:74-96](file://server/services/pipeline.py#L74-L96)
- [server/services/transformer_analysis.py:178-206](file://server/services/transformer_analysis.py#L178-L206)
- [transformer/model/transformer.py:17-50](file://transformer/model/transformer.py#L17-L50)
- [examguard-pro/src/App.tsx:67-91](file://examguard-pro/src/App.tsx#L67-L91)
- [examguard-pro/src/hooks/useWebSocket.ts:18-78](file://examguard-pro/src/hooks/useWebSocket.ts#L18-L78)

**Section sources**
- [server/main.py:110-165](file://server/main.py#L110-L165)
- [server/services/realtime.py:102-138](file://server/services/realtime.py#L102-L138)
- [server/services/pipeline.py:9-53](file://server/services/pipeline.py#L9-L53)
- [server/services/transformer_analysis.py:178-206](file://server/services/transformer_analysis.py#L178-L206)
- [transformer/model/transformer.py:17-50](file://transformer/model/transformer.py#L17-L50)
- [examguard-pro/src/App.tsx:67-91](file://examguard-pro/src/App.tsx#L67-L91)
- [examguard-pro/src/hooks/useWebSocket.ts:18-78](file://examguard-pro/src/hooks/useWebSocket.ts#L18-L78)

## Performance Considerations
- Asynchronous processing: The analysis pipeline uses an asynchronous queue to process events efficiently without blocking the main thread.
- Efficient WebSocket broadcasting: The real-time manager maintains separate sets for dashboards, proctors, and students, minimizing unnecessary broadcasts.
- Adaptive capture: The extension adjusts capture quality and handles errors gracefully to reduce bandwidth and improve reliability.
- Model loading: The transformer analyzer loads models lazily and caches tokenizers to minimize initialization overhead.
- Heartbeat monitoring: The real-time manager sends periodic heartbeats to keep connections alive and monitor system health.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- WebSocket connection failures: The React WebSocket hook implements exponential backoff and reconnection attempts. Verify the WebSocket URL and network connectivity.
- Extension context invalidated: The content script catches “context invalidated” errors and stops monitoring when the extension is reloaded.
- Media permissions: Ensure screen and camera permissions are granted; the capture module handles stream end events and notifies the background script.
- AI model availability: The transformer analyzer falls back to rule-based classification if models are unavailable. Check model checkpoints and tokenizer files.
- Database connectivity: The backend uses Supabase; verify credentials and network access.

**Section sources**
- [examguard-pro/src/hooks/useWebSocket.ts:60-78](file://examguard-pro/src/hooks/useWebSocket.ts#L60-L78)
- [extension/content.js:5-26](file://extension/content.js#L5-L26)
- [extension/capture.js:113-140](file://extension/capture.js#L113-L140)
- [server/services/transformer_analysis.py:332-358](file://server/services/transformer_analysis.py#L332-L358)

## Conclusion
ExamGuard Pro provides a comprehensive, multi-modal exam proctoring solution that integrates a FastAPI backend, real-time monitoring manager, analysis pipeline, secure vision engine, and transformer-based NLP analysis with a React dashboard and Chrome extension. The system’s layered architecture enables scalable, real-time monitoring and alerting, ensuring academic integrity during online examinations.