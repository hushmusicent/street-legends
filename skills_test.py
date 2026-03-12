#!/usr/bin/env python3
"""
Use skills to win battle and test bounty progress
"""

import requests
import time

BACKEND_URL = "https://territory-battle-map.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def main():
    print("🎯 SKILLS-BASED BOUNTY TEST")
    print("=" * 30)
    
    # Create enforcer
    player_name = f"SkillTest{int(time.time())}"
    response = requests.post(f"{API_BASE}/players", json={
        "name": player_name,
        "character_class": "enforcer"
    })
    
    player_data = response.json()
    player_id = player_data["id"]
    print(f"✅ Created ENFORCER: {player_name} (HP={player_data['stats']['health']}, ATK={player_data['stats']['attack']})")
    
    # Get a simpler bounty - generate for level 1
    response = requests.get(f"{API_BASE}/missions/generate", params={
        "latitude": 40.758,
        "longitude": -73.9855,
        "player_level": 1,  # Level 1 for easier bounties
        "player_id": player_id
    })
    
    missions = response.json()
    bounty_missions = [m for m in missions if m.get("mission_type") == "bounty"]
    
    if not bounty_missions:
        print("❌ No bounty missions")
        return False
        
    bounty_mission = bounty_missions[0]
    bounty_enemy = bounty_mission.get("bounty_enemy", "")
    print(f"✅ Target: {bounty_enemy} (Need {bounty_mission.get('goal_target', 1)} kills)")
    
    # Accept mission
    requests.post(f"{API_BASE}/missions/{bounty_mission['id']}/accept", params={"player_id": player_id})
    
    # Spawn level 1 monsters for easier battles
    response = requests.get(f"{API_BASE}/monsters/spawn", params={
        "latitude": 40.758,
        "longitude": -73.9855,
        "player_level": 1
    })
    
    monsters = response.json()
    matching_monsters = [m for m in monsters if bounty_enemy.lower() in m['name'].lower()]
    
    if not matching_monsters:
        print(f"❌ No {bounty_enemy} found. Using any Level 1-2 monster.")
        suitable = [m for m in monsters if m['level'] <= 2]
        if suitable:
            target = suitable[0]
            print(f"   Using {target['name']} instead")
        else:
            return False
    else:
        target = matching_monsters[0]
        print(f"✅ Found {target['name']} (Level {target['level']}, HP={target['stats']['health']})")
    
    # Start battle
    response = requests.post(f"{API_BASE}/battles/start", params={
        "player_id": player_id,
        "enemy_type": "monster",
        "enemy_id": target["id"]
    })
    
    battle = response.json()
    print(f"⚔️ Battle start: Player {battle['player_health']}HP vs Enemy {battle['enemy_health']}HP")
    
    # Fight using heavy_strike skill for extra damage
    battle_won = False
    for round_num in range(1, 15):
        # Use heavy_strike skill (1.5x damage) every other round
        if round_num % 2 == 1:
            action = {"action": "skill", "skill_id": "heavy_strike"}
        else:
            action = {"action": "attack"}
            
        response = requests.post(f"{API_BASE}/battles/{battle['id']}/action", json=action)
        
        if response.status_code != 200:
            print(f"❌ Action failed: {response.text}")
            break
            
        battle_state = response.json()
        status = battle_state['status']
        
        if status == "won":
            print(f"🎉 VICTORY in round {round_num}!")
            battle_won = True
            break
        elif status == "lost":
            print(f"💀 Lost in round {round_num}")
            break
        elif round_num % 3 == 0:
            print(f"   Round {round_num}: Player {battle_state['player_health']}HP, Enemy {battle_state['enemy_health']}HP, Energy {battle_state['player_energy']}")
    
    if battle_won:
        # Check mission progress
        response = requests.get(f"{API_BASE}/missions/active/{player_id}")
        active_missions = response.json()
        
        for mission in active_missions:
            if mission['id'] == bounty_mission['id']:
                progress = mission.get('goal_progress', 0)
                target_count = mission.get('goal_target', 1)
                print(f"📈 Mission progress: {progress}/{target_count}")
                
                # Check if progress incremented correctly
                expected_progress = 1 if bounty_enemy.lower() in target['name'].lower() else 0
                
                if progress == expected_progress:
                    if expected_progress > 0:
                        print("✅ BOUNTY PROGRESS INCREMENTED CORRECTLY!")
                    else:
                        print("✅ Progress correctly stayed at 0 (wrong enemy type)")
                    return True
                else:
                    print(f"❌ Expected progress {expected_progress}, got {progress}")
                    return False
    
    return False

if __name__ == "__main__":
    success = main()
    print(f"\n🎯 Test {'PASSED' if success else 'FAILED'}")