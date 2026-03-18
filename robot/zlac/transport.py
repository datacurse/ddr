"""
Low-level Modbus RTU transport for the ZLAC motor controller.

Everything in this module is private to the package.
"""

from __future__ import annotations

import time

from pymodbus.client import ModbusSerialClient


# ─────────────────────────────────────────────────────────────
# Register map
# ─────────────────────────────────────────────────────────────

class Register:
    CONTROL                     = 0x200E
    OPERATION_MODE              = 0x200D

    LEFT_ACCELERATION_TIME      = 0x2080
    RIGHT_ACCELERATION_TIME     = 0x2081
    LEFT_DECELERATION_TIME      = 0x2082
    RIGHT_DECELERATION_TIME     = 0x2083

    LEFT_COMMAND_RPM            = 0x2088
    RIGHT_COMMAND_RPM           = 0x2089
    LEFT_FEEDBACK_RPM           = 0x20AB
    RIGHT_FEEDBACK_RPM          = 0x20AC

    LEFT_FEEDBACK_POSITION_HI   = 0x20A7
    LEFT_FEEDBACK_POSITION_LO   = 0x20A8
    RIGHT_FEEDBACK_POSITION_HI  = 0x20A9
    RIGHT_FEEDBACK_POSITION_LO  = 0x20AA

    LEFT_FAULT                  = 0x20A5
    RIGHT_FAULT                 = 0x20A6


class Command:
    EMERGENCY_STOP = 0x05
    ALARM_CLEAR    = 0x06
    DISABLE        = 0x07
    ENABLE         = 0x08


# ─────────────────────────────────────────────────────────────
# Modbus serial transport
# ─────────────────────────────────────────────────────────────

class ModbusTransport:
    """Thin wrapper around pymodbus with retry logic and integer helpers."""

    def __init__(self, port: str, baudrate: int, timeout: float, unit_id: int):
        self._client = ModbusSerialClient(
            port=port, baudrate=baudrate, timeout=timeout,
        )
        self._unit_id = unit_id
        if not self._client.connect():
            raise ConnectionError(f"Could not open Modbus on {port}")

    def close(self):
        self._client.close()

    def read_registers(self, address: int, count: int) -> list[int]:
        for _attempt in range(20):
            try:
                result = self._client.read_holding_registers(
                    address, count=count, device_id=self._unit_id,
                )
            except Exception:
                time.sleep(0.05)
                continue
            if hasattr(result, "registers"):
                return list(result.registers)
            time.sleep(0.005)
        raise ConnectionError(f"Failed to read register 0x{address:04X}")

    def write_register(self, address: int, value: int):
        self._client.write_register(address, value, device_id=self._unit_id)

    def write_registers(self, address: int, values: list[int]):
        self._client.write_registers(address, values, device_id=self._unit_id)

    # ── Integer encoding helpers ──

    @staticmethod
    def signed_to_unsigned_16bit(value: int) -> int:
        return value & 0xFFFF

    @staticmethod
    def unsigned_to_signed_16bit(value: int) -> int:
        value &= 0xFFFF
        return value - 0x10000 if value >= 0x8000 else value

    @staticmethod
    def unsigned_pair_to_signed_32bit(high_word: int, low_word: int) -> int:
        unsigned = ((high_word & 0xFFFF) << 16) | (low_word & 0xFFFF)
        return unsigned - 0x100000000 if unsigned >= 0x80000000 else unsigned