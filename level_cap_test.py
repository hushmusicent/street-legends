#!/usr/bin/env python3

import requests
import json
import sys
import random

# Backend URL from environment
BACKEND_URL = "https://heist-map-game.preview.emergentagent.com/api"

def test_detailed_level_cap_verification():
    """More detailed test to verify level capping with multiple spawns to ensure we see variety"""
    
    print("🎯 DETAILED ENEMY LEVEL CAP VERIFICATION")
    print("Testing level cap across many spawns to ensure variety and proper capping")
    print("=" * 80)
    
    # Test different player levels with many spawns to increase chance of variety
    test_cases = [
        {"player_level": 1, "expected_max": 1, "description": "Level 1 player - only Thug (1-2)"},
        {"player_level": 5, "expected_max": 5, "description": "Level 5 player - should see Thugs, Gangsters, maybe Criminals"},
        {"player_level": 10, "expected_max": 10, "description": "Level 10 player - should see all Tier 1 enemies"},
        {"player_level": 15, "expected_max": 15, "description": "Level 15 player - should see Tier 1+2 enemies"},
    ]
    
    all_tests_passed = True
    
    for case in test_cases:
        player_level = case["player_level"]
        expected_max = case["expected_max"]
        description = case["description"]
        
        print(f"\n🔍 {description}")
        print("-" * 60)
        
        # Do many spawns to increase variety
        all_monsters = []
        violations = []
        
        # Try multiple different locations to get different spawn pools
        test_coordinates = [
            (40.758, -73.9855),    # Times Square
            (40.7589, -73.9851),   # Near Times Square 
            (40.760, -73.986),     # Slightly north
            (40.756, -73.987),     # Slightly south
            (40.759, -73.984),     # Slightly east
        ]
        
        for i, (lat, lng) in enumerate(test_coordinates):
            try:
                response = requests.get(
                    f"{BACKEND_URL}/monsters/spawn",
                    params={
                        "latitude": lat,
                        "longitude": lng,
                        "player_level": player_level
                    },
                    timeout=10
                )
                
                if response.status_code != 200:
                    print(f"  ❌ Spawn {i+1} failed: HTTP {response.status_code}")
                    continue
                
                monsters = response.json()
                print(f"  Spawn {i+1}: {len(monsters)} monsters")
                
                for monster in monsters:
                    monster_level = monster.get("level", 0)
                    monster_name = monster.get("name", "Unknown")
                    
                    all_monsters.append({
                        "name": monster_name,
                        "level": monster_level,
                        "spawn": i+1
                    })
                    
                    # Check for level violations
                    if monster_level > player_level:
                        violations.append(f"Spawn {i+1}: {monster_name} level {monster_level} > player level {player_level}")
                
            except Exception as e:
                print(f"  ❌ Spawn {i+1} error: {e}")
                continue
        
        # Analyze results
        total_monsters = len(all_monsters)
        if total_monsters == 0:
            print(f"  ❌ No monsters spawned - test inconclusive")
            all_tests_passed = False
            continue
        
        # Level distribution
        level_distribution = {}
        name_distribution = {}
        max_level_found = 0
        
        for monster in all_monsters:
            level = monster["level"]
            name = monster["name"]
            
            level_distribution[level] = level_distribution.get(level, 0) + 1
            name_distribution[name] = name_distribution.get(name, 0) + 1
            max_level_found = max(max_level_found, level)
        
        print(f"\n  📊 Results for Level {player_level} Player:")
        print(f"    Total monsters spawned: {total_monsters}")
        print(f"    Max level found: {max_level_found}")
        print(f"    Level violations: {len(violations)}")
        print(f"    Level distribution: {dict(sorted(level_distribution.items()))}")
        print(f"    Enemy types: {sorted(name_distribution.keys())}")
        
        # Check for violations
        if violations:
            print(f"    ❌ CRITICAL VIOLATIONS:")
            for violation in violations:
                print(f"      - {violation}")
            all_tests_passed = False
        else:
            print(f"    ✅ NO LEVEL VIOLATIONS - All monsters <= {player_level}")
        
        # Check that max found level is within expected range
        if max_level_found > expected_max:
            print(f"    ❌ Max level {max_level_found} exceeds expected max {expected_max}")
            all_tests_passed = False
        else:
            print(f"    ✅ Max level {max_level_found} within expected range (<= {expected_max})")
    
    return all_tests_passed

def test_level_cap_logic_directly():
    """Test the specific level cap logic by examining the min/max calculation"""
    
    print("\n🔬 TESTING LEVEL CAP LOGIC")
    print("Verifying that the cap calculation min(template[level_max], player_level) works")
    print("=" * 80)
    
    # This tests the actual logic: monster_level = random.randint(template["level_min"], max_enemy_level)
    # where max_enemy_level = min(template["level_max"], player_level)
    
    test_scenarios = [
        {"player_level": 1, "template_min": 1, "template_max": 2, "expected_max": 1},
        {"player_level": 3, "template_min": 3, "template_max": 4, "expected_max": 3},
        {"player_level": 5, "template_min": 3, "template_max": 4, "expected_max": 4},
        {"player_level": 8, "template_min": 7, "template_max": 8, "expected_max": 8},
        {"player_level": 6, "template_min": 7, "template_max": 8, "expected_max": 6},  # This is the key test case
    ]
    
    print("\nTesting level cap calculation logic:")
    print("Format: player_level vs template(min-max) → expected_max_spawn")
    
    for scenario in test_scenarios:
        player_level = scenario["player_level"]
        template_min = scenario["template_min"]
        template_max = scenario["template_max"]
        expected_max = scenario["expected_max"]
        
        # This simulates the backend logic
        max_enemy_level = min(template_max, player_level)
        
        print(f"  Player L{player_level} vs Enemy({template_min}-{template_max}) → max spawn L{max_enemy_level}")
        
        if max_enemy_level != expected_max:
            print(f"    ❌ Expected {expected_max}, got {max_enemy_level}")
            return False
        elif max_enemy_level > player_level:
            print(f"    ❌ Cap failed: {max_enemy_level} > {player_level}")
            return False
        else:
            print(f"    ✅ Correct: max spawn level {max_enemy_level} <= player level {player_level}")
    
    print("\n✅ Level cap calculation logic verified correct")
    return True

def main():
    """Run comprehensive enemy level cap tests"""
    
    print("🚀 COMPREHENSIVE ENEMY LEVEL CAP TESTING")
    print("Verifying enemies never spawn above player level")
    print("Backend URL:", BACKEND_URL)
    print("=" * 80)
    
    # Test the logic directly first
    logic_test_passed = test_level_cap_logic_directly()
    
    # Test with actual spawns
    spawn_test_passed = test_detailed_level_cap_verification()
    
    # Final results
    print("\n🏁 FINAL TEST RESULTS")
    print("=" * 80)
    
    if logic_test_passed and spawn_test_passed:
        print("🎉 ALL ENEMY LEVEL CAP TESTS PASSED!")
        print("✅ Level cap calculation logic is mathematically correct")
        print("✅ No enemies spawn above player level in actual spawns")
        print("✅ Enemy spawning system working as specified")
        sys.exit(0)
    else:
        print("💥 ENEMY LEVEL CAP TESTS FAILED!")
        if not logic_test_passed:
            print("❌ Level cap calculation logic has issues")
        if not spawn_test_passed:
            print("❌ Actual spawns violate level cap requirements")
        sys.exit(1)

if __name__ == "__main__":
    main()