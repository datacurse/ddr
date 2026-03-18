"""
High-level motor controller API.
"""

from __future__ import annotations

import atexit
import math
from typing import Tuple

from .types import Fault, MAXIMUM_RPM, OperationMode, WheelOdometry
from .transport import Command, ModbusTransport, Register


class MotorController:
    """Velocity-mode driver for a ZLAC dual motor controller.

    No hardware ramps — caller is responsible for smooth velocity profiles.
    Automatically disables motors and closes the port on interpreter exit.

    Usage:
        controller = MotorController("/dev/ttyACM0")
        controller.enable()
        controller.set_rpm(30, -30)
        ...
        controller.set_rpm(0, 0)
    """

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baudrate: int = 115200,
        timeout: float = 1.0,
        unit_id: int = 1,
        odometry: WheelOdometry | None = None,
        ramp_ms: int = 50,
    ):
        self.odometry = odometry or WheelOdometry()
        self.ramp_ms = ramp_ms
        self._transport = ModbusTransport(port, baudrate, timeout, unit_id)
        atexit.register(self._shutdown)

    def _shutdown(self):
        """Called automatically at interpreter exit."""
        try:
            self.disable()
        except Exception:
            pass
        self.close()

    def close(self):
        self._transport.close()

    # ── Lifecycle ──

    def enable(self, mode: OperationMode = OperationMode.VELOCITY):
        self._transport.write_register(Register.OPERATION_MODE, mode)
        self._transport.write_registers(
            Register.LEFT_ACCELERATION_TIME, [self.ramp_ms, self.ramp_ms]
        )
        self._transport.write_registers(
            Register.LEFT_DECELERATION_TIME, [self.ramp_ms, self.ramp_ms]
        )
        self._transport.write_register(Register.CONTROL, Command.ENABLE)

    def disable(self):
        self._transport.write_register(Register.CONTROL, Command.DISABLE)

    def emergency_stop(self):
        self._transport.write_register(Register.CONTROL, Command.EMERGENCY_STOP)

    def clear_alarm(self):
        self._transport.write_register(Register.CONTROL, Command.ALARM_CLEAR)

    # ── Velocity ──

    def set_rpm(self, left: int, right: int):
        """Command wheel speeds in RPM.  Clamped to ±3000.

        Both positive = forward, both negative = backward,
        opposite signs = rotate in place.
        The right motor is physically mirrored — this method handles
        the sign inversion internally.
        """
        left  = max(-MAXIMUM_RPM, min(MAXIMUM_RPM, left))
        right = max(-MAXIMUM_RPM, min(MAXIMUM_RPM, right))
        self._transport.write_registers(Register.LEFT_COMMAND_RPM, [
            self._transport.signed_to_unsigned_16bit(-left),
            self._transport.signed_to_unsigned_16bit(right),
        ])

    def get_rpm(self) -> Tuple[float, float]:
        """Read actual RPM feedback → (left, right).

        Both positive = forward, matching set_rpm convention.
        """
        registers = self._transport.read_registers(Register.LEFT_FEEDBACK_RPM, 2)
        return (
            -self._transport.unsigned_to_signed_16bit(registers[0]) / 10.0,
            self._transport.unsigned_to_signed_16bit(registers[1]) / 10.0,
        )

    def get_linear_velocities(self) -> Tuple[float, float]:
        """Wheel velocities in m/s (both positive = forward)."""
        left_rpm, right_rpm = self.get_rpm()
        radians_per_second_per_rpm = 2.0 * math.pi / 60.0
        meters_per_radian = self.odometry.wheel_radius_meters
        conversion_factor = radians_per_second_per_rpm * meters_per_radian
        return left_rpm * conversion_factor, right_rpm * conversion_factor

    # ── Odometry ──

    def get_wheel_ticks(self) -> Tuple[int, int]:
        """Encoder ticks (signed 32-bit, cumulative). Both positive = forward."""
        registers = self._transport.read_registers(
            Register.LEFT_FEEDBACK_POSITION_HI, 4,
        )
        left_ticks = self._transport.unsigned_pair_to_signed_32bit(
            registers[0], registers[1],
        )
        right_ticks = self._transport.unsigned_pair_to_signed_32bit(
            registers[2], registers[3],
        )
        return -left_ticks, right_ticks

    def get_wheel_distances(self) -> Tuple[float, float]:
        """Accumulated travel in meters (both positive = forward)."""
        left_ticks, right_ticks = self.get_wheel_ticks()
        meters_per_tick = self.odometry.meters_per_tick
        return left_ticks * meters_per_tick, right_ticks * meters_per_tick

    # ── Faults ──

    def get_faults(self) -> Tuple[Fault, Fault]:
        """Read fault flags → (left, right).  Check with `if fault: ...`"""
        registers = self._transport.read_registers(Register.LEFT_FAULT, 2)
        return Fault(registers[0]), Fault(registers[1])