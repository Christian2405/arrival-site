import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants/Colors';

interface ModeSelectorProps {
  currentMode: 'default' | 'text' | 'job';
  onModeChange: (mode: 'default' | 'text' | 'job') => void;
  jobModeAllowed: boolean;
  voiceAllowed: boolean;
}

const modes = [
  { key: 'default' as const, label: 'Voice', icon: 'mic' as const },
  { key: 'text' as const, label: 'Text', icon: 'chatbubble' as const },
  { key: 'job' as const, label: 'Job', icon: 'radio' as const },
];

export default function ModeSelector({ currentMode, onModeChange, jobModeAllowed, voiceAllowed }: ModeSelectorProps) {
  const handlePress = (mode: 'default' | 'text' | 'job') => {
    if (mode === 'job' && !jobModeAllowed) {
      Alert.alert('Business Plan Required', 'Job Mode with always-on monitoring is available on the Business plan.');
      return;
    }
    if (mode === 'default' && !voiceAllowed) {
      Alert.alert('Pro Plan Required', 'Voice mode is available on the Pro plan and above.');
      return;
    }
    onModeChange(mode);
  };

  return (
    <View style={styles.container}>
      {modes.map((mode) => {
        const isActive = currentMode === mode.key;
        const isLocked = (mode.key === 'job' && !jobModeAllowed) || (mode.key === 'default' && !voiceAllowed);

        return (
          <TouchableOpacity
            key={mode.key}
            onPress={() => handlePress(mode.key)}
            style={[styles.pill, isActive && styles.pillActive]}
            activeOpacity={0.7}
          >
            <Ionicons
              name={isLocked ? 'lock-closed' : mode.icon}
              size={14}
              color={isActive ? '#FFF' : 'rgba(255,255,255,0.6)'}
            />
            <Text style={[styles.label, isActive && styles.labelActive]}>
              {mode.label}
            </Text>
            {mode.key === 'job' && isActive && (
              <View style={styles.liveDot} />
            )}
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 24,
    padding: 2,
    gap: 2,
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 5,
  },
  pillActive: {
    backgroundColor: Colors.accent,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.6)',
  },
  labelActive: {
    color: '#FFF',
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#FF3B30',
  },
});
