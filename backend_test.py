#!/usr/bin/env python3
"""
Multi-player Mission Acceptance System Test
Tests the new system where multiple players can accept the same mission with independent progress tracking.
"""

import requests
import json
import sys

# Backend URL from frontend/.env
BACKEND_URL = "https://territory-battle-map.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

def log_test(test_name, status, details=""):
    """Log test results with clear formatting"""
    status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
    print(f"{status_symbol} {test_name}")
    if details:
        print(f"   → {details}")

def create_player(name, character_class):
    """Create a new player"""
    response = requests.post(f"{API_BASE}/players", json={
        "name": name,
        "character_class": character_class
    })
    return response

def main():
    print("🎮 MULTI-PLAYER MISSION ACCEPTANCE SYSTEM TEST")
    print("=" * 60)
    
    test_results = []
    
    try:
        # Test 1: Create Player1
        print("\n1. Creating Player1...")
        response = create_player("MultiTest1", "street_soldier")
        if response.status_code == 200:
            player1_data = response.json()
            player1_id = player1_data["id"]
            log_test("Create Player1", "PASS", f"ID: {player1_id}")
            test_results.append(True)
        else:
            log_test("Create Player1", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            return
            
        # Test 2: Create Player2
        print("\n2. Creating Player2...")
        response = create_player("MultiTest2", "hacker")
        if response.status_code == 200:
            player2_data = response.json()
            player2_id = player2_data["id"]
            log_test("Create Player2", "PASS", f"ID: {player2_id}")
            test_results.append(True)
        else:
            log_test("Create Player2", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            return
            
        # Test 3: Generate missions
        print("\n3. Generating missions at Times Square...")
        response = requests.get(f"{API_BASE}/missions/generate", params={
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 5
        })
        if response.status_code == 200:
            missions = response.json()
            if len(missions) >= 1:
                mission = missions[0]
                mission_id = mission["id"]
                log_test("Generate missions", "PASS", f"Generated {len(missions)} missions, using mission: {mission['title']}")
                test_results.append(True)
            else:
                log_test("Generate missions", "FAIL", "No missions generated")
                test_results.append(False)
                return
        else:
            log_test("Generate missions", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            return
            
        # Test 4: Player1 accepts mission
        print(f"\n4. Player1 accepting mission {mission_id}...")
        response = requests.post(f"{API_BASE}/missions/{mission_id}/accept", params={
            "player_id": player1_id
        })
        if response.status_code == 200:
            result = response.json()
            log_test("Player1 accepts mission", "PASS", f"Message: {result['message']}")
            test_results.append(True)
        else:
            log_test("Player1 accepts mission", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            
        # Test 5: Player2 accepts THE SAME mission (KEY TEST)
        print(f"\n5. Player2 accepting THE SAME mission {mission_id}...")
        response = requests.post(f"{API_BASE}/missions/{mission_id}/accept", params={
            "player_id": player2_id
        })
        if response.status_code == 200:
            result = response.json()
            log_test("Player2 accepts SAME mission", "PASS", f"SUCCESS: Multiple players can accept same mission! Message: {result['message']}")
            test_results.append(True)
        else:
            log_test("Player2 accepts SAME mission", "FAIL", f"CRITICAL: Multiple players cannot accept same mission. Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            
        # Test 6: Player1 tries to re-accept same mission
        print(f"\n6. Player1 trying to re-accept same mission {mission_id}...")
        response = requests.post(f"{API_BASE}/missions/{mission_id}/accept", params={
            "player_id": player1_id
        })
        if response.status_code == 400:
            log_test("Player1 re-acceptance blocked", "PASS", f"Correctly blocked: {response.json().get('detail', 'Unknown error')}")
            test_results.append(True)
        else:
            log_test("Player1 re-acceptance blocked", "FAIL", f"Should have been blocked! Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            
        # Test 7: Get Player1's active missions
        print(f"\n7. Getting Player1's active missions...")
        response = requests.get(f"{API_BASE}/missions/active/{player1_id}")
        if response.status_code == 200:
            player1_missions = response.json()
            if len(player1_missions) >= 1:
                p1_mission = player1_missions[0]
                p1_progress = p1_mission.get("goal_progress", "unknown")
                log_test("Player1 active missions", "PASS", f"Found {len(player1_missions)} missions, progress: {p1_progress}")
                test_results.append(True)
            else:
                log_test("Player1 active missions", "FAIL", "No active missions found for Player1")
                test_results.append(False)
        else:
            log_test("Player1 active missions", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            
        # Test 8: Get Player2's active missions
        print(f"\n8. Getting Player2's active missions...")
        response = requests.get(f"{API_BASE}/missions/active/{player2_id}")
        if response.status_code == 200:
            player2_missions = response.json()
            if len(player2_missions) >= 1:
                p2_mission = player2_missions[0]
                p2_progress = p2_mission.get("goal_progress", "unknown")
                log_test("Player2 active missions", "PASS", f"Found {len(player2_missions)} missions, progress: {p2_progress}")
                
                # Verify they have the same mission with independent progress
                if p1_mission["id"] == p2_mission["id"] and p1_progress == p2_progress == 0:
                    log_test("Independent progress tracking", "PASS", f"Both players have same mission with independent progress (both at 0)")
                    test_results.append(True)
                else:
                    log_test("Independent progress tracking", "FAIL", f"Progress mismatch or different missions. P1: {p1_progress}, P2: {p2_progress}")
                    test_results.append(False)
            else:
                log_test("Player2 active missions", "FAIL", "No active missions found for Player2")
                test_results.append(False)
        else:
            log_test("Player2 active missions", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            
        # Test 9: Test generate_missions with player_id parameter
        print(f"\n9. Testing generate_missions with player_id for Player1...")
        response = requests.get(f"{API_BASE}/missions/generate", params={
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 5,
            "player_id": player1_id
        })
        if response.status_code == 200:
            missions_with_player = response.json()
            accepted_missions = [m for m in missions_with_player if m.get("accepted_by") == player1_id]
            if len(accepted_missions) >= 1:
                log_test("Generate missions with player_id", "PASS", f"Found {len(accepted_missions)} missions accepted by Player1")
                test_results.append(True)
            else:
                log_test("Generate missions with player_id", "FAIL", "No missions marked as accepted by Player1")
                test_results.append(False)
        else:
            log_test("Generate missions with player_id", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            
        # Test 10: Test generate_missions with player_id parameter for Player2
        print(f"\n10. Testing generate_missions with player_id for Player2...")
        response = requests.get(f"{API_BASE}/missions/generate", params={
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 5,
            "player_id": player2_id
        })
        if response.status_code == 200:
            missions_with_player2 = response.json()
            accepted_missions_p2 = [m for m in missions_with_player2 if m.get("accepted_by") == player2_id]
            if len(accepted_missions_p2) >= 1:
                log_test("Generate missions with player_id (Player2)", "PASS", f"Found {len(accepted_missions_p2)} missions accepted by Player2")
                test_results.append(True)
            else:
                log_test("Generate missions with player_id (Player2)", "FAIL", "No missions marked as accepted by Player2")
                test_results.append(False)
        else:
            log_test("Generate missions with player_id (Player2)", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)

    except requests.exceptions.RequestException as e:
        log_test("Network Connection", "FAIL", f"Connection error: {e}")
        test_results.append(False)
    except Exception as e:
        log_test("Unexpected Error", "FAIL", f"Error: {e}")
        test_results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 MULTI-PLAYER MISSION SYSTEM TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"Tests passed: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("🎉 MULTI-PLAYER MISSION SYSTEM: ALL TESTS PASSED!")
        print("✅ Multiple players can accept the same mission")
        print("✅ Independent progress tracking working")
        print("✅ Re-acceptance prevention working")
        print("✅ Active missions API working for both players")
        print("✅ Generate missions with player_id parameter working")
    elif success_rate >= 80:
        print("⚠️ MULTI-PLAYER MISSION SYSTEM: MOSTLY WORKING")
        print("Some issues found but core functionality appears to work")
    else:
        print("❌ MULTI-PLAYER MISSION SYSTEM: CRITICAL ISSUES FOUND")
        print("Major problems detected that need attention")
    
    return success_rate == 100

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)