import os
import sys
import time
from enum import Enum
from typing import Optional

import cv2 as cv
from cv2.typing import MatLike


# ══════════════════════════════════════════════════════════════
# RESOLUTION & FPS
# ══════════════════════════════════════════════════════════════

class Resolution(Enum):
    RES_320x240   = (320, 240)
    RES_640x480   = (640, 480)
    RES_800x600   = (800, 600)
    RES_960x720   = (960, 720)
    RES_1024x768  = (1024, 768)
    RES_1280x720  = (1280, 720)
    RES_1280x960  = (1280, 960)
    RES_1600x1200 = (1600, 1200)
    RES_1920x1080 = (1920, 1080)
    RES_1920x1200 = (1920, 1200)

    @property
    def width(self) -> int:
        return self.value[0]

    @property
    def height(self) -> int:
        return self.value[1]


SUPPORTED_FPS = [5, 10, 15, 20, 25, 30, 60, 90]


# ══════════════════════════════════════════════════════════════
# CAMERA PRESETS
# ══════════════════════════════════════════════════════════════

CAMERA_PRESETS = {
    "default": {
        "brightness": 0,
        "contrast": 0,
        "saturation": 100,
        "hue": 0,
        "gamma": 110,
        "sharpness": 0,
        "backlight_compensation": 54,
        "gain": 25,
        "auto_exposure": 1,
        "exposure": 2,
        "auto_white_balance": 0,
        "white_balance_temperature": 4600,
        "power_line_frequency": 1,
        "auto_focus": 0,
        "focus_absolute": 0,
    },
    "original": {
        "brightness": 0,
        "contrast": 0,
        "saturation": 56,
        "hue": 0,
        "gamma": 110,
        "sharpness": 0,
        "backlight_compensation": 54,
        "gain": 0,
        "auto_exposure": 1,
        "exposure": 2,
        "auto_white_balance": 0,
        "white_balance_temperature": 4600,
        "power_line_frequency": 1,
        "auto_focus": 0,
        "focus_absolute": 0,
    },
    "offwhite": {
        "brightness": 0,
        "contrast": 50,
        "saturation": 0,
        "hue": 0,
        "gamma": 0,
        "sharpness": 7,
        "backlight_compensation": 54,
        "gain": 50,
        "auto_exposure": 1,
        "exposure": 2,
        "auto_white_balance": 0,
        "white_balance_temperature": 4600,
        "power_line_frequency": 1,
        "auto_focus": 0,
        "focus_absolute": 0,
    },
}


# ══════════════════════════════════════════════════════════════
# CAMERA
# ══════════════════════════════════════════════════════════════

class Camera:
    """
    MJPG-only camera wrapper.

    1. open() creates the capture, applies settings and warms up.
    2. read() returns the next frame (rotated + cropped).
    3. snapshot() saves one frame as a JPEG.
    4. release() closes the capture.
    """

    def __init__(
        self,
        device: str = "/dev/video0",
        resolution: Resolution = Resolution.RES_640x480,
        fps: int = 90,
        buffersize: int = 4,
        preset: str = "default",
    ) -> None:
        self.cap: Optional[cv.VideoCapture] = None

        self.device = device
        self.resolution = resolution
        self.fps = fps
        self.buffersize = buffersize
        self.preset = preset

        if preset not in CAMERA_PRESETS:
            raise ValueError(
                f"Unknown preset '{preset}'. Available: {list(CAMERA_PRESETS.keys())}"
            )

        if fps not in SUPPORTED_FPS:
            raise ValueError(
                f"FPS {fps} not supported. Options: {SUPPORTED_FPS}"
            )

    # --- Internals ------------------------------------------------

    def _cap(self) -> cv.VideoCapture:
        if self.cap is None:
            raise RuntimeError("Camera not opened. Call open() first.")
        return self.cap

    # --- Public API -----------------------------------------------

    def open(self) -> None:
        if self.cap is not None:
            return

        self._create_video_capture()
        self._v4l2_camera_settings()
        self._apply_preset()
        self._warmup()

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def read(self) -> tuple[bool, MatLike | None]:
        c = self._cap()

        ok, frame = c.read()
        if not ok or frame is None:
            print("Can't receive frame (stream end?). Exiting ...")
            return False, None

        frame = cv.rotate(frame, cv.ROTATE_90_CLOCKWISE)
        frame = self._crop_top_and_bottom(frame)
        return True, frame

    def snapshot(self) -> None:
        self._cap()

        snapshots_dir = os.path.join(os.getcwd(), "snapshots")
        os.makedirs(snapshots_dir, exist_ok=True)

        filename = time.strftime("snapshot-%Y%m%d-%H%M%S.jpg")
        path = os.path.join(snapshots_dir, filename)

        self._warmup()

        ok, frame = self.read()
        if not ok or frame is None:
            raise RuntimeError("Failed to grab frame for snapshot.")

        success = cv.imwrite(path, frame, [cv.IMWRITE_JPEG_QUALITY, 100])
        if not success:
            raise RuntimeError(f"Failed to write snapshot to {path}")

    # --- Setup helpers --------------------------------------------

    def _create_video_capture(self) -> None:
        self.cap = cv.VideoCapture(self.device, cv.CAP_V4L2)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            print(f"[FATAL] Failed to open camera at {self.device}", file=sys.stderr)
            raise RuntimeError(f"Failed to open camera at {self.device}")

    def _v4l2_camera_settings(self) -> None:
        c = self._cap()

        fourcc_code = int(cv.VideoWriter.fourcc(*"MJPG"))

        c.set(cv.CAP_PROP_FOURCC, fourcc_code)
        c.set(cv.CAP_PROP_FRAME_WIDTH, self.resolution.width)
        c.set(cv.CAP_PROP_FRAME_HEIGHT, self.resolution.height)
        c.set(cv.CAP_PROP_FPS, self.fps)
        c.set(cv.CAP_PROP_BUFFERSIZE, self.buffersize)

    def _warmup(self) -> None:
        c = self._cap()
        for _ in range(3):
            c.read()

    def _crop_top_and_bottom(
        self, frame: MatLike, top: float = 0.047, bottom: float = 0.0625
    ) -> MatLike:
        h, w = frame.shape[:2]
        top = max(0.0, float(top))
        bottom = max(0.0, float(bottom))

        top_px = int(round(h * top))
        bottom_px = int(round(h * bottom))

        if top_px + bottom_px >= h:
            top_px = min(top_px, h - 1)
            bottom_px = h - 1 - top_px

        return frame[top_px : h - bottom_px, 0:w]

    def _apply_preset(self) -> None:
        settings = CAMERA_PRESETS[self.preset]
        self._v4l2_image_settings(**settings)

    def _v4l2_image_settings(
        self,
        brightness: int = 0,
        contrast: int = 0,
        saturation: int = 56,
        hue: int = 0,
        gamma: int = 110,
        sharpness: int = 0,
        backlight_compensation: int = 54,
        gain: int = 0,
        auto_exposure: int = 1,
        exposure: int = 2,
        auto_white_balance: int = 0,
        white_balance_temperature: int = 4600,
        power_line_frequency: int = 1,
        auto_focus: int = 0,
        focus_absolute: int = 0,
    ) -> None:
        c = self._cap()

        c.set(cv.CAP_PROP_BRIGHTNESS, brightness)
        c.set(cv.CAP_PROP_CONTRAST, contrast)
        c.set(cv.CAP_PROP_SATURATION, saturation)
        c.set(cv.CAP_PROP_HUE, hue)
        c.set(cv.CAP_PROP_GAMMA, gamma)
        c.set(cv.CAP_PROP_SHARPNESS, sharpness)
        c.set(cv.CAP_PROP_BACKLIGHT, backlight_compensation)
        c.set(cv.CAP_PROP_GAIN, gain)
        c.set(cv.CAP_PROP_AUTO_EXPOSURE, auto_exposure)
        c.set(cv.CAP_PROP_EXPOSURE, exposure)
        c.set(cv.CAP_PROP_AUTO_WB, auto_white_balance)
        c.set(cv.CAP_PROP_WB_TEMPERATURE, white_balance_temperature)

        powerline_prop = getattr(cv, "CAP_PROP_POWERLINE_FREQUENCY", None)
        if powerline_prop is not None:
            c.set(powerline_prop, power_line_frequency)

        c.set(cv.CAP_PROP_AUTOFOCUS, auto_focus)
        c.set(cv.CAP_PROP_FOCUS, focus_absolute)