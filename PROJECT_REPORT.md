# Project Report: Academic Hub - Secure AI Proctoring System

## Title of the Project
**Academic Hub: Secure AI-Powered Proctoring & Examination System**

## Objective / Problem Statement
Academic Hub solves the critical problem of **remote examination integrity**. In an era of online learning, preventing cheating—specifically the use of mobile devices, unauthorized browsers-switching, and external assistance—is a major challenge for educators. 

This project is important because it provides a **low-cost, high-reliability automated proctoring solution** that ensures a level playing field for students and maintains the academic standards of institutions.

## Scope & Features
- **Lockdown Examination Environment**: Enforced fullscreen mode, disabled right-click, copy-paste, and tab-switch detection.
- **AI Proctoring Engine**: 
    - **Object Detection (YOLOv8)**: Real-time identification of cell phones and unauthorized laptops.
    - **Social Guard**: Detects multiple persons in the frame.
    - **Gaze Tracking (MediaPipe)**: Tracks student iris/eye movement to flag off-screen glances for >3 seconds.
- **Real-time Violation Broadcasting**: Instant alerts sent to the professor via WebSockets.
- **Institutional Dashboard**: 
    - **Professor Console**: Live monitoring, persistent violation logs, and integrity scores.
    - **Student Portal**: Secure landing and exam access.
- **Automated Integrity Scoring**: 0-100% score calculated based on behavioral anomalies.

## Technology Stack
- **Frontend**: React 18, Vite, React Router, Context API, CSS3 Modules.
- **Backend**: Python 3.x, FastAPI (High-performance API), WebSockets.
- **AI/ML**: 
    - **YOLOv8** (Computer Vision)
    - **MediaPipe** (Face Mesh & Iris Tracking)
    - **OpenCV** (Image Processing)
- **Database**: SQLite with SQLAlchemy (Async ORM).
- **Tooling**: Git, NPM, Pip.

## Architecture / Workflow
1.  **Student UI**: Inits `LockdownGuard`, requests Fullscreen, and starts capturing webcam frames.
2.  **API Communication**: Frames and browser events (tab-switch) are sent to the **FastAPI Backend**.
3.  **AI Processing**: The vision engine analyzes frames for phones or gaze violations.
4.  **Database & Dispatch**: Violations are logged in the **SQLite Database** and simultaneously broadcasted.
5.  **Professor Dashboard**: Receives WebSocket alerts and displays "Red Alert" toasts and persistent evidence logs.

## Challenges & Solutions
- **Browser Security Restrictions**: Interaction blockers like right-click and copy-paste are difficult to enforce. **Solution**: Use global event listeners and React guards that wrap the entire application state.
- **Real-Time Latency**: Analyzing high-res frames can slow down the system. **Solution**: Implemented background tasks in FastAPI and optimized YOLOv8 to run on small nano-weights.
- **Environment Parity**: Managing separate user experiences. **Solution**: Reorganized the project into role-based directories and implemented a robust `UserContext`.

## Impact & Use Cases
- **Higher Education**: Universities conducting remote midterms/finals.
- **Certification Bodies**: Online professional certification providers ensuring candidate identity.
- **Corporate Training**: Internal skill assessments for large organizations.

## Future Improvements
- **Audio Proctoring**: Using AI to detect forbidden background voices or keywords during exams.
- **Identity Verification**: Multi-factor biometric face-matching before exam entry.
- **Scalability**: Moving from SQLite to a distributed PostgreSQL system for handles thousands of concurrent sessions.

## Tone & Style
Formal Technical Report (Academic/Institutional).
