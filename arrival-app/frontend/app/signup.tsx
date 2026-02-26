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
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants/Colors';
import { useAuthStore } from '../store/authStore';
import ArrivalLogo from '../components/ArrivalLogo';

const TRADES = [
  { label: 'HVAC', value: 'hvac' },
  { label: 'Plumbing', value: 'plumbing' },
  { label: 'Electrical', value: 'electrical' },
  { label: 'General Contractor', value: 'general' },
  { label: 'Other', value: 'other' },
];

const EXPERIENCE = [
  { label: '< 1 year', value: 'less_1_year' },
  { label: '1–3 years', value: '1_3_years' },
  { label: '3–5 years', value: '3_5_years' },
  { label: '5–10 years', value: '5_10_years' },
  { label: '10+ years', value: '10_plus_years' },
];

export default function SignupScreen() {
  const router = useRouter();
  const { signUp, signInWithGoogle, isLoading } = useAuthStore();
  const [googleLoading, setGoogleLoading] = useState(false);

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [trade, setTrade] = useState('hvac');
  const [experience, setExperience] = useState('1_3_years');
  const [error, setError] = useState('');

  const handleSignup = async () => {
    setError('');

    if (!firstName.trim() || !lastName.trim()) {
      setError('Please enter your name.');
      return;
    }
    if (!email.trim()) {
      setError('Please enter your email.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    const result = await signUp({
      email: email.trim(),
      password: password.trim(),
      firstName: firstName.trim(),
      lastName: lastName.trim(),
      trade,
      experience,
    });

    if (result.error) {
      if (result.error.includes('already registered')) {
        setError('This email is already registered. Try signing in instead.');
      } else {
        setError(result.error);
      }
    } else if (result.needsConfirmation) {
      Alert.alert(
        'Check your email',
        'We sent a confirmation link to your email. Please confirm your account, then sign in.',
        [{ text: 'OK', onPress: () => router.push('/login') }]
      );
    } else {
      // Account created — send to website to choose a plan
      Alert.alert(
        'Account created!',
        'To activate your subscription, choose a plan on our website. You have a 7-day trial to get started.',
        [
          {
            text: 'Choose a Plan',
            onPress: () => Linking.openURL('https://arrivalcompany.com/#pricing'),
          },
          { text: 'Later', style: 'cancel' },
        ]
      );
    }
  };

  const handleGoogleSignIn = async () => {
    setError('');
    setGoogleLoading(true);
    const result = await signInWithGoogle();
    if (result.error) {
      setError(result.error);
    }
    setGoogleLoading(false);
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
          {/* Back button */}
          <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
            <Ionicons name="chevron-back" size={24} color={Colors.textDark} />
          </TouchableOpacity>

          {/* Logo */}
          <View style={styles.logoWrap}>
            <ArrivalLogo width={140} color={Colors.text} />
          </View>

          <Text style={styles.heading}>Create your account</Text>

          {error ? (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={16} color={Colors.error} style={{ marginTop: 1 }} />
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
                editable={!isLoading}
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
                editable={!isLoading}
              />
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Email</Text>
            <TextInput
              style={styles.input}
              placeholder="you@example.com"
              placeholderTextColor={Colors.textLight}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              editable={!isLoading}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Password</Text>
            <View style={styles.passwordWrap}>
              <TextInput
                style={styles.passwordInput}
                placeholder="6+ characters"
                placeholderTextColor={Colors.textLight}
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
                editable={!isLoading}
              />
              <TouchableOpacity
                style={styles.eyeBtn}
                onPress={() => setShowPassword(!showPassword)}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              >
                <Ionicons
                  name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                  size={20}
                  color={Colors.textMuted}
                />
              </TouchableOpacity>
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
            style={[styles.button, (isLoading || googleLoading) && styles.buttonDisabled]}
            onPress={handleSignup}
            disabled={isLoading || googleLoading}
            activeOpacity={0.8}
          >
            {isLoading ? (
              <View style={styles.loadingRow}>
                <ActivityIndicator color="#FFF" size="small" />
                <Text style={styles.buttonText}>Creating account...</Text>
              </View>
            ) : (
              <Text style={styles.buttonText}>Create Account</Text>
            )}
          </TouchableOpacity>

          {/* Divider */}
          <View style={styles.dividerRow}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

          {/* Google Sign-Up */}
          <TouchableOpacity
            style={[styles.googleButton, googleLoading && styles.buttonDisabled]}
            onPress={handleGoogleSignIn}
            disabled={isLoading || googleLoading}
            activeOpacity={0.8}
          >
            {googleLoading ? (
              <View style={styles.loadingRow}>
                <ActivityIndicator color={Colors.text} size="small" />
                <Text style={styles.googleButtonText}>Connecting...</Text>
              </View>
            ) : (
              <>
                <Ionicons name="logo-google" size={18} color={Colors.text} />
                <Text style={styles.googleButtonText}>Continue with Google</Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkBtn}
            onPress={() => router.push('/login')}
          >
            <Text style={styles.linkText}>
              Already have an account? <Text style={styles.linkBold}>Sign in</Text>
            </Text>
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
    paddingTop: 8,
    paddingBottom: 40,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.card,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 1,
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
    marginBottom: 20,
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: 'rgba(255, 59, 48, 0.08)',
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    gap: 10,
  },
  errorText: {
    color: Colors.error,
    fontSize: 15,
    fontWeight: '500',
    flex: 1,
    lineHeight: 21,
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
  passwordWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
  },
  passwordInput: {
    flex: 1,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: Colors.text,
    letterSpacing: -0.2,
  },
  eyeBtn: {
    paddingHorizontal: 14,
    paddingVertical: 14,
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
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 22,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: Colors.border,
  },
  dividerText: {
    paddingHorizontal: 14,
    fontSize: 13,
    color: Colors.textLight,
    fontWeight: '500',
  },
  googleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.card,
    borderRadius: 14,
    paddingVertical: 15,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 10,
  },
  googleButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.text,
    letterSpacing: -0.2,
  },
  linkBtn: {
    alignItems: 'center',
    paddingVertical: 18,
  },
  linkText: {
    fontSize: 15,
    color: Colors.textSecondary,
  },
  linkBold: {
    color: Colors.accent,
    fontWeight: '600',
  },
});
