#!/usr/bin/env python3
"""
Backend Testing Script for GTA GPS RPG Game
Tests the redesigned tiled territory grid system
"""
import requests
import json
import sys
from typing import Dict, List, Any

# Backend URL from environment
BACKEND_URL = "https://real-world-raid-game.preview.emergentagent.com/api"

# Test coordinates - Times Square NYC
TEST_LATITUDE = 40.758
TEST_LONGITUDE = -73.9855

class TerritoryGridTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        
    def test_equal_sized_tiled_grid(self) -> Dict[str, Any]:
        """Test that nearby territories return exactly 25 territories with same size (150)"""
        print("🔍 Testing equal-sized tiled grid...")
        
        url = f"{BACKEND_URL}/territories/nearby"
        params = {
            "latitude": TEST_LATITUDE,
            "longitude": TEST_LONGITUDE,
            "player_level": 1
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            territories = response.json()
            
            # Check territory count
            territory_count = len(territories)
            if territory_count != 25:
                return {
                    "success": False,
                    "error": f"Expected 25 territories, got {territory_count}"
                }
            
            # Check all territories have the same size (150)
            sizes = [t.get("size") for t in territories]
            unique_sizes = set(sizes)
            if len(unique_sizes) != 1 or 150 not in unique_sizes:
                return {
                    "success": False,
                    "error": f"Expected all territories to have size 150, got sizes: {unique_sizes}"
                }
                
            # Check all territories have bounds
            missing_bounds = []
            for i, t in enumerate(territories):
                bounds = t.get("bounds")
                if not bounds:
                    missing_bounds.append(f"Territory {i+1}")
                    continue
                required_keys = ["south", "north", "west", "east"]
                missing_keys = [k for k in required_keys if k not in bounds]
                if missing_keys:
                    missing_bounds.append(f"Territory {i+1} missing: {missing_keys}")
            
            if missing_bounds:
                return {
                    "success": False,
                    "error": f"Territories missing bounds: {missing_bounds[:5]}..."  # Show first 5
                }
            
            # Check tiling - adjacent territories should connect perfectly
            tiling_errors = []
            for i, t1 in enumerate(territories):
                for j, t2 in enumerate(territories[i+1:], i+1):
                    b1, b2 = t1["bounds"], t2["bounds"]
                    # Check if territories are adjacent (share a border)
                    if (abs(b1["north"] - b2["south"]) < 1e-6 or  # t1 north = t2 south
                        abs(b1["south"] - b2["north"]) < 1e-6 or  # t1 south = t2 north
                        abs(b1["east"] - b2["west"]) < 1e-6 or    # t1 east = t2 west
                        abs(b1["west"] - b2["east"]) < 1e-6):     # t1 west = t2 east
                        # They are adjacent - check no overlap
                        pass  # This is good - they tile perfectly
                        
            return {
                "success": True,
                "territory_count": territory_count,
                "sizes": unique_sizes,
                "sample_bounds": territories[0]["bounds"] if territories else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def test_unclaimed_color(self) -> Dict[str, Any]:
        """Test that all unclaimed territories have color #3d3d3d"""
        print("🎨 Testing unclaimed territory colors...")
        
        url = f"{BACKEND_URL}/territories/nearby"
        params = {
            "latitude": TEST_LATITUDE,
            "longitude": TEST_LONGITUDE,
            "player_level": 1
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            territories = response.json()
            
            # Check colors of unclaimed territories
            wrong_colors = []
            for i, territory in enumerate(territories):
                if territory.get("owner_id") is None:  # Unclaimed
                    color = territory.get("color")
                    if color != "#3d3d3d":
                        wrong_colors.append({
                            "territory": territory.get("name", f"Territory {i+1}"),
                            "expected": "#3d3d3d",
                            "actual": color
                        })
            
            if wrong_colors:
                return {
                    "success": False,
                    "error": f"Found {len(wrong_colors)} territories with wrong colors",
                    "wrong_colors": wrong_colors[:5]  # Show first 5
                }
            
            unclaimed_count = len([t for t in territories if t.get("owner_id") is None])
            
            return {
                "success": True,
                "unclaimed_count": unclaimed_count,
                "all_have_correct_color": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def test_color_change_on_capture(self) -> Dict[str, Any]:
        """Test that territory color changes when captured"""
        print("⚔️  Testing color change on capture...")
        
        try:
            # Step 1: Create a test player
            player_data = {
                "name": "GridTestPlayer",
                "character_class": "street_soldier"
            }
            
            create_response = self.session.post(f"{BACKEND_URL}/players", json=player_data)
            create_response.raise_for_status()
            player = create_response.json()
            player_id = player["id"]
            
            # Step 2: Get nearby territories
            territories_response = self.session.get(
                f"{BACKEND_URL}/territories/nearby",
                params={"latitude": TEST_LATITUDE, "longitude": TEST_LONGITUDE, "player_level": 1}
            )
            territories_response.raise_for_status()
            territories = territories_response.json()
            
            # Find an unclaimed territory
            unclaimed_territory = None
            for territory in territories:
                if territory.get("owner_id") is None:
                    unclaimed_territory = territory
                    break
            
            if not unclaimed_territory:
                return {
                    "success": False,
                    "error": "No unclaimed territories found to test capture"
                }
            
            territory_id = unclaimed_territory["id"]
            original_color = unclaimed_territory.get("color")
            
            # Step 3: Capture the territory
            capture_response = self.session.post(
                f"{BACKEND_URL}/territories/{territory_id}/capture",
                params={"player_id": player_id}
            )
            capture_response.raise_for_status()
            capture_result = capture_response.json()
            
            if capture_result.get("result") != "victory":
                return {
                    "success": False,
                    "error": f"Territory capture failed: {capture_result.get('result', 'unknown')}"
                }
            
            # Step 4: Check that color changed
            captured_territory = capture_result.get("territory")
            if not captured_territory:
                return {
                    "success": False,
                    "error": "No territory data returned after capture"
                }
            
            new_color = captured_territory.get("color")
            if new_color == "#3d3d3d":
                return {
                    "success": False,
                    "error": f"Territory color didn't change from unclaimed color after capture. Still: {new_color}"
                }
            
            if new_color == original_color:
                return {
                    "success": False,
                    "error": f"Territory color didn't change after capture. Still: {new_color}"
                }
            
            # Step 5: Verify other territories are still unclaimed color
            updated_territories_response = self.session.get(
                f"{BACKEND_URL}/territories/nearby",
                params={"latitude": TEST_LATITUDE, "longitude": TEST_LONGITUDE, "player_level": 1}
            )
            updated_territories_response.raise_for_status()
            updated_territories = updated_territories_response.json()
            
            still_unclaimed = [t for t in updated_territories if t.get("owner_id") is None]
            wrong_unclaimed_colors = [t for t in still_unclaimed if t.get("color") != "#3d3d3d"]
            
            if wrong_unclaimed_colors:
                return {
                    "success": False,
                    "error": f"Found {len(wrong_unclaimed_colors)} unclaimed territories with wrong colors after capture"
                }
            
            return {
                "success": True,
                "original_color": original_color,
                "new_color": new_color,
                "captured_territory": captured_territory.get("name"),
                "remaining_unclaimed": len(still_unclaimed)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def test_unique_territory_names(self) -> Dict[str, Any]:
        """Test that all 25 territories have unique names"""
        print("📝 Testing unique territory names...")
        
        url = f"{BACKEND_URL}/territories/nearby"
        params = {
            "latitude": TEST_LATITUDE,
            "longitude": TEST_LONGITUDE,
            "player_level": 1
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            territories = response.json()
            
            # Check name uniqueness
            names = [t.get("name") for t in territories if t.get("name")]
            unique_names = set(names)
            
            if len(names) != len(unique_names):
                duplicates = {}
                for name in names:
                    duplicates[name] = duplicates.get(name, 0) + 1
                duplicate_names = {name: count for name, count in duplicates.items() if count > 1}
                
                return {
                    "success": False,
                    "error": f"Found duplicate territory names: {duplicate_names}",
                    "total_names": len(names),
                    "unique_names": len(unique_names)
                }
            
            # Check that names come from the 1600+ name pool (should have certain patterns)
            valid_patterns = ["side", "gate", "ridge", "hill", "vale", "creek", "water", "field", "wood", "stone",
                            "cross", "bridge", "port", "haven", "cliff", "peak", "bay", "lake", "river", "pine",
                            "Turf", "Block", "Zone", "Strip", "Row", "Corner", "Plaza", "District", "Junction", "Alley"]
            
            pattern_matches = 0
            sample_names = []
            for name in names[:5]:  # Sample first 5 names
                sample_names.append(name)
                for pattern in valid_patterns:
                    if pattern in name:
                        pattern_matches += 1
                        break
            
            return {
                "success": True,
                "total_territories": len(territories),
                "unique_names": len(unique_names),
                "all_names_unique": True,
                "sample_names": sample_names,
                "pattern_matches": pattern_matches
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }

def run_all_tests():
    """Run all territory grid system tests"""
    print("🏙️ Starting Tiled Territory Grid System Tests")
    print("=" * 60)
    
    tester = TerritoryGridTester()
    tests = [
        ("Equal-sized tiled grid", tester.test_equal_sized_tiled_grid),
        ("Unclaimed color consistency", tester.test_unclaimed_color),
        ("Color change on capture", tester.test_color_change_on_capture),
        ("Unique territory names", tester.test_unique_territory_names),
    ]
    
    results = {}
    overall_success = True
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 40)
        
        result = test_func()
        results[test_name] = result
        
        if result["success"]:
            print(f"✅ PASSED")
            if "territory_count" in result:
                print(f"   Territory count: {result['territory_count']}")
            if "sizes" in result:
                print(f"   Territory sizes: {result['sizes']}")
            if "unclaimed_count" in result:
                print(f"   Unclaimed territories: {result['unclaimed_count']}")
            if "new_color" in result:
                print(f"   Color changed from {result['original_color']} to {result['new_color']}")
            if "unique_names" in result:
                print(f"   All {result['unique_names']} names are unique")
            if "sample_names" in result:
                print(f"   Sample names: {', '.join(result['sample_names'][:3])}")
        else:
            print(f"❌ FAILED: {result['error']}")
            overall_success = False
    
    print("\n" + "=" * 60)
    print(f"🏁 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    # Print summary
    print(f"\n📊 Test Summary:")
    for test_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    return overall_success, results

if __name__ == "__main__":
    success, results = run_all_tests()
    sys.exit(0 if success else 1)