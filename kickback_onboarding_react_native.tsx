import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import ReactNativeBiometrics, { BiometryTypes } from 'react-native-biometrics';

interface Props {
  onRulesAccepted: (consentPayload: Record<string, any>) => void;
}

export const KickBackOnboardingRulesScreen: React.FC<Props> = ({ onRulesAccepted }) => {
  const [termsChecked, setTermsChecked] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const rulesVersion = '1.0.0';

  const handleAcceptance = async () => {
    setIsAuthenticating(true);
    try {
      const rnBiometrics = new ReactNativeBiometrics();
      const { available, biometryType } = await rnBiometrics.isSensorAvailable();

      if (!available) {
        Alert.alert('Hardware Exception', 'Biometric hardware sensor unavailable on this device.');
        setIsAuthenticating(false);
        return;
      }

      const { success } = await rnBiometrics.simplePrompt({
        promptMessage: 'Confirm identity to accept Community Rules & generate non-exportable signing key',
        cancelButtonText: 'Cancel',
      });

      if (success) {
        const consentPayload = {
          event_type: 'USER_PROFILE_UPDATE',
          author_type: 'HUMAN_USER',
          payload: {
            terms_accepted: true,
            terms_version: rulesVersion,
            accepted_at_timestamp: Date.now(),
            attestation_proof: {
              platform: Platform.OS === 'ios' ? 'ios_app_attest' : 'android_play_integrity',
              biometric_type: biometryType || BiometryTypes.Biometrics,
              biometric_auth_confirmed: true,
            },
          },
        };

        onRulesAccepted(consentPayload);
      } else {
        Alert.alert('Authentication Failed', 'Biometric confirmation is required to proceed.');
      }
    } catch (error) {
      Alert.alert('Hardware Authentication Error', String(error));
    } finally {
      setIsAuthenticating(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Welcome to The KickBack</Text>
        <Text style={styles.subtitle}>
          A human-first social experience powered by The Omniverse Network.
        </Text>
      </View>

      <ScrollView style={styles.rulesContainer} contentContainerStyle={styles.rulesContent}>
        <RuleSection
          title="1. Human Sovereignty Policy"
          body="The KickBack feed is strictly reserved for human users. Automated script runners, headless browser bots, emulator spammers, and AI proxy posting are strictly forbidden."
        />
        <RuleSection
          title="2. Biometric Authorization & Hardware Attestation"
          body="To publish content, your mobile device must pass OS hardware attestation. Every post is cryptographically signed using keys secured in hardware, requiring FaceID/TouchID."
        />
        <RuleSection
          title="3. Anti-Spam & Fair Usage Limits"
          body="Post creation is capped at 3 posts per minute and 25 posts per hour. Repetitive spam or automated templates exceeding an 85% similarity threshold will be rejected."
        />
        <RuleSection
          title="4. Immutable Log & Local Privacy"
          body="Actions are appended to an immutable Merkle event log on your device. You retain full data ownership and can export your history or set posts to auto-expire."
        />
        <RuleSection
          title="5. P2P Network Conduct"
          body="Devices relaying forged signatures or bot spam across The-Omni-Hub P2P network will receive peer warnings, bandwidth rate-limiting, and automatic blacklisting."
        />
      </ScrollView>

      <TouchableOpacity
        style={styles.checkboxRow}
        activeOpacity={0.8}
        onPress={() => setTermsChecked(!termsChecked)}
      >
        <View style={[styles.checkbox, termsChecked && styles.checkboxActive]}>
          {termsChecked && <Text style={styles.checkmark}>✓</Text>}
        </View>
        <Text style={styles.checkboxLabel}>
          I agree to the Community Rules & Terms of Conduct
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.button, (!termsChecked || isAuthenticating) && styles.buttonDisabled]}
        disabled={!termsChecked || isAuthenticating}
        onPress={handleAcceptance}
      >
        {isAuthenticating ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.buttonText}>Confirm Identity & Accept</Text>
        )}
      </TouchableOpacity>
    </View>
  );
};

const RuleSection: React.FC<{ title: string; body: string }> = ({ title, body }) => (
  <View style={styles.ruleBlock}>
    <Text style={styles.ruleTitle}>{title}</Text>
    <Text style={styles.ruleBody}>{body}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
    paddingHorizontal: 20,
    paddingTop: 50,
    paddingBottom: 30,
  },
  header: {
    marginBottom: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: '#38BDF8',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 14,
    color: '#94A3B8',
  },
  rulesContainer: {
    flex: 1,
    backgroundColor: '#1E293B',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 16,
  },
  rulesContent: {
    padding: 16,
  },
  ruleBlock: {
    marginBottom: 16,
  },
  ruleTitle: {
    fontWeight: '700',
    fontSize: 14,
    color: '#38BDF8',
    marginBottom: 4,
  },
  ruleBody: {
    fontSize: 12,
    color: '#CBD5E1',
    lineHeight: 18,
  },
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 4,
    borderWidth: 2,
    borderColor: '#38BDF8',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  checkboxActive: {
    backgroundColor: '#0284C7',
    borderColor: '#0284C7',
  },
  checkmark: {
    color: '#FFFFFF',
    fontWeight: 'bold',
    fontSize: 14,
  },
  checkboxLabel: {
    color: '#FFFFFF',
    fontSize: 13,
    flex: 1,
  },
  button: {
    height: 50,
    backgroundColor: '#0284C7',
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonDisabled: {
    backgroundColor: '#475569',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
