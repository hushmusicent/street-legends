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
        "effect": {"restore_health": 30}, "price": 15, "level_requirement": 1,
    },
    "med_kit": {
        "id": "med_kit", "name": "Med Kit", "category": "health_recharge",
        "description": "Military first aid. Restores 75 HP.",
        "icon": "medkit", "rarity": "uncommon",
        "effect": {"restore_health": 75}, "price": 35, "level_requirement": 3,
    },
    "full_heal_pack": {
        "id": "full_heal_pack", "name": "Full Heal Pack", "category": "health_recharge",
        "description": "Top-shelf trauma kit. Restores ALL health.",
        "icon": "medkit", "rarity": "rare",
        "effect": {"restore_health_full": True}, "price": 80, "level_requirement": 5,
    },
    # --- Energy Recharges ---
    "energy_drink": {
        "id": "energy_drink", "name": "Energy Drink", "category": "energy_recharge",
        "description": "Cheap caffeine hit. Restores 25 Energy.",
        "icon": "battery-charging", "rarity": "common",
        "effect": {"restore_energy": 25}, "price": 12, "level_requirement": 1,
    },
    "adrenaline_shot": {
        "id": "adrenaline_shot", "name": "Adrenaline Shot", "category": "energy_recharge",
        "description": "Pure adrenaline rush. Restores 60 Energy.",
        "icon": "battery-charging", "rarity": "uncommon",
        "effect": {"restore_energy": 60}, "price": 30, "level_requirement": 3,
    },
    "full_energy_cell": {
        "id": "full_energy_cell", "name": "Full Energy Cell", "category": "energy_recharge",
        "description": "Military-grade stimulant. Restores ALL energy.",
        "icon": "battery-charging", "rarity": "rare",
        "effect": {"restore_energy_full": True}, "price": 70, "level_requirement": 5,
    },
    # --- Combo Packs ---
    "street_rations": {
        "id": "street_rations", "name": "Street Rations", "category": "combo",
        "description": "Food & drink combo. Restores 20 HP and 20 Energy.",
        "icon": "fast-food", "rarity": "common",
        "effect": {"restore_health": 20, "restore_energy": 20}, "price": 20, "level_requirement": 1,
    },
    "combat_stim": {
        "id": "combat_stim", "name": "Combat Stimulant", "category": "combo",
        "description": "Black market stim. Restores 50 HP and 50 Energy.",
        "icon": "fast-food", "rarity": "rare",
        "effect": {"restore_health": 50, "restore_energy": 50}, "price": 65, "level_requirement": 5,
    },
    "full_recovery_kit": {
        "id": "full_recovery_kit", "name": "Full Recovery Kit", "category": "combo",
        "description": "The ultimate package. Fully restores HP and Energy.",
        "icon": "fast-food", "rarity": "epic",
        "effect": {"restore_health_full": True, "restore_energy_full": True}, "price": 150, "level_requirement": 8,
    },
    # --- Special: Extra Max Health (TEMPORARY) ---
    "heart_implant_mk1": {
        "id": "heart_implant_mk1", "name": "Heart Implant Mk1", "category": "extra_health",
        "description": "Cybernetic heart boost. +10 Max HP for 5 battles.",
        "icon": "heart", "rarity": "rare",
        "effect": {"temp_max_health": 10, "duration_battles": 5}, "price": 80, "level_requirement": 5,
    },
    "heart_implant_mk2": {
        "id": "heart_implant_mk2", "name": "Heart Implant Mk2", "category": "extra_health",
        "description": "Advanced cyber-heart. +25 Max HP for 5 battles.",
        "icon": "heart", "rarity": "epic",
        "effect": {"temp_max_health": 25, "duration_battles": 5}, "price": 160, "level_requirement": 8,
    },
    "heart_implant_mk3": {
        "id": "heart_implant_mk3", "name": "Heart Implant Mk3", "category": "extra_health",
        "description": "Legendary bio-mod. +50 Max HP for 5 battles.",
        "icon": "heart", "rarity": "legendary",
        "effect": {"temp_max_health": 50, "duration_battles": 5}, "price": 320, "level_requirement": 12,
    },
    # --- Special: Extra Max Energy (TEMPORARY) ---
    "neural_booster_mk1": {
        "id": "neural_booster_mk1", "name": "Neural Booster Mk1", "category": "extra_energy",
        "description": "Brain chip boost. +10 Max Energy for 5 battles.",
        "icon": "flash", "rarity": "rare",
        "effect": {"temp_max_energy": 10, "duration_battles": 5}, "price": 75, "level_requirement": 5,
    },
    "neural_booster_mk2": {
        "id": "neural_booster_mk2", "name": "Neural Booster Mk2", "category": "extra_energy",
        "description": "Advanced neural link. +25 Max Energy for 5 battles.",
        "icon": "flash", "rarity": "epic",
        "effect": {"temp_max_energy": 25, "duration_battles": 5}, "price": 150, "level_requirement": 8,
    },
    "neural_booster_mk3": {
        "id": "neural_booster_mk3", "name": "Neural Booster Mk3", "category": "extra_energy",
        "description": "Legendary neuro-mod. +50 Max Energy for 5 battles.",
        "icon": "flash", "rarity": "legendary",
        "effect": {"temp_max_energy": 50, "duration_battles": 5}, "price": 300, "level_requirement": 12,
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

MONSTER_TEMPLATES = [
    {"name": "Street Thug", "type": "humanoid", "base_level": 1, "threat": "low"},
    {"name": "Gang Member", "type": "humanoid", "base_level": 3, "threat": "low"},
    {"name": "Corrupt Cop", "type": "humanoid", "base_level": 5, "threat": "medium"},
    {"name": "Cartel Soldier", "type": "humanoid", "base_level": 8, "threat": "medium"},
    {"name": "Crime Boss", "type": "boss", "base_level": 10, "threat": "high"},
    {"name": "Cyber Mercenary", "type": "tech", "base_level": 12, "threat": "high"},
    {"name": "Shadow Assassin", "type": "stealth", "base_level": 15, "threat": "extreme"},
    {"name": "Kingpin", "type": "boss", "base_level": 20, "threat": "extreme"}
]

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
TERRITORY_NAMES = [
    "Northside Turf", "Downtown Block", "The Docks", "Eastside Plaza", "Westend Corner",
    "Central Park Zone", "Old Factory Row", "Market Square", "Riverside Strip", "The Underpass",
    "Southgate Junction", "Warehouse District", "Rail Yard Outpost", "Harbor Heights", "Canal Street Turf",
    "Hilltop Lookout", "Bridge Crossing", "Neon Alley", "Freeway Overpass", "Dead End Zone",
]

TERRITORY_BOSS_NAMES = [
    "Turf Guardian", "Block Captain", "Dock Warden", "Plaza Enforcer", "Corner King",
    "Zone Protector", "Factory Foreman", "Market Boss", "Strip Lord", "Underpass Phantom",
]

TERRITORY_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#9b59b6", "#f39c12",
    "#1abc9c", "#e91e63", "#ff5722", "#607d8b", "#795548",
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
    """Get player by ID"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
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
    all_players = await db.players.find({"id": {"$ne": player_id}, "position": {"$exists": True}}).to_list(100)
    
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
    players = await db.players.find().sort("reputation", -1).limit(limit).to_list(limit)
    return [
        {
            "rank": i + 1,
            "id": p["id"],
            "name": p["name"],
            "level": p["level"],
            "reputation": p["reputation"],
            "wins": p["wins"],
            "character_class": p["character_class"]
        }
        for i, p in enumerate(players)
    ]

# ============== MONSTER ENDPOINTS ==============
@api_router.get("/monsters/spawn")
async def spawn_monsters(latitude: float, longitude: float, player_level: int = 1):
    """Spawn monsters near a location based on player level"""
    position = Position(latitude=latitude, longitude=longitude)
    
    # Clean up expired monsters
    await db.monsters.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
    
    # Check existing monsters nearby
    existing = await db.monsters.find().to_list(100)
    nearby_count = sum(1 for m in existing if calculate_distance(position, Position(**m["position"])) < 200)
    
    monsters_to_spawn = max(0, 5 - nearby_count)
    spawned = []
    
    for _ in range(monsters_to_spawn):
        # Select appropriate monster template based on player level
        suitable_templates = [t for t in MONSTER_TEMPLATES if abs(t["base_level"] - player_level) <= 3]
        if not suitable_templates:
            suitable_templates = MONSTER_TEMPLATES[:3]
        
        template = random.choice(suitable_templates)
        
        # Randomize position slightly (within 100-300m)
        offset_lat = random.uniform(-0.003, 0.003)
        offset_lon = random.uniform(-0.003, 0.003)
        
        monster_level = max(1, player_level + random.randint(-2, 2))
        base_stats = {"health": 50 + monster_level * 10, "attack": 5 + monster_level * 2, "defense": 3 + monster_level}
        
        # Generate AI description
        description = await generate_ai_content("monster", {
            "name": template["name"],
            "level": monster_level,
            "type": template["type"]
        })
        
        monster = Monster(
            name=template["name"],
            description=description,
            monster_type=template["type"],
            level=monster_level,
            stats=calculate_stats_for_level(base_stats, monster_level),
            position=Position(latitude=latitude + offset_lat, longitude=longitude + offset_lon),
            loot_cash=monster_level * random.randint(10, 25),
            loot_xp=monster_level * random.randint(15, 30),
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
                "reputation": player["reputation"] + enemy["level"]
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
            {"$set": {"losses": player["losses"] + 1}}
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
async def generate_missions(latitude: float, longitude: float, player_level: int = 1):
    """Generate AI missions near a location"""
    position = Position(latitude=latitude, longitude=longitude)
    
    # Clean expired missions
    await db.missions.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
    
    # Get existing nearby missions
    existing = await db.missions.find({"expires_at": {"$gt": datetime.utcnow()}}).to_list(50)
    nearby = [serialize_doc(m) for m in existing if calculate_distance(position, Position(**m["position"])) < 1000]
    
    if len(nearby) >= 3:
        return nearby
    
    # Generate new missions
    mission_types = ["combat", "delivery", "investigation", "heist"]
    difficulties = ["easy", "medium", "hard"]
    
    for _ in range(3 - len(nearby)):
        mission_type = random.choice(mission_types)
        difficulty = random.choice(difficulties)
        
        # AI-generated content
        ai_response = await generate_ai_content("mission", {
            "level": player_level,
            "type": mission_type,
            "location": "urban city block"
        })
        
        try:
            import json
            mission_data = json.loads(ai_response)
        except:
            mission_data = {
                "title": f"Street {mission_type.title()}",
                "description": "Handle business in the neighborhood.",
                "dialogue": "I got a job for you.",
                "objectives": ["Complete the mission", "Return for reward"]
            }
        
        offset_lat = random.uniform(-0.005, 0.005)
        offset_lon = random.uniform(-0.005, 0.005)
        
        reward_mult = {"easy": 1, "medium": 1.5, "hard": 2.5}[difficulty]
        
        mission = Mission(
            title=mission_data.get("title", "Street Mission"),
            description=mission_data.get("description", "Complete the mission."),
            dialogue=mission_data.get("dialogue", "Get it done."),
            objectives=mission_data.get("objectives", ["Complete the task"]),
            mission_type=mission_type,
            difficulty=difficulty,
            level_requirement=max(1, player_level - 2),
            position=Position(latitude=latitude + offset_lat, longitude=longitude + offset_lon),
            rewards={
                "cash": int(50 * player_level * reward_mult),
                "xp": int(40 * player_level * reward_mult),
                "reputation": int(5 * reward_mult)
            },
            expires_at=datetime.utcnow().replace(hour=datetime.utcnow().hour + 2)
        )
        
        await db.missions.insert_one(mission.dict())
        nearby.append(serialize_doc(mission.dict()))
    
    return nearby

@api_router.post("/missions/{mission_id}/complete")
async def complete_mission(mission_id: str, player_id: str):
    """Complete a mission and claim rewards"""
    mission = await db.missions.find_one({"id": mission_id})
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
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
    
    await db.players.update_one({"id": player_id}, {"$set": update_data})
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
    num_shops = random.randint(3, 6)
    
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

def generate_territories_for_location(lat: float, lng: float, player_level: int = 1):
    """Generate 3-5 non-overlapping territories for a given area, cash-only daily rewards"""
    import math
    grid_lat = round(lat / 0.005) * 0.005
    grid_lng = round(lng / 0.005) * 0.005
    seed = int(abs(grid_lat * 1000000 + grid_lng * 1000000)) % 2147483647
    rng = random.Random(seed)
    
    count = rng.randint(3, 5)
    territories = []
    placed = []  # list of (lat, lng, radius_deg) for overlap checking
    
    # 1 degree latitude ≈ 111,000 m, 1 degree longitude ≈ 85,000 m (at ~40° lat)
    LAT_M = 111000.0
    LNG_M = 85000.0
    
    def overlaps(t_lat, t_lng, t_radius_m):
        """Check if a new territory overlaps any existing one"""
        for (p_lat, p_lng, p_radius_m) in placed:
            dist_m = math.sqrt(((t_lat - p_lat) * LAT_M) ** 2 + ((t_lng - p_lng) * LNG_M) ** 2)
            min_gap = t_radius_m + p_radius_m + 50  # 50m buffer between territories
            if dist_m < min_gap:
                return True
        return False
    
    # Place territories in a spread pattern around grid center
    angles = [rng.uniform(0, 2 * math.pi)]
    for _ in range(count - 1):
        angles.append(angles[-1] + (2 * math.pi / count) + rng.uniform(-0.3, 0.3))
    
    for i in range(count):
        idx = (seed + i) % len(TERRITORY_NAMES)
        boss_idx = (seed + i) % len(TERRITORY_BOSS_NAMES)
        color_idx = (seed + i) % len(TERRITORY_COLORS)
        
        radius_m = rng.randint(150, 250)
        
        # Place using angular spread to avoid overlaps
        for attempt in range(10):
            dist = rng.uniform(0.001, 0.003)  # ~110-330m from center
            if attempt > 0:
                dist += attempt * 0.0005  # push further out on retries
            angle = angles[i] if i < len(angles) else rng.uniform(0, 2 * math.pi)
            t_lat = grid_lat + dist * math.sin(angle)
            t_lng = grid_lng + dist * math.cos(angle)
            
            if not overlaps(t_lat, t_lng, radius_m):
                break
        
        placed.append((t_lat, t_lng, radius_m))
        
        # Boss scales with zone difficulty
        zone_level = max(1, player_level + rng.randint(-2, 3))
        boss_hp = 60 + zone_level * 15
        boss_atk = 8 + zone_level * 3
        boss_def = 5 + zone_level * 2
        
        # Daily cash reward only
        daily_income = 20 + zone_level * 10
        
        territory_id = f"territory_{grid_lat:.3f}_{grid_lng:.3f}_{i}"
        territories.append({
            "id": territory_id,
            "name": TERRITORY_NAMES[idx],
            "location": {"latitude": round(t_lat, 6), "longitude": round(t_lng, 6)},
            "radius": radius_m,
            "color": TERRITORY_COLORS[color_idx],
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
        })
    return territories

@api_router.get("/territories/nearby")
async def get_nearby_territories(latitude: float, longitude: float, player_level: int = 1):
    """Get or create territories near a location"""
    grid_lat = round(latitude / 0.005) * 0.005
    grid_lng = round(longitude / 0.005) * 0.005
    grid_key = f"{grid_lat:.3f}_{grid_lng:.3f}"
    
    # Check if territories already exist in DB for this grid
    existing = await db.territories.find({"grid_key": grid_key}).to_list(length=10)
    if existing:
        return [serialize_doc(t) for t in existing]
    
    # Generate new territories and store them
    territories = generate_territories_for_location(latitude, longitude, player_level)
    for t in territories:
        t["grid_key"] = grid_key
        t["created_at"] = datetime.utcnow().isoformat()
        t["last_income_collected"] = None
    await db.territories.insert_many(territories)
    
    stored = await db.territories.find({"grid_key": grid_key}).to_list(length=10)
    return [serialize_doc(t) for t in stored]

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
        combat_log.append(f"🏆 Victory! You defeated {boss['name']} and claimed {territory['name']}!")
        # Transfer ownership
        await db.territories.update_one(
            {"id": territory_id},
            {"$set": {
                "owner_id": player_id,
                "owner_name": player["name"],
                "last_income_collected": datetime.utcnow().isoformat(),
            }}
        )
        # Update player stats
        await db.players.update_one(
            {"id": player_id},
            {"$set": {"stats.health": max(1, player_hp)}, "$inc": {"xp": 50, "reputation": 10}}
        )
        return {
            "result": "victory",
            "combat_log": combat_log,
            "territory": serialize_doc(await db.territories.find_one({"id": territory_id})),
            "rewards": {"xp": 50, "reputation": 10},
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
            {"$set": {"owner_id": None, "owner_name": None}}
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
        await db.territories.update_one(
            {"id": territory["id"]},
            {"$set": {
                "owner_id": challenger["id"],
                "owner_name": challenger["name"],
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
async def collect_territory_income(territory_id: str, player_id: str):
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
