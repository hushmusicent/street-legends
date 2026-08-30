from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import random
import math
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Ensure static directory exists
STATIC_DIR = ROOT_DIR / 'static'
STATIC_DIR.mkdir(exist_ok=True)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Helper function to serialize MongoDB documents
def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if key == '_id':
                continue  # Skip MongoDB _id field
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = serialize_doc(value)
            elif isinstance(value, list):
                result[key] = [serialize_doc(v) if isinstance(v, dict) else v for v in value]
            else:
                result[key] = value
        return result
    return doc

# AI Configuration
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Create the main app
app = FastAPI(title="GTA GPS RPG API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== GAME CONSTANTS ==============
CHARACTER_CLASSES = {
    "street_soldier": {
        "name": "Street Soldier",
        "description": "A hardened fighter from the streets. High attack and defense.",
        "base_stats": {"health": 120, "attack": 15, "defense": 12, "speed": 10, "luck": 8}
    },
    "hacker": {
        "name": "Hacker",
        "description": "A tech genius who uses digital skills in combat. High speed and luck.",
        "base_stats": {"health": 80, "attack": 10, "defense": 8, "speed": 18, "luck": 15}
    },
    "enforcer": {
        "name": "Enforcer",
        "description": "A brutal powerhouse. Maximum attack and health.",
        "base_stats": {"health": 150, "attack": 20, "defense": 10, "speed": 6, "luck": 5}
    },
    "ghost": {
        "name": "Ghost",
        "description": "A silent assassin. Critical hits and evasion specialist.",
        "base_stats": {"health": 90, "attack": 18, "defense": 6, "speed": 16, "luck": 12}
    }
}

EQUIPMENT_TYPES = ["weapon", "armor", "accessory", "vehicle"]
RARITIES = ["common", "uncommon", "rare", "epic", "legendary"]

# ============== DURABILITY SYSTEM ==============
# Max durability by rarity (higher rarity = more durable)
DURABILITY_BY_RARITY = {
    "common": 100,
    "uncommon": 150,
    "rare": 200,
    "epic": 300,
    "legendary": 500,
}

# Durability loss rates by equipment type
DURABILITY_LOSS = {
    "weapon": {"per_battle": 8, "on_hit": 2},       # Loses durability per battle + extra on hits
    "armor": {"per_battle": 5, "on_damage": 3},     # Loses durability per battle + extra when damaged
    "accessory": {"per_battle": 2, "passive": 1},   # Small loss per battle + passive decay
    "vehicle": {"per_use": 10, "per_territory": 15}, # Loses on movement/territory capture
}

# Repair cost multiplier by rarity (cost = base_value * multiplier * damage_percent)
# Increased by 50% for game balance
REPAIR_COST_MULTIPLIER = {
    "common": 0.45,      # was 0.3, +50%
    "uncommon": 0.6,     # was 0.4, +50%
    "rare": 0.75,        # was 0.5, +50%
    "epic": 0.9,         # was 0.6, +50%
    "legendary": 1.2,    # was 0.8, +50%
}

def get_max_durability(item_id: str) -> int:
    """Get max durability for an item based on its rarity"""
    # Try to find item in STARTER_ITEMS first, then in ALL_ITEMS (which gets populated later)
    item = STARTER_ITEMS.get(item_id)
    if not item and 'ALL_ITEMS' in globals():
        item = ALL_ITEMS.get(item_id)
    if not item:
        return 100
    rarity = item.get("rarity", "common")
    return DURABILITY_BY_RARITY.get(rarity, 100)

def create_inventory_item(item_id: str, durability: int = None) -> dict:
    """Create an inventory item dict with durability"""
    max_dur = get_max_durability(item_id)
    return {
        "item_id": item_id,
        "durability": durability if durability is not None else max_dur,
        "max_durability": max_dur,
    }

def calculate_repair_cost(item_id: str, current_durability: int) -> int:
    """Calculate cost to repair an item"""
    # Try to find item in STARTER_ITEMS first, then in ALL_ITEMS
    item = STARTER_ITEMS.get(item_id)
    if not item and 'ALL_ITEMS' in globals():
        item = ALL_ITEMS.get(item_id)
    if not item:
        return 0
    
    max_dur = get_max_durability(item_id)
    damage_percent = (max_dur - current_durability) / max_dur
    rarity = item.get("rarity", "common")
    base_value = item.get("value", 10)
    multiplier = REPAIR_COST_MULTIPLIER.get(rarity, 0.5)
    
    return max(1, int(base_value * multiplier * damage_percent))

def is_item_broken(inventory_item: dict) -> bool:
    """Check if an inventory item is broken (0 durability)"""
    if isinstance(inventory_item, str):
        return False  # Legacy string items are never broken
    return inventory_item.get("durability", 100) <= 0

def migrate_inventory_item(item) -> dict:
    """Migrate old string inventory items to new dict format"""
    if isinstance(item, str):
        return create_inventory_item(item)
    return item


async def apply_battle_durability_loss(player_id: str, dealt_damage: bool, took_damage: bool):
    """Apply durability loss to equipped items after a battle turn"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        return
    
    equipment = player.get("equipment", {})
    inventory = player.get("inventory", [])
    inventory = [migrate_inventory_item(item) for item in inventory]
    
    updates = {}
    
    for item_type, item_id in equipment.items():
        if not item_id:
            continue
        
        # Find item in inventory
        for idx, inv_item in enumerate(inventory):
            i_id = inv_item.get("item_id") if isinstance(inv_item, dict) else inv_item
            if i_id == item_id:
                current_dur = inv_item.get("durability", 100)
                loss = 0
                
                # Calculate durability loss based on item type
                if item_type == "weapon":
                    loss = DURABILITY_LOSS["weapon"]["per_battle"]
                    if dealt_damage:
                        loss += DURABILITY_LOSS["weapon"]["on_hit"]
                elif item_type == "armor":
                    loss = DURABILITY_LOSS["armor"]["per_battle"]
                    if took_damage:
                        loss += DURABILITY_LOSS["armor"]["on_damage"]
                elif item_type == "accessory":
                    loss = DURABILITY_LOSS["accessory"]["per_battle"]
                
                new_dur = max(0, current_dur - loss)
                inventory[idx]["durability"] = new_dur
                break
    
    # Save updated inventory
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"inventory": inventory}}
    )


async def apply_vehicle_durability_loss(player_id: str, action_type: str = "use"):
    """Apply durability loss to equipped vehicle for movement/territory actions"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        return
    
    equipment = player.get("equipment", {})
    vehicle_id = equipment.get("vehicle")
    if not vehicle_id:
        return
    
    inventory = player.get("inventory", [])
    inventory = [migrate_inventory_item(item) for item in inventory]
    
    for idx, inv_item in enumerate(inventory):
        i_id = inv_item.get("item_id") if isinstance(inv_item, dict) else inv_item
        if i_id == vehicle_id:
            current_dur = inv_item.get("durability", 100)
            
            if action_type == "territory":
                loss = DURABILITY_LOSS["vehicle"]["per_territory"]
            else:
                loss = DURABILITY_LOSS["vehicle"]["per_use"]
            
            new_dur = max(0, current_dur - loss)
            inventory[idx]["durability"] = new_dur
            
            await db.players.update_one(
                {"id": player_id},
                {"$set": {"inventory": inventory}}
            )
            break


# Starter equipment items
STARTER_ITEMS = {
    "rusty_pipe": {
        "id": "rusty_pipe", "name": "Rusty Pipe", "description": "A bent pipe found in an alley. Better than nothing.",
        "equipment_type": "weapon", "rarity": "common",
        "stats_bonus": {"attack": 2}, "level_requirement": 1, "value": 10
    },
    "worn_jacket": {
        "id": "worn_jacket", "name": "Worn Leather Jacket", "description": "A beat-up jacket that's seen better days.",
        "equipment_type": "armor", "rarity": "common",
        "stats_bonus": {"defense": 2, "speed": 1}, "level_requirement": 1, "value": 15
    },
    "brass_knuckles": {
        "id": "brass_knuckles", "name": "Brass Knuckles", "description": "Classic street weapon. Hits hard.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 4, "speed": -1}, "level_requirement": 2, "value": 30
    },
    "chain_necklace": {
        "id": "chain_necklace", "name": "Gold Chain", "description": "A flashy chain that boosts your street cred.",
        "equipment_type": "accessory", "rarity": "uncommon",
        "stats_bonus": {"luck": 3, "defense": 1}, "level_requirement": 1, "value": 25
    },
    "kevlar_vest": {
        "id": "kevlar_vest", "name": "Kevlar Vest", "description": "Light body armor. Could save your life.",
        "equipment_type": "armor", "rarity": "rare",
        "stats_bonus": {"defense": 6, "speed": -2}, "level_requirement": 5, "value": 80
    },
    "switchblade": {
        "id": "switchblade", "name": "Switchblade", "description": "Quick and deadly. A street classic.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 3, "speed": 2}, "level_requirement": 3, "value": 40
    },
    "lucky_dice": {
        "id": "lucky_dice", "name": "Lucky Dice", "description": "Loaded dice that bring good fortune.",
        "equipment_type": "accessory", "rarity": "rare",
        "stats_bonus": {"luck": 5}, "level_requirement": 3, "value": 50
    },
    "beat_up_bike": {
        "id": "beat_up_bike", "name": "Beat-up Bike", "description": "A rusty bike that still gets you places faster.",
        "equipment_type": "vehicle", "rarity": "common",
        "stats_bonus": {"speed": 4}, "level_requirement": 1, "value": 20
    },
    "baseball_bat": {
        "id": "baseball_bat", "name": "Baseball Bat", "description": "Louisville Slugger. Classic enforcer tool.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 5}, "level_requirement": 4, "value": 45
    },
    "hoodie_of_shadows": {
        "id": "hoodie_of_shadows", "name": "Shadow Hoodie", "description": "Dark hoodie that helps you blend into the night.",
        "equipment_type": "armor", "rarity": "rare",
        "stats_bonus": {"defense": 3, "speed": 3, "luck": 2}, "level_requirement": 5, "value": 75
    },
}

ALL_ITEMS = {**STARTER_ITEMS}

# Additional gun shop items - Prices DOUBLED
GUN_SHOP_ITEMS = {
    # Pistols
    "glock_9mm": {
        "id": "glock_9mm", "name": "Glock 9mm", "description": "Standard-issue sidearm. Reliable and deadly.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 6, "speed": 1}, "level_requirement": 2, "value": 166
    },
    "desert_eagle": {
        "id": "desert_eagle", "name": "Desert Eagle .50", "description": "Massive hand cannon. One shot, one kill.",
        "equipment_type": "weapon", "rarity": "rare",
        "stats_bonus": {"attack": 10, "speed": -2}, "level_requirement": 5, "value": 360
    },
    "gold_plated_pistol": {
        "id": "gold_plated_pistol", "name": "Gold-Plated Pistol", "description": "A kingpin's weapon. Style meets firepower.",
        "equipment_type": "weapon", "rarity": "epic",
        "stats_bonus": {"attack": 12, "luck": 3}, "level_requirement": 8, "value": 600
    },
    # SMGs
    "uzi": {
        "id": "uzi", "name": "Micro Uzi", "description": "Compact and fast. Spray and pray.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 5, "speed": 3}, "level_requirement": 3, "value": 196
    },
    "mp5": {
        "id": "mp5", "name": "MP5 Submachine Gun", "description": "Precision SMG used by tactical teams worldwide.",
        "equipment_type": "weapon", "rarity": "rare",
        "stats_bonus": {"attack": 8, "speed": 2}, "level_requirement": 6, "value": 330
    },
    # Shotguns
    "sawed_off": {
        "id": "sawed_off", "name": "Sawed-Off Shotgun", "description": "Close range devastation. Not subtle.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 7, "speed": -1}, "level_requirement": 4, "value": 210
    },
    "combat_shotgun": {
        "id": "combat_shotgun", "name": "Combat Shotgun", "description": "Military-grade room clearer.",
        "equipment_type": "weapon", "rarity": "rare",
        "stats_bonus": {"attack": 11, "defense": 1}, "level_requirement": 7, "value": 420
    },
    # Rifles
    "ak47": {
        "id": "ak47", "name": "AK-47", "description": "The most iconic assault rifle. Never jams.",
        "equipment_type": "weapon", "rarity": "rare",
        "stats_bonus": {"attack": 12, "speed": -1}, "level_requirement": 8, "value": 480
    },
    "sniper_rifle": {
        "id": "sniper_rifle", "name": "Sniper Rifle", "description": "Long range precision. One shot from downtown.",
        "equipment_type": "weapon", "rarity": "epic",
        "stats_bonus": {"attack": 15, "speed": -3, "luck": 2}, "level_requirement": 10, "value": 750
    },
    # Body Armor
    "tactical_vest": {
        "id": "tactical_vest", "name": "Tactical Vest", "description": "Military-grade protection with ammo pouches.",
        "equipment_type": "armor", "rarity": "uncommon",
        "stats_bonus": {"defense": 4, "attack": 1}, "level_requirement": 3, "value": 150
    },
    "riot_gear": {
        "id": "riot_gear", "name": "Riot Gear", "description": "Full body protection. Slow but tough.",
        "equipment_type": "armor", "rarity": "rare",
        "stats_bonus": {"defense": 8, "speed": -3}, "level_requirement": 6, "value": 300
    },
    "dragon_skin_armor": {
        "id": "dragon_skin_armor", "name": "Dragon Skin Armor", "description": "Next-gen flexible armor. The best money can buy.",
        "equipment_type": "armor", "rarity": "epic",
        "stats_bonus": {"defense": 10, "speed": 1}, "level_requirement": 10, "value": 840
    },
    "steel_toe_boots": {
        "id": "steel_toe_boots", "name": "Steel-Toe Boots", "description": "Kick harder, walk tougher.",
        "equipment_type": "armor", "rarity": "common",
        "stats_bonus": {"defense": 2, "attack": 1}, "level_requirement": 1, "value": 54
    },
    # Accessories
    "night_vision_goggles": {
        "id": "night_vision_goggles", "name": "Night Vision Goggles", "description": "See everything in the dark.",
        "equipment_type": "accessory", "rarity": "rare",
        "stats_bonus": {"luck": 4, "attack": 2}, "level_requirement": 5, "value": 270
    },
    "bulletproof_watch": {
        "id": "bulletproof_watch", "name": "Bulletproof Watch", "description": "Fancy watch that can stop a bullet. Sometimes.",
        "equipment_type": "accessory", "rarity": "uncommon",
        "stats_bonus": {"defense": 2, "luck": 2}, "level_requirement": 2, "value": 106
    },
    "laser_sight": {
        "id": "laser_sight", "name": "Laser Sight", "description": "Pin-point accuracy attachment.",
        "equipment_type": "accessory", "rarity": "uncommon",
        "stats_bonus": {"attack": 3, "luck": 1}, "level_requirement": 3, "value": 120
    },
    "skull_ring": {
        "id": "skull_ring", "name": "Skull Ring", "description": "Intimidating ring. Enemies think twice.",
        "equipment_type": "accessory", "rarity": "epic",
        "stats_bonus": {"attack": 4, "luck": 4, "defense": 2}, "level_requirement": 8, "value": 540
    },
    # Vehicles
    "stolen_motorcycle": {
        "id": "stolen_motorcycle", "name": "Stolen Motorcycle", "description": "Hot ride. Fast getaway guaranteed.",
        "equipment_type": "vehicle", "rarity": "uncommon",
        "stats_bonus": {"speed": 6}, "level_requirement": 3, "value": 166
    },
    "armored_suv": {
        "id": "armored_suv", "name": "Armored SUV", "description": "Bulletproof ride with all the extras.",
        "equipment_type": "vehicle", "rarity": "rare",
        "stats_bonus": {"speed": 4, "defense": 4}, "level_requirement": 6, "value": 390
    },
    "sports_car": {
        "id": "sports_car", "name": "Stolen Lambo", "description": "0 to 60 in 2.9 seconds. Don't ask where it came from.",
        "equipment_type": "vehicle", "rarity": "epic",
        "stats_bonus": {"speed": 10, "luck": 2}, "level_requirement": 10, "value": 900
    },
}

ALL_ITEMS.update(GUN_SHOP_ITEMS)

# ============== 100 LEVEL-BASED WEAPONS ==============
# Each weapon unlocks at its corresponding level (level 1-100)
LEVEL_WEAPONS = {
    # Level 1-10: Street Weapons
    "broken_bottle": {"id": "broken_bottle", "name": "Broken Bottle", "description": "Shattered glass. Desperate but effective.", "equipment_type": "weapon", "rarity": "common", "stats_bonus": {"attack": 3}, "level_requirement": 1, "value": 15},
    "lead_pipe": {"id": "lead_pipe", "name": "Lead Pipe", "description": "Heavy plumbing. Cracks skulls.", "equipment_type": "weapon", "rarity": "common", "stats_bonus": {"attack": 5}, "level_requirement": 2, "value": 25},
    "pocket_knife": {"id": "pocket_knife", "name": "Pocket Knife", "description": "Small but sharp. Always handy.", "equipment_type": "weapon", "rarity": "common", "stats_bonus": {"attack": 6, "speed": 1}, "level_requirement": 3, "value": 35},
    "crowbar": {"id": "crowbar", "name": "Crowbar", "description": "Versatile tool of destruction.", "equipment_type": "weapon", "rarity": "common", "stats_bonus": {"attack": 8}, "level_requirement": 4, "value": 45},
    "tire_iron": {"id": "tire_iron", "name": "Tire Iron", "description": "Roadside weapon. Solid swing.", "equipment_type": "weapon", "rarity": "uncommon", "stats_bonus": {"attack": 10}, "level_requirement": 5, "value": 60},
    "machete": {"id": "machete", "name": "Machete", "description": "Jungle blade. Cuts through anything.", "equipment_type": "weapon", "rarity": "uncommon", "stats_bonus": {"attack": 12, "speed": -1}, "level_requirement": 6, "value": 75},
    "police_baton": {"id": "police_baton", "name": "Police Baton", "description": "Confiscated from a dirty cop.", "equipment_type": "weapon", "rarity": "uncommon", "stats_bonus": {"attack": 13, "defense": 2}, "level_requirement": 7, "value": 85},
    "steel_chain": {"id": "steel_chain", "name": "Steel Chain", "description": "Heavy links. Wrap and swing.", "equipment_type": "weapon", "rarity": "uncommon", "stats_bonus": {"attack": 14, "speed": 2}, "level_requirement": 8, "value": 95},
    "combat_knife": {"id": "combat_knife", "name": "Combat Knife", "description": "Military-grade blade. Silent killer.", "equipment_type": "weapon", "rarity": "rare", "stats_bonus": {"attack": 16, "speed": 3}, "level_requirement": 9, "value": 120},
    "saturday_special": {"id": "saturday_special", "name": "Saturday Night Special", "description": "Cheap revolver. Gets the job done.", "equipment_type": "weapon", "rarity": "rare", "stats_bonus": {"attack": 18}, "level_requirement": 10, "value": 140},
    
    # Level 11-20: Street Upgraded
    "sawed_off_shotgun": {"id": "sawed_off_shotgun", "name": "Sawed-Off Shotgun", "description": "Cut down for close quarters.", "equipment_type": "weapon", "rarity": "rare", "stats_bonus": {"attack": 20, "speed": -2}, "level_requirement": 11, "value": 160},
    "colt_1911": {"id": "colt_1911", "name": "Colt 1911", "description": "Classic American steel. .45 ACP power.", "equipment_type": "weapon", "rarity": "rare", "stats_bonus": {"attack": 22, "luck": 2}, "level_requirement": 12, "value": 180},
    "butterfly_knife": {"id": "butterfly_knife", "name": "Butterfly Knife", "description": "Flashy blade work. Style points.", "equipment_type": "weapon", "rarity": "rare", "stats_bonus": {"attack": 21, "speed": 5}, "level_requirement": 13, "value": 195},
    "tec_9": {"id": "tec_9", "name": "TEC-9", "description": "Street sweeper. High capacity.", "equipment_type": "weapon", "rarity": "rare", "stats_bonus": {"attack": 24, "speed": 1}, "level_requirement": 14, "value": 210},
    "magnum_357": {"id": "magnum_357", "name": ".357 Magnum", "description": "Dirty Harry's choice. Massive stopping power.", "equipment_type": "weapon", "rarity": "rare", "stats_bonus": {"attack": 26}, "level_requirement": 15, "value": 230},
    "pump_shotgun": {"id": "pump_shotgun", "name": "Pump Shotgun", "description": "12 gauge devastation. Rack and roll.", "equipment_type": "weapon", "rarity": "rare", "stats_bonus": {"attack": 28, "speed": -3}, "level_requirement": 16, "value": 250},
    "mac_10": {"id": "mac_10", "name": "MAC-10", "description": "Compact SMG. Spray the block.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 27, "speed": 4}, "level_requirement": 17, "value": 280},
    "beretta_92": {"id": "beretta_92", "name": "Beretta 92", "description": "Italian precision. 15 rounds of accuracy.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 29, "speed": 2, "luck": 1}, "level_requirement": 18, "value": 300},
    "katana": {"id": "katana", "name": "Katana", "description": "Japanese steel. Slice through enemies.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 31, "speed": 3}, "level_requirement": 19, "value": 330},
    "mp5_navy": {"id": "mp5_navy", "name": "MP5 Navy", "description": "SEAL-approved SMG. Suppressed death.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 32, "speed": 3, "defense": 2}, "level_requirement": 20, "value": 360},
    
    # Level 21-30: Professional Grade
    "ak47": {"id": "ak47", "name": "AK-47", "description": "Russian reliability. Never jams.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 35, "speed": -1}, "level_requirement": 21, "value": 400},
    "m4a1": {"id": "m4a1", "name": "M4A1 Carbine", "description": "US military standard. Versatile and deadly.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 36, "speed": 2}, "level_requirement": 22, "value": 430},
    "sig_sauer": {"id": "sig_sauer", "name": "SIG Sauer P226", "description": "Navy SEAL sidearm. Elite precision.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 34, "speed": 4, "luck": 3}, "level_requirement": 23, "value": 450},
    "combat_axe": {"id": "combat_axe", "name": "Combat Axe", "description": "Viking warrior tool. Brutal cleaves.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 38, "defense": 3}, "level_requirement": 24, "value": 480},
    "p90": {"id": "p90", "name": "P90", "description": "Belgian bullet hose. 50 rounds of fury.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 37, "speed": 5}, "level_requirement": 25, "value": 510},
    "auto_shotgun": {"id": "auto_shotgun", "name": "Auto Shotgun", "description": "Semi-automatic devastation. Room clearer.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 40, "speed": -2}, "level_requirement": 26, "value": 550},
    "g36c": {"id": "g36c", "name": "G36C", "description": "German engineering. Compact assault rifle.", "equipment_type": "weapon", "rarity": "epic", "stats_bonus": {"attack": 41, "speed": 3}, "level_requirement": 27, "value": 580},
    "vector_smg": {"id": "vector_smg", "name": "KRISS Vector", "description": "Super V recoil system. Laser accurate.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 42, "speed": 6}, "level_requirement": 28, "value": 620},
    "aug_a3": {"id": "aug_a3", "name": "AUG A3", "description": "Austrian bullpup. Futuristic firepower.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 44, "speed": 2, "luck": 2}, "level_requirement": 29, "value": 660},
    "scar_h": {"id": "scar_h", "name": "SCAR-H", "description": "Special ops favorite. 7.62 NATO power.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 46, "speed": 1, "defense": 3}, "level_requirement": 30, "value": 700},
    
    # Level 31-40: Elite Weapons
    "aa12": {"id": "aa12", "name": "AA-12", "description": "Full auto shotgun. Absolute chaos.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 48, "speed": -1}, "level_requirement": 31, "value": 750},
    "famas": {"id": "famas", "name": "FAMAS", "description": "French bullpup. Burst fire excellence.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 49, "speed": 4}, "level_requirement": 32, "value": 790},
    "fn_scar": {"id": "fn_scar", "name": "FN SCAR-L", "description": "Light and lethal. Operator's choice.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 50, "speed": 5, "luck": 3}, "level_requirement": 33, "value": 830},
    "double_barrel": {"id": "double_barrel", "name": "Double Barrel Shotgun", "description": "Two shells of pure devastation.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 54, "speed": -4}, "level_requirement": 34, "value": 870},
    "ump45": {"id": "ump45", "name": "UMP45", "description": ".45 ACP SMG. Subsonic silencer ready.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 51, "speed": 6}, "level_requirement": 35, "value": 910},
    "dragunov": {"id": "dragunov", "name": "Dragunov SVD", "description": "Russian sniper. Long range death.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 56, "luck": 5}, "level_requirement": 36, "value": 960},
    "galil": {"id": "galil", "name": "Galil ACE", "description": "Israeli assault rifle. Desert proven.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 55, "speed": 3, "defense": 4}, "level_requirement": 37, "value": 1000},
    "m249": {"id": "m249", "name": "M249 SAW", "description": "Belt-fed suppression. 200 rounds.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 58, "defense": 5}, "level_requirement": 38, "value": 1050},
    "mp7": {"id": "mp7", "name": "MP7", "description": "Armor piercing PDW. Compact killer.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 54, "speed": 8}, "level_requirement": 39, "value": 1100},
    "hk416": {"id": "hk416", "name": "HK416", "description": "DEVGRU standard. Bin Laden killer.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 60, "speed": 4, "luck": 4}, "level_requirement": 40, "value": 1150},
    
    # Level 41-50: Military Spec
    "m14_ebr": {"id": "m14_ebr", "name": "M14 EBR", "description": "Enhanced battle rifle. Semi-auto precision.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 62, "luck": 6}, "level_requirement": 41, "value": 1200},
    "tavor": {"id": "tavor", "name": "Tavor TAR-21", "description": "Israeli bullpup. Urban warfare king.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 63, "speed": 5}, "level_requirement": 42, "value": 1260},
    "mk18": {"id": "mk18", "name": "MK18 CQBR", "description": "Close quarters battle receiver. Compact AR.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 64, "speed": 6, "defense": 4}, "level_requirement": 43, "value": 1320},
    "r700": {"id": "r700", "name": "Remington 700", "description": "Bolt action precision. One shot glory.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 70, "luck": 8}, "level_requirement": 44, "value": 1380},
    "pkm": {"id": "pkm", "name": "PKM", "description": "Russian machine gun. Sustained firepower.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 68, "defense": 6}, "level_requirement": 45, "value": 1450},
    "awp": {"id": "awp", "name": "AWP", "description": "Arctic Warfare Police. Legendary sniper.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 75, "luck": 10}, "level_requirement": 46, "value": 1520},
    "acr": {"id": "acr", "name": "ACR", "description": "Adaptive Combat Rifle. No recoil king.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 70, "speed": 7}, "level_requirement": 47, "value": 1600},
    "m60": {"id": "m60", "name": "M60", "description": "The Pig. Vietnam-era machine gun.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 72, "defense": 8}, "level_requirement": 48, "value": 1680},
    "rpk": {"id": "rpk", "name": "RPK", "description": "Russian LMG. AK with a drum.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 71, "speed": 2, "defense": 7}, "level_requirement": 49, "value": 1760},
    "mk14": {"id": "mk14", "name": "MK14 EBR-RI", "description": "Enhanced battle rifle. Semi-auto beast.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 76, "speed": 4, "luck": 6}, "level_requirement": 50, "value": 1850},
    
    # Level 51-60: Advanced Military
    "mg42": {"id": "mg42", "name": "MG42", "description": "Hitler's Buzzsaw. 1200 RPM.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 78, "defense": 9}, "level_requirement": 51, "value": 1950},
    "barrett_m82": {"id": "barrett_m82", "name": "Barrett M82", "description": ".50 BMG anti-material. Vehicle killer.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 85, "luck": 12}, "level_requirement": 52, "value": 2050},
    "fn_minimi": {"id": "fn_minimi", "name": "FN Minimi", "description": "Belgian LMG. NATO standard.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 80, "defense": 10}, "level_requirement": 53, "value": 2150},
    "groza": {"id": "groza", "name": "OTs-14 Groza", "description": "Russian bullpup. Spetsnaz special.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 81, "speed": 6, "luck": 5}, "level_requirement": 54, "value": 2260},
    "vssk": {"id": "vssk", "name": "VSSK Vykhlop", "description": "Russian silenced sniper. Ghost rifle.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 84, "speed": 8, "luck": 7}, "level_requirement": 55, "value": 2370},
    "negev": {"id": "negev", "name": "IWI Negev", "description": "Israeli LMG. Desert storm proven.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 83, "defense": 11}, "level_requirement": 56, "value": 2480},
    "m110": {"id": "m110", "name": "M110 SASS", "description": "Semi-auto sniper system. Precision.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 86, "luck": 14}, "level_requirement": 57, "value": 2600},
    "as_val": {"id": "as_val", "name": "AS Val", "description": "Russian integrated suppressor. Silent killer.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 82, "speed": 10}, "level_requirement": 58, "value": 2720},
    "qbu_88": {"id": "qbu_88", "name": "QBU-88", "description": "Chinese bullpup DMR. Precision rifle.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 87, "luck": 10, "speed": 4}, "level_requirement": 59, "value": 2850},
    "mg3": {"id": "mg3", "name": "MG3", "description": "German GPMG. 1000 RPM of fury.", "equipment_type": "weapon", "rarity": "legendary", "stats_bonus": {"attack": 88, "defense": 12}, "level_requirement": 60, "value": 2980},
    
    # Level 61-70: Experimental Weapons
    "xm8": {"id": "xm8", "name": "XM8", "description": "Cancelled prototype. Rare find.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 90, "speed": 8, "luck": 8}, "level_requirement": 61, "value": 3120},
    "an94": {"id": "an94", "name": "AN-94", "description": "Russian hyperburst. Two shots one hole.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 92, "speed": 6, "luck": 10}, "level_requirement": 62, "value": 3270},
    "chainsaw": {"id": "chainsaw", "name": "Combat Chainsaw", "description": "Modified for warfare. Brutal.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 95, "defense": 8}, "level_requirement": 63, "value": 3420},
    "minigun": {"id": "minigun", "name": "M134 Minigun", "description": "6000 RPM. Predator approved.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 100, "speed": -10, "defense": 15}, "level_requirement": 64, "value": 3580},
    "railgun_proto": {"id": "railgun_proto", "name": "Railgun Prototype", "description": "Electromagnetic accelerator. Experimental.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 105, "luck": 15}, "level_requirement": 65, "value": 3750},
    "oicw": {"id": "oicw", "name": "XM29 OICW", "description": "Objective Individual Combat Weapon. Future soldier.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 98, "speed": 5, "luck": 12, "defense": 5}, "level_requirement": 66, "value": 3920},
    "cheytac": {"id": "cheytac", "name": "CheyTac M200", "description": "Intervention. 2000+ meter kills.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 110, "luck": 18}, "level_requirement": 67, "value": 4100},
    "corner_shot": {"id": "corner_shot", "name": "CornerShot", "description": "Shoot around corners. Tactical innovation.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 94, "speed": 12, "defense": 10}, "level_requirement": 68, "value": 4280},
    "metal_storm": {"id": "metal_storm", "name": "Metal Storm", "description": "Electronic firing. 1 million RPM capable.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 115, "speed": -5}, "level_requirement": 69, "value": 4470},
    "xm25": {"id": "xm25", "name": "XM25 CDTE", "description": "Airburst grenade launcher. Smart munitions.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 108, "luck": 15, "defense": 8}, "level_requirement": 70, "value": 4660},
    
    # Level 71-80: Black Ops Grade
    "psg1": {"id": "psg1", "name": "PSG1", "description": "German precision sniper. Zero tolerance.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 112, "luck": 20}, "level_requirement": 71, "value": 4860},
    "dsr50": {"id": "dsr50", "name": "DSR-50", "description": ".50 BMG bullpup sniper. Compact destruction.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 118, "luck": 18, "speed": 2}, "level_requirement": 72, "value": 5070},
    "ksg": {"id": "ksg", "name": "Kel-Tec KSG", "description": "Dual tube bullpup shotgun. 14 shells.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 105, "speed": 8, "defense": 12}, "level_requirement": 73, "value": 5280},
    "kriss_super_v": {"id": "kriss_super_v", "name": "KRISS Super V", "description": "Zero recoil system. Perfect accuracy.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 108, "speed": 15}, "level_requirement": 74, "value": 5500},
    "m32_mgl": {"id": "m32_mgl", "name": "M32 MGL", "description": "6-shot grenade launcher. Area denial.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 120, "defense": 10}, "level_requirement": 75, "value": 5720},
    "ots_03": {"id": "ots_03", "name": "OTs-03 SVU", "description": "Bullpup Dragunov. Compact sniper.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 115, "speed": 10, "luck": 15}, "level_requirement": 76, "value": 5950},
    "rpg7": {"id": "rpg7", "name": "RPG-7", "description": "Soviet rocket launcher. Anti-everything.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 130, "speed": -8}, "level_requirement": 77, "value": 6180},
    "at4": {"id": "at4", "name": "AT4", "description": "Disposable anti-tank. One and done.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 135, "luck": 10}, "level_requirement": 78, "value": 6420},
    "carl_gustav": {"id": "carl_gustav", "name": "Carl Gustaf M4", "description": "Recoilless rifle. Swedish steel.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 140, "defense": 12}, "level_requirement": 79, "value": 6660},
    "javelin": {"id": "javelin", "name": "FGM-148 Javelin", "description": "Fire and forget. Tank nightmare.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 145, "luck": 20}, "level_requirement": 80, "value": 6910},
    
    # Level 81-90: Elite Experimental
    "plasma_cutter": {"id": "plasma_cutter", "name": "Plasma Cutter", "description": "Industrial tool weaponized. Melts armor.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 148, "speed": 5, "luck": 15}, "level_requirement": 81, "value": 7160},
    "gauss_rifle": {"id": "gauss_rifle", "name": "Gauss Rifle", "description": "Magnetic acceleration. Hypersonic rounds.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 152, "luck": 22}, "level_requirement": 82, "value": 7420},
    "laser_designator": {"id": "laser_designator", "name": "Laser Designator", "description": "Orbital strike coordinator. Call the thunder.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 155, "luck": 25}, "level_requirement": 83, "value": 7680},
    "pulse_rifle": {"id": "pulse_rifle", "name": "Pulse Rifle", "description": "Energy weapon prototype. Unlimited ammo.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 150, "speed": 12, "defense": 10}, "level_requirement": 84, "value": 7950},
    "sonic_cannon": {"id": "sonic_cannon", "name": "Sonic Cannon", "description": "Sound-based weapon. Internal damage.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 158, "speed": 8}, "level_requirement": 85, "value": 8220},
    "cryo_gun": {"id": "cryo_gun", "name": "Cryo Gun", "description": "Freezing spray. Slow and shatter.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 155, "speed": 15, "luck": 18}, "level_requirement": 86, "value": 8500},
    "microwave_emitter": {"id": "microwave_emitter", "name": "Microwave Emitter", "description": "Active denial weapon. Cooks from inside.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 162, "defense": 15}, "level_requirement": 87, "value": 8780},
    "emp_cannon": {"id": "emp_cannon", "name": "EMP Cannon", "description": "Electromagnetic pulse. Disables everything.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 165, "luck": 20, "speed": 5}, "level_requirement": 88, "value": 9070},
    "fusion_lance": {"id": "fusion_lance", "name": "Fusion Lance", "description": "Focused energy beam. Cuts through steel.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 170, "speed": 10}, "level_requirement": 89, "value": 9360},
    "antimatter_pistol": {"id": "antimatter_pistol", "name": "Antimatter Pistol", "description": "Annihilation rounds. Pure destruction.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 175, "luck": 25}, "level_requirement": 90, "value": 9660},
    
    # Level 91-100: Legendary Arsenal
    "death_ray": {"id": "death_ray", "name": "Death Ray", "description": "Concentrated doom. One shot delete.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 180, "luck": 28}, "level_requirement": 91, "value": 9970},
    "gravity_hammer": {"id": "gravity_hammer", "name": "Gravity Hammer", "description": "Manipulates mass. Crushing blows.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 185, "defense": 20}, "level_requirement": 92, "value": 10280},
    "void_blade": {"id": "void_blade", "name": "Void Blade", "description": "Cuts through dimensions. Reality warper.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 188, "speed": 15, "luck": 20}, "level_requirement": 93, "value": 10600},
    "quantum_rifle": {"id": "quantum_rifle", "name": "Quantum Rifle", "description": "Shoots in multiple realities. Never misses.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 192, "luck": 35}, "level_requirement": 94, "value": 10920},
    "singularity_gun": {"id": "singularity_gun", "name": "Singularity Gun", "description": "Creates micro black holes. Ultimate gravity.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 195, "defense": 18, "luck": 25}, "level_requirement": 95, "value": 11250},
    "nova_cannon": {"id": "nova_cannon", "name": "Nova Cannon", "description": "Stellar explosion in your hands. Supernova.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 200, "speed": -5, "luck": 30}, "level_requirement": 96, "value": 11580},
    "reality_shredder": {"id": "reality_shredder", "name": "Reality Shredder", "description": "Tears the fabric of space. Unstoppable.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 205, "speed": 12, "defense": 15}, "level_requirement": 97, "value": 11920},
    "omega_blade": {"id": "omega_blade", "name": "Omega Blade", "description": "The end of all things. Final strike.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 210, "luck": 40}, "level_requirement": 98, "value": 12260},
    "godslayer": {"id": "godslayer", "name": "Godslayer", "description": "Weapon of legend. Kills anything.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 220, "speed": 15, "luck": 35, "defense": 20}, "level_requirement": 99, "value": 12610},
    "infinity_gauntlet": {"id": "infinity_gauntlet", "name": "Infinity Gauntlet", "description": "Ultimate power. Snap and win.", "equipment_type": "weapon", "rarity": "mythic", "stats_bonus": {"attack": 250, "speed": 20, "luck": 50, "defense": 25}, "level_requirement": 100, "value": 15000},
}

ALL_ITEMS.update(LEVEL_WEAPONS)

# ============== CONSUMABLE SHOP ITEMS ==============
CONSUMABLE_ITEMS = {
    # --- Health Recharges ---
    "health_syringe": {
        "id": "health_syringe", "name": "Health Syringe", "category": "health_recharge",
        "description": "Quick street med. Restores 30 HP.",
        "icon": "medkit", "rarity": "common",
        "effect": {"restore_health": 30}, "price": 50, "level_requirement": 1,
    },
    "med_kit": {
        "id": "med_kit", "name": "Med Kit", "category": "health_recharge",
        "description": "Military first aid. Restores 75 HP.",
        "icon": "medkit", "rarity": "uncommon",
        "effect": {"restore_health": 75}, "price": 100, "level_requirement": 3,
    },
    "full_heal_pack": {
        "id": "full_heal_pack", "name": "Full Heal Pack", "category": "health_recharge",
        "description": "Top-shelf trauma kit. Restores ALL health.",
        "icon": "medkit", "rarity": "rare",
        "effect": {"restore_health_full": True}, "price": 500, "level_requirement": 5,
    },
    # --- Energy Recharges ---
    "energy_drink": {
        "id": "energy_drink", "name": "Energy Drink", "category": "energy_recharge",
        "description": "Cheap caffeine hit. Restores 25 Energy.",
        "icon": "battery-charging", "rarity": "common",
        "effect": {"restore_energy": 25}, "price": 50, "level_requirement": 1,
    },
    "adrenaline_shot": {
        "id": "adrenaline_shot", "name": "Adrenaline Shot", "category": "energy_recharge",
        "description": "Pure adrenaline rush. Restores 60 Energy.",
        "icon": "battery-charging", "rarity": "uncommon",
        "effect": {"restore_energy": 60}, "price": 100, "level_requirement": 3,
    },
    "full_energy_cell": {
        "id": "full_energy_cell", "name": "Full Energy Cell", "category": "energy_recharge",
        "description": "Military-grade stimulant. Restores ALL energy.",
        "icon": "battery-charging", "rarity": "rare",
        "effect": {"restore_energy_full": True}, "price": 500, "level_requirement": 5,
    },
    # --- Combo Packs ---
    "street_rations": {
        "id": "street_rations", "name": "Street Rations", "category": "combo",
        "description": "Food & drink combo. Restores 20 HP and 20 Energy.",
        "icon": "fast-food", "rarity": "common",
        "effect": {"restore_health": 20, "restore_energy": 20}, "price": 100, "level_requirement": 1,
    },
    "combat_stim": {
        "id": "combat_stim", "name": "Combat Stimulant", "category": "combo",
        "description": "Black market stim. Restores 50 HP and 50 Energy.",
        "icon": "fast-food", "rarity": "rare",
        "effect": {"restore_health": 50, "restore_energy": 50}, "price": 200, "level_requirement": 5,
    },
    "full_recovery_kit": {
        "id": "full_recovery_kit", "name": "Full Recovery Kit", "category": "combo",
        "description": "The ultimate package. Fully restores HP and Energy.",
        "icon": "fast-food", "rarity": "epic",
        "effect": {"restore_health_full": True, "restore_energy_full": True}, "price": 1000, "level_requirement": 8,
    },
    # --- Consumables: Temporary Health Boost (adds to current HP, caps at 2x max) ---
    "heart_implant_mk1": {
        "id": "heart_implant_mk1", "name": "Health Stim Mk1", "category": "consumable",
        "description": "Combat stimulant. Instantly adds +25% of max HP to current health.",
        "icon": "heart", "rarity": "rare",
        "effect": {"temp_health_percent": 0.25}, "price": 200, "level_requirement": 5,
    },
    "heart_implant_mk2": {
        "id": "heart_implant_mk2", "name": "Health Stim Mk2", "category": "consumable",
        "description": "Advanced stimulant. Instantly adds +50% of max HP to current health.",
        "icon": "heart", "rarity": "epic",
        "effect": {"temp_health_percent": 0.50}, "price": 500, "level_requirement": 8,
    },
    "heart_implant_mk3": {
        "id": "heart_implant_mk3", "name": "Health Stim Mk3", "category": "consumable",
        "description": "Legendary stim. Instantly adds +100% of max HP to current health.",
        "icon": "heart", "rarity": "legendary",
        "effect": {"temp_health_percent": 1.0}, "price": 1000, "level_requirement": 12,
    },
    # --- Consumables: Temporary Energy Boost (adds to current Energy, caps at 2x max) ---
    "neural_booster_mk1": {
        "id": "neural_booster_mk1", "name": "Energy Stim Mk1", "category": "consumable",
        "description": "Neural stimulant. Instantly adds +25% of max Energy to current energy.",
        "icon": "flash", "rarity": "rare",
        "effect": {"temp_energy_percent": 0.25}, "price": 200, "level_requirement": 5,
    },
    "neural_booster_mk2": {
        "id": "neural_booster_mk2", "name": "Energy Stim Mk2", "category": "consumable",
        "description": "Advanced neural boost. Instantly adds +50% of max Energy to current energy.",
        "icon": "flash", "rarity": "epic",
        "effect": {"temp_energy_percent": 0.50}, "price": 500, "level_requirement": 8,
    },
    "neural_booster_mk3": {
        "id": "neural_booster_mk3", "name": "Energy Stim Mk3", "category": "consumable",
        "description": "Legendary neuro-stim. Instantly adds +100% of max Energy to current energy.",
        "icon": "flash", "rarity": "legendary",
        "effect": {"temp_energy_percent": 1.0}, "price": 1000, "level_requirement": 12,
    },
}

# Shop name templates
SHOP_NAMES = [
    "Underground Arms", "Vinnie's Gun Shop", "The Arsenal", "Black Market Armory",
    "Shadow Dealer", "Bullet Brothers", "Iron Fist Supplies", "Street Surplus",
    "Midnight Arms", "The Pawn & Gun", "Tactical Outfitters", "Back Alley Deals",
    "Don's Weapons Cache", "Neon Arms", "Eastside Arms Dealer", "The Gun Runner",
]

SHOP_TYPES = {
    "gun_shop": {"name_suffix": "", "focus": ["weapon"], "icon": "pistol"},
    "armor_shop": {"name_suffix": "", "focus": ["armor", "accessory"], "icon": "shield"},
    "general_shop": {"name_suffix": "", "focus": ["weapon", "armor", "accessory", "vehicle"], "icon": "storefront"},
}

ENEMY_TIERS = [
    # Tier 1 (Levels 1-10, Boss at 11)
    {"tier": 1, "name": "Thug", "level_min": 1, "level_max": 2, "is_boss": False},
    {"tier": 1, "name": "Gangster", "level_min": 3, "level_max": 4, "is_boss": False},
    {"tier": 1, "name": "Criminal", "level_min": 5, "level_max": 6, "is_boss": False},
    {"tier": 1, "name": "Villain", "level_min": 7, "level_max": 8, "is_boss": False},
    {"tier": 1, "name": "Bandit", "level_min": 9, "level_max": 10, "is_boss": False},
    {"tier": 1, "name": "The Kingpin", "level_min": 8, "level_max": 10, "is_boss": True},
    # Tier 2 (Levels 11-20)
    {"tier": 2, "name": "Assassin", "level_min": 11, "level_max": 12, "is_boss": False},
    {"tier": 2, "name": "Thief", "level_min": 13, "level_max": 14, "is_boss": False},
    {"tier": 2, "name": "Hoodlum", "level_min": 15, "level_max": 16, "is_boss": False},
    {"tier": 2, "name": "Pirate", "level_min": 17, "level_max": 18, "is_boss": False},
    {"tier": 2, "name": "Bully", "level_min": 19, "level_max": 20, "is_boss": False},
    {"tier": 2, "name": "Vinnie The Viper", "level_min": 18, "level_max": 20, "is_boss": True},
    # Tier 3 (Levels 21-30)
    {"tier": 3, "name": "Offender", "level_min": 21, "level_max": 22, "is_boss": False},
    {"tier": 3, "name": "Hood", "level_min": 23, "level_max": 24, "is_boss": False},
    {"tier": 3, "name": "Mobster", "level_min": 25, "level_max": 26, "is_boss": False},
    {"tier": 3, "name": "Gangsta", "level_min": 27, "level_max": 28, "is_boss": False},
    {"tier": 3, "name": "Hooligan", "level_min": 29, "level_max": 30, "is_boss": False},
    {"tier": 3, "name": "Don Corleone", "level_min": 28, "level_max": 30, "is_boss": True},
    # Tier 4 (Levels 31-40)
    {"tier": 4, "name": "Goon", "level_min": 31, "level_max": 32, "is_boss": False},
    {"tier": 4, "name": "Ruffian", "level_min": 33, "level_max": 34, "is_boss": False},
    {"tier": 4, "name": "Gang Banger", "level_min": 35, "level_max": 36, "is_boss": False},
    {"tier": 4, "name": "Tough Guy", "level_min": 37, "level_max": 38, "is_boss": False},
    {"tier": 4, "name": "Gorilla", "level_min": 39, "level_max": 40, "is_boss": False},
    {"tier": 4, "name": "El Chapo", "level_min": 38, "level_max": 40, "is_boss": True},
    # Tier 5 (Levels 41-50)
    {"tier": 5, "name": "Punk", "level_min": 41, "level_max": 42, "is_boss": False},
    {"tier": 5, "name": "Rough Neck", "level_min": 43, "level_max": 44, "is_boss": False},
    {"tier": 5, "name": "Rowdy Person", "level_min": 45, "level_max": 46, "is_boss": False},
    {"tier": 5, "name": "Yardie", "level_min": 47, "level_max": 48, "is_boss": False},
    {"tier": 5, "name": "Perpetrator", "level_min": 49, "level_max": 50, "is_boss": False},
    {"tier": 5, "name": "Tony Montana", "level_min": 48, "level_max": 50, "is_boss": True},
    # Tier 6 (Levels 51-60)
    {"tier": 6, "name": "Vigilante", "level_min": 51, "level_max": 52, "is_boss": False},
    {"tier": 6, "name": "Scoundrel", "level_min": 53, "level_max": 54, "is_boss": False},
    {"tier": 6, "name": "Robber", "level_min": 55, "level_max": 56, "is_boss": False},
    {"tier": 6, "name": "Toughie", "level_min": 57, "level_max": 58, "is_boss": False},
    {"tier": 6, "name": "Felon", "level_min": 59, "level_max": 60, "is_boss": False},
    {"tier": 6, "name": "Pablo Escobar", "level_min": 58, "level_max": 60, "is_boss": True},
    # Tier 7 (Levels 61-70)
    {"tier": 7, "name": "Outlaw", "level_min": 61, "level_max": 62, "is_boss": False},
    {"tier": 7, "name": "Crook", "level_min": 63, "level_max": 64, "is_boss": False},
    {"tier": 7, "name": "Cutthroat", "level_min": 65, "level_max": 66, "is_boss": False},
    {"tier": 7, "name": "Brigade", "level_min": 67, "level_max": 68, "is_boss": False},
    {"tier": 7, "name": "Mafioso", "level_min": 69, "level_max": 70, "is_boss": False},
    {"tier": 7, "name": "The Joker", "level_min": 68, "level_max": 70, "is_boss": True},
    # Tier 8 (Levels 71-80)
    {"tier": 8, "name": "Perp", "level_min": 71, "level_max": 72, "is_boss": False},
    {"tier": 8, "name": "Mugger", "level_min": 73, "level_max": 74, "is_boss": False},
    {"tier": 8, "name": "LawBreaker", "level_min": 75, "level_max": 76, "is_boss": False},
    {"tier": 8, "name": "Racketeer", "level_min": 77, "level_max": 78, "is_boss": False},
    {"tier": 8, "name": "Desperado", "level_min": 79, "level_max": 80, "is_boss": False},
    {"tier": 8, "name": "Bane", "level_min": 78, "level_max": 80, "is_boss": True},
    # Tier 9 (Levels 81-90)
    {"tier": 9, "name": "Highway Man", "level_min": 81, "level_max": 82, "is_boss": False},
    {"tier": 9, "name": "Gunman", "level_min": 83, "level_max": 84, "is_boss": False},
    {"tier": 9, "name": "Vandal", "level_min": 85, "level_max": 86, "is_boss": False},
    {"tier": 9, "name": "Pick Pocket", "level_min": 87, "level_max": 88, "is_boss": False},
    {"tier": 9, "name": "Swindler", "level_min": 89, "level_max": 90, "is_boss": False},
    {"tier": 9, "name": "Thanos", "level_min": 88, "level_max": 90, "is_boss": True},
    # Tier 10 (Levels 91-100)
    {"tier": 10, "name": "Malefactor", "level_min": 91, "level_max": 92, "is_boss": False},
    {"tier": 10, "name": "Bravo", "level_min": 93, "level_max": 94, "is_boss": False},
    {"tier": 10, "name": "Delinquent", "level_min": 95, "level_max": 96, "is_boss": False},
    {"tier": 10, "name": "Maniac", "level_min": 97, "level_max": 98, "is_boss": False},
    {"tier": 10, "name": "Psycho", "level_min": 99, "level_max": 100, "is_boss": False},
    {"tier": 10, "name": "The Godfather", "level_min": 98, "level_max": 100, "is_boss": True},
]

def get_player_tier(player_level: int) -> int:
    """Get the player's current tier (1-10) based on level"""
    return min(10, max(1, (player_level - 1) // 10 + 1))

def get_eligible_enemies(player_level: int):
    """Get enemies at player's level and up to 1 level higher.
    Lower level enemies spawn MORE frequently than higher level ones.
    Bosses spawn from player's current tier and lower tiers."""
    current_tier = get_player_tier(player_level)
    
    # Include enemies whose level_min is at or below player_level + 1
    # This allows enemies at player level and 1 level higher for challenge
    max_spawn_level = player_level + 1
    eligible = [e for e in ENEMY_TIERS if e["level_min"] <= max_spawn_level]
    
    # Weight system: lower tiers get much higher spawn rates
    # Tier 1 = highest weight, each tier above = less common
    weighted = []
    for e in eligible:
        if e["is_boss"]:
            # Bosses spawn from current tier and all lower tiers
            # Boss must be from player's tier or below and player must be at/above boss level
            if e["tier"] <= current_tier and player_level >= e["level_min"]:
                # Bosses have weight 5 - makes them more common than before but still rarer than regular enemies
                weighted.append((e, 5))
        else:
            # Only include regular enemies if player can actually fight them at appropriate level
            # Skip enemies whose level_min would be higher than what player should face
            if e["level_min"] <= player_level + 1:
                # Lower tier enemies spawn more often
                # Tier 1 = weight 10, Tier 2 = weight 9, Tier 3 = weight 8... T10=1
                tier_weight = max(1, 11 - e["tier"])
                
                # Boost even more for much lower tiers (they're the common street thugs)
                tier_diff = current_tier - e["tier"]
                if tier_diff >= 3:
                    tier_weight += 3  # Extra common for enemies 3+ tiers below
                elif tier_diff >= 1:
                    tier_weight += 1  # Slightly boosted for lower tiers
                
                weighted.append((e, tier_weight))
    
    if not weighted:
        # Fallback to first tier (only the lowest level enemy)
        weighted = [(ENEMY_TIERS[0], 10)]
    
    return weighted

def calculate_enemy_stats(enemy_level: int, is_boss: bool) -> dict:
    """Calculate enemy stats based on level and boss status"""
    # Base stats scale with level, bosses get a smaller multiplier (easier)
    boss_mult = 1.3 if is_boss else 1.0
    health = int((80 + enemy_level * 18) * boss_mult)
    attack = int((8 + enemy_level * 3.2) * boss_mult)
    defense = int((5 + enemy_level * 1.8) * boss_mult)
    return {"health": health, "max_health": health, "attack": attack, "defense": defense}

SKILLS = {
    # Level 1 - Starter skills (players start with these 2)
    "heavy_strike": {"name": "Heavy Strike", "damage_mult": 1.5, "cost": 10, "unlock_level": 1, "value": 0, "description": "A powerful melee attack dealing 1.5x damage."},
    "quick_shot": {"name": "Quick Shot", "damage_mult": 1.2, "cost": 5, "unlock_level": 1, "value": 0, "description": "A fast ranged attack dealing 1.2x damage."},
    
    # Level 3
    "defensive_stance": {"name": "Defensive Stance", "defense_buff": 2.0, "cost": 8, "unlock_level": 3, "value": 100, "description": "Double your defense for this turn."},
    
    # Level 5
    "critical_aim": {"name": "Critical Aim", "crit_chance": 0.5, "cost": 15, "unlock_level": 5, "value": 150, "description": "50% chance of guaranteed critical hit."},
    
    # Level 7
    "heal": {"name": "Street Medicine", "heal_percent": 0.3, "cost": 20, "unlock_level": 7, "value": 200, "description": "Heal 30% of your max health."},
    
    # Level 9
    "rage": {"name": "Rage Mode", "damage_mult": 2.0, "cost": 25, "unlock_level": 9, "value": 250, "description": "Unleash fury for 2x damage."},
    
    # Level 11
    "counter_strike": {"name": "Counter Strike", "damage_mult": 1.8, "defense_buff": 1.5, "cost": 18, "unlock_level": 11, "value": 350, "description": "Attack while boosting defense."},
    
    # Level 13
    "blinding_flash": {"name": "Blinding Flash", "stun_chance": 0.4, "damage_mult": 1.3, "cost": 20, "unlock_level": 13, "value": 400, "description": "40% chance to stun enemy, 1.3x damage."},
    
    # Level 15
    "execute": {"name": "Execute", "damage_mult": 3.0, "cost": 40, "unlock_level": 15, "value": 500, "description": "Devastating finisher dealing 3x damage."},
    
    # Level 17
    "iron_skin": {"name": "Iron Skin", "defense_buff": 3.0, "cost": 22, "unlock_level": 17, "value": 550, "description": "Triple your defense temporarily."},
    
    # Level 19
    "adrenaline_rush": {"name": "Adrenaline Rush", "damage_mult": 1.6, "heal_percent": 0.15, "cost": 28, "unlock_level": 19, "value": 600, "description": "Attack for 1.6x and heal 15%."},
    
    # Level 21
    "double_tap": {"name": "Double Tap", "damage_mult": 2.2, "cost": 30, "unlock_level": 21, "value": 700, "description": "Two quick shots for 2.2x total damage."},
    
    # Level 23
    "smoke_bomb": {"name": "Smoke Bomb", "defense_buff": 2.5, "heal_percent": 0.1, "cost": 25, "unlock_level": 23, "value": 750, "description": "Create cover, boost defense 2.5x and heal 10%."},
    
    # Level 25
    "berserker": {"name": "Berserker", "damage_mult": 2.5, "cost": 35, "unlock_level": 25, "value": 850, "description": "Wild attack dealing 2.5x damage."},
    
    # Level 27
    "tactical_reload": {"name": "Tactical Reload", "heal_percent": 0.25, "cost": 18, "unlock_level": 27, "value": 900, "description": "Quick recovery healing 25% HP."},
    
    # Level 29
    "armor_pierce": {"name": "Armor Pierce", "damage_mult": 2.0, "ignore_defense": True, "cost": 32, "unlock_level": 29, "value": 1000, "description": "Attack that ignores enemy defense."},
    
    # Level 31
    "venomous_strike": {"name": "Venomous Strike", "damage_mult": 1.5, "poison": 0.1, "cost": 28, "unlock_level": 31, "value": 1100, "description": "Poison attack, deals damage over time."},
    
    # Level 33
    "battle_cry": {"name": "Battle Cry", "damage_mult": 1.8, "defense_buff": 1.3, "cost": 30, "unlock_level": 33, "value": 1200, "description": "Boost morale: 1.8x damage + defense."},
    
    # Level 35
    "headshot": {"name": "Headshot", "damage_mult": 3.5, "crit_chance": 0.3, "cost": 45, "unlock_level": 35, "value": 1400, "description": "Precision shot for 3.5x damage."},
    
    # Level 37
    "fortress": {"name": "Fortress", "defense_buff": 4.0, "cost": 35, "unlock_level": 37, "value": 1500, "description": "Quadruple your defense."},
    
    # Level 39
    "lifesteal": {"name": "Lifesteal", "damage_mult": 1.8, "lifesteal": 0.3, "cost": 38, "unlock_level": 39, "value": 1650, "description": "Drain 30% of damage dealt as health."},
    
    # Level 41
    "chain_attack": {"name": "Chain Attack", "damage_mult": 2.8, "cost": 42, "unlock_level": 41, "value": 1800, "description": "Multiple hits dealing 2.8x total."},
    
    # Level 43
    "medic": {"name": "Combat Medic", "heal_percent": 0.4, "cost": 30, "unlock_level": 43, "value": 1900, "description": "Advanced healing for 40% HP."},
    
    # Level 45
    "rampage": {"name": "Rampage", "damage_mult": 3.0, "cost": 50, "unlock_level": 45, "value": 2100, "description": "Unstoppable assault for 3x damage."},
    
    # Level 47
    "evasion": {"name": "Evasion", "defense_buff": 5.0, "cost": 40, "unlock_level": 47, "value": 2250, "description": "5x defense through expert dodging."},
    
    # Level 49
    "assassinate": {"name": "Assassinate", "damage_mult": 4.0, "cost": 55, "unlock_level": 49, "value": 2500, "description": "Silent killer dealing 4x damage."},
    
    # Level 51
    "blood_pact": {"name": "Blood Pact", "damage_mult": 2.5, "lifesteal": 0.4, "cost": 48, "unlock_level": 51, "value": 2700, "description": "2.5x damage, steal 40% as HP."},
    
    # Level 53
    "titanium_shell": {"name": "Titanium Shell", "defense_buff": 6.0, "heal_percent": 0.1, "cost": 45, "unlock_level": 53, "value": 2900, "description": "6x defense + 10% heal."},
    
    # Level 55
    "obliterate": {"name": "Obliterate", "damage_mult": 4.5, "cost": 60, "unlock_level": 55, "value": 3200, "description": "Devastating blow for 4.5x damage."},
    
    # Level 57
    "regenerate": {"name": "Regenerate", "heal_percent": 0.5, "cost": 40, "unlock_level": 57, "value": 3400, "description": "Powerful healing for 50% HP."},
    
    # Level 59
    "phantom_strike": {"name": "Phantom Strike", "damage_mult": 3.5, "ignore_defense": True, "cost": 55, "unlock_level": 59, "value": 3700, "description": "Ghostly attack ignores all defense."},
    
    # Level 61
    "war_machine": {"name": "War Machine", "damage_mult": 3.0, "defense_buff": 2.0, "cost": 52, "unlock_level": 61, "value": 4000, "description": "3x damage + 2x defense."},
    
    # Level 63
    "drain_life": {"name": "Drain Life", "damage_mult": 2.0, "lifesteal": 0.5, "cost": 50, "unlock_level": 63, "value": 4300, "description": "2x damage, drain 50% as HP."},
    
    # Level 65
    "massacre": {"name": "Massacre", "damage_mult": 5.0, "cost": 70, "unlock_level": 65, "value": 4700, "description": "Brutal assault for 5x damage."},
    
    # Level 67
    "diamond_armor": {"name": "Diamond Armor", "defense_buff": 8.0, "cost": 55, "unlock_level": 67, "value": 5000, "description": "8x defense, nearly invincible."},
    
    # Level 69
    "phoenix_heal": {"name": "Phoenix Heal", "heal_percent": 0.6, "cost": 50, "unlock_level": 69, "value": 5400, "description": "Rise again with 60% HP restored."},
    
    # Level 71
    "annihilate": {"name": "Annihilate", "damage_mult": 5.5, "cost": 75, "unlock_level": 71, "value": 5800, "description": "Destructive force for 5.5x damage."},
    
    # Level 73
    "vampire": {"name": "Vampire", "damage_mult": 3.0, "lifesteal": 0.6, "cost": 60, "unlock_level": 73, "value": 6200, "description": "3x damage, steal 60% as HP."},
    
    # Level 75
    "juggernaut": {"name": "Juggernaut", "damage_mult": 4.0, "defense_buff": 3.0, "cost": 65, "unlock_level": 75, "value": 6700, "description": "Unstoppable: 4x damage + 3x defense."},
    
    # Level 77
    "omega_heal": {"name": "Omega Heal", "heal_percent": 0.7, "defense_buff": 2.0, "cost": 55, "unlock_level": 77, "value": 7200, "description": "Ultimate heal: 70% HP + 2x defense."},
    
    # Level 79
    "death_blow": {"name": "Death Blow", "damage_mult": 6.0, "cost": 80, "unlock_level": 79, "value": 7800, "description": "Fatal strike dealing 6x damage."},
    
    # Level 81
    "eternal_guard": {"name": "Eternal Guard", "defense_buff": 10.0, "cost": 65, "unlock_level": 81, "value": 8400, "description": "Legendary 10x defense boost."},
    
    # Level 83
    "soul_reaper": {"name": "Soul Reaper", "damage_mult": 5.0, "lifesteal": 0.7, "cost": 75, "unlock_level": 83, "value": 9100, "description": "5x damage, drain 70% as HP."},
    
    # Level 85
    "armageddon": {"name": "Armageddon", "damage_mult": 7.0, "cost": 90, "unlock_level": 85, "value": 9800, "description": "Apocalyptic power for 7x damage."},
    
    # Level 87
    "immortal": {"name": "Immortal", "heal_percent": 0.8, "defense_buff": 5.0, "cost": 70, "unlock_level": 87, "value": 10600, "description": "God mode: 80% heal + 5x defense."},
    
    # Level 89
    "extinction": {"name": "Extinction", "damage_mult": 8.0, "ignore_defense": True, "cost": 100, "unlock_level": 89, "value": 11500, "description": "8x damage that ignores all defense."},
    
    # Level 91
    "divine_shield": {"name": "Divine Shield", "defense_buff": 15.0, "heal_percent": 0.3, "cost": 80, "unlock_level": 91, "value": 12500, "description": "Godlike 15x defense + 30% heal."},
    
    # Level 93
    "apocalypse": {"name": "Apocalypse", "damage_mult": 9.0, "cost": 110, "unlock_level": 93, "value": 13600, "description": "End times: 9x damage devastation."},
    
    # Level 95
    "titan_soul": {"name": "Titan Soul", "damage_mult": 7.0, "defense_buff": 5.0, "lifesteal": 0.5, "cost": 100, "unlock_level": 95, "value": 14800, "description": "Titan power: 7x dmg, 5x def, 50% steal."},
    
    # Level 97
    "rebirth": {"name": "Rebirth", "heal_percent": 1.0, "cost": 90, "unlock_level": 97, "value": 16000, "description": "Full health restoration."},
    
    # Level 99
    "godslayer": {"name": "Godslayer", "damage_mult": 10.0, "ignore_defense": True, "lifesteal": 0.5, "cost": 120, "unlock_level": 99, "value": 18000, "description": "Ultimate skill: 10x dmg, ignore def, 50% steal."},
}

# ============== TERRITORY SYSTEM ==============
# Generate 1000+ unique territory names from combinations
_TERR_PREFIXES = [
    "North", "South", "East", "West", "Central", "Upper", "Lower", "Old", "New", "Dark",
    "Iron", "Steel", "Golden", "Silver", "Crimson", "Shadow", "Broken", "Lost", "Dead", "Red",
    "Black", "White", "Gray", "Blue", "Green", "Rust", "Ash", "Stone", "Frost", "Storm",
    "Thunder", "Silent", "Hidden", "Fallen", "Burning", "Hollow", "Forgotten", "Bloody", "Wild", "Lone",
]
_TERR_MIDS = [
    "side", "gate", "ridge", "hill", "vale", "creek", "water", "field", "wood", "stone",
    "cross", "bridge", "port", "haven", "cliff", "peak", "bay", "lake", "river", "pine",
    "oak", "elm", "palm", "vine", "thorn", "fang", "skull", "bone", "crown", "tower",
    "wall", "forge", "mill", "yard", "well", "spring", "marsh", "grove", "dale", "moor",
]
_TERR_SUFFIXES = [
    "Turf", "Block", "Zone", "Strip", "Row", "Corner", "Plaza", "District", "Junction", "Alley",
    "Heights", "Crossing", "Square", "Outpost", "Quarters", "Grounds", "Yard", "Court", "Lane", "Run",
    "Point", "Stretch", "Flats", "Terrace", "Precinct", "Sector", "Ward", "Patch", "Lot", "Pit",
]

def _generate_territory_names():
    """Generate 1000+ unique territory names"""
    names = []
    # Pattern 1: Prefix + Mid + Suffix (40 * 40 * 30 = 48,000 combos, pick a diverse set)
    for p in _TERR_PREFIXES:
        for m in _TERR_MIDS:
            name = f"{p}{m} {_TERR_SUFFIXES[hash(p + m) % len(_TERR_SUFFIXES)]}"
            names.append(name)
    # Shuffle deterministically for variety
    rng = random.Random(42)
    rng.shuffle(names)
    return names

TERRITORY_NAMES = _generate_territory_names()  # 1600 unique names

TERRITORY_BOSS_NAMES = [
    "Turf Guardian", "Block Captain", "Dock Warden", "Plaza Enforcer", "Corner King",
    "Zone Protector", "Factory Foreman", "Market Boss", "Strip Lord", "Underpass Phantom",
    "Ridge Sentinel", "Heights Watcher", "Quarter Master", "Sector Chief", "Ward Keeper",
    "District Baron", "Junction Brawler", "Court Ruler", "Lane Prowler", "Point Defender",
]

TERRITORY_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#9b59b6", "#f39c12",
    "#1abc9c", "#e91e63", "#ff5722", "#607d8b", "#795548",
    "#00bcd4", "#8bc34a", "#ff9800", "#673ab7", "#009688",
    "#c62828", "#1565c0", "#2e7d32", "#6a1b9a", "#ef6c00",
]

# ============== MODELS ==============
class Position(BaseModel):
    latitude: float
    longitude: float

class PlayerStats(BaseModel):
    health: int = 100
    max_health: int = 100
    attack: int = 10
    defense: int = 10
    speed: int = 10
    luck: int = 10
    energy: int = 100
    max_energy: int = 100

class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    character_class: str
    level: int = 1
    xp: int = 0
    xp_to_next: int = 100
    stats: PlayerStats = Field(default_factory=PlayerStats)
    position: Optional[Position] = None
    cash: int = 100
    reputation: int = 0
    guild_id: Optional[str] = None
    equipment: Dict[str, Optional[str]] = Field(default_factory=lambda: {"weapon": None, "armor": None, "accessory": None, "vehicle": None})
    inventory: List[Any] = Field(default_factory=list)  # List of dicts: {"item_id": str, "durability": int, "max_durability": int}
    owned_skills: List[str] = Field(default_factory=lambda: ["heavy_strike", "quick_shot"])  # All skills player owns
    equipped_skills: List[str] = Field(default_factory=lambda: ["heavy_strike", "quick_shot"])  # Max 4 skills equipped for battle
    skills: List[str] = Field(default_factory=lambda: ["heavy_strike", "quick_shot"])  # Legacy field for backwards compatibility
    wins: int = 0
    losses: int = 0
    missions_completed: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

class PlayerCreate(BaseModel):
    name: str
    character_class: str

class AuthRegister(BaseModel):
    username: str
    password: str
    name: str
    character_class: str

class AuthLogin(BaseModel):
    username: str
    password: str

class PlayerUpdate(BaseModel):
    position: Optional[Position] = None
    last_active: datetime = Field(default_factory=datetime.utcnow)

class Monster(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    monster_type: str
    level: int
    stats: Dict[str, int]
    position: Position
    loot_cash: int
    loot_xp: int
    loot_items: List[str] = Field(default_factory=list)
    spawn_time: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_boss: bool = False

class Equipment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    equipment_type: str
    rarity: str
    stats_bonus: Dict[str, int]
    level_requirement: int = 1
    value: int = 10

class Mission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    dialogue: str
    objectives: List[str]
    mission_type: str
    difficulty: str
    level_requirement: int
    position: Position
    rewards: Dict[str, Any]
    time_limit_minutes: int = 30
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Battle(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player_id: str
    enemy_type: str  # "monster" or "player"
    enemy_id: str
    enemy_name: str
    player_health: int
    enemy_health: int
    player_max_health: int
    enemy_max_health: int
    player_energy: int
    turn: int = 1
    status: str = "active"  # active, won, lost
    combat_log: List[str] = Field(default_factory=list)
    rewards: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BattleAction(BaseModel):
    action: str  # "attack", "skill", "defend", "flee"
    skill_id: Optional[str] = None

class Guild(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    tag: str
    description: str
    leader_id: str
    officers: List[str] = Field(default_factory=list)
    members: List[str] = Field(default_factory=list)
    level: int = 1
    xp: int = 0
    territory_count: int = 0
    total_wins: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GuildCreate(BaseModel):
    name: str
    tag: str
    description: str

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel: str  # "global", "guild", "area"
    player_id: str
    player_name: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# ============== HELPER FUNCTIONS ==============
def calculate_distance(pos1: Position, pos2: Position) -> float:
    """Calculate distance in meters between two positions using Haversine formula"""
    R = 6371000  # Earth's radius in meters
    lat1, lon1 = math.radians(pos1.latitude), math.radians(pos1.longitude)
    lat2, lon2 = math.radians(pos2.latitude), math.radians(pos2.longitude)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def calculate_xp_to_level(level: int) -> int:
    """Calculate XP required for next level"""
    return int(100 * (level ** 1.5))

def calculate_stats_for_level(base_stats: Dict[str, int], level: int) -> Dict[str, int]:
    """Calculate stats based on level"""
    return {
        stat: int(value * (1 + (level - 1) * 0.1))
        for stat, value in base_stats.items()
    }

async def generate_ai_content(content_type: str, context: Dict[str, Any]) -> str:
    """Generate AI content for missions, dialogues, or descriptions"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"gta-rpg-{content_type}-{uuid.uuid4()}",
            system_message="""You are a creative writer for a GTA-style crime RPG game. 
            Generate dark, gritty, urban content with street slang. 
            Keep responses concise and impactful. 
            Never use explicit violence descriptions but imply danger.
            Make dialogue sound authentic to street culture."""
        ).with_model("openai", "gpt-4o")
        
        if content_type == "mission":
            prompt = f"""Generate a brief mission for a level {context.get('level', 1)} player.
            Mission type: {context.get('type', 'combat')}
            Location theme: {context.get('location', 'urban street')}
            
            Respond in this exact JSON format:
            {{"title": "Mission Title", "description": "2-3 sentences", "dialogue": "NPC dialogue 1-2 sentences", "objectives": ["objective 1", "objective 2"]}}"""
        elif content_type == "monster":
            prompt = f"""Generate a brief enemy description for a level {context.get('level', 1)} enemy named "{context.get('name', 'Street Thug')}".
            Type: {context.get('type', 'humanoid')}
            
            Respond with just 1-2 sentences describing their appearance and threat."""
        else:
            prompt = f"Generate brief {content_type} content: {context}"
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        # Fallback content
        if content_type == "mission":
            return '{"title": "Street Business", "description": "Handle some business in the neighborhood.", "dialogue": "Yo, I got a job for you.", "objectives": ["Complete the task", "Return for reward"]}'
        return "A dangerous figure from the streets."

# ============== AUTH ENDPOINTS ==============
@api_router.post("/auth/register")
async def register(data: AuthRegister):
    """Register a new account and create character"""
    # Validate
    if len(data.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(data.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    if data.character_class not in CHARACTER_CLASSES:
        raise HTTPException(status_code=400, detail="Invalid character class")
    
    # Check username taken
    existing = await db.players.find_one({"username": data.username.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Check name taken
    existing_name = await db.players.find_one({"name": data.name})
    if existing_name:
        raise HTTPException(status_code=400, detail="Character name already taken")
    
    class_info = CHARACTER_CLASSES[data.character_class]
    base_stats = class_info["base_stats"]
    
    player = Player(
        name=data.name,
        character_class=data.character_class,
        stats=PlayerStats(
            health=base_stats["health"],
            max_health=base_stats["health"],
            attack=base_stats["attack"],
            defense=base_stats["defense"],
            speed=base_stats["speed"],
            luck=base_stats["luck"]
        ),
        inventory=[
            create_inventory_item("rusty_pipe"),
            create_inventory_item("worn_jacket"),
            create_inventory_item("chain_necklace"),
            create_inventory_item("beat_up_bike")
        ],
        equipment={"weapon": None, "armor": None, "accessory": None, "vehicle": None}
    )
    
    player_dict = player.dict()
    player_dict["username"] = data.username.lower()
    player_dict["password_hash"] = pwd_context.hash(data.password)
    
    await db.players.insert_one(player_dict)
    return player

@api_router.post("/auth/login")
async def login(data: AuthLogin):
    """Login with username and password"""
    player = await db.players.find_one({"username": data.username.lower()})
    if not player:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not pwd_context.verify(data.password, player.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Update last active
    await db.players.update_one(
        {"id": player["id"]},
        {"$set": {"last_active": datetime.utcnow()}}
    )
    
    return Player(**player)

# ============== ACCOUNT DELETION ==============
class DeleteAccountRequest(BaseModel):
    username: str

@api_router.post("/account/delete-request")
async def request_account_deletion(data: DeleteAccountRequest):
    """
    Submit a request to delete an account.
    For privacy, we don't reveal if the account exists.
    """
    username = data.username.strip().lower()
    
    # Find the player by username or character name
    player = await db.players.find_one({
        "$or": [
            {"username": username},
            {"name": {"$regex": f"^{data.username.strip()}$", "$options": "i"}}
        ]
    })
    
    if player:
        player_id = player.get("id")
        
        # Store deletion request for processing
        deletion_request = {
            "id": str(uuid.uuid4()),
            "player_id": player_id,
            "username": username,
            "requested_at": datetime.utcnow(),
            "status": "pending",
            "scheduled_deletion": datetime.utcnow() + timedelta(days=30)
        }
        await db.deletion_requests.insert_one(deletion_request)
        
        # For immediate deletion (can be changed to scheduled):
        # Delete all player data
        await db.players.delete_one({"id": player_id})
        await db.territories.delete_many({"owner_id": player_id})
        await db.battles.delete_many({"player_id": player_id})
        await db.missions.delete_many({"player_id": player_id})
        
        # Clear owner from territories they owned
        await db.territories.update_many(
            {"owner_id": player_id},
            {"$set": {"owner_id": None, "owner_name": None, "owner_pic": None}}
        )
        
        logger.info(f"Account deletion processed for player: {player_id}")
    
    # Always return success for privacy (don't reveal if account exists)
    return {"status": "success", "message": "If an account exists with this username, it will be deleted within 30 days."}


@api_router.delete("/players/{player_id}/account")
async def delete_player_account(player_id: str):
    """
    Permanently delete a player's account and all associated data.
    This is for logged-in users who want to delete their own account.
    """
    # Find the player
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player_name = player.get("name", "Unknown")
    
    try:
        # Delete all player data from all collections
        await db.players.delete_one({"id": player_id})
        await db.territories.delete_many({"owner_id": player_id})
        await db.battles.delete_many({"player_id": player_id})
        await db.missions.delete_many({"player_id": player_id})
        await db.fitness_data.delete_many({"player_id": player_id})
        await db.guild_invites.delete_many({"player_id": player_id})
        await db.chat_messages.delete_many({"player_id": player_id})
        
        # Clear owner from territories they owned (don't delete territories, just remove owner)
        await db.territories.update_many(
            {"owner_id": player_id},
            {"$set": {"owner_id": None, "owner_name": None, "owner_pic": None}}
        )
        
        # Remove player from any guilds they're in
        await db.guilds.update_many(
            {"members": {"$elemMatch": {"id": player_id}}},
            {"$pull": {"members": {"id": player_id}}}
        )
        
        # If player was a guild leader, delete the guild or transfer leadership
        player_guilds = await db.guilds.find({"leader_id": player_id}).to_list(10)
        for guild in player_guilds:
            # Delete the guild if no other members
            if len(guild.get("members", [])) == 0:
                await db.guilds.delete_one({"id": guild["id"]})
            else:
                # Transfer to first available member
                new_leader = guild["members"][0]
                await db.guilds.update_one(
                    {"id": guild["id"]},
                    {"$set": {"leader_id": new_leader["id"], "leader_name": new_leader.get("name", "Unknown")}}
                )
        
        # Log the deletion for records
        deletion_log = {
            "id": str(uuid.uuid4()),
            "player_id": player_id,
            "player_name": player_name,
            "deleted_at": datetime.utcnow(),
            "deletion_type": "user_initiated"
        }
        await db.deletion_logs.insert_one(deletion_log)
        
        logger.info(f"Account permanently deleted for player: {player_id} ({player_name})")
        
        return {
            "status": "success",
            "message": "Your account and all associated data have been permanently deleted."
        }
        
    except Exception as e:
        logger.error(f"Error deleting account for player {player_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete account. Please try again.")


# ============== PLAYER ENDPOINTS ==============
@api_router.get("/")
async def root():
    return {"message": "GTA GPS RPG API v1.0", "status": "online"}

@api_router.get("/classes")
async def get_character_classes():
    """Get all available character classes"""
    return CHARACTER_CLASSES

@api_router.post("/players", response_model=Player)
async def create_player(player_data: PlayerCreate):
    """Create a new player character"""
    if player_data.character_class not in CHARACTER_CLASSES:
        raise HTTPException(status_code=400, detail="Invalid character class")
    
    # Check if name already exists
    existing = await db.players.find_one({"name": player_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Player name already taken")
    
    class_info = CHARACTER_CLASSES[player_data.character_class]
    base_stats = class_info["base_stats"]
    
    player = Player(
        name=player_data.name,
        character_class=player_data.character_class,
        stats=PlayerStats(
            health=base_stats["health"],
            max_health=base_stats["health"],
            attack=base_stats["attack"],
            defense=base_stats["defense"],
            speed=base_stats["speed"],
            luck=base_stats["luck"]
        ),
        inventory=[
            create_inventory_item("rusty_pipe"),
            create_inventory_item("worn_jacket"),
            create_inventory_item("chain_necklace"),
            create_inventory_item("beat_up_bike")
        ],
        equipment={"weapon": None, "armor": None, "accessory": None, "vehicle": None}
    )
    
    await db.players.insert_one(player.dict())
    return player

@api_router.get("/players/{player_id}", response_model=Player)
async def get_player(player_id: str):
    """Get player by ID with passive health regeneration"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Migrate inventory to new durability format if needed
    inventory = player.get("inventory", [])
    migrated_inventory = [migrate_inventory_item(item) for item in inventory]
    
    # Check if any items were migrated (strings converted to dicts)
    needs_migration = any(isinstance(item, str) for item in inventory)
    if needs_migration:
        await db.players.update_one(
            {"id": player_id},
            {"$set": {"inventory": migrated_inventory}}
        )
        player["inventory"] = migrated_inventory
    
    # Passive health & energy regen: 25% every 5 minutes
    now = datetime.utcnow()
    last_regen = player.get("last_health_regen")
    current_hp = player["stats"]["health"]
    max_hp = player["stats"]["max_health"]
    current_energy = player["stats"]["energy"]
    max_energy = player["stats"]["max_energy"]
    
    needs_regen = current_hp < max_hp or current_energy < max_energy
    if needs_regen:
        if last_regen:
            if isinstance(last_regen, str):
                last_regen = datetime.fromisoformat(last_regen)
            elapsed_seconds = (now - last_regen).total_seconds()
        else:
            baseline = player.get("last_active", player.get("created_at", now))
            if isinstance(baseline, str):
                baseline = datetime.fromisoformat(baseline)
            elapsed_seconds = (now - baseline).total_seconds()
        
        intervals = int(elapsed_seconds // 300)  # 300 seconds = 5 minutes
        if intervals > 0:
            update_fields = {"last_health_regen": now.isoformat()}
            
            # Health regen
            new_hp = min(max_hp, current_hp + int(max_hp * 0.25 * intervals))
            if new_hp != current_hp:
                update_fields["stats.health"] = new_hp
                player["stats"]["health"] = new_hp
            
            # Energy regen
            new_energy = min(max_energy, current_energy + int(max_energy * 0.25 * intervals))
            if new_energy != current_energy:
                update_fields["stats.energy"] = new_energy
                player["stats"]["energy"] = new_energy
            
            await db.players.update_one({"id": player_id}, {"$set": update_fields})
            player["last_health_regen"] = now.isoformat()
    
    return Player(**player)

@api_router.put("/players/{player_id}/position")
async def update_player_position(player_id: str, position: Position):
    """Update player's GPS position"""
    result = await db.players.update_one(
        {"id": player_id},
        {"$set": {"position": position.dict(), "last_active": datetime.utcnow()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"status": "position updated"}

class ProfilePicUpload(BaseModel):
    image: str  # base64 encoded image

@api_router.post("/players/{player_id}/profile-pic")
async def upload_profile_pic(player_id: str, data: ProfilePicUpload):
    """Upload a profile picture (base64)"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Validate base64 size (max ~2MB)
    if len(data.image) > 2_800_000:
        raise HTTPException(status_code=400, detail="Image too large. Max 2MB.")
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"profile_pic": data.image}}
    )
    
    # Also update profile pic on any territories this player owns
    result = await db.territories.update_many(
        {"owner_id": player_id},
        {"$set": {"owner_pic": data.image}}
    )
    
    print(f"[PROFILE_PIC_UPLOAD] Player {player_id}: Updated {result.modified_count} territories with new profile pic")
    
    return {"message": "Profile picture updated", "territories_updated": result.modified_count}

@api_router.get("/players/{player_id}/profile-pic")
async def get_profile_pic(player_id: str):
    """Get player's profile picture"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"profile_pic": player.get("profile_pic", None)}


@api_router.get("/debug/territory-sync/{player_id}")
async def debug_territory_sync(player_id: str):
    """Debug endpoint to check territory owner_pic sync status"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    has_profile_pic = bool(player.get("profile_pic"))
    profile_pic_length = len(player.get("profile_pic", "")) if player.get("profile_pic") else 0
    
    # Get all territories owned by this player
    territories = await db.territories.find({"owner_id": player_id}).to_list(100)
    
    territory_status = []
    for t in territories:
        territory_status.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "has_owner_pic": bool(t.get("owner_pic")),
            "owner_pic_length": len(t.get("owner_pic", "")) if t.get("owner_pic") else 0,
        })
    
    # Try to force sync now
    if has_profile_pic and territories:
        sync_result = await db.territories.update_many(
            {"owner_id": player_id},
            {"$set": {"owner_pic": player.get("profile_pic")}}
        )
        synced_count = sync_result.modified_count
    else:
        synced_count = 0
    
    return {
        "player_id": player_id,
        "player_name": player.get("name"),
        "has_profile_pic": has_profile_pic,
        "profile_pic_length": profile_pic_length,
        "territories_owned": len(territories),
        "territories": territory_status,
        "force_synced": synced_count,
    }


@api_router.get("/players/nearby/{player_id}")
async def get_nearby_players(player_id: str, radius: float = 500):
    """Get players within radius (meters)"""
    player = await db.players.find_one({"id": player_id})
    if not player or not player.get("position"):
        raise HTTPException(status_code=404, detail="Player not found or no position")
    
    player_pos = Position(**player["position"])
    all_players = await db.players.find(
        {"id": {"$ne": player_id}, "position": {"$exists": True}},
        {"id": 1, "name": 1, "level": 1, "character_class": 1, "position": 1, "guild_id": 1, "profile_pic": 1}
    ).to_list(100)
    
    nearby = []
    for p in all_players:
        if p.get("position"):
            other_pos = Position(**p["position"])
            distance = calculate_distance(player_pos, other_pos)
            if distance <= radius:
                nearby.append({
                    "id": p["id"],
                    "name": p["name"],
                    "level": p["level"],
                    "character_class": p["character_class"],
                    "position": p["position"],
                    "distance": round(distance, 1),
                    "guild_id": p.get("guild_id")
                })
    
    return nearby

@api_router.get("/leaderboard")
async def get_leaderboard(limit: int = 20):
    """Get top players by reputation"""
    players = await db.players.find(
        {},
        {"id": 1, "name": 1, "level": 1, "reputation": 1, "wins": 1, "character_class": 1, "profile_pic": 1}
    ).sort("reputation", -1).limit(limit).to_list(limit)
    return [
        {
            "rank": i + 1,
            "id": p["id"],
            "name": p["name"],
            "level": p["level"],
            "reputation": p["reputation"],
            "wins": p["wins"],
            "character_class": p["character_class"],
            "profile_pic": p.get("profile_pic", None),
        }
        for i, p in enumerate(players)
    ]

# ============== MONSTER ENDPOINTS ==============
@api_router.get("/monsters/spawn")
async def spawn_monsters(latitude: float, longitude: float, player_level: int = 1):
    """Spawn monsters tied to the territory grid. 5 enemies per new territory cell, 1 more every 5 minutes (max 10)."""
    import math
    
    LAT_M = 111000.0
    LNG_M = math.cos(math.radians(latitude)) * 111000.0
    cell_lat = TERRITORY_CELL_SIZE_M / LAT_M
    cell_lng = TERRITORY_CELL_SIZE_M / LNG_M
    
    # Find which territory cell the player is in
    player_row = int(latitude / cell_lat)
    player_col = int(longitude / cell_lng)
    if longitude < 0:
        player_col -= 1
    
    cell_id = f"spawn_{player_row}_{player_col}"
    
    # Clean up expired monsters
    await db.monsters.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
    
    # Get existing monsters in this cell + neighboring cells (3x3 grid around player)
    cell_ids = []
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            cell_ids.append(f"spawn_{player_row + dr}_{player_col + dc}")
    
    existing = await db.monsters.find({
        "cell_id": {"$in": cell_ids},
        "expires_at": {"$gt": datetime.utcnow()}
    }).to_list(100)
    
    # Monsters in the CURRENT cell
    current_cell_monsters = [m for m in existing if m.get("cell_id") == cell_id]
    nearby_count = len(current_cell_monsters)
    
    # Determine how many to spawn in current cell
    spawn_count = 0
    if nearby_count == 0:
        # New territory cell — spawn exactly 5 enemies
        spawn_count = 5
    elif nearby_count < 10:
        # Existing cell — spawn 1 every 5 minutes
        most_recent = max(current_cell_monsters, key=lambda m: m.get("spawn_time", datetime.min))
        last_spawn_time = most_recent.get("spawn_time", datetime.min)
        if isinstance(last_spawn_time, str):
            last_spawn_time = datetime.fromisoformat(last_spawn_time)
        elapsed = (datetime.utcnow() - last_spawn_time).total_seconds()
        if elapsed >= 300:
            spawn_count = 1
    
    spawn_count = min(spawn_count, 10 - nearby_count)
    
    # Spawn new monsters within this territory cell's bounds
    if spawn_count > 0:
        weighted_enemies = get_eligible_enemies(player_level)
        if not weighted_enemies:
            weighted_enemies = [(ENEMY_TIERS[0], 1)]
        
        cell_center_lat = (player_row + 0.5) * cell_lat
        cell_center_lng = (player_col + 0.5) * cell_lng
        half_cell_lat = cell_lat / 2
        half_cell_lng = cell_lng / 2
        
        for _ in range(spawn_count):
            enemies, weights = zip(*weighted_enemies)
            template = random.choices(enemies, weights=weights, k=1)[0]
            
            # Cap the monster level to player level + 1 for slight challenge
            max_enemy_level = min(template["level_max"], player_level + 1)
            # Ensure level_min doesn't exceed our cap
            min_enemy_level = min(template["level_min"], max_enemy_level)
            monster_level = random.randint(min_enemy_level, max_enemy_level)
            
            # Offset within territory cell bounds
            offset_lat = random.uniform(-half_cell_lat * 0.8, half_cell_lat * 0.8)
            offset_lon = random.uniform(-half_cell_lng * 0.8, half_cell_lng * 0.8)
            
            enemy_stats = calculate_enemy_stats(monster_level, template["is_boss"])
            enemy_type = "boss" if template["is_boss"] else "humanoid"
            description = await generate_ai_content("monster", {
                "name": template["name"],
                "level": monster_level,
                "type": enemy_type
            })
            
            monster = Monster(
                name=template["name"],
                description=description,
                monster_type=enemy_type,
                level=monster_level,
                stats=enemy_stats,
                position=Position(latitude=cell_center_lat + offset_lat, longitude=cell_center_lng + offset_lon),
                loot_cash=monster_level * random.randint(10, 25) * (3 if template["is_boss"] else 1),
                loot_xp=monster_level * random.randint(15, 30) * (3 if template["is_boss"] else 1),
                expires_at=datetime.utcnow() + timedelta(hours=1),
                is_boss=template["is_boss"]
            )
            
            monster_dict = monster.dict()
            monster_dict["cell_id"] = cell_id
            await db.monsters.insert_one(monster_dict)
    
    # Return all monsters in current + neighboring cells (visible area)
    all_nearby = await db.monsters.find({
        "cell_id": {"$in": cell_ids},
        "expires_at": {"$gt": datetime.utcnow()}
    }).to_list(100)
    
    return [serialize_doc(m) for m in all_nearby]

@api_router.get("/monsters/{monster_id}")
async def get_monster(monster_id: str):
    """Get monster details"""
    monster = await db.monsters.find_one({"id": monster_id})
    if not monster:
        raise HTTPException(status_code=404, detail="Monster not found")
    return serialize_doc(monster)

# ============== BATTLE ENDPOINTS ==============
# Helper: decrement active buffs after a battle ends
async def decrement_player_buffs(player_id: str):
    """Decrement battles_remaining on all active buffs; remove expired ones"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        return
    active_buffs = player.get("active_buffs", [])
    if not active_buffs:
        return
    updated_buffs = []
    for buff in active_buffs:
        remaining = buff.get("battles_remaining", 0) - 1
        if remaining > 0:
            buff["battles_remaining"] = remaining
            updated_buffs.append(buff)
    await db.players.update_one({"id": player_id}, {"$set": {"active_buffs": updated_buffs}})

@api_router.post("/battles/start")
async def start_battle(player_id: str, enemy_type: str, enemy_id: str):
    """Start a battle with monster or player"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if enemy_type == "monster":
        enemy = await db.monsters.find_one({"id": enemy_id})
        if not enemy:
            raise HTTPException(status_code=404, detail="Monster not found")
        enemy_name = enemy["name"]
        enemy_health = enemy["stats"]["health"]
    elif enemy_type == "player":
        enemy = await db.players.find_one({"id": enemy_id})
        if not enemy:
            raise HTTPException(status_code=404, detail="Enemy player not found")
        enemy_name = enemy["name"]
        enemy_health = enemy["stats"]["health"]
    else:
        raise HTTPException(status_code=400, detail="Invalid enemy type")
    
    # Calculate buffed max_health and max_energy from active_buffs
    base_max_health = player["stats"]["max_health"]
    base_max_energy = player["stats"]["max_energy"]
    buff_hp = sum(b["amount"] for b in player.get("active_buffs", []) if b["type"] == "max_health")
    buff_en = sum(b["amount"] for b in player.get("active_buffs", []) if b["type"] == "max_energy")
    buffed_max_health = base_max_health + buff_hp
    buffed_max_energy = base_max_energy + buff_en
    # Current health/energy capped to buffed max
    current_health = min(player["stats"]["health"], buffed_max_health)
    current_energy = min(player["stats"]["energy"], buffed_max_energy)
    
    battle = Battle(
        player_id=player_id,
        enemy_type=enemy_type,
        enemy_id=enemy_id,
        enemy_name=enemy_name,
        player_health=current_health,
        enemy_health=enemy_health,
        player_max_health=buffed_max_health,
        enemy_max_health=enemy_health,
        player_energy=current_energy,
        combat_log=[f"Battle started against {enemy_name}!"]
    )
    
    await db.battles.insert_one(battle.dict())
    return battle

@api_router.post("/battles/{battle_id}/action")
async def battle_action(battle_id: str, action: BattleAction):
    """Execute a battle action"""
    battle = await db.battles.find_one({"id": battle_id})
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")
    
    if battle["status"] != "active":
        return serialize_doc(battle)
    
    player = await db.players.find_one({"id": battle["player_id"]})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if battle["enemy_type"] == "monster":
        enemy = await db.monsters.find_one({"id": battle["enemy_id"]})
        if not enemy:
            # Monster expired or was deleted, end the battle
            await db.battles.update_one(
                {"id": battle_id},
                {"$set": {"status": "fled", "combat_log": battle["combat_log"] + ["Enemy has fled!"]}}
            )
            return serialize_doc(await db.battles.find_one({"id": battle_id}))
        enemy_stats = enemy["stats"]
    else:
        enemy = await db.players.find_one({"id": battle["enemy_id"]})
        if not enemy:
            raise HTTPException(status_code=404, detail="Enemy player not found")
        enemy_stats = enemy["stats"]
    
    player_stats = player["stats"]
    combat_log = battle["combat_log"]
    player_health = battle["player_health"]
    enemy_health = battle["enemy_health"]
    player_energy = battle["player_energy"]
    
    # Player action
    if action.action == "attack":
        # Miss chance: 10% base, reduced by luck (min 5%)
        miss_chance = max(0.05, 0.10 - (player_stats.get("luck", 0) * 0.005))
        if random.random() < miss_chance:
            combat_log.append("Your attack MISSED!")
        else:
            damage = max(1, player_stats["attack"] - enemy_stats.get("defense", 0) // 2)
            # Crit chance: based on luck (5% base + luck bonus)
            crit_chance = 0.05 + (player_stats.get("luck", 0) * 0.01)
            crit = random.random() < crit_chance
            if crit:
                damage = int(damage * 2.0)
                combat_log.append(f"💥 CRITICAL HIT! You deal {damage} damage!")
            else:
                combat_log.append(f"You attack for {damage} damage!")
            enemy_health -= damage
        
    elif action.action == "skill" and action.skill_id:
        skill = SKILLS.get(action.skill_id)
        if not skill:
            raise HTTPException(status_code=400, detail="Invalid skill")
        
        # Check if skill is equipped (only equipped skills can be used in battle)
        equipped_skills = player.get("equipped_skills", player.get("owned_skills", player.get("skills", ["heavy_strike", "quick_shot"])))
        if action.skill_id not in equipped_skills:
            raise HTTPException(status_code=400, detail="Skill not equipped. Equip it first to use in battle.")
        
        if skill["cost"] > player_energy:
            raise HTTPException(status_code=400, detail="Not enough energy")
        
        player_energy -= skill["cost"]
        
        if "damage_mult" in skill:
            # Skills have lower miss chance (5%)
            if random.random() < 0.05:
                combat_log.append(f"Your {skill['name']} MISSED!")
            else:
                damage = int(player_stats["attack"] * skill["damage_mult"])
                # Skills can also crit (10% chance)
                if random.random() < 0.10:
                    damage = int(damage * 2.0)
                    combat_log.append(f"💥 CRITICAL {skill['name']}! You deal {damage} damage!")
                else:
                    combat_log.append(f"You use {skill['name']} for {damage} damage!")
                enemy_health -= damage
        elif "heal_percent" in skill:
            heal = int(battle["player_max_health"] * skill["heal_percent"])
            player_health = min(battle["player_max_health"], player_health + heal)
            combat_log.append(f"You use {skill['name']} and heal {heal} HP!")
        elif "defense_buff" in skill:
            combat_log.append(f"You use {skill['name']} - Defense increased!")
            
    elif action.action == "defend":
        combat_log.append("You take a defensive stance!")
        player_energy = min(100, player_energy + 10)
        
    elif action.action == "flee":
        if random.random() < 0.5:
            await decrement_player_buffs(battle["player_id"])
            await db.battles.update_one(
                {"id": battle_id},
                {"$set": {"status": "fled", "combat_log": combat_log + ["You fled from battle!"]}}
            )
            return serialize_doc(await db.battles.find_one({"id": battle_id}))
        else:
            combat_log.append("Failed to flee!")
    
    # Check if enemy defeated
    if enemy_health <= 0:
        rewards = None
        if battle["enemy_type"] == "monster":
            rewards = {
                "cash": enemy["loot_cash"],
                "xp": enemy["loot_xp"],
                "items": enemy.get("loot_items", [])
            }
            
            # Random item drop based on luck
            drop_chance = 0.3 + (player_stats.get("luck", 0) * 0.02)  # 30% base + 2% per luck
            dropped_item = None
            if random.random() < drop_chance:
                # Pick a random item based on enemy level
                available_items = [
                    item for item in ALL_ITEMS.values()
                    if item["level_requirement"] <= enemy["level"] + 2
                ]
                if available_items:
                    dropped_item = random.choice(available_items)
                    rewards["items"] = [dropped_item["id"]]
                    rewards["dropped_item"] = dropped_item
                    await db.players.update_one(
                        {"id": player["id"]},
                        {"$push": {"inventory": dropped_item["id"]}}
                    )
                    combat_log.append(f"Loot drop: {dropped_item['name']}!")
            
            # Update player stats
            new_xp = player["xp"] + rewards["xp"]
            new_cash = player["cash"] + rewards["cash"]
            level_up = new_xp >= player["xp_to_next"]
            
            update_data = {
                "xp": new_xp if not level_up else new_xp - player["xp_to_next"],
                "cash": new_cash,
                "wins": player["wins"] + 1,
                "reputation": player["reputation"] + enemy["level"],
                "stats.health": max(1, player_health),
                "stats.energy": max(0, player_energy),
                "last_health_regen": datetime.utcnow().isoformat(),
            }
            
            if level_up:
                new_level = player["level"] + 1
                update_data["level"] = new_level
                update_data["xp_to_next"] = calculate_xp_to_level(new_level)
                update_data["stats.max_health"] = int(player_stats["max_health"] * 1.1)
                update_data["stats.attack"] = int(player_stats["attack"] * 1.05)
                update_data["stats.defense"] = int(player_stats["defense"] * 1.05)
                combat_log.append(f"LEVEL UP! You are now level {new_level}!")
            
            await db.players.update_one({"id": player["id"]}, {"$set": update_data})
            await db.monsters.delete_one({"id": enemy["id"]})
            
            # Auto-increment "defeat_monsters" mission progress (per-player)
            active_missions = player.get("active_missions", [])
            if active_missions:
                # Batch fetch all missions in one query (fix N+1 pattern)
                missions_cursor = db.missions.find({"id": {"$in": active_missions}})
                missions_list = await missions_cursor.to_list(length=50)
                for m in missions_list:
                    mid = m["id"]
                    pp = m.get("player_progress", {})
                    player_data = pp.get(player["id"], {})
                    current_progress = player_data.get("progress", 0)
                    goal_target = m.get("goal_target", 999)
                    
                    if current_progress < goal_target:
                        should_increment = False
                        if m.get("mission_type") == "defeat_monsters":
                            should_increment = True
                        elif m.get("mission_type") == "bounty":
                            bounty_enemy = m.get("bounty_enemy", "")
                            if bounty_enemy and bounty_enemy.lower() in enemy["name"].lower():
                                should_increment = True
                        
                        if should_increment:
                            player_data["progress"] = current_progress + 1
                            pp[player["id"]] = player_data
                            await db.missions.update_one({"id": mid}, {"$set": {"player_progress": pp}})
            
        combat_log.append(f"Victory! {battle['enemy_name']} defeated!")
        
        # Apply durability loss for battle
        await apply_battle_durability_loss(battle["player_id"], dealt_damage=True, took_damage=True)
        
        await decrement_player_buffs(battle["player_id"])
        
        await db.battles.update_one(
            {"id": battle_id},
            {"$set": {
                "status": "won",
                "enemy_health": 0,
                "player_health": player_health,
                "player_energy": player_energy,
                "combat_log": combat_log,
                "rewards": rewards,
                "turn": battle["turn"] + 1
            }}
        )
        return serialize_doc(await db.battles.find_one({"id": battle_id}))
    
    # Enemy turn
    # Enemy miss chance: 12% base
    if random.random() < 0.12:
        combat_log.append(f"{battle['enemy_name']}'s attack MISSED!")
    else:
        enemy_damage = max(1, enemy_stats.get("attack", 10) - player_stats["defense"] // 2)
        if action.action == "defend":
            enemy_damage = enemy_damage // 2
        
        # Enemy crit chance: 8%
        if random.random() < 0.08:
            enemy_damage = int(enemy_damage * 2.0)
            combat_log.append(f"💥 {battle['enemy_name']} lands a CRITICAL HIT for {enemy_damage} damage!")
        else:
            combat_log.append(f"{battle['enemy_name']} attacks for {enemy_damage} damage!")
        
        player_health -= enemy_damage
    
    # Check if player defeated
    if player_health <= 0:
        await db.players.update_one(
            {"id": player["id"]},
            {"$set": {
                "losses": player["losses"] + 1,
                "stats.health": 1,
                "stats.energy": max(0, player_energy),
                "last_health_regen": datetime.utcnow().isoformat(),
            }}
        )
        # Apply durability loss for battle
        await apply_battle_durability_loss(battle["player_id"], dealt_damage=True, took_damage=True)
        await decrement_player_buffs(battle["player_id"])
        combat_log.append("You have been defeated!")
        
        await db.battles.update_one(
            {"id": battle_id},
            {"$set": {
                "status": "lost",
                "player_health": 0,
                "enemy_health": enemy_health,
                "combat_log": combat_log,
                "turn": battle["turn"] + 1
            }}
        )
        return serialize_doc(await db.battles.find_one({"id": battle_id}))
    
    # Update battle state
    await db.battles.update_one(
        {"id": battle_id},
        {"$set": {
            "player_health": player_health,
            "enemy_health": enemy_health,
            "player_energy": player_energy,
            "combat_log": combat_log,
            "turn": battle["turn"] + 1
        }}
    )
    
    return serialize_doc(await db.battles.find_one({"id": battle_id}))

@api_router.get("/battles/{battle_id}")
async def get_battle(battle_id: str):
    """Get battle state"""
    battle = await db.battles.find_one({"id": battle_id})
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")
    return serialize_doc(battle)

# ============== MISSION ENDPOINTS ==============
@api_router.get("/missions/generate")
async def generate_missions(latitude: float, longitude: float, player_level: int = 1, player_id: str = ""):
    """Generate phone booth missions near a location with goal-based objectives"""
    position = Position(latitude=latitude, longitude=longitude)
    
    # Clean expired missions
    await db.missions.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
    
    # Get existing nearby missions
    existing = await db.missions.find({"expires_at": {"$gt": datetime.utcnow()}}).to_list(50)
    nearby_raw = [m for m in existing if calculate_distance(position, Position(**m["position"])) < 1000]
    
    # Serialize with player-specific progress
    nearby = []
    for m in nearby_raw:
        doc = serialize_doc(m)
        if player_id:
            pp = m.get("player_progress", {})
            if player_id in pp:
                doc["accepted_by"] = player_id
                doc["goal_progress"] = pp[player_id].get("progress", 0)
            else:
                doc["accepted_by"] = None
                doc["goal_progress"] = 0
        nearby.append(doc)
    
    if len(nearby) >= 3:
        return nearby
    
    # Mission templates: defeat monsters, travel distance, walk steps
    MISSION_TEMPLATES = [
        {"type": "defeat_monsters", "title": "Street Cleanup", "targets": [3, 5, 7, 10], "desc": "Defeat {n} monsters in the area."},
        {"type": "defeat_monsters", "title": "Turf War", "targets": [4, 6, 8], "desc": "Take down {n} enemies to prove your strength."},
        {"type": "defeat_monsters", "title": "Bounty Hunt", "targets": [2, 3, 5], "desc": "Hunt down {n} wanted targets."},
        {"type": "travel_distance", "title": "Recon Mission", "targets": [500, 1000, 1500, 2000], "desc": "Travel {n}m to scout the area."},
        {"type": "travel_distance", "title": "Supply Run", "targets": [800, 1200, 2000], "desc": "Cover {n}m to deliver the goods."},
        {"type": "walk_steps", "title": "Patrol Duty", "targets": [1000, 2000, 3000, 5000], "desc": "Walk {n} steps on patrol."},
        {"type": "walk_steps", "title": "Cardio Training", "targets": [1500, 2500, 4000], "desc": "Train with {n} steps."},
    ]
    
    # Bounty missions (dollar sign on map): defeat specific enemy types for cash
    # Dynamically generate bounties from the player's current and previous tiers only
    player_tier = get_player_tier(player_level)
    tier_enemies = [e for e in ENEMY_TIERS if e["tier"] <= player_tier and not e["is_boss"]]
    
    BOUNTY_TEMPLATES = []
    bounty_titles = {
        "Thug": "Thug Bounty", "Gangster": "Gangster Hit", "Gangsta": "Gangsta Hit", "Criminal": "Criminal Warrant",
        "Villain": "Villain Contract", "Bandit": "Bandit Sweep", "Assassin": "Assassin Hunt",
        "Mobster": "Mobster Bounty", "Hooligan": "Hooligan Purge", "Thief": "Thief Hunt",
        "Hoodlum": "Hoodlum Purge", "Pirate": "Pirate Raid", "Bully": "Bully Beatdown",
        "Offender": "Offender Takedown", "Hood": "Hood Cleanup", "Goon": "Goon Smash",
        "Ruffian": "Ruffian Roundup", "Punk": "Punk Patrol", "Rough Neck": "Rough Neck Rush",
        "Tough Guy": "Tough Guy Takedown", "Gang Banger": "Gang Banger Bust", "Gorilla": "Gorilla Hunt",
        "Felon": "Felon Takedown", "Outlaw": "Outlaw Contract",
    }
    for enemy in tier_enemies:
        name = enemy["name"]
        title = bounty_titles.get(name, f"{name} Bounty")
        BOUNTY_TEMPLATES.append({
            "type": "bounty",
            "title": title,
            "enemy": name,
            "targets": [3, 5, 8],
            "desc": f"Eliminate {{n}} {name}s for a cash reward.",
        })
    
    difficulties = ["easy", "medium", "hard"]
    
    missions_to_spawn = max(0, 5 - len(nearby))
    
    # Guarantee at least 2 bounty missions
    existing_bounties = sum(1 for m in nearby if m.get("mission_type") == "bounty")
    bounty_count = existing_bounties
    regular_count = len(nearby) - existing_bounties
    min_bounties = 2
    
    for i in range(missions_to_spawn):
        # Force bounty if we haven't hit the minimum yet and running out of slots
        remaining = missions_to_spawn - i
        bounties_needed = min_bounties - bounty_count
        
        if bounties_needed > 0 and bounties_needed >= remaining:
            is_bounty = True
        elif bounty_count < min_bounties and random.random() < 0.6:
            is_bounty = True
        elif bounty_count >= min_bounties:
            is_bounty = random.random() < 0.3
        else:
            is_bounty = random.random() < 0.5
        
        if is_bounty:
            # Pick a bounty that targets a different enemy than already spawned
            used_enemies = [m.get("bounty_enemy", "") for m in nearby if m.get("mission_type") == "bounty"]
            available = [t for t in BOUNTY_TEMPLATES if t["enemy"] not in used_enemies]
            if not available:
                available = BOUNTY_TEMPLATES
            template = random.choice(available)
            bounty_count += 1
            target = random.choice(template["targets"])
            difficulty = random.choice(difficulties)
            diff_mult = {"easy": 0.7, "medium": 1.0, "hard": 1.5}[difficulty]
            target = int(target * diff_mult)
            description = template["desc"].format(n=target)
            
            offset_lat = random.uniform(-0.005, 0.005)
            offset_lon = random.uniform(-0.005, 0.005)
            
            # Bounties pay 2x cash
            reward_mult = {"easy": 1.5, "medium": 2.5, "hard": 4.0}[difficulty]
            
            mission = Mission(
                title=template["title"],
                description=description,
                dialogue=f"There's money on the table. {description}",
                objectives=[description],
                mission_type="bounty",
                difficulty=difficulty,
                level_requirement=max(1, player_level - 2),
                position=Position(latitude=latitude + offset_lat, longitude=longitude + offset_lon),
                rewards={
                    "cash": int(80 * player_level * reward_mult),
                    "xp": int(30 * player_level * reward_mult),
                    "reputation": int(3 * reward_mult)
                },
                time_limit_minutes=60,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            
            mission_dict = mission.dict()
            mission_dict["goal_target"] = target
            mission_dict["goal_progress"] = 0
            mission_dict["bounty_enemy"] = template["enemy"]
            
            await db.missions.insert_one(mission_dict)
            nearby.append(serialize_doc(mission_dict))
        else:
            regular_count += 1
            template = random.choice(MISSION_TEMPLATES)
            difficulty = random.choice(difficulties)
            target = random.choice(template["targets"])
            
            diff_mult = {"easy": 0.7, "medium": 1.0, "hard": 1.5}[difficulty]
            target = int(target * diff_mult)
            
            description = template["desc"].format(n=target)
            
            offset_lat = random.uniform(-0.005, 0.005)
            offset_lon = random.uniform(-0.005, 0.005)
            
            reward_mult = {"easy": 1, "medium": 1.5, "hard": 2.5}[difficulty]
            
            mission = Mission(
                title=template["title"],
                description=description,
                dialogue=f"Pick up the phone. {description}",
                objectives=[description],
                mission_type=template["type"],
                difficulty=difficulty,
                level_requirement=max(1, player_level - 2),
                position=Position(latitude=latitude + offset_lat, longitude=longitude + offset_lon),
                rewards={
                    "cash": int(50 * player_level * reward_mult),
                    "xp": int(40 * player_level * reward_mult),
                    "reputation": int(5 * reward_mult)
                },
                time_limit_minutes=60,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            
            mission_dict = mission.dict()
            mission_dict["goal_target"] = target
            mission_dict["goal_progress"] = 0
            
            await db.missions.insert_one(mission_dict)
            nearby.append(serialize_doc(mission_dict))
    
    return nearby

@api_router.get("/missions/active/{player_id}")
async def get_active_missions(player_id: str):
    """Get all active/accepted missions for a player with per-player progress"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    active_ids = player.get("active_missions", [])
    if not active_ids:
        return []
    
    missions = []
    stale = False
    clean_ids = list(active_ids)
    for mid in active_ids:
        m = await db.missions.find_one({"id": mid})
        if m:
            doc = serialize_doc(m)
            # Inject this player's specific progress
            pp = m.get("player_progress", {})
            player_data = pp.get(player_id, {})
            doc["goal_progress"] = player_data.get("progress", 0)
            doc["accepted_by"] = player_id  # For frontend compatibility
            missions.append(doc)
        else:
            clean_ids.remove(mid)
            stale = True
    
    if stale:
        await db.players.update_one({"id": player_id}, {"$set": {"active_missions": clean_ids}})
    
    return missions

@api_router.post("/missions/{mission_id}/accept")
async def accept_mission(mission_id: str, player_id: str):
    """Accept a mission - multiple players can accept the same mission"""
    mission = await db.missions.find_one({"id": mission_id})
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Prevent same player from re-accepting
    active = player.get("active_missions", [])
    if mission_id in active:
        raise HTTPException(status_code=400, detail="You already accepted this mission")
    
    pp = mission.get("player_progress", {})
    if player_id in pp:
        raise HTTPException(status_code=400, detail="You already accepted this mission")
    
    # Add this player's progress entry to the mission
    pp[player_id] = {"progress": 0, "accepted_at": datetime.utcnow().isoformat()}
    await db.missions.update_one(
        {"id": mission_id},
        {"$set": {
            "player_progress": pp,
            "accepted_by": player_id,  # Keep for backward compat
        }}
    )
    
    # Track in player's active missions
    active.append(mission_id)
    await db.players.update_one({"id": player_id}, {"$set": {"active_missions": active}})
    
    return {"message": f"Mission accepted: {mission['title']}", "mission_id": mission_id}

@api_router.post("/missions/{mission_id}/cancel")
async def cancel_mission(mission_id: str, player_id: str):
    """Cancel/abandon an accepted mission"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    active = player.get("active_missions", [])
    if mission_id not in active:
        raise HTTPException(status_code=400, detail="Mission not in your active list")
    
    # Remove from player's active missions
    active.remove(mission_id)
    await db.players.update_one({"id": player_id}, {"$set": {"active_missions": active}})
    
    # Remove player's progress from the mission
    mission = await db.missions.find_one({"id": mission_id})
    if mission:
        pp = mission.get("player_progress", {})
        if player_id in pp:
            del pp[player_id]
            await db.missions.update_one({"id": mission_id}, {"$set": {"player_progress": pp}})
    
    return {"message": "Mission cancelled"}

@api_router.put("/missions/{mission_id}/progress")
async def update_mission_progress(mission_id: str, player_id: str, progress: int):
    """Update progress on a mission goal for a specific player"""
    mission = await db.missions.find_one({"id": mission_id})
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    pp = mission.get("player_progress", {})
    if player_id not in pp:
        # Backward compat: check old accepted_by field
        if mission.get("accepted_by") != player_id:
            raise HTTPException(status_code=400, detail="Mission not accepted by this player")
    
    new_progress = min(progress, mission.get("goal_target", 999))
    pp[player_id] = pp.get(player_id, {})
    pp[player_id]["progress"] = new_progress
    
    await db.missions.update_one(
        {"id": mission_id},
        {"$set": {"player_progress": pp}}
    )
    
    completed = new_progress >= mission.get("goal_target", 999)
    return {"progress": new_progress, "target": mission.get("goal_target"), "completed": completed}

@api_router.post("/missions/{mission_id}/complete")
async def complete_mission(mission_id: str, player_id: str):
    """Complete a mission and claim rewards for a specific player"""
    mission = await db.missions.find_one({"id": mission_id})
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Get this player's progress
    pp = mission.get("player_progress", {})
    player_progress = pp.get(player_id, {}).get("progress", mission.get("goal_progress", 0))
    goal_target = mission.get("goal_target", 999)
    
    if player_progress < goal_target:
        raise HTTPException(status_code=400, detail=f"Goal not met: {player_progress}/{goal_target}")
    
    rewards = mission["rewards"]
    
    new_xp = player["xp"] + rewards["xp"]
    level_up = new_xp >= player["xp_to_next"]
    
    update_data = {
        "xp": new_xp if not level_up else new_xp - player["xp_to_next"],
        "cash": player["cash"] + rewards["cash"],
        "reputation": player["reputation"] + rewards.get("reputation", 0),
        "missions_completed": player["missions_completed"] + 1
    }
    
    if level_up:
        new_level = player["level"] + 1
        update_data["level"] = new_level
        update_data["xp_to_next"] = calculate_xp_to_level(new_level)
    
    # Remove from player's active missions
    active = player.get("active_missions", [])
    if mission_id in active:
        active.remove(mission_id)
        update_data["active_missions"] = active
    
    await db.players.update_one({"id": player_id}, {"$set": update_data})
    
    # Remove this player from mission's player_progress
    if player_id in pp:
        del pp[player_id]
        await db.missions.update_one({"id": mission_id}, {"$set": {"player_progress": pp}})
    
    # Only delete mission if no other players are tracking it
    if not pp:
        await db.missions.delete_one({"id": mission_id})
    
    return {
        "message": "Mission completed!",
        "rewards": rewards,
        "level_up": level_up
    }

# ============== GUILD ENDPOINTS ==============
@api_router.post("/guilds", response_model=Guild)
async def create_guild(guild_data: GuildCreate, leader_id: str):
    """Create a new guild"""
    player = await db.players.find_one({"id": leader_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player.get("guild_id"):
        raise HTTPException(status_code=400, detail="Already in a guild")
    
    existing = await db.guilds.find_one({"$or": [{"name": guild_data.name}, {"tag": guild_data.tag}]})
    if existing:
        raise HTTPException(status_code=400, detail="Guild name or tag already taken")
    
    guild = Guild(
        name=guild_data.name,
        tag=guild_data.tag,
        description=guild_data.description,
        leader_id=leader_id,
        members=[leader_id]
    )
    
    await db.guilds.insert_one(guild.dict())
    await db.players.update_one({"id": leader_id}, {"$set": {"guild_id": guild.id}})
    
    return guild

@api_router.get("/guilds/{guild_id}")
async def get_guild(guild_id: str):
    """Get guild details"""
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    # Get member details
    members = await db.players.find({"id": {"$in": guild["members"]}}).to_list(100)
    guild["member_details"] = [
        {"id": m["id"], "name": m["name"], "level": m["level"], "character_class": m["character_class"]}
        for m in members
    ]
    
    return serialize_doc(guild)

@api_router.post("/guilds/{guild_id}/join")
async def join_guild(guild_id: str, player_id: str):
    """Join a guild"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player.get("guild_id"):
        raise HTTPException(status_code=400, detail="Already in a guild")
    
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    await db.guilds.update_one({"id": guild_id}, {"$push": {"members": player_id}})
    await db.players.update_one({"id": player_id}, {"$set": {"guild_id": guild_id}})
    
    return {"message": "Joined guild successfully"}

@api_router.post("/guilds/{guild_id}/leave")
async def leave_guild(guild_id: str, player_id: str):
    """Leave a guild"""
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    if guild["leader_id"] == player_id:
        raise HTTPException(status_code=400, detail="Leader cannot leave. Transfer leadership first.")
    
    await db.guilds.update_one({"id": guild_id}, {"$pull": {"members": player_id}})
    await db.players.update_one({"id": player_id}, {"$set": {"guild_id": None}})
    
    return {"message": "Left guild successfully"}

@api_router.get("/guilds")
async def list_guilds(limit: int = 20):
    """List top guilds"""
    guilds = await db.guilds.find().sort("level", -1).limit(limit).to_list(limit)
    return [serialize_doc(g) for g in guilds]

# ============== SHOP ENDPOINTS ==============

@api_router.get("/shops/spawn")
async def spawn_shops(latitude: float, longitude: float, player_level: int = 1):
    """Spawn random shops near a location - only shows items available at player's level"""
    shops = []
    num_shops = random.randint(2, 3)  # Always spawn 2-3 shops
    
    # Ensure at least one gun shop spawns (for skills)
    shop_types_to_spawn = ["gun_shop"]
    remaining_types = [t for t in SHOP_TYPES.keys() if t != "gun_shop"]
    for _ in range(num_shops - 1):
        shop_types_to_spawn.append(random.choice(remaining_types))
    random.shuffle(shop_types_to_spawn)
    
    for i in range(num_shops):
        # Random offset within ~500m
        lat_offset = random.uniform(-0.004, 0.004)
        lng_offset = random.uniform(-0.004, 0.004)
        
        shop_type = shop_types_to_spawn[i] if i < len(shop_types_to_spawn) else random.choice(list(SHOP_TYPES.keys()))
        shop_config = SHOP_TYPES[shop_type]
        shop_name = random.choice(SHOP_NAMES)
        
        # Filter items by player level - only show items the player can actually use
        level_appropriate_items = [item for item in ALL_ITEMS.values() if item.get("level_requirement", 1) <= player_level]
        
        # Pick random items focused on the shop type from level-appropriate items
        focus_items = [item for item in level_appropriate_items if item.get("equipment_type") in shop_config["focus"]]
        other_items = [item for item in level_appropriate_items if item.get("equipment_type") not in shop_config["focus"]]
        
        # Main stock: 4-8 items from focus + 1-2 random others
        stock_count = random.randint(4, 8)
        stock = random.sample(focus_items, min(stock_count, len(focus_items))) if focus_items else []
        extra_count = random.randint(1, 2)
        if other_items:
            stock += random.sample(other_items, min(extra_count, len(other_items)))
        random.shuffle(stock)
        
        # Price multiplier (0.8x to 1.5x) - some shops have deals, some overcharge
        price_mult = round(random.uniform(0.8, 1.5), 2)
        
        # Apply price multiplier to stock
        priced_stock = []
        for item in stock:
            priced_item = {**item}
            priced_item["shop_price"] = max(5, int(item["value"] * price_mult))
            priced_stock.append(priced_item)
        
        # Add skills to gun shops
        skills_for_sale = []
        if shop_type == "gun_shop":
            # Get skills available at player's level that have a value (purchasable)
            available_skills = [
                {"id": skill_id, **skill, "item_type": "skill"} 
                for skill_id, skill in SKILLS.items() 
                if skill["unlock_level"] <= player_level and skill.get("value", 0) > 0
            ]
            # Pick 3-5 random skills to sell
            if available_skills:
                skill_count = min(random.randint(3, 5), len(available_skills))
                skills_for_sale = random.sample(available_skills, skill_count)
                # Apply price multiplier to skills
                for skill in skills_for_sale:
                    skill["shop_price"] = max(50, int(skill["value"] * price_mult))
        
        shop = {
            "id": str(uuid.uuid4()),
            "name": shop_name,
            "shop_type": shop_type,
            "latitude": latitude + lat_offset,
            "longitude": longitude + lng_offset,
            "price_multiplier": price_mult,
            "stock": priced_stock,
            "skills_for_sale": skills_for_sale,
            "level": player_level,
        }
        shops.append(shop)
    
    return shops

@api_router.post("/shops/buy")
async def buy_from_shop(player_id: str, item_id: str, shop_price: int):
    """Buy an item from a specific shop"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    item = ALL_ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if player.get("cash", 0) < shop_price:
        raise HTTPException(status_code=400, detail="Not enough cash")
    
    if player.get("level", 1) < item["level_requirement"]:
        raise HTTPException(status_code=400, detail=f"Requires level {item['level_requirement']}")
    
    await db.players.update_one(
        {"id": player_id},
        {"$inc": {"cash": -shop_price}, "$push": {"inventory": item_id}}
    )
    return {"message": f"Purchased {item['name']}!", "item": item}


# ============== RESTAURANT ENDPOINTS ==============

RESTAURANT_NAMES = [
    "Cluckin' Bell", "Burger Shot", "Pizza Stack", "Well Stacked Pizza",
    "Taco Bomb", "Wing World", "Noodle Exchange", "Bean Machine",
    "Al Dente's", "The Rusty Brown's", "Steak Out Grill", "Dragon Garden",
    "Lucky Plucker", "Street Eats Diner", "The Golden Skillet",
]

RESTAURANT_ICONS = ["🍔", "🍕", "🌮", "🍗", "🍜", "🥩", "🍣", "☕"]


@api_router.get("/restaurants/spawn")
async def spawn_restaurants(latitude: float, longitude: float, player_level: int = 1):
    """Spawn restaurants near a location — only appears in some areas (not every radius)"""
    # Use a grid-based seed so the same area always gives the same result
    grid_lat = round(latitude * 200) / 200  # ~500m grid cells
    grid_lng = round(longitude * 200) / 200
    area_seed = hash(f"restaurant_{grid_lat}_{grid_lng}")
    rng = random.Random(area_seed)
    
    # Only spawn in ~40% of areas (every few radius areas)
    if rng.random() > 0.4:
        return []
    
    # Check if restaurants already exist nearby in DB
    existing = await db.restaurants.find({
        "latitude": {"$gte": latitude - 0.005, "$lte": latitude + 0.005},
        "longitude": {"$gte": longitude - 0.005, "$lte": longitude + 0.005},
    }).to_list(10)
    
    if existing:
        for r in existing:
            r.pop("_id", None)
        return existing
    
    # Spawn 1 restaurant in this area
    lat_offset = rng.uniform(-0.003, 0.003)
    lng_offset = rng.uniform(-0.003, 0.003)
    
    restaurant = {
        "id": str(uuid.uuid4()),
        "name": rng.choice(RESTAURANT_NAMES),
        "icon": rng.choice(RESTAURANT_ICONS),
        "latitude": latitude + lat_offset,
        "longitude": longitude + lng_offset,
        "heal_percent": 25,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.restaurants.insert_one(restaurant)
    restaurant.pop("_id", None)
    return [restaurant]


@api_router.post("/restaurants/{restaurant_id}/eat")
async def eat_at_restaurant(restaurant_id: str, player_id: str):
    """Player eats at restaurant — heals 25% of max HP. Cooldown: 10 minutes per restaurant."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    restaurant = await db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Check cooldown (10 minutes per player per restaurant)
    cooldown_key = f"restaurant_cooldowns.{restaurant_id}"
    last_visit = player.get("restaurant_cooldowns", {}).get(restaurant_id)
    if last_visit:
        try:
            last_dt = datetime.fromisoformat(last_visit)
            mins_since = (datetime.utcnow() - last_dt).total_seconds() / 60
            if mins_since < 10:
                remaining = round(10 - mins_since, 1)
                raise HTTPException(
                    status_code=400,
                    detail=f"You ate here recently! Come back in {remaining} minutes."
                )
        except (ValueError, TypeError):
            pass
    
    stats = player.get("stats", {})
    current_hp = stats.get("health", 100)
    max_hp = stats.get("max_health", 100)
    
    if current_hp >= max_hp:
        return {"message": "You're already at full health!", "healed": 0, "health": current_hp, "max_health": max_hp}
    
    heal_amount = int(max_hp * 0.25)
    new_hp = min(current_hp + heal_amount, max_hp)
    actual_healed = new_hp - current_hp
    
    await db.players.update_one(
        {"id": player_id},
        {
            "$set": {
                "stats.health": new_hp,
                f"restaurant_cooldowns.{restaurant_id}": datetime.utcnow().isoformat(),
            }
        }
    )
    
    return {
        "message": f"Ate at {restaurant['name']}! Healed {actual_healed} HP.",
        "restaurant_name": restaurant["name"],
        "healed": actual_healed,
        "health": new_hp,
        "max_health": max_hp,
    }


# ============== NIGHT CLUB SYSTEM ==============

NIGHTCLUB_NAMES = [
    "The Malibu Club", "Bahama Mamas", "Maisonette 9", "Hercules",
    "Vanilla Unicorn", "The Pink Swan", "Studio 54", "Tequi-la-la",
    "Club Pulse", "Neon Nights", "The Electric Banana", "Pitchers",
    "Ten Green Bottles", "Misty's", "The Strip Club", "Swingers",
]

NIGHTCLUB_ICONS = ["🎵", "🎶", "🪩", "💃", "🕺", "🍸", "🎤", "🌙"]


@api_router.get("/nightclubs/spawn")
async def spawn_nightclubs(latitude: float, longitude: float, player_level: int = 1):
    """Spawn nightclubs near a location — appears in every other radius area"""
    # Use a grid-based seed so the same area always gives the same result
    grid_lat = round(latitude * 200) / 200  # ~500m grid cells
    grid_lng = round(longitude * 200) / 200
    area_seed = hash(f"nightclub_{grid_lat}_{grid_lng}")
    rng = random.Random(area_seed)
    
    # Only spawn in ~50% of areas (every other radius)
    if rng.random() > 0.5:
        return []
    
    # Check if nightclubs already exist nearby in DB
    existing = await db.nightclubs.find({
        "latitude": {"$gte": latitude - 0.005, "$lte": latitude + 0.005},
        "longitude": {"$gte": longitude - 0.005, "$lte": longitude + 0.005},
    }).to_list(10)
    
    if existing:
        for nc in existing:
            nc.pop("_id", None)
        return existing
    
    # Spawn 1 nightclub in this area
    lat_offset = rng.uniform(-0.003, 0.003)
    lng_offset = rng.uniform(-0.003, 0.003)
    
    nightclub = {
        "id": str(uuid.uuid4()),
        "name": rng.choice(NIGHTCLUB_NAMES),
        "icon": rng.choice(NIGHTCLUB_ICONS),
        "latitude": latitude + lat_offset,
        "longitude": longitude + lng_offset,
        "energy_percent": 25,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.nightclubs.insert_one(nightclub)
    nightclub.pop("_id", None)
    return [nightclub]


@api_router.post("/nightclubs/{nightclub_id}/visit")
async def visit_nightclub(nightclub_id: str, player_id: str):
    """Player visits nightclub — restores 25% of max Energy. Cooldown: 10 minutes per nightclub."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    nightclub = await db.nightclubs.find_one({"id": nightclub_id})
    if not nightclub:
        raise HTTPException(status_code=404, detail="Nightclub not found")
    
    # Check cooldown (10 minutes per player per nightclub)
    last_visit = player.get("nightclub_cooldowns", {}).get(nightclub_id)
    if last_visit:
        try:
            last_dt = datetime.fromisoformat(last_visit)
            mins_since = (datetime.utcnow() - last_dt).total_seconds() / 60
            if mins_since < 10:
                remaining = round(10 - mins_since, 1)
                raise HTTPException(
                    status_code=400,
                    detail=f"You partied here recently! Come back in {remaining} minutes."
                )
        except (ValueError, TypeError):
            pass
    
    stats = player.get("stats", {})
    current_energy = stats.get("energy", 100)
    max_energy = stats.get("max_energy", 100)
    
    if current_energy >= max_energy:
        return {"message": "You're already at full energy!", "restored": 0, "energy": current_energy, "max_energy": max_energy}
    
    restore_amount = int(max_energy * 0.25)
    new_energy = min(current_energy + restore_amount, max_energy)
    actual_restored = new_energy - current_energy
    
    await db.players.update_one(
        {"id": player_id},
        {
            "$set": {
                "stats.energy": new_energy,
                f"nightclub_cooldowns.{nightclub_id}": datetime.utcnow().isoformat(),
            }
        }
    )
    
    return {
        "message": f"Partied at {nightclub['name']}! Restored {actual_restored} Energy.",
        "nightclub_name": nightclub["name"],
        "restored": actual_restored,
        "energy": new_energy,
        "max_energy": max_energy,
    }


# ============== BANK ROBBERY SYSTEM ==============

BANK_NAMES = [
    "Fleeca Bank", "Maze Bank", "Bank of Liberty", "Pacific Standard",
    "Blaine County Savings", "Lombank", "The Exchange", "Union Depository",
    "First National", "Capitol Trust", "Broker Savings", "Algonquin Trust",
]

BANK_ICONS = ["🏦", "💰", "🏛️", "💵"]


@api_router.get("/banks/spawn")
async def spawn_banks(latitude: float, longitude: float, player_level: int = 1):
    """Spawn banks near a location — very rare, only 25% of areas have one"""
    # Use a grid-based seed so the same area always gives the same result
    grid_lat = round(latitude * 200) / 200  # ~500m grid cells
    grid_lng = round(longitude * 200) / 200
    area_seed = hash(f"bank_{grid_lat}_{grid_lng}")
    rng = random.Random(area_seed)
    
    # Only spawn in ~25% of areas (banks are rare)
    if rng.random() > 0.25:
        return []
    
    # Check if banks already exist nearby in DB
    existing = await db.banks.find({
        "latitude": {"$gte": latitude - 0.005, "$lte": latitude + 0.005},
        "longitude": {"$gte": longitude - 0.005, "$lte": longitude + 0.005},
    }).to_list(10)
    
    if existing:
        for bank in existing:
            bank.pop("_id", None)
        return existing
    
    # Spawn 1 bank in this area
    lat_offset = rng.uniform(-0.003, 0.003)
    lng_offset = rng.uniform(-0.003, 0.003)
    
    # Bank rewards scale with player level
    base_reward = 500 + (player_level * 100)
    
    bank = {
        "id": str(uuid.uuid4()),
        "name": rng.choice(BANK_NAMES),
        "icon": rng.choice(BANK_ICONS),
        "latitude": latitude + lat_offset,
        "longitude": longitude + lng_offset,
        "min_reward": int(base_reward * 0.5),
        "max_reward": int(base_reward * 1.5),
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.banks.insert_one(bank)
    bank.pop("_id", None)
    return [bank]


@api_router.post("/banks/{bank_id}/rob")
async def rob_bank(bank_id: str, player_id: str):
    """Attempt to rob a bank — 50/50 chance of success or getting caught"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    bank = await db.banks.find_one({"id": bank_id})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    # Check cooldown (30 minutes per player per bank)
    cooldown_key = f"bank_cooldowns.{bank_id}"
    last_rob = player.get("bank_cooldowns", {}).get(bank_id)
    if last_rob:
        try:
            last_dt = datetime.fromisoformat(last_rob)
            mins_since = (datetime.utcnow() - last_dt).total_seconds() / 60
            if mins_since < 30:
                remaining = round(30 - mins_since, 1)
                raise HTTPException(
                    status_code=400,
                    detail=f"The heat is still on from your last job here! Wait {remaining} minutes."
                )
        except (ValueError, TypeError):
            pass
    
    player_level = player.get("level", 1)
    player_cash = player.get("cash", 0)
    
    # Calculate rewards based on player level
    base_reward = 500 + (player_level * 100)
    min_reward = int(base_reward * 0.5)
    max_reward = int(base_reward * 1.5)
    
    # 50/50 chance of success
    success = random.random() < 0.5
    
    if success:
        # Successful heist!
        loot = random.randint(min_reward, max_reward)
        new_cash = player_cash + loot
        
        await db.players.update_one(
            {"id": player_id},
            {
                "$set": {
                    "cash": new_cash,
                    f"bank_cooldowns.{bank_id}": datetime.utcnow().isoformat(),
                },
                "$inc": {"stats.banks_robbed": 1}
            }
        )
        
        return {
            "success": True,
            "message": f"💰 HEIST SUCCESS! You escaped from {bank['name']} with ${loot}!",
            "bank_name": bank["name"],
            "loot": loot,
            "cash": new_cash,
        }
    else:
        # Caught by cops!
        fine = random.randint(min_reward // 2, min_reward)
        # Can't go below 0
        new_cash = max(0, player_cash - fine)
        actual_fine = player_cash - new_cash
        
        await db.players.update_one(
            {"id": player_id},
            {
                "$set": {
                    "cash": new_cash,
                    f"bank_cooldowns.{bank_id}": datetime.utcnow().isoformat(),
                },
                "$inc": {"stats.times_caught": 1}
            }
        )
        
        return {
            "success": False,
            "message": f"🚔 BUSTED! The cops caught you at {bank['name']}! You paid ${actual_fine} in fines.",
            "bank_name": bank["name"],
            "fine": actual_fine,
            "cash": new_cash,
        }


# ============== CASTLE CANNON MINI-GAME SYSTEM ==============

CASTLE_NAMES = [
    "Fort Desperado", "Gangster's Keep", "Thug Stronghold", "Criminal Citadel",
    "Outlaw Fortress", "Bandit Bastion", "Villain's Tower", "Rogue Castle",
    "Shadow Fortress", "Dark Keep", "Iron Citadel", "Street Stronghold",
    "Urban Castle", "The Compound", "Gang Headquarters", "Mob Fortress",
]

GANG_MEMBER_NAMES = [
    "Vinnie", "Rocco", "Tony", "Sal", "Bruno", "Frankie", "Joey", "Mikey",
    "Paulie", "Carmine", "Enzo", "Luca", "Dante", "Marco", "Rico", "Vito",
]


def generate_castle_layout(difficulty: int, seed: int) -> dict:
    """Generate a randomized fort layout for the cannon mini-game"""
    rng = random.Random(seed)
    
    # Number of forts scales with difficulty (1-10)
    num_forts = max(1, min(10, difficulty))
    
    forts = []
    gang_members = []
    total_members = 0
    
    # Game area: x from 400 to 900 (forts on right side), y from 0 to 400 (ground at 400)
    spacing = 500 // (num_forts + 1)
    
    for i in range(num_forts):
        fort_x = 400 + spacing * (i + 1)
        
        # Random fort height (1-5 blocks tall)
        fort_height = rng.randint(1, min(5, 2 + difficulty // 2))
        
        # Fort width (1-3 blocks)
        fort_width = rng.randint(1, min(3, 1 + difficulty // 3))
        
        # Build the fort blocks
        blocks = []
        block_id = 0
        for row in range(fort_height):
            for col in range(fort_width):
                block = {
                    "id": f"fort_{i}_block_{block_id}",
                    "x": fort_x + col * 40,
                    "y": 360 - row * 40,  # Ground is at y=400, blocks are 40px
                    "width": 40,
                    "height": 40,
                    "destroyed": False,
                }
                blocks.append(block)
                block_id += 1
        
        # Number of gang members on this fort (1-3)
        num_members = rng.randint(1, min(3, 1 + difficulty // 3))
        
        # Place gang members on top of the fort
        for j in range(num_members):
            member_x = fort_x + (j * 35) + 5
            member_y = 360 - fort_height * 40 - 30  # On top of fort
            
            gang_member = {
                "id": f"member_{total_members}",
                "name": rng.choice(GANG_MEMBER_NAMES),
                "x": member_x,
                "y": member_y,
                "width": 30,
                "height": 30,
                "eliminated": False,
                "fort_index": i,
            }
            gang_members.append(gang_member)
            total_members += 1
        
        forts.append({
            "id": f"fort_{i}",
            "x": fort_x,
            "blocks": blocks,
            "height": fort_height,
            "width": fort_width,
        })
    
    return {
        "forts": forts,
        "gang_members": gang_members,
        "total_members": total_members,
        "difficulty": difficulty,
    }


@api_router.get("/castles/spawn")
async def spawn_castles(latitude: float, longitude: float, player_level: int = 1):
    """Spawn castles near a location — rare, only 20% of areas have one"""
    # Use a grid-based seed so the same area always gives the same result
    grid_lat = round(latitude * 150) / 150  # ~700m grid cells
    grid_lng = round(longitude * 150) / 150
    area_seed = hash(f"castle_{grid_lat}_{grid_lng}")
    rng = random.Random(area_seed)
    
    # Only spawn in ~20% of areas (castles are rare)
    if rng.random() > 0.20:
        return []
    
    # Check if castles already exist nearby in DB
    existing = await db.castles.find({
        "latitude": {"$gte": latitude - 0.006, "$lte": latitude + 0.006},
        "longitude": {"$gte": longitude - 0.006, "$lte": longitude + 0.006},
    }).to_list(10)
    
    if existing:
        for castle in existing:
            castle.pop("_id", None)
        return existing
    
    # Spawn 1 castle in this area
    lat_offset = rng.uniform(-0.004, 0.004)
    lng_offset = rng.uniform(-0.004, 0.004)
    
    # Difficulty scales with player level (1-10)
    difficulty = min(10, max(1, (player_level // 5) + rng.randint(1, 3)))
    
    # Cash reward scales with difficulty
    base_reward = 200 + (difficulty * 150) + (player_level * 50)
    
    castle = {
        "id": str(uuid.uuid4()),
        "name": rng.choice(CASTLE_NAMES),
        "latitude": latitude + lat_offset,
        "longitude": longitude + lng_offset,
        "difficulty": difficulty,
        "min_reward": int(base_reward * 0.7),
        "max_reward": int(base_reward * 1.3),
        "xp_reward": 25,
        "rep_reward": 5,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.castles.insert_one(castle)
    castle.pop("_id", None)
    return [castle]


@api_router.get("/minigames/cooldowns/{player_id}")
async def get_minigame_cooldowns(player_id: str):
    """Get all active cooldowns for mini-games (castles and car chases)"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    cooldowns = {}
    now = datetime.utcnow()
    cooldown_duration = 900  # 15 minutes in seconds
    
    # Get castle cooldowns
    castle_cooldowns = player.get("castle_cooldowns", {})
    for castle_id, last_attempt in castle_cooldowns.items():
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            secs_since = (now - last_dt).total_seconds()
            if secs_since < cooldown_duration:
                remaining = int(cooldown_duration - secs_since)
                cooldowns[f"castle_{castle_id}"] = {
                    "type": "castle",
                    "marker_id": castle_id,
                    "remaining_seconds": remaining,
                    "expires_at": (last_dt + timedelta(seconds=cooldown_duration)).isoformat(),
                }
        except (ValueError, TypeError):
            pass
    
    # Get car chase cooldowns
    carchase_cooldowns = player.get("carchase_cooldowns", {})
    for chase_id, last_attempt in carchase_cooldowns.items():
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            secs_since = (now - last_dt).total_seconds()
            if secs_since < cooldown_duration:
                remaining = int(cooldown_duration - secs_since)
                cooldowns[f"carchase_{chase_id}"] = {
                    "type": "carchase",
                    "marker_id": chase_id,
                    "remaining_seconds": remaining,
                    "expires_at": (last_dt + timedelta(seconds=cooldown_duration)).isoformat(),
                }
        except (ValueError, TypeError):
            pass
    
    return cooldowns


@api_router.post("/castles/{castle_id}/start")
async def start_castle_minigame(castle_id: str, player_id: str):
    """Start a castle cannon mini-game and return the layout"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    castle = await db.castles.find_one({"id": castle_id})
    if not castle:
        raise HTTPException(status_code=404, detail="Castle not found")
    
    # Check cooldown (15 minutes per player per castle)
    cooldown_key = f"castle_cooldowns.{castle_id}"
    last_attempt = player.get("castle_cooldowns", {}).get(castle_id)
    if last_attempt:
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            secs_since = (datetime.utcnow() - last_dt).total_seconds()
            if secs_since < 900:  # 15 minutes = 900 seconds
                remaining_secs = int(900 - secs_since)
                mins = remaining_secs // 60
                secs = remaining_secs % 60
                raise HTTPException(
                    status_code=400,
                    detail=f"The fortress is on high alert! Wait {mins}m {secs}s before attacking again."
                )
        except (ValueError, TypeError):
            pass
    
    # Generate a unique layout for this attempt
    game_seed = hash(f"{castle_id}_{player_id}_{datetime.utcnow().timestamp()}")
    layout = generate_castle_layout(castle["difficulty"], game_seed)
    
    # Create game session with exactly 3 shots
    game_session = {
        "id": str(uuid.uuid4()),
        "castle_id": castle_id,
        "player_id": player_id,
        "castle_name": castle["name"],
        "difficulty": castle["difficulty"],
        "layout": layout,
        "shots_remaining": 3,  # Always exactly 3 shots
        "shots_fired": [],
        "members_eliminated": 0,
        "total_members": layout["total_members"],
        "status": "active",
        "min_reward": castle.get("min_reward", 500),
        "max_reward": castle.get("max_reward", 1000),
        "xp_reward": castle.get("xp_reward", 25),
        "rep_reward": castle.get("rep_reward", 5),
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.castle_games.insert_one(game_session)
    game_session.pop("_id", None)
    
    return game_session


@api_router.post("/castles/start-random")
async def start_random_castle_game(player_id: str, castle_id: str = None):
    """Start a random castle game from the map - picks a random difficulty level"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Check cooldown if castle_id provided
    if castle_id:
        last_attempt = player.get("castle_cooldowns", {}).get(castle_id)
        if last_attempt:
            try:
                last_dt = datetime.fromisoformat(last_attempt)
                secs_since = (datetime.utcnow() - last_dt).total_seconds()
                if secs_since < 900:  # 15 minutes
                    remaining_secs = int(900 - secs_since)
                    mins = remaining_secs // 60
                    secs = remaining_secs % 60
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cooldown active! Wait {mins}m {secs}s"
                    )
            except (ValueError, TypeError):
                pass
    
    # Pick random difficulty 1-10
    random_level = random.randint(1, 10)
    
    # Level-based rewards
    level_rewards = {
        1: {"min": 25, "max": 50, "xp": 12, "rep": 2},
        2: {"min": 35, "max": 70, "xp": 18, "rep": 3},
        3: {"min": 50, "max": 100, "xp": 25, "rep": 4},
        4: {"min": 75, "max": 150, "xp": 35, "rep": 5},
        5: {"min": 100, "max": 200, "xp": 50, "rep": 6},
        6: {"min": 125, "max": 250, "xp": 75, "rep": 7},
        7: {"min": 175, "max": 350, "xp": 100, "rep": 8},
        8: {"min": 225, "max": 450, "xp": 125, "rep": 9},
        9: {"min": 300, "max": 600, "xp": 185, "rep": 10},
        10: {"min": 500, "max": 1000, "xp": 250, "rep": 15},
    }
    rewards = level_rewards.get(random_level, level_rewards[5])
    
    # Create game session
    game_session = {
        "id": str(uuid.uuid4()),
        "castle_id": castle_id or f"random_{str(uuid.uuid4())[:8]}",
        "player_id": player_id,
        "castle_name": f"Random Fortress Lv.{random_level}",
        "difficulty": random_level,
        "random_level": random_level,
        "status": "active",
        "min_reward": rewards["min"],
        "max_reward": rewards["max"],
        "xp_reward": rewards["xp"],
        "rep_reward": rewards["rep"],
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.castle_games.insert_one(game_session)
    game_session.pop("_id", None)
    
    return game_session


@api_router.post("/castles/game/{game_id}/complete")
async def complete_castle_game(game_id: str, members_eliminated: int, won: bool):
    """Complete a castle mini-game and award rewards if won"""
    game = await db.castle_games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    if game["status"] != "active":
        raise HTTPException(status_code=400, detail="Game already completed")
    
    player = await db.players.find_one({"id": game["player_id"]})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    castle_id = game["castle_id"]
    
    # Update game status
    await db.castle_games.update_one(
        {"id": game_id},
        {"$set": {
            "status": "completed",
            "won": won,
            "members_eliminated": members_eliminated,
            "completed_at": datetime.utcnow().isoformat(),
        }}
    )
    
    # Set cooldown regardless of win/lose
    await db.players.update_one(
        {"id": game["player_id"]},
        {"$set": {f"castle_cooldowns.{castle_id}": datetime.utcnow().isoformat()}}
    )
    
    if won:
        # Calculate rewards based on difficulty and members eliminated
        difficulty = game["difficulty"]
        total_members = game["total_members"]
        
        # Cash scales with difficulty
        base_cash = random.randint(game["min_reward"], game["max_reward"])
        cash_reward = base_cash
        
        xp_reward = game["xp_reward"]
        rep_reward = game["rep_reward"]
        
        # Update player
        await db.players.update_one(
            {"id": game["player_id"]},
            {
                "$inc": {
                    "cash": cash_reward,
                    "xp": xp_reward,
                    "reputation": rep_reward,
                    "stats.castles_conquered": 1,
                }
            }
        )
        
        # Get updated player
        updated_player = await db.players.find_one({"id": game["player_id"]})
        
        return {
            "success": True,
            "won": True,
            "message": f"🏰 VICTORY! You conquered {game['castle_name']}!",
            "castle_name": game["castle_name"],
            "members_eliminated": members_eliminated,
            "total_members": total_members,
            "rewards": {
                "cash": cash_reward,
                "xp": xp_reward,
                "reputation": rep_reward,
            },
            "cash": updated_player.get("cash", 0),
        }
    else:
        return {
            "success": True,
            "won": False,
            "message": f"💥 DEFEAT! The gang at {game['castle_name']} held their ground!",
            "castle_name": game["castle_name"],
            "members_eliminated": members_eliminated,
            "total_members": game["total_members"],
            "rewards": None,
        }


# ============== CAR CHASE MINI-GAME ==============

CAR_CHASE_NAMES = [
    "Highway Pursuit", "Downtown Escape", "Bridge Run", "Tunnel Chase",
    "Industrial Zone", "Harbor Highway", "City Center", "Mountain Pass",
    "Airport Freeway", "Strip Mile", "Back Alley Run", "Riverside Chase"
]

@api_router.get("/car-chases/spawn")
async def spawn_car_chases(latitude: float, longitude: float, player_level: int = 1):
    """Spawn car chase events near a location — 25% of areas have one"""
    grid_lat = round(latitude * 150) / 150
    grid_lng = round(longitude * 150) / 150
    area_seed = hash(f"carchase_{grid_lat}_{grid_lng}")
    rng = random.Random(area_seed)
    
    # 25% chance of car chase event in an area
    if rng.random() > 0.25:
        return []
    
    # Check if car chase already exists nearby
    existing = await db.car_chases.find({
        "latitude": {"$gte": latitude - 0.005, "$lte": latitude + 0.005},
        "longitude": {"$gte": longitude - 0.005, "$lte": longitude + 0.005},
    }).to_list(10)
    
    if existing:
        for chase in existing:
            chase.pop("_id", None)
        return existing
    
    lat_offset = rng.uniform(-0.004, 0.004)
    lng_offset = rng.uniform(-0.004, 0.004)
    
    # Difficulty scales with player level (1-10)
    difficulty = min(10, max(1, (player_level // 5) + rng.randint(1, 3)))
    
    # Rewards scale with difficulty
    base_cash = 150 + (difficulty * 100) + (player_level * 30)
    
    car_chase = {
        "id": str(uuid.uuid4()),
        "name": rng.choice(CAR_CHASE_NAMES),
        "latitude": latitude + lat_offset,
        "longitude": longitude + lng_offset,
        "difficulty": difficulty,
        "min_reward": int(base_cash * 0.8),
        "max_reward": int(base_cash * 1.5),
        "xp_reward": 20 + (difficulty * 5),
        "rep_reward": 3 + difficulty,
        "county_line_distance": 5000 + (difficulty * 1000),  # Distance to win
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.car_chases.insert_one(car_chase)
    car_chase.pop("_id", None)
    return [car_chase]


@api_router.post("/car-chases/{chase_id}/start")
async def start_car_chase(chase_id: str, player_id: str):
    """Start a car chase mini-game"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    car_chase = await db.car_chases.find_one({"id": chase_id})
    if not car_chase:
        raise HTTPException(status_code=404, detail="Car chase event not found")
    
    # Check cooldown (15 minutes per player per chase)
    last_attempt = player.get("carchase_cooldowns", {}).get(chase_id)
    if last_attempt:
        try:
            last_time = datetime.fromisoformat(last_attempt)
            secs_since = (datetime.utcnow() - last_time).total_seconds()
            if secs_since < 900:  # 15 min = 900 seconds
                remaining_secs = int(900 - secs_since)
                mins = remaining_secs // 60
                secs = remaining_secs % 60
                raise HTTPException(
                    status_code=400, 
                    detail=f"Police are patrolling the area! Wait {mins}m {secs}s before another chase."
                )
        except (ValueError, TypeError):
            pass
    
    # Create game session
    game = {
        "id": str(uuid.uuid4()),
        "player_id": player_id,
        "chase_id": chase_id,
        "chase_name": car_chase["name"],
        "difficulty": car_chase["difficulty"],
        "county_line_distance": car_chase["county_line_distance"],
        "min_reward": car_chase["min_reward"],
        "max_reward": car_chase["max_reward"],
        "xp_reward": car_chase["xp_reward"],
        "rep_reward": car_chase["rep_reward"],
        "status": "active",
        "started_at": datetime.utcnow().isoformat(),
    }
    
    await db.car_chase_games.insert_one(game)
    game.pop("_id", None)
    
    return {
        "game_id": game["id"],
        "chase_name": car_chase["name"],
        "difficulty": car_chase["difficulty"],
        "county_line_distance": car_chase["county_line_distance"],
    }


@api_router.post("/car-chases/game/{game_id}/complete")
async def complete_car_chase(game_id: str, won: bool, distance_traveled: int):
    """Complete a car chase and award rewards if won"""
    game = await db.car_chase_games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    if game["status"] != "active":
        raise HTTPException(status_code=400, detail="Game already completed")
    
    player = await db.players.find_one({"id": game["player_id"]})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    chase_id = game["chase_id"]
    
    # Update game status
    await db.car_chase_games.update_one(
        {"id": game_id},
        {"$set": {
            "status": "completed",
            "won": won,
            "distance_traveled": distance_traveled,
            "completed_at": datetime.utcnow().isoformat(),
        }}
    )
    
    # Set cooldown
    await db.players.update_one(
        {"id": game["player_id"]},
        {"$set": {f"carchase_cooldowns.{chase_id}": datetime.utcnow().isoformat()}}
    )
    
    if won:
        # Calculate rewards based on difficulty and distance
        difficulty = game["difficulty"]
        county_line = game["county_line_distance"]
        
        # Base reward + bonus for distance traveled
        distance_bonus = min(1.5, distance_traveled / county_line)
        base_cash = random.randint(game["min_reward"], game["max_reward"])
        cash_reward = int(base_cash * distance_bonus)
        
        xp_reward = int(game["xp_reward"] * distance_bonus)
        rep_reward = int(game["rep_reward"] * distance_bonus)
        
        await db.players.update_one(
            {"id": game["player_id"]},
            {"$inc": {"cash": cash_reward, "xp": xp_reward, "reputation": rep_reward}}
        )
        
        updated_player = await db.players.find_one({"id": game["player_id"]})
        
        return {
            "success": True,
            "won": True,
            "message": f"🚗💨 ESCAPED! You outran the cops on {game['chase_name']}!",
            "chase_name": game["chase_name"],
            "distance_traveled": distance_traveled,
            "rewards": {
                "cash": cash_reward,
                "xp": xp_reward,
                "reputation": rep_reward,
            },
            "cash": updated_player.get("cash", 0),
        }
    else:
        return {
            "success": True,
            "won": False,
            "message": f"🚔 BUSTED! The cops caught you on {game['chase_name']}!",
            "chase_name": game["chase_name"],
            "distance_traveled": distance_traveled,
            "rewards": None,
        }


# ============== EQUIPMENT ENDPOINTS ==============

@api_router.get("/items")
async def get_all_items():
    """Get all available items in the game"""
    return ALL_ITEMS

@api_router.get("/items/{item_id}")
async def get_item(item_id: str):
    """Get item details by ID"""
    item = ALL_ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@api_router.get("/players/{player_id}/inventory-details")
async def get_player_inventory_details(player_id: str):
    """Get player's inventory with full item details including durability"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    inventory = player.get("inventory", [])
    inventory = [migrate_inventory_item(item) for item in inventory]
    
    inventory_items = []
    for idx, inv_item in enumerate(inventory):
        item_id = inv_item.get("item_id") if isinstance(inv_item, dict) else inv_item
        item = ALL_ITEMS.get(item_id)
        if item:
            # Add durability info to item
            item_with_durability = {**item}
            item_with_durability["durability"] = inv_item.get("durability", 100)
            item_with_durability["max_durability"] = inv_item.get("max_durability", get_max_durability(item_id))
            item_with_durability["is_broken"] = inv_item.get("durability", 100) <= 0
            item_with_durability["inventory_index"] = idx
            inventory_items.append(item_with_durability)
    return inventory_items

@api_router.get("/players/{player_id}/equipment-details")
async def get_player_equipment_details(player_id: str):
    """Get player's equipped items with full details including durability"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    equipment = player.get("equipment", {})
    inventory = player.get("inventory", [])
    inventory = [migrate_inventory_item(item) for item in inventory]
    
    equipped = {}
    for slot, item_id in equipment.items():
        if item_id:
            item = ALL_ITEMS.get(item_id)
            if item:
                # Find durability from inventory for equipped item
                durability = 100
                max_durability = get_max_durability(item_id)
                for inv_item in inventory:
                    if inv_item.get("item_id") == item_id:
                        durability = inv_item.get("durability", 100)
                        max_durability = inv_item.get("max_durability", max_durability)
                        break
                
                equipped[slot] = {
                    **item,
                    "durability": durability,
                    "max_durability": max_durability,
                    "is_broken": durability <= 0
                }
            else:
                equipped[slot] = {"id": item_id, "name": "Unknown", "equipment_type": slot, "rarity": "common", "stats_bonus": {}, "description": "Unknown item", "durability": 100, "max_durability": 100, "is_broken": False}
        else:
            equipped[slot] = None
    return equipped

@api_router.delete("/players/{player_id}/inventory/{item_id}")
async def delete_item(player_id: str, item_id: str):
    """Delete/discard an item from player's inventory"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    inv = player.get("inventory", [])
    inv = [migrate_inventory_item(item) for item in inv]
    
    # Find item in inventory (now stored as dicts)
    item_index = None
    for idx, inv_item in enumerate(inv):
        i_id = inv_item.get("item_id") if isinstance(inv_item, dict) else inv_item
        if i_id == item_id:
            item_index = idx
            break
    
    if item_index is None:
        raise HTTPException(status_code=400, detail="Item not in inventory")
    
    inv.pop(item_index)
    await db.players.update_one({"id": player_id}, {"$set": {"inventory": inv}})
    
    item = ALL_ITEMS.get(item_id, {})
    return {"message": f"Discarded {item.get('name', 'item')}"}

@api_router.post("/players/{player_id}/inventory/{item_id}/sell")
async def sell_item(player_id: str, item_id: str):
    """Sell an item from player's inventory for cash (50% of item value)"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    inv = player.get("inventory", [])
    inv = [migrate_inventory_item(item) for item in inv]
    
    # Find item in inventory (now stored as dicts)
    item_index = None
    for idx, inv_item in enumerate(inv):
        i_id = inv_item.get("item_id") if isinstance(inv_item, dict) else inv_item
        if i_id == item_id:
            item_index = idx
            break
    
    if item_index is None:
        raise HTTPException(status_code=400, detail="Item not in inventory")
    
    item = ALL_ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item data not found")
    
    sell_price = max(1, item.get("value", 10) // 2)
    
    inv.pop(item_index)
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"inventory": inv}, "$inc": {"cash": sell_price}}
    )
    
    return {
        "message": f"Sold {item['name']} for ${sell_price}",
        "sell_price": sell_price,
        "item_name": item["name"],
    }


@api_router.post("/players/{player_id}/inventory/repair")
async def repair_item(player_id: str, item_index: int):
    """Repair an item in player's inventory (restores durability)"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    inv = player.get("inventory", [])
    
    # Migrate inventory if needed
    inv = [migrate_inventory_item(item) for item in inv]
    
    if item_index < 0 or item_index >= len(inv):
        raise HTTPException(status_code=400, detail="Invalid item index")
    
    inv_item = inv[item_index]
    item_id = inv_item.get("item_id") if isinstance(inv_item, dict) else inv_item
    current_durability = inv_item.get("durability", 100) if isinstance(inv_item, dict) else 100
    max_durability = get_max_durability(item_id)
    
    if current_durability >= max_durability:
        raise HTTPException(status_code=400, detail="Item is already at full durability")
    
    repair_cost = calculate_repair_cost(item_id, current_durability)
    
    if player.get("cash", 0) < repair_cost:
        raise HTTPException(status_code=400, detail=f"Not enough cash. Repair costs ${repair_cost}")
    
    # Repair the item
    inv[item_index] = create_inventory_item(item_id, max_durability)
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"inventory": inv}, "$inc": {"cash": -repair_cost}}
    )
    
    item = ALL_ITEMS.get(item_id, {})
    return {
        "message": f"Repaired {item.get('name', 'item')} for ${repair_cost}",
        "repair_cost": repair_cost,
        "item_name": item.get("name", "Unknown"),
        "new_durability": max_durability,
        "max_durability": max_durability,
    }


@api_router.get("/players/{player_id}/repair-costs")
async def get_repair_costs(player_id: str):
    """Get repair costs for all items in player's inventory"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    inv = player.get("inventory", [])
    inv = [migrate_inventory_item(item) for item in inv]
    
    repair_info = []
    for idx, inv_item in enumerate(inv):
        item_id = inv_item.get("item_id") if isinstance(inv_item, dict) else inv_item
        current_durability = inv_item.get("durability", 100) if isinstance(inv_item, dict) else 100
        max_durability = get_max_durability(item_id)
        
        item = ALL_ITEMS.get(item_id, {})
        repair_cost = calculate_repair_cost(item_id, current_durability) if current_durability < max_durability else 0
        
        repair_info.append({
            "index": idx,
            "item_id": item_id,
            "item_name": item.get("name", "Unknown"),
            "current_durability": current_durability,
            "max_durability": max_durability,
            "repair_cost": repair_cost,
            "is_broken": current_durability <= 0,
            "needs_repair": current_durability < max_durability,
        })
    
    return {"items": repair_info}


@api_router.post("/players/{player_id}/unequip")
async def unequip_item(player_id: str, slot: str):
    """Unequip an item from a slot"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if slot not in EQUIPMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid equipment slot")
    
    current_item = player.get("equipment", {}).get(slot)
    if not current_item:
        raise HTTPException(status_code=400, detail="Nothing equipped in that slot")
    
    # Migrate inventory and add unequipped item with durability preserved
    inventory = player.get("inventory", [])
    inventory = [migrate_inventory_item(item) for item in inventory]
    
    # Create inventory item for unequipped gear (preserving durability if item already in inv)
    unequipped_item = create_inventory_item(current_item)
    inventory.append(unequipped_item)
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {f"equipment.{slot}": None, "inventory": inventory}}
    )
    return {"message": f"Unequipped item from {slot}"}

@api_router.post("/players/{player_id}/buy-item")
async def buy_item(player_id: str, item_id: str):
    """Buy an item from the shop"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    item = ALL_ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if player.get("cash", 0) < item["value"]:
        raise HTTPException(status_code=400, detail="Not enough cash")
    
    if player.get("level", 1) < item["level_requirement"]:
        raise HTTPException(status_code=400, detail=f"Requires level {item['level_requirement']}")
    
    # Create inventory item with full durability
    new_item = create_inventory_item(item_id)
    
    await db.players.update_one(
        {"id": player_id},
        {"$inc": {"cash": -item["value"]}, "$push": {"inventory": new_item}}
    )
    return {"message": f"Purchased {item['name']}!", "item": item}

@api_router.get("/equipment/{equipment_id}")
async def get_equipment(equipment_id: str):
    """Get equipment details"""
    equipment = await db.equipment.find_one({"id": equipment_id})
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equipment

@api_router.post("/players/{player_id}/equip")
async def equip_item(player_id: str, equipment_id: str):
    """Equip an item"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    equipment = ALL_ITEMS.get(equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Migrate and check inventory
    inventory = player.get("inventory", [])
    inventory = [migrate_inventory_item(item) for item in inventory]
    
    # Find item in inventory (now stored as dicts)
    item_index = None
    for idx, inv_item in enumerate(inventory):
        i_id = inv_item.get("item_id") if isinstance(inv_item, dict) else inv_item
        if i_id == equipment_id:
            item_index = idx
            # Check if item is broken
            if is_item_broken(inv_item):
                raise HTTPException(status_code=400, detail="Cannot equip broken item. Repair it first!")
            break
    
    if item_index is None:
        raise HTTPException(status_code=400, detail="Item not in inventory")
    
    slot = equipment["equipment_type"]
    current_equipped = player["equipment"].get(slot)
    
    # Get the item being equipped (to preserve durability)
    equipped_item = inventory[item_index]
    
    # Remove item from inventory
    inventory.pop(item_index)
    
    # Move old item back to inventory if exists
    if current_equipped:
        # Find old item's durability in inventory (it might have been there before) or create new
        old_item_dur = None
        for inv_item in inventory:
            if inv_item.get("item_id") == current_equipped:
                old_item_dur = inv_item
                break
        if not old_item_dur:
            old_item_dur = create_inventory_item(current_equipped)
        inventory.append(old_item_dur)
    
    # Update equipment and inventory
    await db.players.update_one(
        {"id": player_id},
        {"$set": {f"equipment.{slot}": equipment_id, "inventory": inventory}}
    )
    
    return {"message": f"Equipped {equipment['name']}"}

# ============== CHAT ENDPOINTS ==============
@api_router.post("/chat")
async def send_chat_message(channel: str, player_id: str, message: str):
    """Send a chat message"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    chat_msg = ChatMessage(
        channel=channel,
        player_id=player_id,
        player_name=player["name"],
        message=message[:500]  # Limit message length
    )
    
    await db.chat_messages.insert_one(chat_msg.dict())
    return chat_msg

@api_router.get("/chat/{channel}")
async def get_chat_messages(channel: str, limit: int = 50):
    """Get recent chat messages"""
    messages = await db.chat_messages.find({"channel": channel}).sort("timestamp", -1).limit(limit).to_list(limit)
    return list(reversed(messages))

# ============== SKILLS ENDPOINT ==============
@api_router.get("/skills")
async def get_all_skills():
    """Get all available skills with their details"""
    skills_list = []
    for skill_id, skill in SKILLS.items():
        skills_list.append({
            "id": skill_id,
            **skill
        })
    # Sort by unlock level
    skills_list.sort(key=lambda s: s["unlock_level"])
    return skills_list

@api_router.get("/players/{player_id}/skills")
async def get_player_skills(player_id: str):
    """Get player's owned skills and equipped skills"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Get owned skills (default to starter skills for backwards compatibility)
    owned_skills = player.get("owned_skills", player.get("skills", ["heavy_strike", "quick_shot"]))
    equipped_skills = player.get("equipped_skills", owned_skills[:4])
    player_level = player.get("level", 1)
    
    # Build response with all skills info
    all_skills = []
    for skill_id, skill in SKILLS.items():
        is_owned = skill_id in owned_skills
        is_equipped = skill_id in equipped_skills
        can_unlock = player_level >= skill["unlock_level"]
        
        all_skills.append({
            "id": skill_id,
            **skill,
            "owned": is_owned,
            "equipped": is_equipped,
            "can_unlock": can_unlock,
        })
    
    # Sort: equipped first, then owned, then by unlock_level
    all_skills.sort(key=lambda s: (0 if s["equipped"] else 1, 0 if s["owned"] else 1, s["unlock_level"]))
    
    return {
        "skills": all_skills,
        "owned_skills": owned_skills,
        "equipped_skills": equipped_skills,
        "max_equipped": 4
    }

@api_router.get("/shop/skills")
async def get_skill_shop(player_level: int = 1):
    """Get skills available to buy at the shop based on player level"""
    available_skills = []
    for skill_id, skill in SKILLS.items():
        # Only show skills that are at or below player level and have a value (can be purchased)
        if skill["unlock_level"] <= player_level and skill.get("value", 0) > 0:
            available_skills.append({
                "id": skill_id,
                **skill
            })
    
    # Sort by unlock level
    available_skills.sort(key=lambda s: s["unlock_level"])
    return available_skills

@api_router.post("/shop/buy-skill")
async def buy_skill(player_id: str, skill_id: str):
    """Buy a skill from the shop"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    skill = SKILLS.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check if player already owns the skill
    owned_skills = player.get("owned_skills", player.get("skills", ["heavy_strike", "quick_shot"]))
    if skill_id in owned_skills:
        raise HTTPException(status_code=400, detail="You already own this skill")
    
    # Check level requirement
    if player.get("level", 1) < skill["unlock_level"]:
        raise HTTPException(status_code=400, detail=f"Requires level {skill['unlock_level']}")
    
    # Check if skill can be purchased (starter skills are free)
    skill_price = skill.get("value", 0)
    if skill_price <= 0:
        raise HTTPException(status_code=400, detail="This skill cannot be purchased")
    
    # Check cash
    if player.get("cash", 0) < skill_price:
        raise HTTPException(status_code=400, detail=f"Not enough cash. Need ${skill_price}")
    
    # Purchase the skill
    await db.players.update_one(
        {"id": player_id},
        {
            "$inc": {"cash": -skill_price},
            "$push": {"owned_skills": skill_id}
        }
    )
    
    return {"message": f"Purchased {skill['name']}!", "skill": skill}

@api_router.post("/players/{player_id}/equip-skill")
async def equip_skill(player_id: str, skill_id: str):
    """Equip a skill (max 4 skills can be equipped)"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    skill = SKILLS.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check if player owns the skill
    owned_skills = player.get("owned_skills", player.get("skills", ["heavy_strike", "quick_shot"]))
    if skill_id not in owned_skills:
        raise HTTPException(status_code=400, detail="You don't own this skill")
    
    # Get current equipped skills
    equipped_skills = player.get("equipped_skills", owned_skills[:4])
    
    # Check if already equipped
    if skill_id in equipped_skills:
        raise HTTPException(status_code=400, detail="Skill is already equipped")
    
    # Check max equipped limit (4)
    if len(equipped_skills) >= 4:
        raise HTTPException(status_code=400, detail="Maximum 4 skills can be equipped. Unequip a skill first.")
    
    # Equip the skill
    await db.players.update_one(
        {"id": player_id},
        {"$push": {"equipped_skills": skill_id}}
    )
    
    return {"message": f"Equipped {skill['name']}!"}

@api_router.post("/players/{player_id}/unequip-skill")
async def unequip_skill(player_id: str, skill_id: str):
    """Unequip a skill"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    skill = SKILLS.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Get current equipped skills
    equipped_skills = player.get("equipped_skills", [])
    
    # Check if equipped
    if skill_id not in equipped_skills:
        raise HTTPException(status_code=400, detail="Skill is not equipped")
    
    # Must have at least 1 skill equipped
    if len(equipped_skills) <= 1:
        raise HTTPException(status_code=400, detail="You must have at least 1 skill equipped")
    
    # Unequip the skill
    await db.players.update_one(
        {"id": player_id},
        {"$pull": {"equipped_skills": skill_id}}
    )
    
    return {"message": f"Unequipped {skill['name']}!"}

# ============== CONSUMABLE SHOP ENDPOINTS ==============

@api_router.get("/shop/consumables")
async def get_consumable_shop():
    """Get all consumable items available in the shop"""
    return list(CONSUMABLE_ITEMS.values())

@api_router.post("/shop/buy-consumable")
async def buy_consumable(player_id: str, item_id: str):
    """Buy a consumable item and apply its effects immediately"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    item = CONSUMABLE_ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Consumable item not found")
    
    if player.get("cash", 0) < item["price"]:
        raise HTTPException(status_code=400, detail="Not enough cash")
    
    if player.get("level", 1) < item["level_requirement"]:
        raise HTTPException(status_code=400, detail=f"Requires level {item['level_requirement']}")
    
    # Build the update operations
    update_ops = {"$inc": {"cash": -item["price"]}}
    effect = item["effect"]
    messages = []
    
    stats = player.get("stats", {})
    
    # Health restore
    if "restore_health" in effect:
        amount = effect["restore_health"]
        current_hp = stats.get("health", 0)
        max_hp = stats.get("max_health", 100)
        new_hp = min(current_hp + amount, max_hp)
        restored = new_hp - current_hp
        update_ops.setdefault("$set", {})["stats.health"] = new_hp
        messages.append(f"Restored {restored} HP")
    
    if effect.get("restore_health_full"):
        max_hp = stats.get("max_health", 100)
        update_ops.setdefault("$set", {})["stats.health"] = max_hp
        messages.append("Fully restored HP")
    
    # Energy restore
    if "restore_energy" in effect:
        amount = effect["restore_energy"]
        current_en = stats.get("energy", 0)
        max_en = stats.get("max_energy", 100)
        new_en = min(current_en + amount, max_en)
        restored = new_en - current_en
        update_ops.setdefault("$set", {})["stats.energy"] = new_en
        messages.append(f"Restored {restored} Energy")
    
    if effect.get("restore_energy_full"):
        max_en = stats.get("max_energy", 100)
        update_ops.setdefault("$set", {})["stats.energy"] = max_en
        messages.append("Fully restored Energy")
    
    # Temporary max health boost (flat amount - legacy)
    if "temp_max_health" in effect:
        amount = effect["temp_max_health"]
        duration = effect.get("duration_battles", 5)
        buff = {
            "id": f"{item_id}_{str(uuid.uuid4())[:8]}",
            "item_id": item_id,
            "name": item["name"],
            "type": "max_health",
            "amount": amount,
            "percent": 0,
            "battles_remaining": duration,
            "icon": "heart",
        }
        update_ops.setdefault("$push", {})["active_buffs"] = buff
        messages.append(f"+{amount} Max HP for {duration} battles")
    
    # Temporary max health boost (percentage-based)
    if "temp_max_health_percent" in effect:
        percent = effect["temp_max_health_percent"]
        duration = effect.get("duration_battles", 5)
        # Calculate actual amount based on player's base max health
        base_max_hp = player.get("stats", {}).get("max_health", 100)
        amount = int(base_max_hp * percent)
        percent_display = int(percent * 100)
        buff = {
            "id": f"{item_id}_{str(uuid.uuid4())[:8]}",
            "item_id": item_id,
            "name": item["name"],
            "type": "max_health",
            "amount": amount,
            "percent": percent,
            "battles_remaining": duration,
            "icon": "heart",
        }
        update_ops.setdefault("$push", {})["active_buffs"] = buff
        if percent >= 1.0:
            messages.append(f"DOUBLED Max HP (+{amount}) for {duration} battles!")
        else:
            messages.append(f"+{percent_display}% Max HP (+{amount}) for {duration} battles")
    
    # Temporary max energy boost (flat amount - legacy)
    if "temp_max_energy" in effect:
        amount = effect["temp_max_energy"]
        duration = effect.get("duration_battles", 5)
        buff = {
            "id": f"{item_id}_{str(uuid.uuid4())[:8]}",
            "item_id": item_id,
            "name": item["name"],
            "type": "max_energy",
            "amount": amount,
            "percent": 0,
            "battles_remaining": duration,
            "icon": "flash",
        }
        update_ops.setdefault("$push", {})["active_buffs"] = buff
        messages.append(f"+{amount} Max Energy for {duration} battles")
    
    # Temporary max energy boost (percentage-based)
    if "temp_max_energy_percent" in effect:
        percent = effect["temp_max_energy_percent"]
        duration = effect.get("duration_battles", 5)
        # Calculate actual amount based on player's base max energy
        base_max_energy = player.get("stats", {}).get("max_energy", 100)
        amount = int(base_max_energy * percent)
        percent_display = int(percent * 100)
        buff = {
            "id": f"{item_id}_{str(uuid.uuid4())[:8]}",
            "item_id": item_id,
            "name": item["name"],
            "type": "max_energy",
            "amount": amount,
            "percent": percent,
            "battles_remaining": duration,
            "icon": "flash",
        }
        update_ops.setdefault("$push", {})["active_buffs"] = buff
        if percent >= 1.0:
            messages.append(f"DOUBLED Max Energy (+{amount}) for {duration} battles!")
        else:
            messages.append(f"+{percent_display}% Max Energy (+{amount}) for {duration} battles")
    
    # Temporary health boost (adds to current HP, capped at 2x max)
    if "temp_health_percent" in effect:
        percent = effect["temp_health_percent"]
        max_hp = player.get("stats", {}).get("max_health", 100)
        current_hp = player.get("stats", {}).get("health", max_hp)
        bonus = int(max_hp * percent)
        # Cap at 2x max health (temporary overheal)
        new_hp = min(current_hp + bonus, max_hp * 2)
        actual_heal = new_hp - current_hp
        update_ops.setdefault("$set", {})["stats.health"] = new_hp
        percent_display = int(percent * 100)
        if new_hp > max_hp:
            messages.append(f"+{actual_heal} HP! (Overhealed to {new_hp}/{max_hp})")
        else:
            messages.append(f"+{actual_heal} HP! ({new_hp}/{max_hp})")
    
    # Temporary energy boost (adds to current Energy, capped at 2x max)
    if "temp_energy_percent" in effect:
        percent = effect["temp_energy_percent"]
        max_energy = player.get("stats", {}).get("max_energy", 100)
        current_energy = player.get("stats", {}).get("energy", max_energy)
        bonus = int(max_energy * percent)
        # Cap at 2x max energy (temporary overcharge)
        new_energy = min(current_energy + bonus, max_energy * 2)
        actual_restore = new_energy - current_energy
        update_ops.setdefault("$set", {})["stats.energy"] = new_energy
        percent_display = int(percent * 100)
        if new_energy > max_energy:
            messages.append(f"+{actual_restore} Energy! (Overcharged to {new_energy}/{max_energy})")
        else:
            messages.append(f"+{actual_restore} Energy! ({new_energy}/{max_energy})")
    
    await db.players.update_one({"id": player_id}, update_ops)
    
    # Fetch updated player
    updated_player = await db.players.find_one({"id": player_id})
    safe_player = serialize_doc(updated_player)
    safe_player.pop("password_hash", None)
    safe_player.pop("profile_pic", None)
    
    return {
        "message": f"Used {item['name']}!",
        "effects": messages,
        "player": safe_player,
    }

@api_router.get("/players/{player_id}/buffs")
async def get_player_buffs(player_id: str):
    """Get all active buffs for a player"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player.get("active_buffs", [])

# ============== TERRITORY ENDPOINTS ==============

TERRITORY_CELL_SIZE_M = 338  # Equal size for all territories (meters)
UNCLAIMED_COLOR = "#3d3d3d"  # Dark gray for all unclaimed territories
CLAIMED_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#9b59b6", "#f39c12",
    "#1abc9c", "#e91e63", "#ff5722", "#00bcd4", "#8bc34a",
    "#ff9800", "#673ab7", "#009688", "#c62828", "#1565c0",
    "#2e7d32", "#6a1b9a", "#ef6c00", "#795548", "#607d8b",
]

def get_owner_color(player_id: str) -> str:
    """Assign a consistent bright color to a player for their territories"""
    return CLAIMED_COLORS[hash(player_id) % len(CLAIMED_COLORS)]

def generate_territory_cell(row: int, col: int, cell_lat: float, cell_lng: float, player_level: int = 1):
    """Generate a single territory for a grid cell"""
    import math
    
    # Deterministic seed from grid position
    seed = abs(row * 100003 + col * 200017) % 2147483647
    rng = random.Random(seed)
    
    # Territory bounds (tiles perfectly, no gaps, no overlaps)
    south = row * cell_lat
    north = (row + 1) * cell_lat
    west = col * cell_lng
    east = (col + 1) * cell_lng
    
    # Center point
    t_lat = (south + north) / 2
    t_lng = (west + east) / 2
    
    # Name and boss from seed
    name_idx = seed % len(TERRITORY_NAMES)
    boss_idx = seed % len(TERRITORY_BOSS_NAMES)
    
    # Boss scales with zone difficulty (reduced stats for easier conquering)
    zone_level = max(1, player_level + rng.randint(-2, 2))
    boss_hp = 40 + zone_level * 8  # Reduced from 60 + 15*level
    boss_atk = 5 + zone_level * 2  # Reduced from 8 + 3*level
    boss_def = 3 + zone_level * 1  # Reduced from 5 + 2*level
    daily_income = 20 + zone_level * 10
    
    territory_id = f"terr_{row}_{col}"
    return {
        "id": territory_id,
        "grid_row": row,
        "grid_col": col,
        "name": TERRITORY_NAMES[name_idx],
        "location": {"latitude": round(t_lat, 6), "longitude": round(t_lng, 6)},
        "size": TERRITORY_CELL_SIZE_M,
        "bounds": {
            "south": round(south, 6),
            "north": round(north, 6),
            "west": round(west, 6),
            "east": round(east, 6),
        },
        "color": UNCLAIMED_COLOR,
        "boss": {
            "name": TERRITORY_BOSS_NAMES[boss_idx],
            "level": zone_level,
            "health": boss_hp,
            "max_health": boss_hp,
            "attack": boss_atk,
            "defense": boss_def,
        },
        "rewards": {
            "passive_income": daily_income,
        },
        "owner_id": None,
        "owner_name": None,
        "owner_pic": None,
    }

@api_router.get("/territories/nearby")
async def get_nearby_territories(latitude: float, longitude: float, player_level: int = 1):
    """Get or create territories near a location as a tiled grid of equal squares"""
    import math
    LAT_M = 111000.0
    LNG_M = math.cos(math.radians(latitude)) * 111000.0
    
    cell_lat = TERRITORY_CELL_SIZE_M / LAT_M
    cell_lng = TERRITORY_CELL_SIZE_M / LNG_M
    
    # Find the grid cell the player is in
    center_row = int(latitude / cell_lat)
    center_col = int(longitude / cell_lng)
    # Handle negative coordinates
    if longitude < 0:
        center_col -= 1
    
    # Generate 5x5 grid of territory IDs around player
    territory_ids = []
    cell_map = {}
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            row = center_row + dr
            col = center_col + dc
            tid = f"terr_{row}_{col}"
            territory_ids.append(tid)
            cell_map[tid] = (row, col)
    
    # Fetch existing territories from DB
    existing = await db.territories.find({"id": {"$in": territory_ids}}).to_list(length=25)
    existing_ids = {t["id"] for t in existing}
    
    # Generate missing territories
    new_territories = []
    for tid, (row, col) in cell_map.items():
        if tid not in existing_ids:
            t = generate_territory_cell(row, col, cell_lat, cell_lng, player_level)
            t["created_at"] = datetime.utcnow().isoformat()
            t["last_income_collected"] = None
            new_territories.append(t)
    
    if new_territories:
        await db.territories.insert_many(new_territories)
    
    # Fetch all territories for this area
    all_terrs = await db.territories.find({"id": {"$in": territory_ids}}).to_list(length=25)
    
    # Sync owner_pic for territories that have owners but missing pic
    for terr in all_terrs:
        if terr.get("owner_id") and not terr.get("owner_pic"):
            owner = await db.players.find_one({"id": terr["owner_id"]}, {"profile_pic": 1})
            if owner and owner.get("profile_pic"):
                # Update the territory with the owner's current profile pic
                await db.territories.update_one(
                    {"id": terr["id"]},
                    {"$set": {"owner_pic": owner["profile_pic"]}}
                )
                terr["owner_pic"] = owner["profile_pic"]
    
    return [serialize_doc(t) for t in all_terrs]


@api_router.post("/territories/collect-income/{player_id}")
async def collect_territory_income(player_id: str):
    """Collect daily income from all owned territories"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    owned = await db.territories.find({"owner_id": player_id}).to_list(100)
    if not owned:
        return {"message": "You don't own any territories", "income": 0, "territories": 0}
    
    now = datetime.utcnow()
    total_income = 0
    territories_paid = 0
    
    for t in owned:
        last_collected = t.get("last_income_collected")
        if last_collected:
            try:
                last_dt = datetime.fromisoformat(last_collected)
                hours_since = (now - last_dt).total_seconds() / 3600
                if hours_since < 24:
                    continue  # Not ready yet
            except (ValueError, TypeError):
                pass
        
        income = t.get("passive_income", 30)
        total_income += income
        territories_paid += 1
        
        await db.territories.update_one(
            {"id": t["id"]},
            {"$set": {"last_income_collected": now.isoformat()}}
        )
    
    if total_income > 0:
        await db.players.update_one(
            {"id": player_id},
            {"$inc": {"cash": total_income}}
        )
    
    return {
        "message": f"Collected ${total_income} from {territories_paid} territories!" if total_income > 0 else "No income ready to collect yet. Come back in 24 hours.",
        "income": total_income,
        "territories": territories_paid,
    }


@api_router.get("/territories/income-preview/{player_id}")
async def territory_income_preview(player_id: str):
    """Preview available income without collecting it"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    owned = await db.territories.find({"owner_id": player_id}).to_list(100)
    if not owned:
        return {"available_income": 0, "ready_territories": 0, "total_territories": 0, "next_collection_hours": 0}
    
    now = datetime.utcnow()
    available_income = 0
    ready_territories = 0
    min_hours_remaining = 999
    
    for t in owned:
        income = t.get("passive_income", 30)
        last_collected = t.get("last_income_collected")
        
        if last_collected:
            try:
                last_dt = datetime.fromisoformat(last_collected)
                hours_since = (now - last_dt).total_seconds() / 3600
                if hours_since < 24:
                    remaining = 24 - hours_since
                    min_hours_remaining = min(min_hours_remaining, remaining)
                    continue
            except (ValueError, TypeError):
                pass
        
        available_income += income
        ready_territories += 1
    
    return {
        "available_income": available_income,
        "ready_territories": ready_territories,
        "total_territories": len(owned),
        "next_collection_hours": round(min_hours_remaining, 1) if min_hours_remaining < 999 else 0,
    }


@api_router.post("/territories/{territory_id}/capture")
async def capture_territory(territory_id: str, player_id: str):
    """Fight the territory boss to capture an unclaimed territory"""
    territory = await db.territories.find_one({"id": territory_id})
    if not territory:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if territory.get("owner_id") == player_id:
        raise HTTPException(status_code=400, detail="You already own this territory")
    
    # If territory is owned by someone else, this is a PvP challenge
    if territory.get("owner_id"):
        return await challenge_territory_owner(territory, player)
    
    # Fight the boss (NPC)
    boss = territory["boss"]
    p_stats = player["stats"]
    
    # Apply active buffs
    buff_atk = sum(b["amount"] for b in player.get("active_buffs", []) if b["type"] == "max_health")
    
    player_hp = p_stats["health"]
    boss_hp = boss["health"]
    combat_log = [f"⚔️ You challenge {boss['name']} (Lv.{boss['level']}) for {territory['name']}!"]
    
    round_num = 0
    max_rounds = 20
    while player_hp > 0 and boss_hp > 0 and round_num < max_rounds:
        round_num += 1
        
        # Player attacks
        p_dmg = max(1, p_stats["attack"] + random.randint(-3, 5) - boss["defense"] // 2)
        # Crit chance
        if random.random() < 0.15:
            p_dmg = int(p_dmg * 1.5)
            combat_log.append(f"Round {round_num}: CRITICAL! You deal {p_dmg} damage!")
        else:
            combat_log.append(f"Round {round_num}: You deal {p_dmg} damage.")
        boss_hp -= p_dmg
        
        if boss_hp <= 0:
            break
        
        # Boss attacks
        b_dmg = max(1, boss["attack"] + random.randint(-2, 4) - p_stats["defense"] // 2)
        if random.random() < 0.1:
            b_dmg = int(b_dmg * 1.5)
            combat_log.append(f"Round {round_num}: {boss['name']} CRITS for {b_dmg} damage!")
        else:
            combat_log.append(f"Round {round_num}: {boss['name']} deals {b_dmg} damage.")
        player_hp -= b_dmg
    
    won = boss_hp <= 0
    
    if won:
        # Calculate capture bonus from territory income
        capture_bonus = territory.get("passive_income", 30)
        combat_log.append(f"🏆 Victory! You defeated {boss['name']} and claimed {territory['name']}!")
        combat_log.append(f"💰 Capture bonus: ${capture_bonus}")
        # Transfer ownership and change color
        owner_color = get_owner_color(player_id)
        await db.territories.update_one(
            {"id": territory_id},
            {"$set": {
                "owner_id": player_id,
                "owner_name": player["name"],
                "owner_pic": player.get("profile_pic", None),
                "color": owner_color,
                "last_income_collected": datetime.utcnow().isoformat(),
            }}
        )
        # Update player stats + give capture cash bonus
        await db.players.update_one(
            {"id": player_id},
            {"$set": {"stats.health": max(1, player_hp)}, "$inc": {"xp": 50, "reputation": 10, "cash": capture_bonus}}
        )
        # Apply vehicle durability loss for territory capture
        await apply_vehicle_durability_loss(player_id, "territory")
        # Apply battle durability loss 
        await apply_battle_durability_loss(player_id, dealt_damage=True, took_damage=True)
        return {
            "result": "victory",
            "combat_log": combat_log,
            "territory": serialize_doc(await db.territories.find_one({"id": territory_id})),
            "rewards": {"xp": 50, "reputation": 10, "cash": capture_bonus},
        }
    else:
        combat_log.append(f"💀 Defeated! {boss['name']} defended {territory['name']}.")
        await db.players.update_one(
            {"id": player_id},
            {"$set": {"stats.health": max(1, player_hp)}}
        )
        return {
            "result": "defeat",
            "combat_log": combat_log,
            "territory": serialize_doc(await db.territories.find_one({"id": territory_id})),
        }

async def challenge_territory_owner(territory: dict, challenger: dict):
    """PvP-style challenge: fight using the owner's stats"""
    owner = await db.players.find_one({"id": territory["owner_id"]})
    if not owner:
        # Owner no longer exists, reset territory
        await db.territories.update_one(
            {"id": territory["id"]},
            {"$set": {"owner_id": None, "owner_name": None, "owner_pic": None, "color": UNCLAIMED_COLOR}}
        )
        raise HTTPException(status_code=400, detail="Territory owner not found. Territory has been reset.")
    
    c_stats = challenger["stats"]
    o_stats = owner["stats"]
    
    challenger_hp = c_stats["health"]
    owner_hp = o_stats["health"]
    combat_log = [f"⚔️ You challenge {owner['name']} (Lv.{owner['level']}) for {territory['name']}!"]
    
    round_num = 0
    max_rounds = 25
    while challenger_hp > 0 and owner_hp > 0 and round_num < max_rounds:
        round_num += 1
        
        # Challenger attacks
        c_dmg = max(1, c_stats["attack"] + random.randint(-3, 5) - o_stats["defense"] // 2)
        if random.random() < (0.1 + c_stats.get("luck", 10) * 0.005):
            c_dmg = int(c_dmg * 1.5)
            combat_log.append(f"Round {round_num}: CRITICAL! You deal {c_dmg} damage!")
        else:
            combat_log.append(f"Round {round_num}: You deal {c_dmg} damage.")
        owner_hp -= c_dmg
        
        if owner_hp <= 0:
            break
        
        # Owner (defender) attacks
        o_dmg = max(1, o_stats["attack"] + random.randint(-3, 5) - c_stats["defense"] // 2)
        if random.random() < (0.1 + o_stats.get("luck", 10) * 0.005):
            o_dmg = int(o_dmg * 1.5)
            combat_log.append(f"Round {round_num}: {owner['name']} CRITS for {o_dmg} damage!")
        else:
            combat_log.append(f"Round {round_num}: {owner['name']} deals {o_dmg} damage.")
        challenger_hp -= o_dmg
    
    won = owner_hp <= 0
    
    if won:
        combat_log.append(f"🏆 Victory! You defeated {owner['name']} and took over {territory['name']}!")
        challenger_color = get_owner_color(challenger["id"])
        await db.territories.update_one(
            {"id": territory["id"]},
            {"$set": {
                "owner_id": challenger["id"],
                "owner_name": challenger["name"],
                "owner_pic": challenger.get("profile_pic", None),
                "color": challenger_color,
                "last_income_collected": datetime.utcnow().isoformat(),
            }}
        )
        await db.players.update_one(
            {"id": challenger["id"]},
            {"$set": {"stats.health": max(1, challenger_hp)}, "$inc": {"xp": 75, "reputation": 15, "wins": 1}}
        )
        await db.players.update_one(
            {"id": owner["id"]},
            {"$inc": {"losses": 1, "reputation": -5}}
        )
        return {
            "result": "victory",
            "combat_log": combat_log,
            "territory": serialize_doc(await db.territories.find_one({"id": territory["id"]})),
            "rewards": {"xp": 75, "reputation": 15},
        }
    else:
        combat_log.append(f"💀 Defeated! {owner['name']} defended {territory['name']}.")
        await db.players.update_one(
            {"id": challenger["id"]},
            {"$set": {"stats.health": max(1, challenger_hp)}, "$inc": {"losses": 1}}
        )
        return {
            "result": "defeat",
            "combat_log": combat_log,
            "territory": serialize_doc(await db.territories.find_one({"id": territory["id"]})),
        }

@api_router.post("/territories/{territory_id}/collect-income")
async def collect_single_territory_income(territory_id: str, player_id: str):
    """Collect passive income from an owned territory"""
    territory = await db.territories.find_one({"id": territory_id})
    if not territory:
        raise HTTPException(status_code=404, detail="Territory not found")
    if territory.get("owner_id") != player_id:
        raise HTTPException(status_code=403, detail="You don't own this territory")
    
    last = territory.get("last_income_collected")
    now = datetime.utcnow()
    if last:
        last_dt = datetime.fromisoformat(last)
        elapsed_hours = (now - last_dt).total_seconds() / 3600
        if elapsed_hours < 24:
            remaining_h = int(24 - elapsed_hours)
            remaining_m = int(((24 - elapsed_hours) - remaining_h) * 60)
            raise HTTPException(status_code=400, detail=f"Income available in {remaining_h}h {remaining_m}m")
    
    income = territory["rewards"]["passive_income"]
    await db.players.update_one({"id": player_id}, {"$inc": {"cash": income}})
    await db.territories.update_one(
        {"id": territory_id},
        {"$set": {"last_income_collected": now.isoformat()}}
    )
    
    return {"message": f"Collected ${income} from {territory['name']}!", "income": income}

@api_router.get("/territories/owned/{player_id}")
async def get_owned_territories(player_id: str):
    """Get all territories owned by a player"""
    territories = await db.territories.find({"owner_id": player_id}).to_list(length=50)
    return [serialize_doc(t) for t in territories]

# ============== FITNESS TRACKER ==============

STEP_GOALS = [
    {"goal": 5000, "reward_type": "xp", "reward_value": 200, "label": "Walker", "description": "Earn 200 XP"},
    {"goal": 10000, "reward_type": "xp", "reward_value": 500, "label": "Jogger", "description": "Earn 500 XP"},
    {"goal": 50000, "reward_type": "xp_and_buff", "reward_value": 1000, "label": "Runner", "description": "Earn 1000 XP + Attack Boost"},
]

@api_router.get("/fitness/{player_id}")
async def get_fitness_data(player_id: str):
    """Get today's fitness data for a player"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    data = await db.fitness.find_one({"player_id": player_id, "date": today})
    if not data:
        data = {
            "player_id": player_id,
            "date": today,
            "steps": 0,
            "claimed_goals": [],
        }
        await db.fitness.insert_one(data)
    
    return {
        "steps": data.get("steps", 0),
        "calories": round(data.get("steps", 0) * 0.04, 1),
        "distance_km": round(data.get("steps", 0) * 0.00078, 2),
        "claimed_goals": data.get("claimed_goals", []),
        "goals": STEP_GOALS,
        "date": today,
    }

@api_router.put("/fitness/{player_id}/steps")
async def update_steps(player_id: str, steps: int):
    """Update step count for today and sync walk_steps mission progress"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    await db.fitness.update_one(
        {"player_id": player_id, "date": today},
        {"$set": {"steps": steps}},
        upsert=True,
    )
    
    # Update walk_steps mission progress
    player = await db.players.find_one({"id": player_id})
    if player:
        active_ids = player.get("active_missions", [])
        if active_ids:
            missions = await db.missions.find({"id": {"$in": active_ids}, "mission_type": "walk_steps"}).to_list(50)
            for m in missions:
                pp = m.get("player_progress", {})
                player_data = pp.get(player_id, {})
                old_progress = player_data.get("progress", 0)
                # Steps are absolute (total today), so set progress directly
                if steps > old_progress:
                    player_data["progress"] = steps
                    pp[player_id] = player_data
                    await db.missions.update_one(
                        {"id": m["id"]},
                        {"$set": {"player_progress": pp}}
                    )
    
    return {"steps": steps}

@api_router.post("/fitness/{player_id}/claim/{goal_steps}")
async def claim_step_goal(player_id: str, goal_steps: int):
    """Claim a step goal reward"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Validate goal exists
    goal = next((g for g in STEP_GOALS if g["goal"] == goal_steps), None)
    if not goal:
        raise HTTPException(status_code=400, detail="Invalid goal")
    
    # Check fitness data
    data = await db.fitness.find_one({"player_id": player_id, "date": today})
    if not data:
        raise HTTPException(status_code=400, detail="No fitness data for today")
    
    if data.get("steps", 0) < goal_steps:
        raise HTTPException(status_code=400, detail=f"Need {goal_steps} steps. You have {data.get('steps', 0)}.")
    
    claimed = data.get("claimed_goals", [])
    if goal_steps in claimed:
        raise HTTPException(status_code=400, detail="Already claimed this goal today")
    
    # Give rewards
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    updates = {}
    reward_msg = ""
    
    if goal["reward_type"] == "xp":
        updates["$inc"] = {"xp": goal["reward_value"]}
        reward_msg = f"+{goal['reward_value']} XP!"
    elif goal["reward_type"] == "xp_and_buff":
        updates["$inc"] = {"xp": goal["reward_value"]}
        # Add a temporary attack buff (5 battles)
        buff = {"type": "attack", "value": 10, "remaining": 5}
        updates["$push"] = {"buffs": buff}
        reward_msg = f"+{goal['reward_value']} XP and +10 Attack for 5 battles!"
    
    if updates:
        await db.players.update_one({"id": player_id}, updates)
    
    # Check for level up
    player = await db.players.find_one({"id": player_id})
    current_xp = player.get("xp", 0)
    current_level = player.get("level", 1)
    xp_needed = current_level * 100
    leveled_up = False
    while current_xp >= xp_needed:
        current_level += 1
        current_xp -= xp_needed
        xp_needed = current_level * 100
        leveled_up = True
    if leveled_up:
        stat_boost = 2
        await db.players.update_one(
            {"id": player_id},
            {"$set": {
                "level": current_level,
                "xp": current_xp,
            }, "$inc": {
                "stats.max_health": stat_boost * 5,
                "stats.health": stat_boost * 5,
                "stats.attack": stat_boost,
                "stats.defense": stat_boost,
                "stats.max_energy": stat_boost * 2,
                "stats.energy": stat_boost * 2,
            }}
        )
        reward_msg += f" LEVEL UP to {current_level}!"
    
    # Mark goal as claimed
    await db.fitness.update_one(
        {"player_id": player_id, "date": today},
        {"$push": {"claimed_goals": goal_steps}}
    )
    
    return {"message": reward_msg, "goal": goal_steps, "reward_type": goal["reward_type"]}

# Include the router in the main app
app.include_router(api_router)

# Mount static files directory for serving sprites and other assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
