import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { LayoutChangeEvent, PixelRatio, Pressable, StyleSheet, Text, View } from 'react-native';
import { GLView, ExpoWebGLRenderingContext } from 'expo-gl';
import Expo2DContext from 'expo-2d-context';

import { useTheme } from '@/context/theme-context';
import type { Facing, Telemetry } from '@/hooks/useRobot';
import {
  useRobotAnimation,
  stepAnimation,
  cellToPixel,
  type AnimState,
} from '@/hooks/useRobotAnimation';

const GAP = 8;
const CORNER_LEN = 10;
const LERP_FACTOR = 0.15;

interface CanvasGridProps {
  grid: Record<string, [number, number]>;
  robotCell: number | null;
  prevCell: number | null;
  facing: Facing | null;
  target: number | null;
  route: number[];
  status: string;
  telemetry: Telemetry | null;
  turnDeg: number | null;
  disabled: boolean;
  onCellPress: (cell: number) => void;
}

export const CanvasGrid = React.memo(function CanvasGrid({
  grid,
  robotCell,
  prevCell,
  facing,
  target,
  route,
  status,
  telemetry,
  turnDeg,
  disabled,
  onCellPress,
}: CanvasGridProps) {
  const { colors } = useTheme();
  const c = colors.canvas;

  const [containerWidth, setContainerWidth] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);

  const onLayout = useCallback((e: LayoutChangeEvent) => {
    setContainerWidth(e.nativeEvent.layout.width);
    setContainerHeight(e.nativeEvent.layout.height);
  }, []);

  // ── Grid geometry ─────────────────────────────────────────────

  const { cols, rows, cells } = useMemo(() => {
    const entries = Object.entries(grid);
    if (entries.length === 0) {
      return { cols: 2, rows: 4, cells: [] as Array<{ id: number; x: number; y: number }> };
    }
    let maxX = 0, maxY = 0;
    const parsed = entries.map(([id, [x, y]]) => {
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
      return { id: Number(id), x, y };
    });
    return { cols: maxX + 1, rows: maxY + 1, cells: parsed };
  }, [grid]);

  const cellSize = containerWidth > 0 && containerHeight > 0
    ? Math.min(
        (containerWidth - GAP * (cols - 1)) / cols,
        (containerHeight - GAP * (rows - 1)) / rows,
      )
    : 0;
  const canvasWidth = cellSize > 0 ? cellSize * cols + GAP * (cols - 1) : 0;
  const canvasHeight = cellSize > 0 ? cellSize * rows + GAP * (rows - 1) : 0;

  // ── Animation ─────────────────────────────────────────────────

  const animRef = useRobotAnimation({
    grid, cell: robotCell, prevCell, facing, status, telemetry, turnDeg, route,
    rows, cellSize, gap: GAP,
  });

  // ── Drawing refs ──────────────────────────────────────────────

  const ctxRef = useRef<Expo2DContext | null>(null);
  const rafRef = useRef<number | null>(null);
  const mountedRef = useRef(true);

  // Store latest props in refs so the render loop can read them without re-creating
  const propsRef = useRef({
    cells, cols, rows, cellSize, canvasWidth, canvasHeight,
    routeSet: new Set(route), route,
    robotCell, target, c, grid,
  });
  propsRef.current = {
    cells, cols, rows, cellSize, canvasWidth, canvasHeight,
    routeSet: new Set(route), route,
    robotCell, target, c, grid,
  };

  // ── Render loop ───────────────────────────────────────────────

  const draw = useCallback(() => {
    if (!mountedRef.current) return;
    const ctx = ctxRef.current;
    if (!ctx) return;

    const p = propsRef.current;
    if (p.cellSize === 0) {
      rafRef.current = requestAnimationFrame(draw);
      return;
    }

    // Step animation
    const anim = animRef.current;
    stepAnimation(anim, LERP_FACTOR);

    // Scale for device pixel ratio (GL buffer is in physical pixels)
    const dpr = PixelRatio.get();
    ctx.save();
    ctx.scale(dpr, dpr);

    // Clear
    ctx.clearRect(0, 0, p.canvasWidth, p.canvasHeight);

    // ── Route lines ───────────────────────────────────────────
    if (p.route.length >= 2) {
      ctx.strokeStyle = p.c.routeLine;
      ctx.lineWidth = 3;
      ctx.beginPath();
      for (let i = 0; i < p.route.length - 1; i++) {
        const a = cellToPixel(p.route[i], p.grid, p.rows, p.cellSize, GAP);
        const b = cellToPixel(p.route[i + 1], p.grid, p.rows, p.cellSize, GAP);
        if (!a || !b) continue;
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
      }
      ctx.stroke();
    }

    // ── Cells ─────────────────────────────────────────────────
    for (const cell of p.cells) {
      const invertedY = p.rows - 1 - cell.y;
      const px = cell.x * (p.cellSize + GAP);
      const py = invertedY * (p.cellSize + GAP);
      const s = p.cellSize;
      const isTarget = cell.id === p.target;
      const isRobot = cell.id === p.robotCell;
      const isOnRoute = p.routeSet.has(cell.id) && !isRobot && !isTarget;

      // Background fill
      if (isTarget || isOnRoute) {
        ctx.fillStyle = isTarget ? p.c.targetFill : p.c.overlaySubtle;
        ctx.fillRect(px, py, s, s);
      }

      // HUD corners (L-brackets)
      ctx.strokeStyle = p.c.border;
      ctx.lineWidth = 1;

      // Top-left
      ctx.beginPath();
      ctx.moveTo(px + CORNER_LEN, py);
      ctx.lineTo(px, py);
      ctx.lineTo(px, py + CORNER_LEN);
      ctx.stroke();

      // Top-right
      ctx.beginPath();
      ctx.moveTo(px + s - CORNER_LEN, py);
      ctx.lineTo(px + s, py);
      ctx.lineTo(px + s, py + CORNER_LEN);
      ctx.stroke();

      // Bottom-left
      ctx.beginPath();
      ctx.moveTo(px + CORNER_LEN, py + s);
      ctx.lineTo(px, py + s);
      ctx.lineTo(px, py + s - CORNER_LEN);
      ctx.stroke();

      // Bottom-right
      ctx.beginPath();
      ctx.moveTo(px + s - CORNER_LEN, py + s);
      ctx.lineTo(px + s, py + s);
      ctx.lineTo(px + s, py + s - CORNER_LEN);
      ctx.stroke();

      // HUD edge lines (between corners)
      ctx.strokeStyle = p.c.borderMuted;
      ctx.beginPath();
      // Top
      ctx.moveTo(px + CORNER_LEN, py);
      ctx.lineTo(px + s - CORNER_LEN, py);
      // Bottom
      ctx.moveTo(px + CORNER_LEN, py + s);
      ctx.lineTo(px + s - CORNER_LEN, py + s);
      // Left
      ctx.moveTo(px, py + CORNER_LEN);
      ctx.lineTo(px, py + s - CORNER_LEN);
      // Right
      ctx.moveTo(px + s, py + CORNER_LEN);
      ctx.lineTo(px + s, py + s - CORNER_LEN);
      ctx.stroke();

      // Cell ID label (non-robot cells)
      if (!isRobot) {
        ctx.fillStyle = isTarget ? p.c.foreground : p.c.subtle;
        ctx.font = '14px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(cell.id), px + s / 2, py + s / 2, s);
      }
    }

    // ── Robot arrow ───────────────────────────────────────────
    if (p.robotCell !== null && anim.initialized) {
      const arrowSize = p.cellSize * 0.3;

      ctx.save();
      ctx.translate(anim.x, anim.y);
      ctx.rotate(anim.angle);

      // Triangle pointing up (north = 0)
      ctx.fillStyle = p.c.foreground;
      ctx.beginPath();
      ctx.moveTo(0, -arrowSize);
      ctx.lineTo(arrowSize * 0.7, arrowSize * 0.5);
      ctx.lineTo(-arrowSize * 0.7, arrowSize * 0.5);
      ctx.closePath();
      ctx.fill();

      ctx.restore();

      // Small cell ID near robot (not rotated)
      ctx.fillStyle = p.c.subtle;
      ctx.font = '8px monospace';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'top';
      // Find robot cell pixel position for label placement
      const rPos = cellToPixel(p.robotCell, p.grid, p.rows, p.cellSize, GAP);
      if (rPos) {
        const halfCell = p.cellSize / 2;
        ctx.fillText(String(p.robotCell), rPos.x + halfCell - 4, rPos.y - halfCell + 4, halfCell);
      }
    }

    ctx.restore();
    ctx.flush();
    rafRef.current = requestAnimationFrame(draw);
  }, []);

  // ── GL context setup ──────────────────────────────────────────

  const onContextCreate = useCallback(async (gl: ExpoWebGLRenderingContext) => {
    // expo-2d-context types say `number` but it takes the GL context object
    const ctx = new Expo2DContext(gl as unknown as number, {} as any);
    // Must load font assets before any fillText/strokeText calls
    await ctx.initializeText();
    ctxRef.current = ctx;
    // Kick off the render loop
    rafRef.current = requestAnimationFrame(draw);
  }, [draw]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  // ── Touch handling ────────────────────────────────────────────

  const handlePress = useCallback(
    (evt: { nativeEvent: { locationX: number; locationY: number } }) => {
      if (disabled) return;
      const { locationX, locationY } = evt.nativeEvent;
      const p = propsRef.current;
      for (const cell of p.cells) {
        const invertedY = p.rows - 1 - cell.y;
        const px = cell.x * (p.cellSize + GAP);
        const py = invertedY * (p.cellSize + GAP);
        if (
          locationX >= px && locationX <= px + p.cellSize &&
          locationY >= py && locationY <= py + p.cellSize &&
          cell.id !== p.robotCell
        ) {
          onCellPress(cell.id);
          return;
        }
      }
    },
    [disabled, onCellPress],
  );

  // ── Render ────────────────────────────────────────────────────

  if (cells.length === 0) {
    return (
      <View onLayout={onLayout} className="flex-1 items-center justify-center py-12">
        <Text className="font-ibm text-[11px] text-subtle tracking-[2px] uppercase">
          connect to see grid
        </Text>
      </View>
    );
  }

  if (cellSize === 0) {
    return <View onLayout={onLayout} style={{ flex: 1, width: '100%' }} />;
  }

  return (
    <View onLayout={onLayout} style={{ flex: 1, width: '100%', justifyContent: 'center', alignItems: 'center' }}>
      <View style={{ width: canvasWidth, height: canvasHeight, position: 'relative' }}>
        <GLView
          style={{ width: canvasWidth, height: canvasHeight }}
          onContextCreate={onContextCreate}
        />
        <Pressable
          style={[StyleSheet.absoluteFill, { width: canvasWidth, height: canvasHeight }]}
          onPress={handlePress}
        />
      </View>
    </View>
  );
});
