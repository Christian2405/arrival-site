import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  ScrollView,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Colors } from '../constants/Colors';
import { useAuthStore } from '../store/authStore';
import ArrivalLogo from '../components/ArrivalLogo';

const TRADES = [
  { label: 'HVAC', value: 'hvac' },
  { label: 'Plumbing', value: 'plumbing' },
  { label: 'Electrical', value: 'electrical' },
  { label: 'General Contractor', value: 'general_construction' },
  { label: 'Other', value: 'other' },
];

const EXPERIENCE = [
  { label: '< 1 year', value: 'apprentice' },
  { label: '1-3 years', value: '1_3_years' },
  { label: '3-10 years', value: '3_10_years' },
  { label: '10+ years', value: '10_plus_years' },
  { label: 'DIY / Homeowner', value: 'diy_homeowner' },
];

export default function OnboardingScreen() {
  const router = useRouter();
  const { user, completeOnboarding } = useAuthStore();

  // Pre-fill name from Google metadata if available
  const meta = user?.user_metadata || {};
  const googleFullName = meta.full_name || meta.name || '';
  const googleFirst = meta.first_name || googleFullName.split(' ')[0] || '';
  const googleLast = meta.last_name || googleFullName.split(' ').slice(1).join(' ') || '';

  const [firstName, setFirstName] = useState(googleFirst);
  const [lastName, setLastName] = useState(googleLast);
  const [trade, setTrade] = useState('');
  const [experience, setExperience] = useState('1_3_years');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleComplete = async () => {
    setError('');

    if (!firstName.trim() || !lastName.trim()) {
      setError('Please enter your name.');
      return;
    }
    if (!trade) {
      setError('Please select your trade.');
      return;
    }

    setLoading(true);
    const result = await completeOnboarding({
      firstName: firstName.trim(),
      lastName: lastName.trim(),
      trade,
      experience,
    });
    setLoading(false);

    if (result.error) {
      setError(result.error);
    } else {
      Alert.alert(
        'Welcome to Arrival!',
        'Your account is ready. You have a 7-day free trial with full access.',
        [{ text: 'Get Started' }]
      );
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.logoWrap}>
            <ArrivalLogo width={140} color={Colors.text} />
          </View>

          <Text style={styles.heading}>Complete your profile</Text>
          <Text style={styles.subheading}>Tell us a bit about yourself so we can tailor Arrival to your trade.</Text>

          {error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          {/* Name row */}
          <View style={styles.nameRow}>
            <View style={[styles.inputGroup, styles.nameField]}>
              <Text style={styles.label}>First Name</Text>
              <TextInput
                style={styles.input}
                placeholder="John"
                placeholderTextColor={Colors.textLight}
                value={firstName}
                onChangeText={setFirstName}
                autoCapitalize="words"
                editable={!loading}
              />
            </View>
            <View style={[styles.inputGroup, styles.nameField]}>
              <Text style={styles.label}>Last Name</Text>
              <TextInput
                style={styles.input}
                placeholder="Smith"
                placeholderTextColor={Colors.textLight}
                value={lastName}
                onChangeText={setLastName}
                autoCapitalize="words"
                editable={!loading}
              />
            </View>
          </View>

          {/* Trade picker */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Primary Trade</Text>
            <View style={styles.chipRow}>
              {TRADES.map((t) => (
                <TouchableOpacity
                  key={t.value}
                  style={[styles.chip, trade === t.value && styles.chipActive]}
                  onPress={() => setTrade(t.value)}
                >
                  <Text style={[styles.chipText, trade === t.value && styles.chipTextActive]}>
                    {t.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Experience picker */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Experience</Text>
            <View style={styles.chipRow}>
              {EXPERIENCE.map((e) => (
                <TouchableOpacity
                  key={e.value}
                  style={[styles.chip, experience === e.value && styles.chipActive]}
                  onPress={() => setExperience(e.value)}
                >
                  <Text style={[styles.chipText, experience === e.value && styles.chipTextActive]}>
                    {e.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleComplete}
            disabled={loading}
            activeOpacity={0.8}
          >
            {loading ? (
              <View style={styles.loadingRow}>
                <ActivityIndicator color="#FFF" size="small" />
                <Text style={styles.buttonText}>Saving...</Text>
              </View>
            ) : (
              <Text style={styles.buttonText}>Get Started</Text>
            )}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.backgroundWarm,
  },
  flex: { flex: 1 },
  scrollContent: {
    paddingHorizontal: 28,
    paddingTop: 40,
    paddingBottom: 40,
  },
  logoWrap: {
    alignItems: 'center',
    marginBottom: 24,
  },
  heading: {
    fontSize: 26,
    fontWeight: '700',
    color: Colors.text,
    letterSpacing: -0.5,
    marginBottom: 8,
  },
  subheading: {
    fontSize: 15,
    color: Colors.textSecondary,
    marginBottom: 24,
    lineHeight: 21,
  },
  errorBox: {
    backgroundColor: 'rgba(255, 59, 48, 0.08)',
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
  },
  errorText: {
    color: Colors.error,
    fontSize: 15,
    fontWeight: '500',
  },
  nameRow: {
    flexDirection: 'row',
    gap: 12,
  },
  nameField: {
    flex: 1,
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: 6,
    letterSpacing: -0.1,
  },
  input: {
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: Colors.text,
    letterSpacing: -0.2,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: Colors.borderLight,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  chipActive: {
    backgroundColor: Colors.accentMuted,
    borderColor: Colors.accent,
  },
  chipText: {
    fontSize: 13,
    fontWeight: '500',
    color: Colors.textSecondary,
  },
  chipTextActive: {
    color: Colors.accent,
    fontWeight: '600',
  },
  button: {
    backgroundColor: Colors.buttonDark,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonText: {
    color: Colors.textOnDark,
    fontSize: 17,
    fontWeight: '600',
    letterSpacing: -0.2,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
});
