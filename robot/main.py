#!/usr/bin/env python3
"""
Grid Robot — A* pathfinding with real hardware control.

Grid:  3 7
       2 6
       1 5
       0 4

Type a cell number (0-7) to navigate there. The robot plans an optimal
route (A* with turn costs), then turns and drives each segment using
camera-based line following.
"""

from driver import Driver


def main():
    bot = Driver()
    try:
        while True:
            try:
                raw = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if raw.lower() in ("q", "quit", "exit", ""):
                break
            try:
                bot.go_to(int(raw))
            except ValueError:
                print(f"  enter 0-7 or q\n")
    finally:
        bot.close()


if __name__ == "__main__":
    main()
