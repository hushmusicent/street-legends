import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface HealthBarProps {
  current: number;
  max: number;
  label?: string;
  color?: string;
  height?: number;
}

export const HealthBar: React.FC<HealthBarProps> = ({
  current,
  max,
  label,
  color = '#e74c3c',
  height = 20,
}) => {
  const percentage = Math.max(0, Math.min(100, (current / max) * 100));
  
  return (
    <View style={styles.container}>
      {label && <Text style={styles.label}>{label}</Text>}
      <View style={[styles.barContainer, { height }]}>
        <View
          style={[
            styles.bar,
            {
              width: `${percentage}%`,
              backgroundColor: color,
            },
          ]}
        />
        <Text style={styles.text}>
          {current} / {max}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  label: {
    color: '#fff',
    fontSize: 12,
    marginBottom: 4,
    fontWeight: '600',
  },
  barContainer: {
    backgroundColor: '#333',
    borderRadius: 4,
    overflow: 'hidden',
    position: 'relative',
    justifyContent: 'center',
  },
  bar: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    borderRadius: 4,
  },
  text: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
    textAlign: 'center',
    textShadowColor: '#000',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
});
