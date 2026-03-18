import heapq
from enum import IntEnum
from typing import Literal, TypeAlias, TypedDict


class Cell(int):
    """ArUco marker ID used as a grid cell identifier."""
Direction = Literal["north", "east", "south", "west"]


class Turn(IntEnum):
    LEFT = -1
    RIGHT = 1
    BACK = 2
Pos: TypeAlias = tuple[int, int]


class TurnCommand(TypedDict):
    type: Literal["turn"]
    turn: Turn


class MoveCommand(TypedDict):
    type: Literal["move"]
    steps: int


Command = TurnCommand | MoveCommand

DIRECTIONS: list[Direction] = ["north", "east", "south", "west"]
DIRECTION_INDEX: dict[Direction, int] = {d: i for i, d in enumerate(DIRECTIONS)}
DIRECTION_STEP: dict[Direction, Pos] = {"north": (0, 1), "east": (1, 0), "south": (0, -1), "west": (-1, 0)}

def shortest_turn(from_direction: Direction, to_direction: Direction) -> Turn | None:
    diff = (DIRECTION_INDEX[to_direction] - DIRECTION_INDEX[from_direction]) % 4
    if diff == 0:
        return None
    if diff == 3:
        diff = -1
    return Turn(diff)

class Grid:
    def __init__(self, layout: list[list[int]]) -> None:
        """layout: 2D list, top row = highest y, north is up."""
        self.cols = len(layout[0])
        self.rows = len(layout)
        self._cell_to_pos: dict[Cell, Pos] = {}
        self._pos_to_cell: dict[Pos, Cell] = {}
        for gy, row in enumerate(reversed(layout)):
            for gx, cell in enumerate(row):
                self._cell_to_pos[Cell(cell)] = (gx, gy)
                self._pos_to_cell[(gx, gy)] = Cell(cell)

    def cell_to_pos(self, cell: Cell) -> Pos:
        return self._cell_to_pos[cell]

    def pos_to_cell(self, x: int, y: int) -> Cell:
        return self._pos_to_cell[(x, y)]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows

    def is_valid_cell(self, cell_id: int) -> bool:
        return Cell(cell_id) in self._cell_to_pos

    def destination(self, from_cell: Cell, facing: Direction, steps: int) -> Cell:
        """Return the cell reached after moving `steps` in `facing` from `from_cell`."""
        x, y = self.cell_to_pos(from_cell)
        dx, dy = DIRECTION_STEP[facing]
        return self.pos_to_cell(x + dx * steps, y + dy * steps)

grid = Grid([
    [3, 7],
    [2, 6],
    [1, 5],
    [0, 4],
])

# 2. A* — find cheapest path considering turn costs
def find_best_path(from_cell: Cell, to_cell: Cell, facing: Direction) -> list[Direction]:
    from_x, from_y = grid.cell_to_pos(from_cell)
    goal_x, goal_y = grid.cell_to_pos(to_cell)

    if (from_x, from_y) == (goal_x, goal_y):
        return []

    def heuristic(x: int, y: int) -> int:
        return abs(x - goal_x) + abs(y - goal_y)

    # (f_score, tiebreaker, x, y, facing, path)
    start = (heuristic(from_x, from_y), 0, from_x, from_y, facing, [])
    open_set = [start]
    best_g = {(from_x, from_y, facing): 0}
    counter = 1

    while open_set:
        f_score, _, x, y, direction, path = heapq.heappop(open_set)
        g_score = f_score - heuristic(x, y)

        if x == goal_x and y == goal_y:
            return path

        if g_score > best_g.get((x, y, direction), float('inf')):
            continue

        # move forward
        dx, dy = DIRECTION_STEP[direction]
        nx, ny = x + dx, y + dy
        if grid.in_bounds(nx, ny):
            new_g_score = g_score + 1
            state = (nx, ny, direction)
            if new_g_score < best_g.get(state, float('inf')):
                best_g[state] = new_g_score
                heapq.heappush(open_set, (new_g_score + heuristic(nx, ny), counter, nx, ny, direction, path + [direction]))
                counter += 1

        # turn (90° left, 90° right, 180°)
        for delta in (-1, 1, 2):
            new_direction = DIRECTIONS[(DIRECTION_INDEX[direction] + delta) % 4]
            cost = 1 if abs(delta) == 1 else 2
            new_g_score = g_score + cost
            state = (x, y, new_direction)
            if new_g_score < best_g.get(state, float('inf')):
                best_g[state] = new_g_score
                heapq.heappush(open_set, (new_g_score + heuristic(x, y), counter, x, y, new_direction, path))
                counter += 1

    return []  # no path


# 3. CONVERT — path to robot commands
def path_to_commands(path: list[Direction], from_cell: Cell, facing: Direction | None = None) -> list[Command]:
    commands: list[Command] = []
    x, y = grid.cell_to_pos(from_cell)
    direction: Direction | None = facing

    for step_direction in path:
        if direction is not None:
            turn = shortest_turn(direction, step_direction)
            if turn is not None:
                commands.append({"type": "turn", "turn": turn})
        direction = step_direction
        dx, dy = DIRECTION_STEP[direction]
        x += dx
        y += dy
        commands.append({"type": "move", "steps": 1})

    return commands


def merge_moves(commands: list[Command]) -> list[Command]:
    """Merge consecutive move commands into one with combined step count."""
    merged: list[Command] = []
    for cmd in commands:
        if cmd["type"] == "move" and merged and merged[-1]["type"] == "move":
            merged[-1] = {"type": "move", "steps": merged[-1]["steps"] + cmd["steps"]}
        else:
            merged.append(cmd)
    return merged

if __name__ == "__main__":
    start, end, facing = Cell(0), Cell(6), "north"
    best_path = find_best_path(start, end, facing)
    print(f"Best path: {best_path}")
    print(f"Commands:")
    for cmd in merge_moves(path_to_commands(best_path, start, facing)):
        print(f"  {cmd}")
