import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function PrivacyPolicyScreen() {
  const router = useRouter();

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );

  const Paragraph = ({ children }: { children: React.ReactNode }) => (
    <Text style={styles.paragraph}>{children}</Text>
  );

  const BulletPoint = ({ children }: { children: React.ReactNode }) => (
    <View style={styles.bulletContainer}>
      <Text style={styles.bullet}>•</Text>
      <Text style={styles.bulletText}>{children}</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.backButton} 
          onPress={() => router.back()}
          accessibilityLabel="Go back"
          accessibilityRole="button"
        >
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Privacy Policy</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView 
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={true}
      >
        {/* App Title */}
        <View style={styles.titleContainer}>
          <Text style={styles.appName}>Street Legends</Text>
          <Text style={styles.lastUpdated}>Last Updated: June 2026</Text>
        </View>

        {/* Introduction */}
        <Section title="Introduction">
          <Paragraph>
            Welcome to Street Legends! Your privacy is important to us. This Privacy Policy explains 
            how we collect, use, and protect your information when you use our GPS-based RPG mobile 
            application.
          </Paragraph>
          <Paragraph>
            By using Street Legends, you agree to the collection and use of information in accordance 
            with this policy.
          </Paragraph>
        </Section>

        {/* Information We Collect */}
        <Section title="Information We Collect">
          <Paragraph>
            We collect the following types of information to provide and improve our services:
          </Paragraph>

          <Text style={styles.subheading}>1. Location Data</Text>
          <Paragraph>
            Street Legends uses your device's location to power core gameplay features including:
          </Paragraph>
          <BulletPoint>Discovering and capturing territories on the map</BulletPoint>
          <BulletPoint>Finding nearby missions, enemies, and points of interest</BulletPoint>
          <BulletPoint>Tracking fitness activities (step counting) for in-game rewards</BulletPoint>
          <Paragraph>
            Location data is collected only while you are actively using the app or when background 
            location is enabled for fitness tracking features you have opted into.
          </Paragraph>

          <Text style={styles.subheading}>2. Profile Pictures</Text>
          <Paragraph>
            If you choose to upload a profile picture for your character, we store this image on our 
            secure servers. Profile pictures may be visible to other players when you capture territories 
            or appear on leaderboards.
          </Paragraph>

          <Text style={styles.subheading}>3. Account Information</Text>
          <Paragraph>
            When you create a character, we collect:
          </Paragraph>
          <BulletPoint>Username/Character name</BulletPoint>
          <BulletPoint>Character customization data (stats, skills, inventory)</BulletPoint>
          <BulletPoint>Game progress and achievements</BulletPoint>
          <BulletPoint>Device identifier for account association</BulletPoint>
        </Section>

        {/* How We Use Your Information */}
        <Section title="How We Use Your Information">
          <Paragraph>
            We use the collected information for the following purposes:
          </Paragraph>
          <BulletPoint>To provide and maintain the game experience</BulletPoint>
          <BulletPoint>To enable location-based gameplay features</BulletPoint>
          <BulletPoint>To save your game progress and character data</BulletPoint>
          <BulletPoint>To display your profile to other players in multiplayer features</BulletPoint>
          <BulletPoint>To track fitness activities and award in-game rewards</BulletPoint>
          <BulletPoint>To improve and optimize the app experience</BulletPoint>
        </Section>

        {/* Data Sharing */}
        <Section title="Data Sharing & Third Parties">
          <View style={styles.highlightBox}>
            <Ionicons name="shield-checkmark" size={24} color="#4ade80" />
            <Text style={styles.highlightText}>
              We do NOT sell your personal data to third parties.
            </Text>
          </View>
          <Paragraph>
            Your data is never sold, rented, or traded to advertisers, data brokers, or any other 
            third parties for their marketing purposes.
          </Paragraph>
          <Paragraph>
            We may share limited information only in the following circumstances:
          </Paragraph>
          <BulletPoint>
            With service providers who help us operate the app (e.g., cloud hosting), under strict 
            confidentiality agreements
          </BulletPoint>
          <BulletPoint>
            If required by law or to protect the rights and safety of our users
          </BulletPoint>
          <BulletPoint>
            Aggregated, anonymized data for analytics (which cannot identify you personally)
          </BulletPoint>
        </Section>

        {/* Data Security */}
        <Section title="Data Security">
          <Paragraph>
            We implement industry-standard security measures to protect your data, including:
          </Paragraph>
          <BulletPoint>Encrypted data transmission (HTTPS/TLS)</BulletPoint>
          <BulletPoint>Secure cloud storage infrastructure</BulletPoint>
          <BulletPoint>Regular security assessments</BulletPoint>
          <Paragraph>
            While we strive to protect your information, no method of electronic transmission or 
            storage is 100% secure. We cannot guarantee absolute security.
          </Paragraph>
        </Section>

        {/* Data Retention */}
        <Section title="Data Retention">
          <Paragraph>
            We retain your data for as long as your account is active or as needed to provide you 
            with our services. If you wish to delete your account and associated data, please 
            contact us.
          </Paragraph>
        </Section>

        {/* Your Rights */}
        <Section title="Your Rights">
          <Paragraph>
            You have the right to:
          </Paragraph>
          <BulletPoint>Access the personal data we hold about you</BulletPoint>
          <BulletPoint>Request correction of inaccurate data</BulletPoint>
          <BulletPoint>Request deletion of your account and data</BulletPoint>
          <BulletPoint>Disable location services through your device settings</BulletPoint>
          <BulletPoint>Opt out of fitness tracking features</BulletPoint>
        </Section>

        {/* Children's Privacy */}
        <Section title="Children's Privacy">
          <Paragraph>
            Street Legends is not intended for children under 13 years of age. We do not knowingly 
            collect personal information from children under 13. If you are a parent or guardian 
            and believe your child has provided us with personal information, please contact us.
          </Paragraph>
        </Section>

        {/* Changes to Policy */}
        <Section title="Changes to This Policy">
          <Paragraph>
            We may update this Privacy Policy from time to time. We will notify you of any changes 
            by posting the new Privacy Policy on this page and updating the "Last Updated" date.
          </Paragraph>
        </Section>

        {/* Contact */}
        <Section title="Contact Us">
          <Paragraph>
            If you have any questions about this Privacy Policy or our data practices, please 
            contact us through the app's support feature or reach out to our development team.
          </Paragraph>
        </Section>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>© 2026 Street Legends. All rights reserved.</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0a',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#1a1a1a',
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  backButton: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: '#333',
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  headerSpacer: {
    width: 44,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  titleContainer: {
    alignItems: 'center',
    marginBottom: 24,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  appName: {
    fontSize: 28,
    fontWeight: '800',
    color: '#f59e0b',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 2,
  },
  lastUpdated: {
    fontSize: 14,
    color: '#888',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#f59e0b',
    marginBottom: 12,
  },
  subheading: {
    fontSize: 16,
    fontWeight: '600',
    color: '#e5e5e5',
    marginTop: 12,
    marginBottom: 8,
  },
  paragraph: {
    fontSize: 15,
    lineHeight: 24,
    color: '#d1d5db',
    marginBottom: 12,
  },
  bulletContainer: {
    flexDirection: 'row',
    marginBottom: 8,
    paddingLeft: 8,
  },
  bullet: {
    fontSize: 15,
    color: '#f59e0b',
    marginRight: 10,
    lineHeight: 24,
  },
  bulletText: {
    flex: 1,
    fontSize: 15,
    lineHeight: 24,
    color: '#d1d5db',
  },
  highlightBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a2e1a',
    borderWidth: 1,
    borderColor: '#4ade80',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    gap: 12,
  },
  highlightText: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: '#4ade80',
    lineHeight: 22,
  },
  footer: {
    marginTop: 24,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#333',
    alignItems: 'center',
  },
  footerText: {
    fontSize: 13,
    color: '#666',
  },
});
