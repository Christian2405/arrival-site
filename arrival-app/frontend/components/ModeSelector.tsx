import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, Radius, FontSize, IconSize } from '../constants/Colors';

interface ModeSelectorProps {
  currentMode: 'default' | 'text' | 'job';
  onModeChange: (mode: 'default' | 'text' | 'job') => void;
  jobModeAllowed: boolean;
  voiceAllowed: boolean;
  variant?: 'dark' | 'light';
}

const modes = [
  { key: 'default' as const, label: 'Voice', icon: 'mic' as const },
  { key: 'text' as const, label: 'Text', icon: 'chatbubble' as const },
  { key: 'job' as const, label: 'Job', icon: 'radio' as const },
];

export default function ModeSelector({ currentMode, onModeChange, jobModeAllowed, voiceAllowed, variant = 'dark' }: ModeSelectorProps) {
  const isLight = variant === 'light';

  return (
    <View style={[styles.container, isLight && styles.containerLight]}>
      {modes.map((mode) => {
        const isActive = currentMode === mode.key;
        const isLocked = (mode.key === 'job' && !jobModeAllowed) || (mode.key === 'default' && !voiceAllowed);

        const iconColor = isLocked
          ? (isLight ? Colors.textFaint : 'rgba(255,255,255,0.3)')
          : isActive
            ? '#FFF'
            : (isLight ? Colors.textMuted : 'rgba(255,255,255,0.6)');

        return (
          <TouchableOpacity
            key={mode.key}
            onPress={() => onModeChange(mode.key)}
            style={[styles.pill, isActive && styles.pillActive]}
            activeOpacity={0.7}
            accessibilityLabel={`${mode.label} mode${isLocked ? ', locked' : ''}${isActive ? ', selected' : ''}`}
            accessibilityRole="button"
          >
            <Ionicons
              name={isLocked ? 'lock-closed' : mode.icon}
              size={IconSize.sm}
              color={iconColor}
            />
            <Text style={[
              styles.label,
              isActive && styles.labelActive,
              !isActive && isLight && styles.labelLight,
            ]}>
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
    borderRadius: Radius.full,
    padding: 2,
    gap: 2,
  },
  containerLight: {
    backgroundColor: Colors.backgroundWarm,
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.full,
    gap: Spacing.xs,
  },
  pillActive: {
    backgroundColor: Colors.accent,
  },
  label: {
    fontSize: FontSize.sm,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.6)',
  },
  labelLight: {
    color: Colors.textMuted,
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
