#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for GTA GPS RPG Game
Focuses on Fitness Tracker API functionality
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

    def test_fitness_api_comprehensive(self):
        """Test the complete fitness tracker API as specified in review request"""
        print("\n🏃 TESTING FITNESS TRACKER API")
        print("=" * 50)
        
        # Step 1: Create a player first
        self.test_create_player_for_fitness()
        
        if not self.current_player_id:
            self.log_test("Fitness API Testing", False, "Could not create test player")
            return False
            
        # Step 2: Get initial fitness data
        self.test_get_initial_fitness_data()
        
        # Step 3: Update steps to 5000
        self.test_update_steps_5000()
        
        # Step 4: Verify steps=5000 and calculations
        self.test_verify_steps_5000()
        
        # Step 5: Claim 3000 step goal
        self.test_claim_3000_step_goal()
        
        # Step 6: Verify 3000 is in claimed_goals
        self.test_verify_3000_claimed()
        
        # Step 7: Set steps to 7000 for 6000 goal test
        self.test_update_steps_7000()
        
        # Step 8: Claim 6000 step goal
        self.test_claim_6000_step_goal()
        
        # Step 9: Test error - double claim 3000
        self.test_error_double_claim_3000()
        
        # Step 10: Test error - claim 10000 with only 7000 steps
        self.test_error_insufficient_steps_10000()
        
        return True

    def test_create_player_for_fitness(self):
        """Create a test player for fitness testing"""
        print("\n📝 Creating test player for fitness testing...")
        
        # Generate unique name with timestamp
        import time
        unique_name = f"FitTest_{int(time.time())}"
        
        player_data = {
            "name": unique_name,
            "character_class": "street_soldier"
        }
        
        success, response = self.api_call("POST", "/players", json=player_data)
        
        if success and response.get("id"):
            self.current_player_id = response["id"]
            self.log_test("Create Player for Fitness", True, f"Player ID: {self.current_player_id}")
        else:
            self.log_test("Create Player for Fitness", False, f"Failed to create player: {response}")

    def test_get_initial_fitness_data(self):
        """Test GET /api/fitness/{player_id} - should return initial data"""
        print(f"\n📊 Testing GET /api/fitness/{self.current_player_id}...")
        
        success, response = self.api_call("GET", f"/fitness/{self.current_player_id}")
        
        if success:
            # Verify initial data structure
            expected_fields = ["steps", "calories", "distance_km", "claimed_goals", "goals"]
            missing_fields = [field for field in expected_fields if field not in response]
            
            if missing_fields:
                self.log_test("Get Initial Fitness Data", False, f"Missing fields: {missing_fields}")
                return
                
            # Verify initial values
            if (response.get("steps") == 0 and
                isinstance(response.get("calories"), (int, float)) and
                isinstance(response.get("distance_km"), (int, float)) and
                response.get("claimed_goals") == [] and
                len(response.get("goals", [])) == 3):
                
                self.log_test("Get Initial Fitness Data", True, 
                            f"Steps: {response['steps']}, Goals: {len(response['goals'])}")
            else:
                self.log_test("Get Initial Fitness Data", False, 
                            f"Invalid initial data: {response}")
        else:
            self.log_test("Get Initial Fitness Data", False, f"API call failed: {response}")

    def test_update_steps_5000(self):
        """Test PUT /api/fitness/{player_id}/steps?steps=5000"""
        print(f"\n🚶 Testing PUT /api/fitness/{self.current_player_id}/steps?steps=5000...")
        
        success, response = self.api_call("PUT", f"/fitness/{self.current_player_id}/steps", 
                                        params={"steps": 5000})
        
        if success and response.get("steps") == 5000:
            self.log_test("Update Steps to 5000", True, f"Steps updated to: {response['steps']}")
        else:
            self.log_test("Update Steps to 5000", False, f"Failed to update steps: {response}")

    def test_verify_steps_5000(self):
        """Verify steps=5000 and that calories/distance are calculated correctly"""
        print(f"\n🔍 Verifying steps=5000 and calculations...")
        
        success, response = self.api_call("GET", f"/fitness/{self.current_player_id}")
        
        if success:
            steps = response.get("steps", 0)
            calories = response.get("calories", 0)
            distance_km = response.get("distance_km", 0)
            
            if steps == 5000:
                # Check if calories and distance are reasonable (non-zero)
                if calories > 0 and distance_km > 0:
                    self.log_test("Verify Steps 5000 Calculations", True, 
                                f"Steps: {steps}, Calories: {calories}, Distance: {distance_km}km")
                else:
                    self.log_test("Verify Steps 5000 Calculations", False, 
                                f"Invalid calculations - Calories: {calories}, Distance: {distance_km}")
            else:
                self.log_test("Verify Steps 5000 Calculations", False, 
                            f"Steps not updated correctly: {steps}")
        else:
            self.log_test("Verify Steps 5000 Calculations", False, f"API call failed: {response}")

    def test_claim_3000_step_goal(self):
        """Test POST /api/fitness/{player_id}/claim/3000 - should succeed"""
        print(f"\n🏆 Testing POST /api/fitness/{self.current_player_id}/claim/3000...")
        
        success, response = self.api_call("POST", f"/fitness/{self.current_player_id}/claim/3000")
        
        if success:
            # Should return success message and XP reward
            if "xp" in response or "XP" in str(response) or "reward" in str(response).lower():
                self.log_test("Claim 3000 Step Goal", True, f"Goal claimed successfully: {response}")
            else:
                self.log_test("Claim 3000 Step Goal", False, f"Unexpected response: {response}")
        else:
            self.log_test("Claim 3000 Step Goal", False, f"Failed to claim goal: {response}")

    def test_verify_3000_claimed(self):
        """Verify 3000 is in claimed_goals"""
        print(f"\n✅ Verifying 3000 is in claimed_goals...")
        
        success, response = self.api_call("GET", f"/fitness/{self.current_player_id}")
        
        if success:
            claimed_goals = response.get("claimed_goals", [])
            if 3000 in claimed_goals:
                self.log_test("Verify 3000 in Claimed Goals", True, f"Claimed goals: {claimed_goals}")
            else:
                self.log_test("Verify 3000 in Claimed Goals", False, 
                            f"3000 not found in claimed_goals: {claimed_goals}")
        else:
            self.log_test("Verify 3000 in Claimed Goals", False, f"API call failed: {response}")

    def test_update_steps_7000(self):
        """Set steps to 7000 for 6000 goal test"""
        print(f"\n🏃 Testing PUT /api/fitness/{self.current_player_id}/steps?steps=7000...")
        
        success, response = self.api_call("PUT", f"/fitness/{self.current_player_id}/steps", 
                                        params={"steps": 7000})
        
        if success and response.get("steps") == 7000:
            self.log_test("Update Steps to 7000", True, f"Steps updated to: {response['steps']}")
        else:
            self.log_test("Update Steps to 7000", False, f"Failed to update steps: {response}")

    def test_claim_6000_step_goal(self):
        """Test claiming 6000 step goal with 7000 steps"""
        print(f"\n🏆 Testing POST /api/fitness/{self.current_player_id}/claim/6000...")
        
        success, response = self.api_call("POST", f"/fitness/{self.current_player_id}/claim/6000")
        
        if success:
            self.log_test("Claim 6000 Step Goal", True, f"Goal claimed successfully: {response}")
        else:
            self.log_test("Claim 6000 Step Goal", False, f"Failed to claim goal: {response}")

    def test_error_double_claim_3000(self):
        """Test error: Try claiming 3000 again - should fail with 'Already claimed'"""
        print(f"\n🚫 Testing double claim error for 3000 steps...")
        
        success, response = self.api_call("POST", f"/fitness/{self.current_player_id}/claim/3000")
        
        # This should fail
        if not success:
            error_text = str(response.get("error", "")).lower()
            if "already" in error_text or "claimed" in error_text:
                self.log_test("Error: Double Claim 3000", True, f"Correctly rejected: {response}")
            else:
                self.log_test("Error: Double Claim 3000", False, f"Wrong error message: {response}")
        else:
            self.log_test("Error: Double Claim 3000", False, f"Should have failed but succeeded: {response}")

    def test_error_insufficient_steps_10000(self):
        """Test error: Try claiming 10000 with only 7000 steps - should fail"""
        print(f"\n🚫 Testing insufficient steps error for 10000 goal...")
        
        success, response = self.api_call("POST", f"/fitness/{self.current_player_id}/claim/10000")
        
        # This should fail
        if not success:
            error_text = str(response.get("error", "")).lower()
            if ("need" in error_text and "10000" in error_text) or ("insufficient" in error_text):
                self.log_test("Error: Insufficient Steps 10000", True, f"Correctly rejected: {response}")
            else:
                self.log_test("Error: Insufficient Steps 10000", False, f"Wrong error message: {response}")
        else:
            self.log_test("Error: Insufficient Steps 10000", False, f"Should have failed but succeeded: {response}")

    def run_all_tests(self):
        """Run all fitness tracker tests"""
        print("🎮 STARTING COMPREHENSIVE FITNESS TRACKER API TESTING")
        print("=" * 60)
        
        # Test fitness tracker functionality
        self.test_fitness_api_comprehensive()
        
        # Print summary
        self.print_summary()
        
        return len([r for r in self.test_results if r["success"]]) == len(self.test_results)

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🎯 FITNESS TRACKER API TEST SUMMARY")
        print("=" * 60)
        
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
        print("\n🎉 ALL FITNESS TRACKER TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n💥 SOME FITNESS TRACKER TESTS FAILED!")
        sys.exit(1)