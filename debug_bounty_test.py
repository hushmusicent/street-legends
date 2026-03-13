#!/usr/bin/env python3
"""
Debug Bounty Mission Test - Step by step debugging
Focus on identifying why battle was lost and mission tracking isn't working
"""

import requests
import json
import sys
import time

BACKEND_URL = "https://nexus-battle-quest.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def debug_log(message):
    print(f"🔍 {message}")

def main():
    print("🔧 DEBUG BOUNTY MISSION TEST")
    print("=" * 50)
    
    try:
        # Step 1: Create player
        debug_log("Creating test player...")
        response = requests.post(f"{API_BASE}/players", json={
            "name": f"DebugPlayer{int(time.time())}",
            "character_class": "street_soldier"
        })
        
        if response.status_code != 200:
            print(f"❌ Player creation failed: {response.status_code} - {response.text}")
            return False
            
        player_data = response.json()
        player_id = player_data["id"]
        print(f"✅ Player created: {player_data['name']} (Level {player_data['level']})")
        print(f"   Stats: HP={player_data['stats']['health']}, ATK={player_data['stats']['attack']}, DEF={player_data['stats']['defense']}")
        
        # Step 2: Generate missions and find bounty
        debug_log("Generating missions...")
        response = requests.get(f"{API_BASE}/missions/generate", params={
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 1,
            "player_id": player_id
        })
        
        if response.status_code != 200:
            print(f"❌ Mission generation failed: {response.status_code}")
            return False
            
        missions = response.json()
        bounty_missions = [m for m in missions if m.get("mission_type") == "bounty"]
        
        if not bounty_missions:
            print(f"❌ No bounty missions found. Available types: {[m.get('mission_type') for m in missions]}")
            return False
            
        bounty_mission = bounty_missions[0]
        print(f"✅ Bounty mission found: {bounty_mission['title']}")
        print(f"   Enemy: {bounty_mission.get('bounty_enemy')}")
        print(f"   Target: {bounty_mission.get('goal_target')}")
        
        # Step 3: Accept mission
        debug_log("Accepting bounty mission...")
        response = requests.post(f"{API_BASE}/missions/{bounty_mission['id']}/accept", params={
            "player_id": player_id
        })
        
        if response.status_code != 200:
            print(f"❌ Mission acceptance failed: {response.status_code} - {response.text}")
            return False
            
        print("✅ Mission accepted")
        
        # Step 4: Check player's active missions array
        debug_log("Checking player data after mission acceptance...")
        response = requests.get(f"{API_BASE}/players/{player_id}")
        
        if response.status_code == 200:
            updated_player = response.json()
            active_missions = updated_player.get("active_missions", [])
            print(f"   Active missions array: {active_missions}")
            
            if bounty_mission['id'] in active_missions:
                print("✅ Mission ID correctly added to player's active_missions array")
            else:
                print("❌ Mission ID NOT found in player's active_missions array")
        
        # Step 5: Check active missions API
        debug_log("Checking active missions API...")
        response = requests.get(f"{API_BASE}/missions/active/{player_id}")
        
        if response.status_code == 200:
            active_data = response.json()
            print(f"   Active missions API returned: {len(active_data)} missions")
            for mission in active_data:
                print(f"   → {mission['title']}: Progress {mission.get('goal_progress', 0)}/{mission.get('goal_target', '?')}")
        
        # Step 6: Spawn monsters
        debug_log("Spawning monsters...")
        response = requests.get(f"{API_BASE}/monsters/spawn", params={
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 1
        })
        
        monsters = response.json()
        bounty_enemy = bounty_mission.get('bounty_enemy', '')
        matching_monsters = [m for m in monsters if bounty_enemy.lower() in m['name'].lower()]
        
        if not matching_monsters:
            print(f"❌ No monsters match bounty enemy '{bounty_enemy}'")
            print(f"   Available monsters: {[m['name'] for m in monsters]}")
            # Use any monster for testing
            target_monster = monsters[0]
            print(f"   Using {target_monster['name']} for testing")
        else:
            target_monster = matching_monsters[0]
            print(f"✅ Found matching monster: {target_monster['name']}")
        
        print(f"   Monster stats: Level {target_monster['level']}, HP={target_monster['stats']['health']}, ATK={target_monster['stats']['attack']}")
        
        # Step 7: Start battle
        debug_log("Starting battle...")
        response = requests.post(f"{API_BASE}/battles/start", params={
            "player_id": player_id,
            "enemy_type": "monster",
            "enemy_id": target_monster["id"]
        })
        
        if response.status_code != 200:
            print(f"❌ Battle start failed: {response.status_code}")
            return False
            
        battle = response.json()
        print(f"✅ Battle started: Player HP={battle['player_health']}, Monster HP={battle['enemy_health']}")
        
        # Step 8: Fight carefully and track health
        debug_log("Fighting battle (max 15 rounds)...")
        for round_num in range(1, 16):
            response = requests.post(f"{API_BASE}/battles/{battle['id']}/action", json={"action": "attack"})
            
            if response.status_code != 200:
                print(f"❌ Attack failed: {response.status_code}")
                break
                
            battle_state = response.json()
            player_hp = battle_state['player_health']
            enemy_hp = battle_state['enemy_health']
            status = battle_state['status']
            
            print(f"   Round {round_num}: Player {player_hp}HP, Enemy {enemy_hp}HP, Status: {status}")
            
            if status == "won":
                print("🎉 Battle WON!")
                break
            elif status == "lost":
                print("💀 Battle LOST!")
                break
            elif status != "active":
                print(f"⚠️ Unexpected status: {status}")
                break
        
        # Step 9: Check mission progress after battle
        debug_log("Checking mission progress after battle...")
        response = requests.get(f"{API_BASE}/missions/active/{player_id}")
        
        if response.status_code == 200:
            active_data = response.json()
            for mission in active_data:
                if mission['id'] == bounty_mission['id']:
                    progress = mission.get('goal_progress', 0)
                    target = mission.get('goal_target', '?')
                    print(f"   Final mission progress: {progress}/{target}")
                    
                    if progress > 0:
                        print("✅ Mission progress INCREMENTED!")
                    else:
                        print("❌ Mission progress DID NOT increment")
        
        return True
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

if __name__ == "__main__":
    main()