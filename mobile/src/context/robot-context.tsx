import { createContext, useContext } from 'react';
import { useRobot } from '@/hooks/useRobot';

type RobotContextValue = ReturnType<typeof useRobot>;

const RobotContext = createContext<RobotContextValue | null>(null);

export function RobotProvider({ children }: { children: React.ReactNode }) {
  const robot = useRobot();
  return <RobotContext.Provider value={robot}>{children}</RobotContext.Provider>;
}

export function useRobotContext() {
  const ctx = useContext(RobotContext);
  if (!ctx) throw new Error('useRobotContext must be used within RobotProvider');
  return ctx;
}
