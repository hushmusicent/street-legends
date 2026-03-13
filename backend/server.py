from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import random
import math
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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

# Additional gun shop items
GUN_SHOP_ITEMS = {
    # Pistols
    "glock_9mm": {
        "id": "glock_9mm", "name": "Glock 9mm", "description": "Standard-issue sidearm. Reliable and deadly.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 6, "speed": 1}, "level_requirement": 2, "value": 55
    },
    "desert_eagle": {
        "id": "desert_eagle", "name": "Desert Eagle .50", "description": "Massive hand cannon. One shot, one kill.",
        "equipment_type": "weapon", "rarity": "rare",
        "stats_bonus": {"attack": 10, "speed": -2}, "level_requirement": 5, "value": 120
    },
    "gold_plated_pistol": {
        "id": "gold_plated_pistol", "name": "Gold-Plated Pistol", "description": "A kingpin's weapon. Style meets firepower.",
        "equipment_type": "weapon", "rarity": "epic",
        "stats_bonus": {"attack": 12, "luck": 3}, "level_requirement": 8, "value": 200
    },
    # SMGs
    "uzi": {
        "id": "uzi", "name": "Micro Uzi", "description": "Compact and fast. Spray and pray.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 5, "speed": 3}, "level_requirement": 3, "value": 65
    },
    "mp5": {
        "id": "mp5", "name": "MP5 Submachine Gun", "description": "Precision SMG used by tactical teams worldwide.",
        "equipment_type": "weapon", "rarity": "rare",
        "stats_bonus": {"attack": 8, "speed": 2}, "level_requirement": 6, "value": 110
    },
    # Shotguns
    "sawed_off": {
        "id": "sawed_off", "name": "Sawed-Off Shotgun", "description": "Close range devastation. Not subtle.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 7, "speed": -1}, "level_requirement": 4, "value": 70
    },
    "combat_shotgun": {
        "id": "combat_shotgun", "name": "Combat Shotgun", "description": "Military-grade room clearer.",
        "equipment_type": "weapon", "rarity": "rare",
        "stats_bonus": {"attack": 11, "defense": 1}, "level_requirement": 7, "value": 140
    },
    # Rifles
    "ak47": {
        "id": "ak47", "name": "AK-47", "description": "The most iconic assault rifle. Never jams.",
        "equipment_type": "weapon", "rarity": "rare",
        "stats_bonus": {"attack": 12, "speed": -1}, "level_requirement": 8, "value": 160
    },
    "sniper_rifle": {
        "id": "sniper_rifle", "name": "Sniper Rifle", "description": "Long range precision. One shot from downtown.",
        "equipment_type": "weapon", "rarity": "epic",
        "stats_bonus": {"attack": 15, "speed": -3, "luck": 2}, "level_requirement": 10, "value": 250
    },
    # Body Armor
    "tactical_vest": {
        "id": "tactical_vest", "name": "Tactical Vest", "description": "Military-grade protection with ammo pouches.",
        "equipment_type": "armor", "rarity": "uncommon",
        "stats_bonus": {"defense": 4, "attack": 1}, "level_requirement": 3, "value": 50
    },
    "riot_gear": {
        "id": "riot_gear", "name": "Riot Gear", "description": "Full body protection. Slow but tough.",
        "equipment_type": "armor", "rarity": "rare",
        "stats_bonus": {"defense": 8, "speed": -3}, "level_requirement": 6, "value": 100
    },
    "dragon_skin_armor": {
        "id": "dragon_skin_armor", "name": "Dragon Skin Armor", "description": "Next-gen flexible armor. The best money can buy.",
        "equipment_type": "armor", "rarity": "epic",
        "stats_bonus": {"defense": 10, "speed": 1}, "level_requirement": 10, "value": 280
    },
    "steel_toe_boots": {
        "id": "steel_toe_boots", "name": "Steel-Toe Boots", "description": "Kick harder, walk tougher.",
        "equipment_type": "armor", "rarity": "common",
        "stats_bonus": {"defense": 2, "attack": 1}, "level_requirement": 1, "value": 18
    },
    # Accessories
    "night_vision_goggles": {
        "id": "night_vision_goggles", "name": "Night Vision Goggles", "description": "See everything in the dark.",
        "equipment_type": "accessory", "rarity": "rare",
        "stats_bonus": {"luck": 4, "attack": 2}, "level_requirement": 5, "value": 90
    },
    "bulletproof_watch": {
        "id": "bulletproof_watch", "name": "Bulletproof Watch", "description": "Fancy watch that can stop a bullet. Sometimes.",
        "equipment_type": "accessory", "rarity": "uncommon",
        "stats_bonus": {"defense": 2, "luck": 2}, "level_requirement": 2, "value": 35
    },
    "laser_sight": {
        "id": "laser_sight", "name": "Laser Sight", "description": "Pin-point accuracy attachment.",
        "equipment_type": "accessory", "rarity": "uncommon",
        "stats_bonus": {"attack": 3, "luck": 1}, "level_requirement": 3, "value": 40
    },
    "skull_ring": {
        "id": "skull_ring", "name": "Skull Ring", "description": "Intimidating ring. Enemies think twice.",
        "equipment_type": "accessory", "rarity": "epic",
        "stats_bonus": {"attack": 4, "luck": 4, "defense": 2}, "level_requirement": 8, "value": 180
    },
    # Vehicles
    "stolen_motorcycle": {
        "id": "stolen_motorcycle", "name": "Stolen Motorcycle", "description": "Hot ride. Fast getaway guaranteed.",
        "equipment_type": "vehicle", "rarity": "uncommon",
        "stats_bonus": {"speed": 6}, "level_requirement": 3, "value": 55
    },
    "armored_suv": {
        "id": "armored_suv", "name": "Armored SUV", "description": "Bulletproof ride with all the extras.",
        "equipment_type": "vehicle", "rarity": "rare",
        "stats_bonus": {"speed": 4, "defense": 4}, "level_requirement": 6, "value": 130
    },
    "sports_car": {
        "id": "sports_car", "name": "Stolen Lambo", "description": "0 to 60 in 2.9 seconds. Don't ask where it came from.",
        "equipment_type": "vehicle", "rarity": "epic",
        "stats_bonus": {"speed": 10, "luck": 2}, "level_requirement": 10, "value": 300
    },
}

ALL_ITEMS.update(GUN_SHOP_ITEMS)

# ============== CONSUMABLE SHOP ITEMS ==============
CONSUMABLE_ITEMS = {
    # --- Health Recharges ---
    "health_syringe": {
        "id": "health_syringe", "name": "Health Syringe", "category": "health_recharge",
        "description": "Quick street med. Restores 30 HP.",
        "icon": "medkit", "rarity": "common",
        "effect": {"restore_health": 30}, "price": 26, "level_requirement": 1,
    },
    "med_kit": {
        "id": "med_kit", "name": "Med Kit", "category": "health_recharge",
        "description": "Military first aid. Restores 75 HP.",
        "icon": "medkit", "rarity": "uncommon",
        "effect": {"restore_health": 75}, "price": 60, "level_requirement": 3,
    },
    "full_heal_pack": {
        "id": "full_heal_pack", "name": "Full Heal Pack", "category": "health_recharge",
        "description": "Top-shelf trauma kit. Restores ALL health.",
        "icon": "medkit", "rarity": "rare",
        "effect": {"restore_health_full": True}, "price": 138, "level_requirement": 5,
    },
    # --- Energy Recharges ---
    "energy_drink": {
        "id": "energy_drink", "name": "Energy Drink", "category": "energy_recharge",
        "description": "Cheap caffeine hit. Restores 25 Energy.",
        "icon": "battery-charging", "rarity": "common",
        "effect": {"restore_energy": 25}, "price": 21, "level_requirement": 1,
    },
    "adrenaline_shot": {
        "id": "adrenaline_shot", "name": "Adrenaline Shot", "category": "energy_recharge",
        "description": "Pure adrenaline rush. Restores 60 Energy.",
        "icon": "battery-charging", "rarity": "uncommon",
        "effect": {"restore_energy": 60}, "price": 53, "level_requirement": 3,
    },
    "full_energy_cell": {
        "id": "full_energy_cell", "name": "Full Energy Cell", "category": "energy_recharge",
        "description": "Military-grade stimulant. Restores ALL energy.",
        "icon": "battery-charging", "rarity": "rare",
        "effect": {"restore_energy_full": True}, "price": 122, "level_requirement": 5,
    },
    # --- Combo Packs ---
    "street_rations": {
        "id": "street_rations", "name": "Street Rations", "category": "combo",
        "description": "Food & drink combo. Restores 20 HP and 20 Energy.",
        "icon": "fast-food", "rarity": "common",
        "effect": {"restore_health": 20, "restore_energy": 20}, "price": 35, "level_requirement": 1,
    },
    "combat_stim": {
        "id": "combat_stim", "name": "Combat Stimulant", "category": "combo",
        "description": "Black market stim. Restores 50 HP and 50 Energy.",
        "icon": "fast-food", "rarity": "rare",
        "effect": {"restore_health": 50, "restore_energy": 50}, "price": 129, "level_requirement": 5,
    },
    "full_recovery_kit": {
        "id": "full_recovery_kit", "name": "Full Recovery Kit", "category": "combo",
        "description": "The ultimate package. Fully restores HP and Energy.",
        "icon": "fast-food", "rarity": "epic",
        "effect": {"restore_health_full": True, "restore_energy_full": True}, "price": 260, "level_requirement": 8,
    },
    # --- Special: Extra Max Health (TEMPORARY) ---
    "heart_implant_mk1": {
        "id": "heart_implant_mk1", "name": "Heart Implant Mk1", "category": "extra_health",
        "description": "Cybernetic heart boost. +10 Max HP for 5 battles.",
        "icon": "heart", "rarity": "rare",
        "effect": {"temp_max_health": 10, "duration_battles": 5}, "price": 138, "level_requirement": 5,
    },
    "heart_implant_mk2": {
        "id": "heart_implant_mk2", "name": "Heart Implant Mk2", "category": "extra_health",
        "description": "Advanced cyber-heart. +25 Max HP for 5 battles.",
        "icon": "heart", "rarity": "epic",
        "effect": {"temp_max_health": 25, "duration_battles": 5}, "price": 276, "level_requirement": 8,
    },
    "heart_implant_mk3": {
        "id": "heart_implant_mk3", "name": "Heart Implant Mk3", "category": "extra_health",
        "description": "Legendary bio-mod. +50 Max HP for 5 battles.",
        "icon": "heart", "rarity": "legendary",
        "effect": {"temp_max_health": 50, "duration_battles": 5}, "price": 552, "level_requirement": 12,
    },
    # --- Special: Extra Max Energy (TEMPORARY) ---
    "neural_booster_mk1": {
        "id": "neural_booster_mk1", "name": "Neural Booster Mk1", "category": "extra_energy",
        "description": "Brain chip boost. +10 Max Energy for 5 battles.",
        "icon": "flash", "rarity": "rare",
        "effect": {"temp_max_energy": 10, "duration_battles": 5}, "price": 129, "level_requirement": 5,
    },
    "neural_booster_mk2": {
        "id": "neural_booster_mk2", "name": "Neural Booster Mk2", "category": "extra_energy",
        "description": "Advanced neural link. +25 Max Energy for 5 battles.",
        "icon": "flash", "rarity": "epic",
        "effect": {"temp_max_energy": 25, "duration_battles": 5}, "price": 260, "level_requirement": 8,
    },
    "neural_booster_mk3": {
        "id": "neural_booster_mk3", "name": "Neural Booster Mk3", "category": "extra_energy",
        "description": "Legendary neuro-mod. +50 Max Energy for 5 battles.",
        "icon": "flash", "rarity": "legendary",
        "effect": {"temp_max_energy": 50, "duration_battles": 5}, "price": 518, "level_requirement": 12,
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
    {"tier": 1, "name": "Super Thug", "level_min": 11, "level_max": 11, "is_boss": True},
    # Tier 2 (Levels 11-20, Boss at 21)
    {"tier": 2, "name": "Assassin", "level_min": 11, "level_max": 12, "is_boss": False},
    {"tier": 2, "name": "Thief", "level_min": 13, "level_max": 14, "is_boss": False},
    {"tier": 2, "name": "Hoodlum", "level_min": 15, "level_max": 16, "is_boss": False},
    {"tier": 2, "name": "Pirate", "level_min": 17, "level_max": 18, "is_boss": False},
    {"tier": 2, "name": "Bully", "level_min": 19, "level_max": 20, "is_boss": False},
    {"tier": 2, "name": "Super Bully", "level_min": 21, "level_max": 21, "is_boss": True},
    # Tier 3 (Levels 21-30, Boss at 31)
    {"tier": 3, "name": "Offender", "level_min": 21, "level_max": 22, "is_boss": False},
    {"tier": 3, "name": "Hood", "level_min": 23, "level_max": 24, "is_boss": False},
    {"tier": 3, "name": "Mobster", "level_min": 25, "level_max": 26, "is_boss": False},
    {"tier": 3, "name": "Gangsta", "level_min": 27, "level_max": 28, "is_boss": False},
    {"tier": 3, "name": "Hooligan", "level_min": 29, "level_max": 30, "is_boss": False},
    {"tier": 3, "name": "Super Hood", "level_min": 31, "level_max": 31, "is_boss": True},
    # Tier 4 (Levels 31-40, Boss at 41)
    {"tier": 4, "name": "Goon", "level_min": 31, "level_max": 32, "is_boss": False},
    {"tier": 4, "name": "Ruffian", "level_min": 33, "level_max": 34, "is_boss": False},
    {"tier": 4, "name": "Gang Banger", "level_min": 35, "level_max": 36, "is_boss": False},
    {"tier": 4, "name": "Tough Guy", "level_min": 37, "level_max": 38, "is_boss": False},
    {"tier": 4, "name": "Gorilla", "level_min": 39, "level_max": 40, "is_boss": False},
    {"tier": 4, "name": "Super Goon", "level_min": 41, "level_max": 41, "is_boss": True},
    # Tier 5 (Levels 41-50, Boss at 51)
    {"tier": 5, "name": "Punk", "level_min": 41, "level_max": 42, "is_boss": False},
    {"tier": 5, "name": "Rough Neck", "level_min": 43, "level_max": 44, "is_boss": False},
    {"tier": 5, "name": "Rowdy Person", "level_min": 45, "level_max": 46, "is_boss": False},
    {"tier": 5, "name": "Yardie", "level_min": 47, "level_max": 48, "is_boss": False},
    {"tier": 5, "name": "Perpetrator", "level_min": 49, "level_max": 50, "is_boss": False},
    {"tier": 5, "name": "Super Punk", "level_min": 51, "level_max": 51, "is_boss": True},
    # Tier 6 (Levels 51-60, Boss at 61)
    {"tier": 6, "name": "Vigilante", "level_min": 51, "level_max": 52, "is_boss": False},
    {"tier": 6, "name": "Scoundrel", "level_min": 53, "level_max": 54, "is_boss": False},
    {"tier": 6, "name": "Robber", "level_min": 55, "level_max": 56, "is_boss": False},
    {"tier": 6, "name": "Toughie", "level_min": 57, "level_max": 58, "is_boss": False},
    {"tier": 6, "name": "Felon", "level_min": 59, "level_max": 60, "is_boss": False},
    {"tier": 6, "name": "Super Felon", "level_min": 61, "level_max": 61, "is_boss": True},
    # Tier 7 (Levels 61-70, Boss at 71)
    {"tier": 7, "name": "Outlaw", "level_min": 61, "level_max": 62, "is_boss": False},
    {"tier": 7, "name": "Crook", "level_min": 63, "level_max": 64, "is_boss": False},
    {"tier": 7, "name": "Cutthroat", "level_min": 65, "level_max": 66, "is_boss": False},
    {"tier": 7, "name": "Brigade", "level_min": 67, "level_max": 68, "is_boss": False},
    {"tier": 7, "name": "Mafioso", "level_min": 69, "level_max": 70, "is_boss": False},
    {"tier": 7, "name": "Super Outlaw", "level_min": 71, "level_max": 71, "is_boss": True},
    # Tier 8 (Levels 71-80, Boss at 81)
    {"tier": 8, "name": "Perp", "level_min": 71, "level_max": 72, "is_boss": False},
    {"tier": 8, "name": "Mugger", "level_min": 73, "level_max": 74, "is_boss": False},
    {"tier": 8, "name": "LawBreaker", "level_min": 75, "level_max": 76, "is_boss": False},
    {"tier": 8, "name": "Racketeer", "level_min": 77, "level_max": 78, "is_boss": False},
    {"tier": 8, "name": "Desperado", "level_min": 79, "level_max": 80, "is_boss": False},
    {"tier": 8, "name": "Super Mugger", "level_min": 81, "level_max": 81, "is_boss": True},
    # Tier 9 (Levels 81-90, Boss at 91)
    {"tier": 9, "name": "Highway Man", "level_min": 81, "level_max": 82, "is_boss": False},
    {"tier": 9, "name": "Gunman", "level_min": 83, "level_max": 84, "is_boss": False},
    {"tier": 9, "name": "Vandal", "level_min": 85, "level_max": 86, "is_boss": False},
    {"tier": 9, "name": "Pick Pocket", "level_min": 87, "level_max": 88, "is_boss": False},
    {"tier": 9, "name": "Swindler", "level_min": 89, "level_max": 90, "is_boss": False},
    {"tier": 9, "name": "Super Vandal", "level_min": 91, "level_max": 91, "is_boss": True},
    # Tier 10 (Levels 91-100, Boss at 101)
    {"tier": 10, "name": "Malefactor", "level_min": 91, "level_max": 92, "is_boss": False},
    {"tier": 10, "name": "Bravo", "level_min": 93, "level_max": 94, "is_boss": False},
    {"tier": 10, "name": "Delinquent", "level_min": 95, "level_max": 96, "is_boss": False},
    {"tier": 10, "name": "Maniac", "level_min": 97, "level_max": 98, "is_boss": False},
    {"tier": 10, "name": "Psycho", "level_min": 99, "level_max": 100, "is_boss": False},
    {"tier": 10, "name": "Super Psycho", "level_min": 101, "level_max": 101, "is_boss": True},
]

def get_player_tier(player_level: int) -> int:
    """Get the player's current tier (1-10) based on level"""
    return min(10, max(1, (player_level - 1) // 10 + 1))

def get_eligible_enemies(player_level: int):
    """Get enemies from current tier and all previous tiers.
    Lower level enemies spawn MORE frequently than higher level ones."""
    current_tier = get_player_tier(player_level)
    eligible = [e for e in ENEMY_TIERS if e["tier"] <= current_tier]
    
    # Weight system: lower tiers get much higher spawn rates
    # Tier 1 = highest weight, each tier above = less common
    weighted = []
    for e in eligible:
        if e["is_boss"]:
            # Bosses are always rare, only when player is at/above boss level
            if player_level >= e["level_min"]:
                weighted.append((e, 1))
        else:
            # Lower tier enemies spawn more often
            # Tier 1 = weight 10, Tier 2 = weight 7, Tier 3 = weight 5, etc.
            tier_weight = max(1, 11 - e["tier"])  # T1=10, T2=9, T3=8... T10=1
            
            # Boost even more for much lower tiers (they're the common street thugs)
            tier_diff = current_tier - e["tier"]
            if tier_diff >= 3:
                tier_weight += 3  # Extra common for enemies 3+ tiers below
            elif tier_diff >= 1:
                tier_weight += 1  # Slightly boosted for lower tiers
            
            weighted.append((e, tier_weight))
    
    if not weighted:
        # Fallback to first tier
        weighted = [(e, 10) for e in ENEMY_TIERS if e["tier"] == 1 and not e["is_boss"]]
    
    return weighted

def calculate_enemy_stats(enemy_level: int, is_boss: bool) -> dict:
    """Calculate enemy stats based on level and boss status"""
    # Base stats scale with level, bosses get a significant multiplier
    boss_mult = 2.0 if is_boss else 1.0
    health = int((80 + enemy_level * 18) * boss_mult)
    attack = int((8 + enemy_level * 3.2) * boss_mult)
    defense = int((5 + enemy_level * 1.8) * boss_mult)
    return {"health": health, "max_health": health, "attack": attack, "defense": defense}

SKILLS = {
    "heavy_strike": {"name": "Heavy Strike", "damage_mult": 1.5, "cost": 10, "unlock_level": 1},
    "quick_shot": {"name": "Quick Shot", "damage_mult": 1.2, "cost": 5, "unlock_level": 1},
    "defensive_stance": {"name": "Defensive Stance", "defense_buff": 2.0, "cost": 8, "unlock_level": 3},
    "critical_aim": {"name": "Critical Aim", "crit_chance": 0.5, "cost": 15, "unlock_level": 5},
    "heal": {"name": "Street Medicine", "heal_percent": 0.3, "cost": 20, "unlock_level": 7},
    "rage": {"name": "Rage Mode", "damage_mult": 2.0, "cost": 25, "unlock_level": 10},
    "execute": {"name": "Execute", "damage_mult": 3.0, "cost": 40, "unlock_level": 15}
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
    inventory: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=lambda: ["heavy_strike", "quick_shot"])
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
        inventory=["rusty_pipe", "worn_jacket", "chain_necklace", "beat_up_bike"],
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
        inventory=["rusty_pipe", "worn_jacket", "chain_necklace", "beat_up_bike"],
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
    await db.territories.update_many(
        {"owner_id": player_id},
        {"$set": {"owner_pic": data.image}}
    )
    
    return {"message": "Profile picture updated"}

@api_router.get("/players/{player_id}/profile-pic")
async def get_profile_pic(player_id: str):
    """Get player's profile picture"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"profile_pic": player.get("profile_pic", None)}

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
    """Spawn monsters near a location - 1 new enemy every 5 minutes, max 10 per area"""
    position = Position(latitude=latitude, longitude=longitude)
    
    # Clean up expired monsters
    await db.monsters.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
    
    # Check existing monsters nearby (within 500m)
    existing = await db.monsters.find({"expires_at": {"$gt": datetime.utcnow()}}).to_list(100)
    nearby = [m for m in existing if calculate_distance(position, Position(**m["position"])) < 500]
    nearby_count = len(nearby)
    
    # Max 10 per area
    if nearby_count >= 10:
        # Already at max, return existing
        all_monsters = await db.monsters.find({"expires_at": {"$gt": datetime.utcnow()}}).to_list(50)
        return [serialize_doc(m) for m in all_monsters if calculate_distance(position, Position(**m["position"])) < 500]
    
    # Determine how many to spawn
    spawn_count = 0
    if nearby_count == 0:
        # New area — always spawn exactly 5 enemies
        spawn_count = 5
    elif nearby_count < 10:
        # Existing area — spawn 1 every 5 minutes
        most_recent = max(nearby, key=lambda m: m.get("spawn_time", datetime.min))
        last_spawn_time = most_recent.get("spawn_time", datetime.min)
        if isinstance(last_spawn_time, str):
            last_spawn_time = datetime.fromisoformat(last_spawn_time)
        elapsed = (datetime.utcnow() - last_spawn_time).total_seconds()
        if elapsed >= 300:  # 5 minutes
            spawn_count = 1
    
    # Cap so we don't exceed 10
    spawn_count = min(spawn_count, 10 - nearby_count)
    
    spawned = []
    if spawn_count > 0:
        weighted_enemies = get_eligible_enemies(player_level)
        if not weighted_enemies:
            weighted_enemies = [(ENEMY_TIERS[0], 1)]
        
        for _ in range(spawn_count):
            enemies, weights = zip(*weighted_enemies)
            template = random.choices(enemies, weights=weights, k=1)[0]
            
            monster_level = random.randint(template["level_min"], template["level_max"])
            
            offset_lat = random.uniform(-0.003, 0.003)
            offset_lon = random.uniform(-0.003, 0.003)
            
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
                position=Position(latitude=latitude + offset_lat, longitude=longitude + offset_lon),
                loot_cash=monster_level * random.randint(10, 25) * (3 if template["is_boss"] else 1),
                loot_xp=monster_level * random.randint(15, 30) * (3 if template["is_boss"] else 1),
                expires_at=datetime.utcnow().replace(hour=datetime.utcnow().hour + 1)
            )
            
            await db.monsters.insert_one(monster.dict())
            spawned.append(monster)
    
    # Return all nearby monsters
    all_monsters = await db.monsters.find({"expires_at": {"$gt": datetime.utcnow()}}).to_list(50)
    nearby_monsters = [
        serialize_doc(m) for m in all_monsters 
        if calculate_distance(position, Position(**m["position"])) < 500
    ]
    
    return nearby_monsters

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
        return battle
    
    player = await db.players.find_one({"id": battle["player_id"]})
    
    if battle["enemy_type"] == "monster":
        enemy = await db.monsters.find_one({"id": battle["enemy_id"]})
        enemy_stats = enemy["stats"]
    else:
        enemy = await db.players.find_one({"id": battle["enemy_id"]})
        enemy_stats = enemy["stats"]
    
    player_stats = player["stats"]
    combat_log = battle["combat_log"]
    player_health = battle["player_health"]
    enemy_health = battle["enemy_health"]
    player_energy = battle["player_energy"]
    
    # Player action
    if action.action == "attack":
        damage = max(1, player_stats["attack"] - enemy_stats.get("defense", 0) // 2)
        crit = random.random() < (player_stats["luck"] / 100)
        if crit:
            damage = int(damage * 1.5)
            combat_log.append(f"CRITICAL HIT! You deal {damage} damage!")
        else:
            combat_log.append(f"You attack for {damage} damage!")
        enemy_health -= damage
        
    elif action.action == "skill" and action.skill_id:
        skill = SKILLS.get(action.skill_id)
        if not skill:
            raise HTTPException(status_code=400, detail="Invalid skill")
        if skill["cost"] > player_energy:
            raise HTTPException(status_code=400, detail="Not enough energy")
        
        player_energy -= skill["cost"]
        
        if "damage_mult" in skill:
            damage = int(player_stats["attack"] * skill["damage_mult"])
            enemy_health -= damage
            combat_log.append(f"You use {skill['name']} for {damage} damage!")
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
            return await db.battles.find_one({"id": battle_id})
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
    enemy_damage = max(1, enemy_stats.get("attack", 10) - player_stats["defense"] // 2)
    if action.action == "defend":
        enemy_damage = enemy_damage // 2
    
    player_health -= enemy_damage
    combat_log.append(f"{battle['enemy_name']} attacks for {enemy_damage} damage!")
    
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
                expires_at=datetime.utcnow().replace(hour=datetime.utcnow().hour + 2)
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
                expires_at=datetime.utcnow().replace(hour=datetime.utcnow().hour + 2)
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
    """Spawn random shops near a location"""
    shops = []
    num_shops = random.randint(1, 2)
    
    for i in range(num_shops):
        # Random offset within ~500m
        lat_offset = random.uniform(-0.004, 0.004)
        lng_offset = random.uniform(-0.004, 0.004)
        
        shop_type = random.choice(list(SHOP_TYPES.keys()))
        shop_config = SHOP_TYPES[shop_type]
        shop_name = random.choice(SHOP_NAMES)
        
        # Pick random items focused on the shop type
        focus_items = [item for item in ALL_ITEMS.values() if item["equipment_type"] in shop_config["focus"]]
        other_items = [item for item in ALL_ITEMS.values() if item["equipment_type"] not in shop_config["focus"]]
        
        # Main stock: 4-8 items from focus + 1-2 random others
        stock_count = random.randint(4, 8)
        stock = random.sample(focus_items, min(stock_count, len(focus_items)))
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
        
        shop = {
            "id": str(uuid.uuid4()),
            "name": shop_name,
            "shop_type": shop_type,
            "latitude": latitude + lat_offset,
            "longitude": longitude + lng_offset,
            "price_multiplier": price_mult,
            "stock": priced_stock,
            "level": max(1, player_level + random.randint(-2, 3)),
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
    """Get player's inventory with full item details"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    inventory_items = []
    for item_id in player.get("inventory", []):
        item = ALL_ITEMS.get(item_id)
        if item:
            inventory_items.append(item)
    return inventory_items

@api_router.get("/players/{player_id}/equipment-details")
async def get_player_equipment_details(player_id: str):
    """Get player's equipped items with full details"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    equipment = player.get("equipment", {})
    equipped = {}
    for slot, item_id in equipment.items():
        if item_id:
            item = ALL_ITEMS.get(item_id)
            equipped[slot] = item if item else {"id": item_id, "name": "Unknown", "equipment_type": slot, "rarity": "common", "stats_bonus": {}, "description": "Unknown item"}
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
    if item_id not in inv:
        raise HTTPException(status_code=400, detail="Item not in inventory")
    
    inv.remove(item_id)
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
    if item_id not in inv:
        raise HTTPException(status_code=400, detail="Item not in inventory")
    
    item = ALL_ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item data not found")
    
    sell_price = max(1, item.get("value", 10) // 2)
    
    inv.remove(item_id)
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"inventory": inv}, "$inc": {"cash": sell_price}}
    )
    
    return {
        "message": f"Sold {item['name']} for ${sell_price}",
        "sell_price": sell_price,
        "item_name": item["name"],
    }

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
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {f"equipment.{slot}": None}, "$push": {"inventory": current_item}}
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
    
    await db.players.update_one(
        {"id": player_id},
        {"$inc": {"cash": -item["value"]}, "$push": {"inventory": item_id}}
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
    
    if equipment_id not in player.get("inventory", []):
        raise HTTPException(status_code=400, detail="Item not in inventory")
    
    slot = equipment["equipment_type"]
    current_equipped = player["equipment"].get(slot)
    
    # Update equipment
    update_data = {f"equipment.{slot}": equipment_id}
    
    # Move old item back to inventory if exists
    if current_equipped:
        await db.players.update_one(
            {"id": player_id},
            {"$push": {"inventory": current_equipped}}
        )
    
    # Remove new item from inventory and equip
    await db.players.update_one(
        {"id": player_id},
        {"$pull": {"inventory": equipment_id}, "$set": update_data}
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
    """Get all available skills"""
    return SKILLS

@api_router.get("/players/{player_id}/skills")
async def get_player_skills(player_id: str):
    """Get player's unlocked skills"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    unlocked = []
    for skill_id, skill in SKILLS.items():
        if player["level"] >= skill["unlock_level"]:
            unlocked.append({"id": skill_id, **skill, "unlocked": skill_id in player.get("skills", [])})
    
    return unlocked

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
    
    # Temporary max health boost
    if "temp_max_health" in effect:
        amount = effect["temp_max_health"]
        duration = effect.get("duration_battles", 5)
        buff = {
            "id": f"{item_id}_{str(uuid.uuid4())[:8]}",
            "item_id": item_id,
            "name": item["name"],
            "type": "max_health",
            "amount": amount,
            "battles_remaining": duration,
            "icon": "heart",
        }
        update_ops.setdefault("$push", {})["active_buffs"] = buff
        messages.append(f"+{amount} Max HP for {duration} battles")
    
    # Temporary max energy boost
    if "temp_max_energy" in effect:
        amount = effect["temp_max_energy"]
        duration = effect.get("duration_battles", 5)
        buff = {
            "id": f"{item_id}_{str(uuid.uuid4())[:8]}",
            "item_id": item_id,
            "name": item["name"],
            "type": "max_energy",
            "amount": amount,
            "battles_remaining": duration,
            "icon": "flash",
        }
        update_ops.setdefault("$push", {})["active_buffs"] = buff
        messages.append(f"+{amount} Max Energy for {duration} battles")
    
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
    
    # Boss scales with zone difficulty
    zone_level = max(1, player_level + rng.randint(-2, 3))
    boss_hp = 60 + zone_level * 15
    boss_atk = 8 + zone_level * 3
    boss_def = 5 + zone_level * 2
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
    {"goal": 3000, "reward_type": "xp", "reward_value": 200, "label": "Walker", "description": "Earn 200 XP"},
    {"goal": 6000, "reward_type": "xp", "reward_value": 500, "label": "Jogger", "description": "Earn 500 XP"},
    {"goal": 10000, "reward_type": "xp_and_buff", "reward_value": 1000, "label": "Runner", "description": "Earn 1000 XP + Attack Boost"},
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
