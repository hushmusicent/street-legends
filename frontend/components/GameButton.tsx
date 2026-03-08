import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator, ViewStyle, TextStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface GameButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'success';
  icon?: keyof typeof Ionicons.glyphMap;
  disabled?: boolean;
  loading?: boolean;
  size?: 'small' | 'medium' | 'large';
  style?: ViewStyle;
}

export const GameButton: React.FC<GameButtonProps> = ({
  title,
  onPress,
  variant = 'primary',
  icon,
  disabled = false,
  loading = false,
  size = 'medium',
  style,
}) => {
  const variantStyles: Record<string, { bg: string; text: string }> = {
    primary: { bg: '#e74c3c', text: '#fff' },
    secondary: { bg: '#34495e', text: '#fff' },
    danger: { bg: '#c0392b', text: '#fff' },
    success: { bg: '#27ae60', text: '#fff' },
  };
  
  const sizeStyles: Record<string, { padding: number; fontSize: number; iconSize: number }> = {
    small: { padding: 8, fontSize: 12, iconSize: 16 },
    medium: { padding: 14, fontSize: 16, iconSize: 20 },
    large: { padding: 18, fontSize: 18, iconSize: 24 },
  };
  
  const colors = variantStyles[variant];
  const sizes = sizeStyles[size];
  
  return (
    <TouchableOpacity
      style={[
        styles.button,
        {
          backgroundColor: disabled ? '#555' : colors.bg,
          paddingVertical: sizes.padding,
          paddingHorizontal: sizes.padding * 1.5,
        },
        style,
      ]}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.8}
    >
      {loading ? (
        <ActivityIndicator color={colors.text} size="small" />
      ) : (
        <>
          {icon && (
            <Ionicons
              name={icon}
              size={sizes.iconSize}
              color={disabled ? '#888' : colors.text}
              style={styles.icon}
            />
          )}
          <Text
            style={[
              styles.text,
              {
                color: disabled ? '#888' : colors.text,
                fontSize: sizes.fontSize,
              },
            ]}
          >
            {title}
          </Text>
        </>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  icon: {
    marginRight: 8,
  },
  text: {
    fontWeight: 'bold',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
});
