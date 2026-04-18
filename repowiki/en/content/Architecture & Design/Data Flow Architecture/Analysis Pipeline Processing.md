# Analysis Pipeline Processing

<cite>
**Referenced Files in This Document**
- [pipeline.py](file://server/services/pipeline.py)
- [queue.py](file://server/tasks/queue.py)
- [worker.py](file://server/tasks/worker.py)
- [engine.py](file://server/scoring/engine.py)
- [calculator.py](file://server/scoring/calculator.py)
- [transformer_analysis.py](file://server/services/transformer_analysis.py)
- [anomaly.py](file://server/services/anomaly.py)
- [website_classification.py](file://server/services/website_classification.py)
- [face_detection.py](file://server/services/face_detection.py)
- [ocr.py](file://server/services/ocr.py)
- [realtime.py](file://server/services/realtime.py)
- [config.py](file://server/config.py)
- [analysis.py](file://server/models/analysis.py)
- [event.py](file://server/models/event.py)
- [session.py](file://server/models/session.py)
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
10. [Appendices](#appendices)

## Introduction
This document explains the AI/ML analysis pipeline powering ExamGuard Pro. It covers the event-driven architecture, queue-based processing, real-time scoring, and database integration. It documents specialized analysis modules (text similarity, URL categorization, vision-based anomaly detection, and transformer-based content analysis), risk scoring algorithms, thresholds, and decision-making for alert generation. It also describes batch processing strategies, real-time updates, and monitoring.

## Project Structure
The analysis pipeline spans several modules:
- Real-time event ingestion and routing via an asynchronous pipeline
- Background task processing via Celery workers
- Scoring engine computing engagement, relevance, effort, and risk
- Specialized AI/ML services for vision, OCR, URL classification, and transformer-based analysis
- Real-time broadcasting to dashboards and clients
- Data models and configuration for risk thresholds and categories

```mermaid
graph TB
subgraph "Event Ingestion"
EP["Extension/Client Events"]
Q["Async Pipeline Queue"]
end
subgraph "Processing"
P["AnalysisPipeline<br/>routes & updates"]
T["TransformerAnalyzer"]
A["AnomalyDetector"]
F["SecureVision"]
O["ScreenOCR"]
WC["WebsiteClassifier"]
end
subgraph "Scoring"
SE["ScoringEngine"]
RC["RiskCalculator"]
end
subgraph "Integration"
DB["Supabase/DB"]
WS["Realtime Manager"]
end
EP --> Q --> P
P --> T
P --> A
P --> F
P --> O
P --> WC
P --> DB
P --> WS
SE --> DB
RC --> DB
```

**Diagram sources**
- [pipeline.py:9-345](file://server/services/pipeline.py#L9-L345)
- [queue.py:11-75](file://server/tasks/queue.py#L11-L75)
- [worker.py:9-31](file://server/tasks/worker.py#L9-L31)
- [engine.py:373-445](file://server/scoring/engine.py#L373-L445)
- [calculator.py:161-207](file://server/scoring/calculator.py#L161-L207)
- [transformer_analysis.py:178-549](file://server/services/transformer_analysis.py#L178-L549)
- [anomaly.py:11-221](file://server/services/anomaly.py#L11-L221)
- [face_detection.py:27-126](file://server/services/face_detection.py#L27-L126)
- [ocr.py:20-121](file://server/services/ocr.py#L20-L121)
- [website_classification.py:50-100](file://server/services/website_classification.py#L50-L100)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)
- [config.py:58-205](file://server/config.py#L58-L205)

**Section sources**
- [pipeline.py:9-345](file://server/services/pipeline.py#L9-L345)
- [engine.py:373-445](file://server/scoring/engine.py#L373-L445)
- [calculator.py:161-207](file://server/scoring/calculator.py#L161-L207)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)

## Core Components
- AnalysisPipeline: Asynchronous event router and processor that enqueues events, routes to handlers, persists analysis results, and updates session risk.
- ScoringEngine: Pure calculation engine that recomputes engagement, relevance, effort, and risk from stored events and analyses.
- RiskCalculator: Computes risk breakdown and thresholds from event counts.
- TransformerAnalyzer: Loads and runs transformer-based models for URL classification, behavioral anomaly, and screen content classification.
- AnomalyDetector: Rule-based behavioral anomaly detection.
- SecureVision: Face detection and presence checks.
- ScreenOCR: OCR and forbidden keyword detection.
- WebsiteClassifier: Rule-based URL categorization.
- Realtime Manager: WebSocket broadcasting for dashboards and proctors.
- Configuration: Risk weights, thresholds, and URL category lists.

**Section sources**
- [pipeline.py:9-345](file://server/services/pipeline.py#L9-L345)
- [engine.py:373-445](file://server/scoring/engine.py#L373-L445)
- [calculator.py:161-207](file://server/scoring/calculator.py#L161-L207)
- [transformer_analysis.py:178-549](file://server/services/transformer_analysis.py#L178-L549)
- [anomaly.py:11-221](file://server/services/anomaly.py#L11-L221)
- [face_detection.py:27-126](file://server/services/face_detection.py#L27-L126)
- [ocr.py:20-121](file://server/services/ocr.py#L20-L121)
- [website_classification.py:50-100](file://server/services/website_classification.py#L50-L100)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)
- [config.py:58-205](file://server/config.py#L58-L205)

## Architecture Overview
The pipeline is event-driven and queue-based:
- Events arrive asynchronously and are queued.
- A background worker dequeues and processes events by type.
- Specialized analyzers produce results and risk contributions.
- Results are persisted and session risk is recalculated and broadcast.

```mermaid
sequenceDiagram
participant Ext as "Extension/Client"
participant Pipe as "AnalysisPipeline"
participant DB as "Supabase"
participant RT as "Realtime Manager"
Ext->>Pipe : "submit(event_data)"
Pipe->>Pipe : "enqueue(event)"
Pipe->>Pipe : "_worker() loop"
Pipe->>Pipe : "_process_event(event)"
alt "Text/Navigate/Face/Vision/Alert"
Pipe->>DB : "insert analysis_result"
Pipe->>RT : "broadcast dashboard update"
end
Pipe->>DB : "update session risk_score/risk_level"
Pipe->>RT : "broadcast risk_score_update"
```

**Diagram sources**
- [pipeline.py:25-96](file://server/services/pipeline.py#L25-L96)
- [pipeline.py:278-336](file://server/services/pipeline.py#L278-L336)
- [realtime.py:334-403](file://server/services/realtime.py#L334-L403)

## Detailed Component Analysis

### AnalysisPipeline
Responsibilities:
- Start/stop background worker
- Enqueue events and process with timeouts
- Route to specialized handlers by event type
- Persist analysis results and update session risk
- Broadcast real-time updates

Key routing:
- Text events: transformer screen content classification (when available)
- Navigation events: URL categorization and forbidden keyword checks
- Vision events: phone and face absence penalties and alerts
- Transformer alerts: plagiarism-like similarity adjustments
- Risk update: recalculation and level assignment

```mermaid
flowchart TD
Start(["Event Received"]) --> Type{"Event Type"}
Type --> |Text| Text["Text Handler<br/>Transformer screen classification"]
Type --> |Navigation| Nav["URL Visit Handler<br/>Forbidden keyword + category"]
Type --> |Vision| Vision["Vision Handler<br/>Phone/Face absence"]
Type --> |Alert| Alert["Transformer Alert Handler"]
Text --> Persist["Persist Analysis Result"]
Nav --> Persist
Vision --> Persist
Alert --> Persist
Persist --> Risk["Update Session Risk"]
Risk --> Broadcast["Broadcast to Dashboard/WebSocket"]
Broadcast --> End(["Done"])
```

**Diagram sources**
- [pipeline.py:74-336](file://server/services/pipeline.py#L74-L336)

**Section sources**
- [pipeline.py:25-345](file://server/services/pipeline.py#L25-L345)

### Transformer-Based Content Analysis
Capabilities:
- URL classification
- Behavioral anomaly detection from event sequences
- Screen content classification

Initialization and availability:
- Dynamically loads models and tokenizers from the transformer module
- Falls back to rule-based classification if models are unavailable

Classification outputs:
- Categories and risk scores mapped per class
- Confidence and method used

```mermaid
classDiagram
class TransformerAnalyzer {
+bool _url_initialized
+bool _behavior_initialized
+bool _screen_initialized
+classify_url(url) Dict
+predict_behavior_risk(events) Dict
+classify_screen_content(text) Dict
+get_status() Dict
}
class BehavioralAnomalyDetector {
+forward(event_ids, intervals) Tensor
}
class ScreenContentClassifier {
+forward(input_ids) Tensor
}
class URLClassifier {
+forward(input_ids) Tensor
}
TransformerAnalyzer --> BehavioralAnomalyDetector : "loads"
TransformerAnalyzer --> ScreenContentClassifier : "loads"
TransformerAnalyzer --> URLClassifier : "loads"
```

**Diagram sources**
- [transformer_analysis.py:178-549](file://server/services/transformer_analysis.py#L178-L549)

**Section sources**
- [transformer_analysis.py:178-549](file://server/services/transformer_analysis.py#L178-L549)

### URL Categorization and Navigation Handling
- Rule-based categorization using domain and keyword lists
- Forbidden keyword detection for URLs
- Risk impact assignment and session updates

```mermaid
flowchart TD
UStart["URL Visit Event"] --> Parse["Parse URL"]
Parse --> CheckFK["Check Forbidden Keywords"]
CheckFK --> Cat["Assign Category"]
Cat --> Impact["Compute Risk Impact"]
Impact --> Save["Insert Analysis Result"]
Save --> Update["Update Session Counts/Risk"]
Update --> Alert["Optional Forbidden Site Alert"]
Alert --> Done["Done"]
```

**Diagram sources**
- [pipeline.py:149-220](file://server/services/pipeline.py#L149-L220)
- [config.py:84-163](file://server/config.py#L84-L163)

**Section sources**
- [pipeline.py:149-220](file://server/services/pipeline.py#L149-L220)
- [config.py:84-163](file://server/config.py#L84-L163)

### Vision-Based Anomaly Detection
- Face detection using MediaPipe Tasks or Haar cascades
- Presence/absence violations and penalties
- Phone/object detection via object detectors
- Immediate alerts and session updates

```mermaid
sequenceDiagram
participant Cam as "Webcam Frames"
participant SV as "SecureVision"
participant RT as "Realtime Manager"
participant DB as "Supabase"
Cam->>SV : "analyze_frame(frame)"
SV-->>Cam : "results {violations, detections}"
alt "Phone Detected"
SV->>RT : "broadcast anomaly_alert PHONE_DETECTED"
SV->>DB : "update session risk_level=risk"
else "Face Absent"
SV->>DB : "increment absence counter"
SV->>RT : "broadcast anomaly_alert FACE_ABSENT"
end
```

**Diagram sources**
- [face_detection.py:64-126](file://server/services/face_detection.py#L64-L126)
- [pipeline.py:246-277](file://server/services/pipeline.py#L246-L277)
- [realtime.py:412-417](file://server/services/realtime.py#L412-L417)

**Section sources**
- [face_detection.py:27-126](file://server/services/face_detection.py#L27-L126)
- [pipeline.py:246-277](file://server/services/pipeline.py#L246-L277)

### OCR and Forbidden Keyword Detection
- Extracts text from screenshots and detects forbidden keywords
- Computes risk contribution based on keyword matches
- Provides fallback when OCR is unavailable

```mermaid
flowchart TD
S["Screenshot"] --> OCR["ScreenOCR.analyze()"]
OCR --> Found{"Forbidden Keywords?"}
Found --> |Yes| Risk["Compute Risk Score"]
Found --> |No| Zero["Risk Score = 0"]
Risk --> Save["Persist OCR Analysis"]
Zero --> Save
```

**Diagram sources**
- [ocr.py:29-84](file://server/services/ocr.py#L29-L84)
- [pipeline.py:149-220](file://server/services/pipeline.py#L149-L220)

**Section sources**
- [ocr.py:20-121](file://server/services/ocr.py#L20-L121)
- [pipeline.py:149-220](file://server/services/pipeline.py#L149-L220)

### Real-Time Broadcasting and Alerts
- WebSocket rooms per session
- Broadcasts risk updates, anomalies, and analysis results
- Severity levels guide alerting

```mermaid
sequenceDiagram
participant PM as "Pipeline"
participant RM as "Realtime Manager"
participant Dash as "Dashboard"
participant Proctor as "Proctor"
participant Student as "Student"
PM->>RM : "broadcast_event(...)"
RM->>Dash : "send_json(alert/risk)"
RM->>Proctor : "send_json(alert/risk)"
RM->>Student : "send_json(alert/risk)"
```

**Diagram sources**
- [pipeline.py:306-336](file://server/services/pipeline.py#L306-L336)
- [realtime.py:334-403](file://server/services/realtime.py#L334-L403)

**Section sources**
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)
- [pipeline.py:306-336](file://server/services/pipeline.py#L306-L336)

### Risk Scoring Algorithms and Decision-Making
- Engagement: penalizes tab switches, window blurs, distraction time, flagged tabs; rewards face presence
- Relevance: penalizes forbidden site visits and OCR forbidden keywords; considers exam time ratio
- Effort: productivity ratio, bonus for time spent, blending with extension estimates; copy/paste penalties
- Risk: weighted combination of vision impact, OCR-derived content relevance, anomaly score, browsing risk; additive bonuses for forbidden categories; level thresholds

```mermaid
flowchart TD
Load["Load Session/Events/Analyses"] --> Eng["Compute Engagement"]
Load --> Rel["Compute Content Relevance"]
Load --> Eff["Compute Effort Alignment"]
Load --> An["Compute Anomaly Score"]
Eng --> Risk["Compute Risk Score"]
Rel --> Risk
Eff --> Risk
An --> Risk
Risk --> Level["Apply Risk Level Thresholds"]
Level --> Persist["Persist Scores"]
```

**Diagram sources**
- [engine.py:382-445](file://server/scoring/engine.py#L382-L445)

**Section sources**
- [engine.py:27-445](file://server/scoring/engine.py#L27-L445)
- [calculator.py:161-207](file://server/scoring/calculator.py#L161-L207)
- [config.py:191-197](file://server/config.py#L191-L197)

### Batch Processing and Real-Time Updates
- Pipeline processes events in batches via queue and updates risk after each event
- ScoringEngine recomputes all metrics periodically or on-demand
- Real-time updates are pushed immediately upon risk changes or alerts

**Section sources**
- [pipeline.py:55-96](file://server/services/pipeline.py#L55-L96)
- [engine.py:382-445](file://server/scoring/engine.py#L382-L445)
- [realtime.py:334-403](file://server/services/realtime.py#L334-L403)

## Dependency Analysis
Inter-module dependencies:
- AnalysisPipeline depends on Supabase for persistence and Realtime Manager for broadcasting
- ScoringEngine and RiskCalculator depend on models and configuration
- TransformerAnalyzer depends on external transformer module and checkpoints
- Vision and OCR services depend on external libraries (MediaPipe, OpenCV, Tesseract)
- Realtime Manager coordinates WebSocket connections and event routing

```mermaid
graph LR
Pipe["AnalysisPipeline"] --> DB["Supabase"]
Pipe --> RT["Realtime Manager"]
Pipe --> TA["TransformerAnalyzer"]
Pipe --> AD["AnomalyDetector"]
Pipe --> SV["SecureVision"]
Pipe --> OCR["ScreenOCR"]
Pipe --> WC["WebsiteClassifier"]
SE["ScoringEngine"] --> DB
RC["RiskCalculator"] --> DB
TA --> TR["Transformer Module"]
SV --> MP["MediaPipe/OpenCV"]
OCR --> PT["PyTesseract/PIL"]
```

**Diagram sources**
- [pipeline.py:9-345](file://server/services/pipeline.py#L9-L345)
- [engine.py:373-445](file://server/scoring/engine.py#L373-L445)
- [calculator.py:161-207](file://server/scoring/calculator.py#L161-L207)
- [transformer_analysis.py:26-48](file://server/services/transformer_analysis.py#L26-L48)
- [face_detection.py:11-26](file://server/services/face_detection.py#L11-L26)
- [ocr.py:11-17](file://server/services/ocr.py#L11-L17)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)

**Section sources**
- [pipeline.py:9-345](file://server/services/pipeline.py#L9-L345)
- [engine.py:373-445](file://server/scoring/engine.py#L373-L445)
- [calculator.py:161-207](file://server/scoring/calculator.py#L161-L207)
- [transformer_analysis.py:26-48](file://server/services/transformer_analysis.py#L26-L48)
- [face_detection.py:11-26](file://server/services/face_detection.py#L11-L26)
- [ocr.py:11-17](file://server/services/ocr.py#L11-L17)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)

## Performance Considerations
- Asynchronous processing: Pipeline uses asyncio queues and non-blocking I/O to handle bursts
- External model availability: TransformerAnalyzer gracefully falls back when models are unavailable
- Resource constraints: Vision and OCR services may degrade gracefully if libraries are missing
- Database writes: Minimize write frequency by batching updates and leveraging real-time broadcasts
- WebSocket scalability: Room-based broadcasting reduces unnecessary fan-out

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and remedies:
- Missing OCR/Tesseract: OCR falls back to a warning and zero risk contribution
- Missing MediaPipe/Haar: Vision backend falls back to minimal/no detection
- Transformer models not found: URL classification falls back to rule-based
- WebSocket errors: Pipeline logs and continues; check connectivity and room membership
- Risk update failures: Pipeline logs and continues; verify Supabase connectivity

**Section sources**
- [ocr.py:75-84](file://server/services/ocr.py#L75-L84)
- [face_detection.py:11-26](file://server/services/face_detection.py#L11-L26)
- [transformer_analysis.py:321-326](file://server/services/transformer_analysis.py#L321-L326)
- [pipeline.py:306-336](file://server/services/pipeline.py#L306-L336)

## Conclusion
ExamGuard Pro’s analysis pipeline combines event-driven orchestration, specialized AI/ML modules, and real-time scoring to continuously monitor and assess session risk. The system balances accuracy with resilience by falling back to rule-based or lightweight modes when advanced models are unavailable. Real-time updates keep stakeholders informed, while robust scoring algorithms provide transparent risk assessments.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Data Models Overview
```mermaid
erDiagram
EVENT {
uuid id PK
string session_id
string event_type
datetime timestamp
int client_timestamp
json data
int risk_weight
}
ANALYSIS_RESULT {
uuid id PK
string session_id
string analysis_type
datetime timestamp
string source_file
string source_url
json result_data
boolean face_detected
float face_confidence
string detected_text
json forbidden_keywords_found
float similarity_score
string matched_content
float risk_score_added
}
EXAM_SESSION {
uuid id PK
string student_id
string student_name
string exam_id
datetime started_at
datetime ended_at
boolean is_active
string status
float risk_score
string risk_level
float engagement_score
float content_relevance
float effort_alignment
int tab_switch_count
int copy_count
int face_absence_count
int forbidden_site_count
int phone_detection_count
int total_events
}
EVENT ||--o{ ANALYSIS_RESULT : "generates"
EXAM_SESSION ||--o{ ANALYSIS_RESULT : "accumulates"
EXAM_SESSION ||--o{ EVENT : "contains"
```

**Diagram sources**
- [event.py:6-30](file://server/models/event.py#L6-L30)
- [analysis.py:6-49](file://server/models/analysis.py#L6-L49)
- [session.py:15-63](file://server/models/session.py#L15-L63)

### Example Workflows

#### Text Analysis Workflow
```mermaid
sequenceDiagram
participant Ext as "Extension"
participant Pipe as "AnalysisPipeline"
participant TA as "TransformerAnalyzer"
participant DB as "Supabase"
participant RT as "Realtime Manager"
Ext->>Pipe : "submit({type : TEXT, data : {text}})"
Pipe->>TA : "classify_screen_content(text)"
TA-->>Pipe : "risk_category, score"
Pipe->>DB : "insert analysis_result"
Pipe->>RT : "broadcast text_analysis"
Pipe->>DB : "update session risk"
Pipe->>RT : "broadcast risk_score_update"
```

**Diagram sources**
- [pipeline.py:97-148](file://server/services/pipeline.py#L97-L148)
- [transformer_analysis.py:474-524](file://server/services/transformer_analysis.py#L474-L524)

#### Navigation and Forbidden Site Workflow
```mermaid
sequenceDiagram
participant Ext as "Extension"
participant Pipe as "AnalysisPipeline"
participant DB as "Supabase"
participant RT as "Realtime Manager"
Ext->>Pipe : "submit({type : NAVIGATION, data : {url}})"
Pipe->>Pipe : "rule-based categorize"
Pipe->>DB : "insert analysis_result"
Pipe->>DB : "update session forbidden_site_count/risk"
Pipe->>RT : "broadcast forbidden_site"
Pipe->>RT : "broadcast risk_score_update"
```

**Diagram sources**
- [pipeline.py:149-220](file://server/services/pipeline.py#L149-L220)

#### Vision Anomaly Workflow
```mermaid
sequenceDiagram
participant Cam as "Webcam Frames"
participant SV as "SecureVision"
participant Pipe as "AnalysisPipeline"
participant DB as "Supabase"
participant RT as "Realtime Manager"
Cam->>SV : "analyze_frame(frame)"
SV-->>Pipe : "violations"
Pipe->>DB : "update session counters/flags"
Pipe->>RT : "broadcast anomaly_alert"
```

**Diagram sources**
- [face_detection.py:64-126](file://server/services/face_detection.py#L64-L126)
- [pipeline.py:246-277](file://server/services/pipeline.py#L246-L277)
- [realtime.py:412-417](file://server/services/realtime.py#L412-L417)

### Analysis Result Structures
- Text Analysis: includes similarity and transformer classification outputs
- URL Visit: includes category, domain, forbidden keyword matches
- Vision: includes violations and integrity impact
- OCR: includes detected text, forbidden keywords, and computed risk

**Section sources**
- [pipeline.py:123-144](file://server/services/pipeline.py#L123-L144)
- [pipeline.py:189-202](file://server/services/pipeline.py#L189-L202)
- [pipeline.py:246-277](file://server/services/pipeline.py#L246-L277)
- [ocr.py:57-73](file://server/services/ocr.py#L57-L73)