
## Fix (Jun 2026)
- Park PvP routes 404: removed double /api prefix and moved app.include_router(api_router) to end of server.py so routes defined after it (park_pvp, center-prize/award) register.
