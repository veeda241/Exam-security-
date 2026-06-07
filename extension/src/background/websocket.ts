let ws: WebSocket | null = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

export function initWebSocket() {
  const backendUrl = "ws://localhost:8000/api/v1/events/ws";
  
  ws = new WebSocket(backendUrl);

  ws.onopen = () => {
    console.log("WebSocket connected to backend");
    reconnectAttempts = 0;
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Received message from backend:", data);
  };

  ws.onclose = () => {
    console.log("WebSocket disconnected");
    handleReconnect();
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
    ws?.close();
  };
}

function handleReconnect() {
  if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
    reconnectAttempts++;
    console.log(`Reconnecting attempt ${reconnectAttempts}...`);
    setTimeout(initWebSocket, Math.pow(2, reconnectAttempts) * 1000);
  } else {
    console.error("Max reconnect attempts reached");
  }
}

export function sendEvent(event: any) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(event));
  } else {
    // Buffer event or handle offline
    console.warn("WebSocket not connected, event not sent");
  }
}
