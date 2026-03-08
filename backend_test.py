#!/usr/bin/env python3
"""
Comprehensive Backend API Test Suite for GTA GPS RPG
Tests all backend endpoints with realistic data
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# API Configuration
API_BASE_URL = "https://orna-quest-map.preview.emergentagent.com/api"

class RPGAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_data = {}  # Store created resources for cleanup and further testing
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(ssl=False)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            print(f"  → {method} {url}")
            if params:
                print(f"    Params: {params}")
            if data:
                print(f"    Data: {json.dumps(data, indent=2)}")
            
            async with self.session.request(
                method, url, 
                json=data if data else None, 
                params=params if params else None
            ) as response:
                
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
    
    def print_result(self, test_name: str, result: Dict[str, Any]) -> bool:
        """Print test result and return success status"""
        if result["success"]:
            print(f"✅ {test_name} - SUCCESS")
            if isinstance(result["data"], dict) and "message" in result["data"]:
                print(f"   Message: {result['data']['message']}")
            return True
        else:
            print(f"❌ {test_name} - FAILED")
            print(f"   Status: {result['status_code']}")
            print(f"   Error: {result['data']}")
            return False
    
    async def test_1_root_endpoint(self) -> bool:
        """Test GET /"""
        print("\n1. Testing Root Endpoint")
        result = await self.make_request("GET", "/")
        return self.print_result("Root endpoint", result)
    
    async def test_2_character_classes(self) -> bool:
        """Test GET /classes"""
        print("\n2. Testing Character Classes")
        result = await self.make_request("GET", "/classes")
        
        success = self.print_result("Get character classes", result)
        if success and result["data"]:
            classes = list(result["data"].keys())
            print(f"   Available classes: {classes}")
            self.test_data["available_classes"] = classes
        
        return success
    
    async def test_3_create_player(self) -> bool:
        """Test POST /players"""
        print("\n3. Testing Player Creation")
        
        player_data = {
            "name": "Marcus_Rodriguez", 
            "character_class": "enforcer"
        }
        
        result = await self.make_request("POST", "/players", data=player_data)
        success = self.print_result("Create player", result)
        
        if success and result["data"]:
            player_id = result["data"].get("id")
            player_name = result["data"].get("name")
            player_class = result["data"].get("character_class")
            
            print(f"   Player ID: {player_id}")
            print(f"   Player Name: {player_name}")
            print(f"   Character Class: {player_class}")
            
            self.test_data["player_id"] = player_id
            self.test_data["player_name"] = player_name
        
        return success
    
    async def test_4_get_player(self) -> bool:
        """Test GET /players/{player_id}"""
        print("\n4. Testing Player Retrieval")
        
        if "player_id" not in self.test_data:
            print("❌ Skipping - No player ID from previous test")
            return False
        
        player_id = self.test_data["player_id"]
        result = await self.make_request("GET", f"/players/{player_id}")
        
        success = self.print_result("Get player", result)
        if success and result["data"]:
            player = result["data"]
            print(f"   Level: {player.get('level')}")
            print(f"   XP: {player.get('xp')}")
            print(f"   Cash: {player.get('cash')}")
            print(f"   Health: {player.get('stats', {}).get('health')}")
        
        return success
    
    async def test_5_spawn_monsters(self) -> bool:
        """Test GET /monsters/spawn"""
        print("\n5. Testing Monster Spawning")
        
        params = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "player_level": 1
        }
        
        result = await self.make_request("GET", "/monsters/spawn", params=params)
        success = self.print_result("Spawn monsters", result)
        
        if success and result["data"] and isinstance(result["data"], list):
            monsters = result["data"]
            print(f"   Monsters spawned/found: {len(monsters)}")
            
            if monsters:
                monster = monsters[0]
                monster_id = monster.get("id")
                monster_name = monster.get("name")
                monster_level = monster.get("level")
                
                print(f"   First monster: {monster_name} (Level {monster_level})")
                self.test_data["monster_id"] = monster_id
                self.test_data["monster_name"] = monster_name
        
        return success
    
    async def test_6_generate_missions(self) -> bool:
        """Test GET /missions/generate"""
        print("\n6. Testing Mission Generation")
        
        params = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "player_level": 1
        }
        
        result = await self.make_request("GET", "/missions/generate", params=params)
        success = self.print_result("Generate missions", result)
        
        if success and result["data"] and isinstance(result["data"], list):
            missions = result["data"]
            print(f"   Missions generated/found: {len(missions)}")
            
            if missions:
                mission = missions[0]
                mission_title = mission.get("title")
                mission_type = mission.get("mission_type")
                mission_difficulty = mission.get("difficulty")
                
                print(f"   First mission: {mission_title} ({mission_type}, {mission_difficulty})")
        
        return success
    
    async def test_7_start_battle(self) -> bool:
        """Test POST /battles/start"""
        print("\n7. Testing Battle Start")
        
        if "player_id" not in self.test_data or "monster_id" not in self.test_data:
            print("❌ Skipping - Missing player ID or monster ID from previous tests")
            return False
        
        params = {
            "player_id": self.test_data["player_id"],
            "enemy_type": "monster",
            "enemy_id": self.test_data["monster_id"]
        }
        
        result = await self.make_request("POST", "/battles/start", params=params)
        success = self.print_result("Start battle", result)
        
        if success and result["data"]:
            battle = result["data"]
            battle_id = battle.get("id")
            enemy_name = battle.get("enemy_name")
            player_health = battle.get("player_health")
            enemy_health = battle.get("enemy_health")
            
            print(f"   Battle ID: {battle_id}")
            print(f"   Fighting: {enemy_name}")
            print(f"   Player Health: {player_health}")
            print(f"   Enemy Health: {enemy_health}")
            
            self.test_data["battle_id"] = battle_id
        
        return success
    
    async def test_8_battle_action(self) -> bool:
        """Test POST /battles/{battle_id}/action"""
        print("\n8. Testing Battle Action")
        
        if "battle_id" not in self.test_data:
            print("❌ Skipping - No battle ID from previous test")
            return False
        
        battle_id = self.test_data["battle_id"]
        action_data = {"action": "attack"}
        
        result = await self.make_request("POST", f"/battles/{battle_id}/action", data=action_data)
        success = self.print_result("Battle action (attack)", result)
        
        if success and result["data"]:
            battle = result["data"]
            status = battle.get("status")
            player_health = battle.get("player_health")
            enemy_health = battle.get("enemy_health")
            turn = battle.get("turn")
            
            print(f"   Battle Status: {status}")
            print(f"   Turn: {turn}")
            print(f"   Player Health: {player_health}")
            print(f"   Enemy Health: {enemy_health}")
            
            if battle.get("combat_log"):
                latest_log = battle["combat_log"][-1] if battle["combat_log"] else "No logs"
                print(f"   Latest Action: {latest_log}")
        
        return success
    
    async def test_9_get_battle(self) -> bool:
        """Test GET /battles/{battle_id}"""
        print("\n9. Testing Battle Retrieval")
        
        if "battle_id" not in self.test_data:
            print("❌ Skipping - No battle ID from previous test")
            return False
        
        battle_id = self.test_data["battle_id"]
        result = await self.make_request("GET", f"/battles/{battle_id}")
        
        success = self.print_result("Get battle state", result)
        if success and result["data"]:
            battle = result["data"]
            status = battle.get("status")
            turn = battle.get("turn")
            print(f"   Battle Status: {status}")
            print(f"   Current Turn: {turn}")
        
        return success
    
    async def test_10_create_guild(self) -> bool:
        """Test POST /guilds"""
        print("\n10. Testing Guild Creation")
        
        if "player_id" not in self.test_data:
            print("❌ Skipping - No player ID from previous tests")
            return False
        
        guild_data = {
            "name": "Shadow Syndicate",
            "tag": "SHAD",
            "description": "Elite criminals operating in the shadows of the city"
        }
        
        params = {"leader_id": self.test_data["player_id"]}
        
        result = await self.make_request("POST", "/guilds", data=guild_data, params=params)
        success = self.print_result("Create guild", result)
        
        if success and result["data"]:
            guild = result["data"]
            guild_id = guild.get("id")
            guild_name = guild.get("name")
            guild_tag = guild.get("tag")
            
            print(f"   Guild ID: {guild_id}")
            print(f"   Guild Name: {guild_name}")
            print(f"   Guild Tag: {guild_tag}")
            
            self.test_data["guild_id"] = guild_id
        
        return success
    
    async def test_11_list_guilds(self) -> bool:
        """Test GET /guilds"""
        print("\n11. Testing Guild Listing")
        
        result = await self.make_request("GET", "/guilds")
        success = self.print_result("List guilds", result)
        
        if success and result["data"] and isinstance(result["data"], list):
            guilds = result["data"]
            print(f"   Total guilds: {len(guilds)}")
            
            if guilds:
                guild = guilds[0]
                print(f"   Top guild: {guild.get('name')} (Level {guild.get('level')})")
        
        return success
    
    async def test_12_leaderboard(self) -> bool:
        """Test GET /leaderboard"""
        print("\n12. Testing Leaderboard")
        
        result = await self.make_request("GET", "/leaderboard")
        success = self.print_result("Get leaderboard", result)
        
        if success and result["data"] and isinstance(result["data"], list):
            players = result["data"]
            print(f"   Players on leaderboard: {len(players)}")
            
            if players:
                top_player = players[0]
                print(f"   #1 Player: {top_player.get('name')} (Rep: {top_player.get('reputation')})")
        
        return success
    
    async def test_13_get_skills(self) -> bool:
        """Test GET /skills"""
        print("\n13. Testing Skills List")
        
        result = await self.make_request("GET", "/skills")
        success = self.print_result("Get all skills", result)
        
        if success and result["data"] and isinstance(result["data"], dict):
            skills = result["data"]
            skill_names = list(skills.keys())
            print(f"   Available skills: {len(skill_names)}")
            print(f"   Skills: {', '.join(skill_names)}")
        
        return success
    
    async def test_14_player_skills(self) -> bool:
        """Test GET /players/{player_id}/skills"""
        print("\n14. Testing Player Skills")
        
        if "player_id" not in self.test_data:
            print("❌ Skipping - No player ID from previous tests")
            return False
        
        player_id = self.test_data["player_id"]
        result = await self.make_request("GET", f"/players/{player_id}/skills")
        
        success = self.print_result("Get player skills", result)
        if success and result["data"] and isinstance(result["data"], list):
            skills = result["data"]
            unlocked_skills = [s for s in skills if s.get("unlocked")]
            available_skills = [s for s in skills if not s.get("unlocked")]
            
            print(f"   Unlocked skills: {len(unlocked_skills)}")
            print(f"   Available to unlock: {len(available_skills)}")
            
            if unlocked_skills:
                skill_names = [s.get("name") for s in unlocked_skills]
                print(f"   Unlocked: {', '.join(skill_names)}")
        
        return success

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all API tests in sequence"""
        print("=" * 60)
        print("🎮 GTA GPS RPG Backend API Test Suite")
        print("=" * 60)
        print(f"API Base URL: {self.base_url}")
        print(f"Test Started: {datetime.now().isoformat()}")
        
        test_results = {}
        
        # Define test sequence
        tests = [
            ("Root Endpoint", self.test_1_root_endpoint),
            ("Character Classes", self.test_2_character_classes),
            ("Create Player", self.test_3_create_player),
            ("Get Player", self.test_4_get_player),
            ("Spawn Monsters", self.test_5_spawn_monsters),
            ("Generate Missions", self.test_6_generate_missions),
            ("Start Battle", self.test_7_start_battle),
            ("Battle Action", self.test_8_battle_action),
            ("Get Battle", self.test_9_get_battle),
            ("Create Guild", self.test_10_create_guild),
            ("List Guilds", self.test_11_list_guilds),
            ("Leaderboard", self.test_12_leaderboard),
            ("Get Skills", self.test_13_get_skills),
            ("Player Skills", self.test_14_player_skills)
        ]
        
        # Run tests
        for test_name, test_func in tests:
            try:
                test_results[test_name] = await test_func()
            except Exception as e:
                print(f"❌ {test_name} - EXCEPTION: {str(e)}")
                test_results[test_name] = False
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\n📈 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All tests PASSED! Backend API is working correctly.")
        else:
            failed_tests = [name for name, result in test_results.items() if not result]
            print(f"⚠️  Failed tests: {', '.join(failed_tests)}")
        
        return test_results

async def main():
    """Main test runner"""
    try:
        async with RPGAPITester(API_BASE_URL) as tester:
            results = await tester.run_all_tests()
            
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