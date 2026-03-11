#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for GTA GPS RPG Game
Focuses on Phone Booth Mission System functionality
"""

import requests
import json
import uuid
import time
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://real-world-raid-game.preview.emergentagent.com/api"

class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.current_player_id = None
        self.generated_missions = []
        self.accepted_mission_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def api_call(self, method: str, endpoint: str, **kwargs) -> tuple[bool, Dict[Any, Any]]:
        """Make API call and return success status and response data"""
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"Making {method} request to: {url}")
            
            response = self.session.request(method, url, **kwargs)
            
            print(f"Response Status: {response.status_code}")
            if response.text:
                print(f"Response Body: {response.text[:500]}...")
            
            if response.status_code >= 400:
                return False, {"error": response.text, "status_code": response.status_code}
                
            try:
                data = response.json() if response.text else {}
                return True, data
            except json.JSONDecodeError:
                return True, {"text": response.text}
                
        except Exception as e:
            print(f"Error making API call: {e}")
            return False, {"error": str(e)}

    def test_phone_booth_mission_system(self):
        """Test the complete phone booth mission system as specified in review request"""
        print("\n📞 TESTING PHONE BOOTH MISSION SYSTEM")
        print("=" * 60)
        
        # Step 1: Create a player first
        self.test_create_player_for_missions()
        
        if not self.current_player_id:
            self.log_test("Mission System Testing", False, "Could not create test player")
            return False
            
        # Step 2: Generate missions at specific coordinates (NYC Times Square)
        self.test_generate_missions()
        
        # Step 3: Accept a mission
        self.test_accept_mission()
        
        # Step 4: Update mission progress
        self.test_update_mission_progress()
        
        # Step 5: Complete mission when goal met
        self.test_complete_mission_when_goal_met()
        
        # Step 6: Test cannot complete if goal not met
        self.test_cannot_complete_if_goal_not_met()
        
        return True

    def test_create_player_for_missions(self):
        """Create a test player for mission testing"""
        print("\n📝 Creating test player for mission testing...")
        
        # Generate unique name with timestamp
        unique_name = f"PhoneTest_{int(time.time())}"
        
        player_data = {
            "name": unique_name,
            "character_class": "street_soldier"
        }
        
        success, response = self.api_call("POST", "/players", json=player_data)
        
        if success and response.get("id"):
            self.current_player_id = response["id"]
            self.log_test("Create Player for Missions", True, f"Player ID: {self.current_player_id}")
        else:
            self.log_test("Create Player for Missions", False, f"Failed to create player: {response}")

    def test_generate_missions(self):
        """Test GET /api/missions/generate with specific coordinates and player level"""
        print("\n🎯 Testing mission generation at Times Square NYC...")
        
        # Use Times Square coordinates as specified in review request
        latitude = 40.758
        longitude = -73.9855
        player_level = 5
        
        success, response = self.api_call("GET", f"/missions/generate", 
                                        params={
                                            "latitude": latitude,
                                            "longitude": longitude,
                                            "player_level": player_level
                                        })
        
        if success:
            missions = response if isinstance(response, list) else []
            
            if len(missions) >= 1:
                # Store missions for later tests
                self.generated_missions = missions
                
                # Verify mission structure
                mission = missions[0]
                required_fields = ["id", "mission_type", "goal_target", "goal_progress", "title", "description", "rewards"]
                missing_fields = [field for field in required_fields if field not in mission]
                
                if missing_fields:
                    self.log_test("Generate Missions - Structure", False, f"Missing fields: {missing_fields}")
                    return
                
                # Check mission types
                valid_types = ["defeat_monsters", "travel_distance", "walk_steps"]
                mission_type = mission.get("mission_type")
                
                if mission_type not in valid_types:
                    self.log_test("Generate Missions - Type", False, f"Invalid mission type: {mission_type}")
                    return
                
                # Check goal_progress starts at 0
                if mission.get("goal_progress") != 0:
                    self.log_test("Generate Missions - Progress", False, f"Goal progress should start at 0, got: {mission.get('goal_progress')}")
                    return
                
                # Check goal_target is numeric
                goal_target = mission.get("goal_target")
                if not isinstance(goal_target, (int, float)) or goal_target <= 0:
                    self.log_test("Generate Missions - Target", False, f"Invalid goal_target: {goal_target}")
                    return
                
                self.log_test("Generate Missions", True, 
                            f"Generated {len(missions)} missions. Sample: {mission['mission_type']} - {mission['title']} (target: {goal_target})")
            else:
                self.log_test("Generate Missions", False, f"Should return at least 1 mission, got: {len(missions)}")
        else:
            self.log_test("Generate Missions", False, f"API call failed: {response}")

    def test_accept_mission(self):
        """Test POST /api/missions/{mission_id}/accept"""
        print(f"\n✅ Testing mission acceptance...")
        
        if not self.generated_missions:
            self.log_test("Accept Mission", False, "No generated missions available")
            return
        
        mission = self.generated_missions[0]
        mission_id = mission["id"]
        self.accepted_mission_id = mission_id
        
        success, response = self.api_call("POST", f"/missions/{mission_id}/accept", 
                                        params={"player_id": self.current_player_id})
        
        if success:
            # Should return success message
            message = response.get("message", "")
            if "accepted" in message.lower() or "success" in str(response).lower():
                self.log_test("Accept Mission", True, f"Mission accepted: {message}")
            else:
                self.log_test("Accept Mission", False, f"Unexpected response: {response}")
        else:
            self.log_test("Accept Mission", False, f"Failed to accept mission: {response}")

    def test_update_mission_progress(self):
        """Test PUT /api/missions/{mission_id}/progress"""
        print(f"\n📈 Testing mission progress update...")
        
        if not self.accepted_mission_id:
            self.log_test("Update Mission Progress", False, "No accepted mission available")
            return
        
        # Update progress to 3
        progress_value = 3
        
        success, response = self.api_call("PUT", f"/missions/{self.accepted_mission_id}/progress", 
                                        params={
                                            "player_id": self.current_player_id,
                                            "progress": progress_value
                                        })
        
        if success:
            # Should return updated progress
            returned_progress = response.get("progress")
            target = response.get("target")
            
            if returned_progress == progress_value:
                self.log_test("Update Mission Progress", True, 
                            f"Progress updated to {returned_progress}/{target}")
            else:
                self.log_test("Update Mission Progress", False, 
                            f"Expected progress {progress_value}, got {returned_progress}")
        else:
            self.log_test("Update Mission Progress", False, f"Failed to update progress: {response}")

    def test_complete_mission_when_goal_met(self):
        """Test POST /api/missions/{mission_id}/complete when goal is met"""
        print(f"\n🏆 Testing mission completion when goal is met...")
        
        if not self.accepted_mission_id:
            self.log_test("Complete Mission (Goal Met)", False, "No accepted mission available")
            return
        
        # First, get the mission's goal target
        original_mission = None
        for mission in self.generated_missions:
            if mission["id"] == self.accepted_mission_id:
                original_mission = mission
                break
        
        if not original_mission:
            self.log_test("Complete Mission (Goal Met)", False, "Original mission not found")
            return
        
        goal_target = original_mission["goal_target"]
        
        # Set progress to match goal target
        success, response = self.api_call("PUT", f"/missions/{self.accepted_mission_id}/progress", 
                                        params={
                                            "player_id": self.current_player_id,
                                            "progress": goal_target
                                        })
        
        if not success:
            self.log_test("Complete Mission (Goal Met)", False, f"Failed to set progress to goal: {response}")
            return
        
        # Now try to complete the mission
        success, response = self.api_call("POST", f"/missions/{self.accepted_mission_id}/complete", 
                                        params={"player_id": self.current_player_id})
        
        if success:
            # Should return rewards
            rewards = response.get("rewards", {})
            if rewards and ("cash" in rewards or "xp" in rewards):
                self.log_test("Complete Mission (Goal Met)", True, f"Mission completed with rewards: {rewards}")
            else:
                self.log_test("Complete Mission (Goal Met)", True, f"Mission completed: {response}")
        else:
            error_msg = response.get("error", str(response))
            self.log_test("Complete Mission (Goal Met)", False, f"Failed to complete mission: {error_msg}")

    def test_cannot_complete_if_goal_not_met(self):
        """Test that mission completion fails with 'Goal not met' when progress < goal_target"""
        print(f"\n🚫 Testing mission completion failure when goal not met...")
        
        # Generate a new mission for this test
        latitude = 40.758
        longitude = -73.9855
        player_level = 5
        
        success, response = self.api_call("GET", f"/missions/generate", 
                                        params={
                                            "latitude": latitude,
                                            "longitude": longitude,
                                            "player_level": player_level
                                        })
        
        if not success or not response:
            self.log_test("Cannot Complete (Goal Not Met)", False, "Failed to generate new mission")
            return
        
        missions = response if isinstance(response, list) else []
        if not missions:
            self.log_test("Cannot Complete (Goal Not Met)", False, "No missions generated")
            return
        
        # Accept the new mission
        new_mission = missions[0]
        new_mission_id = new_mission["id"]
        
        success, response = self.api_call("POST", f"/missions/{new_mission_id}/accept", 
                                        params={"player_id": self.current_player_id})
        
        if not success:
            self.log_test("Cannot Complete (Goal Not Met)", False, f"Failed to accept new mission: {response}")
            return
        
        # Don't update progress (should remain at 0)
        # Try to complete the mission without meeting the goal
        success, response = self.api_call("POST", f"/missions/{new_mission_id}/complete", 
                                        params={"player_id": self.current_player_id})
        
        # This should fail
        if not success:
            error_text = str(response.get("error", "")).lower()
            if "goal not met" in error_text or "not met" in error_text:
                self.log_test("Cannot Complete (Goal Not Met)", True, f"Correctly rejected: {response}")
            else:
                self.log_test("Cannot Complete (Goal Not Met)", False, f"Wrong error message: {response}")
        else:
            self.log_test("Cannot Complete (Goal Not Met)", False, f"Should have failed but succeeded: {response}")

    def run_all_tests(self):
        """Run all phone booth mission system tests"""
        print("📞 STARTING COMPREHENSIVE PHONE BOOTH MISSION SYSTEM TESTING")
        print("=" * 70)
        
        # Test phone booth mission functionality
        self.test_phone_booth_mission_system()
        
        # Print summary
        self.print_summary()
        
        return len([r for r in self.test_results if r["success"]]) == len(self.test_results)

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("🎯 PHONE BOOTH MISSION SYSTEM TEST SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n✅ PASSED TESTS:")
        for result in self.test_results:
            if result["success"]:
                print(f"  - {result['test']}")

if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL PHONE BOOTH MISSION TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n💥 SOME PHONE BOOTH MISSION TESTS FAILED!")
        sys.exit(1)