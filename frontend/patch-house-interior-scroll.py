"""Street Legends frontend: house interior scrolls left/right.
Run from repo root: python3 frontend/patch-house-interior-scroll.py
Idempotent - safe to re-run.

BUG: the interior modal shows the room image with resizeMode="cover"
at screen width, so a wide landscape room gets its sides cropped off
— the player only ever sees a slice of the room.

FIX (House Interior Modal in index.tsx):
1. Wrap the interior image in a horizontal ScrollView.
2. Size the image to full screen height at its true aspect ratio
   (1280x853), so it is wider than the phone and the player swipes
   left/right to pan across the whole room.
3. LEAVE HOUSE button and house name stay as fixed overlays outside
   the ScrollView, so they never scroll away.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this.
"""
import sys
from pathlib import Path

PATH = Path("frontend/app/(tabs)/index.tsx")

IMPORT_OLD = """import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  ScrollView,
  Modal,
  Pressable,
  Image,
} from 'react-native';"""
IMPORT_NEW = """import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  ScrollView,
  Modal,
  Pressable,
  Image,
  Dimensions,
} from 'react-native';"""

IMAGE_OLD = """          {interiorHouse && (
            <Image
              source={HOUSE_IMAGES[interiorHouse.tier] || HOUSE_IMAGES.apartment}
              style={{ flex: 1, width: '100%' }}
              resizeMode="cover"
            />
          )}"""
IMAGE_NEW = """          {interiorHouse && (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={{ flex: 1 }}
            >
              <Image
                source={HOUSE_IMAGES[interiorHouse.tier] || HOUSE_IMAGES.apartment}
                style={{ height: Dimensions.get('window').height, aspectRatio: 1280 / 853 }}
                resizeMode="cover"
              />
            </ScrollView>
          )}"""

REPLACEMENTS = [
    (IMPORT_OLD, IMPORT_NEW, "Dimensions import added"),
    (IMAGE_OLD, IMAGE_NEW, "interior image now scrolls left/right"),
]


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from repo root.")
        sys.exit(1)
    src = PATH.read_text()
    for old, new, desc in REPLACEMENTS:
        if new in src:
            print(f"SKIP: {desc} (already applied)")
        elif src.count(old) == 1:
            src = src.replace(old, new, 1)
            print(f"OK: {desc}")
        else:
            print(f"WARNING: anchor matched {src.count(old)}x — {desc}")
    PATH.write_text(src)
    print("HOUSE_INTERIOR_SCROLL_OK")


if __name__ == "__main__":
    main()
