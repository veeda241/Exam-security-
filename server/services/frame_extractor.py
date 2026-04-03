import os
import subprocess
import threading
import time
import cv2
import numpy as np
import tempfile
from typing import Dict, Optional, Callable

class StreamFrameExtractor:
    """
    Experimental service to extract frames from a live WebM stream (binary chunks)
    using FFmpeg on the server side.
    """
    def __init__(self, fps: float = 0.2):
        self.fps = fps # Extraction rate (e.g., 1 frame every 5 seconds)
        self.sessions: Dict[str, str] = {} # session_id -> temp_file_path
        self.last_extraction: Dict[str, float] = {} # session_id -> timestamp
        self._lock = threading.Lock()
        
    def _get_temp_file(self, session_id: str) -> str:
        if session_id not in self.sessions:
            # Create a persistent temp file for this session's stream
            fd, path = tempfile.mkstemp(suffix='.webm', prefix=f'stream_{session_id}_')
            os.close(fd)
            self.sessions[session_id] = path
            self.last_extraction[session_id] = 0
            print(f"[FFmpeg] Created stream buffer for session {session_id}: {path}")
        return self.sessions[session_id]

    def add_chunk(self, session_id: str, chunk: bytes, callback: Optional[Callable] = None):
        """Append a video chunk to the session buffer and check if it's time to extract a frame."""
        path = self._get_temp_file(session_id)
        
        with open(path, 'ab') as f:
            f.write(chunk)
            
        now = time.time()
        # Extract a frame if enough time has passed (e.g., every 5s)
        if now - self.last_extraction.get(session_id, 0) >= (1.0 / self.fps):
            self.last_extraction[session_id] = now
            # Run extraction in a background thread to avoid blocking WebSocket
            threading.Thread(target=self._extract_latest_frame, args=(session_id, path, callback), daemon=True).start()

    def _extract_latest_frame(self, session_id: str, file_path: str, callback: Optional[Callable]):
        """Runs FFmpeg to pull the most recent frame from the accumulating WebM file."""
        if not callback:
            return

        try:
            ffmpeg_exe = os.getenv("FFMPEG_PATH", "ffmpeg")
            # Command to extract the VERY LAST frame from the file
            output_img = f"{file_path}.jpg"
            
            cmd = [
                ffmpeg_exe, '-y', 
                '-i', file_path, 
                '-frames:v', '1', 
                '-f', 'image2', 
                '-update', '1', 
                output_img
            ]
            
            # Run FFmpeg (silently)
            # Note: This requires ffmpeg to be installed on the system
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(output_img):
                # Load frame with OpenCV
                frame = cv2.imread(output_img)
                if frame is not None:
                    # Clean up the snapshot image (but keep the webm buffer)
                    try: os.remove(output_img)
                    except: pass
                    
                    # Pass frame to AI callback
                    callback(session_id, frame)
                else:
                    print(f"[FFmpeg] Failed to read extracted frame for {session_id}")
            else:
                # If first frames are missing or file is corrupt
                pass
                
        except Exception as e:
            # If FFmpeg is missing, this will fail
            if "ffmpeg" in str(e).lower():
                print("[FFmpeg] ERROR: ffmpeg executable not found. Server-side extraction disabled.")
            else:
                print(f"[FFmpeg] Extraction error for {session_id}: {e}")

    def cleanup(self, session_id: str):
        """Removes the temp file once the session ends."""
        with self._lock:
            if session_id in self.sessions:
                path = self.sessions[session_id]
                try:
                    if os.path.exists(path):
                        os.remove(path)
                    if os.path.exists(f"{path}.jpg"):
                        os.remove(f"{path}.jpg")
                    print(f"[FFmpeg] Cleaned up stream buffer for {session_id}")
                except Exception as e:
                    print(f"[FFmpeg] Cleanup error: {e}")
                del self.sessions[session_id]
                del self.last_extraction[session_id]

# Singleton instance
_extractor = None

def get_frame_extractor():
    global _extractor
    if _extractor is None:
        _extractor = StreamFrameExtractor(fps=0.1) # 1 frame every 10 seconds
    return _extractor
