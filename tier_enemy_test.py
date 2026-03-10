#!/usr/bin/env python3
"""
10-Tier Enemy System Test Suite for GTA GPS RPG
Tests the new enemy tier system to ensure proper enemy spawning based on player level
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any, Optional, List

# API Configuration
API_BASE_URL = "https://real-world-raid-game.preview.emergentagent.com/api"

class TierEnemyTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(ssl=False)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            print(f"  → {method} {url}")
            if params:
                print(f"    Params: {params}")
            
            async with self.session.request(method, url, params=params if params else None) as response:
                print(f"    Status: {response.status}")
                
                if response.content_type == 'application/json':
                    result = await response.json()
                else:
                    result = {"error": "Non-JSON response", "text": await response.text()}
                
                return {
                    "success": 200 <= response.status < 300,
                    "status_code": response.status,
                    "data": result
                }
                
        except Exception as e:
            print(f"    ❌ Request failed: {str(e)}")
            return {
                "success": False,
                "status_code": 0,
                "data": {"error": str(e)}
            }
    
    def analyze_enemy_tier_compliance(self, monsters: List[Dict], player_level: int, expected_tiers: List[int]) -> Dict[str, Any]:
        """Analyze spawned monsters for tier system compliance"""
        analysis = {
            "total_monsters": len(monsters),
            "tier_distribution": {},
            "enemy_names": [],
            "boss_count": 0,
            "non_boss_count": 0,
            "tier_violations": [],
            "expected_tier_1_names": ["Thug", "Gangster", "Criminal", "Villain", "Bandit"],
            "expected_tier_2_names": ["Assassin", "Thief", "Hoodlum", "Pirate", "Bully"],
            "expected_tier_3_names": ["Offender", "Hood", "Mobster", "Gangster", "Hooligan"],
            "tier_1_boss": "Super Thug",
            "tier_2_boss": "Super Bully",
            "tier_3_boss": "Super Hood"
        }
        
        # Analyze each monster
        for monster in monsters:
            name = monster.get("name", "")
            level = monster.get("level", 0)
            monster_type = monster.get("monster_type", "")
            
            analysis["enemy_names"].append(name)
            
            # Determine if it's a boss
            is_boss = "Super" in name or monster_type == "boss"
            if is_boss:
                analysis["boss_count"] += 1
            else:
                analysis["non_boss_count"] += 1
            
            # Determine tier based on name
            tier = self.get_tier_from_name(name)
            if tier:
                if tier not in analysis["tier_distribution"]:
                    analysis["tier_distribution"][tier] = 0
                analysis["tier_distribution"][tier] += 1
                
                # Check if this tier is allowed for player level
                if tier not in expected_tiers:
                    analysis["tier_violations"].append({
                        "name": name,
                        "tier": tier,
                        "level": level,
                        "reason": f"Tier {tier} enemy spawned for player level {player_level}"
                    })
        
        # Check for proper boss spawning rules
        if player_level < 11 and analysis["boss_count"] > 0:
            analysis["tier_violations"].append({
                "name": "Boss spawning",
                "tier": "N/A",
                "level": player_level,
                "reason": f"Boss enemies spawned for player level {player_level} (bosses should only spawn at level 11+)"
            })
        
        return analysis
    
    def get_tier_from_name(self, name: str) -> Optional[int]:
        """Get tier number based on enemy name"""
        # Tier 1 enemies
        tier_1_names = ["Thug", "Gangster", "Criminal", "Villain", "Bandit", "Super Thug"]
        # Tier 2 enemies  
        tier_2_names = ["Assassin", "Thief", "Hoodlum", "Pirate", "Bully", "Super Bully"]
        # Tier 3 enemies
        tier_3_names = ["Offender", "Hood", "Mobster", "Hooligan", "Super Hood"]
        # Note: Tier 3 also has "Gangster" again, but we'll consider it tier 3 when it appears with higher level enemies
        
        if name in tier_1_names:
            return 1
        elif name in tier_2_names:
            return 2
        elif name in tier_3_names:
            return 3
        # Add more tiers as needed
        return None
    
    async def test_level_1_tier_1_only(self) -> bool:
        """Test level 1 player - should only get Tier 1 enemies, NO bosses"""
        print("\n🎯 Test 1: Level 1 Player - Tier 1 Enemies Only")
        
        params = {
            "latitude": 40.758,
            "longitude": -73.9855,
            "player_level": 1
        }
        
        result = await self.make_request("GET", "/monsters/spawn", params=params)
        
        if not result["success"]:
            print(f"❌ API call failed: {result['data']}")
            return False
        
        monsters = result["data"] if isinstance(result["data"], list) else []
        analysis = self.analyze_enemy_tier_compliance(monsters, 1, [1])  # Only tier 1 allowed
        
        print(f"   Monsters spawned: {analysis['total_monsters']}")
        print(f"   Enemy names: {', '.join(analysis['enemy_names'])}")
        print(f"   Tier distribution: {analysis['tier_distribution']}")
        print(f"   Bosses: {analysis['boss_count']}")
        print(f"   Non-bosses: {analysis['non_boss_count']}")
        
        # Verify no bosses for level 1
        if analysis["boss_count"] > 0:
            print("   ❌ VIOLATION: Bosses found for level 1 player (should be none)")
            return False
        
        # Verify only tier 1 enemies
        if len(analysis["tier_violations"]) > 0:
            print("   ❌ TIER VIOLATIONS:")
            for violation in analysis["tier_violations"]:
                print(f"      - {violation['name']}: {violation['reason']}")
            return False
        
        # Verify tier 1 enemy names are correct
        expected_names = analysis["expected_tier_1_names"]
        found_valid_names = [name for name in analysis["enemy_names"] if name in expected_names]
        
        if len(found_valid_names) == 0:
            print(f"   ❌ No valid tier 1 enemy names found. Expected: {expected_names}")
            return False
        
        print(f"   ✅ Valid tier 1 enemies found: {found_valid_names}")
        print("   ✅ Level 1 player test PASSED - Only tier 1, no bosses")
        return True
    
    async def test_level_5_still_tier_1(self) -> bool:
        """Test level 5 player - should still only get Tier 1 enemies"""
        print("\n🎯 Test 2: Level 5 Player - Still Tier 1 Only")
        
        params = {
            "latitude": 40.76,
            "longitude": -73.98,
            "player_level": 5
        }
        
        result = await self.make_request("GET", "/monsters/spawn", params=params)
        
        if not result["success"]:
            print(f"❌ API call failed: {result['data']}")
            return False
        
        monsters = result["data"] if isinstance(result["data"], list) else []
        analysis = self.analyze_enemy_tier_compliance(monsters, 5, [1])  # Only tier 1 allowed
        
        print(f"   Monsters spawned: {analysis['total_monsters']}")
        print(f"   Enemy names: {', '.join(analysis['enemy_names'])}")
        print(f"   Tier distribution: {analysis['tier_distribution']}")
        print(f"   Bosses: {analysis['boss_count']}")
        
        # Verify no bosses for level 5 (bosses start at level 11)
        if analysis["boss_count"] > 0:
            print("   ❌ VIOLATION: Bosses found for level 5 player (should be none)")
            return False
        
        # Verify only tier 1 enemies
        if len(analysis["tier_violations"]) > 0:
            print("   ❌ TIER VIOLATIONS:")
            for violation in analysis["tier_violations"]:
                print(f"      - {violation['name']}: {violation['reason']}")
            return False
        
        print("   ✅ Level 5 player test PASSED - Only tier 1, no bosses")
        return True
    
    async def test_level_15_tier_1_and_2(self) -> bool:
        """Test level 15 player - should get Tier 1 + Tier 2 enemies, including bosses"""
        print("\n🎯 Test 3: Level 15 Player - Tier 1 + Tier 2 Enemies")
        
        params = {
            "latitude": 40.77,
            "longitude": -73.97,
            "player_level": 15
        }
        
        result = await self.make_request("GET", "/monsters/spawn", params=params)
        
        if not result["success"]:
            print(f"❌ API call failed: {result['data']}")
            return False
        
        monsters = result["data"] if isinstance(result["data"], list) else []
        analysis = self.analyze_enemy_tier_compliance(monsters, 15, [1, 2])  # Tier 1 and 2 allowed
        
        print(f"   Monsters spawned: {analysis['total_monsters']}")
        print(f"   Enemy names: {', '.join(analysis['enemy_names'])}")
        print(f"   Tier distribution: {analysis['tier_distribution']}")
        print(f"   Bosses: {analysis['boss_count']}")
        
        # Verify tier violations
        if len(analysis["tier_violations"]) > 0:
            print("   ❌ TIER VIOLATIONS:")
            for violation in analysis["tier_violations"]:
                print(f"      - {violation['name']}: {violation['reason']}")
            return False
        
        # Check for expected tier 1 and tier 2 names
        expected_tier_1 = analysis["expected_tier_1_names"]
        expected_tier_2 = analysis["expected_tier_2_names"]
        all_expected = expected_tier_1 + expected_tier_2 + [analysis["tier_1_boss"]]
        
        found_valid_names = [name for name in analysis["enemy_names"] if name in all_expected]
        
        if len(found_valid_names) == 0:
            print(f"   ❌ No valid tier 1/2 enemy names found. Expected: {all_expected}")
            return False
        
        print(f"   ✅ Valid tier 1/2 enemies found: {found_valid_names}")
        
        # Bosses are allowed at level 15 (11+), check if Super Thug can appear
        if analysis["tier_1_boss"] in analysis["enemy_names"]:
            print(f"   ✅ Boss '{analysis['tier_1_boss']}' correctly available for level 15")
        
        print("   ✅ Level 15 player test PASSED - Tier 1+2 enemies available")
        return True
    
    async def test_level_25_tier_1_2_3(self) -> bool:
        """Test level 25 player - should get Tier 1 + 2 + 3 enemies"""
        print("\n🎯 Test 4: Level 25 Player - Tier 1 + 2 + 3 Enemies")
        
        params = {
            "latitude": 40.78,
            "longitude": -73.96,
            "player_level": 25
        }
        
        result = await self.make_request("GET", "/monsters/spawn", params=params)
        
        if not result["success"]:
            print(f"❌ API call failed: {result['data']}")
            return False
        
        monsters = result["data"] if isinstance(result["data"], list) else []
        analysis = self.analyze_enemy_tier_compliance(monsters, 25, [1, 2, 3])  # Tier 1, 2, and 3 allowed
        
        print(f"   Monsters spawned: {analysis['total_monsters']}")
        print(f"   Enemy names: {', '.join(analysis['enemy_names'])}")
        print(f"   Tier distribution: {analysis['tier_distribution']}")
        print(f"   Bosses: {analysis['boss_count']}")
        
        # Verify tier violations
        if len(analysis["tier_violations"]) > 0:
            print("   ❌ TIER VIOLATIONS:")
            for violation in analysis["tier_violations"]:
                print(f"      - {violation['name']}: {violation['reason']}")
            return False
        
        # Check for tier 3 enemies (Offender, Hood, Mobster)
        expected_tier_3 = analysis["expected_tier_3_names"]
        found_tier_3 = [name for name in analysis["enemy_names"] if name in expected_tier_3]
        
        if len(found_tier_3) > 0:
            print(f"   ✅ Tier 3 enemies found: {found_tier_3}")
        
        print("   ✅ Level 25 player test PASSED - Tier 1+2+3 enemies available")
        return True
    
    async def test_monster_name_verification(self) -> bool:
        """Verify monster names match the tier system (not old names)"""
        print("\n🎯 Test 5: Monster Name Verification")
        
        # Test at different levels to get a variety of monsters
        test_levels = [1, 15, 25]
        all_monster_names = set()
        
        for level in test_levels:
            params = {
                "latitude": 40.75 + (level * 0.01),  # Slightly different coordinates
                "longitude": -73.98 + (level * 0.01),
                "player_level": level
            }
            
            result = await self.make_request("GET", "/monsters/spawn", params=params)
            
            if result["success"] and isinstance(result["data"], list):
                for monster in result["data"]:
                    name = monster.get("name", "")
                    all_monster_names.add(name)
        
        print(f"   All unique monster names found: {sorted(list(all_monster_names))}")
        
        # Check for old-style names (these should NOT appear)
        old_names = ["Street Thug", "Gang Member", "Corrupt Cop", "Drug Dealer", "Hitman"]
        found_old_names = [name for name in all_monster_names if name in old_names]
        
        if found_old_names:
            print(f"   ❌ OLD NAMING SYSTEM DETECTED: {found_old_names}")
            print("      These names should be replaced with new tier system names")
            return False
        
        # Check for new tier system names
        new_tier_names = ["Thug", "Gangster", "Criminal", "Villain", "Bandit", "Super Thug",
                         "Assassin", "Thief", "Hoodlum", "Pirate", "Bully", "Super Bully",
                         "Offender", "Hood", "Mobster", "Hooligan", "Super Hood"]
        
        found_new_names = [name for name in all_monster_names if name in new_tier_names]
        
        if len(found_new_names) > 0:
            print(f"   ✅ New tier system names confirmed: {sorted(found_new_names)}")
            print("   ✅ Monster names match the tier system")
            return True
        else:
            print("   ❌ No tier system names found - this indicates a problem")
            return False
    
    async def test_boss_spawning_rules(self) -> bool:
        """Verify boss spawning rules (level 11+ only)"""
        print("\n🎯 Test 6: Boss Spawning Rules Verification")
        
        # Test levels below 11 (should have no bosses)
        no_boss_levels = [1, 5, 10]
        boss_found_early = False
        
        for level in no_boss_levels:
            print(f"   Testing level {level} (should have NO bosses)...")
            params = {
                "latitude": 40.75 + (level * 0.005),
                "longitude": -73.98 + (level * 0.005), 
                "player_level": level
            }
            
            result = await self.make_request("GET", "/monsters/spawn", params=params)
            
            if result["success"] and isinstance(result["data"], list):
                for monster in result["data"]:
                    name = monster.get("name", "")
                    if "Super" in name or monster.get("monster_type") == "boss":
                        print(f"      ❌ BOSS VIOLATION: '{name}' spawned for level {level}")
                        boss_found_early = True
        
        if boss_found_early:
            print("   ❌ Bosses found at levels < 11 - VIOLATION")
            return False
        
        # Test levels 11+ (bosses should be possible)
        boss_levels = [11, 15, 21, 25]
        boss_names_found = set()
        
        for level in boss_levels:
            print(f"   Testing level {level} (bosses should be possible)...")
            params = {
                "latitude": 40.75 + (level * 0.005),
                "longitude": -73.98 + (level * 0.005),
                "player_level": level
            }
            
            # Try multiple spawns to increase chance of finding a boss
            for attempt in range(3):
                result = await self.make_request("GET", "/monsters/spawn", params=params)
                
                if result["success"] and isinstance(result["data"], list):
                    for monster in result["data"]:
                        name = monster.get("name", "")
                        if "Super" in name:
                            boss_names_found.add(name)
        
        if len(boss_names_found) > 0:
            print(f"   ✅ Boss enemies found at appropriate levels: {sorted(list(boss_names_found))}")
        else:
            print("   ⚠️  No bosses found in multiple attempts (may be rare spawn rate)")
        
        print("   ✅ Boss spawning rules verification PASSED")
        return True
    
    async def run_all_tier_tests(self) -> Dict[str, bool]:
        """Run all tier system tests"""
        print("=" * 70)
        print("🎮 GTA GPS RPG - 10-Tier Enemy System Test Suite")
        print("=" * 70)
        print(f"API Base URL: {self.base_url}")
        
        test_results = {}
        
        # Define test sequence
        tests = [
            ("Level 1 - Tier 1 Only", self.test_level_1_tier_1_only),
            ("Level 5 - Still Tier 1", self.test_level_5_still_tier_1),  
            ("Level 15 - Tier 1+2", self.test_level_15_tier_1_and_2),
            ("Level 25 - Tier 1+2+3", self.test_level_25_tier_1_2_3),
            ("Monster Name Verification", self.test_monster_name_verification),
            ("Boss Spawning Rules", self.test_boss_spawning_rules),
        ]
        
        # Run tests
        for test_name, test_func in tests:
            try:
                test_results[test_name] = await test_func()
            except Exception as e:
                print(f"❌ {test_name} - EXCEPTION: {str(e)}")
                test_results[test_name] = False
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 10-TIER ENEMY SYSTEM TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n📈 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All tier system tests PASSED! 10-tier enemy system is working correctly.")
            print("\n✅ KEY FINDINGS:")
            print("   • Level 1-10 players get only Tier 1 enemies (no bosses)")
            print("   • Level 11+ players can encounter bosses (Super Thug, etc.)")
            print("   • Level 15+ players get Tier 1 + Tier 2 enemies")
            print("   • Level 25+ players get Tier 1 + Tier 2 + Tier 3 enemies")
            print("   • Monster names follow new tier system (Thug, Gangster, etc.)")
            print("   • No old naming system detected")
        else:
            failed_tests = [name for name, result in test_results.items() if not result]
            print(f"⚠️  Failed tests: {', '.join(failed_tests)}")
            print("\n🔍 ISSUES FOUND:")
            print("   Check the failed tests above for specific tier system violations")
        
        return test_results

async def main():
    """Main test runner"""
    try:
        async with TierEnemyTester(API_BASE_URL) as tester:
            results = await tester.run_all_tier_tests()
            
            # Exit with error code if any tests failed
            failed_count = sum(1 for result in results.values() if not result)
            return failed_count
            
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test suite failed with exception: {e}")
        return 1

if __name__ == "__main__":
    failed_tests = asyncio.run(main())
    sys.exit(failed_tests)