#!/usr/bin/env python3
"""
Backend API Testing for GTA GPS RPG Game
Test the two new mission features:
1. GET /api/missions/active/{player_id} - Returns all active/accepted missions for a player
2. POST /api/missions/{mission_id}/accept - Updated to prevent re-acceptance
"""

import requests
import json
import time
from typing import Dict, Any, List

# Backend URL from frontend/.env
BASE_URL = "https://gta-rpg-quest.preview.emergentagent.com/api"

class MissionTestSuite:
    def __init__(self):
        self.base_url = BASE_URL
        self.test_results = []
        self.created_players = []
        self.generated_missions = []
        
    def log_result(self, test_name: str, success: bool, message: str, data: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "data": data,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if data and not success:
            print(f"    Data: {json.dumps(data, indent=2)}")
    
    def create_player(self, name: str, character_class: str) -> Dict[str, Any]:
        """Create a test player"""
        try:
            response = requests.post(f"{self.base_url}/players", 
                json={"name": name, "character_class": character_class},
                timeout=30)
            
            if response.status_code == 200:
                player = response.json()
                self.created_players.append(player)
                self.log_result(f"Create Player '{name}'", True, 
                              f"Player created with ID: {player['id']}")
                return player
            else:
                self.log_result(f"Create Player '{name}'", False, 
                              f"Failed to create player: {response.status_code}", 
                              response.text)
                return None
        except Exception as e:
            self.log_result(f"Create Player '{name}'", False, 
                          f"Exception: {str(e)}")
            return None
    
    def generate_missions(self, latitude: float, longitude: float, player_level: int) -> List[Dict[str, Any]]:
        """Generate missions for testing"""
        try:
            response = requests.get(f"{self.base_url}/missions/generate", 
                params={
                    "latitude": latitude,
                    "longitude": longitude, 
                    "player_level": player_level
                },
                timeout=30)
            
            if response.status_code == 200:
                missions = response.json()
                self.generated_missions = missions
                self.log_result("Generate Missions", True, 
                              f"Generated {len(missions)} missions")
                return missions
            else:
                self.log_result("Generate Missions", False, 
                              f"Failed to generate missions: {response.status_code}", 
                              response.text)
                return []
        except Exception as e:
            self.log_result("Generate Missions", False, 
                          f"Exception: {str(e)}")
            return []
    
    def accept_mission(self, mission_id: str, player_id: str) -> Dict[str, Any]:
        """Accept a mission"""
        try:
            response = requests.post(f"{self.base_url}/missions/{mission_id}/accept", 
                params={"player_id": player_id},
                timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                self.log_result("Accept Mission", True, 
                              f"Mission accepted: {result.get('message', 'Success')}")
                return result
            else:
                self.log_result("Accept Mission", False, 
                              f"Failed to accept mission: {response.status_code} - {response.text}")
                return {"error": response.text, "status_code": response.status_code}
        except Exception as e:
            self.log_result("Accept Mission", False, 
                          f"Exception: {str(e)}")
            return {"error": str(e)}
    
    def get_active_missions(self, player_id: str) -> List[Dict[str, Any]]:
        """Get active missions for a player"""
        try:
            response = requests.get(f"{self.base_url}/missions/active/{player_id}", 
                timeout=30)
            
            if response.status_code == 200:
                missions = response.json()
                self.log_result("Get Active Missions", True, 
                              f"Retrieved {len(missions)} active missions")
                return missions
            else:
                self.log_result("Get Active Missions", False, 
                              f"Failed to get active missions: {response.status_code}", 
                              response.text)
                return []
        except Exception as e:
            self.log_result("Get Active Missions", False, 
                          f"Exception: {str(e)}")
            return []
    
    def test_new_mission_features(self):
        """
        Test the two new mission features as specified in the review request:
        1. Create a player
        2. Generate missions
        3. Accept a mission
        4. Verify GET /api/missions/active returns the accepted mission
        5. Try accepting same mission again - verify 400 error
        6. Create second player and try to accept same mission - verify 400 error
        7. Accept second mission with first player - verify GET returns both
        """
        print(f"\n🧪 Starting Mission Features Test Suite")
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Step 1: Create first player
        print("\n📋 Step 1: Create first test player")
        player1 = self.create_player("MissionTest", "street_soldier")
        if not player1:
            print("❌ Cannot continue without first player")
            return False
        
        # Step 2: Generate missions
        print("\n📋 Step 2: Generate missions at Times Square NYC")
        missions = self.generate_missions(40.758, -73.9855, 5)
        if not missions:
            print("❌ Cannot continue without missions")
            return False
        
        if len(missions) == 0:
            self.log_result("Mission Generation Check", False, "No missions generated")
            return False
        
        # Get first mission for testing
        mission1 = missions[0]
        mission1_id = mission1.get('id')
        
        if not mission1_id:
            self.log_result("Mission ID Check", False, "First mission has no ID")
            return False
        
        print(f"\n📝 Using mission: {mission1.get('title', 'Unknown')} (ID: {mission1_id})")
        
        # Step 3: Accept first mission with first player
        print("\n📋 Step 3: Accept mission with first player")
        accept_result1 = self.accept_mission(mission1_id, player1['id'])
        
        if "error" in accept_result1:
            print("❌ Failed to accept first mission")
            return False
        
        # Step 4: Verify GET /api/missions/active returns the accepted mission
        print("\n📋 Step 4: Verify active missions endpoint returns accepted mission")
        active_missions = self.get_active_missions(player1['id'])
        
        # Check if accepted mission is in the active list
        found_mission = False
        for mission in active_missions:
            if mission.get('id') == mission1_id:
                found_mission = True
                break
        
        if found_mission:
            self.log_result("Active Mission Verification", True, 
                          f"Accepted mission found in active missions list")
        else:
            self.log_result("Active Mission Verification", False, 
                          f"Accepted mission NOT found in active missions list. Found {len(active_missions)} missions")
            return False
        
        # Step 5: Try accepting same mission again - verify 400 error
        print("\n📋 Step 5: Try accepting same mission again (should fail)")
        accept_result2 = self.accept_mission(mission1_id, player1['id'])
        
        # This should fail with 400 error
        if "error" in accept_result2 and accept_result2.get("status_code") == 400:
            error_msg = accept_result2["error"]
            if "already accepted" in error_msg.lower():
                self.log_result("Prevent Re-acceptance Test", True, 
                              f"Correctly prevented re-acceptance: {error_msg}")
            else:
                self.log_result("Prevent Re-acceptance Test", False, 
                              f"Wrong error message: {error_msg}")
        else:
            self.log_result("Prevent Re-acceptance Test", False, 
                          f"Should have failed with 400 error, got: {accept_result2}")
            return False
        
        # Step 6: Create second player and try to accept same mission
        print("\n📋 Step 6: Create second player and try to accept same mission")
        player2 = self.create_player("MissionTest2", "hacker")
        if not player2:
            print("❌ Cannot create second player")
            return False
        
        accept_result3 = self.accept_mission(mission1_id, player2['id'])
        
        # This should fail with 400 error about mission being taken by another player
        if "error" in accept_result3 and accept_result3.get("status_code") == 400:
            error_msg = accept_result3["error"]
            if "already taken by another player" in error_msg.lower():
                self.log_result("Prevent Other Player Acceptance Test", True, 
                              f"Correctly prevented acceptance by other player: {error_msg}")
            else:
                self.log_result("Prevent Other Player Acceptance Test", False, 
                              f"Wrong error message: {error_msg}")
        else:
            self.log_result("Prevent Other Player Acceptance Test", False, 
                          f"Should have failed with 400 error, got: {accept_result3}")
            return False
        
        # Step 7: Accept a second mission with first player, verify GET returns both
        print("\n📋 Step 7: Accept second mission with first player")
        if len(missions) < 2:
            self.log_result("Second Mission Test", False, "Need at least 2 missions for this test")
            return False
        
        mission2 = missions[1]
        mission2_id = mission2.get('id')
        
        if not mission2_id:
            self.log_result("Second Mission ID Check", False, "Second mission has no ID")
            return False
        
        print(f"\n📝 Using second mission: {mission2.get('title', 'Unknown')} (ID: {mission2_id})")
        
        accept_result4 = self.accept_mission(mission2_id, player1['id'])
        
        if "error" in accept_result4:
            print("❌ Failed to accept second mission")
            return False
        
        # Verify both missions are now active
        print("\n📋 Step 8: Verify both missions are in active missions list")
        active_missions_final = self.get_active_missions(player1['id'])
        
        mission1_found = False
        mission2_found = False
        
        for mission in active_missions_final:
            if mission.get('id') == mission1_id:
                mission1_found = True
            if mission.get('id') == mission2_id:
                mission2_found = True
        
        if mission1_found and mission2_found:
            self.log_result("Multiple Active Missions Test", True, 
                          f"Both missions found in active list (total: {len(active_missions_final)})")
        else:
            self.log_result("Multiple Active Missions Test", False, 
                          f"Missing missions: mission1={mission1_found}, mission2={mission2_found}")
            return False
        
        return True
    
    def run_all_tests(self):
        """Run all tests and return summary"""
        print("🚀 Starting GTA GPS RPG Mission Features Test Suite")
        print(f"Target Backend: {self.base_url}")
        
        success = self.test_new_mission_features()
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['message']}")
        
        if success:
            print("\n🎉 ALL MISSION FEATURE TESTS PASSED!")
        else:
            print("\n💥 SOME TESTS FAILED - Check details above")
        
        return success

if __name__ == "__main__":
    suite = MissionTestSuite()
    success = suite.run_all_tests()
    exit(0 if success else 1)