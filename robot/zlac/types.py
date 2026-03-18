"""
Public types, enums, and constants for the ZLAC motor controller.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WheelOdometry:
    """Physical parameters of the wheel + encoder.

    Only wheel_radius_meters is required — everything else is derived
    or has a sensible default for the ZLAC8015D.
    """
    wheel_radius_meters: float = 0.064
    encoder_counts_per_revolution: int = 16385

    @property
    def travel_per_revolution_meters(self) -> float:
        return 2.0 * math.pi * self.wheel_radius_meters

    @property
    def meters_per_tick(self) -> float:
        return self.travel_per_revolution_meters / self.encoder_counts_per_revolution

    def ticks_for_distance(self, distance_meters: float) -> int:
        """How many encoder ticks correspond to a given linear distance."""
        return int(distance_meters / self.meters_per_tick)

    def distance_for_ticks(self, ticks: int) -> float:
        """How many meters correspond to a given number of encoder ticks."""
        return ticks * self.meters_per_tick


MAXIMUM_RPM = 3000


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class OperationMode(enum.IntEnum):
    """Operation modes written to register 0x200D."""
    POSITION_RELATIVE = 1
    POSITION_ABSOLUTE = 2
    VELOCITY          = 3
    TORQUE            = 4


class Fault(enum.IntFlag):
    """Bit-flag fault codes reported by the controller (registers 0x20A5/0x20A6)."""
    NONE                     = 0x0000
    OVER_VOLTAGE             = 0x0001
    UNDER_VOLTAGE            = 0x0002
    OVER_CURRENT             = 0x0004
    OVERLOAD                 = 0x0008
    CURRENT_OUT_OF_TOLERANCE = 0x0010
    ENCODER_OUT_OF_TOLERANCE = 0x0020
    SPEED_OUT_OF_TOLERANCE   = 0x0040
    REFERENCE_VOLTAGE_ERROR  = 0x0080
    EEPROM_ERROR             = 0x0100
    HALL_SENSOR_ERROR        = 0x0200
    HIGH_TEMPERATURE         = 0x0400