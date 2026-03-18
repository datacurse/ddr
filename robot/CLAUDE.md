# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Differential-drive robot control system running on an Orange Pi (aarch64, Linux rockchip-rk3588). The robot follows blue lines on the floor between ArUco markers using a USB camera for vision and a ZLAC8015D dual brushless motor controller over Modbus RTU (RS-485) for drive.

## Hardware

- **Motors**: ZLAC8015D dual motor controller on `/dev/ttyACM0`, 127mm diameter wheels, 380mm track width
- **Camera**: USB V4L2 camera on `/dev/video0`, mounted vertically (frames rotated 90° CW in software), MJPG codec
- **Board**: Orange Pi with RK3588 SoC

## Running

All scripts run directly with Python from the venv:

```bash
source .venv/bin/activate
python main.py       # A* grid navigation with interactive REPL
python robot.py      # quick test: rotate 90°
```

There are no tests, no linter config, and no build step.

## Architecture

### Entry point (`main.py`)
Thin REPL — imports `Driver` from `driver.py`, prompts for a target cell (0-7), calls `driver.go_to()`.

### Orchestrator (`driver.py`)
`Driver` class wires together hardware, camera, navigation, and steering. Handles `go_to(cell)`: plans A* route, executes turn/move commands, runs the 90 Hz line-following drive loop with encoder-based distance tracking. Flushes stale V4L2 frames after blocking turns.

### Steering & motion profile (`steering.py`)
`PDState` class: PD controller for line-following (smoothed offset + heading correction). `profile_speed()`: trapezoidal velocity envelope (accel → cruise → decel). All tuning constants (PD gains, cruise speed, accel/decel rates) live here.

### Hardware abstraction (`robot.py`)
`Robot` class wraps the ZLAC motor controller. Provides high-level blocking `move(meters)` and `rotate(degrees)` with trapezoidal velocity profiles, plus low-level `set_rpm()`, `set_velocity()`, `get_wheel_ticks()` for external control loops.

### Navigation (`navigator.py`)
A* pathfinding on a 4x2 grid with turn-cost optimization. `Grid` class maps cell IDs to positions. `path_to_commands()` converts direction sequences to turn/move commands. `merge_moves()` combines consecutive moves.

### Navigation logging (`nav_logger.py`)
`NavLogger` class: timestamped CSV logging of navigation events (detect, plan, turn, move frames) to `.studies/nav_logs/`.

### Motor driver (`zlac/`)
Modbus RTU driver for the ZLAC8015D. `MotorController` handles enable/disable, RPM commands, encoder tick reading, and fault clearing. `WheelOdometry` converts ticks to meters.

### Vision (`camera/`)
- `camera.py` — `Camera` class: V4L2 capture with MJPG, resolution presets, auto-rotates frames 90° CW, crops top/bottom edges
- `aruco_detector.py` — Custom red-background ArUco detection (not OpenCV's built-in detector). Returns `ArucoMarker` NamedTuple with id, corners, center, angle. Uses `MarkerCache` for 5x5_100 dictionary matching
- `line_detector.py` — Blue line detection from HSV color segmentation
- `line_fusion.py` — Fuses ArUco-derived line data (preferred when marker visible) with blue-line fallback. Returns `LineDetection` (angle, offset_x, offset_y)

## Key conventions

- Speeds are in m/s for `Robot.set_velocity()` and `Robot.move()`, but in RPM for `Robot.set_rpm()` and in `patrol.py`'s Settings class
- Direction: `+1` = forward, `-1` = reverse. For rotation: positive = clockwise
- Camera frames are always rotated 90° CW from the raw V4L2 capture
- ArUco markers use red backgrounds with black code modules (custom detector, not cv2.aruco.detectMarkers)
- PD steering: offset correction flips sign with direction; heading correction does not
