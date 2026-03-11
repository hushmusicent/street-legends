#!/usr/bin/env python3
"""
Backend Test for GTA GPS RPG Item Delete and Sell Endpoints
Testing: DELETE /api/players/{player_id}/inventory/{item_id} and POST /api/players/{player_id}/inventory/{item_id}/sell
"""

import requests
import json
import sys
from typing import Dict, Any

# Get backend URL from environment
BACKEND_URL = "https://real-world-raid-game.preview.emergentagent.com/api"

def make_request(method: str, endpoint: str, data: Dict[str, Any] = None, params: Dict[str, str] = None) -> requests.Response:
    """Make HTTP request with proper error handling"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method.upper() == "POST":
            if params:
                # For endpoints that expect query parameters instead of JSON body
                response = requests.post(url, params=params, timeout=30)
            else:
                response = requests.post(url, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        return response
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error for {method} {url}: {e}")
        return None

def test_item_delete_and_sell_endpoints():
    """Test item delete and sell functionality for GTA GPS RPG backend"""
    print("🔧 TESTING ITEM DELETE AND SELL ENDPOINTS")
    print("=" * 60)
    
    test_results = {
        "create_player": False,
        "buy_item_for_testing": False,
        "get_inventory": False,
        "delete_item": False,
        "sell_item": False,
        "error_cases": False
    }
    
    # Test 1: Create a test player
    print("\n1️⃣ Creating test player...")
    import time
    unique_suffix = str(int(time.time()))[-6:]  # Use timestamp suffix for uniqueness
    player_data = {
        "name": f"ItemTestPlayer{unique_suffix}",
        "character_class": "street_soldier"
    }
    
    response = make_request("POST", "/players", data=player_data)
    if not response or response.status_code != 200:
        print(f"❌ Failed to create player: {response.status_code if response else 'Network error'}")
        if response:
            print(f"Response: {response.text}")
        return test_results
    
    player = response.json()
    player_id = player["id"]
    print(f"✅ Created test player: {player['name']} (ID: {player_id})")
    print(f"   Starting cash: ${player['cash']}")
    print(f"   Starting inventory: {player['inventory']}")
    test_results["create_player"] = True
    
    # Test 2: Use existing inventory items and buy additional items for testing
    print(f"\n2️⃣ Preparing items for testing...")
    
    # Get all available items for reference
    response = make_request("GET", "/items")
    if not response or response.status_code != 200:
        print(f"❌ Failed to get items list: {response.status_code if response else 'Network error'}")
        return test_results
    
    all_items = response.json()
    
    # Use existing inventory items
    existing_items = []
    for item_id in player['inventory']:
        if item_id in all_items:
            existing_items.append((item_id, all_items[item_id]))
    
    print(f"✅ Using existing inventory items:")
    for item_id, item in existing_items:
        print(f"   - {item['name']} (ID: {item_id}, Value: ${item.get('value', 'N/A')})")
    
    # Try to buy one additional item for more comprehensive testing
    bought_items = []
    affordable_items = [
        (item_id, item) for item_id, item in all_items.items()
        if item.get("value", 0) <= 50 and item.get("level_requirement", 1) <= 1
        and item_id not in player['inventory']  # Don't buy duplicates
    ]
    
    if affordable_items:
        item_id, item = affordable_items[0]  # Buy the first affordable item
        response = make_request("POST", f"/players/{player_id}/buy-item", params={"item_id": item_id})
        if response and response.status_code == 200:
            bought_items.append((item_id, item))
            print(f"✅ Bought additional item: {item['name']} (ID: {item_id}) for ${item['value']}")
        else:
            print(f"⚠️  Could not buy additional item: {response.status_code if response else 'Network error'}")
    
    # Combine existing and newly bought items for testing
    test_items = existing_items + bought_items
    
    if len(test_items) == 0:
        print("❌ No items available for testing")
        return test_results
    
    print(f"✅ Total items available for testing: {len(test_items)}")
    test_results["buy_item_for_testing"] = True
    
    # Test 3: Get player inventory details
    print(f"\n3️⃣ Getting player inventory details...")
    response = make_request("GET", f"/players/{player_id}/inventory-details")
    if not response or response.status_code != 200:
        print(f"❌ Failed to get inventory details: {response.status_code if response else 'Network error'}")
        return test_results
    
    inventory_details = response.json()
    print(f"✅ Retrieved inventory with {len(inventory_details)} items:")
    for item in inventory_details:
        print(f"   - {item['name']} (ID: {item['id']}, Value: ${item.get('value', 'N/A')})")
    
    test_results["get_inventory"] = True
    
    # Get updated player cash before testing
    response = make_request("GET", f"/players/{player_id}")
    if response and response.status_code == 200:
        player_data = response.json()
        current_cash = player_data["cash"]
        current_inventory = player_data["inventory"]
        print(f"   Current cash: ${current_cash}")
        print(f"   Current inventory count: {len(current_inventory)}")
    
    # Test 4: Delete/Drop an item
    print(f"\n4️⃣ Testing item deletion (drop)...")
    if test_items:
        item_to_delete = test_items[0][0]  # Use first test item
        item_name = test_items[0][1]["name"]
        
        print(f"   Deleting item: {item_name} (ID: {item_to_delete})")
        response = make_request("DELETE", f"/players/{player_id}/inventory/{item_to_delete}")
        
        if not response:
            print("❌ Network error during item deletion")
            return test_results
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Item deleted successfully: {result['message']}")
            
            # Verify item was removed from inventory
            response = make_request("GET", f"/players/{player_id}/inventory-details")
            if response and response.status_code == 200:
                updated_inventory = response.json()
                item_still_exists = any(item["id"] == item_to_delete for item in updated_inventory)
                if not item_still_exists:
                    print(f"✅ Verified: Item {item_name} removed from inventory")
                    test_results["delete_item"] = True
                else:
                    print(f"❌ Error: Item {item_name} still in inventory after deletion")
            
        else:
            print(f"❌ Failed to delete item: {response.status_code}")
            print(f"Response: {response.text}")
    
    # Test 5: Sell an item
    print(f"\n5️⃣ Testing item selling...")
    if len(test_items) > 1:
        item_to_sell = test_items[1][0]  # Use second test item
        item_data = test_items[1][1]
        item_name = item_data["name"]
        item_value = item_data.get("value", 0)
        expected_sell_price = max(1, item_value // 2)  # 50% of item value
        
        print(f"   Selling item: {item_name} (ID: {item_to_sell})")
        print(f"   Item value: ${item_value}, Expected sell price: ${expected_sell_price}")
        
        response = make_request("POST", f"/players/{player_id}/inventory/{item_to_sell}/sell")
        
        if not response:
            print("❌ Network error during item selling")
            return test_results
        
        if response.status_code == 200:
            result = response.json()
            actual_sell_price = result.get("sell_price", 0)
            print(f"✅ Item sold successfully: {result['message']}")
            print(f"   Actual sell price: ${actual_sell_price}")
            
            # Verify the sell price calculation
            if actual_sell_price == expected_sell_price:
                print(f"✅ Sell price calculation correct (50% of item value)")
            else:
                print(f"⚠️  Sell price mismatch: expected ${expected_sell_price}, got ${actual_sell_price}")
            
            # Verify item was removed and cash increased
            response = make_request("GET", f"/players/{player_id}")
            if response and response.status_code == 200:
                updated_player = response.json()
                new_cash = updated_player["cash"]
                new_inventory = updated_player["inventory"]
                
                print(f"   Cash after sale: ${new_cash} (increased by ${new_cash - current_cash})")
                
                # Check if item was removed from inventory
                if item_to_sell not in new_inventory:
                    print(f"✅ Verified: Item {item_name} removed from inventory")
                    test_results["sell_item"] = True
                else:
                    print(f"❌ Error: Item {item_name} still in inventory after sale")
            
        else:
            print(f"❌ Failed to sell item: {response.status_code}")
            print(f"Response: {response.text}")
    
    # Test 6: Error cases
    print(f"\n6️⃣ Testing error cases...")
    
    # Test 6a: Try to delete an item that doesn't exist in inventory
    print("   6a. Testing delete non-existent item...")
    fake_item_id = "non_existent_item_12345"
    response = make_request("DELETE", f"/players/{player_id}/inventory/{fake_item_id}")
    
    if response and response.status_code == 400:
        result = response.json()
        print(f"✅ Correctly rejected deletion of non-existent item: {result.get('detail', 'Error message')}")
    elif response:
        print(f"⚠️  Unexpected response for non-existent item deletion: {response.status_code}")
    else:
        print("❌ Network error during error case testing")
    
    # Test 6b: Try to sell an item that doesn't exist in inventory
    print("   6b. Testing sell non-existent item...")
    response = make_request("POST", f"/players/{player_id}/inventory/{fake_item_id}/sell")
    
    if response and response.status_code == 400:
        result = response.json()
        print(f"✅ Correctly rejected sale of non-existent item: {result.get('detail', 'Error message')}")
    elif response:
        print(f"⚠️  Unexpected response for non-existent item sale: {response.status_code}")
    else:
        print("❌ Network error during error case testing")
    
    # Test 6c: Try operations with non-existent player
    print("   6c. Testing operations with non-existent player...")
    fake_player_id = "fake_player_12345"
    if test_items:
        test_item_id = test_items[0][0]  # Use any valid item ID
        
        # Test delete with fake player
        response = make_request("DELETE", f"/players/{fake_player_id}/inventory/{test_item_id}")
        if response and response.status_code == 404:
            print(f"✅ Correctly rejected delete for non-existent player")
        elif response:
            print(f"⚠️  Unexpected response for non-existent player delete: {response.status_code}")
        
        # Test sell with fake player  
        response = make_request("POST", f"/players/{fake_player_id}/inventory/{test_item_id}/sell")
        if response and response.status_code == 404:
            print(f"✅ Correctly rejected sell for non-existent player")
            test_results["error_cases"] = True
        elif response:
            print(f"⚠️  Unexpected response for non-existent player sell: {response.status_code}")
    
    return test_results

def main():
    """Main test function"""
    print("🎮 GTA GPS RPG - Item Delete and Sell Endpoints Test")
    print(f"🔗 Testing backend at: {BACKEND_URL}")
    print("=" * 80)
    
    try:
        results = test_item_delete_and_sell_endpoints()
        
        # Summary
        print(f"\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")
        
        print(f"\n📈 Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Item delete and sell endpoints working correctly.")
            return 0
        else:
            print(f"⚠️  {total_tests - passed_tests} test(s) failed. Review results above.")
            return 1
            
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())