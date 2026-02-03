# Exam Security - Project Structure Guide

This guide helps you identify and edit files in the **Academic Hub** proctoring system.

## 🎨 Frontend (React Dashboard)
Located in `/react-dashboard/`

### 📄 Pages (Role-Based)
Each page in the dashboard has its own dedicated file for easy editing.
- `src/pages/LandingPage.jsx`: The entry point for role selection (Professor vs Student).
- `src/pages/teacher/` - **Professor Console**
  - `Dashboard.jsx`: Main overview with stats and recent activity.
  - `CoursesPage.jsx`: Management of departments and subjects.
  - `SessionsPage.jsx`: Full database of all student exam sessions.
  - `FlaggedPage.jsx`: High-priority queue for suspicious activity.
  - `AnalyticsPage.jsx`: Institutional integrity trends and charts.
  - `SettingsPage.jsx`: AI configuration (gaze sensitivity, YOLOv8 toggles).
- `src/pages/student/` - **Student Portal**
  - `StudentDashboard.jsx`: Student landing page and secure exam environment.

### 🧱 Components (Reusable UI)
Located in `src/components/`
- `Layout.jsx`: The main wrapper (Sidebar + Content area).
- `Sidebar.jsx`: Navigation menu with role-based links.
- `LockdownGuard.jsx`: The security wrapper that enforces Fullscreen and blocks cheating.
- `NotificationFeed.jsx`: The real-time WebSocket alert system.
- `ViolationLogs.jsx`: Persistent database view for tracking flags.

### 🧠 Logic & State
- `src/context/`: Global state (User roles, Session data).
- `src/services/api.js`: The central hub for all communication with the Python backend.

---

## 🤖 Backend (AI Engine)
Located in `/server/`

- `main.py`: FastAPI entry point and WebSocket manager.
- `api/`: Endpoint definitions (uploads, sessions, events).
- `analysis/`: The "Brain" of the project.
  - `secure_vision.py`: Integrated YOLOv8 (phones) and MediaPipe (gaze).
  - `screen_ocr.py`: OCR text analysis.
- `database.py`: Core database connection and model management.

---

## 🛠️ Browser extension
Located in `/extension/`
- `content.js`: Injects security scripts into the student's browser tab.
- `background.js`: Manages the session state and background communication.
