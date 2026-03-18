import { Text, View, ScrollView } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@/context/theme-context';
import { HudBox } from '@/components/hud-box';
import type { ThemePreference } from '@/lib/theme';

const options: { value: ThemePreference; label: string; icon: 'smartphone' | 'sun' | 'moon' }[] = [
  { value: 'system', label: 'SYSTEM', icon: 'smartphone' },
  { value: 'light', label: 'LIGHT', icon: 'sun' },
  { value: 'dark', label: 'DARK', icon: 'moon' },
];

export function SettingsPage() {
  const { preference, setPreference, colors } = useTheme();

  return (
    <ScrollView className="flex-1 bg-surface px-6 pt-4">
      <Text className="font-ibm text-[10px] tracking-[2px] text-subtle uppercase mb-4">
        appearance
      </Text>
      <View className="gap-3">
        {options.map((opt) => (
          <HudBox
            key={opt.value}
            onPress={() => setPreference(opt.value)}
            className={`flex-row items-center gap-3 py-3 px-4 ${
              preference === opt.value ? 'bg-fill' : ''
            }`}
          >
            <Feather name={opt.icon} size={14} color={colors.muted} />
            <Text className={`font-ibm text-[11px] tracking-[2px] ${
              preference === opt.value ? 'text-foreground' : 'text-muted'
            }`}>
              {opt.label}
            </Text>
            {preference === opt.value && (
              <View className="ml-auto">
                <Feather name="check" size={14} color={colors.muted} />
              </View>
            )}
          </HudBox>
        ))}
      </View>
    </ScrollView>
  );
}
