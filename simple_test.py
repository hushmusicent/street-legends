#!/usr/bin/env python3
"""
Simple test to check specific issues
"""

import requests
import json

BACKEND_URL = "https://nexus-battle-quest.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def main():
    # Test with existing player from previous test
    player_id = "a14cd5cd-0640-4de0-ac1e-7fdcc89ea36b"
    
    print("1. Checking player data...")
    response = requests.get(f"{API_BASE}/players/{player_id}")
    if response.status_code == 200:
        player = response.json()
        print(f"   Player: {player['name']}")
        print(f"   Active missions: {player.get('active_missions', [])}")
        print(f"   Equipment: {player.get('equipment', {})}")
        print(f"   Inventory: {player.get('inventory', [])}")
    
    print("\n2. Checking active missions API...")
    response = requests.get(f"{API_BASE}/missions/active/{player_id}")
    if response.status_code == 200:
        missions = response.json()
        print(f"   Found {len(missions)} active missions")
        for m in missions:
            print(f"   → {m['title']}: {m.get('goal_progress', 0)}/{m.get('goal_target', '?')}")
    
    print("\n3. Creating a LOW level enemy to test battle...")
    # Spawn monsters and find a Level 1-2 enemy
    response = requests.get(f"{API_BASE}/monsters/spawn", params={
        "latitude": 40.758,
        "longitude": -73.9855,
        "player_level": 1  # Should spawn level 1-2 monsters
    })
    
    if response.status_code == 200:
        monsters = response.json()
        level_1_monsters = [m for m in monsters if m['level'] <= 2]
        if level_1_monsters:
            target = level_1_monsters[0]
            print(f"   Found Level {target['level']} {target['name']}: HP={target['stats']['health']}, ATK={target['stats']['attack']}")
            
            # Try battle with this weaker enemy
            response = requests.post(f"{API_BASE}/battles/start", params={
                "player_id": player_id,
                "enemy_type": "monster",
                "enemy_id": target["id"]
            })
            
            if response.status_code == 200:
                battle = response.json()
                print(f"   Battle started: Player {battle['player_health']}HP vs Monster {battle['enemy_health']}HP")
                
                # Fight until win/loss
                for round_num in range(1, 21):
                    response = requests.post(f"{API_BASE}/battles/{battle['id']}/action", json={"action": "attack"})
                    
                    if response.status_code == 200:
                        battle_state = response.json()
                        status = battle_state['status']
                        
                        if status == "won":
                            print(f"   ✅ Battle WON in round {round_num}!")
                            break
                        elif status == "lost":
                            print(f"   ❌ Battle LOST in round {round_num}")
                            break
                        elif round_num % 5 == 0:
                            print(f"   Round {round_num}: Player {battle_state['player_health']}HP, Monster {battle_state['enemy_health']}HP")
                
                # Check mission progress
                print("\n4. Checking mission progress after easier battle...")
                response = requests.get(f"{API_BASE}/missions/active/{player_id}")
                if response.status_code == 200:
                    missions = response.json()
                    for m in missions:
                        if m.get('mission_type') == 'bounty':
                            print(f"   Bounty mission progress: {m.get('goal_progress', 0)}/{m.get('goal_target', '?')}")

if __name__ == "__main__":
    main()