import { useEffect, useRef } from 'react';
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

// ── Animation state ───────────────────────────────────────────────

export interface AnimState {
  x: number;
  y: number;
  angle: number;
  targetX: number;
  targetY: number;
  targetAngle: number;
  initialized: boolean;
}

const INITIAL_ANIM: AnimState = {
  x: 0, y: 0, angle: 0,
  targetX: 0, targetY: 0, targetAngle: 0,
  initialized: false,
};

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
}: UseRobotAnimationParams) {
  const animRef = useRef<AnimState>({ ...INITIAL_ANIM });
  const lastFacing = useRef<Facing | null>(null);
  const turnAnimating = useRef(false);

  // -- Position: always target current cell (telemetry effect overrides during movement) --
  useEffect(() => {
    if (cell === null || cellSize === 0) return;

    const pos = cellToPixel(cell, grid, rows, cellSize, gap);
    if (!pos) return;

    const a = animRef.current;
    if (!a.initialized) {
      // First time: snap
      a.x = a.targetX = pos.x;
      a.y = a.targetY = pos.y;
      a.initialized = true;
    } else {
      a.targetX = pos.x;
      a.targetY = pos.y;
    }
  }, [cell, cellSize, gap, rows, grid]);

  // -- Position: interpolate during movement via telemetry --
  useEffect(() => {
    if (!telemetry || prevCell === null || cell === null || cellSize === 0) return;
    if (status !== 'navigating' && status !== 'moving') return;

    let toId: number;
    if (prevCell !== cell) {
      // After MOVE_DONE: prevCell is departure, cell is arrival
      toId = cell;
    } else {
      // Mid-move (before MOVE_DONE): prevCell === cell === departure
      // Look up destination from route
      const idx = route.indexOf(prevCell);
      toId = idx >= 0 && idx + 1 < route.length ? route[idx + 1] : cell;
    }

    const fromPos = cellToPixel(prevCell, grid, rows, cellSize, gap);
    const toPos = cellToPixel(toId, grid, rows, cellSize, gap);
    if (!fromPos || !toPos) return;

    const total = telemetry.d_mm + telemetry.rem_mm;
    const progress = total > 0 ? telemetry.d_mm / total : 0;

    animRef.current.targetX = fromPos.x + (toPos.x - fromPos.x) * progress;
    animRef.current.targetY = fromPos.y + (toPos.y - fromPos.y) * progress;
  }, [telemetry, prevCell, cell, route, cellSize, gap, rows, grid, status]);

  // -- Rotation: animate on turn_start --
  useEffect(() => {
    if (turnDeg !== null) {
      const deltaRad = (turnDeg * Math.PI) / 180;
      animRef.current.targetAngle = animRef.current.angle + deltaRad;
      turnAnimating.current = true;
    }
  }, [turnDeg]);

  // -- Rotation: snap on facing change --
  useEffect(() => {
    if (!facing) return;
    if (lastFacing.current === facing) return;

    const target = FACING_ANGLE[facing];
    const a = animRef.current;

    if (!a.initialized || lastFacing.current === null) {
      // First time: snap
      a.angle = a.targetAngle = target;
    } else if (turnAnimating.current) {
      // Turn animation was running → snap to exact facing
      const delta = shortestAngleDelta(a.angle, target);
      a.angle = a.angle + delta;
      a.targetAngle = a.angle;
      turnAnimating.current = false;
    } else {
      // State sync without a turn animation → set target (lerp will handle)
      const delta = shortestAngleDelta(a.angle, target);
      a.targetAngle = a.angle + delta;
    }

    lastFacing.current = facing;
  }, [facing]);

  // -- Reset when disconnected --
  useEffect(() => {
    if (cell === null) {
      animRef.current = { ...INITIAL_ANIM };
      lastFacing.current = null;
      turnAnimating.current = false;
    }
  }, [cell]);

  return animRef;
}

/** Advance animation state one tick (call from rAF loop). Returns true if still moving. */
export function stepAnimation(anim: AnimState, lerpFactor = 0.15): boolean {
  const dx = anim.targetX - anim.x;
  const dy = anim.targetY - anim.y;
  const da = shortestAngleDelta(anim.angle, anim.targetAngle);

  anim.x += dx * lerpFactor;
  anim.y += dy * lerpFactor;
  anim.angle += da * lerpFactor;

  // Return true if still animating (not settled)
  return Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5 || Math.abs(da) > 0.005;
}
