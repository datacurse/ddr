"""
Line detection from ArUco markers: when a marker is visible, derive the
line from its position and angle (much more stable than blue-pixel
detection near the marker).

align_aruco_angle() adjusts the raw ArUco angle so it's relative to the
robot's current travel direction (north/east/south/west).
"""

import math
import numpy as np
from cv2.typing import MatLike

from .aruco_detector import ArucoMarker
from .line_detector import LineDetection, detect_blue_line

_FACING_OFFSET = {"north": 0.0, "east": 90.0, "south": 180.0, "west": 270.0}


def align_aruco_angle(aruco_angle_deg: float, facing: str) -> float:
    """
    Adjust raw ArUco angle_deg so it's relative to the robot's travel direction.

    ArUco angle is 0-360 (0=up/north in image, CW+).
    Subtracts the facing rotation then folds to -90..90 (lines have no
    polarity, so 0° and 180° are the same).

    facing: "north", "east", "south", "west"
    """
    angle = (aruco_angle_deg - _FACING_OFFSET[facing]) % 180.0
    if angle > 90.0:
        angle -= 180.0
    return angle


def line_from_aruco(
    aruco: ArucoMarker,
    frame_shape: tuple[int, ...],
    facing: str = "north",
) -> LineDetection:
    """
    Derive a LineDetection from an ArUco marker.

    The marker sits on the line, so its center = line position
    and its angle = line angle (adjusted for the robot's facing direction).
    """
    h, w = frame_shape[:2]
    cx_img = w / 2.0
    cy_img = h / 2.0

    cx = aruco.center.x
    cy = aruco.center.y

    angle = align_aruco_angle(aruco.angle_deg, facing)

    # Perpendicular offset from image center to the line through marker center.
    # Line runs at `angle` degrees from vertical, so its normal points at
    # (angle + 90) degrees. Project the center-to-marker vector onto that normal.
    angle_rad = math.radians(angle)
    normal_x = math.cos(angle_rad)   # normal to a near-vertical line is near-horizontal
    normal_y = math.sin(angle_rad)

    offset_x = (cx - cx_img) * normal_x + (cy - cy_img) * normal_y
    offset_y = -(cx - cx_img) * normal_y + (cy - cy_img) * normal_x

    return LineDetection(angle=angle, offset_x=offset_x, offset_y=offset_y)


def fuse_line(
    frame_bgr: MatLike | None,
    aruco_result: ArucoMarker | None = None,
    heading_offset: float = 0.0,
    facing: str | None = None,
) -> LineDetection | None:
    """
    Convenience wrapper: prefer ArUco-derived line, fall back to blue line.

    Pass facing="east" etc. for direction-aware alignment, or heading_offset
    for backward compatibility with patrol/smart scripts.
    """
    if facing is None:
        facing = ["north", "east", "south", "west"][int(heading_offset / 90) % 4]

    if aruco_result is not None and frame_bgr is not None:
        return line_from_aruco(aruco_result, frame_bgr.shape, facing=facing)

    return detect_blue_line(frame_bgr)