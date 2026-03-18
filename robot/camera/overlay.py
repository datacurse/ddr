"""ArUco marker overlay drawing."""

import cv2
import numpy as np
from .aruco_detector import ArucoMarker


def draw_marker_overlay(frame, marker: ArucoMarker) -> None:
    """Draw red quad, corner dots, ID and angle on the frame."""
    corners = marker.corners
    pts = np.array(corners, dtype=np.int32).reshape((-1, 1, 2))

    cv2.polylines(frame, [pts], isClosed=True, color=(0, 0, 255), thickness=2)

    for x, y in corners:
        cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

    cx = int(np.mean([p[0] for p in corners]))
    cy = int(np.mean([p[1] for p in corners]))

    for i, text in enumerate((f"ID: {marker.id}", f"Angle: {marker.angle_deg:.1f} deg")):
        cv2.putText(
            frame, text, (cx + 15, cy - 20 + i * 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA,
        )