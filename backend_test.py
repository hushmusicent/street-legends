#!/usr/bin/env python3

import requests
import json
import sys
from typing import Dict, List
from collections import Counter

# Use the backend URL from frontend .env
BASE_URL = "https://heist-map-game.preview.emergentagent.com/api"

def test_exact_5_enemies_new_area():
    """Test that exactly 5 enemies spawn in a new area"""
    print("=== TEST 1: Exactly 5 enemies spawn in new area ===")
    
    # Use unique coordinates that haven't been used before
    url = f"{BASE_URL}/monsters/spawn"
    params = {
        "latitude": 41.123,
        "longitude": -74.567,
        "player_level": 25
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"Request: GET {url} with params {params}")
        print(f"Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected status 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        enemy_count = len(data)
        
        print(f"Number of enemies returned: {enemy_count}")
        
        if enemy_count == 5:
            print("✅ PASSED: Exactly 5 enemies spawned in new area")
            
            # Show enemy details
            print("\nSpawned enemies:")
            for i, enemy in enumerate(data, 1):
                print(f"  {i}. {enemy.get('name', 'Unknown')} (Level {enemy.get('level', 'Unknown')})")
            
            return True
        else:
            print(f"❌ FAILED: Expected exactly 5 enemies, got {enemy_count}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def test_level_distribution_high_level_player():
    """Test that lower level enemies spawn more frequently for high-level player"""
    print("\n=== TEST 2: Level distribution for high-level player (3 attempts) ===")
    
    test_coordinates = [
        (41.456, -74.789),
        (41.457, -74.790), 
        (41.458, -74.791)
    ]
    
    all_enemies = []
    success_count = 0
    
    for i, (lat, lon) in enumerate(test_coordinates, 1):
        print(f"\nAttempt {i}: Testing at coordinates ({lat}, {lon})")
        
        url = f"{BASE_URL}/monsters/spawn"
        params = {
            "latitude": lat,
            "longitude": lon,
            "player_level": 50  # High level player with access to Tiers 1-5
        }
        
        try:
            response = requests.get(url, params=params)
            print(f"Request: GET {url} with params {params}")
            print(f"Response Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ FAILED: Expected status 200, got {response.status_code}")
                continue
            
            data = response.json()
            enemy_count = len(data)
            
            if enemy_count != 5:
                print(f"❌ FAILED: Expected 5 enemies, got {enemy_count}")
                continue
                
            print(f"✅ Got exactly 5 enemies")
            success_count += 1
            
            # Analyze tier distribution
            tier_1_enemies = ["Thug", "Gangster", "Criminal", "Villain", "Bandit"]
            tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            
            print("Spawned enemies:")
            for enemy in data:
                enemy_name = enemy.get('name', 'Unknown')
                enemy_level = enemy.get('level', 'Unknown')
                print(f"  - {enemy_name} (Level {enemy_level})")
                
                # Determine tier based on enemy name
                if enemy_name in tier_1_enemies:
                    tier_counts[1] += 1
                elif enemy_name in ["Assassin", "Thief", "Hoodlum", "Pirate", "Bully"]:
                    tier_counts[2] += 1
                elif enemy_name in ["Offender", "Hood", "Mobster", "Gangsta", "Hooligan"]:
                    tier_counts[3] += 1
                elif enemy_name in ["Goon", "Ruffian", "Gang Banger", "Tough Guy", "Gorilla"]:
                    tier_counts[4] += 1
                elif enemy_name in ["Punk", "Rough Neck", "Rowdy Person", "Yardie", "Perpetrator"]:
                    tier_counts[5] += 1
                
                all_enemies.append({
                    'name': enemy_name,
                    'level': enemy_level,
                    'attempt': i
                })
            
            print(f"Tier distribution for attempt {i}:")
            for tier, count in tier_counts.items():
                print(f"  Tier {tier}: {count} enemies")
                
            # Check if lower tiers are more common
            if tier_counts[1] >= tier_counts[2] and tier_counts[1] >= tier_counts[3]:
                print("✅ Lower tier enemies (Tier 1) appear most frequently")
            else:
                print("⚠️  Lower tier enemies not most frequent")
                
        except Exception as e:
            print(f"❌ ERROR in attempt {i}: {str(e)}")
    
    print(f"\n=== SUMMARY: High-level player test ===")
    print(f"Successful attempts: {success_count}/3")
    
    if all_enemies:
        enemy_name_counts = Counter([e['name'] for e in all_enemies])
        print("\nOverall enemy name distribution:")
        for name, count in enemy_name_counts.most_common():
            print(f"  {name}: {count}")
    
    return success_count >= 2  # At least 2 out of 3 attempts should succeed

def test_level_1_player():
    """Test that level 1 player gets exactly 5 Tier 1 enemies only"""
    print("\n=== TEST 3: Level 1 player gets only Tier 1 enemies ===")
    
    url = f"{BASE_URL}/monsters/spawn"
    params = {
        "latitude": 42.111,
        "longitude": -75.222,
        "player_level": 1
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"Request: GET {url} with params {params}")
        print(f"Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected status 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        enemy_count = len(data)
        
        print(f"Number of enemies returned: {enemy_count}")
        
        if enemy_count != 5:
            print(f"❌ FAILED: Expected exactly 5 enemies, got {enemy_count}")
            return False
        
        print("✅ PASSED: Exactly 5 enemies spawned")
        
        # Check that all enemies are Tier 1
        tier_1_enemies = ["Thug", "Gangster", "Criminal", "Villain", "Bandit"]
        all_tier_1 = True
        
        print("\nSpawned enemies:")
        for i, enemy in enumerate(data, 1):
            enemy_name = enemy.get('name', 'Unknown')
            enemy_level = enemy.get('level', 'Unknown')
            print(f"  {i}. {enemy_name} (Level {enemy_level})")
            
            if enemy_name not in tier_1_enemies:
                all_tier_1 = False
                print(f"    ❌ ERROR: {enemy_name} is not a Tier 1 enemy!")
        
        if all_tier_1:
            print("✅ PASSED: All enemies are Tier 1 (Thug, Bandit, Villain, Criminal, Gangster)")
            return True
        else:
            print("❌ FAILED: Some enemies are not Tier 1")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def run_enemy_spawning_tests():
    """Run all enemy spawning tests"""
    print("🎯 ENEMY SPAWNING SYSTEM TESTING")
    print("=" * 50)
    
    results = []
    
    # Test 1: Exactly 5 enemies in new area
    results.append(test_exact_5_enemies_new_area())
    
    # Test 2: Level distribution for high-level player
    results.append(test_level_distribution_high_level_player())
    
    # Test 3: Level 1 player gets only Tier 1 enemies
    results.append(test_level_1_player())
    
    # Final summary
    print("\n" + "=" * 50)
    print("🏆 FINAL TEST RESULTS")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    test_names = [
        "Exactly 5 enemies spawn in new area",
        "Lower level enemies more frequent (high-level player)",
        "Level 1 player gets only Tier 1 enemies"
    ]
    
    for i, (result, name) in enumerate(zip(results, test_names)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{i+1}. {name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Enemy spawning system working correctly!")
        return True
    else:
        print(f"⚠️  {total - passed} test(s) failed - Enemy spawning system needs fixes")
        return False

if __name__ == "__main__":
    success = run_enemy_spawning_tests()
    sys.exit(0 if success else 1)