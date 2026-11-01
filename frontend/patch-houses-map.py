"""Street Legends frontend: houses on the map + Enter/Hide/Sell + interior.
Run from repo root: python3 frontend/patch-houses-map.py
Idempotent - safe to re-run.

WHAT IT DOES:
1. Map query fetches nearby houses (useMapQueries) and shows them as
   house icons on the map (GameMap).
2. Tapping a house icon opens its menu:
   - Anyone: house name + owner.
   - Owner only: ENTER (opens a full-screen view of the house picture
     they paid for — this is where furniture/items will go later),
     HIDE (player disappears from other players' maps) / UNHIDE,
     SELL (confirm, refunds HALF the price paid, house removed).
3. Sell refreshes the map + player cash immediately.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. Requires the houses backend patch + shop patch.
"""
import sys
from pathlib import Path

MAP_EDITS = [
    # --- useMapQueries.ts ---
    (
        Path("frontend/hooks/useMapQueries.ts"),
        "  spawnShootouts,\n  getPlayer,",
        "  spawnShootouts,\n  getNearbyHouses,\n  getPlayer,",
        "getNearbyHouses imported in map queries",
    ),
    (
        Path("frontend/hooks/useMapQueries.ts"),
        "  shootouts: any[];\n}",
        "  shootouts: any[];\n  houses: any[];\n}",
        "houses added to MapEntitiesData",
    ),
    (
        Path("frontend/hooks/useMapQueries.ts"),
        "        spawnShootouts(latitude, longitude, playerLevel),\n      ]);",
        "        spawnShootouts(latitude, longitude, playerLevel),\n        getNearbyHouses(latitude, longitude, 2000),\n      ]);",
        "houses fetched with map entities",
    ),
    (
        Path("frontend/hooks/useMapQueries.ts"),
        "        shootouts: results[13].status === 'fulfilled' ? results[13].value : [],",
        "        shootouts: results[13].status === 'fulfilled' ? results[13].value : [],\n        houses: results[14].status === 'fulfilled' ? results[14].value : [],",
        "houses returned with map entities",
    ),
    # --- GameMap.tsx ---
    (
        Path("frontend/components/GameMap.tsx"),
        "casino: '#d4af37' };",
        "casino: '#d4af37', house: '#FF9800' };",
        "house marker color added",
    ),
    (
        Path("frontend/components/GameMap.tsx"),
        "casino: '🎰' };",
        "casino: '🎰', house: '🏠' };",
        "house marker icon added",
    ),
]

INDEX_EDITS = [
    # API imports gain house actions
    (
        "  sendFriendRequest,\n} from '../../services/api';",
        "  sendFriendRequest,\n  toggleHouseHide,\n  sellHouse,\n} from '../../services/api';",
        "house action imports added",
    ),
    # House state + images (after selectedBank state)
    (
        "  const [selectedBank, setSelectedBank] = useState<any | null>(null);",
        """  const [selectedBank, setSelectedBank] = useState<any | null>(null);
  const [interiorHouse, setInteriorHouse] = useState<any | null>(null);
  const [houseHidden, setHouseHidden] = useState(false);

const HOUSE_IMAGES: Record<string, any> = {
  apartment: require('../../assets/houses/house-apartment.jpg'),
  cabin: require('../../assets/houses/house-cabin.jpg'),
  mansion: require('../../assets/houses/house-mansion.jpg'),
};""",
        "house menu state + images added",
    ),
    # Derive nearbyHouses
    (
        "  const nearbyBanks = useMemo(() => entitiesData?.banks || [], [entitiesData?.banks]);",
        "  const nearbyBanks = useMemo(() => entitiesData?.banks || [], [entitiesData?.banks]);\n  const nearbyHouses = useMemo(() => entitiesData?.houses || [], [entitiesData?.houses]);",
        "nearbyHouses derived",
    ),
    # Houses in map markers (after banks markers)
    (
        """    ...nearbyBanks.map((b) => ({
      id: b.id,
      coordinate: { latitude: b.latitude, longitude: b.longitude },
      type: 'bank' as const,
      name: b.name,
      icon: '🏦',
    })),""",
        """    ...nearbyBanks.map((b) => ({
      id: b.id,
      coordinate: { latitude: b.latitude, longitude: b.longitude },
      type: 'bank' as const,
      name: b.name,
      icon: '🏦',
    })),
    ...nearbyHouses.map((h) => ({
      id: h.id,
      coordinate: { latitude: h.latitude, longitude: h.longitude },
      type: 'house' as const,
      name: h.name,
      icon: '🏠',
    })),""",
        "houses added to map markers",
    ),
    # Marker press: house branch (before casino branch)
    (
        "    } else if (marker.type === 'casino') {",
        """    } else if (marker.type === 'house') {
      const house = nearbyHouses.find((h) => h.id === marker.id);
      if (house) {
        setSelectedMarker({ type: 'house', data: house });
        if (house.player_id === playerId && playerId) {
          getPlayer(playerId).then((p: any) => setHouseHidden(!!p.hidden_from_map)).catch(() => {});
        }
      }
    } else if (marker.type === 'casino') {""",
        "house marker press added",
    ),
    # handleMarkerPress deps gain nearbyHouses
    (
        "nearbyRunaways, nearbyPackageGrabs, nearbyShootouts]);",
        "nearbyRunaways, nearbyPackageGrabs, nearbyShootouts, nearbyHouses]);",
        "house added to marker-press deps",
    ),
    # House popup (after nightclub popup, before popup close)
    (
        "          )}\n        </View>\n      )}\n\n      {/* Territory Modal */}",
        """          )}
          {selectedMarker.type === 'house' && (
            <View>
              <View style={styles.popupHeader}>
                <Text style={{ fontSize: 28 }}>🏠</Text>
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name}</Text>
                  <Text style={styles.popupSubtitle}>Owned by {selectedMarker.data.player_name || 'someone'}</Text>
                </View>
              </View>
              {selectedMarker.data.player_id === playerId ? (
                <>
                  <TouchableOpacity
                    style={[styles.actionButton, { backgroundColor: '#4caf50' }]}
                    onPress={() => setInteriorHouse(selectedMarker.data)}
                  >
                    <Text style={styles.actionButtonText}>ENTER HOUSE</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.actionButton, { backgroundColor: '#666' }]}
                    onPress={async () => {
                      if (!playerId) return;
                      try {
                        const res = await toggleHouseHide(selectedMarker.data.id, playerId);
                        setHouseHidden(res.hidden);
                        showGameToast({ type: 'info', title: res.hidden ? 'Hidden' : 'Visible', message: res.hidden ? 'Other players can no longer see you on the map.' : 'Other players can see you again.', duration: 3000 });
                      } catch (err: any) {
                        showGameToast({ type: 'warning', title: 'Error', message: err?.response?.data?.detail || 'Could not toggle hide', duration: 3000 });
                      }
                    }}
                  >
                    <Text style={styles.actionButtonText}>{houseHidden ? 'UNHIDE ME' : 'HIDE ME FROM MAP'}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.actionButton, { backgroundColor: '#e74c3c' }]}
                    onPress={() => {
                      const refund = Math.floor((selectedMarker.data.price || 0) / 2);
                      Alert.alert('Sell House?', `Sell ${selectedMarker.data.name} for $${refund.toLocaleString()} (half of what you paid)?`, [
                        { text: 'Keep It', style: 'cancel' },
                        { text: 'Sell', style: 'destructive', onPress: async () => {
                          if (!playerId) return;
                          try {
                            const res = await sellHouse(selectedMarker.data.id, playerId);
                            showGameToast({ type: 'success', title: 'House Sold', message: `+$${res.refund.toLocaleString()} cash back.`, duration: 3000 });
                            setSelectedMarker(null);
                            refetchEntities();
                            refetchPlayer();
                          } catch (err: any) {
                            showGameToast({ type: 'warning', title: 'Error', message: err?.response?.data?.detail || 'Could not sell', duration: 3000 });
                          }
                        } },
                      ]);
                    }}
                  >
                    <Text style={styles.actionButtonText}>SELL FOR ${Math.floor((selectedMarker.data.price || 0) / 2).toLocaleString()}</Text>
                  </TouchableOpacity>
                </>
              ) : (
                <Text style={styles.popupSubtitle}>This house belongs to another player.</Text>
              )}
            </View>
          )}
        </View>
      )}

      {/* House Interior Modal */}
      <Modal
        visible={!!interiorHouse}
        animationType="slide"
        onRequestClose={() => setInteriorHouse(null)}
      >
        <View style={{ flex: 1, backgroundColor: '#000' }}>
          {interiorHouse && (
            <Image
              source={HOUSE_IMAGES[interiorHouse.tier] || HOUSE_IMAGES.apartment}
              style={{ flex: 1, width: '100%' }}
              resizeMode="cover"
            />
          )}
          <TouchableOpacity
            style={{ position: 'absolute', top: 48, right: 16, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 }}
            onPress={() => setInteriorHouse(null)}
          >
            <Text style={{ color: '#fff', fontWeight: '800' }}>LEAVE HOUSE ✕</Text>
          </TouchableOpacity>
          <View style={{ position: 'absolute', bottom: 32, left: 16, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 12, paddingVertical: 8, paddingHorizontal: 14 }}>
            <Text style={{ color: '#fff', fontWeight: '800', fontSize: 16 }}>{interiorHouse?.name || ''}</Text>
          </View>
        </View>
      </Modal>

      {/* Territory Modal */}""",
        "house popup + interior modal added",
    ),
]


def apply_edits(path, edits):
    if not path.exists():
        print(f"ERROR: {path} not found.")
        return False
    src = path.read_text()
    ok = True
    for old, new, desc in edits:
        if new in src:
            print(f"SKIP ({path.name}): {desc} (already applied)")
            continue
        n = src.count(old)
        if n >= 1:
            src = src.replace(old, new, 1)
            print(f"OK ({path.name}): {desc}")
        else:
            print(f"WARNING ({path.name}): anchor not found — {desc}")
            ok = False
    path.write_text(src)
    return ok


def main():
    # Group MAP_EDITS by file
    by_file = {}
    for path, old, new, desc in MAP_EDITS:
        by_file.setdefault(path, []).append((old, new, desc))
    all_ok = True
    for path, edits in by_file.items():
        if not apply_edits(path, edits):
            all_ok = False
    index_path = Path("frontend/app/(tabs)/index.tsx")
    if not apply_edits(index_path, INDEX_EDITS):
        all_ok = False
    if not all_ok:
        print("NOTE: some anchors missed — check warnings above.")
    print("HOUSES_MAP_OK")


if __name__ == "__main__":
    main()
