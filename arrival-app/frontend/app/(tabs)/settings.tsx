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
import { Colors, Spacing, Radius, FontSize, IconSize } from '../../constants/Colors';
import { useSettingsStore } from '../../store/settingsStore';
import { useAuthStore } from '../../store/authStore';
import { supabase } from '../../services/supabase';
import { useUsageStore, queryDisplayText, documentDisplayText } from '../../store/usageStore';

const WEBSITE_URL = 'https://arrivalcompany.com';

export default function SettingsScreen() {
  const router = useRouter();
  const {
    voiceOutput,
    voiceSpeed,
    units,
    textSize,
    setVoiceOutput,
    setVoiceSpeed,
    setUnits,
    setTextSize,
  } = useSettingsStore();

  const { profile, subscription, signOut, updateSpatialConsent } = useAuthStore();
  const { fetchUsage, isLoaded: usageLoaded } = useUsageStore();

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  const displayName = profile
    ? `${profile.first_name} ${profile.last_name}`
    : 'Arrival User';
  const displayEmail = profile?.email || 'Sign in to sync your data';

  // Use the effective plan from usage store (checks trial expiry on backend)
  // Fall back to subscription row if usage hasn't loaded yet
  const effectivePlan = usageLoaded
    ? useUsageStore.getState().plan
    : (subscription?.plan || 'free');
  const isTrial = subscription?.trial_ends_at && !subscription?.stripe_subscription_id;
  const planLabel = effectivePlan === 'free' && isTrial
    ? 'Free'
    : isTrial
      ? `${effectivePlan.charAt(0).toUpperCase() + effectivePlan.slice(1)} (Trial)`
      : effectivePlan.charAt(0).toUpperCase() + effectivePlan.slice(1);

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
      Alert.alert(
        `Disable ${type === 'mic' ? 'Microphone' : 'Camera'}`,
        'To revoke access, open your device settings for Arrival.',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Open Settings', onPress: () => Linking.openSettings().catch(() => {}) },
        ]
      );
    } else {
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
              // Call backend endpoint — handles Pinecone cleanup + DB + auth deletion
              const api = (await import('../../services/api')).default;
              const resp = await api.delete('/account');
              if (resp.status !== 200) {
                console.error('[Delete] Backend error:', resp.status, resp.data);
                Alert.alert('Error', 'Failed to delete account. Please contact support@arrivalcompany.com');
                return;
              }

              useAuthStore.setState({
                session: null,
                user: null,
                profile: null,
                subscription: null,
                teamMembership: null,
                needsOnboarding: false,
              });
              await supabase.auth.signOut().catch(() => {});
              router.replace('/login');
            } catch (e) {
              console.error('[Delete] Error:', e);
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

  // Simple row component
  const Row = ({ icon, label, right, hint, onPress }: {
    icon: keyof typeof Ionicons.glyphMap;
    label: string;
    right?: React.ReactNode;
    hint?: string;
    onPress?: () => void;
  }) => {
    const content = (
      <View style={st.row}>
        <Ionicons name={icon} size={20} color={Colors.textMuted} style={{ width: 28 }} />
        <View style={{ flex: 1 }}>
          <Text style={st.rowLabel}>{label}</Text>
          {hint && <Text style={st.rowHint}>{hint}</Text>}
        </View>
        {right}
      </View>
    );
    if (onPress) {
      return (
        <TouchableOpacity activeOpacity={0.5} onPress={onPress}>
          {content}
        </TouchableOpacity>
      );
    }
    return content;
  };

  const Seg = ({ options, value, onChange }: {
    options: { label: string; value: string }[];
    value: string;
    onChange: (v: any) => void;
  }) => (
    <View style={st.seg}>
      {options.map((o) => (
        <TouchableOpacity
          key={o.value}
          style={[st.segItem, value === o.value && st.segItemActive]}
          onPress={() => onChange(o.value)}
        >
          <Text style={[st.segText, value === o.value && st.segTextActive]}>{o.label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );

  return (
    <SafeAreaView style={st.container}>
      {/* Header */}
      <View style={st.header}>
        <TouchableOpacity onPress={() => router.push('/(tabs)/home')} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={Colors.textDark} />
        </TouchableOpacity>
        <Text style={st.headerTitle}>Settings</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 60 }}>
        {/* Profile */}
        <View style={st.profile}>
          <View style={st.avatar}>
            <Text style={st.avatarText}>{initials}</Text>
          </View>
          <Text style={st.profileName}>{displayName}</Text>
          <Text style={st.profileEmail}>{displayEmail}</Text>
          <View style={st.planPill}>
            <Text style={st.planPillText}>{planLabel} Plan</Text>
          </View>
        </View>

        {/* Usage */}
        {profile && (
          <View style={st.usageRow}>
            <View style={st.usageStat}>
              <Text style={st.usageNumber}>{usageLoaded ? queryDisplayText() : '—'}</Text>
              <Text style={st.usageLabel}>Queries</Text>
            </View>
            <View style={st.usageDivider} />
            <View style={st.usageStat}>
              <Text style={st.usageNumber}>{usageLoaded ? documentDisplayText() : '—'}</Text>
              <Text style={st.usageLabel}>Documents</Text>
            </View>
            <View style={st.usageDivider} />
            <View style={st.usageStat}>
              <Text style={st.usageNumber}>
                {usageLoaded
                  ? useUsageStore.getState().jobModeMinutes === -1
                    ? 'Unlimited'
                    : `${Math.floor(useUsageStore.getState().jobSecondsUsedToday / 60)}/${useUsageStore.getState().jobModeMinutes} min`
                  : '—'}
              </Text>
              <Text style={st.usageLabel}>Job Mode</Text>
            </View>
          </View>
        )}

        {/* Voice */}
        <Text style={st.section}>VOICE & INPUT</Text>
        <View style={st.group}>
          <Row
            icon="volume-high-outline"
            label="Voice Output"
            right={
              <Switch
                value={voiceOutput}
                onValueChange={setVoiceOutput}
                trackColor={{ false: '#E0E0E0', true: Colors.textDark }}
                thumbColor="#FFF"
              />
            }
          />
          <View style={st.sep} />
          <Row
            icon="speedometer-outline"
            label="Voice Speed"
            right={
              <Seg
                options={[{ label: 'Slow', value: 'slow' }, { label: 'Normal', value: 'normal' }, { label: 'Fast', value: 'fast' }]}
                value={voiceSpeed}
                onChange={setVoiceSpeed}
              />
            }
          />
          <View style={st.sep} />
          <Row
            icon="text-outline"
            label="Text Size"
            right={
              <Seg
                options={[{ label: 'S', value: 'small' }, { label: 'M', value: 'medium' }, { label: 'L', value: 'large' }]}
                value={textSize}
                onChange={setTextSize}
              />
            }
          />
          <View style={st.sep} />
          <Row
            icon="swap-horizontal-outline"
            label="Units"
            right={
              <Seg
                options={[{ label: 'Imperial', value: 'imperial' }, { label: 'Metric', value: 'metric' }]}
                value={units}
                onChange={setUnits}
              />
            }
          />
        </View>

        {/* App */}
        <Text style={st.section}>APP</Text>
        <View style={st.group}>
          <Row
            icon="notifications-outline"
            label="Notifications"
            right={<Ionicons name="chevron-forward" size={16} color={Colors.textFaint} />}
            onPress={() => Linking.openSettings().catch(() => {})}
          />
        </View>

        {/* Permissions */}
        <Text style={st.section}>PERMISSIONS</Text>
        <View style={st.group}>
          <Row
            icon="mic-outline"
            label="Microphone"
            right={
              <Switch
                value={micPermission === true}
                onValueChange={() => handlePermissionToggle('mic')}
                trackColor={{ false: '#E0E0E0', true: Colors.textDark }}
                thumbColor="#FFF"
              />
            }
          />
          <View style={st.sep} />
          <Row
            icon="camera-outline"
            label="Camera"
            right={
              <Switch
                value={cameraPermission === true}
                onValueChange={() => handlePermissionToggle('camera')}
                trackColor={{ false: '#E0E0E0', true: Colors.textDark }}
                thumbColor="#FFF"
              />
            }
          />
        </View>

        {/* Data & Privacy */}
        <Text style={st.section}>DATA & PRIVACY</Text>
        <View style={st.group}>
          <Row
            icon="videocam-outline"
            label="AI training recordings"
            right={
              <Switch
                value={profile?.spatial_capture_consent === true}
                onValueChange={(val) => updateSpatialConsent(val)}
                trackColor={{ false: '#E0E0E0', true: Colors.textDark }}
                thumbColor="#FFF"
              />
            }
          />
        </View>

        {/* Account */}
        <Text style={st.section}>ACCOUNT</Text>
        <View style={st.group}>
          <Row
            icon="help-circle-outline"
            label="Help & Support"
            right={<Ionicons name="chevron-forward" size={16} color={Colors.textFaint} />}
            onPress={() => Linking.openURL(`mailto:support@arrivalcompany.com?subject=Help%20Request`).catch(() => {})}
          />
          <View style={st.sep} />
          <Row
            icon="document-text-outline"
            label="Terms & Privacy"
            right={<Ionicons name="chevron-forward" size={16} color={Colors.textFaint} />}
            onPress={() => Linking.openURL(`${WEBSITE_URL}/terms`).catch(() => {})}
          />
        </View>

        {/* Actions */}
        <TouchableOpacity style={st.actionBtn} onPress={handleSignOut} activeOpacity={0.5}>
          <Text style={st.actionText}>Sign Out</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[st.actionBtn, { marginTop: 4 }]} onPress={handleDeleteAccount} activeOpacity={0.5}>
          <Text style={[st.actionText, { color: '#D32F2F', fontSize: 14 }]}>Delete Account</Text>
        </TouchableOpacity>

        <Text style={st.version}>Arrival v1.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const st = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: Colors.textDark,
  },

  // Profile — centered card
  profile: {
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 20,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: Colors.textDark,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  avatarText: {
    color: '#FFF',
    fontSize: 22,
    fontWeight: '700',
  },
  profileName: {
    fontSize: 20,
    fontWeight: '700',
    color: Colors.textDark,
    letterSpacing: -0.3,
  },
  profileEmail: {
    fontSize: 14,
    color: Colors.textMuted,
    marginTop: 2,
  },
  planPill: {
    marginTop: 10,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: Colors.backgroundWarm,
  },
  planPillText: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.textMuted,
  },

  // Usage stats
  usageRow: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 8,
    backgroundColor: Colors.card,
    borderRadius: 12,
    paddingVertical: 14,
  },
  usageStat: {
    flex: 1,
    alignItems: 'center',
  },
  usageNumber: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.textDark,
  },
  usageLabel: {
    fontSize: 12,
    color: Colors.textMuted,
    marginTop: 2,
  },
  usageDivider: {
    width: 1,
    backgroundColor: Colors.borderWarm,
  },

  // Section headers
  section: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 0.5,
    paddingHorizontal: 20,
    marginTop: 24,
    marginBottom: 8,
  },

  // Grouped rows
  group: {
    marginHorizontal: 16,
    backgroundColor: Colors.card,
    borderRadius: 12,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 12,
    minHeight: 48,
  },
  rowLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: Colors.text,
    letterSpacing: -0.2,
  },
  rowHint: {
    fontSize: 12,
    color: Colors.textSecondary,
    marginTop: 1,
  },
  rowDetail: {
    fontSize: 14,
    color: Colors.textSecondary,
  },
  sep: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: Colors.borderWarm,
    marginLeft: 42,
  },

  // Segmented control
  seg: {
    flexDirection: 'row',
    backgroundColor: Colors.backgroundWarm,
    borderRadius: 8,
    padding: 2,
  },
  segItem: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
  },
  segItemActive: {
    backgroundColor: Colors.textDark,
  },
  segText: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.textMuted,
  },
  segTextActive: {
    color: '#FFF',
  },

  // Actions
  actionBtn: {
    alignItems: 'center',
    paddingVertical: 14,
    marginTop: 28,
    marginHorizontal: 16,
  },
  actionText: {
    fontSize: 16,
    fontWeight: '500',
    color: Colors.errorMuted,
  },

  version: {
    fontSize: 12,
    color: Colors.textFaint,
    textAlign: 'center',
    marginTop: 8,
  },

  // Upgrade banner
  upgradeBanner: {
    marginHorizontal: 16,
    marginBottom: 12,
    borderRadius: 14,
    backgroundColor: Colors.planBusiness,
    overflow: 'hidden',
  },
  upgradeBannerInner: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 18,
    paddingVertical: 16,
    gap: 12,
  },
  upgradeBannerTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: -0.3,
  },
  upgradeBannerSub: {
    fontSize: 13,
    color: 'rgba(255,255,255,0.85)',
    marginTop: 2,
  },
});
