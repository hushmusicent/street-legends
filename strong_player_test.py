#!/usr/bin/env python3
"""
Test with Level Up to Win Battle - Give player better stats to win
"""

import requests
import json
import time

BACKEND_URL = "https://territory-battle-map.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def main():
    print("💪 STRONGER PLAYER BOUNTY TEST")
    print("=" * 40)
    
    # Create a player and level them up first
    player_name = f"StrongTest{int(time.time())}"
    response = requests.post(f"{API_BASE}/players", json={
        "name": player_name,
        "character_class": "enforcer"  # Strongest class with 150HP, 20 ATK
    })
    
    player_data = response.json()
    player_id = player_data["id"]
    print(f"✅ Created ENFORCER: {player_name}")
    print(f"   Base stats: HP={player_data['stats']['health']}, ATK={player_data['stats']['attack']}")
    
    # Generate low-level missions but look for easier bounties
    response = requests.get(f"{API_BASE}/missions/generate", params={
        "latitude": 40.758,
        "longitude": -73.9855,
        "player_level": 2,  # Lower level for easier bounties
        "player_id": player_id
    })
    
    missions = response.json()
    bounty_missions = [m for m in missions if m.get("mission_type") == "bounty"]
    
    if bounty_missions:
        bounty_mission = bounty_missions[0]
        bounty_enemy = bounty_mission.get("bounty_enemy", "")
        print(f"✅ Bounty target: {bounty_enemy}")
        
        # Accept mission
        requests.post(f"{API_BASE}/missions/{bounty_mission['id']}/accept", params={
            "player_id": player_id
        })
        
        # Spawn low level monsters
        response = requests.get(f"{API_BASE}/monsters/spawn", params={
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 1  # Level 1 spawns for easier battles
        })
        
        monsters = response.json()
        matching_monsters = [m for m in monsters if bounty_enemy.lower() in m['name'].lower()]
        
        if matching_monsters:
            target = matching_monsters[0]
            print(f"✅ Found {target['name']} (Level {target['level']}, HP={target['stats']['health']})")
            
            # Start battle
            response = requests.post(f"{API_BASE}/battles/start", params={
                "player_id": player_id,
                "enemy_type": "monster", 
                "enemy_id": target["id"]
            })
            
            battle = response.json()
            print(f"⚔️ Battle: Player {battle['player_health']}HP vs Enemy {battle['enemy_health']}HP")
            
            # Fight
            for round_num in range(1, 20):
                response = requests.post(f"{API_BASE}/battles/{battle['id']}/action", json={"action": "attack"})
                battle_state = response.json()
                status = battle_state['status']
                
                if status == "won":
                    print(f"🎉 VICTORY in round {round_num}!")
                    
                    # Check progress
                    response = requests.get(f"{API_BASE}/missions/active/{player_id}")
                    active_missions = response.json()
                    
                    for mission in active_missions:
                        if mission['id'] == bounty_mission['id']:
                            progress = mission.get('goal_progress', 0)
                            print(f"📈 Mission progress: {progress}/{mission.get('goal_target', 1)}")
                            
                            if progress > 0:
                                print("✅ BOUNTY PROGRESS INCREMENTED!")
                                return True
                            else:
                                print("❌ Progress did not increment")
                                return False
                    break
                elif status == "lost":
                    print(f"💀 Lost in round {round_num}")
                    return False
        else:
            print(f"❌ No {bounty_enemy} found")
    
    return False

if __name__ == "__main__":
    success = main()
    print(f"\n🎯 Test {'PASSED' if success else 'FAILED'}")