import React, { useState } from 'react';
import {
  View,
  Text,
  Image,
  Modal,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Dimensions,
  NativeScrollEvent,
  NativeSyntheticEvent,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const { width: SCREEN_W } = Dimensions.get('window');
const CARD_W = SCREEN_W * 0.9;

const BUNDLES = [
  { name: '$100,000 Cash', price: '$10.00' },
  { name: '$250,000 Cash', price: '$25.00' },
  { name: '$500,000 Pack', price: '$50.00' },
  { name: '$1,000,000 Pack', price: '$100.00' },
];

// Swipeable promo popup shown at game start, over the map.
// PROMO_POPUP_V6: explicit width + height (CARD_W square) instead of
// aspectRatio - the aspectRatio box was rendering wider than the card
// and cropping the right side off (blue Energy can cut off). The
// user's 648x648 pictures are square, so the box is square, whole
// picture shown (contain), centered. Page 1 is the Recovery Ward
// picture (God Potions), page 2 the Bonus art.
// Page 1: God Potions (Infinite Health + Infinite Energy), $1 each.
// Page 2: Bonus Bundles and their prices.
// X closes it. Shows once per app launch (state resets on restart).
export default function PromoPopup() {
  const [visible, setVisible] = useState(true);
  const [page, setPage] = useState(0);

  if (!visible) return null;

  const onScrollEnd = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const x = e.nativeEvent.contentOffset.x;
    const p = Math.round(x / CARD_W);
    if (p !== page) setPage(p);
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={() => setVisible(false)}
    >
      <View style={styles.overlay}>
        <View style={styles.card}>
          <TouchableOpacity
            style={styles.closeBtn}
            onPress={() => setVisible(false)}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="close" size={24} color="#fff" />
          </TouchableOpacity>

          <ScrollView
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onMomentumScrollEnd={onScrollEnd}
            style={styles.pager}
          >
            {/* Page 1: God Potions, $1 each */}
            <View style={styles.page}>
              <Image
                source={require('../assets/promo-mk.jpg')}
                style={styles.image}
                resizeMode="contain"
              />
              <Text style={styles.title}>GOD POTIONS</Text>
              <Text style={styles.price}>$1 EACH</Text>
              <Text style={styles.sub}>
                Infinite Health — take no damage for 1 hour. Infinite Energy — skills cost no energy for 1 hour. Grab them in the Shop.
              </Text>
            </View>

            {/* Page 2: Bundles and prices */}
            <View style={styles.page}>
              <Image
                source={require('../assets/promo-bundles.jpg')}
                style={styles.image}
                resizeMode="contain"
              />
              <Text style={styles.title}>BONUS BUNDLES</Text>
              {BUNDLES.map((b) => (
                <View key={b.name} style={styles.bundleRow}>
                  <Text style={styles.bundleName}>{b.name}</Text>
                  <Text style={styles.bundlePrice}>{b.price}</Text>
                </View>
              ))}
              <Text style={styles.sub}>
                Real money. Find them in the Shop, Bonus tab.
              </Text>
            </View>
          </ScrollView>

          <View style={styles.dots}>
            <View style={[styles.dot, page === 0 && styles.dotActive]} />
            <View style={[styles.dot, page === 1 && styles.dotActive]} />
          </View>
          <Text style={styles.swipeHint}>Swipe for more</Text>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.75)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  card: {
    width: CARD_W,
    backgroundColor: '#141414',
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#333',
  },
  closeBtn: {
    position: 'absolute',
    top: 10,
    right: 10,
    zIndex: 10,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(0,0,0,0.65)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pager: {
    width: CARD_W,
  },
  page: {
    width: CARD_W,
    paddingBottom: 12,
    alignItems: 'center',
  },
  image: {
    width: CARD_W,
    height: CARD_W,
    alignSelf: 'center',
  },
  title: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '900',
    textAlign: 'center',
    marginTop: 10,
    letterSpacing: 0.5,
  },
  price: {
    color: '#f39c12',
    fontSize: 28,
    fontWeight: '900',
    textAlign: 'center',
    marginTop: 4,
  },
  sub: {
    color: '#bbb',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 6,
    marginHorizontal: 20,
    lineHeight: 18,
  },
  bundleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginHorizontal: 24,
    marginTop: 8,
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: '#222',
  },
  bundleName: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  bundlePrice: {
    color: '#f39c12',
    fontSize: 16,
    fontWeight: '900',
  },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 2,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#555',
    marginHorizontal: 4,
  },
  dotActive: {
    backgroundColor: '#f39c12',
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  swipeHint: {
    color: '#888',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 6,
    marginBottom: 10,
  },
});
