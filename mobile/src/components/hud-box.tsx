import { View, Pressable } from 'react-native';

interface HudBoxProps {
  children: React.ReactNode;
  className?: string;
  onPress?: () => void;
}

function Corner({ position }: { position: 'tl' | 'tr' | 'bl' | 'br' }) {
  const base = 'absolute w-2.5 h-2.5';
  const map = {
    tl: `${base} top-0 left-0 border-t border-l border-border`,
    tr: `${base} top-0 right-0 border-t border-r border-border`,
    bl: `${base} bottom-0 left-0 border-b border-l border-border`,
    br: `${base} bottom-0 right-0 border-b border-r border-border`,
  };
  return <View className={map[position]} />;
}

export function HudBox({ children, className, onPress }: HudBoxProps) {
  const Wrapper = onPress ? Pressable : View;

  return (
    <Wrapper
      onPress={onPress}
      className={`relative ${className ?? ''}`}
    >
      <Corner position="tl" />
      <Corner position="tr" />
      <Corner position="bl" />
      <Corner position="br" />
      {/* Edge lines */}
      <View className="absolute top-0 left-3 right-3 border-t border-border-muted" />
      <View className="absolute bottom-0 left-3 right-3 border-b border-border-muted" />
      <View className="absolute left-0 top-3 bottom-3 border-l border-border-muted" />
      <View className="absolute right-0 top-3 bottom-3 border-r border-border-muted" />
      {children}
    </Wrapper>
  );
}
