import { useCallback, useMemo } from 'react';
import { FlatList, Text, View } from 'react-native';
import { HudBox } from '@/components/hud-box';
import { useRobotContext } from '@/context/robot-context';
import type { LogEntry } from '@/hooks/useRobot';

const TYPE_COLORS: Record<string, string> = {
  connect: '#22c55e',
  error: '#ef4444',
  stop: '#f59e0b',
};

function formatTime(ts: number): string {
  const d = new Date(ts);
  const h = String(d.getHours()).padStart(2, '0');
  const m = String(d.getMinutes()).padStart(2, '0');
  const s = String(d.getSeconds()).padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function LogRow({ item }: { item: LogEntry }) {
  const color = TYPE_COLORS[item.type];
  return (
    <View className="flex-row items-start gap-3 py-1.5 px-1">
      <Text className="font-ibm text-[9px] text-subtle tracking-[0.5px]">
        {formatTime(item.ts)}
      </Text>
      <Text
        className="font-ibm text-[9px] tracking-[1px] uppercase w-14"
        style={color ? { color } : undefined}
        numberOfLines={1}
      >
        {item.type}
      </Text>
      <Text className="font-ibm text-[10px] text-foreground flex-1 flex-shrink" numberOfLines={2}>
        {item.detail}
      </Text>
    </View>
  );
}

export function LogsPage() {
  const { state, clearLogs } = useRobotContext();

  const reversed = useMemo(() => [...state.logs].reverse(), [state.logs]);

  const renderItem = useCallback(({ item }: { item: LogEntry }) => <LogRow item={item} />, []);
  const keyExtractor = useCallback((item: LogEntry) => String(item.id), []);

  return (
    <View className="flex-1 bg-surface">
      {/* Header */}
      <View className="flex-row items-center justify-between px-6 pt-4 pb-2">
        <Text className="font-ibm text-[10px] tracking-[2px] text-subtle uppercase">
          event log
        </Text>
        {state.logs.length > 0 && (
          <HudBox onPress={clearLogs} className="px-3 py-1 items-center justify-center">
            <Text className="font-ibm text-[9px] tracking-[2px] text-subtle uppercase">clear</Text>
          </HudBox>
        )}
      </View>

      {state.logs.length === 0 ? (
        <View className="flex-1 items-center justify-center">
          <Text className="font-ibm text-[11px] text-subtle tracking-[2px] uppercase">
            no events yet
          </Text>
        </View>
      ) : (
        <FlatList
          data={reversed}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerClassName="px-5 pb-4"
        />
      )}
    </View>
  );
}
