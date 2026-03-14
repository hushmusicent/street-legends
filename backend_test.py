#!/usr/bin/env python3

import requests
import json
import sys
import time
import random

# Backend URL from environment
BACKEND_URL = "https://heist-map-game.preview.emergentagent.com/api"

def test_enemy_level_cap():
    """Test that enemies never spawn at a level higher than the player's level"""
    
    print("🎯 TESTING ENEMY LEVEL CAP - No enemies should spawn above player level")
    print("=" * 80)
    
    # Test coordinates (Times Square NYC)
    test_lat = 40.758
    test_lng = -73.9855
    
    # Test different player levels as requested
    test_levels = [1, 5, 10, 15]
    
    all_tests_passed = True
    total_violations = 0
    total_monsters = 0
    
    for player_level in test_levels:
        print(f"\n🔍 Testing Player Level {player_level}")
        print("-" * 40)
        
        # Test with multiple spawn calls to ensure consistency 
        level_violations = []
        level_monsters = []
        
        for test_run in range(3):  # Run 3 times per level to get more data
            print(f"  Test Run {test_run + 1}/3:", end=" ")
            
            try:
                # Call spawn endpoint
                response = requests.get(
                    f"{BACKEND_URL}/monsters/spawn",
                    params={
                        "latitude": test_lat + (test_run * 0.001),  # Slightly offset each test
                        "longitude": test_lng + (test_run * 0.001),
                        "player_level": player_level
                    },
                    timeout=10
                )
                
                if response.status_code != 200:
                    print(f"❌ HTTP {response.status_code}")
                    print(f"    Response: {response.text[:200]}")
                    all_tests_passed = False
                    continue
                
                monsters = response.json()
                if not isinstance(monsters, list):
                    print(f"❌ Invalid response format (expected list, got {type(monsters)})")
                    all_tests_passed = False
                    continue
                
                print(f"✅ Spawned {len(monsters)} monsters")
                
                # Check each monster's level
                test_violations = []
                for i, monster in enumerate(monsters):
                    monster_level = monster.get("level", 0)
                    monster_name = monster.get("name", "Unknown")
                    
                    level_monsters.append({
                        "name": monster_name,
                        "level": monster_level,
                        "run": test_run + 1
                    })
                    
                    if monster_level > player_level:
                        violation = f"Monster '{monster_name}' level {monster_level} > player level {player_level}"
                        test_violations.append(violation)
                        print(f"    ❌ VIOLATION: {violation}")
                
                if test_violations:
                    level_violations.extend(test_violations)
                else:
                    max_monster_level = max([m.get("level", 0) for m in monsters]) if monsters else 0
                    print(f"    ✅ All monsters <= level {player_level} (max found: {max_monster_level})")
                    
            except requests.RequestException as e:
                print(f"❌ Request failed: {e}")
                all_tests_passed = False
                continue
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                all_tests_passed = False
                continue
        
        # Summary for this player level
        total_monsters += len(level_monsters)
        total_violations += len(level_violations)
        
        print(f"\n  📊 Level {player_level} Summary:")
        print(f"    Total monsters spawned: {len(level_monsters)}")
        print(f"    Level violations: {len(level_violations)}")
        
        if level_violations:
            print(f"    ❌ CRITICAL FAILURES:")
            for violation in level_violations:
                print(f"      - {violation}")
            all_tests_passed = False
        else:
            print(f"    ✅ ALL MONSTERS PROPERLY CAPPED")
        
        # Show monster distribution for this level
        if level_monsters:
            level_distribution = {}
            for monster in level_monsters:
                level = monster["level"]
                level_distribution[level] = level_distribution.get(level, 0) + 1
            
            print(f"    📈 Level Distribution: {dict(sorted(level_distribution.items()))}")
            
            # Show monster name variety
            names = set(monster["name"] for monster in level_monsters)
            print(f"    🎭 Enemy Types: {sorted(names)}")
    
    print("\n" + "=" * 80)
    print("🎯 FINAL ENEMY LEVEL CAP TEST RESULTS")
    print("=" * 80)
    print(f"Total monsters tested: {total_monsters}")
    print(f"Total level violations: {total_violations}")
    
    if all_tests_passed and total_violations == 0:
        print("✅ ALL TESTS PASSED - Enemy level cap working correctly!")
        print("✅ NO enemies spawned above player level across all test scenarios")
        return True
    else:
        print("❌ TEST FAILURES DETECTED")
        print(f"❌ Found {total_violations} enemies spawning above player level")
        print("❌ Enemy level cap logic has CRITICAL ISSUES")
        return False

def test_edge_cases():
    """Test edge cases for enemy level capping"""
    
    print("\n🔬 TESTING EDGE CASES")
    print("=" * 80)
    
    edge_cases = [
        {"level": 1, "description": "Minimum level player"},
        {"level": 11, "description": "Boss unlock threshold"}, 
        {"level": 21, "description": "Tier 2 boss threshold"},
        {"level": 50, "description": "Mid-tier player"},
        {"level": 100, "description": "Maximum level player"}
    ]
    
    test_lat = 40.7589  # Slightly different coordinates for edge cases
    test_lng = -73.9851
    
    all_edge_tests_passed = True
    
    for case in edge_cases:
        player_level = case["level"]
        description = case["description"]
        
        print(f"\n🧪 Edge Case: {description} (Level {player_level})")
        
        try:
            response = requests.get(
                f"{BACKEND_URL}/monsters/spawn",
                params={
                    "latitude": test_lat,
                    "longitude": test_lng,
                    "player_level": player_level
                },
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                all_edge_tests_passed = False
                continue
            
            monsters = response.json()
            if not monsters:
                print("⚠️  No monsters spawned (this can happen in edge cases)")
                continue
            
            violations = []
            max_level = 0
            
            for monster in monsters:
                monster_level = monster.get("level", 0)
                monster_name = monster.get("name", "Unknown")
                max_level = max(max_level, monster_level)
                
                if monster_level > player_level:
                    violations.append(f"{monster_name} (Level {monster_level})")
            
            if violations:
                print(f"❌ VIOLATIONS found: {', '.join(violations)}")
                all_edge_tests_passed = False
            else:
                print(f"✅ All monsters properly capped (max level found: {max_level})")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            all_edge_tests_passed = False
    
    return all_edge_tests_passed

def main():
    """Run all enemy level cap tests"""
    
    print("🚀 ENEMY LEVEL CAP TESTING SUITE")
    print("Testing that enemies never spawn at levels higher than player level")
    print("Backend URL:", BACKEND_URL)
    print("=" * 80)
    
    # Run main test suite
    main_tests_passed = test_enemy_level_cap()
    
    # Run edge case tests
    edge_tests_passed = test_edge_cases()
    
    # Final result
    print("\n" + "🏁 OVERALL TEST RESULTS" + " " * 50)
    print("=" * 80)
    
    if main_tests_passed and edge_tests_passed:
        print("🎉 ALL ENEMY LEVEL CAP TESTS PASSED!")
        print("✅ Enemy spawning logic correctly caps levels at player level")
        print("✅ System is working as specified in review request")
        sys.exit(0)
    else:
        print("💥 ENEMY LEVEL CAP TESTS FAILED!")
        print("❌ Critical issues found with enemy level capping logic")
        print("❌ Some enemies are spawning above player level")
        sys.exit(1)

if __name__ == "__main__":
    main()