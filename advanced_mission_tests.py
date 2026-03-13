#!/usr/bin/env python3
"""
Advanced Multi-player Mission System Tests
Tests edge cases and mission completion flow with independent progress tracking.
"""

import requests
import json
import sys

# Backend URL from frontend/.env
BACKEND_URL = "https://nexus-battle-quest.preview.emergentagent.com"
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
    print("🔥 ADVANCED MULTI-PLAYER MISSION SYSTEM TESTS")
    print("=" * 60)
    
    test_results = []
    
    try:
        # Setup: Create players
        print("\nSetup: Creating test players...")
        
        # Player A
        response = create_player("AdvancedTestA", "street_soldier")
        if response.status_code != 200:
            print("❌ Failed to create Player A")
            return False
        playerA_id = response.json()["id"]
        
        # Player B
        response = create_player("AdvancedTestB", "hacker")
        if response.status_code != 200:
            print("❌ Failed to create Player B")
            return False
        playerB_id = response.json()["id"]
        
        # Player C
        response = create_player("AdvancedTestC", "enforcer")
        if response.status_code != 200:
            print("❌ Failed to create Player C")
            return False
        playerC_id = response.json()["id"]
        
        print(f"✅ Created 3 test players: {playerA_id[:8]}..., {playerB_id[:8]}..., {playerC_id[:8]}...")
        
        # Test 1: Generate missions for all players to accept
        print("\n1. Generating missions...")
        response = requests.get(f"{API_BASE}/missions/generate", params={
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 5
        })
        
        if response.status_code == 200:
            missions = response.json()
            if len(missions) >= 2:
                mission1_id = missions[0]["id"]
                mission2_id = missions[1]["id"]
                log_test("Generate missions for testing", "PASS", f"Using missions: {missions[0]['title']}, {missions[1]['title']}")
                test_results.append(True)
            else:
                log_test("Generate missions for testing", "FAIL", "Need at least 2 missions")
                test_results.append(False)
                return
        else:
            log_test("Generate missions for testing", "FAIL", f"Status: {response.status_code}")
            test_results.append(False)
            return
            
        # Test 2: Three players accept the same mission
        print(f"\n2. Testing 3 players accepting same mission {mission1_id[:8]}...")
        
        # Player A accepts
        response = requests.post(f"{API_BASE}/missions/{mission1_id}/accept", params={"player_id": playerA_id})
        if response.status_code != 200:
            log_test("Player A accepts mission", "FAIL", f"Status: {response.status_code}")
            test_results.append(False)
        else:
            log_test("Player A accepts mission", "PASS", "Success")
        
        # Player B accepts same mission
        response = requests.post(f"{API_BASE}/missions/{mission1_id}/accept", params={"player_id": playerB_id})
        if response.status_code != 200:
            log_test("Player B accepts same mission", "FAIL", f"Status: {response.status_code}")
            test_results.append(False)
        else:
            log_test("Player B accepts same mission", "PASS", "Success")
        
        # Player C accepts same mission
        response = requests.post(f"{API_BASE}/missions/{mission1_id}/accept", params={"player_id": playerC_id})
        if response.status_code != 200:
            log_test("Player C accepts same mission", "FAIL", f"Status: {response.status_code}")
            test_results.append(False)
        else:
            log_test("Player C accepts same mission", "PASS", "3 players successfully accepted same mission")
            test_results.append(True)
            
        # Test 3: Update progress for each player independently
        print(f"\n3. Testing independent progress updates...")
        
        # Get mission details to know the goal_target
        missions_data = requests.get(f"{API_BASE}/missions/active/{playerA_id}").json()
        mission_data = missions_data[0] if missions_data else {}
        goal_target = mission_data.get("goal_target", 10)
        
        # Player A updates progress to 3
        response = requests.put(f"{API_BASE}/missions/{mission1_id}/progress", params={
            "player_id": playerA_id,
            "progress": 3
        })
        if response.status_code == 200:
            playerA_progress = response.json()["progress"]
            log_test("Player A progress update", "PASS", f"Progress: {playerA_progress}")
        else:
            log_test("Player A progress update", "FAIL", f"Status: {response.status_code}")
            test_results.append(False)
            return
        
        # Player B updates progress to 7
        response = requests.put(f"{API_BASE}/missions/{mission1_id}/progress", params={
            "player_id": playerB_id,
            "progress": 7
        })
        if response.status_code == 200:
            playerB_progress = response.json()["progress"]
            log_test("Player B progress update", "PASS", f"Progress: {playerB_progress}")
        else:
            log_test("Player B progress update", "FAIL", f"Status: {response.status_code}")
            test_results.append(False)
            return
            
        # Player C keeps progress at 0 (no update)
        
        # Verify independent progress tracking
        if playerA_progress == 3 and playerB_progress == 7:
            log_test("Independent progress verification", "PASS", f"A: {playerA_progress}, B: {playerB_progress}, C: 0")
            test_results.append(True)
        else:
            log_test("Independent progress verification", "FAIL", f"Expected A:3, B:7, got A:{playerA_progress}, B:{playerB_progress}")
            test_results.append(False)
            
        # Test 4: Check active missions for each player show their specific progress
        print(f"\n4. Verifying active missions show correct per-player progress...")
        
        # Player A's view
        response = requests.get(f"{API_BASE}/missions/active/{playerA_id}")
        if response.status_code == 200:
            playerA_missions = response.json()
            if len(playerA_missions) > 0 and playerA_missions[0]["goal_progress"] == 3:
                log_test("Player A sees own progress", "PASS", f"Sees progress: {playerA_missions[0]['goal_progress']}")
            else:
                log_test("Player A sees own progress", "FAIL", f"Expected 3, got {playerA_missions[0]['goal_progress'] if playerA_missions else 'no missions'}")
                test_results.append(False)
        
        # Player B's view
        response = requests.get(f"{API_BASE}/missions/active/{playerB_id}")
        if response.status_code == 200:
            playerB_missions = response.json()
            if len(playerB_missions) > 0 and playerB_missions[0]["goal_progress"] == 7:
                log_test("Player B sees own progress", "PASS", f"Sees progress: {playerB_missions[0]['goal_progress']}")
            else:
                log_test("Player B sees own progress", "FAIL", f"Expected 7, got {playerB_missions[0]['goal_progress'] if playerB_missions else 'no missions'}")
                test_results.append(False)
                
        # Player C's view
        response = requests.get(f"{API_BASE}/missions/active/{playerC_id}")
        if response.status_code == 200:
            playerC_missions = response.json()
            if len(playerC_missions) > 0 and playerC_missions[0]["goal_progress"] == 0:
                log_test("Player C sees own progress", "PASS", f"Sees progress: {playerC_missions[0]['goal_progress']}")
                test_results.append(True)
            else:
                log_test("Player C sees own progress", "FAIL", f"Expected 0, got {playerC_missions[0]['goal_progress'] if playerC_missions else 'no missions'}")
                test_results.append(False)
        
        # Test 5: Complete mission as Player B, verify others still have it
        print(f"\n5. Testing mission completion with remaining players...")
        
        # Update Player B to completion
        response = requests.put(f"{API_BASE}/missions/{mission1_id}/progress", params={
            "player_id": playerB_id,
            "progress": goal_target
        })
        
        # Complete mission as Player B
        response = requests.post(f"{API_BASE}/missions/{mission1_id}/complete", params={"player_id": playerB_id})
        if response.status_code == 200:
            log_test("Player B completes mission", "PASS", "Mission completed successfully")
        else:
            log_test("Player B completes mission", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            test_results.append(False)
            
        # Verify Player B no longer has the mission
        response = requests.get(f"{API_BASE}/missions/active/{playerB_id}")
        playerB_active_after = response.json()
        if len(playerB_active_after) == 0:
            log_test("Player B mission removed after completion", "PASS", "No active missions")
        else:
            log_test("Player B mission removed after completion", "FAIL", f"Still has {len(playerB_active_after)} missions")
            test_results.append(False)
            
        # Verify Players A and C still have the mission
        response_A = requests.get(f"{API_BASE}/missions/active/{playerA_id}")
        response_C = requests.get(f"{API_BASE}/missions/active/{playerC_id}")
        
        playerA_still_has = len(response_A.json()) > 0
        playerC_still_has = len(response_C.json()) > 0
        
        if playerA_still_has and playerC_still_has:
            log_test("Other players still have mission", "PASS", "Players A and C still have active mission")
            test_results.append(True)
        else:
            log_test("Other players still have mission", "FAIL", f"A has: {playerA_still_has}, C has: {playerC_still_has}")
            test_results.append(False)
            
        # Test 6: Multiple missions per player
        print(f"\n6. Testing multiple missions per player...")
        
        # Player A accepts second mission
        response = requests.post(f"{API_BASE}/missions/{mission2_id}/accept", params={"player_id": playerA_id})
        if response.status_code == 200:
            log_test("Player A accepts second mission", "PASS", "Success")
        else:
            log_test("Player A accepts second mission", "FAIL", f"Status: {response.status_code}")
            test_results.append(False)
            
        # Check Player A now has 2 active missions
        response = requests.get(f"{API_BASE}/missions/active/{playerA_id}")
        playerA_missions_count = len(response.json())
        
        if playerA_missions_count == 2:
            log_test("Player A has multiple missions", "PASS", f"Has {playerA_missions_count} active missions")
            test_results.append(True)
        else:
            log_test("Player A has multiple missions", "FAIL", f"Expected 2, has {playerA_missions_count}")
            test_results.append(False)

    except requests.exceptions.RequestException as e:
        log_test("Network Connection", "FAIL", f"Connection error: {e}")
        test_results.append(False)
    except Exception as e:
        log_test("Unexpected Error", "FAIL", f"Error: {e}")
        test_results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ADVANCED MULTI-PLAYER MISSION TESTS SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"Advanced tests passed: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("🚀 ADVANCED FEATURES: ALL TESTS PASSED!")
        print("✅ Multiple players (3+) can accept same mission")
        print("✅ Independent progress tracking works perfectly")
        print("✅ Mission completion removes only completing player")
        print("✅ Other players retain mission after one completes")
        print("✅ Players can have multiple active missions")
        print("✅ Per-player mission views work correctly")
    elif success_rate >= 80:
        print("⚠️ ADVANCED FEATURES: MOSTLY WORKING")
        print("Some edge cases need attention")
    else:
        print("❌ ADVANCED FEATURES: CRITICAL ISSUES")
        print("Major problems in edge cases")
    
    return success_rate >= 90

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)