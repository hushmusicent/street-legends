#!/usr/bin/env python3
"""Street Legends: Spades — show the last card played before the next hand.

Problem: the final trick of a hand vanished the instant the hand ended
(PvC: 700ms after the 4th card, spEndTrick cleared the trick and scored;
PvP: the replay cleared it before the hand-over screen ever rendered),
so the last card played was never readable. Next-hand advance itself is
already user-paced (NEXT HAND button in both versions) — only the
display was too fast.

Fix (CardPvpHtml.ts, the file holding both Spades games):
 A. PvC normal tricks: 700ms -> 2000ms pause after the 4th card.
 B. PvC hand end: spEndTrick no longer clears the final trick — it stays
    on the table through the score screen, the score message names the
    last card played ('Last card played: <rank><suit> by <player>.'), and
    spNewHand (NEXT HAND tap) is what finally clears it.
 C. PvP hand end: spEndTrickPvp saves SP.lastTrick before clearing, and
    the PvP render shows lastTrick while phase is 'over', so the
    hand-over screen shows the final trick; the score text also names
    the last card. A fresh hand's replay object has no lastTrick, so
    mid-hand rendering is unchanged.
Frontend / Expo Go only. Each part is guarded: a missed anchor prints a
WARNING and skips only that part."""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
HTML = ROOT / "frontend/components/CardPvpHtml.ts"
MARKER = "SPADES_LAST_CARD"

def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))

def main():
    if not HTML.exists():
        print("WARNING: CardPvpHtml.ts not found - nothing changed")
        return 1
    src = HTML.read_text(errors="ignore")
    orig = delta(src)
    done = []

    # A. PvC trick pause.
    if "setTimeout(spEndTrick, 2000)" in src:
        print("SPADES_LAST_CARD_PAUSE_ALREADY_APPLIED"); done.append("pause")
    elif "setTimeout(spEndTrick, 700)" in src:
        src = src.replace("setTimeout(spEndTrick, 700)", "setTimeout(spEndTrick, 2000)", 1)
        print("SPADES_LAST_CARD_PAUSE_OK"); done.append("pause")
    else:
        print("WARNING: PvC trick timeout anchor not found - pause NOT changed")

    # B. PvC hand end: keep the final trick through the score screen.
    if "SPADES_LAST_CARD_PVC" in src:
        print("SPADES_LAST_CARD_PVC_ALREADY_APPLIED"); done.append("pvc")
    else:
        old = ("  SP.msg = ['You', 'West', 'Partner', 'East'][w] + ' takes the trick.';\n"
               "  SP.trick = [];\n"
               "  SP.ledSuit = null;\n"
               "  if (SP.hands[0].length === 0) { spScoreHand(); return; }")
        new = ("  SP.msg = ['You', 'West', 'Partner', 'East'][w] + ' takes the trick.';\n"
               "  if (SP.hands[0].length === 0) {\n"
               "    // SPADES_LAST_CARD_PVC: keep the final trick visible until NEXT HAND.\n"
               "    var lastPlayed = SP.trick[SP.trick.length - 1];\n"
               "    SP.ledSuit = null;\n"
               "    spScoreHand();\n"
               "    SP.msg = SP.msg + ' Last card played: ' + rlab(lastPlayed.c.r) + SUITS[lastPlayed.c.s] + ' by ' + ['You', 'West', 'Partner', 'East'][lastPlayed.p] + '.';\n"
               "    spRender();\n"
               "    return;\n"
               "  }\n"
               "  SP.trick = [];\n"
               "  SP.ledSuit = null;")
        if old in src:
            src = src.replace(old, new, 1)
            print("SPADES_LAST_CARD_PVC_OK"); done.append("pvc")
        else:
            print("WARNING: PvC spEndTrick anchor not found - hand-end NOT changed")

    # C1. PvP: save the last trick before clearing.
    if "SP.lastTrick = SP.trick.slice();" in src:
        print("SPADES_LAST_CARD_PVP_SAVE_ALREADY_APPLIED"); done.append("pvpsave")
    else:
        old = "  SP.msg = spSeatName(w) + ' takes the trick.';\n  SP.trick = [];"
        new = "  SP.msg = spSeatName(w) + ' takes the trick.';\n  SP.lastTrick = SP.trick.slice();\n  SP.trick = [];"
        if old in src:
            src = src.replace(old, new, 1)
            print("SPADES_LAST_CARD_PVP_SAVE_OK"); done.append("pvpsave")
        else:
            print("WARNING: PvP spEndTrick anchor not found - lastTrick NOT saved")

    # C2. PvP render: show lastTrick on the hand-over screen.
    if "shownTrick" in src:
        print("SPADES_LAST_CARD_PVP_RENDER_ALREADY_APPLIED"); done.append("pvprend")
    else:
        ti = src.find("spPvpTrick")
        if ti == -1:
            print("WARNING: spPvpTrick not found - PvP render NOT changed")
        else:
            pi = src.find("var played = SP.trick.find(function (t) { return t.p === i; });", ti)
            if pi == -1:
                print("WARNING: PvP trick render anchor not found - PvP render NOT changed")
            else:
                src = (src[:pi] + "var shownTrick = (SP.phase === 'over' && SP.lastTrick) ? SP.lastTrick : SP.trick;\n    "
                       + "var played = shownTrick.find(function (t) { return t.p === i; });" + src[pi + len("var played = SP.trick.find(function (t) { return t.p === i; });"):])
                print("SPADES_LAST_CARD_PVP_RENDER_OK"); done.append("pvprend")

    # C3. PvP score text names the last card (only if the name helpers exist here).
    if "SPADES_LAST_CARD_PVP_TEXT" in src:
        print("SPADES_LAST_CARD_PVP_TEXT_ALREADY_APPLIED"); done.append("pvptext")
    elif "function rlab" not in src and "rlab =" not in src:
        print("WARNING: rlab helper not found in PvP file - score text NOT changed")
    else:
        ei = src.find("SP.endText = 'Hand over.")
        if ei == -1:
            print("WARNING: PvP endText anchor not found - score text NOT changed")
        else:
            line_end = src.find("\n", ei)
            add = ("\n  // SPADES_LAST_CARD_PVP_TEXT\n"
                   "  if (SP.lastTrick && SP.lastTrick.length) { var lp = SP.lastTrick[SP.lastTrick.length - 1]; "
                   "SP.endText += ' Last card played: ' + rlab(lp.c.r) + SUITS[lp.c.s] + ' by ' + spSeatName(lp.p) + '.'; }")
            src = src[:line_end] + add + src[line_end:]
            print("SPADES_LAST_CARD_PVP_TEXT_OK"); done.append("pvptext")

    if delta(src) != orig:
        print("WARNING: balance changed - CardPvpHtml.ts NOT written")
        return 1
    HTML.write_text(src)
    if len(done) == 5:
        print("SPADES_LAST_CARD_OK")
    else:
        print("SPADES_LAST_CARD_PARTIAL: " + ",".join(done))
    return 0

if __name__ == "__main__":
    sys.exit(main())
