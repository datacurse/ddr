import { useEffect, useRef } from 'react';
import {
  useSharedValue,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import type { Facing, Telemetry } from './useRobot';

// ── Constants ─────────────────────────────────────────────────────

const FACING_ANGLE: Record<Facing, number> = {
  north: 0,
  east: Math.PI / 2,
  south: Math.PI,
  west: (3 * Math.PI) / 2,
};

// ── Helpers ───────────────────────────────────────────────────────

/** Convert a cell ID to pixel center coordinates on the canvas. */
export function cellToPixel(
  cellId: number,
  grid: Record<string, [number, number]>,
  rows: number,
  cellSize: number,
  gap: number,
): { x: number; y: number } | null {
  const pos = grid[String(cellId)];
  if (!pos) return null;
  const [gx, gy] = pos;
  const invertedY = rows - 1 - gy;
  return {
    x: gx * (cellSize + gap) + cellSize / 2,
    y: invertedY * (cellSize + gap) + cellSize / 2,
  };
}

/** Shortest signed angular delta from `from` to `to`. */
function shortestAngleDelta(from: number, to: number): number {
  const TWO_PI = 2 * Math.PI;
  let delta = ((to - from) % TWO_PI + TWO_PI) % TWO_PI;
  if (delta > Math.PI) delta -= TWO_PI;
  return delta;
}

// ── Hook ──────────────────────────────────────────────────────────

interface UseRobotAnimationParams {
  grid: Record<string, [number, number]>;
  cell: number | null;
  prevCell: number | null;
  facing: Facing | null;
  status: string;
  telemetry: Telemetry | null;
  turnDeg: number | null;
  route: number[];
  rows: number;
  cellSize: number;
  gap: number;
}

export interface RobotAnimationValues {
  x: SharedValue<number>;
  y: SharedValue<number>;
  angle: SharedValue<number>;
  initialized: SharedValue<boolean>;
}

export function useRobotAnimation({
  grid,
  cell,
  prevCell,
  facing,
  status,
  telemetry,
  turnDeg,
  route,
  rows,
  cellSize,
  gap,
}: UseRobotAnimationParams): RobotAnimationValues {
  const x = useSharedValue(0);
  const y = useSharedValue(0);
  const angle = useSharedValue(0);
  const initialized = useSharedValue(false);

  const lastFacing = useRef<Facing | null>(null);
  const turnAnimating = useRef(false);

  // -- Position: target current cell --
  useEffect(() => {
    if (cell === null || cellSize === 0) return;
    const pos = cellToPixel(cell, grid, rows, cellSize, gap);
    if (!pos) return;

    if (!initialized.value) {
      x.value = pos.x;
      y.value = pos.y;
      initialized.value = true;
    } else {
      x.value = withTiming(pos.x, { duration: 150 });
      y.value = withTiming(pos.y, { duration: 150 });
    }
  }, [cell, cellSize, gap, rows, grid]);

  // -- Position: interpolate during movement via telemetry --
  useEffect(() => {
    if (!telemetry || prevCell === null || cell === null || cellSize === 0) return;
    if (status !== 'navigating' && status !== 'moving') return;

    let toId: number;
    if (prevCell !== cell) {
      toId = cell;
    } else {
      const idx = route.indexOf(prevCell);
      toId = idx >= 0 && idx + 1 < route.length ? route[idx + 1] : cell;
    }

    const fromPos = cellToPixel(prevCell, grid, rows, cellSize, gap);
    const toPos = cellToPixel(toId, grid, rows, cellSize, gap);
    if (!fromPos || !toPos) return;

    const total = telemetry.d_mm + telemetry.rem_mm;
    const progress = total > 0 ? telemetry.d_mm / total : 0;

    x.value = withTiming(
      fromPos.x + (toPos.x - fromPos.x) * progress,
      { duration: 100 },
    );
    y.value = withTiming(
      fromPos.y + (toPos.y - fromPos.y) * progress,
      { duration: 100 },
    );
  }, [telemetry, prevCell, cell, route, cellSize, gap, rows, grid, status]);

  // -- Rotation: animate on turn_start --
  useEffect(() => {
    if (turnDeg !== null) {
      const deltaRad = (turnDeg * Math.PI) / 180;
      angle.value = withTiming(angle.value + deltaRad, { duration: 400 });
      turnAnimating.current = true;
    }
  }, [turnDeg]);

  // -- Rotation: snap/smooth on facing change --
  useEffect(() => {
    if (!facing) return;
    if (lastFacing.current === facing) return;

    const target = FACING_ANGLE[facing];

    if (lastFacing.current === null) {
      // First time: snap
      angle.value = target;
    } else if (turnAnimating.current) {
      // Turn animation was running -> snap to exact facing (handle wraparound)
      const current = angle.value;
      const normalized =
        target + Math.round((current - target) / (2 * Math.PI)) * (2 * Math.PI);
      angle.value = normalized;
      turnAnimating.current = false;
    } else {
      // State sync -> smooth transition via shortest path
      const delta = shortestAngleDelta(angle.value, target);
      angle.value = withTiming(angle.value + delta, { duration: 300 });
    }

    lastFacing.current = facing;
  }, [facing]);

  // -- Reset when disconnected --
  useEffect(() => {
    if (cell === null) {
      x.value = 0;
      y.value = 0;
      angle.value = 0;
      initialized.value = false;
      lastFacing.current = null;
      turnAnimating.current = false;
    }
  }, [cell]);

  return { x, y, angle, initialized };
}
