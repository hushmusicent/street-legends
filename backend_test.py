#!/usr/bin/env python3
"""
Backend API Testing Script for Bank Robbery System
"""

import requests
import json
import time
from datetime import datetime

# Backend URL
BACKEND_URL = "https://street-empire-test.preview.emergentagent.com/api"

def test_bank_robbery_system():
    """Test the complete bank robbery system functionality"""
    print("🏦 TESTING BANK ROBBERY SYSTEM")
    print("=" * 50)
    
    # Test coordinates from review request
    test_lat = 40.7575
    test_lng = -73.98
    test_level = 5
    
    # First, get or create a test player
    print("\n1️⃣ Setting up test player...")
    
    # Try to find existing players first
    try:
        players_response = requests.get(f"{BACKEND_URL}/leaderboard?limit=5")
        if players_response.status_code == 200:
            players = players_response.json()
            if players:
                player_id = players[0]["id"]
                player_name = players[0]["name"]
                print(f"✅ Using existing player: {player_name} (ID: {player_id})")
            else:
                # Create new player
                player_id = create_test_player()
        else:
            # Create new player
            player_id = create_test_player()
    except Exception as e:
        print(f"⚠️ Error finding existing player: {e}")
        # Create new player
        player_id = create_test_player()
    
    # Test 1: Bank Spawning
    print("\n2️⃣ Testing bank spawning...")
    spawn_url = f"{BACKEND_URL}/banks/spawn"
    spawn_params = {
        "latitude": test_lat,
        "longitude": test_lng,
        "player_level": test_level
    }
    
    try:
        spawn_response = requests.get(spawn_url, params=spawn_params)
        print(f"Request: GET {spawn_url}")
        print(f"Params: {spawn_params}")
        print(f"Status: {spawn_response.status_code}")
        
        if spawn_response.status_code == 200:
            banks = spawn_response.json()
            print(f"Response: {json.dumps(banks, indent=2)}")
            
            if banks:
                bank = banks[0]
                bank_id = bank["id"]
                bank_name = bank["name"]
                print(f"✅ Bank spawned successfully: {bank_name} (ID: {bank_id})")
                print(f"📍 Location: ({bank['latitude']}, {bank['longitude']})")
                print(f"💰 Reward range: ${bank['min_reward']} - ${bank['max_reward']}")
            else:
                print("❌ No bank returned from spawn endpoint")
                return False
        else:
            print(f"❌ Bank spawn failed: {spawn_response.status_code} - {spawn_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing bank spawn: {e}")
        return False
    
    # Test 2: Bank Robbery - First Attempt
    print("\n3️⃣ Testing bank robbery (first attempt)...")
    rob_url = f"{BACKEND_URL}/banks/{bank_id}/rob"
    rob_params = {"player_id": player_id}
    
    try:
        rob_response = requests.post(rob_url, params=rob_params)
        print(f"Request: POST {rob_url}")
        print(f"Params: {rob_params}")
        print(f"Status: {rob_response.status_code}")
        
        if rob_response.status_code == 200:
            rob_result = rob_response.json()
            print(f"Response: {json.dumps(rob_result, indent=2)}")
            
            # Check if result follows expected format
            if rob_result.get("success") is True:
                message = rob_result.get("message", "")
                if message.startswith("💰 HEIST SUCCESS"):
                    print("✅ Successful heist detected!")
                    print(f"💰 Loot: ${rob_result.get('loot', 0)}")
                    print(f"💵 New cash: ${rob_result.get('cash', 0)}")
                else:
                    print(f"⚠️ Success but unexpected message format: {message}")
            elif rob_result.get("success") is False:
                message = rob_result.get("message", "")
                if message.startswith("🚔 BUSTED"):
                    print("✅ Busted scenario detected!")
                    print(f"💸 Fine: ${rob_result.get('fine', 0)}")
                    print(f"💵 New cash: ${rob_result.get('cash', 0)}")
                else:
                    print(f"⚠️ Failure but unexpected message format: {message}")
            else:
                print(f"❌ Invalid response format: {rob_result}")
                return False
                
        else:
            print(f"❌ Bank robbery failed: {rob_response.status_code} - {rob_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing bank robbery: {e}")
        return False
    
    # Test 3: Bank Robbery - Cooldown Test
    print("\n4️⃣ Testing cooldown system (immediate retry)...")
    
    try:
        # Immediate retry should trigger cooldown
        cooldown_response = requests.post(rob_url, params=rob_params)
        print(f"Request: POST {rob_url}")
        print(f"Params: {rob_params}")
        print(f"Status: {cooldown_response.status_code}")
        
        if cooldown_response.status_code == 400:
            error_detail = cooldown_response.json().get("detail", "")
            print(f"Response: {cooldown_response.text}")
            
            if "heat is still on" in error_detail.lower():
                print("✅ Cooldown system working correctly!")
                print(f"📝 Cooldown message: {error_detail}")
            else:
                print(f"⚠️ Unexpected cooldown message: {error_detail}")
        else:
            print(f"❌ Expected 400 status for cooldown, got {cooldown_response.status_code}")
            print(f"Response: {cooldown_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing cooldown: {e}")
        return False
    
    # Test 4: Multiple Bank Robbery Attempts (for success/failure distribution)
    print("\n5️⃣ Testing multiple robbery attempts for success/failure distribution...")
    print("(This will test with a different bank to avoid cooldown)")
    
    # Try different coordinates to get a different bank
    alt_lat = 40.7589  # Slightly different coordinates
    alt_lng = -73.9851
    
    try:
        alt_spawn_response = requests.get(f"{BACKEND_URL}/banks/spawn", params={
            "latitude": alt_lat,
            "longitude": alt_lng,
            "player_level": test_level
        })
        
        if alt_spawn_response.status_code == 200:
            alt_banks = alt_spawn_response.json()
            if alt_banks:
                alt_bank_id = alt_banks[0]["id"]
                alt_bank_name = alt_banks[0]["name"]
                print(f"📍 Testing with alternate bank: {alt_bank_name}")
                
                success_count = 0
                failure_count = 0
                max_attempts = 5
                
                for attempt in range(max_attempts):
                    try:
                        attempt_response = requests.post(f"{BACKEND_URL}/banks/{alt_bank_id}/rob", 
                                                       params={"player_id": player_id})
                        
                        if attempt_response.status_code == 200:
                            result = attempt_response.json()
                            if result.get("success"):
                                success_count += 1
                                print(f"  Attempt {attempt + 1}: ✅ SUCCESS - ${result.get('loot', 0)}")
                            else:
                                failure_count += 1
                                print(f"  Attempt {attempt + 1}: 🚔 BUSTED - Fine: ${result.get('fine', 0)}")
                        else:
                            print(f"  Attempt {attempt + 1}: ❌ Error {attempt_response.status_code}")
                        
                        # Wait a bit to avoid cooldown
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"  Attempt {attempt + 1}: ❌ Error: {e}")
                
                print(f"\n📊 Results after {max_attempts} attempts:")
                print(f"  ✅ Successes: {success_count}")
                print(f"  🚔 Failures: {failure_count}")
                print(f"  📈 Success rate: {(success_count/max_attempts)*100:.1f}%")
                
                if success_count > 0 and failure_count > 0:
                    print("✅ Both success and failure scenarios working!")
                else:
                    print("⚠️ Only one outcome type occurred - might be due to randomness")
            else:
                print("⚠️ Could not spawn alternate bank for distribution testing")
        else:
            print("⚠️ Could not spawn alternate bank for distribution testing")
            
    except Exception as e:
        print(f"⚠️ Error in distribution testing: {e}")
    
    print("\n🎉 BANK ROBBERY SYSTEM TESTING COMPLETE!")
    return True

def create_test_player():
    """Create a test player for bank robbery testing"""
    print("Creating new test player...")
    
    # Create player
    player_data = {
        "name": "BankRobber",
        "character_class": "enforcer",
        "email": f"banktest_{int(time.time())}@test.com",
        "password": "testpass123"
    }
    
    try:
        create_response = requests.post(f"{BACKEND_URL}/players", json=player_data)
        if create_response.status_code == 201:
            player = create_response.json()
            player_id = player["id"]
            print(f"✅ Created test player: {player['name']} (ID: {player_id})")
            return player_id
        else:
            print(f"❌ Failed to create player: {create_response.status_code} - {create_response.text}")
            # Try to get an existing player from leaderboard
            try:
                lb_response = requests.get(f"{BACKEND_URL}/leaderboard?limit=1")
                if lb_response.status_code == 200:
                    players = lb_response.json()
                    if players:
                        player_id = players[0]["id"]
                        print(f"✅ Using existing player from leaderboard: {players[0]['name']} (ID: {player_id})")
                        return player_id
            except:
                pass
            raise Exception("Could not create or find a test player")
    except Exception as e:
        print(f"❌ Error creating player: {e}")
        raise

def main():
    """Main test execution"""
    print(f"🔗 Backend URL: {BACKEND_URL}")
    print(f"⏰ Test started at: {datetime.now()}")
    print()
    
    try:
        success = test_bank_robbery_system()
        if success:
            print("\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        else:
            print("\n❌ SOME TESTS FAILED!")
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()