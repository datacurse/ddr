"""
ArUco detection pipeline using red hue-based detection.
Detects a single ArUco marker with RED background and BLACK code modules.
"""

import cv2
import numpy as np
from numpy.typing import NDArray
from typing import Tuple, NamedTuple, Optional
from cv2.typing import MatLike


class Point(NamedTuple):
    x: float
    y: float


class ArucoMarker(NamedTuple):
    id: int
    corners: list[Tuple[int, int]]
    center: Point
    angle_deg: float


class MarkerCache:
    """Pre-computed ArUco bit patterns. Build once, reuse every frame."""

    def __init__(self, dict_name: int = cv2.aruco.DICT_5X5_100):
        aruco_dict = cv2.aruco.getPredefinedDictionary(dict_name)
        self.entries: list[Tuple[NDArray[np.uint8], int]] = []
        for marker_id in range(len(aruco_dict.bytesList)):
            bits = np.zeros((5, 5), dtype=np.uint8)
            bit_idx = 0
            for byte in aruco_dict.bytesList[marker_id].flatten():
                for b in range(8):
                    if bit_idx >= 25:
                        break
                    bits[bit_idx // 5, bit_idx % 5] = (byte >> (7 - b)) & 1
                    bit_idx += 1
            self.entries.append((bits, marker_id))


# Module-level default cache, built on first use
_default_cache: Optional[MarkerCache] = None


def get_default_cache(dict_name: int = cv2.aruco.DICT_5X5_100) -> MarkerCache:
    global _default_cache
    if _default_cache is None:
        _default_cache = MarkerCache(dict_name)
    return _default_cache


def _order_quad(pts: NDArray[np.float32]) -> NDArray[np.float32]:
    """Order 4 points as: TL, TR, BR, BL."""
    quad = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    quad[0], quad[2] = pts[np.argmin(s)], pts[np.argmax(s)]
    d = np.diff(pts, axis=1).flatten()
    quad[1], quad[3] = pts[np.argmin(d)], pts[np.argmax(d)]
    return quad


def _match_marker(
    data_5: NDArray[np.uint8],
    cache: MarkerCache,
    max_hamming: int,
) -> Tuple[Optional[int], Optional[int]]:
    """
    Match 5x5 bit pattern against cache across 4 rotations. Single pass.
    Returns (marker_id, rotation_index) or (None, None) if no unambiguous match.

    Requires a confidence margin of >=2 between the best and second-best
    hamming distance (across all IDs and rotations) to avoid ambiguous
    rotation assignments from garbled/blurry frames.
    """
    best_id: Optional[int] = None
    best_rot: Optional[int] = None
    best_dist = max_hamming + 1
    second_dist = max_hamming + 2

    for rot in range(4):
        rotated = np.rot90(data_5, rot)
        for ref_bits, marker_id in cache.entries:
            dist = int(np.sum(rotated != ref_bits))
            if dist < best_dist:
                second_dist = best_dist
                best_dist, best_id, best_rot = dist, marker_id, rot
            elif dist < second_dist:
                second_dist = dist

    if best_dist > max_hamming:
        return None, None
    if second_dist - best_dist < 2:
        return None, None
    return best_id, best_rot


def detect_aruco(
    image: MatLike,
    cache: Optional[MarkerCache] = None,
    min_area: int = 200,
    max_hamming: int = 2,
) -> Optional[ArucoMarker]:
    """
    Detect a single ArUco marker with RED background and BLACK code modules.

    Args:
        image: BGR image from camera.
        cache: Pre-built MarkerCache. Uses default 5x5_100 if None.
        min_area: Minimum contour area to consider.
        max_hamming: Max bit errors allowed (2 = tolerant of reflections).

    Returns:
        ArucoMarker dict (id, corners, center, angle_deg) or None if not found.
    """
    if cache is None:
        cache = get_default_cache()

    TOTAL_BITS = 7
    CELL_PX = 20
    SIZE = TOTAL_BITS * CELL_PX

    # --- Red mask ---
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red_mask = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 80, 50]), np.array([10, 255, 255])),
        cv2.inRange(hsv, np.array([170, 80, 50]), np.array([180, 255, 255])),
    )

    # Include white/reflective pixels that fall inside red bounding rects
    mask_white = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 60, 255]))
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    red_regions = np.zeros_like(red_mask)
    for cnt in contours:
        cv2.fillPoly(red_regions, [cv2.boxPoints(cv2.minAreaRect(cnt)).astype(np.int32)], 255)
    red_mask = cv2.bitwise_or(red_mask, cv2.bitwise_and(mask_white, red_regions))

    # --- Largest quad ---
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < min_area:
        return None

    quad = _order_quad(cv2.boxPoints(cv2.minAreaRect(largest)).astype(np.float32))

    # --- Warp, invert, extract bits ---
    dst = np.array([[0, 0], [SIZE - 1, 0], [SIZE - 1, SIZE - 1], [0, SIZE - 1]], dtype=np.float32)
    warped = cv2.warpPerspective(red_mask, cv2.getPerspectiveTransform(quad, dst), (SIZE, SIZE), flags=cv2.INTER_NEAREST)
    code_mask = cv2.bitwise_not(warped)

    cell_h, cell_w = SIZE / TOTAL_BITS, SIZE / TOTAL_BITS
    bits_7 = np.zeros((TOTAL_BITS, TOTAL_BITS), dtype=np.uint8)
    for r in range(TOTAL_BITS):
        for c in range(TOTAL_BITS):
            cell = code_mask[int(r * cell_h):int((r + 1) * cell_h), int(c * cell_w):int((c + 1) * cell_w)]
            bits_7[r, c] = 1 if np.sum(cell > 127) > cell.size * 0.5 else 0
    data_5 = bits_7[1:-1, 1:-1]

    # --- Match ---
    marker_id, rot = _match_marker(data_5, cache, max_hamming)
    if marker_id is None:
        return None

    # --- Angle from quad geometry ---
    top_mid = (quad[0] + quad[1]) / 2.0
    center = quad.mean(axis=0)
    vec_up = top_mid - center
    quad_angle = np.degrees(np.atan2(vec_up[0], -vec_up[1]))
    angle_deg = float((quad_angle + rot * 90) % 360)

    return ArucoMarker(
        id=marker_id,
        corners=[(int(x), int(y)) for x, y in quad],
        center=Point(float(center[0]), float(center[1])),
        angle_deg=angle_deg,
    )