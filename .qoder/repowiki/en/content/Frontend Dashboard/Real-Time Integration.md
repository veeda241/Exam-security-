# Real-Time Integration

<cite>
**Referenced Files in This Document**
- [useWebSocket.ts](file://examguard-pro/src/hooks/useWebSocket.ts)
- [config.ts](file://examguard-pro/src/config.ts)
- [Dashboard.tsx](file://examguard-pro/src/components/Dashboard.tsx)
- [SessionDetail.tsx](file://examguard-pro/src/components/SessionDetail.tsx)
- [main.py](file://server/main.py)
- [realtime.py](file://server/services/realtime.py)
- [background.js](file://extension/background.js)
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
This document explains the real-time integration for the ExamGuard Pro React dashboard. It covers WebSocket connection establishment, message handling, room-based subscriptions, and real-time data synchronization patterns. It documents the useWebSocket custom hook, connection lifecycle management, error recovery strategies, event-driven UI updates, optimistic updates, and debugging techniques. It also describes the server-side real-time broadcasting and room management.

## Project Structure
The real-time system spans three layers:
- Frontend React hooks and components that establish WebSocket connections and render live data.
- A shared WebSocket manager that centralizes connection state, subscriptions, and reconnection logic.
- Backend FastAPI WebSocket endpoints and a real-time manager that broadcast events to dashboards, proctors, and students.

```mermaid
graph TB
subgraph "Frontend"
Hook["useWebSocket.ts<br/>WebSocketManager"]
Cfg["config.ts<br/>wsUrl resolution"]
Dash["Dashboard.tsx<br/>/dashboard room"]
Sess["SessionDetail.tsx<br/>per-session rooms"]
Ext["background.js<br/>extension signaling"]
end
subgraph "Backend"
WSMain["server/main.py<br/>/ws/dashboard, /ws/proctor, /ws/student"]
RT["server/services/realtime.py<br/>RealtimeMonitoringManager"]
end
Cfg --> Hook
Dash --> Hook
Sess --> Hook
Hook --> WSMain
WSMain --> RT
Ext --> WSMain
```

**Diagram sources**
- [useWebSocket.ts:1-175](file://examguard-pro/src/hooks/useWebSocket.ts#L1-L175)
- [config.ts:1-12](file://examguard-pro/src/config.ts#L1-L12)
- [Dashboard.tsx:30-35](file://examguard-pro/src/components/Dashboard.tsx#L30-L35)
- [SessionDetail.tsx:22-35](file://examguard-pro/src/components/SessionDetail.tsx#L22-L35)
- [main.py:275-474](file://server/main.py#L275-L474)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)
- [background.js:114-152](file://extension/background.js#L114-L152)

**Section sources**
- [useWebSocket.ts:1-175](file://examguard-pro/src/hooks/useWebSocket.ts#L1-L175)
- [config.ts:1-12](file://examguard-pro/src/config.ts#L1-L12)
- [Dashboard.tsx:30-35](file://examguard-pro/src/components/Dashboard.tsx#L30-L35)
- [SessionDetail.tsx:22-35](file://examguard-pro/src/components/SessionDetail.tsx#L22-L35)
- [main.py:275-474](file://server/main.py#L275-L474)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)
- [background.js:114-152](file://extension/background.js#L114-L152)

## Core Components
- useWebSocket custom hook and WebSocketManager
  - Provides a singleton WebSocket connection to the dashboard endpoint.
  - Manages message subscriptions, connection status, room subscriptions, and reconnection.
  - Exposes messages, connection status, and a sendMessage function.
- Configuration
  - Resolves wsUrl based on protocol and host, supporting dev and prod environments.
- Dashboard and SessionDetail components
  - Subscribe to the dashboard room for global alerts and events.
  - Subscribe to per-session rooms for targeted WebRTC and live frames.
- Server-side real-time manager
  - Manages connections for dashboards, proctors, and students.
  - Implements room-based broadcasting and event history.
  - Handles ping/pong, stats, and binary video streaming.

**Section sources**
- [useWebSocket.ts:1-175](file://examguard-pro/src/hooks/useWebSocket.ts#L1-L175)
- [config.ts:1-12](file://examguard-pro/src/config.ts#L1-L12)
- [Dashboard.tsx:30-35](file://examguard-pro/src/components/Dashboard.tsx#L30-L35)
- [SessionDetail.tsx:22-35](file://examguard-pro/src/components/SessionDetail.tsx#L22-L35)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)

## Architecture Overview
The real-time architecture uses a publish/subscribe pattern:
- Clients connect to FastAPI WebSocket endpoints.
- The server maintains connection pools and rooms.
- Events are broadcast to dashboards, proctors, and students.
- The frontend hook manages subscriptions and UI updates.

```mermaid
sequenceDiagram
participant Browser as "React Dashboard"
participant Hook as "useWebSocket.ts"
participant WS as "FastAPI /ws/dashboard"
participant RT as "RealtimeMonitoringManager"
Browser->>Hook : "useWebSocket('/dashboard', onMessage)"
Hook->>WS : "new WebSocket(wsUrl/dashboard)"
WS-->>Hook : "onopen -> send 'connection' + history"
WS-->>Hook : "onmessage -> JSON event"
Hook-->>Browser : "onMessage(event)"
Browser->>Hook : "sendMessage('subscribe : {roomId}')"
Hook->>WS : "send 'subscribe : {roomId}'"
WS->>RT : "join_room(session_id)"
RT-->>WS : "broadcast events to room"
WS-->>Hook : "forward events to subscribers"
Hook-->>Browser : "update messages + UI"
```

**Diagram sources**
- [useWebSocket.ts:21-74](file://examguard-pro/src/hooks/useWebSocket.ts#L21-L74)
- [main.py:275-343](file://server/main.py#L275-L343)
- [realtime.py:213-274](file://server/services/realtime.py#L213-L274)

## Detailed Component Analysis

### useWebSocket Hook and WebSocketManager
- Responsibilities
  - Singleton WebSocket connection with exponential backoff reconnection.
  - Message routing: filters heartbeat/connection messages; forwards parsed JSON to subscribers.
  - Room subscriptions: supports subscribing/unsubscribing to session rooms.
  - Connection status notifications to UI.
  - Send helper for low-level text messages.
- Lifecycle
  - connect(): creates WebSocket if not already connecting/open.
  - onopen: resets reconnect attempts, notifies status, re-subscribes to rooms.
  - onmessage: parses JSON, ignores heartbeat/connection/subscribed; forwards others.
  - onclose/onerror: updates status; schedules reconnect until max attempts.
  - disconnect(): cancels timers and closes connection cleanly.
- Room management
  - subscribeRoom()/unsubscribeRoom() maintain a set of subscribed rooms.
  - On reconnect, re-sends subscribe commands for all rooms.
- UI integration
  - useWebSocket returns messages array (recent N), isConnected flag, and sendMessage.

```mermaid
classDiagram
class WebSocketManager {
-ws : WebSocket
-url : string
-subscribers : Set
-statusSubscribers : Set
-reconnectAttempts : number
-reconnectTimer : Timeout
-connecting : boolean
-subscribedRooms : Set~string~
-MAX_RECONNECT_ATTEMPTS : number
+connect()
+subscribe(callback)
+subscribeStatus(callback)
+subscribeRoom(roomId)
+unsubscribeRoom(roomId)
+send(msg)
+disconnect()
-notifyStatus(connected)
}
class useWebSocket {
+messages : any[]
+isConnected : boolean
+sendMessage(msg)
}
WebSocketManager <.. useWebSocket : "singleton instance"
```

**Diagram sources**
- [useWebSocket.ts:5-126](file://examguard-pro/src/hooks/useWebSocket.ts#L5-L126)

**Section sources**
- [useWebSocket.ts:1-175](file://examguard-pro/src/hooks/useWebSocket.ts#L1-L175)

### Dashboard Component Real-Time Updates
- Subscribes to the dashboard room to receive global alerts and events.
- Aggregates live alerts with local initial data and limits the visible list.
- Uses connection status to reflect connectivity.

```mermaid
flowchart TD
Start(["Dashboard mount"]) --> Subscribe["Subscribe to /dashboard room"]
Subscribe --> Receive["Receive WebSocket events"]
Receive --> Parse["Parse JSON event"]
Parse --> Filter["Filter by event_type != heartbeat/connection/pong/subscribed"]
Filter --> Update["Update recent messages list"]
Update --> Render["Render alerts and stats"]
Render --> End(["Idle until next event"])
```

**Diagram sources**
- [Dashboard.tsx:30-113](file://examguard-pro/src/components/Dashboard.tsx#L30-L113)
- [useWebSocket.ts:43-54](file://examguard-pro/src/hooks/useWebSocket.ts#L43-L54)

**Section sources**
- [Dashboard.tsx:30-113](file://examguard-pro/src/components/Dashboard.tsx#L30-L113)
- [useWebSocket.ts:43-54](file://examguard-pro/src/hooks/useWebSocket.ts#L43-L54)

### SessionDetail Component: Room-Based Communication and WebRTC
- Subscribes to the session’s room to receive per-session events.
- Dynamically subscribes to each student’s room when they join.
- Handles WebRTC signaling via the hook’s sendMessage and a dedicated signal handler.
- Maintains live frames and MediaStreams for camera/screen feeds.

```mermaid
sequenceDiagram
participant UI as "SessionDetail.tsx"
participant Hook as "useWebSocket"
participant WS as "FastAPI /ws/dashboard"
participant RT as "RealtimeManager"
participant Ext as "Extension background.js"
UI->>Hook : "useWebSocket(sessionId, onMessage)"
Hook->>WS : "connect wsUrl/dashboard"
WS-->>Hook : "onopen -> subscribe to sessionId"
WS-->>Hook : "onmessage -> student_joined/left/live_frame/webrtc_signal"
Hook-->>UI : "onMessage(event)"
UI->>Hook : "sendMessage('subscribe : {studentId}')"
UI->>Hook : "sendMessage('command : request_webrtc_offer')"
Ext-->>WS : "webrtc signal"
WS-->>Hook : "forward webrtc_signal"
Hook-->>UI : "signal forwarded to handler"
```

**Diagram sources**
- [SessionDetail.tsx:47-117](file://examguard-pro/src/components/SessionDetail.tsx#L47-L117)
- [main.py:304-339](file://server/main.py#L304-L339)
- [background.js:133-141](file://extension/background.js#L133-L141)

**Section sources**
- [SessionDetail.tsx:47-117](file://examguard-pro/src/components/SessionDetail.tsx#L47-L117)
- [main.py:304-339](file://server/main.py#L304-L339)
- [background.js:133-141](file://extension/background.js#L133-L141)

### Server-Side Real-Time Manager
- Connection pools
  - Dashboard connections, proctor connections, and student connections.
- Room management
  - RoomManager organizes WebSocket connections by session_id.
- Broadcasting
  - broadcast_to_session(session_id, message) routes to room members.
  - broadcast_binary(session_id, bytes) relays live video chunks.
- Commands and signals
  - Handles subscribe commands, ping/pong, and WebRTC signaling.
- Heartbeat and stats
  - Periodic heartbeat with connection counts and event stats.

```mermaid
classDiagram
class RealtimeMonitoringManager {
+dashboard_connections : Set
+proctor_connections : Set
+student_connections : Dict
+room_manager : RoomManager
+event_history : List
+stats : Dict
+connect_dashboard(websocket)
+connect_proctor(websocket, session_id)
+connect_student(websocket, student_id, session_id)
+broadcast_event(...)
+broadcast_to_session(session_id, message)
+broadcast_binary(session_id, bytes)
+send_alert(...)
+send_to_student(student_id, message)
+start_heartbeat(interval)
+get_stats() Dict
}
class RoomManager {
+rooms : Dict~str, Set~WebSocket~~
+join_room(session_id, websocket)
+leave_room(session_id, websocket)
+get_room_members(session_id) Set
}
RealtimeMonitoringManager --> RoomManager : "uses"
```

**Diagram sources**
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)

**Section sources**
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)
- [main.py:275-474](file://server/main.py#L275-L474)

## Dependency Analysis
- Frontend
  - useWebSocket.ts depends on config.ts for wsUrl resolution.
  - Dashboard.tsx and SessionDetail.tsx depend on useWebSocket.ts.
- Backend
  - main.py registers WebSocket endpoints and delegates to RealtimeMonitoringManager.
  - RealtimeMonitoringManager orchestrates broadcasting and room management.

```mermaid
graph LR
Config["config.ts"] --> Hook["useWebSocket.ts"]
Hook --> Dash["Dashboard.tsx"]
Hook --> Sess["SessionDetail.tsx"]
Hook --> WS["server/main.py:/ws/*"]
WS --> RT["server/services/realtime.py"]
```

**Diagram sources**
- [config.ts:1-12](file://examguard-pro/src/config.ts#L1-L12)
- [useWebSocket.ts:1-175](file://examguard-pro/src/hooks/useWebSocket.ts#L1-L175)
- [Dashboard.tsx:30-35](file://examguard-pro/src/components/Dashboard.tsx#L30-L35)
- [SessionDetail.tsx:22-35](file://examguard-pro/src/components/SessionDetail.tsx#L22-L35)
- [main.py:275-474](file://server/main.py#L275-L474)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)

**Section sources**
- [config.ts:1-12](file://examguard-pro/src/config.ts#L1-L12)
- [useWebSocket.ts:1-175](file://examguard-pro/src/hooks/useWebSocket.ts#L1-L175)
- [Dashboard.tsx:30-35](file://examguard-pro/src/components/Dashboard.tsx#L30-L35)
- [SessionDetail.tsx:22-35](file://examguard-pro/src/components/SessionDetail.tsx#L22-L35)
- [main.py:275-474](file://server/main.py#L275-L474)
- [realtime.py:102-643](file://server/services/realtime.py#L102-L643)

## Performance Considerations
- Connection reuse
  - The singleton WebSocketManager avoids redundant connections and consolidates subscriptions.
- Backpressure and buffering
  - The server broadcasts binary video chunks to dashboards and proctors; ensure clients can process frames efficiently.
- Message filtering
  - Ignoring heartbeat/connection messages reduces UI churn.
- Room granularity
  - Per-session rooms minimize unnecessary fan-out and improve scalability.
- History and stats
  - Recent event history helps late-joining clients catch up without reprocessing full streams.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
- Connection does not establish
  - Verify wsUrl resolution in config.ts for the current protocol/host.
  - Check backend WebSocket endpoints are reachable and accepting connections.
- Frequent reconnections
  - Inspect onclose conditions and reconnect attempts; ensure network stability.
  - Confirm the server does not abruptly close connections.
- Messages not received
  - Ensure the client sent subscribe commands for rooms.
  - Verify message parsing ignores heartbeat/connection/subscribed types.
- WebRTC signaling failures
  - Confirm the extension sends webrtc signals and the server routes them to the correct student.
  - Validate that the client’s signal handler is wired to the hook’s onMessage callback.
- Debugging techniques
  - Enable console logs for connection, room subscription, and message parsing in the hook.
  - Use browser DevTools Network tab to inspect WebSocket frames and timing.
  - Monitor server logs for connection, room joins, and broadcasting actions.
  - Use server stats endpoints or logs to track connection counts and event rates.

**Section sources**
- [useWebSocket.ts:31-74](file://examguard-pro/src/hooks/useWebSocket.ts#L31-L74)
- [main.py:282-342](file://server/main.py#L282-L342)
- [background.js:133-141](file://extension/background.js#L133-L141)

## Conclusion
The ExamGuard Pro real-time integration leverages a robust WebSocket architecture with a centralized manager on the frontend and a scalable room-based broadcasting system on the backend. The useWebSocket hook encapsulates connection lifecycle, reconnection, and room subscriptions, enabling event-driven UI updates across the dashboard and session views. Room-based communication and careful message filtering ensure efficient, client-consistent real-time experiences, while server-side stats and heartbeats provide operational visibility.