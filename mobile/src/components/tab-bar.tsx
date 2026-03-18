import { Pressable, Text, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@/context/theme-context';

export type TabId = 'home' | 'logs' | 'settings';

const TABS: { id: TabId; label: string; icon: React.ComponentProps<typeof Feather>['name'] }[] = [
  { id: 'home', label: 'HOME', icon: 'home' },
  { id: 'logs', label: 'LOGS', icon: 'terminal' },
  { id: 'settings', label: 'SETTINGS', icon: 'settings' },
];

interface TabBarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export function TabBar({ activeTab, onTabChange }: TabBarProps) {
  const { colors } = useTheme();

  return (
    <View className="mx-6 mb-4 flex-row p-1 relative">
      {/* HUD corners */}
      <View className="absolute w-2.5 h-2.5 top-0 left-0 border-t border-l border-border" />
      <View className="absolute w-2.5 h-2.5 top-0 right-0 border-t border-r border-border" />
      <View className="absolute w-2.5 h-2.5 bottom-0 left-0 border-b border-l border-border" />
      <View className="absolute w-2.5 h-2.5 bottom-0 right-0 border-b border-r border-border" />
      {/* HUD edge lines */}
      <View className="absolute top-0 left-3 right-3 border-t border-border-muted" />
      <View className="absolute bottom-0 left-3 right-3 border-b border-border-muted" />
      <View className="absolute left-0 top-3 bottom-3 border-l border-border-muted" />
      <View className="absolute right-0 top-3 bottom-3 border-r border-border-muted" />

      {TABS.map((tab) => {
        const active = activeTab === tab.id;
        return (
          <Pressable
            key={tab.id}
            onPress={() => onTabChange(tab.id)}
            className="flex-1 items-center justify-center py-2 relative"
          >
            {active && (
              <View className="absolute inset-0 bg-fill" />
            )}
            <Feather
              name={tab.icon}
              size={18}
              color={colors.muted}
              style={{ position: 'relative', zIndex: 1 }}
            />
            <Text
              className={`font-ibm text-[8px] tracking-[1px] mt-0.5 ${
                active ? 'text-foreground' : 'text-subtle'
              }`}
              style={{ position: 'relative', zIndex: 1 }}
            >
              {tab.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}
