#!/usr/bin/env python3
"""
Bounty Mission Tracking Flow Test
Tests the FULL bounty mission flow end-to-end as requested:
1. Create player → 2. Generate missions → 3. Find bounty mission → 4. Accept it
5. Verify active missions → 6. Spawn monsters → 7. Find matching enemy → 8. Battle and win
9. Check mission progress increments → 10. Verify active missions display works
"""

import requests
import json
import sys
import time

# Backend URL from frontend/.env
BACKEND_URL = "https://heist-map-game.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def log_test(test_name, status, details=""):
    """Log test results with clear formatting"""
    status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
    print(f"{status_symbol} {test_name}")
    if details:
        print(f"   → {details}")

def main():
    print("🎯 BOUNTY MISSION TRACKING FLOW TEST - FULL END-TO-END")
    print("=" * 70)
    
    test_results = []
    player_id = None
    bounty_mission_id = None
    bounty_enemy = None
    goal_target = None
    matching_monster = None
    
    try:
        # Test 1: Create a new player (street_soldier, level 1)
        print("\n1. Creating new player for bounty test...")
        response = requests.post(f"{API_BASE}/auth/register", json={
            "username": f"bountytest{int(time.time())}",
            "password": "test123",
            "name": f"BountyTester{int(time.time())}",
            "class_id": "street_soldier"
        })
        
        if response.status_code == 200:
            player_data = response.json()
            player_id = player_data["id"]
            log_test("Create Player", "PASS", f"Created player: {player_data['name']} (ID: {player_id})")
            test_results.append(True)
        else:
            # Try with /api/players endpoint if auth fails
            response = requests.post(f"{API_BASE}/players", json={
                "name": f"BountyTester{int(time.time())}",
                "character_class": "street_soldier"
            })
            if response.status_code == 200:
                player_data = response.json()
                player_id = player_data["id"]
                log_test("Create Player", "PASS", f"Created player: {player_data['name']} (ID: {player_id})")
                test_results.append(True)
            else:
                log_test("Create Player", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
                test_results.append(False)
                return False
        
        # Test 2: Generate missions at specified coordinates with player_id
        print("\n2. Generating missions at Times Square (40.758, -73.9855)...")
        response = requests.get(f"{API_BASE}/missions/generate", params={
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 1,
            "player_id": player_id
        })
        
        if response.status_code == 200:
            missions = response.json()
            if len(missions) >= 1:
                log_test("Generate Missions", "PASS", f"Generated {len(missions)} missions")
                test_results.append(True)
                
                # Find bounty missions
                bounty_missions = [m for m in missions if m.get("mission_type") == "bounty"]
                if bounty_missions:
                    bounty_mission = bounty_missions[0]
                    bounty_mission_id = bounty_mission["id"]
                    bounty_enemy = bounty_mission.get("bounty_enemy", "")
                    goal_target = bounty_mission.get("goal_target", 1)
                    log_test("Find Bounty Mission", "PASS", f"Found bounty mission: {bounty_mission['title']}, Enemy: {bounty_enemy}, Target: {goal_target}")
                    test_results.append(True)
                else:
                    log_test("Find Bounty Mission", "FAIL", "No bounty missions found in generated missions")
                    test_results.append(False)
                    return False
            else:
                log_test("Generate Missions", "FAIL", "No missions generated")
                test_results.append(False)
                return False
        else:
            log_test("Generate Missions", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            return False
        
        # Test 3: Accept the bounty mission
        print(f"\n3. Accepting bounty mission {bounty_mission_id}...")
        response = requests.post(f"{API_BASE}/missions/{bounty_mission_id}/accept", params={
            "player_id": player_id
        })
        
        if response.status_code == 200:
            result = response.json()
            log_test("Accept Bounty Mission", "PASS", f"Message: {result.get('message', 'Mission accepted')}")
            test_results.append(True)
        else:
            log_test("Accept Bounty Mission", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            return False
        
        # Test 4: Verify player's active_missions array contains the mission ID
        print(f"\n4. Checking player's active_missions array...")
        response = requests.get(f"{API_BASE}/players/{player_id}")
        
        if response.status_code == 200:
            player_data = response.json()
            active_missions = player_data.get("active_missions", [])
            if bounty_mission_id in active_missions:
                log_test("Player Active Missions Array", "PASS", f"Mission {bounty_mission_id} found in active_missions array")
                test_results.append(True)
            else:
                log_test("Player Active Missions Array", "FAIL", f"Mission {bounty_mission_id} NOT found in active_missions. Found: {active_missions}")
                test_results.append(False)
        else:
            log_test("Player Active Missions Array", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
        
        # Test 5: Check active missions API and verify initial goal_progress is 0
        print(f"\n5. Checking active missions API - initial progress...")
        response = requests.get(f"{API_BASE}/missions/active/{player_id}")
        
        if response.status_code == 200:
            active_missions_data = response.json()
            bounty_mission_data = None
            for mission in active_missions_data:
                if mission["id"] == bounty_mission_id:
                    bounty_mission_data = mission
                    break
            
            if bounty_mission_data:
                initial_progress = bounty_mission_data.get("goal_progress", -1)
                if initial_progress == 0:
                    log_test("Initial Goal Progress", "PASS", f"Initial progress correctly set to 0")
                    test_results.append(True)
                else:
                    log_test("Initial Goal Progress", "FAIL", f"Initial progress is {initial_progress}, expected 0")
                    test_results.append(False)
            else:
                log_test("Initial Goal Progress", "FAIL", f"Bounty mission not found in active missions API")
                test_results.append(False)
        else:
            log_test("Initial Goal Progress", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
        
        # Test 6: Spawn monsters near the same location
        print(f"\n6. Spawning monsters at same location...")
        response = requests.get(f"{API_BASE}/monsters/spawn", params={
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 1
        })
        
        if response.status_code == 200:
            monsters = response.json()
            if len(monsters) >= 1:
                log_test("Spawn Monsters", "PASS", f"Spawned {len(monsters)} monsters")
                test_results.append(True)
                
                # Find monster whose name MATCHES the bounty_enemy
                for monster in monsters:
                    monster_name = monster.get("name", "")
                    if bounty_enemy and bounty_enemy.lower() in monster_name.lower():
                        matching_monster = monster
                        break
                
                if matching_monster:
                    log_test("Find Matching Monster", "PASS", f"Found matching monster: {matching_monster['name']} (matches bounty_enemy: {bounty_enemy})")
                    test_results.append(True)
                else:
                    log_test("Find Matching Monster", "FAIL", f"No monster found matching bounty_enemy '{bounty_enemy}'. Available: {[m['name'] for m in monsters]}")
                    test_results.append(False)
                    # Try with first available monster for testing
                    matching_monster = monsters[0]
                    print(f"   → Using first monster '{matching_monster['name']}' for battle testing")
            else:
                log_test("Spawn Monsters", "FAIL", "No monsters spawned")
                test_results.append(False)
                return False
        else:
            log_test("Spawn Monsters", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            return False
        
        # Test 7: Start battle with matching monster
        print(f"\n7. Starting battle with {matching_monster['name']}...")
        response = requests.post(f"{API_BASE}/battles/start", params={
            "player_id": player_id,
            "enemy_type": "monster",
            "enemy_id": matching_monster["id"]
        })
        
        if response.status_code == 200:
            battle_data = response.json()
            battle_id = battle_data["id"]
            log_test("Start Battle", "PASS", f"Battle started: {battle_id}")
            test_results.append(True)
        else:
            log_test("Start Battle", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            return False
        
        # Test 8: Win the battle by attacking repeatedly
        print(f"\n8. Fighting battle to victory...")
        max_attacks = 20
        attack_count = 0
        battle_won = False
        
        while attack_count < max_attacks:
            response = requests.post(f"{API_BASE}/battles/{battle_id}/action", json={
                "action": "attack"
            })
            
            if response.status_code == 200:
                battle_state = response.json()
                status = battle_state.get("status", "active")
                
                if status == "won":
                    battle_won = True
                    log_test("Win Battle", "PASS", f"Battle won after {attack_count + 1} attacks!")
                    test_results.append(True)
                    break
                elif status == "lost":
                    log_test("Win Battle", "FAIL", f"Battle lost after {attack_count + 1} attacks")
                    test_results.append(False)
                    break
                else:
                    attack_count += 1
            else:
                log_test("Win Battle", "FAIL", f"Attack failed: Status {response.status_code}")
                test_results.append(False)
                break
        
        if not battle_won and attack_count >= max_attacks:
            log_test("Win Battle", "FAIL", f"Battle didn't end after {max_attacks} attacks")
            test_results.append(False)
        
        # Test 9: Check if mission progress incremented after victory
        print(f"\n9. Checking mission progress after battle victory...")
        response = requests.get(f"{API_BASE}/missions/active/{player_id}")
        
        if response.status_code == 200:
            active_missions_data = response.json()
            bounty_mission_data = None
            for mission in active_missions_data:
                if mission["id"] == bounty_mission_id:
                    bounty_mission_data = mission
                    break
            
            if bounty_mission_data:
                final_progress = bounty_mission_data.get("goal_progress", -1)
                if final_progress > 0:
                    log_test("Mission Progress Incremented", "PASS", f"Progress increased from 0 to {final_progress} ✅")
                    test_results.append(True)
                else:
                    log_test("Mission Progress Incremented", "FAIL", f"Progress still at {final_progress}, expected > 0 ❌")
                    test_results.append(False)
            else:
                log_test("Mission Progress Incremented", "FAIL", f"Bounty mission not found in active missions after battle")
                test_results.append(False)
        else:
            log_test("Mission Progress Incremented", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
        
        # Test 10: Check raw mission in DB to inspect player_progress
        print(f"\n10. Additional check - verify missions endpoint returns missions...")
        response = requests.get(f"{API_BASE}/missions/active/{player_id}")
        
        if response.status_code == 200:
            active_missions_data = response.json()
            if len(active_missions_data) > 0:
                log_test("Active Missions Display", "PASS", f"Active missions API returns {len(active_missions_data)} missions")
                test_results.append(True)
                
                # Show detailed mission data for debugging
                for mission in active_missions_data:
                    print(f"   → Mission: {mission.get('title', 'Unknown')}")
                    print(f"     Type: {mission.get('mission_type', 'Unknown')}")
                    print(f"     Progress: {mission.get('goal_progress', 0)}/{mission.get('goal_target', '?')}")
                    if mission.get('mission_type') == 'bounty':
                        print(f"     Bounty Enemy: {mission.get('bounty_enemy', 'None')}")
            else:
                log_test("Active Missions Display", "FAIL", "No missions returned by active missions API")
                test_results.append(False)
        else:
            log_test("Active Missions Display", "FAIL", f"Active missions API failed: {response.status_code}")
            test_results.append(False)
    
    except requests.exceptions.RequestException as e:
        log_test("Network Connection", "FAIL", f"Connection error: {e}")
        test_results.append(False)
    except Exception as e:
        log_test("Unexpected Error", "FAIL", f"Error: {e}")
        test_results.append(False)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 BOUNTY MISSION TRACKING FLOW TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(test_results)
    total = len(test_results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"Tests passed: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("🎉 BOUNTY MISSION TRACKING: ALL TESTS PASSED!")
        print("✅ Players can create characters and accept bounty missions")
        print("✅ Active missions API working correctly") 
        print("✅ Battle system correctly increments bounty mission progress")
        print("✅ End-to-end bounty flow working as expected")
    elif success_rate >= 80:
        print("⚠️ BOUNTY MISSION TRACKING: MOSTLY WORKING")
        print("Some issues found but core functionality appears to work")
    else:
        print("❌ BOUNTY MISSION TRACKING: CRITICAL ISSUES FOUND")
        print("Major problems detected that need attention")
    
    return success_rate >= 80

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)