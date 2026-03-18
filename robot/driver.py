"""High-level robot orchestrator — plans A* routes and drives them with camera-based line following."""

import time
import signal
import threading

from camera import (
    Camera, Resolution,
    detect_aruco, get_default_cache,
    detect_blue_line, line_from_aruco,
)
from robot import Robot
from steering import PDState, profile_speed, LOOP_HZ
from navigator import (
    Cell, Turn, grid,
    find_best_path, path_to_commands, merge_moves,
    DIRECTIONS, DIRECTION_INDEX,
)
from nav_logger import NavLogger, ts

# ── drive-loop config ────────────────────────────────

PIXEL_TO_MM = 0.245
LEG_DISTANCE_MM = 1000       # distance between adjacent markers
TURN_SPEED = 0.15            # m/s for robot.rotate()

# ── display helpers ──────────────────────────────────

DIR_ARROW = {"north": "\u2191", "east": "\u2192", "south": "\u2193", "west": "\u2190"}


def _turn_label(t: Turn) -> str:
    return {Turn.LEFT: "LEFT", Turn.RIGHT: "RIGHT", Turn.BACK: "BACK"}[t]


# ── Driver ───────────────────────────────────────────

class Driver:
    def __init__(self):
        self.cell = None
        self.facing = None

        self.hw = Robot(ramp_ms=0)
        self.hw.disable()

        self.cam = Camera(resolution=Resolution.RES_640x480, fps=LOOP_HZ)
        self.cam.open()
        self.aruco_cache = get_default_cache()
        self.pd = PDState()

        self._running = True
        self._stop_event = threading.Event()
        self.logger = NavLogger()
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        print(f"  {ts()}  looking for marker to detect position ...")
        self._detect_position()

    def _detect_position(self):
        """Read camera frames until a valid ArUco marker is found, then set cell and facing."""
        while self._running:
            ok, frame = self.cam.read()
            if not ok or frame is None:
                time.sleep(0.01)
                continue

            aruco = detect_aruco(frame, cache=self.aruco_cache)
            if aruco is None or not grid.is_valid_cell(aruco.id):
                continue

            self.cell = aruco.id
            idx = round(aruco.angle_deg / 90) % 4
            self.facing = ["north", "west", "south", "east"][idx]
            self._update_log_defaults()
            self.logger.log(event="DETECT", aruco_id=aruco.id,
                            aruco_angle=f"{aruco.angle_deg:.1f}")
            print(f"  {ts()}  detected: cell={self.cell}  "
                  f"facing={self.facing} {DIR_ARROW[self.facing]}  "
                  f"(angle={aruco.angle_deg:.1f} deg)\n")
            return

    def _shutdown(self, sig, _f):
        self._running = False

    def close(self):
        self.hw.close()
        self.cam.release()

    def _update_log_defaults(self):
        self.logger.defaults = {
            "cell": self.cell,
            "facing": self.facing,
        }

    def go_to(self, target, on_event=None):
        self._stop_event.clear()

        def _emit(event, data=None):
            if on_event:
                on_event(event, data or {})

        if not grid.is_valid_cell(target):
            print(f"  {ts()}  error: invalid cell {target}")
            _emit("error", {"message": f"invalid cell {target}"})
            return
        if target == self.cell:
            print(f"  {ts()}  already on {target}")
            _emit("nav_done", {"cell": self.cell})
            return

        # Open CSV log for this navigation
        log_path = self.logger.open()
        self._update_log_defaults()
        print(f"  {ts()}  logging to {log_path}")

        path = find_best_path(Cell(self.cell), Cell(target), self.facing)
        cmds = merge_moves(path_to_commands(path, Cell(self.cell), self.facing))

        # Serialize route for the event callback
        route = []
        for cmd in cmds:
            if cmd["type"] == "turn":
                route.append({"cmd": "turn", "deg": int(cmd["turn"]) * 90})
            else:
                route.append({"cmd": "move", "steps": cmd["steps"]})

        _emit("nav_start", {"cell": self.cell, "target": target, "route": route})

        print(f"  {ts()}  go_to({target}) -- {len(cmds)} commands:")
        for cmd in cmds:
            if cmd["type"] == "turn":
                delta = int(cmd["turn"])
                self.logger.log(event="PLAN", turn_cmd=delta, turn_deg=delta * 90)
                print(f"           TURN {_turn_label(cmd['turn'])}")
            else:
                self.logger.log(event="PLAN", d_mm=cmd["steps"] * LEG_DISTANCE_MM)
                print(f"           MOVE {cmd['steps']}")
        print()

        for i, cmd in enumerate(cmds):
            if not self._running or self._stop_event.is_set():
                self.hw.stop()
                self.hw.disable()
                print(f"  {ts()}  interrupted!")
                _emit("stopped", {"cell": self.cell})
                break

            if cmd["type"] == "turn":
                delta = int(cmd["turn"])
                degrees = delta * 90.0
                self.facing = DIRECTIONS[(DIRECTION_INDEX[self.facing] + delta) % 4]
                self._update_log_defaults()
                label = _turn_label(cmd["turn"])
                self.logger.log(event="TURN_START", turn_cmd=delta,
                                turn_deg=degrees)
                _emit("turn_start", {"deg": degrees})
                print(f"  {ts()}  [{i+1}/{len(cmds)}] TURN {label} ({degrees:.0f} deg) ...")
                self.hw.enable()
                self.hw.rotate(degrees, speed=TURN_SPEED)
                self.hw.disable()
                # flush stale V4L2 frames captured before/during the turn
                for _ in range(self.cam.buffersize + 1):
                    self.cam.read()
                self.logger.log(event="TURN_DONE")
                _emit("turn_done", {"facing": self.facing})
                print(f"  {ts()}  [{i+1}/{len(cmds)}] TURN done  "
                      f"(facing {self.facing} {DIR_ARROW[self.facing]})")
            else:
                steps = cmd["steps"]
                total_mm = steps * LEG_DISTANCE_MM
                print(f"  {ts()}  [{i+1}/{len(cmds)}] MOVE {steps} "
                      f"({total_mm:.0f} mm) ...")
                ok = self._drive_move(total_mm, on_event=on_event)
                if ok:
                    self.cell = int(grid.destination(Cell(self.cell), self.facing, steps))
                    self._update_log_defaults()
                    _emit("move_done", {"cell": self.cell})
                    print(f"\n  {ts()}  [{i+1}/{len(cmds)}] MOVE done  "
                          f"(now on cell {self.cell})")
                else:
                    print(f"\n  {ts()}  [{i+1}/{len(cmds)}] MOVE interrupted")
                    _emit("stopped", {"cell": self.cell})
                    break

        _emit("nav_done", {"cell": self.cell, "facing": self.facing})
        print(f"  {ts()}  done -- cell {self.cell}, "
              f"facing {self.facing} {DIR_ARROW[self.facing]}\n")

        self.logger.close()

    def _drive_move(self, default_distance_mm: float, on_event=None):
        """Drive forward with line following until distance is covered.

        Returns True if the move completed, False if interrupted.
        """
        state = "IDLE"
        idle_since = time.monotonic()
        trip_mm = 0.0
        ticks_start = (0, 0)
        self.pd.reset()

        while self._running and not self._stop_event.is_set():
            t0 = time.monotonic()

            ok, frame = self.cam.read()
            if not ok or frame is None:
                time.sleep(0.01)
                continue

            aruco = detect_aruco(frame, cache=self.aruco_cache)
            if aruco is not None:
                line = line_from_aruco(aruco, frame.shape, facing=self.facing)
            else:
                line = detect_blue_line(frame)

            if state == "IDLE":
                if aruco and aruco.id == self.cell_ahead():
                    # We see the start marker — compute trip distance and go
                    offset_px = frame.shape[1] / 2.0 - aruco.center.x
                    trip_mm = default_distance_mm + offset_px * PIXEL_TO_MM
                    ticks_start = self.hw.get_wheel_ticks()
                    self.pd.reset()
                    self.hw.enable()
                    state = "MOVING"
                    print(f"  {ts()}  [marker {aruco.id} seen] "
                          f"trip={trip_mm:.0f} mm")
                elif time.monotonic() - idle_since > 2.0:
                    # Marker not visible — start with default distance
                    trip_mm = default_distance_mm
                    ticks_start = self.hw.get_wheel_ticks()
                    self.pd.reset()
                    self.hw.enable()
                    state = "MOVING"
                    print(f"  {ts()}  [no marker after 2s, using default "
                          f"trip={trip_mm:.0f} mm]")

            elif state == "MOVING":
                lt, rt = self.hw.get_wheel_ticks()
                avg_ticks = ((lt - ticks_start[0]) + (rt - ticks_start[1])) / 2
                traveled = abs(self.hw.ticks_to_meters(avg_ticks))
                remaining = max(0.0, trip_mm / 1000.0 - traveled)

                if remaining < 0.005:
                    self.hw.set_rpm(0, 0)
                    self.hw.disable()
                    self.logger.log(event="MOVE_DONE",
                                   d_mm=f"{traveled*1000:.0f}")
                    print(f"\n  {ts()}  [STOP] {traveled * 1000:.0f} mm traveled")
                    return True

                speed = profile_speed(traveled, remaining)
                if line:
                    lv, rv = self.pd.update(line, speed)
                else:
                    lv, rv = speed, speed
                self.hw.set_velocity(lv, rv)
                self.logger.log(
                    event="MOVE_FRAME",
                    aruco_id=aruco.id if aruco else "",
                    aruco_angle=f"{aruco.angle_deg:.1f}" if aruco else "",
                    line_angle=f"{line.angle:.1f}" if line else "",
                    line_ox=f"{line.offset_x:.1f}" if line else "",
                    line_oy=f"{line.offset_y:.1f}" if line else "",
                    speed=f"{speed:.3f}",
                    lv=f"{lv:.3f}", rv=f"{rv:.3f}",
                    d_mm=f"{traveled*1000:.0f}",
                    rem_mm=f"{remaining*1000:.0f}",
                )

                # Emit telemetry for WebSocket clients
                if on_event:
                    on_event("move_frame", {
                        "speed": round(speed, 3),
                        "lv": round(lv, 3), "rv": round(rv, 3),
                        "d_mm": round(traveled * 1000),
                        "rem_mm": round(remaining * 1000),
                        "line_angle": round(line.angle, 1) if line else None,
                        "aruco_id": aruco.id if aruco else None,
                    })

                aruco_info = f"aruco={aruco.angle_deg:.1f}\u00b0" if aruco else "no_aruco"
                line_info  = f"line={line.angle:.1f}\u00b0" if line else "no_line"
                print(f"  d={traveled*1000:.0f}  rem={remaining*1000:.0f}  "
                      f"v={speed:.3f}  {aruco_info}  {line_info}  "
                      f"lv={lv:.3f} rv={rv:.3f}", end="\r")

            sleep_t = (1.0 / LOOP_HZ) - (time.monotonic() - t0)
            if sleep_t > 0:
                time.sleep(sleep_t)

        # If we exited due to stop/interrupt, ensure motors are off
        self.hw.set_rpm(0, 0)
        self.hw.disable()
        return False

    def request_stop(self):
        """Signal the drive loop to stop. Thread-safe."""
        self._stop_event.set()

    def cell_ahead(self):
        """The marker ID at the current cell (where the robot is starting from)."""
        return self.cell
