import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Switch,
  TouchableOpacity,
  Alert,
  Platform,
  Linking,
  AppState,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Camera } from 'expo-camera';
import { Audio } from 'expo-av';
import { Colors, Spacing, Radius, FontSize, IconSize, Shadow } from '../../constants/Colors';
import { useSettingsStore } from '../../store/settingsStore';
import { useAuthStore } from '../../store/authStore';
import { useUsageStore, queryDisplayText, documentDisplayText } from '../../store/usageStore';

const WEBSITE_URL = 'https://arrivalcompany.com';

type IoniconsName = keyof typeof Ionicons.glyphMap;

export default function SettingsScreen() {
  const router = useRouter();
  const {
    voiceOutput,
    demoMode,
    voiceSpeed,
    units,
    textSize,
    setVoiceOutput,
    setDemoMode,
    setVoiceSpeed,
    setUnits,
    setTextSize,
  } = useSettingsStore();

  const { profile, subscription, signOut } = useAuthStore();
  const { fetchUsage, isLoaded: usageLoaded } = useUsageStore();

  // Fetch usage on mount
  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  const displayName = profile
    ? `${profile.first_name} ${profile.last_name}`
    : 'Arrival User';
  const displayEmail = profile?.email || 'Sign in to sync your data';
  const plan = subscription?.plan;
  const planLabel = plan
    ? plan.charAt(0).toUpperCase() + plan.slice(1)
    : '';

  // Permission states
  const [micPermission, setMicPermission] = useState<boolean | null>(null);
  const [cameraPermission, setCameraPermission] = useState<boolean | null>(null);

  const checkPermissions = useCallback(async () => {
    try {
      const { status: camStatus } = await Camera.getCameraPermissionsAsync();
      setCameraPermission(camStatus === 'granted');
      const { status: micStatus } = await Audio.getPermissionsAsync();
      setMicPermission(micStatus === 'granted');
    } catch (e) {
      console.error('Permission check error:', e);
    }
  }, []);

  // Check permissions on mount and when app returns from settings
  useEffect(() => {
    checkPermissions();
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') checkPermissions();
    });
    return () => sub.remove();
  }, [checkPermissions]);

  const handlePermissionToggle = async (type: 'mic' | 'camera') => {
    const currentlyGranted = type === 'mic' ? micPermission : cameraPermission;

    if (currentlyGranted) {
      // Can't revoke from app — send to device settings
      Alert.alert(
        `Disable ${type === 'mic' ? 'Microphone' : 'Camera'}`,
        'To revoke access, open your device settings for Arrival.',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Open Settings', onPress: () => Linking.openSettings().catch(() => {}) },
        ]
      );
    } else {
      // Request permission
      if (type === 'mic') {
        const { status } = await Audio.requestPermissionsAsync();
        if (status === 'granted') {
          setMicPermission(true);
        } else {
          Alert.alert(
            'Microphone Access',
            'Microphone access was denied. You can enable it in your device settings.',
            [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Open Settings', onPress: () => Linking.openSettings().catch(() => {}) },
            ]
          );
        }
      } else {
        const { status } = await Camera.requestCameraPermissionsAsync();
        if (status === 'granted') {
          setCameraPermission(true);
        } else {
          Alert.alert(
            'Camera Access',
            'Camera access was denied. You can enable it in your device settings.',
            [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Open Settings', onPress: () => Linking.openSettings().catch(() => {}) },
            ]
          );
        }
      }
    }
  };

  const handleSignOut = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: async () => {
          await signOut();
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      'Delete Account',
      'This will permanently delete your account and all data. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete My Account',
          style: 'destructive',
          onPress: async () => {
            try {
              const token = await useAuthStore.getState().getAccessToken();
              const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';
              await fetch(`${BASE_URL}/api/account`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` },
              });
              await signOut();
              Alert.alert('Account Deleted', 'Your account has been permanently deleted.');
            } catch (e) {
              Alert.alert('Error', 'Failed to delete account. Please contact support@arrivalcompany.com');
            }
          },
        },
      ]
    );
  };

  const initials = profile
    ? `${profile.first_name?.charAt(0) || ''}${profile.last_name?.charAt(0) || ''}`
    : 'A';

  return (
    <SafeAreaView style={styles.container}>
      {/* Header with back button */}
      <View style={styles.headerRow}>
        <TouchableOpacity onPress={() => router.push('/(tabs)/home')}>
          <Ionicons name="chevron-back" size={IconSize.lg} color={Colors.textDark} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Settings</Text>
        <View style={{ width: IconSize.lg }} />
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Profile Card */}
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{initials}</Text>
          </View>
          <View style={styles.profileInfo}>
            <Text style={styles.profileName}>{displayName}</Text>
            <Text style={styles.profileEmail}>{displayEmail}</Text>
          </View>
          <View style={styles.planBadge}>
            <Text style={styles.planBadgeText}>{planLabel}</Text>
          </View>
        </View>

        {/* Usage — only show when signed in */}
        {profile && (
          <>
            <Text style={styles.sectionLabel}>Usage</Text>
            <View style={styles.card}>
              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Ionicons name="chatbubble-outline" size={IconSize.md} color={Colors.textDark} />
                  <Text style={styles.rowLabel}>Queries</Text>
                </View>
                <Text style={styles.usageValue}>{usageLoaded ? queryDisplayText() : '...'}</Text>
              </View>

              <View style={styles.divider} />

              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Ionicons name="document-outline" size={IconSize.md} color={Colors.textDark} />
                  <Text style={styles.rowLabel}>Documents</Text>
                </View>
                <Text style={styles.usageValue}>{usageLoaded ? documentDisplayText() : '...'}</Text>
              </View>
            </View>
          </>
        )}

        {/* Voice & Input */}
        <Text style={styles.sectionLabel}>Voice & Input</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="volume-high-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Voice Output</Text>
            </View>
            <Switch
              value={voiceOutput}
              onValueChange={setVoiceOutput}
              trackColor={{ false: Colors.switchTrack, true: Colors.textDark }}
              thumbColor={Colors.card}
              ios_backgroundColor={Colors.switchTrack}
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="speedometer-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Voice Speed</Text>
            </View>
            <View style={styles.segmentedControl}>
              {(['slow', 'normal', 'fast'] as const).map((speed) => (
                <TouchableOpacity
                  key={speed}
                  style={[styles.segment, voiceSpeed === speed && styles.segmentActive]}
                  onPress={() => setVoiceSpeed(speed)}
                >
                  <Text
                    style={[styles.segmentText, voiceSpeed === speed && styles.segmentTextActive]}
                  >
                    {speed.charAt(0).toUpperCase() + speed.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={styles.divider} />

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="text-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Text Size</Text>
            </View>
            <View style={styles.segmentedControl}>
              {([
                { label: 'S', value: 'small' },
                { label: 'M', value: 'medium' },
                { label: 'L', value: 'large' },
              ] as const).map((size) => (
                <TouchableOpacity
                  key={size.value}
                  style={[styles.segment, textSize === size.value && styles.segmentActive]}
                  onPress={() => setTextSize(size.value as any)}
                >
                  <Text
                    style={[styles.segmentText, textSize === size.value && styles.segmentTextActive]}
                  >
                    {size.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>

        {/* Measurement */}
        <Text style={styles.sectionLabel}>Measurement</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="swap-horizontal-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Units</Text>
            </View>
            <View style={styles.segmentedControl}>
              {(['imperial', 'metric'] as const).map((unit) => (
                <TouchableOpacity
                  key={unit}
                  style={[styles.segment, units === unit && styles.segmentActive]}
                  onPress={() => setUnits(unit)}
                >
                  <Text style={[styles.segmentText, units === unit && styles.segmentTextActive]}>
                    {unit.charAt(0).toUpperCase() + unit.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>

        {/* App */}
        <Text style={styles.sectionLabel}>App</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="flask-outline" size={IconSize.md} color={Colors.textDark} />
              <View style={{ flex: 1 }}>
                <Text style={styles.rowLabel}>Demo Mode</Text>
                <Text style={styles.rowHint}>Uses sample responses</Text>
              </View>
            </View>
            <Switch
              value={demoMode}
              onValueChange={setDemoMode}
              trackColor={{ false: Colors.switchTrack, true: Colors.textDark }}
              thumbColor={Colors.card}
              ios_backgroundColor={Colors.switchTrack}
            />
          </View>

          <View style={styles.divider} />

          <TouchableOpacity
            style={styles.row}
            activeOpacity={0.6}
            onPress={() => Linking.openSettings().catch(() => {})}
          >
            <View style={styles.rowLeft}>
              <Ionicons name="notifications-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Notifications</Text>
            </View>
            <Ionicons name="chevron-forward" size={IconSize.sm} color={Colors.textFaint} />
          </TouchableOpacity>

          <View style={styles.divider} />

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="moon-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Dark Mode</Text>
            </View>
            <View style={styles.comingSoonBadge}>
              <Text style={styles.comingSoonText}>Coming Soon</Text>
            </View>
          </View>
        </View>

        {/* Permissions */}
        <Text style={styles.sectionLabel}>Permissions</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="mic-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Microphone</Text>
            </View>
            <Switch
              value={micPermission === true}
              onValueChange={() => handlePermissionToggle('mic')}
              trackColor={{ false: Colors.switchTrack, true: Colors.textDark }}
              thumbColor={Colors.card}
              ios_backgroundColor={Colors.switchTrack}
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="camera-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Camera</Text>
            </View>
            <Switch
              value={cameraPermission === true}
              onValueChange={() => handlePermissionToggle('camera')}
              trackColor={{ false: Colors.switchTrack, true: Colors.textDark }}
              thumbColor={Colors.card}
              ios_backgroundColor={Colors.switchTrack}
            />
          </View>
        </View>

        {/* Account */}
        <Text style={styles.sectionLabel}>Account</Text>
        <View style={styles.card}>
          <TouchableOpacity
            style={styles.row}
            activeOpacity={0.6}
            onPress={() => Linking.openURL(`${WEBSITE_URL}/dashboard-individual#billing`).catch(() => Alert.alert('Error', 'Could not open link'))}
          >
            <View style={styles.rowLeft}>
              <Ionicons name="card-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Subscription</Text>
            </View>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <View style={styles.planBadgeSmall}>
                <Text style={styles.planBadgeSmallText}>{planLabel}</Text>
              </View>
              <Ionicons name="chevron-forward" size={IconSize.sm} color={Colors.textFaint} />
            </View>
          </TouchableOpacity>

          <View style={styles.divider} />

          <TouchableOpacity
            style={styles.row}
            activeOpacity={0.6}
            onPress={() => Linking.openURL(`mailto:support@arrivalcompany.com?subject=Help%20Request`).catch(() => Alert.alert('Error', 'Could not open link'))}
          >
            <View style={styles.rowLeft}>
              <Ionicons name="help-circle-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Help & Support</Text>
            </View>
            <Ionicons name="chevron-forward" size={IconSize.sm} color={Colors.textFaint} />
          </TouchableOpacity>

          <View style={styles.divider} />

          <TouchableOpacity
            style={styles.row}
            activeOpacity={0.6}
            onPress={() => Linking.openURL(`${WEBSITE_URL}/terms`).catch(() => Alert.alert('Error', 'Could not open link'))}
          >
            <View style={styles.rowLeft}>
              <Ionicons name="document-text-outline" size={IconSize.md} color={Colors.textDark} />
              <Text style={styles.rowLabel}>Terms & Privacy</Text>
            </View>
            <Ionicons name="chevron-forward" size={IconSize.sm} color={Colors.textFaint} />
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut} activeOpacity={0.6}>
          <Text style={styles.signOutText}>Sign Out</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.signOutButton, { marginTop: 8 }]} onPress={handleDeleteAccount} activeOpacity={0.6}>
          <Text style={[styles.signOutText, { fontSize: FontSize.sm, color: Colors.textMuted }]}>Delete Account</Text>
        </TouchableOpacity>

        <Text style={styles.versionText}>Arrival v1.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.backgroundWarm,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.md,
  },
  headerTitle: {
    fontSize: FontSize.lg,
    fontWeight: '700',
    color: Colors.textDark,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 50,
  },

  // Profile Card
  profileCard: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: Spacing.base,
    marginTop: Spacing.md,
    marginBottom: Spacing.sm,
    backgroundColor: Colors.card,
    borderRadius: Radius.lg,
    padding: 18,
    ...Shadow.medium,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: Radius.full,
    backgroundColor: Colors.textDark,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: Colors.card,
    fontSize: FontSize.lg,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  profileInfo: {
    flex: 1,
    marginLeft: 14,
  },
  profileName: {
    fontSize: FontSize.lg,
    fontWeight: '700',
    color: Colors.textDark,
    letterSpacing: -0.3,
  },
  profileEmail: {
    fontSize: FontSize.sm,
    color: Colors.textMuted,
    marginTop: 1,
    letterSpacing: -0.1,
  },
  planBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: Radius.full,
    backgroundColor: Colors.backgroundWarm,
  },
  planBadgeText: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    color: Colors.textDark,
    letterSpacing: 0.3,
  },

  // Section
  sectionLabel: {
    fontSize: FontSize.xs,
    fontWeight: '600',
    color: Colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    paddingHorizontal: 20,
    marginTop: 28,
    marginBottom: 10,
  },

  // Card
  card: {
    backgroundColor: Colors.card,
    marginHorizontal: Spacing.base,
    borderRadius: Radius.lg,
    ...Shadow.medium,
  },

  // Row
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.base,
    paddingVertical: 14,
    minHeight: 54,
  },
  rowLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    flex: 1,
    marginRight: Spacing.md,
  },
  rowLabel: {
    fontSize: FontSize.base,
    fontWeight: '500',
    color: Colors.textDark,
    letterSpacing: -0.2,
  },
  rowHint: {
    fontSize: FontSize.xs,
    color: Colors.textMuted,
    marginTop: 1,
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: Colors.borderWarm,
    marginLeft: 48,
  },

  // Usage value
  usageValue: {
    fontSize: FontSize.sm,
    fontWeight: '600',
    color: Colors.textMuted,
    letterSpacing: -0.2,
  },

  // Segmented Control
  segmentedControl: {
    flexDirection: 'row',
    backgroundColor: Colors.backgroundWarm,
    borderRadius: Radius.sm,
    padding: 2,
  },
  segment: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    borderRadius: Radius.sm,
  },
  segmentActive: {
    backgroundColor: Colors.textDark,
    ...Shadow.subtle,
  },
  segmentText: {
    fontSize: FontSize.sm,
    fontWeight: '600',
    color: Colors.textMuted,
  },
  segmentTextActive: {
    color: Colors.card,
  },

  // Coming soon
  comingSoonBadge: {
    backgroundColor: Colors.backgroundWarm,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radius.sm,
  },
  comingSoonText: {
    fontSize: FontSize.xs,
    fontWeight: '600',
    color: Colors.textMuted,
    letterSpacing: 0.2,
  },

  // Plan badge (small, in row)
  planBadgeSmall: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.sm,
    backgroundColor: Colors.backgroundWarm,
  },
  planBadgeSmallText: {
    fontSize: FontSize.xs,
    fontWeight: '700',
    color: Colors.textDark,
  },

  // Sign out
  signOutButton: {
    alignItems: 'center',
    paddingVertical: Spacing.base,
    marginTop: Spacing.xl,
    marginHorizontal: Spacing.base,
  },
  signOutText: {
    fontSize: FontSize.base,
    fontWeight: '600',
    color: Colors.errorMuted,
    letterSpacing: -0.2,
  },

  // Version
  versionText: {
    fontSize: FontSize.xs,
    color: Colors.textFaint,
    textAlign: 'center',
    marginTop: Spacing.xs,
  },
});
