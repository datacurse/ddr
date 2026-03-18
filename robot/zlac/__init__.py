"""
ZLAC Dual Motor Controller — Modbus RTU Driver

A minimal driver for ZLAC-series dual brushless motor controllers
(e.g. ZLAC8015D) communicating over Modbus RTU (RS-485).

Quick start:
    >>> from zlac import MotorController
    >>> controller = MotorController("/dev/ttyACM0")
    >>> controller.enable()
    >>> controller.set_rpm(30, -30)
    >>> time.sleep(2)
    >>> controller.set_rpm(0, 0)
"""

from .types import Fault, MAXIMUM_RPM, OperationMode, WheelOdometry
from .controller import MotorController

__all__ = [
    "Fault",
    "MAXIMUM_RPM",
    "MotorController",
    "OperationMode",
    "WheelOdometry",
]