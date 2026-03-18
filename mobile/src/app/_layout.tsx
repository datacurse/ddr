import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import {
  useFonts,
  IBMPlexMono_300Light,
  IBMPlexMono_400Regular,
  IBMPlexMono_500Medium,
} from '@expo-google-fonts/ibm-plex-mono';
import { useEffect } from 'react';
import { ThemeProvider, useTheme } from '@/context/theme-context';
import { RobotProvider } from '@/context/robot-context';

import '@/global.css';

SplashScreen.preventAutoHideAsync();

function InnerLayout() {
  const { resolved } = useTheme();

  return (
    <>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
      </Stack>
      <StatusBar style={resolved === 'dark' ? 'light' : 'dark'} />
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    IBMPlexMono_300Light,
    IBMPlexMono_400Regular,
    IBMPlexMono_500Medium,
  });

  useEffect(() => {
    if (fontsLoaded) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ThemeProvider>
        <RobotProvider>
          <InnerLayout />
        </RobotProvider>
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}
