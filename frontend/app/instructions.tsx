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

type IconName = React.ComponentProps<typeof Ionicons>['name'];

export default function InstructionsScreen() {
  const router = useRouter();

  const Section = ({ 
    icon, 
    iconColor, 
    title, 
    children 
  }: { 
    icon: IconName; 
    iconColor: string; 
    title: string; 
    children: React.ReactNode 
  }) => (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <View style={[styles.iconContainer, { backgroundColor: iconColor + '20' }]}>
          <Ionicons name={icon} size={24} color={iconColor} />
        </View>
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      <View style={styles.sectionContent}>
        {children}
      </View>
    </View>
  );

  const Step = ({ number, text }: { number: number; text: string }) => (
    <View style={styles.stepContainer}>
      <View style={styles.stepNumber}>
        <Text style={styles.stepNumberText}>{number}</Text>
      </View>
      <Text style={styles.stepText}>{text}</Text>
    </View>
  );

  const Tip = ({ children }: { children: React.ReactNode }) => (
    <View style={styles.tipContainer}>
      <Ionicons name="bulb" size={16} color="#f59e0b" />
      <Text style={styles.tipText}>{children}</Text>
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
        <Text style={styles.headerTitle}>How to Play</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView 
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={true}
      >
        {/* Title */}
        <View style={styles.titleContainer}>
          <Text style={styles.appName}>Street Legends</Text>
          <Text style={styles.subtitle}>Game Guide</Text>
        </View>

        {/* Introduction */}
        <View style={styles.introBox}>
          <Text style={styles.introText}>
            Welcome to Street Legends! Build your empire by conquering real-world territories, 
            battling rivals, and becoming the ultimate street legend. This guide will help you 
            master the streets.
          </Text>
        </View>

        {/* Creating Your Character */}
        <Section icon="person-add" iconColor="#4ade80" title="Creating Your Character">
          <Text style={styles.paragraph}>
            Your journey begins with creating a unique character. Choose wisely - your class 
            determines your playstyle!
          </Text>
          
          <Step number={1} text="Enter a unique character name that will be your identity on the streets." />
          <Step number={2} text="Select your character class - each has different strengths:" />
          
          <View style={styles.classGrid}>
            <View style={styles.classItem}>
              <Text style={styles.className}>🔫 Street Soldier</Text>
              <Text style={styles.classDesc}>Balanced fighter with high attack & defense</Text>
            </View>
            <View style={styles.classItem}>
              <Text style={styles.className}>💻 Hacker</Text>
              <Text style={styles.classDesc}>Tech genius with high speed & luck</Text>
            </View>
            <View style={styles.classItem}>
              <Text style={styles.className}>💪 Enforcer</Text>
              <Text style={styles.classDesc}>Powerhouse with max attack & health</Text>
            </View>
            <View style={styles.classItem}>
              <Text style={styles.className}>👻 Ghost</Text>
              <Text style={styles.classDesc}>Assassin with critical hits & evasion</Text>
            </View>
          </View>

          <Step number={3} text="Confirm your choice and enter the game world!" />
          
          <Tip>You can upload a profile picture later from the Character tab to personalize your avatar!</Tip>
        </Section>

        {/* Capturing Territory */}
        <Section icon="map" iconColor="#3b82f6" title="Capturing Territory">
          <Text style={styles.paragraph}>
            The map shows your real-world location. Territories appear as colored zones you can 
            claim as your own turf!
          </Text>
          
          <Step number={1} text="Open the Map tab and allow location access to see territories near you." />
          <Step number={2} text="Look for unclaimed territories (gray) or rival territories (colored)." />
          <Step number={3} text="Move physically to get within range of a territory (about 100 meters)." />
          <Step number={4} text="Tap on the territory marker to view its details." />
          <Step number={5} text="Press 'CAPTURE' to claim it as your own!" />
          
          <View style={styles.infoBox}>
            <Ionicons name="flag" size={20} color="#f59e0b" />
            <Text style={styles.infoText}>
              Captured territories generate passive income over time. The more you own, 
              the richer you become!
            </Text>
          </View>
          
          <Tip>Your profile picture will appear on territories you capture, showing others who owns it!</Tip>
        </Section>

        {/* Battling Rivals */}
        <Section icon="flash" iconColor="#ef4444" title="Battling Rivals">
          <Text style={styles.paragraph}>
            Enemies and rival players roam the streets. Defeat them to earn XP, cash, and loot!
          </Text>
          
          <Step number={1} text="Find enemy markers (skulls) on the map - they spawn based on your level." />
          <Step number={2} text="Tap an enemy to see their stats and level." />
          <Step number={3} text="Press 'FIGHT' to enter turn-based combat." />
          <Step number={4} text="Choose your actions each turn: Attack, use Skills, or Defend." />
          <Step number={5} text="Defeat the enemy before your health reaches zero!" />
          
          <View style={styles.combatTips}>
            <Text style={styles.combatTipsTitle}>Combat Tips:</Text>
            <Text style={styles.combatTip}>• <Text style={styles.highlight}>Attack</Text> - Basic damage based on your attack stat</Text>
            <Text style={styles.combatTip}>• <Text style={styles.highlight}>Skills</Text> - Powerful abilities with energy costs</Text>
            <Text style={styles.combatTip}>• <Text style={styles.highlight}>Defend</Text> - Reduce incoming damage by 50%</Text>
          </View>
          
          <Tip>Equip up to 4 skills from your Character tab to use special moves in battle!</Tip>
        </Section>

        {/* Implants & Neural Boosters */}
        <Section icon="hardware-chip" iconColor="#a855f7" title="Implants & Neural Boosters">
          <Text style={styles.paragraph}>
            Visit the Health Store to permanently enhance your character with cybernetic upgrades!
          </Text>
          
          <View style={styles.upgradeType}>
            <Text style={styles.upgradeTitle}>🧠 Neural Implants</Text>
            <Text style={styles.upgradeDesc}>
              Permanent stat increases that boost your base attributes. Once installed, 
              they're part of you forever!
            </Text>
            <Text style={styles.upgradeExample}>
              Example: "Cortex Enhancer" - +5% Attack permanently
            </Text>
          </View>
          
          <View style={styles.upgradeType}>
            <Text style={styles.upgradeTitle}>💉 Boosters</Text>
            <Text style={styles.upgradeDesc}>
              Powerful permanent upgrades that enhance specific stats by a percentage. 
              Stack them for maximum effect!
            </Text>
            <Text style={styles.upgradeExample}>
              Example: "Adrenaline Surge" - +10% Speed permanently
            </Text>
          </View>

          <Step number={1} text="Navigate to the Map and find a Health Store marker (green cross)." />
          <Step number={2} text="Browse available stims and consumables." />
          <Step number={3} text="Purchase items using your hard-earned cash." />
          <Step number={4} text="Use stims from Inventory for instant HP/Energy boosts!" />
          
          <Tip>Health and Energy Stims give temporary boosts that can exceed your max stats!</Tip>
        </Section>

        {/* Leveling Up */}
        <Section icon="trending-up" iconColor="#f59e0b" title="Leveling Up">
          <Text style={styles.paragraph}>
            Gain experience (XP) to level up and become stronger. Higher levels unlock better 
            enemies, gear, and skills!
          </Text>
          
          <View style={styles.xpSources}>
            <Text style={styles.xpSourcesTitle}>Ways to Earn XP:</Text>
            <View style={styles.xpItem}>
              <Ionicons name="skull" size={18} color="#ef4444" />
              <Text style={styles.xpItemText}>Defeating enemies in combat</Text>
            </View>
            <View style={styles.xpItem}>
              <Ionicons name="flag" size={18} color="#3b82f6" />
              <Text style={styles.xpItemText}>Capturing new territories</Text>
            </View>
            <View style={styles.xpItem}>
              <Ionicons name="checkbox" size={18} color="#4ade80" />
              <Text style={styles.xpItemText}>Completing missions</Text>
            </View>
            <View style={styles.xpItem}>
              <Ionicons name="footsteps" size={18} color="#f59e0b" />
              <Text style={styles.xpItemText}>Fitness rewards (step tracking)</Text>
            </View>
          </View>
          
          <View style={styles.levelBenefits}>
            <Text style={styles.benefitsTitle}>Level Up Benefits:</Text>
            <Text style={styles.benefitItem}>✓ Increased base stats</Text>
            <Text style={styles.benefitItem}>✓ Access to stronger enemies & bosses</Text>
            <Text style={styles.benefitItem}>✓ Better equipment drops</Text>
            <Text style={styles.benefitItem}>✓ New skills unlock at odd levels (1, 3, 5...)</Text>
            <Text style={styles.benefitItem}>✓ Higher tier shops and content</Text>
          </View>
          
          <Tip>Check your XP progress on the Character tab - the bar shows how close you are to the next level!</Tip>
        </Section>

        {/* Quick Tips */}
        <Section icon="sparkles" iconColor="#ec4899" title="Pro Tips">
          <View style={styles.proTipsList}>
            <View style={styles.proTip}>
              <Text style={styles.proTipNumber}>1</Text>
              <Text style={styles.proTipText}>
                <Text style={styles.highlight}>Equip your gear!</Text> Check your inventory and equip 
                weapons, armor, and accessories for stat boosts.
              </Text>
            </View>
            <View style={styles.proTip}>
              <Text style={styles.proTipNumber}>2</Text>
              <Text style={styles.proTipText}>
                <Text style={styles.highlight}>Visit Gun Shops</Text> to buy new weapons, armor, and 
                skills to expand your arsenal.
              </Text>
            </View>
            <View style={styles.proTip}>
              <Text style={styles.proTipNumber}>3</Text>
              <Text style={styles.proTipText}>
                <Text style={styles.highlight}>Complete Missions</Text> for bonus rewards - check the 
                Missions tab for available jobs.
              </Text>
            </View>
            <View style={styles.proTip}>
              <Text style={styles.proTipNumber}>4</Text>
              <Text style={styles.proTipText}>
                <Text style={styles.highlight}>Rob Banks</Text> for high-risk, high-reward heists - 
                but beware, you might get caught!
              </Text>
            </View>
            <View style={styles.proTip}>
              <Text style={styles.proTipNumber}>5</Text>
              <Text style={styles.proTipText}>
                <Text style={styles.highlight}>Walk in real life</Text> to earn fitness rewards and 
                discover new territories!
              </Text>
            </View>
          </View>
        </Section>

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>Now get out there and become a Street Legend!</Text>
          <TouchableOpacity 
            style={styles.startButton}
            onPress={() => router.back()}
          >
            <Text style={styles.startButtonText}>Start Playing</Text>
            <Ionicons name="arrow-forward" size={20} color="#000" />
          </TouchableOpacity>
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
    marginBottom: 20,
  },
  appName: {
    fontSize: 32,
    fontWeight: '800',
    color: '#f59e0b',
    textTransform: 'uppercase',
    letterSpacing: 2,
  },
  subtitle: {
    fontSize: 16,
    color: '#888',
    marginTop: 4,
  },
  introBox: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    borderLeftWidth: 4,
    borderLeftColor: '#f59e0b',
  },
  introText: {
    fontSize: 15,
    lineHeight: 24,
    color: '#d1d5db',
  },
  section: {
    marginBottom: 28,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 12,
  },
  iconContainer: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    flex: 1,
  },
  sectionContent: {
    paddingLeft: 8,
  },
  paragraph: {
    fontSize: 15,
    lineHeight: 24,
    color: '#9ca3af',
    marginBottom: 16,
  },
  stepContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
    gap: 12,
  },
  stepNumber: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#f59e0b',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepNumberText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#000',
  },
  stepText: {
    flex: 1,
    fontSize: 15,
    lineHeight: 22,
    color: '#d1d5db',
    paddingTop: 3,
  },
  tipContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#2d2510',
    borderRadius: 10,
    padding: 12,
    marginTop: 12,
    gap: 10,
  },
  tipText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    color: '#fcd34d',
  },
  classGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginVertical: 12,
  },
  classItem: {
    width: '48%',
    backgroundColor: '#1a1a1a',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  className: {
    fontSize: 14,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  classDesc: {
    fontSize: 12,
    color: '#888',
    lineHeight: 16,
  },
  infoBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#1a1a1a',
    borderRadius: 10,
    padding: 14,
    marginTop: 12,
    gap: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  infoText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    color: '#d1d5db',
  },
  combatTips: {
    backgroundColor: '#1a1010',
    borderRadius: 10,
    padding: 14,
    marginTop: 12,
    borderWidth: 1,
    borderColor: '#ef444440',
  },
  combatTipsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ef4444',
    marginBottom: 8,
  },
  combatTip: {
    fontSize: 14,
    color: '#d1d5db',
    lineHeight: 22,
  },
  highlight: {
    color: '#f59e0b',
    fontWeight: '600',
  },
  upgradeType: {
    backgroundColor: '#1a1a1a',
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  upgradeTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 6,
  },
  upgradeDesc: {
    fontSize: 14,
    lineHeight: 20,
    color: '#9ca3af',
    marginBottom: 8,
  },
  upgradeExample: {
    fontSize: 13,
    color: '#a855f7',
    fontStyle: 'italic',
  },
  xpSources: {
    backgroundColor: '#1a1a1a',
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  xpSourcesTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#f59e0b',
    marginBottom: 10,
  },
  xpItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
  },
  xpItemText: {
    fontSize: 14,
    color: '#d1d5db',
  },
  levelBenefits: {
    backgroundColor: '#101a10',
    borderRadius: 10,
    padding: 14,
    borderWidth: 1,
    borderColor: '#4ade8040',
  },
  benefitsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4ade80',
    marginBottom: 8,
  },
  benefitItem: {
    fontSize: 14,
    color: '#d1d5db',
    lineHeight: 24,
  },
  proTipsList: {
    gap: 12,
  },
  proTip: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#1a1a1a',
    borderRadius: 10,
    padding: 14,
    gap: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  proTipNumber: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#ec4899',
    textAlign: 'center',
    lineHeight: 24,
    fontSize: 13,
    fontWeight: '700',
    color: '#fff',
    overflow: 'hidden',
  },
  proTipText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    color: '#d1d5db',
  },
  footer: {
    marginTop: 20,
    paddingTop: 24,
    borderTopWidth: 1,
    borderTopColor: '#333',
    alignItems: 'center',
  },
  footerText: {
    fontSize: 16,
    color: '#888',
    marginBottom: 16,
    textAlign: 'center',
  },
  startButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f59e0b',
    borderRadius: 12,
    paddingHorizontal: 32,
    paddingVertical: 14,
    gap: 8,
  },
  startButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#000',
  },
});
