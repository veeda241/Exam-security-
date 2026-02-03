# ExamGuard Pro - Improvements Roadmap

Based on the current project structure, here are recommended improvements categorized by impact and complexity.

## 1. 🔐 Security & Authentication (High Priority)
Currently, the system allows open access. Verification is crucial for exam integrity.

- **Admin Authentication**:
  - Implement **JWT (JSON Web Token)** login for the Dashboard.
  - Create an `Admins` table in the database.
  - Secure API routes with `Depends(get_current_admin)`.
- **Student Verification**:
  - **ID Card Matching**: Use the webcam to capture a Student ID card before the exam and match the name using OCR/Face recognition.
  - **Magic Links**: Send unique, one-time exam links to students via email to prevent unauthorized access.
- **Secure Exam Browser Mode**:
  - Enforce **fullscreen** mode in the extension; trigger an alert if the user exits fullscreen.

## 2. 🧠 Advanced AI Capabilities
Enhance the depth of proctoring analysis.

- **Audio Proctoring** (New Module):
  - Capture audio via the extension.
  - Detect **speech** (someone talking to the student) or **background noise**.
  - Use libraries like `pyacoustid` or `SpeechRecognition`.
- **Object Detection (YOLO Integration)**:
  - Integrate **YOLOv8** to detect specific forbidden objects: **Mobile Phones**, **Books**, **Headphones**.
  - Current face detection only checks for presence; YOLO adds context.
- **Head Pose & Gaze Tracking**:
  - Refine `face_detection.py` to calculate precise **yaw/pitch/roll** angles.
  - Determine if the student is looking at the screen, notes (down), or a second monitor (side).

## 3. 📊 Frontend & Visualization
Make the dashboard more actionable and real-time.

- **Live WebSocket Updates**:
  - Replace the 10-second polling mechanism with **WebSockets** for instant alert updates on the dashboard.
- **Interactive Charts**:
  - Integrate **Chart.js** or **Recharts**.
  - Show "Engagement over Time" line charts for each student.
- **Session Playback**:
  - Store "snapshots" (images/logs) with timestamps.
  - Create a "Timeline View" allowing admins to scrub through the exam session events.

## 4. ⚙️ Infrastructure & Performance
Prepare for scale.

- **Database Migrations (Alembic)**:
  - Set up **Alembic** to handle database schema changes without losing data.
- **Redis Caching**:
  - Cache dashboard statistics (`/api/analysis/dashboard`) in Redis to reduce DB load for large classes.
- **Object Storage (S3)**:
  - Move image storage from the local file system (`uploads/`) to **AWS S3** or **MinIO** for persistence and scalability.

## Recommended "Next Step" Feature
I recommend starting with **Audio Proctoring** or **Object Detection (YOLO)** as they add significant value to the "AI Proctoring" core promise.
