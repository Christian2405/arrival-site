import { Tabs } from 'expo-router';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: { display: 'none' },
      }}
    >
      <Tabs.Screen name="home" />
      <Tabs.Screen name="history" />
      <Tabs.Screen name="settings" />
      <Tabs.Screen name="codes" options={{ href: null }} />
      <Tabs.Screen name="manuals" options={{ href: null }} />
      <Tabs.Screen name="quick-tools" options={{ href: null }} />
      <Tabs.Screen name="saved-answers" options={{ href: null }} />
    </Tabs>
  );
}
