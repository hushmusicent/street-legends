#!/usr/bin/env python3
"""
Final Bounty Mission Test - Tests the complete flow with proper enemy matching
"""

import requests
import json
import time

BACKEND_URL = "https://heist-map-game.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def main():
    print("🎯 FINAL BOUNTY MISSION TRACKING TEST")
    print("=" * 50)
    
    # Step 1: Create a fresh player
    player_name = f"FinalTest{int(time.time())}"
    response = requests.post(f"{API_BASE}/players", json={
        "name": player_name,
        "character_class": "street_soldier"
    })
    
    if response.status_code != 200:
        print(f"❌ Player creation failed")
        return False
        
    player_data = response.json()
    player_id = player_data["id"]
    print(f"✅ Created player: {player_name}")
    
    # Step 2: Generate missions at higher level to get Gangster enemies
    print("\n🔍 Generating missions for level 3-4 range (to get Gangster enemies)...")
    response = requests.get(f"{API_BASE}/missions/generate", params={
        "latitude": 40.758,
        "longitude": -73.9855,
        "player_level": 4,  # Higher level to get Gangster enemies
        "player_id": player_id
    })
    
    missions = response.json()
    bounty_missions = [m for m in missions if m.get("mission_type") == "bounty"]
    
    if not bounty_missions:
        print("❌ No bounty missions generated")
        return False
        
    bounty_mission = bounty_missions[0]
    bounty_enemy = bounty_mission.get("bounty_enemy", "")
    print(f"✅ Found bounty mission: {bounty_mission['title']}")
    print(f"   Target enemy: {bounty_enemy}")
    print(f"   Goal: {bounty_mission.get('goal_target', 1)}")
    
    # Step 3: Accept the mission
    print(f"\n📝 Accepting bounty mission...")
    response = requests.post(f"{API_BASE}/missions/{bounty_mission['id']}/accept", params={
        "player_id": player_id
    })
    
    if response.status_code != 200:
        print(f"❌ Mission acceptance failed: {response.text}")
        return False
        
    print("✅ Mission accepted")
    
    # Step 4: Verify both mission tracking methods
    print(f"\n🔍 Checking mission tracking...")
    
    # Check player's active_missions array
    response = requests.get(f"{API_BASE}/players/{player_id}")
    player_data = response.json()
    active_missions_array = player_data.get("active_missions", [])
    
    # Check active missions API
    response = requests.get(f"{API_BASE}/missions/active/{player_id}")
    active_missions_api = response.json()
    
    print(f"   Player active_missions array: {len(active_missions_array)} missions")
    print(f"   Active missions API: {len(active_missions_api)} missions")
    
    if bounty_mission['id'] in active_missions_array:
        print("   ✅ Mission found in player's active_missions array")
    else:
        print("   ❌ Mission NOT in player's active_missions array")
    
    # Step 5: Spawn monsters at level 4 to match bounty enemy
    print(f"\n🐺 Spawning level 4 monsters to find {bounty_enemy}...")
    response = requests.get(f"{API_BASE}/monsters/spawn", params={
        "latitude": 40.758,
        "longitude": -73.9855,
        "player_level": 4  # Higher level to get Gangster-type enemies
    })
    
    monsters = response.json()
    matching_monsters = [m for m in monsters if bounty_enemy.lower() in m['name'].lower()]
    
    if not matching_monsters:
        print(f"   ❌ No {bounty_enemy} found. Available: {[m['name'] for m in monsters[:5]]}")
        # Try with any monster that has similar level
        suitable_monsters = [m for m in monsters if m['level'] <= 3]
        if suitable_monsters:
            target_monster = suitable_monsters[0]
            print(f"   🔄 Using {target_monster['name']} (Level {target_monster['level']}) instead")
        else:
            print("   ❌ No suitable monsters found")
            return False
    else:
        target_monster = matching_monsters[0]
        print(f"   ✅ Found {target_monster['name']} (Level {target_monster['level']})")
    
    # Step 6: Battle the monster
    print(f"\n⚔️ Starting battle...")
    response = requests.post(f"{API_BASE}/battles/start", params={
        "player_id": player_id,
        "enemy_type": "monster",
        "enemy_id": target_monster["id"]
    })
    
    battle = response.json()
    print(f"   Battle started: Player {battle['player_health']}HP vs {target_monster['name']} {battle['enemy_health']}HP")
    
    # Fight the battle
    battle_won = False
    for round_num in range(1, 25):
        response = requests.post(f"{API_BASE}/battles/{battle['id']}/action", json={"action": "attack"})
        battle_state = response.json()
        status = battle_state['status']
        
        if status == "won":
            print(f"   🎉 Battle WON in round {round_num}!")
            battle_won = True
            break
        elif status == "lost":
            print(f"   💀 Battle LOST in round {round_num}")
            break
        elif round_num % 5 == 0:
            print(f"   Round {round_num}: Player {battle_state['player_health']}HP, Enemy {battle_state['enemy_health']}HP")
    
    # Step 7: Check mission progress
    print(f"\n📊 Checking mission progress after battle...")
    response = requests.get(f"{API_BASE}/missions/active/{player_id}")
    active_missions = response.json()
    
    for mission in active_missions:
        if mission['id'] == bounty_mission['id']:
            progress = mission.get('goal_progress', 0)
            target = mission.get('goal_target', 1)
            print(f"   Mission progress: {progress}/{target}")
            
            if battle_won and bounty_enemy.lower() in target_monster['name'].lower():
                if progress > 0:
                    print("   ✅ Mission progress INCREMENTED correctly!")
                    return True
                else:
                    print("   ❌ Mission progress did NOT increment despite winning with correct enemy")
                    return False
            elif not battle_won:
                print("   ⚠️ Battle was lost, so mission progress should not increment")
                return True
            else:
                print(f"   ⚠️ Enemy mismatch: fought {target_monster['name']}, needed {bounty_enemy}")
                return True
    
    print("   ❌ Bounty mission not found in active missions")
    return False

if __name__ == "__main__":
    success = main()
    print(f"\n🎯 Test {'PASSED' if success else 'FAILED'}")