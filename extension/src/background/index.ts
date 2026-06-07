import { initWebSocket } from "./websocket";
import { setupStorage } from "../utils/storage";

console.log("ExamGuard Pro background script initialized");

chrome.runtime.onInstalled.addListener(() => {
  setupStorage();
  console.log("ExamGuard Pro extension installed");
});

// Initialize WebSocket connection
initWebSocket();

// Message listener for content scripts and popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "START_EXAM") {
    // Handle exam start
    console.log("Exam started", message.data);
    sendResponse({ status: "success" });
  }
  return true;
});
