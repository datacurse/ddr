import { HudBox } from '@/components/hud-box';
import { CanvasGrid } from '@/components/canvas-grid';
import { useRobotContext } from '@/context/robot-context';
import AsyncStorage from '@react-native-async-storage/async-storage';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Text, TextInput, View } from 'react-native';

const IP_STORAGE_KEY = 'robot-ip';

export function HomePage() {
  const { state, connect, disconnect, goTo, stop } = useRobotContext();

  const [ip, setIp] = useState('192.168.3.154');

  useEffect(() => {
    AsyncStorage.getItem(IP_STORAGE_KEY).then((v) => {
      if (v) setIp(v);
    });
  }, []);

  useEffect(() => {
    if (ip) AsyncStorage.setItem(IP_STORAGE_KEY, ip);
  }, [ip]);

  const handleConnect = useCallback(() => {
    if (state.connection === 'disconnected') {
      connect(ip);
    } else {
      disconnect();
    }
  }, [state.connection, ip, connect, disconnect]);

  const isIdle = state.status === 'idle' && state.connection === 'connected';

  return (
    <View className="flex-1 bg-surface">
      {/* Nav bar */}
      <View className="items-center px-6 pt-1">
        <Text className="font-ibm text-[9px] tracking-[3px] text-subtle uppercase">robot</Text>
        <Text className="font-ibm text-[9px] tracking-[3px] text-subtle uppercase">control</Text>
      </View>

      {/* Connection bar */}
      <ConnectionBar
        ip={ip}
        onIpChange={setIp}
        connection={state.connection}
        onToggle={handleConnect}
      />

      {/* Grid */}
      <View className="flex-1 px-6">
        <CanvasGrid
          grid={state.grid}
          robotCell={state.cell}
          prevCell={state.prevCell}
          facing={state.facing}
          target={state.target}
          route={state.route}
          status={state.status}
          telemetry={state.telemetry}
          turnDeg={state.turnDeg}
          disabled={!isIdle}
          onCellPress={goTo}
        />
      </View>

      {/* Status panel */}
      <StatusPanel
        status={state.status}
        target={state.target}
        telemetry={state.telemetry}
        error={state.error}
        connected={state.connection === 'connected'}
        onStop={stop}
      />
    </View>
  );
}

// ── Connection Bar ─────────────────────────────────────────────────

function ConnectionBar({
  ip,
  onIpChange,
  connection,
  onToggle,
}: {
  ip: string;
  onIpChange: (v: string) => void;
  connection: string;
  onToggle: () => void;
}) {
  const dotColor =
    connection === 'connected' ? '#22c55e' :
    connection === 'connecting' ? '#f59e0b' :
    '#ef4444';

  return (
    <View className="flex-row items-center gap-3 px-6 mt-4">
      <View className="flex-1">
        <TextInput
          className="font-ibm text-[12px] text-foreground bg-overlay px-3 py-2 rounded border border-border-muted"
          placeholder="192.168.x.x"
          placeholderTextColor="rgba(128,128,128,0.5)"
          value={ip}
          onChangeText={onIpChange}
          keyboardType="numeric"
          autoCapitalize="none"
          autoCorrect={false}
        />
      </View>
      <HudBox onPress={onToggle} className="px-4 py-2 items-center justify-center">
        <Text className="font-ibm text-[10px] tracking-[2px] text-foreground uppercase">
          {connection === 'disconnected' ? 'conn' : 'disc'}
        </Text>
      </HudBox>
      <View
        style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: dotColor }}
      />
    </View>
  );
}

// ── Status Panel ───────────────────────────────────────────────────

function StatusPanel({
  status,
  target,
  telemetry,
  error,
  connected,
  onStop,
}: {
  status: string;
  target: number | null;
  telemetry: ReturnType<typeof useRobotContext>['state']['telemetry'];
  error: string | null;
  connected: boolean;
  onStop: () => void;
}) {
  const statusText = useMemo(() => {
    if (!connected) return 'DISCONNECTED';
    if (status === 'navigating' && target !== null) return `NAVIGATING TO ${target}`;
    if (status === 'turning') return 'TURNING';
    if (status === 'moving') return 'MOVING';
    return status.toUpperCase();
  }, [connected, status, target]);

  const totalDist = telemetry ? telemetry.d_mm + telemetry.rem_mm : 0;
  const progress = totalDist > 0 ? telemetry!.d_mm / totalDist : 0;

  return (
    <View className="px-6 pb-2 gap-3">
      <View className="flex-row items-center justify-between">
        <Text className={`font-ibm text-[10px] tracking-[2px] uppercase ${
          status === 'idle' ? 'text-subtle' : 'text-foreground'
        }`}>
          {statusText}
        </Text>
        {telemetry && (
          <Text className="font-ibm text-[10px] text-subtle tracking-[1px]">
            {telemetry.speed.toFixed(2)} m/s
          </Text>
        )}
      </View>

      {telemetry && totalDist > 0 && (
        <View>
          <View className="flex-row justify-between mb-1">
            <Text className="font-ibm text-[9px] text-subtle tracking-[1px]">
              DIST: {telemetry.d_mm}/{totalDist}mm
            </Text>
          </View>
          <View className="h-1 bg-overlay rounded-full overflow-hidden">
            <View
              className="h-full bg-muted rounded-full"
              style={{ width: `${Math.min(progress * 100, 100)}%` }}
            />
          </View>
        </View>
      )}

      {error && (
        <Text className="font-ibm text-[10px] tracking-[1px]" style={{ color: '#ef4444' }}>
          {error}
        </Text>
      )}

      {connected && (
        <HudBox
          onPress={onStop}
          className="py-4 items-center justify-center"
        >
          <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: 2 }} />
          <Text
            className="font-ibm-medium text-[14px] tracking-[3px]"
            style={{ color: '#ef4444' }}
          >
            STOP
          </Text>
        </HudBox>
      )}
    </View>
  );
}
