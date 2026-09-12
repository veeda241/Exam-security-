# Model weights

Place downloaded inference artifacts in this directory during local or image
build setup. Large binaries are intentionally ignored by Git.

- `yolov8n.pt` — optional Ultralytics object detector weights.
- Additional model bundles may be added here as the worker configuration grows.

The MediaPipe face landmarker bundle currently remains at
`server/services/face_landmarker.task` for backward compatibility.
