"""PD steering controller and trapezoidal velocity profile for line following."""

import time

from camera import LineDetection

# ── motion profile ───────────────────────────────────

LOOP_HZ = 90
CRUISE_SPEED = 0.5           # m/s
ACCEL = 2                    # m/s^2
DECEL = 2                    # m/s^2
MIN_START_SPEED = 0.02       # m/s

# ── PD gains (line following) ────────────────────────

OFFSET_P, OFFSET_D = 0.000, 0.0000
HEADING_P, HEADING_D = 0.02, 0.002
SMOOTH, D_SMOOTH = 0.8, 0.8


class PDState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.off = 0.0
        self.hdg = 0.0
        self.d_off = 0.0
        self.d_hdg = 0.0
        self.t = None
        self._first = True

    def update(self, line: LineDetection, base_speed: float) -> tuple[float, float]:
        now = time.monotonic()

        if self._first:
            self.off = line.offset_x
            self.hdg = line.angle
            self._first = False
        else:
            self.off += SMOOTH * (line.offset_x - self.off)
            self.hdg += SMOOTH * (line.angle - self.hdg)

        dt = (now - self.t) if self.t else 1.0 / LOOP_HZ
        if dt > 0:
            self.d_off += D_SMOOTH * ((line.offset_x - self.off) / dt - self.d_off)
            self.d_hdg += D_SMOOTH * ((line.angle - self.hdg) / dt - self.d_hdg)

        self.t = now

        corr = (OFFSET_P * self.off
                + OFFSET_D * self.d_off
                + HEADING_P * self.hdg
                + HEADING_D * self.d_hdg)

        return base_speed + corr, base_speed - corr


def profile_speed(traveled: float, remaining: float) -> float:
    accel_d = CRUISE_SPEED / ACCEL
    decel_d = CRUISE_SPEED / DECEL
    v = min(CRUISE_SPEED * min(1.0, traveled / accel_d),
            CRUISE_SPEED * min(1.0, remaining / decel_d))
    return max(v, MIN_START_SPEED)
