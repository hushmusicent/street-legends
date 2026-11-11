
## Fix (Jun 2026)
- Park PvP routes 404: removed double /api prefix and moved app.include_router(api_router) to end of server.py so routes defined after it (park_pvp, center-prize/award) register.

## Park PvP extras (Jun 2026)
- All 6 park games (Basketball, Baseball, Soccer, Tennis, 1-on-1, Football): poll every 100ms, position posts every 100ms with in-flight guards; read opponent slot room.states[oppRole]; oppSeq tracking.
- Rematch: each phone posts st.rm (round it wants next) + st.round; both agree -> restart; older-round posts dropped. Floating PvP bar (SHARE CODE while host waiting, REMATCH when over). Game REMATCH button in PvP routes to the handshake.
- Share: WebView posts share:<code>; index.tsx handleParkGameMessage opens native Share sheet.

## Park PvP cash wagers (Jun 2026)
- Backend: POST /api/park_pvp/rooms/{code}/wager/propose|agree|decline|start|settle (host proposes with round, guest agrees, start holds both stakes atomically, settle needs both phones to report same winner else refund). Leave mid-game with held bet = forfeit to the other player.
- Frontend (6 park HTML games): BET CASH / ACCEPT / DECLINE in the PvP bar while waiting or after game over; game start + rematch wait until the bet is decided.
