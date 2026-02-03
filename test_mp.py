import mediapipe as mp
print(f"MediaPipe Version: {mp.__version__}")
try:
    from mediapipe.python.solutions import face_mesh
    print("FaceMesh imported from mediapipe.python.solutions")
except ImportError as e:
    print(f"ImportError (python.solutions): {e}")

try:
    import mediapipe.solutions.face_mesh as face_mesh_legacy
    print("FaceMesh imported from mediapipe.solutions")
except ImportError as e:
    print(f"ImportError (solutions): {e}")
