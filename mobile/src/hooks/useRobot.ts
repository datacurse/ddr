import { useReducer, useRef, useCallback, useEffect } from 'react';

// ── Types ──────────────────────────────────────────────────────────

type Facing = 'north' | 'east' | 'south' | 'west';
type ConnectionStatus = 'disconnected' | 'connecting' | 'connected';

interface Telemetry {
  speed: number;
  lv: number;
  rv: number;
  d_mm: number;
  rem_mm: number;
  line_angle: number | null;
  aruco_id: number | null;
}

interface LogEntry {
  id: number;
  ts: number;
  type: string;
  detail: string;
}

interface RobotState {
  connection: ConnectionStatus;
  cell: number | null;
  prevCell: number | null;
  facing: Facing | null;
  status: string;
  target: number | null;
  grid: Record<string, [number, number]>;
  route: number[];
  telemetry: Telemetry | null;
  turnDeg: number | null;
  error: string | null;
  logs: LogEntry[];
}

// ── Reducer ────────────────────────────────────────────────────────

type Action =
  | { type: 'CONNECT_START' }
  | { type: 'CONNECTED' }
  | { type: 'DISCONNECTED' }
  | { type: 'STATE_UPDATE'; cell: number; facing: Facing; status: string; target: number | null }
  | { type: 'GRID_UPDATE'; cells: Record<string, [number, number]> }
  | { type: 'NAV_START'; cell: number; target: number; route: number[] }
  | { type: 'TURN_START'; deg: number }
  | { type: 'TURN_DONE'; facing: Facing }
  | { type: 'TELEMETRY'; payload: Telemetry }
  | { type: 'MOVE_DONE'; cell: number }
  | { type: 'NAV_DONE'; cell: number; facing: Facing }
  | { type: 'STOPPED'; cell: number }
  | { type: 'ERROR'; message: string }
  | { type: 'CLEAR_ERROR' }
  | { type: 'CLEAR_LOGS' };

const INITIAL_STATE: RobotState = {
  connection: 'disconnected',
  cell: null,
  prevCell: null,
  facing: null,
  status: 'idle',
  target: null,
  grid: {},
  route: [],
  telemetry: null,
  turnDeg: null,
  error: null,
  logs: [],
};

let _logId = 0;

function appendLog(logs: LogEntry[], type: string, detail: string): LogEntry[] {
  const entry: LogEntry = { id: ++_logId, ts: Date.now(), type, detail };
  const next = [...logs, entry];
  return next.length > 200 ? next.slice(-200) : next;
}

function reducer(state: RobotState, action: Action): RobotState {
  switch (action.type) {
    case 'CONNECT_START':
      return { ...INITIAL_STATE, connection: 'connecting', logs: appendLog(state.logs, 'connect', 'Connecting…') };

    case 'CONNECTED':
      return { ...state, connection: 'connected', logs: appendLog(state.logs, 'connect', 'Connected') };

    case 'DISCONNECTED':
      return { ...INITIAL_STATE, logs: appendLog(state.logs, 'connect', 'Disconnected') };

    case 'STATE_UPDATE':
      return {
        ...state,
        cell: action.cell,
        facing: action.facing,
        status: action.status,
        target: action.target,
        ...(action.status === 'idle' ? { route: [], telemetry: null } : {}),
        logs: appendLog(state.logs, 'state', `Cell ${action.cell} · ${action.facing} · ${action.status}`),
      };

    case 'GRID_UPDATE':
      return { ...state, grid: action.cells, logs: appendLog(state.logs, 'grid', `Grid received (${Object.keys(action.cells).length} cells)`) };

    case 'NAV_START':
      return {
        ...state,
        cell: action.cell,
        prevCell: action.cell,
        target: action.target,
        route: action.route,
        status: 'navigating',
        logs: appendLog(state.logs, 'nav', `Nav to cell ${action.target}`),
      };

    case 'TURN_START':
      return { ...state, status: 'turning', turnDeg: action.deg, logs: appendLog(state.logs, 'nav', `Turning ${action.deg}°`) };

    case 'TURN_DONE':
      return { ...state, facing: action.facing, status: 'navigating', turnDeg: null, logs: appendLog(state.logs, 'nav', `Turn done · facing ${action.facing}`) };

    case 'TELEMETRY':
      return {
        ...state,
        telemetry: action.payload,
      };

    case 'MOVE_DONE':
      return { ...state, prevCell: state.cell, cell: action.cell, status: 'navigating', logs: appendLog(state.logs, 'nav', `Move done · cell ${action.cell}`) };

    case 'NAV_DONE':
      return {
        ...state,
        cell: action.cell,
        prevCell: null,
        facing: action.facing,
        status: 'idle',
        target: null,
        route: [],
        telemetry: null,
        turnDeg: null,
        logs: appendLog(state.logs, 'nav', `Nav complete · cell ${action.cell} · ${action.facing}`),
      };

    case 'STOPPED':
      return {
        ...state,
        cell: action.cell,
        prevCell: null,
        status: 'idle',
        target: null,
        route: [],
        telemetry: null,
        turnDeg: null,
        logs: appendLog(state.logs, 'stop', `Stopped at cell ${action.cell}`),
      };

    case 'ERROR':
      return { ...state, error: action.message, logs: appendLog(state.logs, 'error', action.message) };

    case 'CLEAR_ERROR':
      return { ...state, error: null };

    case 'CLEAR_LOGS':
      return { ...state, logs: [] };

    default:
      return state;
  }
}

// ── Helpers ────────────────────────────────────────────────────────

/** Compute the ordered cell sequence from nav_start route commands. */
function computeRouteCells(
  startCell: number,
  startFacing: Facing,
  commands: Array<{ cmd: string; deg?: number; steps?: number }>,
  grid: Record<string, [number, number]>,
): number[] {
  // Build reverse lookup: "x,y" → cellId
  const posToCell: Record<string, number> = {};
  for (const [id, [x, y]] of Object.entries(grid)) {
    posToCell[`${x},${y}`] = Number(id);
  }

  const FACING_DELTA: Record<string, [number, number]> = {
    north: [0, 1],
    east: [1, 0],
    south: [0, -1],
    west: [-1, 0],
  };

  const FACING_ORDER: Facing[] = ['north', 'east', 'south', 'west'];

  let pos = grid[String(startCell)];
  if (!pos) return [startCell];
  let [cx, cy] = pos;
  let facing = startFacing;
  const cells: number[] = [startCell];

  for (const cmd of commands) {
    if (cmd.cmd === 'turn' && cmd.deg !== undefined) {
      // Rotate facing by degrees (positive = clockwise)
      const steps = ((cmd.deg / 90) % 4 + 4) % 4;
      const idx = FACING_ORDER.indexOf(facing);
      facing = FACING_ORDER[(idx + steps) % 4];
    } else if (cmd.cmd === 'move' && cmd.steps !== undefined) {
      const [dx, dy] = FACING_DELTA[facing];
      for (let i = 0; i < cmd.steps; i++) {
        cx += dx;
        cy += dy;
        const key = `${cx},${cy}`;
        if (key in posToCell) {
          cells.push(posToCell[key]);
        }
      }
    }
  }

  return cells;
}

// ── Hook ───────────────────────────────────────────────────────────

export function useRobot() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const wsRef = useRef<WebSocket | null>(null);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Keep a ref to latest state so onmessage never has stale closures
  const stateRef = useRef(state);
  stateRef.current = state;

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    };
  }, []);

  const dispatchError = useCallback((message: string) => {
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    dispatch({ type: 'ERROR', message });
    errorTimerRef.current = setTimeout(() => dispatch({ type: 'CLEAR_ERROR' }), 3000);
  }, []);

  const connect = useCallback((ip: string) => {
    // Close existing connection
    wsRef.current?.close();
    dispatch({ type: 'CONNECT_START' });

    const ws = new WebSocket(`ws://${ip}:8765`);
    wsRef.current = ws;

    ws.onopen = () => {
      dispatch({ type: 'CONNECTED' });
    };

    ws.onclose = () => {
      dispatch({ type: 'DISCONNECTED' });
      wsRef.current = null;
    };

    ws.onerror = () => {
      dispatchError('Connection failed');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        switch (msg.type) {
          case 'state':
            dispatch({
              type: 'STATE_UPDATE',
              cell: msg.cell,
              facing: msg.facing,
              status: msg.status,
              target: msg.target ?? null,
            });
            break;

          case 'grid':
            dispatch({ type: 'GRID_UPDATE', cells: msg.cells });
            break;

          case 'nav_start': {
            // Compute cell sequence from route commands (use ref for fresh state)
            const s = stateRef.current;
            const currentCell = msg.cell ?? s.cell ?? 0;
            const currentFacing = s.facing ?? 'north';
            const routeCells = msg.route
              ? computeRouteCells(currentCell, currentFacing, msg.route, s.grid)
              : [currentCell, msg.target];

            dispatch({
              type: 'NAV_START',
              cell: msg.cell,
              target: msg.target,
              route: routeCells,
            });
            break;
          }

          case 'turn_start':
            dispatch({ type: 'TURN_START', deg: msg.deg });
            break;

          case 'turn_done':
            dispatch({ type: 'TURN_DONE', facing: msg.facing });
            break;

          case 'telemetry':
            dispatch({
              type: 'TELEMETRY',
              payload: {
                speed: msg.speed ?? 0,
                lv: msg.lv ?? 0,
                rv: msg.rv ?? 0,
                d_mm: msg.d_mm ?? 0,
                rem_mm: msg.rem_mm ?? 0,
                line_angle: msg.line_angle ?? null,
                aruco_id: msg.aruco_id ?? null,
              },
            });
            break;

          case 'move_done':
            dispatch({ type: 'MOVE_DONE', cell: msg.cell });
            break;

          case 'nav_done':
            dispatch({ type: 'NAV_DONE', cell: msg.cell, facing: msg.facing });
            break;

          case 'stopped':
            dispatch({ type: 'STOPPED', cell: msg.cell });
            break;

          case 'error':
            dispatchError(msg.message ?? 'Unknown error');
            break;
        }
      } catch {
        dispatchError('Failed to parse server message');
      }
    };
  }, [dispatchError]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
  }, []);

  const goTo = useCallback((cell: number) => {
    wsRef.current?.send(JSON.stringify({ type: 'go_to', cell }));
  }, []);

  const stop = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: 'stop' }));
  }, []);

  const clearLogs = useCallback(() => {
    dispatch({ type: 'CLEAR_LOGS' });
  }, []);

  return { state, connect, disconnect, goTo, stop, clearLogs };
}

export type { RobotState, Facing, Telemetry, ConnectionStatus, LogEntry };
