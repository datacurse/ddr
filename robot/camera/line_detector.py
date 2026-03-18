import cv2 as cv
import numpy as np
from cv2.typing import MatLike
from typing import NamedTuple


class LineDetection(NamedTuple):
    angle: float      # Angle from vertical in degrees (positive = clockwise)
    offset_x: float   # Horizontal offset from image center to line
    offset_y: float   # Vertical offset from image center to line


def detect_blue_line(frame_bgr: MatLike | None) -> LineDetection | None:
    """
    Detect a blue tape line in a BGR frame using HSV masking + minAreaRect.

    Returns:
        LineDetection with angle and offset, or None if no line detected
    """
    if frame_bgr is None:
        return None

    h, w = frame_bgr.shape[:2]
    img_center = np.array([w / 2.0, h / 2.0])

    # --- Hardcoded BLUE HSV range (OpenCV: H 0..180) ---
    lower = np.array([100,  80,  50], dtype=np.uint8)
    upper = np.array([130, 255, 255], dtype=np.uint8)

    hsv = cv.cvtColor(frame_bgr, cv.COLOR_BGR2HSV)
    mask = cv.inRange(hsv, lower, upper)

    contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    MIN_AREA = 500
    contours = [c for c in contours if cv.contourArea(c) >= MIN_AREA]
    if not contours:
        return None

    rect_data: list[tuple[float, float, float, float]] = []
    for cnt in contours:
        rect = cv.minAreaRect(cnt)
        (cx, cy), (rw, rh), rect_angle = rect
        area = float(cv.contourArea(cnt))

        if rw >= rh:
            theta = np.radians(rect_angle)
        else:
            theta = np.radians(rect_angle + 90.0)

        rect_data.append((float(cx), float(cy), float(theta), area))

    VERTICAL_THRESH_DEG = 45.0
    vertical: list[tuple[float, float, float, float]] = []
    for cx, cy, theta, area in rect_data:
        angle_from_vertical = abs(abs(np.degrees(theta)) - 90)
        if angle_from_vertical < VERTICAL_THRESH_DEG:
            vertical.append((cx, cy, theta, area))

    if not vertical:
        return None

    total_area = sum(a for _, _, _, a in vertical)
    avg_cx = sum(cx * a for cx, _, _, a in vertical) / total_area
    avg_cy = sum(cy * a for _, cy, _, a in vertical) / total_area

    avg_cos = sum(np.cos(theta) * a for _, _, theta, a in vertical) / total_area
    avg_sin = sum(np.sin(theta) * a for _, _, theta, a in vertical) / total_area
    avg_theta = np.arctan2(avg_sin, avg_cos)

    line_dir = np.array([np.cos(avg_theta), np.sin(avg_theta)])
    line_point = np.array([avg_cx, avg_cy])

    angle_deg = float(np.degrees(np.arctan2(line_dir[0], -line_dir[1])))
    if angle_deg > 90:
        angle_deg -= 180
    elif angle_deg < -90:
        angle_deg += 180

    v = img_center - line_point
    proj = float(np.dot(v, line_dir))
    foot = line_point + proj * line_dir
    offset_x = float(foot[0] - img_center[0])
    offset_y = float(foot[1] - img_center[1])

    return LineDetection(angle=angle_deg, offset_x=offset_x, offset_y=offset_y)