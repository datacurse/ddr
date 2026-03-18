import { useState } from 'react';
import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { HomePage } from '@/components/pages/home-page';
import { LogsPage } from '@/components/pages/logs-page';
import { SettingsPage } from '@/components/pages/settings-page';
import { TabBar, type TabId } from '@/components/tab-bar';

export default function RobotScreen() {
  const [activeTab, setActiveTab] = useState<TabId>('home');

  return (
    <SafeAreaView className="flex-1 bg-surface">
      <View className={activeTab === 'home' ? 'flex-1' : 'hidden'}>
        <HomePage />
      </View>
      <View className={activeTab === 'logs' ? 'flex-1' : 'hidden'}>
        <LogsPage />
      </View>
      <View className={activeTab === 'settings' ? 'flex-1' : 'hidden'}>
        <SettingsPage />
      </View>
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
    </SafeAreaView>
  );
}
