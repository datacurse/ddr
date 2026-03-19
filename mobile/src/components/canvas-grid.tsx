import React, { useCallback, useMemo, useState } from 'react';
import { LayoutChangeEvent, Pressable, StyleSheet, Text, View } from 'react-native';
import Animated, { useAnimatedStyle } from 'react-native-reanimated';

import { useTheme } from '@/context/theme-context';
import type { Facing, Telemetry } from '@/hooks/useRobot';
import { useRobotAnimation, cellToPixel } from '@/hooks/useRobotAnimation';

const GAP = 8;
const PADDING = 16;
const CORNER_LEN = 10;

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
    let maxX = 0,
      maxY = 0;
    const parsed = entries.map(([id, [x, y]]) => {
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
      return { id: Number(id), x, y };
    });
    return { cols: maxX + 1, rows: maxY + 1, cells: parsed };
  }, [grid]);

  const cellSize =
    containerWidth > 0 && containerHeight > 0
      ? Math.min(
          (containerWidth - 2 * PADDING - GAP * (cols - 1)) / cols,
          (containerHeight - 2 * PADDING - GAP * (rows - 1)) / rows,
        )
      : 0;
  const gridWidth = cellSize > 0 ? cellSize * cols + GAP * (cols - 1) : 0;
  const gridHeight = cellSize > 0 ? cellSize * rows + GAP * (rows - 1) : 0;

  // ── Animation ─────────────────────────────────────────────────

  const anim = useRobotAnimation({
    grid,
    cell: robotCell,
    prevCell,
    facing,
    status,
    telemetry,
    turnDeg,
    route,
    rows,
    cellSize,
    gap: GAP,
  });

  const arrowSize = cellSize * 0.3;
  const robotViewSize = arrowSize * 2.5;

  const robotAnimatedStyle = useAnimatedStyle(() => {
    if (!anim.initialized.value) return { opacity: 0 };
    return {
      opacity: 1,
      transform: [
        { translateX: anim.x.value - robotViewSize / 2 },
        { translateY: anim.y.value - robotViewSize / 2 },
        { rotate: `${anim.angle.value}rad` },
      ],
    };
  });

  // ── Route line segments ───────────────────────────────────────

  const routeSegments = useMemo(() => {
    if (route.length < 2 || cellSize === 0) return [];
    const segs: Array<{ left: number; top: number; width: number; height: number }> = [];
    for (let i = 0; i < route.length - 1; i++) {
      const a = cellToPixel(route[i], grid, rows, cellSize, GAP);
      const b = cellToPixel(route[i + 1], grid, rows, cellSize, GAP);
      if (!a || !b) continue;
      if (Math.abs(a.y - b.y) < 1) {
        segs.push({
          left: Math.min(a.x, b.x),
          top: a.y - 1.5,
          width: Math.abs(b.x - a.x),
          height: 3,
        });
      } else {
        segs.push({
          left: a.x - 1.5,
          top: Math.min(a.y, b.y),
          width: 3,
          height: Math.abs(b.y - a.y),
        });
      }
    }
    return segs;
  }, [route, grid, rows, cellSize]);

  const routeSet = useMemo(() => new Set(route), [route]);

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
    <View
      onLayout={onLayout}
      style={{ flex: 1, width: '100%', justifyContent: 'center', alignItems: 'center' }}
    >
      <View style={{ width: gridWidth, height: gridHeight, position: 'relative' }}>
        {/* Route line segments */}
        {routeSegments.map((seg, i) => (
          <View
            key={`r${i}`}
            pointerEvents="none"
            style={{
              position: 'absolute',
              backgroundColor: c.routeLine,
              left: seg.left,
              top: seg.top,
              width: seg.width,
              height: seg.height,
            }}
          />
        ))}

        {/* Grid cells */}
        {cells.map((cell) => {
          const invertedY = rows - 1 - cell.y;
          const px = cell.x * (cellSize + GAP);
          const py = invertedY * (cellSize + GAP);
          const isTarget = cell.id === target;
          const isRobot = cell.id === robotCell;
          const isOnRoute = routeSet.has(cell.id) && !isRobot && !isTarget;

          return (
            <Pressable
              key={cell.id}
              android_ripple={null}
              disabled={disabled || isRobot}
              onPress={() => onCellPress(cell.id)}
              style={{
                position: 'absolute',
                left: px,
                top: py,
                width: cellSize,
                height: cellSize,
              }}
            >
              {/* Background highlight */}
              {(isTarget || isOnRoute) && (
                <View
                  style={[
                    StyleSheet.absoluteFill,
                    { backgroundColor: isTarget ? c.targetFill : c.overlaySubtle },
                  ]}
                />
              )}

              {/* HUD corner brackets */}
              <View style={[styles.corner, styles.tl, { borderColor: c.border }]} />
              <View style={[styles.corner, styles.tr, { borderColor: c.border }]} />
              <View style={[styles.corner, styles.bl, { borderColor: c.border }]} />
              <View style={[styles.corner, styles.br, { borderColor: c.border }]} />

              {/* HUD edge lines */}
              <View
                style={{
                  position: 'absolute',
                  top: 0,
                  left: CORNER_LEN,
                  right: CORNER_LEN,
                  height: 1,
                  backgroundColor: c.borderMuted,
                }}
              />
              <View
                style={{
                  position: 'absolute',
                  bottom: 0,
                  left: CORNER_LEN,
                  right: CORNER_LEN,
                  height: 1,
                  backgroundColor: c.borderMuted,
                }}
              />
              <View
                style={{
                  position: 'absolute',
                  left: 0,
                  top: CORNER_LEN,
                  bottom: CORNER_LEN,
                  width: 1,
                  backgroundColor: c.borderMuted,
                }}
              />
              <View
                style={{
                  position: 'absolute',
                  right: 0,
                  top: CORNER_LEN,
                  bottom: CORNER_LEN,
                  width: 1,
                  backgroundColor: c.borderMuted,
                }}
              />

              {/* Cell ID */}
              {isRobot ? (
                <Text
                  style={{
                    position: 'absolute',
                    top: 4,
                    right: 4,
                    fontFamily: 'IBMPlexMono_400Regular',
                    fontSize: 8,
                    color: c.subtle,
                  }}
                >
                  {cell.id}
                </Text>
              ) : (
                <View
                  style={[
                    StyleSheet.absoluteFill,
                    { justifyContent: 'center', alignItems: 'center' },
                  ]}
                >
                  <Text
                    style={{
                      fontFamily: 'IBMPlexMono_400Regular',
                      fontSize: 14,
                      color: isTarget ? c.foreground : c.subtle,
                    }}
                  >
                    {cell.id}
                  </Text>
                </View>
              )}
            </Pressable>
          );
        })}

        {/* Robot arrow */}
        {robotCell !== null && (
          <Animated.View
            pointerEvents="none"
            style={[
              {
                position: 'absolute',
                left: 0,
                top: 0,
                width: robotViewSize,
                height: robotViewSize,
                justifyContent: 'center',
                alignItems: 'center',
              },
              robotAnimatedStyle,
            ]}
          >
            <View
              style={{
                width: 0,
                height: 0,
                marginTop: -arrowSize * 0.25,
                borderLeftWidth: arrowSize * 0.7,
                borderRightWidth: arrowSize * 0.7,
                borderBottomWidth: arrowSize * 1.5,
                borderLeftColor: 'transparent',
                borderRightColor: 'transparent',
                borderBottomColor: c.foreground,
              }}
            />
          </Animated.View>
        )}
      </View>
    </View>
  );
});

// ── Static styles ───────────────────────────────────────────────

const styles = StyleSheet.create({
  corner: {
    position: 'absolute',
    width: CORNER_LEN,
    height: CORNER_LEN,
  },
  tl: {
    top: 0,
    left: 0,
    borderTopWidth: 1,
    borderLeftWidth: 1,
  },
  tr: {
    top: 0,
    right: 0,
    borderTopWidth: 1,
    borderRightWidth: 1,
  },
  bl: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 1,
    borderLeftWidth: 1,
  },
  br: {
    bottom: 0,
    right: 0,
    borderBottomWidth: 1,
    borderRightWidth: 1,
  },
});
