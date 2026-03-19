"""WebSocket server for remote robot control from a mobile app."""

import asyncio
import json
import threading
import time

import websockets

from driver import Driver
from navigator import grid, Cell

PORT = 8765
TELEMETRY_HZ = 10  # broadcast rate to clients


class RobotServer:
    def __init__(self):
        self.driver = Driver()
        self.clients: set[websockets.WebSocketServerProtocol] = set()
        self.status = "idle"     # idle | navigating | turning | moving
        self.target = None
        self.route = None
        self._telemetry = {}     # latest frame data, written by driver thread
        self._nav_thread = None
        self._loop = None        # asyncio event loop, set in run()

    # ── WebSocket handlers ──────────────────────────────

    async def _handler(self, ws):
        self.clients.add(ws)
        print(f"[ws] client connected ({len(self.clients)} total)")
        try:
            # Send current state on connect
            await ws.send(json.dumps(self._state_msg()))
            await ws.send(json.dumps(self._grid_msg()))

            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send(json.dumps({"type": "error", "message": "invalid JSON"}))
                    continue
                await self._handle_msg(ws, msg)
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)
            print(f"[ws] client disconnected ({len(self.clients)} total)")

    async def _handle_msg(self, ws, msg):
        msg_type = msg.get("type")

        if msg_type == "status":
            await ws.send(json.dumps(self._state_msg()))

        elif msg_type == "grid":
            await ws.send(json.dumps(self._grid_msg()))

        elif msg_type == "go_to":
            cell = msg.get("cell")
            if cell is None:
                await ws.send(json.dumps({"type": "error", "message": "missing cell"}))
                return
            if self.status != "idle":
                await ws.send(json.dumps({"type": "error", "message": "robot is busy"}))
                return
            self._start_nav(int(cell))

        elif msg_type == "stop":
            self.driver.request_stop()

        else:
            await ws.send(json.dumps({"type": "error", "message": f"unknown type: {msg_type}"}))

    # ── State messages ──────────────────────────────────

    def _state_msg(self):
        return {
            "type": "state",
            "cell": self.driver.cell,
            "facing": self.driver.facing,
            "status": self.status,
            "target": self.target,
        }

    def _grid_msg(self):
        cells = {}
        for cell_id in range(8):
            c = Cell(cell_id)
            if grid.is_valid_cell(c):
                x, y = grid.cell_to_pos(c)
                cells[str(cell_id)] = [x, y]
        return {"type": "grid", "cells": cells}

    # ── Navigation in background thread ─────────────────

    def _start_nav(self, target):
        self.status = "navigating"
        self.target = target
        self._telemetry = {}
        self._nav_thread = threading.Thread(
            target=self._nav_worker, args=(target,), daemon=True
        )
        self._nav_thread.start()

    def _nav_worker(self, target):
        """Runs in a background thread — calls the blocking driver.go_to()."""
        try:
            self.driver.go_to(target, on_event=self._on_driver_event)
        except Exception as e:
            self._broadcast_soon({"type": "error", "message": str(e)})
        finally:
            self.status = "idle"
            self.target = None
            self.route = None
            self._telemetry = {}
            # Sync client state even if nav_done/stopped was lost
            self._broadcast_soon(self._state_msg())

    def _on_driver_event(self, event, data):
        """Callback from Driver, called from the driver thread."""
        if event == "nav_start":
            self.status = "navigating"
            self.route = data.get("route")
            self._broadcast_soon({
                "type": "nav_start",
                "cell": data.get("cell"),
                "target": data.get("target"),
                "route": data.get("route"),
            })

        elif event == "turn_start":
            self.status = "turning"
            self._telemetry = {}
            self._broadcast_soon({"type": "turn_start", "deg": data.get("deg")})

        elif event == "turn_done":
            self.status = "moving"
            self._broadcast_soon({
                "type": "turn_done",
                "facing": data.get("facing"),
            })

        elif event == "move_frame":
            # Just update the shared telemetry dict — the broadcast task sends it
            self._telemetry = {
                "type": "telemetry",
                "cell": self.driver.cell,
                "facing": self.driver.facing,
                "status": self.status,
                **data,
            }

        elif event == "move_done":
            self._telemetry = {}
            self._broadcast_soon({
                "type": "move_done",
                "cell": data.get("cell"),
            })

        elif event == "nav_done":
            self._broadcast_soon({
                "type": "nav_done",
                "cell": data.get("cell"),
                "facing": data.get("facing"),
            })

        elif event == "stopped":
            self._telemetry = {}
            self._broadcast_soon({
                "type": "stopped",
                "cell": data.get("cell"),
            })

        elif event == "error":
            self._broadcast_soon({
                "type": "error",
                "message": data.get("message"),
            })

    # ── Async broadcast helpers ─────────────────────────

    def _broadcast_soon(self, msg):
        """Schedule a broadcast from any thread."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                asyncio.ensure_future, self._broadcast(msg)
            )

    async def _broadcast(self, msg):
        """Send a message to all connected clients."""
        if not self.clients:
            return
        payload = json.dumps(msg)
        await asyncio.gather(
            *(client.send(payload) for client in self.clients),
            return_exceptions=True,
        )

    async def _telemetry_loop(self):
        """Periodically broadcast the latest telemetry at TELEMETRY_HZ."""
        while True:
            if self._telemetry and self.clients:
                await self._broadcast(self._telemetry)
            await asyncio.sleep(1.0 / TELEMETRY_HZ)

    # ── Main entry point ────────────────────────────────

    async def run(self):
        self._loop = asyncio.get_running_loop()
        asyncio.create_task(self._telemetry_loop())

        async with websockets.serve(self._handler, "0.0.0.0", PORT):
            print(f"[server] listening on ws://0.0.0.0:{PORT}")
            print(f"[server] robot at cell {self.driver.cell}, facing {self.driver.facing}")
            await asyncio.Future()  # run forever


def main():
    server = RobotServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n[server] shutting down")
    finally:
        server.driver.close()


if __name__ == "__main__":
    main()
