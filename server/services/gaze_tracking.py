"""Head-pose and coarse gaze estimation helpers.

The helpers intentionally operate on MediaPipe's normalized face landmarks so
the worker can use them without coupling the API layer to a model runtime.
"""
from __future__ import annotations

from math import atan2, degrees, hypot, asin
from typing import Any

import cv2
import numpy as np


POSE_LANDMARKS = (1, 199, 33, 263, 61, 291)
POSE_MODEL_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),
        (0.0, -63.6, -12.5),
        (-43.3, 32.7, -26.0),
        (43.3, 32.7, -26.0),
        (-28.9, -28.9, -24.1),
        (28.9, -28.9, -24.1),
    ],
    dtype=np.float64,
)


def _point(landmark: Any, width: int, height: int) -> tuple[float, float]:
    return float(landmark.x * width), float(landmark.y * height)


def estimate_head_pose(
    landmarks: list[Any], width: int, height: int
) -> dict[str, float] | None:
    """Estimate pitch, yaw, and roll in degrees from six face landmarks."""
    if len(landmarks) <= max(POSE_LANDMARKS):
        return None

    image_points = np.array(
        [_point(landmarks[index], width, height) for index in POSE_LANDMARKS],
        dtype=np.float64,
    )
    focal_length = float(width)
    camera_matrix = np.array(
        [
            [focal_length, 0, width / 2],
            [0, focal_length, height / 2],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )
    success, rotation_vector, _ = cv2.solvePnP(
        POSE_MODEL_POINTS,
        image_points,
        camera_matrix,
        np.zeros((4, 1), dtype=np.float64),
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not success:
        return None

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    yaw = degrees(asin(float(np.clip(rotation_matrix[0, 2], -1.0, 1.0))))
    pitch = degrees(atan2(-rotation_matrix[1, 2], rotation_matrix[2, 2]))
    roll = degrees(atan2(-rotation_matrix[0, 1], rotation_matrix[0, 0]))
    return {"pitch": pitch, "yaw": yaw, "roll": roll}


def estimate_gaze(landmarks: list[Any]) -> dict[str, Any]:
    """Return a normalized horizontal iris ratio and a coarse direction."""
    required = (33, 133, 263, 362, 468, 473)
    if len(landmarks) <= max(required):
        return {"ratio": None, "direction": "unknown", "off_screen": False}

    left_inner = landmarks[133]
    left_outer = landmarks[33]
    right_inner = landmarks[362]
    right_outer = landmarks[263]
    left_iris = landmarks[473]
    right_iris = landmarks[468]

    def ratio(iris: Any, inner: Any, outer: Any) -> float:
        span = hypot(outer.x - inner.x, outer.y - inner.y)
        return hypot(iris.x - inner.x, iris.y - inner.y) / span if span else 0.5

    ratios = [ratio(left_iris, left_inner, left_outer), ratio(right_iris, right_inner, right_outer)]
    average = sum(ratios) / len(ratios)
    if average < 0.35:
        direction = "left"
    elif average > 0.65:
        direction = "right"
    else:
        direction = "center"
    return {
        "ratio": round(average, 4),
        "direction": direction,
        "off_screen": direction != "center",
    }
