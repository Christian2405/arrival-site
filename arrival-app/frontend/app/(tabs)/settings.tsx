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
import { Colors } from '../../constants/Colors';
import { useSettingsStore } from '../../store/settingsStore';
import { useAuthStore } from '../../store/authStore';

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
          { text: 'Open Settings', onPress: () => Linking.openSettings() },
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
              { text: 'Open Settings', onPress: () => Linking.openSettings() },
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
              { text: 'Open Settings', onPress: () => Linking.openSettings() },
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

  const initials = profile
    ? `${profile.first_name?.charAt(0) || ''}${profile.last_name?.charAt(0) || ''}`
    : 'A';

  return (
    <SafeAreaView style={styles.container}>
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

        {/* Voice & Input */}
        <Text style={styles.sectionLabel}>Voice & Input</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="volume-high-outline" size={18} color="#2A2622" />
              <Text style={styles.rowLabel}>Voice Output</Text>
            </View>
            <Switch
              value={voiceOutput}
              onValueChange={setVoiceOutput}
              trackColor={{ false: '#DDD9D5', true: '#2A2622' }}
              thumbColor="#FFF"
              ios_backgroundColor="#DDD9D5"
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="speedometer-outline" size={18} color="#2A2622" />
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
              <Ionicons name="text-outline" size={18} color="#2A2622" />
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
              <Ionicons name="swap-horizontal-outline" size={18} color="#2A2622" />
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
              <Ionicons name="flask-outline" size={18} color="#2A2622" />
              <View style={{ flex: 1 }}>
                <Text style={styles.rowLabel}>Demo Mode</Text>
                <Text style={styles.rowHint}>Uses sample responses</Text>
              </View>
            </View>
            <Switch
              value={demoMode}
              onValueChange={setDemoMode}
              trackColor={{ false: '#DDD9D5', true: '#2A2622' }}
              thumbColor="#FFF"
              ios_backgroundColor="#DDD9D5"
            />
          </View>

          <View style={styles.divider} />

          <TouchableOpacity
            style={styles.row}
            activeOpacity={0.6}
            onPress={() => Linking.openSettings()}
          >
            <View style={styles.rowLeft}>
              <Ionicons name="notifications-outline" size={18} color="#2A2622" />
              <Text style={styles.rowLabel}>Notifications</Text>
            </View>
            <Ionicons name="chevron-forward" size={16} color="#C7C2BC" />
          </TouchableOpacity>

          <View style={styles.divider} />

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="moon-outline" size={18} color="#2A2622" />
              <Text style={styles.rowLabel}>Dark Mode</Text>
            </View>
            <Switch
              value={false}
              disabled
              trackColor={{ false: '#E8E4DF', true: '#FE6B3F' }}
              thumbColor="#fff"
            />
          </View>
        </View>

        {/* Permissions */}
        <Text style={styles.sectionLabel}>Permissions</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="mic-outline" size={18} color="#2A2622" />
              <Text style={styles.rowLabel}>Microphone</Text>
            </View>
            <Switch
              value={micPermission === true}
              onValueChange={() => handlePermissionToggle('mic')}
              trackColor={{ false: '#DDD9D5', true: '#2A2622' }}
              thumbColor="#FFF"
              ios_backgroundColor="#DDD9D5"
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Ionicons name="camera-outline" size={18} color="#2A2622" />
              <Text style={styles.rowLabel}>Camera</Text>
            </View>
            <Switch
              value={cameraPermission === true}
              onValueChange={() => handlePermissionToggle('camera')}
              trackColor={{ false: '#DDD9D5', true: '#2A2622' }}
              thumbColor="#FFF"
              ios_backgroundColor="#DDD9D5"
            />
          </View>
        </View>

        {/* Account */}
        <Text style={styles.sectionLabel}>Account</Text>
        <View style={styles.card}>
          <TouchableOpacity
            style={styles.row}
            activeOpacity={0.6}
            onPress={() => Linking.openURL(`${WEBSITE_URL}/dashboard-individual#billing`)}
          >
            <View style={styles.rowLeft}>
              <Ionicons name="card-outline" size={18} color="#2A2622" />
              <Text style={styles.rowLabel}>Subscription</Text>
            </View>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <View style={styles.planBadgeSmall}>
                <Text style={styles.planBadgeSmallText}>{planLabel}</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#C7C2BC" />
            </View>
          </TouchableOpacity>

          <View style={styles.divider} />

          <TouchableOpacity
            style={styles.row}
            activeOpacity={0.6}
            onPress={() => Linking.openURL(`mailto:support@arrivalcompany.com?subject=Help%20Request`)}
          >
            <View style={styles.rowLeft}>
              <Ionicons name="help-circle-outline" size={18} color="#2A2622" />
              <Text style={styles.rowLabel}>Help & Support</Text>
            </View>
            <Ionicons name="chevron-forward" size={16} color="#C7C2BC" />
          </TouchableOpacity>

          <View style={styles.divider} />

          <TouchableOpacity
            style={styles.row}
            activeOpacity={0.6}
            onPress={() => Linking.openURL(`${WEBSITE_URL}/terms`)}
          >
            <View style={styles.rowLeft}>
              <Ionicons name="document-text-outline" size={18} color="#2A2622" />
              <Text style={styles.rowLabel}>Terms & Privacy</Text>
            </View>
            <Ionicons name="chevron-forward" size={16} color="#C7C2BC" />
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut} activeOpacity={0.6}>
          <Text style={styles.signOutText}>Sign Out</Text>
        </TouchableOpacity>

        <Text style={styles.versionText}>Arrival v2.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3F0EB',
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
    marginHorizontal: 16,
    marginTop: 12,
    marginBottom: 8,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 18,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#2A2622',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  profileInfo: {
    flex: 1,
    marginLeft: 14,
  },
  profileName: {
    fontSize: 17,
    fontWeight: '700',
    color: '#2A2622',
    letterSpacing: -0.3,
  },
  profileEmail: {
    fontSize: 13,
    color: '#A09A93',
    marginTop: 1,
    letterSpacing: -0.1,
  },
  planBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
    backgroundColor: '#F3F0EB',
  },
  planBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#2A2622',
    letterSpacing: 0.3,
  },

  // Section
  sectionLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#A09A93',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    paddingHorizontal: 20,
    marginTop: 28,
    marginBottom: 10,
  },

  // Card
  card: {
    backgroundColor: '#FFFFFF',
    marginHorizontal: 16,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },

  // Row — no icon backgrounds, just inline icons
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    minHeight: 54,
  },
  rowLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    flex: 1,
    marginRight: 12,
  },
  rowLabel: {
    fontSize: 15,
    fontWeight: '500',
    color: '#2A2622',
    letterSpacing: -0.2,
  },
  rowHint: {
    fontSize: 12,
    color: '#A09A93',
    marginTop: 1,
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: '#EBE7E2',
    marginLeft: 48,
  },

  // Segmented Control
  segmentedControl: {
    flexDirection: 'row',
    backgroundColor: '#F3F0EB',
    borderRadius: 8,
    padding: 2,
  },
  segment: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  segmentActive: {
    backgroundColor: '#2A2622',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.12,
    shadowRadius: 3,
    elevation: 2,
  },
  segmentText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#A09A93',
  },
  segmentTextActive: {
    color: '#FFFFFF',
  },

  // Coming soon
  comingSoonBadge: {
    backgroundColor: '#F3F0EB',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  comingSoonText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#A09A93',
    letterSpacing: 0.2,
  },

  // Plan badge (small, in row)
  planBadgeSmall: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    backgroundColor: '#F3F0EB',
  },
  planBadgeSmallText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#2A2622',
  },

  // Sign out
  signOutButton: {
    alignItems: 'center',
    paddingVertical: 16,
    marginTop: 32,
    marginHorizontal: 16,
  },
  signOutText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#C75450',
    letterSpacing: -0.2,
  },

  // Version
  versionText: {
    fontSize: 12,
    color: '#C7C2BC',
    textAlign: 'center',
    marginTop: 4,
  },
});
