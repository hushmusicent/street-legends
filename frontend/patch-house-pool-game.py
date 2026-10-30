"""Street Legends frontend: playable pool game first (menu comes later).
Run from repo root: python3 frontend/patch-house-pool-game.py
Idempotent - safe to re-run.

USER DIRECTION (2026-10-30): "Make the game first."
So this patch ships ONLY the game, wired the simplest way: tap the
pool table in the room and the game opens directly. No menu yet.
Once the game plays right, the next patch adds the Play / Move /
Sell menu on tap (PLAY will open this same game; MOVE and SELL
already work today via drag-to-move and the dropdown row).

THE GAME (single player, for fun, no payout):
- Top-down table, cue ball + 7 object balls in a rack.
- Pull back anywhere on the table and release to shoot; the aim
  line shows the shot direction and power.
- Balls roll with friction, bounce off cushions, collide, and drop
  into the 6 pockets. Pocket all 7 to win.
- Pocketing the cue ball is a foul: it respots and play continues.
- RESTART resets the table; LEAVE TABLE closes the game.
- The component lives at top level (not inside MapScreen) so it
  doesn't remount and reset on every parent render. It uses only
  hooks/components already imported in index.tsx (useState,
  useRef, PanResponder, Modal, View, Text, TouchableOpacity,
  Dimensions) — no new imports needed.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this. No backend
change needed.
"""
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")

STATE_OLD = "  const [interiorHouse, setInteriorHouse] = useState<any | null>(null);"
STATE_NEW = """  const [interiorHouse, setInteriorHouse] = useState<any | null>(null);
  const [poolGameOpen, setPoolGameOpen] = useState(false);"""

MAPSCREEN_ANCHOR = "export default function MapScreen() {"

POOL_GAME = """
const PoolGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {
  const TABLE_W = Math.min(340, Dimensions.get('window').width - 32);
  const TABLE_H = 200;
  const BALL_R = 9;
  const POCKET_R = 15;
  const POCKETS = [
    { x: 6, y: 6 }, { x: TABLE_W / 2, y: 2 }, { x: TABLE_W - 6, y: 6 },
    { x: 6, y: TABLE_H - 6 }, { x: TABLE_W / 2, y: TABLE_H - 2 }, { x: TABLE_W - 6, y: TABLE_H - 6 },
  ];
  const COLORS = ['#e53935', '#1e88e5', '#fdd835', '#43a047', '#8e24aa', '#fb8c00', '#111111'];
  const makeBalls = () => {
    const balls: any[] = [{ id: 'cue', x: TABLE_W * 0.25, y: TABLE_H / 2, vx: 0, vy: 0, color: '#ffffff', pocketed: false }];
    const ax = TABLE_W * 0.68;
    const ay = TABLE_H / 2;
    const gap = BALL_R * 2 + 2;
    const rows = [1, 2, 3, 1];
    let idx = 0;
    rows.forEach((count, r) => {
      for (let i = 0; i < count; i++) {
        if (idx >= COLORS.length) break;
        balls.push({ id: 'b' + idx, x: ax + r * gap * 0.866, y: ay + (i - (count - 1) / 2) * gap, vx: 0, vy: 0, color: COLORS[idx], pocketed: false });
        idx++;
      }
    });
    return balls;
  };
  const [balls, setBalls] = useState<any[]>(() => makeBalls());
  const ballsRef = useRef(balls);
  ballsRef.current = balls;
  const [moving, setMoving] = useState(false);
  const movingRef = useRef(false);
  const [won, setWon] = useState(false);
  const wonRef = useRef(false);
  const [message, setMessage] = useState('Pull back on the table and release to shoot. Clear all 7 balls to win!');
  const [aim, setAim] = useState<any>(null);
  const aimRef = useRef<any>(null);
  const timerRef = useRef<any>(null);

  const step = () => {
    const bs = ballsRef.current.map((b: any) => ({ ...b }));
    let anyMoving = false;
    for (const b of bs) {
      if (b.pocketed) continue;
      b.x += b.vx;
      b.y += b.vy;
      b.vx *= 0.985;
      b.vy *= 0.985;
      if (Math.hypot(b.vx, b.vy) < 0.05) { b.vx = 0; b.vy = 0; }
      else anyMoving = true;
      for (const p of POCKETS) {
        if (Math.hypot(b.x - p.x, b.y - p.y) < POCKET_R) { b.pocketed = true; b.vx = 0; b.vy = 0; break; }
      }
      if (b.pocketed) continue;
      if (b.x < BALL_R) { b.x = BALL_R; b.vx = Math.abs(b.vx); }
      if (b.x > TABLE_W - BALL_R) { b.x = TABLE_W - BALL_R; b.vx = -Math.abs(b.vx); }
      if (b.y < BALL_R) { b.y = BALL_R; b.vy = Math.abs(b.vy); }
      if (b.y > TABLE_H - BALL_R) { b.y = TABLE_H - BALL_R; b.vy = -Math.abs(b.vy); }
    }
    for (let i = 0; i < bs.length; i++) {
      for (let j = i + 1; j < bs.length; j++) {
        const a = bs[i];
        const c = bs[j];
        if (a.pocketed || c.pocketed) continue;
        const dx = c.x - a.x;
        const dy = c.y - a.y;
        const dist = Math.hypot(dx, dy);
        if (dist > 0 && dist < BALL_R * 2) {
          const nx = dx / dist;
          const ny = dy / dist;
          const overlap = BALL_R * 2 - dist;
          a.x -= nx * overlap / 2;
          a.y -= ny * overlap / 2;
          c.x += nx * overlap / 2;
          c.y += ny * overlap / 2;
          const p = (a.vx - c.vx) * nx + (a.vy - c.vy) * ny;
          if (p > 0) {
            a.vx -= p * nx;
            a.vy -= p * ny;
            c.vx += p * nx;
            c.vy += p * ny;
          }
        }
      }
    }
    const cue = bs.find((b: any) => b.id === 'cue');
    if (cue && cue.pocketed && !anyMoving) {
      cue.pocketed = false;
      cue.x = TABLE_W * 0.25;
      cue.y = TABLE_H / 2;
      cue.vx = 0;
      cue.vy = 0;
      setMessage('Foul! Cue ball pocketed — it is back on the table.');
    }
    const remaining = bs.filter((b: any) => b.id !== 'cue' && !b.pocketed).length;
    if (remaining === 0 && !wonRef.current) {
      wonRef.current = true;
      setWon(true);
      setMessage('YOU WIN! Table cleared!');
    }
    ballsRef.current = bs;
    setBalls(bs);
    if (!anyMoving) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      movingRef.current = false;
      setMoving(false);
    }
  };

  const startLoop = () => {
    if (timerRef.current) return;
    movingRef.current = true;
    setMoving(true);
    timerRef.current = setInterval(step, 16);
  };

  const resetGame = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    const fresh = makeBalls();
    ballsRef.current = fresh;
    setBalls(fresh);
    movingRef.current = false;
    setMoving(false);
    wonRef.current = false;
    setWon(false);
    setAim(null);
    setMessage('Pull back on the table and release to shoot. Clear all 7 balls to win!');
  };

  const closeGame = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    onClose();
  };

  const aimResponderRef = useRef<any>(null);
  if (!aimResponderRef.current) {
    aimResponderRef.current = PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (evt: any) => {
        aimRef.current = { x: evt.nativeEvent.locationX, y: evt.nativeEvent.locationY };
        setAim(null);
      },
      onPanResponderMove: (evt: any) => {
        if (movingRef.current || wonRef.current) return;
        const cue = ballsRef.current.find((b: any) => b.id === 'cue');
        if (!cue || cue.pocketed) return;
        const s = aimRef.current;
        if (!s) return;
        const dx = evt.nativeEvent.locationX - s.x;
        const dy = evt.nativeEvent.locationY - s.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 5) { setAim(null); return; }
        const angle = Math.atan2(-dy, -dx);
        const power = Math.min(dist, 120) / 120;
        setAim({ angle, power });
      },
      onPanResponderRelease: (evt: any) => {
        if (movingRef.current || wonRef.current) return;
        const cue = ballsRef.current.find((b: any) => b.id === 'cue');
        if (!cue || cue.pocketed) return;
        const s = aimRef.current;
        if (!s) return;
        const dx = evt.nativeEvent.locationX - s.x;
        const dy = evt.nativeEvent.locationY - s.y;
        const dist = Math.hypot(dx, dy);
        setAim(null);
        if (dist < 10) return;
        const angle = Math.atan2(-dy, -dx);
        const speed = 2 + (Math.min(dist, 120) / 120) * 11;
        const bs = ballsRef.current.map((b: any) => b.id === 'cue' ? { ...b, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed } : { ...b });
        ballsRef.current = bs;
        setBalls(bs);
        setMessage('');
        startLoop();
      },
    });
  }

  const cueBall = balls.find((b: any) => b.id === 'cue');
  const pocketedCount = balls.filter((b: any) => b.id !== 'cue' && b.pocketed).length;
  let aimLine: any = null;
  if (aim && cueBall && !cueBall.pocketed && !moving && !won) {
    const cx = cueBall.x + Math.cos(aim.angle) * 35;
    const cy = cueBall.y + Math.sin(aim.angle) * 35;
    aimLine = (
      <View style={{ position: 'absolute', left: cx - 35, top: cy - 1, width: 70, height: 2, backgroundColor: '#ffffff', opacity: 0.9, transform: [{ rotate: `${aim.angle}rad` }] }} />
    );
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={closeGame}>
      <View style={{ flex: 1, backgroundColor: '#111111', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
        <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 18, marginBottom: 8 }}>POOL TABLE</Text>
        <Text style={{ color: '#cccccc', fontSize: 12, marginBottom: 8, textAlign: 'center' }}>{message}</Text>
        <Text style={{ color: '#f39c12', fontWeight: '800', marginBottom: 12 }}>{pocketedCount} / 7 pocketed</Text>
        <View {...aimResponderRef.current.panHandlers} style={{ width: TABLE_W, height: TABLE_H, backgroundColor: '#2e7d32', borderWidth: 10, borderColor: '#8d5a2b', borderRadius: 12, overflow: 'hidden' }}>
          {POCKETS.map((p: any, i: number) => (
            <View key={'p' + i} style={{ position: 'absolute', left: p.x - POCKET_R, top: p.y - POCKET_R, width: POCKET_R * 2, height: POCKET_R * 2, borderRadius: POCKET_R, backgroundColor: '#000000' }} />
          ))}
          {aimLine}
          {balls.filter((b: any) => !b.pocketed).map((b: any) => (
            <View key={b.id} style={{ position: 'absolute', left: b.x - BALL_R, top: b.y - BALL_R, width: BALL_R * 2, height: BALL_R * 2, borderRadius: BALL_R, backgroundColor: b.color, borderWidth: b.id === 'cue' ? 1 : 0, borderColor: '#999999' }} />
          ))}
        </View>
        {aim && !moving ? (
          <Text style={{ color: '#ffffff', fontSize: 12, marginTop: 10 }}>Power {Math.round(aim.power * 100)}%</Text>
        ) : (
          <Text style={{ color: '#999999', fontSize: 11, marginTop: 10, textAlign: 'center' }}>Pull back on the table and release to shoot. Pocket all 7 balls to win.</Text>
        )}
        <View style={{ flexDirection: 'row', gap: 12, marginTop: 16 }}>
          <TouchableOpacity onPress={resetGame} style={{ backgroundColor: '#666666', paddingVertical: 10, paddingHorizontal: 20, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>RESTART</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={closeGame} style={{ backgroundColor: '#e74c3c', paddingVertical: 10, paddingHorizontal: 20, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>LEAVE TABLE</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

"""

RELEASE_ANCHOR = """        onPanResponderRelease: (evt: any, gesture: any) => {
          setRoomScrollEnabled(true);"""
TAP_BLOCK = RELEASE_ANCHOR + """
          const tapDist = Math.hypot(gesture.dx, gesture.dy);
          if (tapDist < 12) {
            if (itemId === 'pool-table') setPoolGameOpen(true);
            return;
          }"""

MODAL_ANCHOR = "      {/* House Interior Modal */}"
GAME_MODAL = """      {poolGameOpen ? (
        <PoolGameModal visible={poolGameOpen} onClose={() => setPoolGameOpen(false)} />
      ) : null}

""" + MODAL_ANCHOR


def main():
    if not INDEX.exists():
        print(f"ERROR: {INDEX} not found. Run from repo root.")
        sys.exit(1)
    src = INDEX.read_text()

    if STATE_NEW in src:
        print("SKIP: pool game state already present")
    elif src.count(STATE_OLD) == 1:
        src = src.replace(STATE_OLD, STATE_NEW, 1)
        print("OK: pool game state added")
    else:
        print(f"WARNING: state anchor matched {src.count(STATE_OLD)}x")

    if "const PoolGameModal" in src:
        print("SKIP: PoolGameModal already present")
    elif src.count(MAPSCREEN_ANCHOR) == 1:
        src = src.replace(MAPSCREEN_ANCHOR, POOL_GAME + MAPSCREEN_ANCHOR, 1)
        print("OK: PoolGameModal added")
    else:
        print(f"WARNING: MapScreen anchor matched {src.count(MAPSCREEN_ANCHOR)}x")

    if "const tapDist = Math.hypot(gesture.dx, gesture.dy);" in src:
        print("SKIP: tap detection already present")
    elif src.count(RELEASE_ANCHOR) == 1:
        src = src.replace(RELEASE_ANCHOR, TAP_BLOCK, 1)
        print("OK: tap opens pool game (drag still moves the table)")
    else:
        print(f"WARNING: release anchor matched {src.count(RELEASE_ANCHOR)}x")

    if "setPoolGameOpen(false)" in src and "PoolGameModal visible={poolGameOpen}" in src:
        print("SKIP: game modal already present")
    elif src.count(MODAL_ANCHOR) == 1:
        src = src.replace(MODAL_ANCHOR, GAME_MODAL, 1)
        print("OK: game modal added")
    else:
        print(f"WARNING: interior modal anchor matched {src.count(MODAL_ANCHOR)}x")

    INDEX.write_text(src)
    print("HOUSE_POOL_GAME_OK")


if __name__ == "__main__":
    main()
