"""Dead-simple robot movement: move(meters), rotate(degrees), stop().

Also exposes low-level RPM / tick access for external control loops.
"""

import math
import time
from zlac import MotorController, WheelOdometry

WHEEL_RADIUS_METERS   = 0.127 / 2
TRACK_WIDTH_METERS    = 0.38     # centre-to-centre wheel distance
DEFAULT_SPEED         = 0.3     # m/s
DEFAULT_ACC           = 1.0     # m/s²
DEFAULT_DEC           = 2.0     # m/s²
POLL_INTERVAL_SECONDS = 0.05


class Robot:
    def __init__(self, port: str = "/dev/ttyACM0", ramp_ms: int = 50):
        self._odometry = WheelOdometry(wheel_radius_meters=WHEEL_RADIUS_METERS)
        self._ctrl = MotorController(port, odometry=self._odometry, ramp_ms=ramp_ms)
        self._clear_faults()
        self._ctrl.enable()

    # ══════════════════════════════════════════════════════════
    # HIGH-LEVEL (blocking, self-contained)
    # ══════════════════════════════════════════════════════════

    def move(self, meters: float, speed: float = DEFAULT_SPEED,
             acc: float = DEFAULT_ACC, dec: float = DEFAULT_DEC):
        total_distance = abs(meters)
        direction = 1 if meters >= 0 else -1
        v_max = abs(speed)

        ticks_start = self.get_wheel_ticks()
        start_time = time.monotonic()

        while True:
            left, right = self.get_wheel_ticks()
            avg = ((left - ticks_start[0]) + (right - ticks_start[1])) / 2
            traveled = abs(self.ticks_to_meters(avg))
            remaining = total_distance - traveled

            if remaining <= 0:
                break

            elapsed = time.monotonic() - start_time
            v_acc = acc * elapsed
            v_dec = math.sqrt(2 * dec * remaining)

            v = min(v_max, v_acc, v_dec)
            rpm = max(1, int(self._velocity_to_rpm(v)))
            self.set_rpm(direction * rpm, direction * rpm)

            time.sleep(POLL_INTERVAL_SECONDS)

        self.stop()
        self._wait_until_stopped()

    def rotate(self, degrees: float, speed: float = DEFAULT_SPEED,
               acc: float = DEFAULT_ACC, dec: float = DEFAULT_DEC):
        """Rotate in place by the given angle.

        degrees: positive = clockwise, negative = counter-clockwise.
        speed:   max tangential wheel speed in m/s.
        acc:     acceleration in m/s².
        dec:     deceleration in m/s².
        Blocks until done.
        """
        if degrees == 0:
            return

        direction = 1 if degrees > 0 else -1   # +1 = CW, -1 = CCW
        v_max = abs(speed)

        # arc each wheel must travel for the requested chassis rotation
        wheel_arc = abs(math.radians(degrees)) * (TRACK_WIDTH_METERS / 2)

        ticks_start = self.get_wheel_ticks()
        start_time = time.monotonic()

        while True:
            left, right = self.get_wheel_ticks()
            # wheels spin opposite directions, so use abs of each delta
            delta_l = abs(left  - ticks_start[0])
            delta_r = abs(right - ticks_start[1])
            traveled_arc = (delta_l + delta_r) / 2 * self._odometry.meters_per_tick
            remaining = wheel_arc - traveled_arc

            if remaining <= 0:
                break

            elapsed = time.monotonic() - start_time
            v_acc = acc * elapsed
            v_dec = math.sqrt(2 * dec * remaining)

            v = min(v_max, v_acc, v_dec)
            rpm = max(1, int(self._velocity_to_rpm(v)))
            # CW: left forward, right backward
            self.set_rpm(direction * rpm, -direction * rpm)

            time.sleep(POLL_INTERVAL_SECONDS)

        self.stop()
        self._wait_until_stopped()

    def stop(self):
        self.set_rpm(0, 0)

    def enable(self):
        """Engage the motor controller — wheels are held in position."""
        self._ctrl.enable()

    def disable(self):
        """Disengage the motor controller — wheels spin freely."""
        self.stop()
        self._ctrl.disable()

    def close(self):
        self.disable()
        self._ctrl.close()

    # ══════════════════════════════════════════════════════════
    # LOW-LEVEL (for external control loops)
    # ══════════════════════════════════════════════════════════

    def set_rpm(self, left: float, right: float):
        """Set raw wheel RPMs (positive = forward).

        Accepts floats for smooth control math — rounds to int
        at the hardware boundary since the controller uses 16-bit registers.
        """
        self._ctrl.set_rpm(int(round(left)), int(round(right)))

    def get_rpm(self) -> tuple[float, float]:
        """Return current (left, right) RPMs as reported by the controller."""
        return self._ctrl.get_rpm()

    def set_velocity(self, left_ms: float, right_ms: float):
        """Set wheel speeds in m/s (positive = forward)."""
        self.set_rpm(self.velocity_to_rpm(left_ms), self.velocity_to_rpm(right_ms))

    def get_velocity(self) -> tuple[float, float]:
        """Return current (left, right) wheel speeds in m/s."""
        left_rpm, right_rpm = self.get_rpm()
        return self.rpm_to_velocity(left_rpm), self.rpm_to_velocity(right_rpm)

    def get_wheel_ticks(self) -> tuple[int, int]:
        """Return current (left, right) encoder tick counts."""
        return self._ctrl.get_wheel_ticks()

    def ticks_to_meters(self, ticks: float) -> float:
        """Convert an encoder tick delta to a distance in meters."""
        return self._odometry.distance_for_ticks(ticks)

    def velocity_to_rpm(self, velocity: float) -> float:
        """Convert a velocity in m/s to RPM."""
        return velocity / (2.0 * math.pi / 60.0) / self._odometry.wheel_radius_meters

    def rpm_to_velocity(self, rpm: float) -> float:
        """Convert RPM to velocity in m/s."""
        return rpm * (2.0 * math.pi / 60.0) * self._odometry.wheel_radius_meters

    # ══════════════════════════════════════════════════════════
    # INTERNALS
    # ══════════════════════════════════════════════════════════

    def _velocity_to_rpm(self, velocity: float) -> float:
        return self.velocity_to_rpm(velocity)

    def _wait_until_stopped(self):
        while True:
            left_rpm, right_rpm = self.get_rpm()
            if abs(left_rpm) < 0.5 and abs(right_rpm) < 0.5:
                break
            time.sleep(POLL_INTERVAL_SECONDS)
        time.sleep(0.1)

    def _clear_faults(self):
        left, right = self._ctrl.get_faults()
        if left or right:
            self._ctrl.clear_alarm()
            time.sleep(0.5)


if __name__ == "__main__":
    robot = Robot()
    try:
        robot.rotate(90, speed=0.15, acc=1.0, dec=2.0)
    finally:
        robot.close()