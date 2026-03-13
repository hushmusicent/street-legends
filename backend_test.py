#!/usr/bin/env python3
"""
GTA GPS RPG Backend API Testing Suite
Testing Territory Income Features and Battle System
"""

import requests
import json
import time
import sys
from datetime import datetime

# Backend URL from frontend/.env
BASE_URL = "https://nexus-battle-quest.preview.emergentagent.com/api"

# Test configuration
TEST_COORDS = {
    "latitude": 40.758,
    "longitude": -73.9855,
    "player_level": 1
}

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(message, color=Colors.WHITE):
    """Print colored log message"""
    print(f"{color}{message}{Colors.END}")

def log_success(message):
    log(f"✅ {message}", Colors.GREEN)

def log_error(message):
    log(f"❌ {message}", Colors.RED)

def log_info(message):
    log(f"ℹ️  {message}", Colors.BLUE)

def log_warning(message):
    log(f"⚠️  {message}", Colors.YELLOW)

def log_test_start(test_name):
    log(f"\n🧪 TESTING: {test_name}", Colors.CYAN + Colors.BOLD)
    print("=" * 60)

def make_request(method, endpoint, data=None, params=None):
    """Make HTTP request and handle errors"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=data, params=params)
        elif method == "PUT":
            response = requests.put(url, json=data, params=params)
        else:
            log_error(f"Unsupported method: {method}")
            return None
        
        log_info(f"{method} {endpoint} -> {response.status_code}")
        
        if response.status_code >= 400:
            log_error(f"HTTP Error: {response.status_code} - {response.text}")
            return None
        
        return response.json()
    except Exception as e:
        log_error(f"Request failed: {e}")
        return None

def test_1_register_user():
    """Test 1: Register new user as specified in review request"""
    log_test_start("User Registration")
    
    register_data = {
        "username": "incometest",
        "password": "test123",
        "name": "IncomeTester",
        "character_class": "street_soldier"
    }
    
    log_info(f"Registering user: {register_data['username']}")
    result = make_request("POST", "/auth/register", register_data)
    
    if result and "id" in result:
        log_success(f"User registered successfully! Player ID: {result['id']}")
        log_info(f"Character: {result['name']} (Level {result['level']})")
        log_info(f"Class: {result['character_class']} | Cash: ${result['cash']}")
        return result["id"]
    else:
        log_error("Failed to register user")
        return None

def test_2_territory_income_preview(player_id):
    """Test 2: Territory Income Preview endpoint"""
    log_test_start("Territory Income Preview")
    
    log_info(f"Testing GET /territories/income-preview/{player_id}")
    result = make_request("GET", f"/territories/income-preview/{player_id}")
    
    if result is not None:
        log_success("Income preview endpoint working!")
        log_info(f"Available Income: ${result.get('available_income', 0)}")
        log_info(f"Ready Territories: {result.get('ready_territories', 0)}")
        log_info(f"Total Territories: {result.get('total_territories', 0)}")
        log_info(f"Next Collection Hours: {result.get('next_collection_hours', 0)}")
        
        # Verify expected fields exist
        required_fields = ["available_income", "ready_territories", "total_territories", "next_collection_hours"]
        missing = [field for field in required_fields if field not in result]
        if missing:
            log_error(f"Missing required fields: {missing}")
            return False
        
        log_success("All required fields present!")
        return result
    else:
        log_error("Income preview endpoint failed")
        return None

def test_3_territory_capture_flow(player_id):
    """Test 3: Territory Capture + Income Flow"""
    log_test_start("Territory Capture + Income Flow")
    
    # Step 1: Get nearby territories
    log_info("Step 1: Getting nearby territories")
    territories = make_request("GET", "/territories/nearby", params=TEST_COORDS)
    
    if not territories:
        log_error("Failed to get nearby territories")
        return False
    
    log_success(f"Found {len(territories)} territories nearby")
    
    # Find an unclaimed territory
    unclaimed = None
    for territory in territories:
        if not territory.get("owner_id"):
            unclaimed = territory
            break
    
    if not unclaimed:
        log_warning("No unclaimed territories found, using first available")
        unclaimed = territories[0]
    
    log_info(f"Selected territory: {unclaimed['name']} (ID: {unclaimed['id']})")
    
    # Step 2: Capture territory
    log_info("Step 2: Capturing territory")
    capture_result = make_request("POST", f"/territories/{unclaimed['id']}/capture", params={"player_id": player_id})
    
    if not capture_result:
        log_error("Territory capture failed")
        return False
    
    log_success(f"Territory captured! {capture_result.get('message', 'Success')}")
    
    # Step 3: Check income preview after capture
    log_info("Step 3: Checking income preview after capture")
    income_preview = make_request("GET", f"/territories/income-preview/{player_id}")
    
    if income_preview:
        log_success("Income preview after capture:")
        log_info(f"Available Income: ${income_preview.get('available_income', 0)}")
        log_info(f"Total Territories: {income_preview.get('total_territories', 0)}")
        
        if income_preview.get("total_territories", 0) > 0:
            log_success("Territory ownership confirmed!")
        else:
            log_warning("Territory capture may not have been recorded")
    
    # Step 4: Try to collect income
    log_info("Step 4: Attempting to collect income")
    collect_result = make_request("POST", f"/territories/collect-income/{player_id}")
    
    if collect_result:
        log_success(f"Income collection result: {collect_result.get('message', 'Success')}")
        log_info(f"Income collected: ${collect_result.get('income', 0)}")
        log_info(f"Territories paid: {collect_result.get('territories', 0)}")
        
        # Step 5: Check income preview after collection
        log_info("Step 5: Checking income preview after collection")
        final_preview = make_request("GET", f"/territories/income-preview/{player_id}")
        
        if final_preview:
            log_success("Final income preview:")
            log_info(f"Available Income: ${final_preview.get('available_income', 0)}")
            
            if final_preview.get("available_income", 0) == 0:
                log_success("Income collection successful - available income now 0!")
            else:
                log_info(f"Still has ${final_preview.get('available_income', 0)} available (may be expected)")
        
        return True
    else:
        log_error("Income collection failed")
        return False

def test_4_battle_system(player_id):
    """Test 4: Existing battle endpoint still works"""
    log_test_start("Battle System Verification")
    
    # Step 1: Spawn monsters
    log_info("Step 1: Spawning monsters")
    monsters = make_request("GET", "/monsters/spawn", params=TEST_COORDS)
    
    if not monsters:
        log_error("Failed to spawn monsters")
        return False
    
    log_success(f"Spawned {len(monsters)} monsters")
    
    if not monsters:
        log_warning("No monsters available for battle test")
        return True
    
    monster = monsters[0]
    log_info(f"Selected monster: {monster['name']} (Level {monster['level']})")
    
    # Step 2: Start battle
    log_info("Step 2: Starting battle")
    battle_params = {
        "player_id": player_id,
        "enemy_type": "monster",
        "enemy_id": monster["id"]
    }
    battle = make_request("POST", "/battles/start", params=battle_params)
    
    if not battle:
        log_error("Failed to start battle")
        return False
    
    log_success("Battle started successfully!")
    log_info(f"Battle ID: {battle['id']}")
    log_info(f"Enemy: {battle.get('enemy_name', 'Unknown')}")
    log_info(f"Player Health: {battle['player_health']}/{battle['player_max_health']}")
    log_info(f"Enemy Health: {battle['enemy_health']}/{battle['enemy_max_health']}")
    
    # Verify enemy_name is included
    if "enemy_name" in battle:
        log_success(f"Battle response includes enemy_name: '{battle['enemy_name']}'")
        return True
    else:
        log_error("Battle response missing enemy_name field!")
        return False

def run_comprehensive_test():
    """Run all tests in sequence"""
    log(f"\n{'='*60}", Colors.PURPLE + Colors.BOLD)
    log("🎮 GTA GPS RPG BACKEND API TEST SUITE", Colors.PURPLE + Colors.BOLD)
    log(f"{'='*60}\n", Colors.PURPLE + Colors.BOLD)
    
    log_info(f"Testing Backend URL: {BASE_URL}")
    log_info(f"Test Coordinates: {TEST_COORDS}")
    
    results = {
        "user_registration": False,
        "income_preview": False,
        "territory_capture_flow": False,
        "battle_system": False
    }
    
    # Test 1: Register user
    player_id = test_1_register_user()
    if player_id:
        results["user_registration"] = True
        
        # Test 2: Income preview
        income_preview_result = test_2_territory_income_preview(player_id)
        if income_preview_result is not None:
            results["income_preview"] = True
        
        # Test 3: Territory capture flow
        if test_3_territory_capture_flow(player_id):
            results["territory_capture_flow"] = True
        
        # Test 4: Battle system
        if test_4_battle_system(player_id):
            results["battle_system"] = True
    
    # Final results
    log(f"\n{'='*60}", Colors.PURPLE + Colors.BOLD)
    log("📊 TEST RESULTS SUMMARY", Colors.PURPLE + Colors.BOLD)
    log(f"{'='*60}", Colors.PURPLE + Colors.BOLD)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        color = Colors.GREEN if passed else Colors.RED
        log(f"{test_name.upper()}: {status}", color)
    
    log(f"\nOVERALL: {passed_tests}/{total_tests} tests passed", 
        Colors.GREEN if passed_tests == total_tests else Colors.YELLOW)
    
    if passed_tests == total_tests:
        log("🎉 ALL TESTS PASSED! Territory income system working correctly!", Colors.GREEN + Colors.BOLD)
    else:
        failed_tests = [name for name, passed in results.items() if not passed]
        log(f"🚨 FAILED TESTS: {', '.join(failed_tests)}", Colors.RED + Colors.BOLD)
    
    return passed_tests == total_tests

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("\n🛑 Test interrupted by user", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        log(f"\n💥 Test suite crashed: {e}", Colors.RED)
        sys.exit(1)