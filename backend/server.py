from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
import httpx
import re
import ipaddress
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
import secrets
from item_icons import ITEM_ICON_URLS, CONSUMABLE_ICON_URLS, SKILL_ICON_URLS, ACCESSORY_ICON_URLS

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

# Email Configuration (Emergent Managed Resend)
EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Street Legends")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO", "hushmusicent419@gmail.com")

# Email safety gate helpers (G2/G3 compliance)
_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)

def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)

def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)

class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []
    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []
    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []

def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan(); scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Links must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Invalid URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Misleading anchor text (G3)")

async def send_email(*, to: str, subject: str, html: str, reply_to: str | None = None) -> str | None:
    """Send email via Emergent managed email service"""
    if not EMAIL_KEY:
        logger.warning("Email not configured - EMERGENT_EMAIL_KEY missing")
        return None
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    if reply_to or EMAIL_REPLY_TO:
        payload["contact_email"] = reply_to or EMAIL_REPLY_TO
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json=payload,
            )
        resp.raise_for_status()
        return resp.json().get("id")
    except httpx.HTTPStatusError as e:
        logger.error(f"Email send failed: {e.response.status_code} {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Email send error: {str(e)}")
        return None

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

# ============== OBJECT STORAGE CONFIGURATION ==============
import requests
from starlette.concurrency import run_in_threadpool

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "street-legends"
storage_key = None

def init_storage():
    """Initialize storage and get reusable storage_key"""
    global storage_key
    if storage_key:
        return storage_key
    if not EMERGENT_LLM_KEY:
        logger.warning("EMERGENT_LLM_KEY not set, storage disabled")
        return None
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Object storage initialized successfully")
        return storage_key
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload object to storage"""
    key = init_storage()
    if not key:
        raise Exception("Storage not initialized")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str) -> tuple:
    """Download object from storage"""
    key = init_storage()
    if not key:
        raise Exception("Storage not initialized")
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

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

# Durability loss rates by equipment type (DOUBLED for faster wear)
DURABILITY_LOSS = {
    "weapon": {"per_battle": 16, "on_hit": 4},       # Loses durability per battle + extra on hits
    "armor": {"per_battle": 10, "on_damage": 6},     # Loses durability per battle + extra when damaged
    "accessory": {"per_battle": 4, "passive": 2},    # Small loss per battle + passive decay
    "vehicle": {"per_use": 20, "per_territory": 30}, # Loses on movement/territory capture
}

# Repair cost multiplier by rarity (cost = base_value * multiplier * damage_percent)
# Increased by 50% for game balance
REPAIR_COST_MULTIPLIER = {
    "common": 0.75,      # 50% higher repair costs
    "uncommon": 0.975,   # Progressively more expensive
    "rare": 1.2,         # Rare items cost more
    "epic": 1.5,         # Epic items - premium repair
    "legendary": 1.8,    # Legendary - very expensive repairs
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
    """Calculate cost to repair an item - 50% higher costs"""
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
    multiplier = REPAIR_COST_MULTIPLIER.get(rarity, 1.0)
    
    # Minimum repair cost is $8 (increased from $5)
    return max(8, int(base_value * multiplier * damage_percent))

def is_item_broken(inventory_item: dict) -> bool:
    """Check if an inventory item is broken (0 durability)"""
    if isinstance(inventory_item, str):
        return False  # Legacy string items are never broken
    return inventory_item.get("durability", 100) <= 0

async def get_effective_stats(player: dict) -> dict:
    """
    Calculate effective stats based on equipment condition.
    - Broken weapon: attack = 2
    - Broken armor: defense = 0
    - Broken accessory: luck = 0
    - Broken vehicle: speed = 1
    Returns a copy of player stats with adjustments applied.
    """
    base_stats = dict(player.get("stats", {}))
    equipment = player.get("equipment", {})
    equipment_durability = player.get("equipment_durability", {})
    
    # Check each slot for broken items
    weapon_id = equipment.get("weapon")
    armor_id = equipment.get("armor")
    accessory_id = equipment.get("accessory")
    vehicle_id = equipment.get("vehicle")
    
    # Check weapon - if broken, attack = 2
    if weapon_id:
        dur = equipment_durability.get("weapon", 100)
        if dur <= 0:
            base_stats["attack"] = 2
    
    # Check armor - if broken, defense = 0
    if armor_id:
        dur = equipment_durability.get("armor", 100)
        if dur <= 0:
            base_stats["defense"] = 0
    
    # Check accessory - if broken, luck = 0
    if accessory_id:
        dur = equipment_durability.get("accessory", 100)
        if dur <= 0:
            base_stats["luck"] = 0
    
    # Check vehicle - if broken, speed = 1
    if vehicle_id:
        dur = equipment_durability.get("vehicle", 100)
        if dur <= 0:
            base_stats["speed"] = 1
    
    return base_stats

def get_speed_advantage(player_speed: int, enemy_speed: int) -> dict:
    """
    Calculate speed advantage for double attacks.
    - Player speed > 5: Player may attack twice before enemy
    - Enemy speed much higher: Enemy attacks twice more often
    Returns: {"player_double": bool, "enemy_double": bool}
    """
    result = {"player_double": False, "enemy_double": False}
    
    # Player attacks twice if speed > 5
    if player_speed > 5:
        # Chance increases with speed difference
        double_chance = min(0.6, 0.2 + (player_speed - 5) * 0.05)  # 20% base, +5% per point above 5
        if random.random() < double_chance:
            result["player_double"] = True
    
    # Enemy attacks twice if player speed is 1 (broken vehicle)
    if player_speed <= 1:
        # Enemy has 50% chance to attack twice when player speed is 1
        if random.random() < 0.5:
            result["enemy_double"] = True
    
    return result

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
    equipment_durability = player.get("equipment_durability", {})
    
    updates = {}
    
    for item_type, item_id in equipment.items():
        if not item_id:
            continue
        
        # Get or initialize durability for this equipment slot
        if item_type not in equipment_durability:
            # Initialize with max durability for new items
            max_dur = get_max_durability(item_id)
            equipment_durability[item_type] = max_dur
        
        current_dur = equipment_durability.get(item_type, 100)
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
        equipment_durability[item_type] = new_dur
    
    # Save updated equipment durability
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"equipment_durability": equipment_durability}}
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
        "stats_bonus": {"attack": 1}, "level_requirement": 1, "value": 10
    },
    "worn_jacket": {
        "id": "worn_jacket", "name": "Worn Leather Jacket", "description": "A beat-up jacket that's seen better days.",
        "equipment_type": "armor", "rarity": "common",
        "stats_bonus": {"defense": 2, "speed": 1}, "level_requirement": 1, "value": 15
    },
    "brass_knuckles": {
        "id": "brass_knuckles", "name": "Brass Knuckles", "description": "Classic street weapon. Hits hard.",
        "equipment_type": "weapon", "rarity": "uncommon",
        "stats_bonus": {"attack": 2, "speed": -1}, "level_requirement": 2, "value": 30
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
        "stats_bonus": {"attack": 1, "speed": 2}, "level_requirement": 3, "value": 40
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
        "stats_bonus": {"attack": 2}, "level_requirement": 4, "value": 45
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
        "stats_bonus": {"defense": 4, "attack": 2}, "level_requirement": 3, "value": 150
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
        "stats_bonus": {"defense": 2, "attack": 2}, "level_requirement": 1, "value": 54
    },
    # Accessories
    "night_vision_goggles": {
        "id": "night_vision_goggles", "name": "Night Vision Goggles", "description": "See everything in the dark.",
        "equipment_type": "accessory", "rarity": "rare",
        "stats_bonus": {"luck": 4, "attack": 4}, "level_requirement": 5, "value": 270
    },
    "bulletproof_watch": {
        "id": "bulletproof_watch", "name": "Bulletproof Watch", "description": "Fancy watch that can stop a bullet. Sometimes.",
        "equipment_type": "accessory", "rarity": "uncommon",
        "stats_bonus": {"defense": 2, "luck": 2}, "level_requirement": 2, "value": 106
    },
    "laser_sight": {
        "id": "laser_sight", "name": "Laser Sight", "description": "Pin-point accuracy attachment.",
        "equipment_type": "accessory", "rarity": "uncommon",
        "stats_bonus": {"attack": 6, "luck": 1}, "level_requirement": 3, "value": 120
    },
    "skull_ring": {
        "id": "skull_ring", "name": "Skull Ring", "description": "Intimidating ring. Enemies think twice.",
        "equipment_type": "accessory", "rarity": "epic",
        "stats_bonus": {"attack": 8, "luck": 4, "defense": 2}, "level_requirement": 8, "value": 540
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

# ============== 20 LEVEL-BASED VEHICLES ==============
# 2 vehicles per tier (every 10 levels)
LEVEL_VEHICLES = {
    # Level 1-10: Street Level
    "skateboard": {
        "id": "skateboard", "name": "Skateboard", "description": "Four wheels and a dream. Kickflip away from trouble.",
        "equipment_type": "vehicle", "rarity": "common",
        "stats_bonus": {"speed": 3, "luck": 1}, "level_requirement": 5, "value": 50
    },
    "stolen_scooter": {
        "id": "stolen_scooter", "name": "Stolen Scooter", "description": "Some kid's missing their ride. Your gain.",
        "equipment_type": "vehicle", "rarity": "uncommon",
        "stats_bonus": {"speed": 5}, "level_requirement": 8, "value": 120
    },
    
    # Level 11-20: Upgraded Street
    "dirt_bike": {
        "id": "dirt_bike", "name": "Dirt Bike", "description": "Off-road beast. Go where cars can't follow.",
        "equipment_type": "vehicle", "rarity": "uncommon",
        "stats_bonus": {"speed": 7, "luck": 2}, "level_requirement": 12, "value": 250
    },
    "lowrider": {
        "id": "lowrider", "name": "Lowrider", "description": "Hydraulics bouncing. All eyes on you.",
        "equipment_type": "vehicle", "rarity": "rare",
        "stats_bonus": {"speed": 5, "luck": 5, "defense": 2}, "level_requirement": 18, "value": 450
    },
    
    # Level 21-30: Professional Grade
    "muscle_car": {
        "id": "muscle_car", "name": "Muscle Car", "description": "American V8 thunder. Raw power on wheels.",
        "equipment_type": "vehicle", "rarity": "rare",
        "stats_bonus": {"speed": 9, "attack": 2}, "level_requirement": 22, "value": 650
    },
    "street_racer": {
        "id": "street_racer", "name": "Street Racer", "description": "Tuned for illegal races. Nitrous ready.",
        "equipment_type": "vehicle", "rarity": "rare",
        "stats_bonus": {"speed": 11, "luck": 3}, "level_requirement": 28, "value": 850
    },
    
    # Level 31-40: Elite
    "blacked_out_sedan": {
        "id": "blacked_out_sedan", "name": "Blacked-Out Sedan", "description": "Government plates. Tinted windows. No questions.",
        "equipment_type": "vehicle", "rarity": "epic",
        "stats_bonus": {"speed": 8, "defense": 5, "luck": 3}, "level_requirement": 32, "value": 1100
    },
    "custom_chopper": {
        "id": "custom_chopper", "name": "Custom Chopper", "description": "Chrome and leather. Born to ride.",
        "equipment_type": "vehicle", "rarity": "epic",
        "stats_bonus": {"speed": 10, "attack": 3, "luck": 4}, "level_requirement": 38, "value": 1400
    },
    
    # Level 41-50: Military Spec
    "tactical_humvee": {
        "id": "tactical_humvee", "name": "Tactical Humvee", "description": "Military surplus. Built for war zones.",
        "equipment_type": "vehicle", "rarity": "epic",
        "stats_bonus": {"speed": 7, "defense": 10, "attack": 3}, "level_requirement": 42, "value": 1800
    },
    "interceptor": {
        "id": "interceptor", "name": "Interceptor", "description": "Pursuit vehicle. Nothing outruns this.",
        "equipment_type": "vehicle", "rarity": "epic",
        "stats_bonus": {"speed": 14, "luck": 4}, "level_requirement": 48, "value": 2200
    },
    
    # Level 51-60: Advanced
    "armored_limo": {
        "id": "armored_limo", "name": "Armored Limo", "description": "VIP protection. Bulletproof luxury.",
        "equipment_type": "vehicle", "rarity": "legendary",
        "stats_bonus": {"speed": 8, "defense": 12, "luck": 5}, "level_requirement": 52, "value": 2800
    },
    "rally_car": {
        "id": "rally_car", "name": "Rally Car", "description": "WRC champion. Handles any terrain.",
        "equipment_type": "vehicle", "rarity": "legendary",
        "stats_bonus": {"speed": 16, "luck": 5}, "level_requirement": 58, "value": 3400
    },
    
    # Level 61-70: Experimental
    "stealth_van": {
        "id": "stealth_van", "name": "Stealth Van", "description": "Mobile operations center. Off the grid.",
        "equipment_type": "vehicle", "rarity": "legendary",
        "stats_bonus": {"speed": 10, "defense": 8, "luck": 8, "attack": 5}, "level_requirement": 62, "value": 4200
    },
    "hypercar": {
        "id": "hypercar", "name": "Hypercar", "description": "Million dollar machine. Breaks every speed record.",
        "equipment_type": "vehicle", "rarity": "legendary",
        "stats_bonus": {"speed": 20, "luck": 6}, "level_requirement": 68, "value": 5000
    },
    
    # Level 71-80: Black Ops
    "apc": {
        "id": "apc", "name": "APC", "description": "Armored Personnel Carrier. Rolling fortress.",
        "equipment_type": "vehicle", "rarity": "mythic",
        "stats_bonus": {"speed": 8, "defense": 18, "attack": 8}, "level_requirement": 72, "value": 6500
    },
    "attack_helicopter": {
        "id": "attack_helicopter", "name": "Attack Helicopter", "description": "Apache gunship. Death from above.",
        "equipment_type": "vehicle", "rarity": "mythic",
        "stats_bonus": {"speed": 22, "attack": 12, "luck": 5}, "level_requirement": 78, "value": 8000
    },
    
    # Level 81-90: Elite Experimental
    "hovercraft": {
        "id": "hovercraft", "name": "Hovercraft", "description": "Amphibious assault. Land or water.",
        "equipment_type": "vehicle", "rarity": "mythic",
        "stats_bonus": {"speed": 18, "defense": 10, "luck": 10}, "level_requirement": 82, "value": 10000
    },
    "stealth_jet": {
        "id": "stealth_jet", "name": "Stealth Jet", "description": "F-35 Lightning. Invisible to radar.",
        "equipment_type": "vehicle", "rarity": "mythic",
        "stats_bonus": {"speed": 28, "attack": 15, "defense": 5}, "level_requirement": 88, "value": 12500
    },
    
    # Level 91-100: Legendary
    "flying_car": {
        "id": "flying_car", "name": "Flying Car", "description": "Anti-gravity prototype. The future is now.",
        "equipment_type": "vehicle", "rarity": "mythic",
        "stats_bonus": {"speed": 30, "luck": 12, "defense": 8}, "level_requirement": 92, "value": 15000
    },
    "mech_suit": {
        "id": "mech_suit", "name": "Mech Suit", "description": "Titanium exoskeleton. One-man army.",
        "equipment_type": "vehicle", "rarity": "mythic",
        "stats_bonus": {"speed": 20, "attack": 25, "defense": 20, "luck": 10}, "level_requirement": 98, "value": 20000
    },
}

ALL_ITEMS.update(LEVEL_VEHICLES)

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

# ============== LEVEL-BASED ARMOR (20 items across 10 tiers) ==============
LEVEL_ARMOR = {
    # --- Tier 1: Level 1-10 (Street Gear) ---
    "street_hoodie": {
        "id": "street_hoodie", "name": "Street Hoodie", 
        "description": "Basic protection that lets you blend into the crowd.",
        "equipment_type": "armor", "rarity": "common",
        "stats_bonus": {"defense": 3, "speed": 2}, "level_requirement": 5, "value": 50
    },
    "denim_jacket": {
        "id": "denim_jacket", "name": "Denim Jacket",
        "description": "Tough denim with hidden pockets. Lucky find.",
        "equipment_type": "armor", "rarity": "uncommon",
        "stats_bonus": {"defense": 4, "luck": 1}, "level_requirement": 8, "value": 100
    },
    
    # --- Tier 2: Level 11-20 (Gang Wear) ---
    "biker_leather": {
        "id": "biker_leather", "name": "Biker Leather",
        "description": "Heavy leather jacket with metal studs. Intimidating.",
        "equipment_type": "armor", "rarity": "uncommon",
        "stats_bonus": {"defense": 6, "attack": 2}, "level_requirement": 12, "value": 250
    },
    "reinforced_jacket": {
        "id": "reinforced_jacket", "name": "Reinforced Jacket",
        "description": "Jacket with hidden Kevlar panels. Heavier but safer.",
        "equipment_type": "armor", "rarity": "rare",
        "stats_bonus": {"defense": 8, "speed": -1}, "level_requirement": 18, "value": 400
    },
    
    # --- Tier 3: Level 21-30 (Professional Grade) ---
    "stab_vest": {
        "id": "stab_vest", "name": "Stab Vest",
        "description": "Anti-stab protection favored by security personnel.",
        "equipment_type": "armor", "rarity": "rare",
        "stats_bonus": {"defense": 10, "attack": 3}, "level_requirement": 22, "value": 700
    },
    "combat_fatigues": {
        "id": "combat_fatigues", "name": "Combat Fatigues",
        "description": "Military surplus gear. Light and durable.",
        "equipment_type": "armor", "rarity": "rare",
        "stats_bonus": {"defense": 12, "speed": 2}, "level_requirement": 28, "value": 900
    },
    
    # --- Tier 4: Level 31-40 (Tactical) ---
    "swat_armor": {
        "id": "swat_armor", "name": "SWAT Armor",
        "description": "Police tactical armor. 'Borrowed' from an evidence locker.",
        "equipment_type": "armor", "rarity": "rare",
        "stats_bonus": {"defense": 15, "attack": 4}, "level_requirement": 32, "value": 1500
    },
    "ballistic_vest": {
        "id": "ballistic_vest", "name": "Ballistic Vest",
        "description": "Heavy-duty protection against firearms. Slows you down.",
        "equipment_type": "armor", "rarity": "epic",
        "stats_bonus": {"defense": 18, "speed": -2}, "level_requirement": 38, "value": 2000
    },
    
    # --- Tier 5: Level 41-50 (Military Spec) ---
    "plate_carrier": {
        "id": "plate_carrier", "name": "Military Plate Carrier",
        "description": "Full military-grade ceramic plate system.",
        "equipment_type": "armor", "rarity": "epic",
        "stats_bonus": {"defense": 22, "attack": 5}, "level_requirement": 42, "value": 3500
    },
    "juggernaut_suit": {
        "id": "juggernaut_suit", "name": "Juggernaut Suit",
        "description": "Bomb disposal armor repurposed for combat. Nearly unstoppable.",
        "equipment_type": "armor", "rarity": "epic",
        "stats_bonus": {"defense": 28, "speed": -4}, "level_requirement": 48, "value": 5000
    },
    
    # --- Tier 6: Level 51-60 (Elite) ---
    "ceramic_plate_armor": {
        "id": "ceramic_plate_armor", "name": "Ceramic Plate Armor",
        "description": "Advanced ceramic composite. Light yet incredibly strong.",
        "equipment_type": "armor", "rarity": "epic",
        "stats_bonus": {"defense": 32, "speed": 3}, "level_requirement": 52, "value": 8000
    },
    "black_ops_suit": {
        "id": "black_ops_suit", "name": "Black Ops Suit",
        "description": "Covert operations gear. Enhanced with lucky charms.",
        "equipment_type": "armor", "rarity": "epic",
        "stats_bonus": {"defense": 35, "luck": 5}, "level_requirement": 58, "value": 10000
    },
    
    # --- Tier 7: Level 61-70 (Experimental) ---
    "graphene_weave": {
        "id": "graphene_weave", "name": "Graphene Weave",
        "description": "Experimental graphene-laced fabric. Incredibly light and tough.",
        "equipment_type": "armor", "rarity": "legendary",
        "stats_bonus": {"defense": 40, "speed": 6}, "level_requirement": 62, "value": 18000
    },
    "exo_frame": {
        "id": "exo_frame", "name": "Exo-Frame Armor",
        "description": "Powered exoskeleton frame. Enhances strength and protection.",
        "equipment_type": "armor", "rarity": "legendary",
        "stats_bonus": {"defense": 45, "attack": 8}, "level_requirement": 68, "value": 25000
    },
    
    # --- Tier 8: Level 71-80 (Black Ops) ---
    "stealth_suit": {
        "id": "stealth_suit", "name": "Stealth Combat Suit",
        "description": "Advanced infiltration suit with adaptive camouflage.",
        "equipment_type": "armor", "rarity": "legendary",
        "stats_bonus": {"defense": 50, "speed": 8, "luck": 5}, "level_requirement": 72, "value": 40000
    },
    "heavy_assault_armor": {
        "id": "heavy_assault_armor", "name": "Heavy Assault Armor",
        "description": "Maximum protection for front-line combat. Walk through bullets.",
        "equipment_type": "armor", "rarity": "legendary",
        "stats_bonus": {"defense": 60, "attack": 10, "speed": -5}, "level_requirement": 78, "value": 55000
    },
    
    # --- Tier 9: Level 81-90 (Futuristic) ---
    "nano_fiber_suit": {
        "id": "nano_fiber_suit", "name": "Nano-Fiber Suit",
        "description": "Self-repairing nanotech armor. The future of protection.",
        "equipment_type": "armor", "rarity": "legendary",
        "stats_bonus": {"defense": 70, "speed": 10, "attack": 5}, "level_requirement": 82, "value": 90000
    },
    "titan_armor": {
        "id": "titan_armor", "name": "Titan Armor",
        "description": "Massive powered armor suit. You ARE the tank.",
        "equipment_type": "armor", "rarity": "legendary",
        "stats_bonus": {"defense": 85, "attack": 15, "speed": -3}, "level_requirement": 88, "value": 120000
    },
    
    # --- Tier 10: Level 91-100 (Mythic) ---
    "quantum_shield_armor": {
        "id": "quantum_shield_armor", "name": "Quantum Shield Armor",
        "description": "Reality-bending protection. Attacks phase through you.",
        "equipment_type": "armor", "rarity": "mythic",
        "stats_bonus": {"defense": 100, "speed": 12, "luck": 10}, "level_requirement": 92, "value": 200000
    },
    "godplate": {
        "id": "godplate", "name": "Godplate",
        "description": "Armor of legends. Said to make the wearer invincible.",
        "equipment_type": "armor", "rarity": "mythic",
        "stats_bonus": {"defense": 150, "attack": 20, "speed": 15}, "level_requirement": 98, "value": 500000
    },
}

ALL_ITEMS.update(LEVEL_ARMOR)

# ============== LEVEL-BASED ACCESSORIES (20 items across 10 tiers) ==============
LEVEL_ACCESSORIES = {
    # --- Tier 1: Level 1-10 (Street Bling) ---
    "bandana": {
        "id": "bandana", "name": "Street Bandana",
        "description": "Gang colors that boost your rep on the streets.",
        "equipment_type": "accessory", "rarity": "common",
        "stats_bonus": {"luck": 2, "speed": 1}, "level_requirement": 5, "value": 75
    },
    "dog_tags": {
        "id": "dog_tags", "name": "Dog Tags",
        "description": "Military surplus tags. A reminder of tougher times.",
        "equipment_type": "accessory", "rarity": "uncommon",
        "stats_bonus": {"attack": 2, "defense": 1, "luck": 1}, "level_requirement": 8, "value": 150
    },
    
    # --- Tier 2: Level 11-20 (Street Cred) ---
    "silver_chain": {
        "id": "silver_chain", "name": "Silver Chain",
        "description": "Heavy silver links. Shows you're moving up.",
        "equipment_type": "accessory", "rarity": "uncommon",
        "stats_bonus": {"luck": 4, "defense": 2}, "level_requirement": 12, "value": 300
    },
    "brass_knuckle_rings": {
        "id": "brass_knuckle_rings", "name": "Brass Knuckle Rings",
        "description": "Stylish rings that double as weapons.",
        "equipment_type": "accessory", "rarity": "rare",
        "stats_bonus": {"attack": 5, "luck": 2}, "level_requirement": 18, "value": 500
    },
    
    # --- Tier 3: Level 21-30 (Hustler Gear) ---
    "diamond_earring": {
        "id": "diamond_earring", "name": "Diamond Earring",
        "description": "Single diamond stud. Ice cold flex.",
        "equipment_type": "accessory", "rarity": "rare",
        "stats_bonus": {"luck": 6, "speed": 2}, "level_requirement": 22, "value": 800
    },
    "tactical_gloves": {
        "id": "tactical_gloves", "name": "Tactical Gloves",
        "description": "Kevlar-lined combat gloves. Better grip, harder hits.",
        "equipment_type": "accessory", "rarity": "rare",
        "stats_bonus": {"attack": 6, "defense": 3, "luck": 2}, "level_requirement": 28, "value": 1100
    },
    
    # --- Tier 4: Level 31-40 (Boss Accessories) ---
    "platinum_watch": {
        "id": "platinum_watch", "name": "Platinum Watch",
        "description": "Swiss timepiece worth more than most cars.",
        "equipment_type": "accessory", "rarity": "rare",
        "stats_bonus": {"luck": 8, "defense": 3, "speed": 2}, "level_requirement": 32, "value": 1800
    },
    "combat_earpiece": {
        "id": "combat_earpiece", "name": "Combat Earpiece",
        "description": "Military-grade communication device. Stay connected.",
        "equipment_type": "accessory", "rarity": "epic",
        "stats_bonus": {"attack": 8, "speed": 4, "luck": 3}, "level_requirement": 38, "value": 2500
    },
    
    # --- Tier 5: Level 41-50 (Elite Bling) ---
    "diamond_grillz": {
        "id": "diamond_grillz", "name": "Diamond Grillz",
        "description": "Full set of diamond teeth. Intimidating smile.",
        "equipment_type": "accessory", "rarity": "epic",
        "stats_bonus": {"luck": 12, "attack": 5}, "level_requirement": 42, "value": 4000
    },
    "tactical_belt": {
        "id": "tactical_belt", "name": "Tactical Belt",
        "description": "Military utility belt with hidden compartments.",
        "equipment_type": "accessory", "rarity": "epic",
        "stats_bonus": {"defense": 8, "speed": 5, "luck": 4}, "level_requirement": 48, "value": 5500
    },
    
    # --- Tier 6: Level 51-60 (Crime Lord) ---
    "ruby_pendant": {
        "id": "ruby_pendant", "name": "Blood Ruby Pendant",
        "description": "Deep red ruby said to be cursed. Grants power at a price.",
        "equipment_type": "accessory", "rarity": "epic",
        "stats_bonus": {"attack": 12, "luck": 8}, "level_requirement": 52, "value": 9000
    },
    "titanium_bracelet": {
        "id": "titanium_bracelet", "name": "Titanium Bracelet",
        "description": "Aerospace-grade titanium. Light and nearly indestructible.",
        "equipment_type": "accessory", "rarity": "epic",
        "stats_bonus": {"defense": 10, "speed": 6, "luck": 6}, "level_requirement": 58, "value": 12000
    },
    
    # --- Tier 7: Level 61-70 (Kingpin) ---
    "emerald_ring": {
        "id": "emerald_ring", "name": "Emerald Signet Ring",
        "description": "Cartel boss signature. Opens doors and closes caskets.",
        "equipment_type": "accessory", "rarity": "legendary",
        "stats_bonus": {"attack": 15, "luck": 12, "defense": 5}, "level_requirement": 62, "value": 20000
    },
    "exo_gloves": {
        "id": "exo_gloves", "name": "Exoskeleton Gloves",
        "description": "Powered gloves that enhance strength tenfold.",
        "equipment_type": "accessory", "rarity": "legendary",
        "stats_bonus": {"attack": 18, "speed": 8, "luck": 6}, "level_requirement": 68, "value": 28000
    },
    
    # --- Tier 8: Level 71-80 (Underworld Elite) ---
    "obsidian_amulet": {
        "id": "obsidian_amulet", "name": "Obsidian Amulet",
        "description": "Ancient volcanic glass. Said to absorb enemy attacks.",
        "equipment_type": "accessory", "rarity": "legendary",
        "stats_bonus": {"defense": 15, "luck": 15, "attack": 8}, "level_requirement": 72, "value": 45000
    },
    "neural_interface": {
        "id": "neural_interface", "name": "Neural Interface",
        "description": "Direct brain-computer link. Think faster, react faster.",
        "equipment_type": "accessory", "rarity": "legendary",
        "stats_bonus": {"speed": 15, "attack": 12, "luck": 10}, "level_requirement": 78, "value": 60000
    },
    
    # --- Tier 9: Level 81-90 (Shadow Council) ---
    "void_crystal": {
        "id": "void_crystal", "name": "Void Crystal Pendant",
        "description": "Crystal from another dimension. Reality bends around it.",
        "equipment_type": "accessory", "rarity": "legendary",
        "stats_bonus": {"luck": 20, "attack": 15, "defense": 10}, "level_requirement": 82, "value": 100000
    },
    "quantum_watch": {
        "id": "quantum_watch", "name": "Quantum Watch",
        "description": "Experimental timepiece. Lets you see moments ahead.",
        "equipment_type": "accessory", "rarity": "legendary",
        "stats_bonus": {"speed": 20, "luck": 18, "defense": 8}, "level_requirement": 88, "value": 140000
    },
    
    # --- Tier 10: Level 91-100 (Mythic) ---
    "crown_of_shadows": {
        "id": "crown_of_shadows", "name": "Crown of Shadows",
        "description": "Worn by the king of the underworld. Absolute authority.",
        "equipment_type": "accessory", "rarity": "mythic",
        "stats_bonus": {"luck": 25, "attack": 20, "defense": 15, "speed": 10}, "level_requirement": 92, "value": 250000
    },
    "infinity_band": {
        "id": "infinity_band", "name": "Infinity Band",
        "description": "A ring containing infinite power. The ultimate accessory.",
        "equipment_type": "accessory", "rarity": "mythic",
        "stats_bonus": {"attack": 30, "defense": 20, "speed": 15, "luck": 30}, "level_requirement": 98, "value": 500000
    },
}

ALL_ITEMS.update(LEVEL_ACCESSORIES)

# Apply icons to accessories
for acc_id, acc_data in LEVEL_ACCESSORIES.items():
    if acc_id in ACCESSORY_ICON_URLS:
        acc_data["icon_url"] = ACCESSORY_ICON_URLS[acc_id]
        # Also update ALL_ITEMS
        if acc_id in ALL_ITEMS:
            ALL_ITEMS[acc_id]["icon_url"] = ACCESSORY_ICON_URLS[acc_id]

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

# Apply icon URLs to all equipment items
def _apply_item_icons():
    """Apply icon URLs from item_icons.py to all items"""
    for item_id, item_data in ALL_ITEMS.items():
        if item_id in ITEM_ICON_URLS:
            item_data["icon_url"] = ITEM_ICON_URLS[item_id]
    for item_id, item_data in CONSUMABLE_ITEMS.items():
        if item_id in CONSUMABLE_ICON_URLS:
            item_data["icon_url"] = CONSUMABLE_ICON_URLS[item_id]

_apply_item_icons()

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

# Apply icons to skills
for skill_id, skill_data in SKILLS.items():
    if skill_id in SKILL_ICON_URLS:
        skill_data["icon_url"] = SKILL_ICON_URLS[skill_id]

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
    profile_picture: Optional[str] = None  # Storage path for profile picture
    # Social fields
    followers: List[str] = Field(default_factory=list)  # List of player IDs who follow this player
    following: List[str] = Field(default_factory=list)  # List of player IDs this player follows
    friends: List[str] = Field(default_factory=list)  # List of mutual friend player IDs
    friend_requests_sent: List[str] = Field(default_factory=list)  # Outgoing friend requests
    friend_requests_received: List[str] = Field(default_factory=list)  # Incoming friend requests
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
    email: Optional[str] = None  # Optional but needed for password reset

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
    total_reputation: int = 0
    icon_path: Optional[str] = None  # Storage path for custom guild icon
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
    if data.email:
        player_dict["email"] = data.email.lower().strip()
    
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

# ============== PASSWORD RESET ==============
class ForgotPasswordRequest(BaseModel):
    email_or_username: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@api_router.post("/auth/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    """
    Request a password reset link. Sends email if account exists.
    For security, always returns success to avoid revealing account existence.
    """
    identifier = data.email_or_username.strip().lower()
    
    # Find player by email or username
    player = await db.players.find_one({
        "$or": [
            {"email": identifier},
            {"username": identifier}
        ]
    })
    
    if player and player.get("email"):
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Store token in database
        await db.password_reset_tokens.delete_many({"player_id": player["id"]})  # Remove old tokens
        await db.password_reset_tokens.insert_one({
            "token": reset_token,
            "player_id": player["id"],
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "used": False
        })
        
        # Create reset URL (web-based for universal access)
        reset_url = f"https://streetlegends.app/reset-password?token={reset_token}"
        
        # Email HTML content
        email_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #1a1a1a; color: #ffffff;">
            <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #e74c3c;">
                <h1 style="color: #e74c3c; margin: 0;">STREET LEGENDS</h1>
                <p style="color: #888; margin: 5px 0;">Password Reset Request</p>
            </div>
            <div style="padding: 30px 0;">
                <p style="color: #ccc; font-size: 16px;">Hey <strong style="color: #fff;">{player.get('name', 'Legend')}</strong>,</p>
                <p style="color: #ccc; font-size: 14px; line-height: 1.6;">
                    We received a request to reset your password. Use the code below to reset it in the app:
                </p>
                <div style="background: #222; border: 2px solid #e74c3c; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                    <p style="color: #888; font-size: 12px; margin: 0 0 10px;">YOUR RESET CODE</p>
                    <p style="color: #e74c3c; font-size: 24px; font-weight: bold; letter-spacing: 2px; margin: 0;">{reset_token[:8].upper()}</p>
                </div>
                <p style="color: #888; font-size: 12px; text-align: center;">
                    This code expires in <strong style="color: #f39c12;">1 hour</strong>.
                </p>
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    If you didn't request this, you can safely ignore this email.
                </p>
            </div>
            <div style="border-top: 1px solid #333; padding-top: 20px; text-align: center;">
                <p style="color: #555; font-size: 11px;">
                    Street Legends - Rule the Streets
                </p>
            </div>
        </div>
        """
        
        # Send email
        email_id = await send_email(
            to=player["email"],
            subject="Street Legends - Password Reset Code",
            html=email_html
        )
        
        if email_id:
            logger.info(f"Password reset email sent to {player['email']} for player {player['id']}")
        else:
            logger.warning(f"Failed to send password reset email to {player['email']}")
    
    # Always return success for security
    return {
        "message": "If an account exists with this email/username, a reset code has been sent.",
        "success": True
    }

@api_router.post("/auth/reset-password")
async def reset_password(data: ResetPasswordRequest):
    """
    Reset password using a valid token.
    Token can be the full token or the first 8 characters (uppercase code shown to user).
    """
    if len(data.new_password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    
    # Find token - support both full token and short code
    token_query = data.token.strip()
    
    # Try to find by full token first, then by prefix match (case-insensitive for short code)
    token_record = await db.password_reset_tokens.find_one({
        "token": token_query,
        "used": False
    })
    
    if not token_record:
        # Try prefix match for short code
        all_tokens = await db.password_reset_tokens.find({"used": False}).to_list(100)
        for t in all_tokens:
            if t["token"][:8].upper() == token_query.upper():
                token_record = t
                break
    
    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    
    # Check expiration
    if token_record["expires_at"] < datetime.utcnow():
        await db.password_reset_tokens.delete_one({"_id": token_record["_id"]})
        raise HTTPException(status_code=400, detail="Reset code has expired. Please request a new one.")
    
    # Update password
    player_id = token_record["player_id"]
    new_hash = pwd_context.hash(data.new_password)
    
    result = await db.players.update_one(
        {"id": player_id},
        {"$set": {"password_hash": new_hash}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Mark token as used
    await db.password_reset_tokens.update_one(
        {"_id": token_record["_id"]},
        {"$set": {"used": True, "used_at": datetime.utcnow()}}
    )
    
    logger.info(f"Password reset successful for player {player_id}")
    
    return {
        "message": "Password has been reset successfully. You can now login with your new password.",
        "success": True
    }

@api_router.post("/auth/change-password/{player_id}")
async def change_password(player_id: str, data: ChangePasswordRequest):
    """
    Change password for a logged-in user. Requires current password verification.
    """
    if len(data.new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters")
    
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Verify current password
    if not pwd_context.verify(data.current_password, player.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Update password
    new_hash = pwd_context.hash(data.new_password)
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"password_hash": new_hash}}
    )
    
    logger.info(f"Password changed for player {player_id}")
    
    return {
        "message": "Password changed successfully",
        "success": True
    }

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


@api_router.post("/players/{player_id}/logout")
async def logout_player(player_id: str):
    """
    Log out a player - removes their character from the game world.
    Sets is_logged_out=True and clears their visible position.
    """
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {
            "is_logged_out": True,
            "logged_out_at": datetime.utcnow(),
            "visible_on_map": False,
        }}
    )
    
    return {"message": "Logged out successfully", "player_id": player_id}


@api_router.post("/players/{player_id}/login")
async def login_player(player_id: str):
    """
    Log in a player - makes their character visible in the game world.
    """
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {
            "is_logged_out": False,
            "logged_out_at": None,
            "visible_on_map": True,
            "last_active": datetime.utcnow(),
        }}
    )
    
    return {"message": "Logged in successfully", "player_id": player_id}


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

# IMPORTANT: Static routes must come BEFORE dynamic {player_id} routes
@api_router.get("/players/search")
async def search_players_route(name: str, limit: int = 20):
    """Search players by name (case-insensitive partial match)"""
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
    
    players = await db.players.find(
        {"name": {"$regex": name, "$options": "i"}},
        {"id": 1, "name": 1, "level": 1, "character_class": 1, "profile_picture": 1, "profile_pic": 1, "wins": 1, "reputation": 1}
    ).limit(limit).to_list(limit)
    
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "level": p["level"],
            "character_class": p["character_class"],
            "profile_picture": p.get("profile_picture"),
            "profile_pic": p.get("profile_pic"),
            "wins": p.get("wins", 0),
            "reputation": p.get("reputation", 0),
        }
        for p in players
    ]

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
    """Get players within radius (meters) - excludes logged out and inactive (30+ min) players"""
    player = await db.players.find_one({"id": player_id})
    if not player or not player.get("position"):
        raise HTTPException(status_code=404, detail="Player not found or no position")
    
    # 30 minute inactivity threshold
    inactivity_threshold = datetime.utcnow() - timedelta(minutes=30)
    
    player_pos = Position(**player["position"])
    all_players = await db.players.find(
        {
            "id": {"$ne": player_id}, 
            "position": {"$exists": True},
            # Exclude logged out players
            "$or": [
                {"is_logged_out": {"$ne": True}},
                {"is_logged_out": {"$exists": False}}
            ],
            # Must have been active in last 30 minutes
            "last_active": {"$gte": inactivity_threshold}
        },
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

# ============== SOCIAL / FRIENDS ENDPOINTS ==============

@api_router.get("/players/{player_id}/social-stats")
async def get_social_stats(player_id: str):
    """Get follower/following/friends counts for a player"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    return {
        "followers_count": len(player.get("followers", [])),
        "following_count": len(player.get("following", [])),
        "friends_count": len(player.get("friends", [])),
        "pending_requests": len(player.get("friend_requests_received", [])),
    }

@api_router.get("/players/{player_id}/friends")
async def get_friends_list(player_id: str):
    """Get full friends list with details"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    friend_ids = player.get("friends", [])
    if not friend_ids:
        return []
    
    friends = await db.players.find(
        {"id": {"$in": friend_ids}},
        {"id": 1, "name": 1, "level": 1, "character_class": 1, "profile_picture": 1, "profile_pic": 1, 
         "wins": 1, "losses": 1, "reputation": 1, "last_active": 1, "position": 1}
    ).to_list(100)
    
    return [
        {
            "id": f["id"],
            "name": f["name"],
            "level": f["level"],
            "character_class": f["character_class"],
            "profile_picture": f.get("profile_picture"),
            "profile_pic": f.get("profile_pic"),
            "wins": f.get("wins", 0),
            "losses": f.get("losses", 0),
            "reputation": f.get("reputation", 0),
            "last_active": f.get("last_active"),
            "is_online": (datetime.utcnow() - f.get("last_active", datetime.min)).total_seconds() < 300 if f.get("last_active") else False,
        }
        for f in friends
    ]

@api_router.get("/players/{player_id}/friend-requests")
async def get_friend_requests(player_id: str):
    """Get pending friend requests"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    request_ids = player.get("friend_requests_received", [])
    if not request_ids:
        return []
    
    requesters = await db.players.find(
        {"id": {"$in": request_ids}},
        {"id": 1, "name": 1, "level": 1, "character_class": 1, "profile_picture": 1, "profile_pic": 1}
    ).to_list(100)
    
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "level": r["level"],
            "character_class": r["character_class"],
            "profile_picture": r.get("profile_picture"),
            "profile_pic": r.get("profile_pic"),
        }
        for r in requesters
    ]

@api_router.get("/players/{player_id}/relationship/{target_id}")
async def get_relationship_status(player_id: str, target_id: str):
    """Get the relationship status between two players"""
    player = await db.players.find_one({"id": player_id})
    target = await db.players.find_one({"id": target_id})
    
    if not player or not target:
        raise HTTPException(status_code=404, detail="Player not found")
    
    is_following = target_id in player.get("following", [])
    is_followed_by = player_id in target.get("following", [])
    is_friend = target_id in player.get("friends", [])
    has_sent_request = target_id in player.get("friend_requests_sent", [])
    has_received_request = target_id in player.get("friend_requests_received", [])
    
    return {
        "is_following": is_following,
        "is_followed_by": is_followed_by,
        "is_friend": is_friend,
        "has_sent_friend_request": has_sent_request,
        "has_received_friend_request": has_received_request,
    }

@api_router.post("/players/{player_id}/follow/{target_id}")
async def follow_player(player_id: str, target_id: str):
    """Follow another player (one-way)"""
    if player_id == target_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    player = await db.players.find_one({"id": player_id})
    target = await db.players.find_one({"id": target_id})
    
    if not player or not target:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if target_id in player.get("following", []):
        raise HTTPException(status_code=400, detail="Already following this player")
    
    # Add to player's following list
    await db.players.update_one(
        {"id": player_id},
        {"$addToSet": {"following": target_id}}
    )
    
    # Add to target's followers list
    await db.players.update_one(
        {"id": target_id},
        {"$addToSet": {"followers": player_id}}
    )
    
    return {"message": f"Now following {target['name']}", "success": True}

@api_router.delete("/players/{player_id}/unfollow/{target_id}")
async def unfollow_player(player_id: str, target_id: str):
    """Unfollow a player"""
    player = await db.players.find_one({"id": player_id})
    target = await db.players.find_one({"id": target_id})
    
    if not player or not target:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Remove from player's following list
    await db.players.update_one(
        {"id": player_id},
        {"$pull": {"following": target_id}}
    )
    
    # Remove from target's followers list
    await db.players.update_one(
        {"id": target_id},
        {"$pull": {"followers": player_id}}
    )
    
    return {"message": f"Unfollowed {target['name']}", "success": True}

@api_router.post("/players/{player_id}/friend-request/{target_id}")
async def send_friend_request(player_id: str, target_id: str):
    """Send a friend request to another player"""
    if player_id == target_id:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    
    player = await db.players.find_one({"id": player_id})
    target = await db.players.find_one({"id": target_id})
    
    if not player or not target:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Check if already friends
    if target_id in player.get("friends", []):
        raise HTTPException(status_code=400, detail="Already friends with this player")
    
    # Check if request already sent
    if target_id in player.get("friend_requests_sent", []):
        raise HTTPException(status_code=400, detail="Friend request already sent")
    
    # Check if target already sent us a request - auto accept
    if target_id in player.get("friend_requests_received", []):
        # Auto-accept: they sent us a request, we're sending one back = friends
        await db.players.update_one(
            {"id": player_id},
            {
                "$addToSet": {"friends": target_id},
                "$pull": {"friend_requests_received": target_id}
            }
        )
        await db.players.update_one(
            {"id": target_id},
            {
                "$addToSet": {"friends": player_id},
                "$pull": {"friend_requests_sent": player_id}
            }
        )
        return {"message": f"You are now friends with {target['name']}!", "success": True, "became_friends": True}
    
    # Send the friend request
    await db.players.update_one(
        {"id": player_id},
        {"$addToSet": {"friend_requests_sent": target_id}}
    )
    await db.players.update_one(
        {"id": target_id},
        {"$addToSet": {"friend_requests_received": player_id}}
    )
    
    return {"message": f"Friend request sent to {target['name']}", "success": True, "became_friends": False}

@api_router.post("/players/{player_id}/accept-friend/{target_id}")
async def accept_friend_request(player_id: str, target_id: str):
    """Accept a pending friend request"""
    player = await db.players.find_one({"id": player_id})
    target = await db.players.find_one({"id": target_id})
    
    if not player or not target:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Check if there's a pending request
    if target_id not in player.get("friend_requests_received", []):
        raise HTTPException(status_code=400, detail="No pending friend request from this player")
    
    # Add each other as friends and clean up requests
    await db.players.update_one(
        {"id": player_id},
        {
            "$addToSet": {"friends": target_id},
            "$pull": {"friend_requests_received": target_id}
        }
    )
    await db.players.update_one(
        {"id": target_id},
        {
            "$addToSet": {"friends": player_id},
            "$pull": {"friend_requests_sent": player_id}
        }
    )
    
    return {"message": f"You are now friends with {target['name']}!", "success": True}

@api_router.post("/players/{player_id}/reject-friend/{target_id}")
async def reject_friend_request(player_id: str, target_id: str):
    """Reject a pending friend request"""
    player = await db.players.find_one({"id": player_id})
    target = await db.players.find_one({"id": target_id})
    
    if not player or not target:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Remove the request
    await db.players.update_one(
        {"id": player_id},
        {"$pull": {"friend_requests_received": target_id}}
    )
    await db.players.update_one(
        {"id": target_id},
        {"$pull": {"friend_requests_sent": player_id}}
    )
    
    return {"message": "Friend request rejected", "success": True}

@api_router.delete("/players/{player_id}/remove-friend/{target_id}")
async def remove_friend(player_id: str, target_id: str):
    """Remove a friend"""
    player = await db.players.find_one({"id": player_id})
    target = await db.players.find_one({"id": target_id})
    
    if not player or not target:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Remove from both friends lists
    await db.players.update_one(
        {"id": player_id},
        {"$pull": {"friends": target_id}}
    )
    await db.players.update_one(
        {"id": target_id},
        {"$pull": {"friends": player_id}}
    )
    
    return {"message": f"Removed {target['name']} from friends", "success": True}

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
    
    # Get effective stats based on equipment condition
    player_stats = await get_effective_stats(player)
    
    combat_log = battle["combat_log"]
    player_health = battle["player_health"]
    enemy_health = battle["enemy_health"]
    player_energy = battle["player_energy"]
    
    # Check for speed advantage (double attacks)
    speed_adv = get_speed_advantage(player_stats.get("speed", 5), enemy_stats.get("speed", 5))
    
    # Determine how many times player attacks this turn (only for attack action)
    player_attacks = 2 if speed_adv["player_double"] and action.action == "attack" else 1
    if player_attacks > 1:
        combat_log.append("⚡ Your superior speed allows a double attack!")
    
    # Player action(s)
    if action.action == "attack":
        for attack_num in range(player_attacks):
            if enemy_health <= 0:
                break  # Enemy already defeated
                
            # Miss chance: 10% base, reduced by luck (min 5%). If luck is 0 (broken accessory), 25% miss
            luck_val = player_stats.get("luck", 0)
            if luck_val <= 0:
                miss_chance = 0.25  # 25% miss chance with broken accessory
            else:
                miss_chance = max(0.05, 0.10 - (luck_val * 0.005))
            
            if random.random() < miss_chance:
                if luck_val <= 0:
                    combat_log.append("Your attack MISSED! (Broken accessory - bad luck)")
                else:
                    combat_log.append("Your attack MISSED!")
            else:
                damage = max(1, player_stats["attack"] - enemy_stats.get("defense", 0) // 2)
                # Crit chance: based on luck (5% base + luck bonus). 0 luck = no crits
                crit_chance = 0.05 + (luck_val * 0.01) if luck_val > 0 else 0
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
            # Save the player's current HP and energy when fleeing (damage persists)
            await db.players.update_one(
                {"id": player["id"]},
                {
                    "$set": {
                        "stats.health": max(1, player_health),
                        "stats.energy": max(0, player_energy),
                        "last_health_regen": datetime.utcnow().isoformat(),
                    }
                }
            )
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
    # Determine how many times enemy attacks this turn (double attack if player speed is 1)
    enemy_attacks = 2 if speed_adv["enemy_double"] else 1
    if enemy_attacks > 1:
        combat_log.append(f"⚡ {battle['enemy_name']} exploits your low speed and attacks twice!")
    
    for enemy_attack_num in range(enemy_attacks):
        if player_health <= 0:
            break  # Player already defeated
            
        # Enemy miss chance: 12% base
        if random.random() < 0.12:
            combat_log.append(f"{battle['enemy_name']}'s attack MISSED!")
        else:
            # Defense = 0 if armor is broken
            defense_val = player_stats.get("defense", 0)
            enemy_damage = max(1, enemy_stats.get("attack", 10) - defense_val // 2)
            if action.action == "defend":
                enemy_damage = enemy_damage // 2
            
            # Extra damage message if armor is broken
            if defense_val <= 0:
                enemy_damage = max(1, enemy_stats.get("attack", 10))  # Full damage with no defense
            
            # Enemy crit chance: 8%
            if random.random() < 0.08:
                enemy_damage = int(enemy_damage * 2.0)
                combat_log.append(f"💥 {battle['enemy_name']} lands a CRITICAL HIT for {enemy_damage} damage!")
            else:
                if defense_val <= 0:
                    combat_log.append(f"{battle['enemy_name']} attacks for {enemy_damage} damage! (No defense - broken armor)")
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
                # This player has accepted this mission - HIDE it from map (only show in tracker)
                continue  # Skip accepted missions - they shouldn't appear on map
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
    
    # Get member details with profile pictures
    # Support both profile_picture (Object Storage) and profile_pic (legacy base64)
    members = await db.players.find({"id": {"$in": guild["members"]}}).to_list(100)
    guild["member_details"] = [
        {
            "id": m["id"], 
            "name": m["name"], 
            "level": m["level"], 
            "character_class": m["character_class"],
            "reputation": m.get("reputation", 0),
            "profile_picture": m.get("profile_picture"),  # Object Storage path
            "profile_pic": m.get("profile_pic")  # Legacy base64 data
        }
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


# ============== GUILD CHAT ENDPOINTS ==============

@api_router.get("/guilds/{guild_id}/chat")
async def get_guild_chat(guild_id: str, player_id: str, limit: int = 50):
    """Get guild chat messages - only for guild members"""
    # Verify player is in the guild
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    # Get recent messages
    messages = await db.guild_chat.find({"guild_id": guild_id}).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Return in chronological order (oldest first)
    messages.reverse()
    
    return [serialize_doc(m) for m in messages]


@api_router.post("/guilds/{guild_id}/chat")
async def send_guild_message(guild_id: str, player_id: str, message: str):
    """Send a message to guild chat - only for guild members"""
    # Verify player is in the guild
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    # Validate message
    if not message or len(message.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if len(message) > 500:
        raise HTTPException(status_code=400, detail="Message too long (max 500 characters)")
    
    # Create message
    chat_message = {
        "id": str(uuid.uuid4()),
        "guild_id": guild_id,
        "player_id": player_id,
        "player_name": player.get("name", "Unknown"),
        "player_level": player.get("level", 1),
        "message": message.strip(),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    await db.guild_chat.insert_one(chat_message)
    
    # Clean up old messages (keep only last 200 per guild)
    message_count = await db.guild_chat.count_documents({"guild_id": guild_id})
    if message_count > 200:
        oldest_messages = await db.guild_chat.find({"guild_id": guild_id}).sort("timestamp", 1).limit(message_count - 200).to_list(message_count - 200)
        if oldest_messages:
            oldest_ids = [m["id"] for m in oldest_messages]
            await db.guild_chat.delete_many({"id": {"$in": oldest_ids}})
    
    return serialize_doc(chat_message)


@api_router.delete("/guilds/{guild_id}/chat/{message_id}")
async def delete_guild_message(guild_id: str, message_id: str, player_id: str):
    """Delete a guild chat message - only by message sender or guild leader"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    message = await db.guild_chat.find_one({"id": message_id, "guild_id": guild_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check if player is message sender or guild leader
    guild = await db.guilds.find_one({"id": guild_id})
    is_leader = guild and guild.get("leader_id") == player_id
    is_sender = message.get("player_id") == player_id
    
    if not is_leader and not is_sender:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")
    
    await db.guild_chat.delete_one({"id": message_id})
    return {"message": "Message deleted"}


# ============== GUILD BATTLES SYSTEM ==============
# Constants for Guild Battles
GUILD_BATTLE_MIN_MEMBERS = 5
GUILD_BATTLE_COOLDOWN_HOURS = 24
GUILD_BATTLE_CHALLENGE_EXPIRE_HOURS = 24
GUILD_BATTLE_FORMATS = ["3v3", "5v5"]

# Reward amounts per participant
GUILD_BATTLE_REWARDS = {
    "winner": {
        "cash": 5000,
        "xp": 500,
        "reputation": 100
    },
    "guild_reputation": 250  # Added to winning guild
}


def calculate_combat_power(player: dict) -> int:
    """Calculate a player's total combat power for guild battle selection"""
    stats = player.get("stats", {})
    # Combat power = attack*2 + defense + speed + (health/10) + level*10
    power = (
        stats.get("attack", 10) * 2 +
        stats.get("defense", 10) +
        stats.get("speed", 10) +
        stats.get("max_health", 100) // 10 +
        player.get("level", 1) * 10
    )
    return power


async def get_top_guild_members(guild_id: str, count: int) -> list:
    """Get top N members of a guild by combat power"""
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        return []
    
    member_ids = guild.get("members", [])
    members = await db.players.find({"id": {"$in": member_ids}}).to_list(100)
    
    # Sort by combat power (descending)
    members_with_power = [(m, calculate_combat_power(m)) for m in members]
    members_with_power.sort(key=lambda x: x[1], reverse=True)
    
    return [m[0] for m, _ in members_with_power[:count]]


@api_router.get("/guilds/{guild_id}/battle/eligibility")
async def check_guild_battle_eligibility(guild_id: str):
    """Check if a guild is eligible for guild battles"""
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    member_count = len(guild.get("members", []))
    is_eligible = member_count >= GUILD_BATTLE_MIN_MEMBERS
    
    # Check cooldown
    last_battle_time = guild.get("last_guild_battle")
    on_cooldown = False
    cooldown_remaining = 0
    
    if last_battle_time:
        if isinstance(last_battle_time, str):
            last_battle_time = datetime.fromisoformat(last_battle_time.replace('Z', '+00:00'))
        cooldown_end = last_battle_time + timedelta(hours=GUILD_BATTLE_COOLDOWN_HOURS)
        if datetime.utcnow() < cooldown_end:
            on_cooldown = True
            cooldown_remaining = int((cooldown_end - datetime.utcnow()).total_seconds() // 3600)
    
    return {
        "guild_id": guild_id,
        "member_count": member_count,
        "required_members": GUILD_BATTLE_MIN_MEMBERS,
        "is_eligible": is_eligible,
        "on_cooldown": on_cooldown,
        "cooldown_remaining_hours": cooldown_remaining,
        "message": f"Need {GUILD_BATTLE_MIN_MEMBERS - member_count} more members" if not is_eligible else "Eligible for battles" if not on_cooldown else f"Cooldown: {cooldown_remaining}h remaining"
    }


@api_router.post("/guilds/{guild_id}/battle/challenge")
async def create_guild_battle_challenge(
    guild_id: str,
    target_guild_id: str,
    player_id: str,
    format: str = "3v3"
):
    """Create a guild battle challenge - only by leader or officers"""
    if format not in GUILD_BATTLE_FORMATS:
        raise HTTPException(status_code=400, detail=f"Invalid format. Choose: {GUILD_BATTLE_FORMATS}")
    
    # Verify challenger
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    challenger_guild = await db.guilds.find_one({"id": guild_id})
    if not challenger_guild:
        raise HTTPException(status_code=404, detail="Your guild not found")
    
    # Check if player is leader or officer
    is_leader = challenger_guild.get("leader_id") == player_id
    is_officer = player_id in challenger_guild.get("officers", [])
    if not is_leader and not is_officer:
        raise HTTPException(status_code=403, detail="Only guild leaders or officers can issue challenges")
    
    # Check challenger guild eligibility
    challenger_members = len(challenger_guild.get("members", []))
    if challenger_members < GUILD_BATTLE_MIN_MEMBERS:
        raise HTTPException(
            status_code=400, 
            detail=f"Your guild needs at least {GUILD_BATTLE_MIN_MEMBERS} members to battle. Current: {challenger_members}"
        )
    
    # Check format requirements
    format_size = int(format[0])  # "3v3" -> 3, "5v5" -> 5
    if challenger_members < format_size:
        raise HTTPException(
            status_code=400,
            detail=f"Your guild needs at least {format_size} members for {format} format"
        )
    
    # Check cooldown
    last_battle = challenger_guild.get("last_guild_battle")
    if last_battle:
        if isinstance(last_battle, str):
            last_battle = datetime.fromisoformat(last_battle.replace('Z', '+00:00'))
        cooldown_end = last_battle + timedelta(hours=GUILD_BATTLE_COOLDOWN_HOURS)
        if datetime.utcnow() < cooldown_end:
            hours_left = int((cooldown_end - datetime.utcnow()).total_seconds() // 3600)
            raise HTTPException(
                status_code=400,
                detail=f"Guild is on cooldown. {hours_left} hours remaining."
            )
    
    # Verify target guild
    target_guild = await db.guilds.find_one({"id": target_guild_id})
    if not target_guild:
        raise HTTPException(status_code=404, detail="Target guild not found")
    
    if target_guild_id == guild_id:
        raise HTTPException(status_code=400, detail="Cannot challenge your own guild")
    
    # Check target guild eligibility
    target_members = len(target_guild.get("members", []))
    if target_members < GUILD_BATTLE_MIN_MEMBERS:
        raise HTTPException(
            status_code=400,
            detail=f"Target guild needs at least {GUILD_BATTLE_MIN_MEMBERS} members. They have: {target_members}"
        )
    
    if target_members < format_size:
        raise HTTPException(
            status_code=400,
            detail=f"Target guild needs at least {format_size} members for {format} format"
        )
    
    # Check if there's already a pending challenge between these guilds
    existing = await db.guild_battle_challenges.find_one({
        "$or": [
            {"challenger_guild_id": guild_id, "target_guild_id": target_guild_id, "status": "pending"},
            {"challenger_guild_id": target_guild_id, "target_guild_id": guild_id, "status": "pending"}
        ]
    })
    if existing:
        raise HTTPException(status_code=400, detail="There's already a pending challenge between these guilds")
    
    # Create the challenge
    challenge = {
        "id": str(uuid.uuid4()),
        "challenger_guild_id": guild_id,
        "challenger_guild_name": challenger_guild.get("name"),
        "challenger_guild_tag": challenger_guild.get("tag"),
        "target_guild_id": target_guild_id,
        "target_guild_name": target_guild.get("name"),
        "target_guild_tag": target_guild.get("tag"),
        "format": format,
        "challenger_player_id": player_id,
        "challenger_player_name": player.get("name"),
        "status": "pending",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=GUILD_BATTLE_CHALLENGE_EXPIRE_HOURS)
    }
    
    await db.guild_battle_challenges.insert_one(challenge)
    
    return serialize_doc(challenge)


@api_router.get("/guilds/{guild_id}/battle/challenges")
async def get_guild_battle_challenges(guild_id: str, player_id: str):
    """Get all pending challenges for a guild (incoming and outgoing)"""
    player = await db.players.find_one({"id": player_id})
    if not player or player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    # Get incoming and outgoing challenges
    incoming = await db.guild_battle_challenges.find({
        "target_guild_id": guild_id,
        "status": "pending"
    }).to_list(50)
    
    outgoing = await db.guild_battle_challenges.find({
        "challenger_guild_id": guild_id,
        "status": "pending"
    }).to_list(50)
    
    # Clean up expired challenges
    now = datetime.utcnow()
    for challenge in incoming + outgoing:
        expires = challenge.get("expires_at")
        if expires:
            if isinstance(expires, str):
                expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if now > expires:
                await db.guild_battle_challenges.update_one(
                    {"id": challenge["id"]},
                    {"$set": {"status": "expired"}}
                )
    
    # Re-fetch after cleanup
    incoming = await db.guild_battle_challenges.find({
        "target_guild_id": guild_id,
        "status": "pending"
    }).to_list(50)
    
    outgoing = await db.guild_battle_challenges.find({
        "challenger_guild_id": guild_id,
        "status": "pending"
    }).to_list(50)
    
    return {
        "incoming": serialize_doc(incoming),
        "outgoing": serialize_doc(outgoing)
    }


@api_router.post("/guilds/{guild_id}/battle/accept/{challenge_id}")
async def accept_guild_battle_challenge(guild_id: str, challenge_id: str, player_id: str):
    """Accept a guild battle challenge - starts the battle"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    # Check if player is leader or officer
    is_leader = guild.get("leader_id") == player_id
    is_officer = player_id in guild.get("officers", [])
    if not is_leader and not is_officer:
        raise HTTPException(status_code=403, detail="Only guild leaders or officers can accept challenges")
    
    # Get the challenge
    challenge = await db.guild_battle_challenges.find_one({"id": challenge_id, "status": "pending"})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found or already processed")
    
    if challenge.get("target_guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="This challenge is not for your guild")
    
    # Check if expired
    expires = challenge.get("expires_at")
    if expires:
        if isinstance(expires, str):
            expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
        if datetime.utcnow() > expires:
            await db.guild_battle_challenges.update_one(
                {"id": challenge_id},
                {"$set": {"status": "expired"}}
            )
            raise HTTPException(status_code=400, detail="Challenge has expired")
    
    # Get both guilds
    challenger_guild = await db.guilds.find_one({"id": challenge["challenger_guild_id"]})
    target_guild = guild
    
    if not challenger_guild:
        raise HTTPException(status_code=404, detail="Challenger guild no longer exists")
    
    # Get format size
    format_str = challenge.get("format", "3v3")
    format_size = int(format_str[0])
    
    # Auto-select top members by combat power
    challenger_members = await get_top_guild_members(challenge["challenger_guild_id"], format_size)
    target_members = await get_top_guild_members(guild_id, format_size)
    
    if len(challenger_members) < format_size or len(target_members) < format_size:
        raise HTTPException(status_code=400, detail="Not enough eligible members to start the battle")
    
    # Create matchups
    matchups = []
    for i in range(format_size):
        matchup = {
            "id": str(uuid.uuid4()),
            "match_number": i + 1,
            "challenger_player": {
                "id": challenger_members[i]["id"],
                "name": challenger_members[i]["name"],
                "level": challenger_members[i].get("level", 1),
                "combat_power": calculate_combat_power(challenger_members[i]),
                "stats": challenger_members[i].get("stats", {}),
                "current_health": challenger_members[i]["stats"].get("max_health", 100),
                "max_health": challenger_members[i]["stats"].get("max_health", 100),
                "current_energy": challenger_members[i]["stats"].get("max_energy", 100)
            },
            "target_player": {
                "id": target_members[i]["id"],
                "name": target_members[i]["name"],
                "level": target_members[i].get("level", 1),
                "combat_power": calculate_combat_power(target_members[i]),
                "stats": target_members[i].get("stats", {}),
                "current_health": target_members[i]["stats"].get("max_health", 100),
                "max_health": target_members[i]["stats"].get("max_health", 100),
                "current_energy": target_members[i]["stats"].get("max_energy", 100)
            },
            "status": "pending",  # pending, in_progress, challenger_won, target_won
            "combat_log": [],
            "turn": 1
        }
        matchups.append(matchup)
    
    # Create the battle
    battle = {
        "id": str(uuid.uuid4()),
        "challenge_id": challenge_id,
        "challenger_guild_id": challenge["challenger_guild_id"],
        "challenger_guild_name": challenge.get("challenger_guild_name"),
        "challenger_guild_tag": challenge.get("challenger_guild_tag"),
        "target_guild_id": guild_id,
        "target_guild_name": target_guild.get("name"),
        "target_guild_tag": target_guild.get("tag"),
        "format": format_str,
        "matchups": matchups,
        "challenger_wins": 0,
        "target_wins": 0,
        "current_matchup": 0,
        "status": "in_progress",
        "created_at": datetime.utcnow()
    }
    
    await db.guild_battles.insert_one(battle)
    
    # Update challenge status
    await db.guild_battle_challenges.update_one(
        {"id": challenge_id},
        {"$set": {"status": "accepted", "battle_id": battle["id"]}}
    )
    
    return serialize_doc(battle)


@api_router.post("/guilds/{guild_id}/battle/decline/{challenge_id}")
async def decline_guild_battle_challenge(guild_id: str, challenge_id: str, player_id: str):
    """Decline a guild battle challenge"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    # Check if player is leader or officer
    is_leader = guild.get("leader_id") == player_id
    is_officer = player_id in guild.get("officers", [])
    if not is_leader and not is_officer:
        raise HTTPException(status_code=403, detail="Only guild leaders or officers can decline challenges")
    
    # Get and update the challenge
    challenge = await db.guild_battle_challenges.find_one({"id": challenge_id, "status": "pending"})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found or already processed")
    
    if challenge.get("target_guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="This challenge is not for your guild")
    
    await db.guild_battle_challenges.update_one(
        {"id": challenge_id},
        {"$set": {"status": "declined", "declined_by": player_id, "declined_at": datetime.utcnow()}}
    )
    
    return {"message": "Challenge declined"}


@api_router.get("/guilds/{guild_id}/battle/history")
async def get_guild_battle_history(guild_id: str, player_id: str, limit: int = 10):
    """Get guild battle history"""
    player = await db.players.find_one({"id": player_id})
    if not player or player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    battles = await db.guild_battles.find({
        "$or": [
            {"challenger_guild_id": guild_id},
            {"target_guild_id": guild_id}
        ],
        "status": "completed"
    }).sort("completed_at", -1).limit(limit).to_list(limit)
    
    return serialize_doc(battles)


@api_router.get("/guilds/{guild_id}/battle/active")
async def get_active_guild_battle(guild_id: str, player_id: str):
    """Get any active guild battle for the guild"""
    player = await db.players.find_one({"id": player_id})
    if not player or player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    battle = await db.guild_battles.find_one({
        "$or": [
            {"challenger_guild_id": guild_id},
            {"target_guild_id": guild_id}
        ],
        "status": "in_progress"
    })
    
    return serialize_doc(battle) if battle else None


@api_router.get("/guilds/{guild_id}/battle/{battle_id}")
async def get_guild_battle(guild_id: str, battle_id: str, player_id: str):
    """Get the current state of a guild battle"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    battle = await db.guild_battles.find_one({"id": battle_id})
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")
    
    # Check if player's guild is involved
    if battle["challenger_guild_id"] != guild_id and battle["target_guild_id"] != guild_id:
        raise HTTPException(status_code=403, detail="Your guild is not part of this battle")
    
    return serialize_doc(battle)


@api_router.post("/guilds/{guild_id}/battle/{battle_id}/action")
async def guild_battle_action(
    guild_id: str,
    battle_id: str,
    player_id: str,
    action: str = "attack",
    skill_id: Optional[str] = None
):
    """Execute an action in a guild battle matchup"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    battle = await db.guild_battles.find_one({"id": battle_id})
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")
    
    if battle["status"] != "in_progress":
        return serialize_doc(battle)
    
    # Get current matchup
    current_idx = battle.get("current_matchup", 0)
    if current_idx >= len(battle["matchups"]):
        return serialize_doc(battle)
    
    matchup = battle["matchups"][current_idx]
    
    # Determine which side the player is on
    is_challenger = any(m["challenger_player"]["id"] == player_id for m in battle["matchups"])
    is_target = any(m["target_player"]["id"] == player_id for m in battle["matchups"])
    
    if not is_challenger and not is_target:
        raise HTTPException(status_code=403, detail="You are not a participant in this battle")
    
    # Check if it's this player's matchup
    current_challenger_id = matchup["challenger_player"]["id"]
    current_target_id = matchup["target_player"]["id"]
    
    if player_id != current_challenger_id and player_id != current_target_id:
        raise HTTPException(status_code=400, detail="It's not your turn to fight yet")
    
    # Determine attacker and defender
    if player_id == current_challenger_id:
        attacker = matchup["challenger_player"]
        defender = matchup["target_player"]
        attacker_key = "challenger_player"
        defender_key = "target_player"
        win_key = "challenger_won"
    else:
        attacker = matchup["target_player"]
        defender = matchup["challenger_player"]
        attacker_key = "target_player"
        defender_key = "challenger_player"
        win_key = "target_won"
    
    combat_log = matchup.get("combat_log", [])
    
    # Execute action
    if action == "attack":
        attacker_stats = attacker["stats"]
        defender_stats = defender["stats"]
        
        # Miss chance
        miss_chance = max(0.05, 0.10 - (attacker_stats.get("luck", 0) * 0.005))
        if random.random() < miss_chance:
            combat_log.append(f"{attacker['name']}'s attack MISSED!")
        else:
            damage = max(1, attacker_stats.get("attack", 10) - defender_stats.get("defense", 0) // 2)
            # Crit chance
            crit_chance = 0.05 + (attacker_stats.get("luck", 0) * 0.01)
            if random.random() < crit_chance:
                damage = int(damage * 2.0)
                combat_log.append(f"💥 CRITICAL! {attacker['name']} deals {damage} damage!")
            else:
                combat_log.append(f"{attacker['name']} attacks for {damage} damage!")
            defender["current_health"] = max(0, defender.get("current_health", 100) - damage)
    
    elif action == "skill" and skill_id:
        skill = SKILLS.get(skill_id)
        if not skill:
            raise HTTPException(status_code=400, detail="Invalid skill")
        
        attacker_stats = attacker["stats"]
        defender_stats = defender["stats"]
        
        if skill.get("cost", 0) > attacker.get("current_energy", 0):
            raise HTTPException(status_code=400, detail="Not enough energy")
        
        attacker["current_energy"] = attacker.get("current_energy", 100) - skill.get("cost", 0)
        
        if "damage_mult" in skill:
            if random.random() < 0.05:
                combat_log.append(f"{attacker['name']}'s {skill['name']} MISSED!")
            else:
                damage = int(attacker_stats.get("attack", 10) * skill["damage_mult"])
                if random.random() < 0.10:
                    damage = int(damage * 2.0)
                    combat_log.append(f"💥 CRITICAL {skill['name']}! {attacker['name']} deals {damage} damage!")
                else:
                    combat_log.append(f"{attacker['name']} uses {skill['name']} for {damage} damage!")
                defender["current_health"] = max(0, defender.get("current_health", 100) - damage)
        elif "heal_percent" in skill:
            heal = int(attacker.get("max_health", 100) * skill["heal_percent"])
            attacker["current_health"] = min(attacker.get("max_health", 100), attacker.get("current_health", 100) + heal)
            combat_log.append(f"{attacker['name']} uses {skill['name']} and heals {heal} HP!")
    
    elif action == "defend":
        combat_log.append(f"{attacker['name']} takes a defensive stance!")
        attacker["current_energy"] = min(100, attacker.get("current_energy", 100) + 10)
    
    # Update matchup
    matchup[attacker_key] = attacker
    matchup[defender_key] = defender
    matchup["combat_log"] = combat_log
    matchup["turn"] = matchup.get("turn", 1) + 1
    
    # Check if defender is defeated
    if defender.get("current_health", 0) <= 0:
        matchup["status"] = win_key
        combat_log.append(f"🏆 {attacker['name']} wins the matchup!")
        
        # Update battle scores
        if win_key == "challenger_won":
            battle["challenger_wins"] = battle.get("challenger_wins", 0) + 1
        else:
            battle["target_wins"] = battle.get("target_wins", 0) + 1
        
        # Move to next matchup
        battle["current_matchup"] = current_idx + 1
        
        # Check if battle is over
        format_size = int(battle["format"][0])
        wins_needed = (format_size // 2) + 1
        
        if battle["challenger_wins"] >= wins_needed or battle["target_wins"] >= wins_needed:
            # Battle is over
            battle["status"] = "completed"
            
            if battle["challenger_wins"] > battle["target_wins"]:
                battle["winner_guild_id"] = battle["challenger_guild_id"]
                battle["winner_guild_name"] = battle["challenger_guild_name"]
                winning_guild_id = battle["challenger_guild_id"]
                winning_members = [m["challenger_player"]["id"] for m in battle["matchups"]]
            else:
                battle["winner_guild_id"] = battle["target_guild_id"]
                battle["winner_guild_name"] = battle["target_guild_name"]
                winning_guild_id = battle["target_guild_id"]
                winning_members = [m["target_player"]["id"] for m in battle["matchups"]]
            
            battle["completed_at"] = datetime.utcnow()
            
            # Calculate top performers
            all_participants = []
            for m in battle["matchups"]:
                cp = m["challenger_player"]
                tp = m["target_player"]
                all_participants.append({
                    "player_id": cp["id"],
                    "name": cp["name"],
                    "guild_id": battle["challenger_guild_id"],
                    "combat_power": cp.get("combat_power", 0),
                    "won": m["status"] == "challenger_won"
                })
                all_participants.append({
                    "player_id": tp["id"],
                    "name": tp["name"],
                    "guild_id": battle["target_guild_id"],
                    "combat_power": tp.get("combat_power", 0),
                    "won": m["status"] == "target_won"
                })
            
            # Top performers = those who won their matchups
            battle["top_performers"] = [p for p in all_participants if p["won"]]
            
            # Award rewards to winners
            rewards = GUILD_BATTLE_REWARDS["winner"]
            for member_id in winning_members:
                await db.players.update_one(
                    {"id": member_id},
                    {"$inc": {
                        "cash": rewards["cash"],
                        "xp": rewards["xp"],
                        "reputation": rewards["reputation"]
                    }}
                )
            
            # Award guild reputation
            await db.guilds.update_one(
                {"id": winning_guild_id},
                {"$inc": {
                    "total_reputation": GUILD_BATTLE_REWARDS["guild_reputation"],
                    "total_wins": 1
                }}
            )
            
            # Set cooldown on both guilds
            await db.guilds.update_many(
                {"id": {"$in": [battle["challenger_guild_id"], battle["target_guild_id"]]}},
                {"$set": {"last_guild_battle": datetime.utcnow()}}
            )
    else:
        # Enemy counter-attack if battle continues and it was the attacker's turn
        if defender.get("current_health", 0) > 0 and action != "defend":
            defender_stats = defender["stats"]
            attacker_stats = attacker["stats"]
            
            if random.random() < 0.12:
                combat_log.append(f"{defender['name']}'s counter-attack MISSED!")
            else:
                enemy_damage = max(1, defender_stats.get("attack", 10) - attacker_stats.get("defense", 0) // 2)
                if random.random() < 0.08:
                    enemy_damage = int(enemy_damage * 2.0)
                    combat_log.append(f"💥 {defender['name']} lands a CRITICAL counter for {enemy_damage}!")
                else:
                    combat_log.append(f"{defender['name']} counters for {enemy_damage} damage!")
                attacker["current_health"] = max(0, attacker.get("current_health", 100) - enemy_damage)
            
            # Check if attacker is now defeated
            if attacker.get("current_health", 0) <= 0:
                if attacker_key == "challenger_player":
                    matchup["status"] = "target_won"
                    battle["target_wins"] = battle.get("target_wins", 0) + 1
                else:
                    matchup["status"] = "challenger_won"
                    battle["challenger_wins"] = battle.get("challenger_wins", 0) + 1
                
                combat_log.append(f"🏆 {defender['name']} wins the matchup!")
                battle["current_matchup"] = current_idx + 1
                
                # Check if battle is over
                format_size = int(battle["format"][0])
                wins_needed = (format_size // 2) + 1
                
                if battle["challenger_wins"] >= wins_needed or battle["target_wins"] >= wins_needed:
                    battle["status"] = "completed"
                    
                    if battle["challenger_wins"] > battle["target_wins"]:
                        battle["winner_guild_id"] = battle["challenger_guild_id"]
                        battle["winner_guild_name"] = battle["challenger_guild_name"]
                        winning_guild_id = battle["challenger_guild_id"]
                        winning_members = [m["challenger_player"]["id"] for m in battle["matchups"]]
                    else:
                        battle["winner_guild_id"] = battle["target_guild_id"]
                        battle["winner_guild_name"] = battle["target_guild_name"]
                        winning_guild_id = battle["target_guild_id"]
                        winning_members = [m["target_player"]["id"] for m in battle["matchups"]]
                    
                    battle["completed_at"] = datetime.utcnow()
                    
                    # Award rewards
                    rewards = GUILD_BATTLE_REWARDS["winner"]
                    for member_id in winning_members:
                        await db.players.update_one(
                            {"id": member_id},
                            {"$inc": {
                                "cash": rewards["cash"],
                                "xp": rewards["xp"],
                                "reputation": rewards["reputation"]
                            }}
                        )
                    
                    await db.guilds.update_one(
                        {"id": winning_guild_id},
                        {"$inc": {
                            "total_reputation": GUILD_BATTLE_REWARDS["guild_reputation"],
                            "total_wins": 1
                        }}
                    )
                    
                    await db.guilds.update_many(
                        {"id": {"$in": [battle["challenger_guild_id"], battle["target_guild_id"]]}},
                        {"$set": {"last_guild_battle": datetime.utcnow()}}
                    )
    
    # Update matchup in battle
    battle["matchups"][current_idx] = matchup
    matchup["combat_log"] = combat_log
    
    # Save battle
    await db.guild_battles.update_one(
        {"id": battle_id},
        {"$set": battle}
    )
    
    return serialize_doc(battle)


# ============== GUILD RAIDS SYSTEM ==============
# Constants for Guild Raids
GUILD_RAID_MAX_PLAYERS = 3
GUILD_RAID_LEVELS = 20  # Max levels in a raid

# Raid rewards scaling per level
def get_raid_level_rewards(level: int, num_enemies_at_level: int = 1) -> dict:
    """Calculate rewards for a specific raid level"""
    base_cash = 200 + (level * 150)
    base_xp = 100 + (level * 75)
    base_rep = 20 + (level * 10)
    return {
        "cash": base_cash * num_enemies_at_level,
        "xp": base_xp * num_enemies_at_level,
        "reputation": base_rep * num_enemies_at_level
    }


def generate_raid_enemy(level: int) -> dict:
    """Generate a raid enemy for a specific level"""
    # Get enemies appropriate for this level
    eligible = [e for e in ENEMY_TIERS if e["level_min"] <= level + 2 and e["level_max"] >= level - 2 and not e["is_boss"]]
    if not eligible:
        eligible = [e for e in ENEMY_TIERS if not e["is_boss"]][:5]
    
    template = random.choice(eligible)
    enemy_level = max(1, min(level, template["level_max"]))
    
    # Scale stats for raid (slightly harder than normal)
    stats = calculate_enemy_stats(enemy_level, False)
    stats["health"] = int(stats["health"] * 1.2)
    stats["max_health"] = stats["health"]
    stats["attack"] = int(stats["attack"] * 1.1)
    
    return {
        "id": str(uuid.uuid4()),
        "name": template["name"],
        "level": enemy_level,
        "stats": stats,
        "is_boss": False
    }


def generate_raid_boss(level: int) -> dict:
    """Generate a raid boss for milestone levels (every 5 levels)"""
    # Get bosses appropriate for this level
    eligible = [e for e in ENEMY_TIERS if e["is_boss"] and e["level_min"] <= level + 5]
    if not eligible:
        eligible = [e for e in ENEMY_TIERS if e["is_boss"]][:3]
    
    template = random.choice(eligible)
    boss_level = max(template["level_min"], min(level, template["level_max"]))
    
    # Scale stats for raid boss (tougher than normal)
    stats = calculate_enemy_stats(boss_level, True)
    stats["health"] = int(stats["health"] * 1.5)
    stats["max_health"] = stats["health"]
    stats["attack"] = int(stats["attack"] * 1.2)
    
    return {
        "id": str(uuid.uuid4()),
        "name": template["name"],
        "level": boss_level,
        "stats": stats,
        "is_boss": True
    }


@api_router.post("/guilds/{guild_id}/raid/start")
async def start_guild_raid(guild_id: str, player_id: str):
    """Start a new guild raid - creates a lobby that other guild members can join"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    # Check if player is already in an active raid
    existing_raid = await db.guild_raids.find_one({
        "participants.player_id": player_id,
        "status": {"$in": ["waiting", "in_progress"]}
    })
    if existing_raid:
        raise HTTPException(status_code=400, detail="You are already in an active raid")
    
    # Create the raid
    raid = {
        "id": str(uuid.uuid4()),
        "guild_id": guild_id,
        "guild_name": guild.get("name"),
        "leader_id": player_id,
        "participants": [{
            "player_id": player_id,
            "player_name": player.get("name"),
            "player_level": player.get("level", 1),
            "stats": player.get("stats", {}),
            "current_health": player["stats"].get("max_health", 100),
            "max_health": player["stats"].get("max_health", 100)
        }],
        "current_level": 1,
        "current_enemy": None,
        "enemies_defeated": 0,
        "accumulated_rewards": {"cash": 0, "xp": 0, "reputation": 0},
        "combat_log": [],
        "status": "waiting",  # waiting, in_progress, completed, failed
        "created_at": datetime.utcnow(),
        "started_at": None,
        "ended_at": None
    }
    
    await db.guild_raids.insert_one(raid)
    return serialize_doc(raid)


@api_router.post("/guilds/{guild_id}/raid/{raid_id}/join")
async def join_guild_raid(guild_id: str, raid_id: str, player_id: str):
    """Join an existing guild raid lobby"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    raid = await db.guild_raids.find_one({"id": raid_id, "guild_id": guild_id})
    if not raid:
        raise HTTPException(status_code=404, detail="Raid not found")
    
    if raid["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Raid has already started or ended")
    
    if len(raid["participants"]) >= GUILD_RAID_MAX_PLAYERS:
        raise HTTPException(status_code=400, detail=f"Raid is full (max {GUILD_RAID_MAX_PLAYERS} players)")
    
    # Check if already in this raid
    if any(p["player_id"] == player_id for p in raid["participants"]):
        raise HTTPException(status_code=400, detail="You are already in this raid")
    
    # Check if player is in another active raid
    existing_raid = await db.guild_raids.find_one({
        "participants.player_id": player_id,
        "status": {"$in": ["waiting", "in_progress"]},
        "id": {"$ne": raid_id}
    })
    if existing_raid:
        raise HTTPException(status_code=400, detail="You are already in another active raid")
    
    # Add participant
    participant = {
        "player_id": player_id,
        "player_name": player.get("name"),
        "player_level": player.get("level", 1),
        "stats": player.get("stats", {}),
        "current_health": player["stats"].get("max_health", 100),
        "max_health": player["stats"].get("max_health", 100)
    }
    
    await db.guild_raids.update_one(
        {"id": raid_id},
        {"$push": {"participants": participant}}
    )
    
    updated_raid = await db.guild_raids.find_one({"id": raid_id})
    return serialize_doc(updated_raid)


@api_router.post("/guilds/{guild_id}/raid/{raid_id}/leave")
async def leave_guild_raid(guild_id: str, raid_id: str, player_id: str):
    """Leave a guild raid (only during waiting phase)"""
    raid = await db.guild_raids.find_one({"id": raid_id, "guild_id": guild_id})
    if not raid:
        raise HTTPException(status_code=404, detail="Raid not found")
    
    if raid["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Cannot leave raid after it has started")
    
    # Check if player is in the raid
    if not any(p["player_id"] == player_id for p in raid["participants"]):
        raise HTTPException(status_code=400, detail="You are not in this raid")
    
    # If leader leaves, cancel the raid
    if raid["leader_id"] == player_id:
        await db.guild_raids.update_one(
            {"id": raid_id},
            {"$set": {"status": "cancelled", "ended_at": datetime.utcnow()}}
        )
        return {"message": "Raid cancelled (leader left)"}
    
    # Remove participant
    await db.guild_raids.update_one(
        {"id": raid_id},
        {"$pull": {"participants": {"player_id": player_id}}}
    )
    
    return {"message": "Left raid successfully"}


@api_router.post("/guilds/{guild_id}/raid/{raid_id}/begin")
async def begin_guild_raid(guild_id: str, raid_id: str, player_id: str):
    """Begin the raid (only leader can do this)"""
    raid = await db.guild_raids.find_one({"id": raid_id, "guild_id": guild_id})
    if not raid:
        raise HTTPException(status_code=404, detail="Raid not found")
    
    if raid["leader_id"] != player_id:
        raise HTTPException(status_code=403, detail="Only the raid leader can start the raid")
    
    if raid["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Raid has already started or ended")
    
    # Generate first enemy
    first_enemy = generate_raid_enemy(1)
    
    await db.guild_raids.update_one(
        {"id": raid_id},
        {"$set": {
            "status": "in_progress",
            "started_at": datetime.utcnow(),
            "current_enemy": first_enemy,
            "combat_log": [f"🏰 RAID BEGINS! Level 1 - {first_enemy['name']} (Lv.{first_enemy['level']}) appears!"]
        }}
    )
    
    updated_raid = await db.guild_raids.find_one({"id": raid_id})
    return serialize_doc(updated_raid)


@api_router.get("/guilds/{guild_id}/raid/active")
async def get_active_guild_raid(guild_id: str, player_id: str):
    """Get any active raid for a player in this guild"""
    player = await db.players.find_one({"id": player_id})
    if not player or player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    # Find raid where player is a participant
    raid = await db.guild_raids.find_one({
        "guild_id": guild_id,
        "participants.player_id": player_id,
        "status": {"$in": ["waiting", "in_progress"]}
    })
    
    return serialize_doc(raid) if raid else None


@api_router.get("/guilds/{guild_id}/raid/available")
async def get_available_guild_raids(guild_id: str, player_id: str):
    """Get all available raids to join in this guild"""
    player = await db.players.find_one({"id": player_id})
    if not player or player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    # Find waiting raids that player is not already in
    raids = await db.guild_raids.find({
        "guild_id": guild_id,
        "status": "waiting",
        "participants.player_id": {"$ne": player_id}
    }).to_list(10)
    
    # Filter to only show raids with space
    available = [r for r in raids if len(r.get("participants", [])) < GUILD_RAID_MAX_PLAYERS]
    
    return serialize_doc(available)


@api_router.get("/guilds/{guild_id}/raid/history")
async def get_guild_raid_history(guild_id: str, player_id: str, limit: int = 10):
    """Get raid history for a player in this guild"""
    player = await db.players.find_one({"id": player_id})
    if not player or player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    raids = await db.guild_raids.find({
        "guild_id": guild_id,
        "participants.player_id": player_id,
        "status": {"$in": ["completed", "failed", "retreated"]}
    }).sort("ended_at", -1).limit(limit).to_list(limit)
    
    return serialize_doc(raids)


@api_router.get("/guilds/{guild_id}/raid/{raid_id}")
async def get_guild_raid(guild_id: str, raid_id: str, player_id: str):
    """Get current raid state"""
    player = await db.players.find_one({"id": player_id})
    if not player or player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    raid = await db.guild_raids.find_one({"id": raid_id, "guild_id": guild_id})
    if not raid:
        raise HTTPException(status_code=404, detail="Raid not found")
    
    return serialize_doc(raid)


@api_router.post("/guilds/{guild_id}/raid/{raid_id}/fight")
async def guild_raid_fight(guild_id: str, raid_id: str, player_id: str, action: str = "attack"):
    """Execute a fight action in the raid"""
    player = await db.players.find_one({"id": player_id})
    if not player or player.get("guild_id") != guild_id:
        raise HTTPException(status_code=403, detail="You are not a member of this guild")
    
    raid = await db.guild_raids.find_one({"id": raid_id, "guild_id": guild_id})
    if not raid:
        raise HTTPException(status_code=404, detail="Raid not found")
    
    if raid["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Raid is not in progress")
    
    # Check if player is a participant
    participant_idx = next((i for i, p in enumerate(raid["participants"]) if p["player_id"] == player_id), None)
    if participant_idx is None:
        raise HTTPException(status_code=403, detail="You are not a participant in this raid")
    
    current_enemy = raid.get("current_enemy")
    if not current_enemy:
        raise HTTPException(status_code=400, detail="No enemy to fight")
    
    participants = raid["participants"]
    combat_log = raid.get("combat_log", [])
    
    # Calculate combined party stats
    total_attack = sum(p["stats"].get("attack", 10) for p in participants)
    total_defense = sum(p["stats"].get("defense", 10) for p in participants) // len(participants)
    
    # Execute attack based on action
    if action == "attack":
        # Party attacks enemy
        damage = max(1, total_attack - current_enemy["stats"].get("defense", 0) // 2)
        # Add some variance
        damage = int(damage * random.uniform(0.8, 1.2))
        
        # Crit chance
        if random.random() < 0.15:
            damage = int(damage * 1.5)
            combat_log.append(f"💥 CRITICAL! Party deals {damage} damage to {current_enemy['name']}!")
        else:
            combat_log.append(f"⚔️ Party attacks {current_enemy['name']} for {damage} damage!")
        
        current_enemy["stats"]["health"] = max(0, current_enemy["stats"]["health"] - damage)
    
    elif action == "defend":
        # Heal the party slightly
        heal_amount = 20
        for p in participants:
            p["current_health"] = min(p["max_health"], p["current_health"] + heal_amount)
        combat_log.append(f"🛡️ Party defends and recovers {heal_amount} HP each!")
    
    # Enemy counter-attack if still alive
    if current_enemy["stats"]["health"] > 0:
        enemy_damage = max(1, current_enemy["stats"].get("attack", 10) - total_defense // 2)
        enemy_damage = int(enemy_damage * random.uniform(0.8, 1.2))
        
        # Distribute damage among participants
        damage_per_player = enemy_damage // len(participants)
        for p in participants:
            p["current_health"] = max(0, p["current_health"] - damage_per_player)
        
        combat_log.append(f"👊 {current_enemy['name']} counter-attacks for {damage_per_player} damage to each member!")
        
        # Check if all participants are down
        all_down = all(p["current_health"] <= 0 for p in participants)
        if all_down:
            # Raid failed - but keep accumulated rewards
            combat_log.append(f"💀 All party members have fallen! Raid ends at Level {raid['current_level']}.")
            
            # Distribute accumulated rewards
            num_participants = len(participants)
            rewards = raid["accumulated_rewards"]
            share_cash = rewards["cash"] // num_participants
            share_xp = rewards["xp"] // num_participants
            share_rep = rewards["reputation"] // num_participants
            
            for p in participants:
                await db.players.update_one(
                    {"id": p["player_id"]},
                    {"$inc": {
                        "cash": share_cash,
                        "xp": share_xp,
                        "reputation": share_rep
                    }}
                )
            
            await db.guild_raids.update_one(
                {"id": raid_id},
                {"$set": {
                    "status": "failed",
                    "ended_at": datetime.utcnow(),
                    "participants": participants,
                    "current_enemy": current_enemy,
                    "combat_log": combat_log,
                    "final_rewards_per_player": {
                        "cash": share_cash,
                        "xp": share_xp,
                        "reputation": share_rep
                    }
                }}
            )
            
            updated_raid = await db.guild_raids.find_one({"id": raid_id})
            return serialize_doc(updated_raid)
    
    # Check if enemy is defeated
    if current_enemy["stats"]["health"] <= 0:
        # Enemy defeated!
        level = raid["current_level"]
        level_rewards = get_raid_level_rewards(level)
        
        # Add to accumulated rewards
        accumulated = raid["accumulated_rewards"]
        accumulated["cash"] += level_rewards["cash"]
        accumulated["xp"] += level_rewards["xp"]
        accumulated["reputation"] += level_rewards["reputation"]
        
        enemies_defeated = raid["enemies_defeated"] + 1
        
        combat_log.append(f"🎉 {current_enemy['name']} defeated! +${level_rewards['cash']}, +{level_rewards['xp']} XP, +{level_rewards['reputation']} Rep")
        
        # Heal party slightly between levels
        for p in participants:
            heal = int(p["max_health"] * 0.2)
            p["current_health"] = min(p["max_health"], p["current_health"] + heal)
        combat_log.append(f"💚 Party recovers between battles!")
        
        # Check if raid is complete
        if level >= GUILD_RAID_LEVELS:
            # Raid complete!
            combat_log.append(f"🏆 RAID COMPLETE! All {GUILD_RAID_LEVELS} levels cleared!")
            
            # Distribute rewards
            num_participants = len(participants)
            share_cash = accumulated["cash"] // num_participants
            share_xp = accumulated["xp"] // num_participants
            share_rep = accumulated["reputation"] // num_participants
            
            for p in participants:
                await db.players.update_one(
                    {"id": p["player_id"]},
                    {"$inc": {
                        "cash": share_cash,
                        "xp": share_xp,
                        "reputation": share_rep
                    }}
                )
            
            await db.guild_raids.update_one(
                {"id": raid_id},
                {"$set": {
                    "status": "completed",
                    "ended_at": datetime.utcnow(),
                    "participants": participants,
                    "current_enemy": None,
                    "enemies_defeated": enemies_defeated,
                    "accumulated_rewards": accumulated,
                    "combat_log": combat_log,
                    "final_rewards_per_player": {
                        "cash": share_cash,
                        "xp": share_xp,
                        "reputation": share_rep
                    }
                }}
            )
            
            updated_raid = await db.guild_raids.find_one({"id": raid_id})
            return serialize_doc(updated_raid)
        
        # Move to next level
        next_level = level + 1
        
        # Generate next enemy (boss every 5 levels)
        if next_level % 5 == 0:
            next_enemy = generate_raid_boss(next_level)
            combat_log.append(f"⚠️ BOSS LEVEL! {next_enemy['name']} (Lv.{next_enemy['level']}) appears!")
        else:
            next_enemy = generate_raid_enemy(next_level)
            combat_log.append(f"🏰 Level {next_level} - {next_enemy['name']} (Lv.{next_enemy['level']}) appears!")
        
        await db.guild_raids.update_one(
            {"id": raid_id},
            {"$set": {
                "current_level": next_level,
                "current_enemy": next_enemy,
                "enemies_defeated": enemies_defeated,
                "accumulated_rewards": accumulated,
                "participants": participants,
                "combat_log": combat_log
            }}
        )
    else:
        # Update raid state
        await db.guild_raids.update_one(
            {"id": raid_id},
            {"$set": {
                "current_enemy": current_enemy,
                "participants": participants,
                "combat_log": combat_log
            }}
        )
    
    updated_raid = await db.guild_raids.find_one({"id": raid_id})
    return serialize_doc(updated_raid)


@api_router.post("/guilds/{guild_id}/raid/{raid_id}/retreat")
async def retreat_guild_raid(guild_id: str, raid_id: str, player_id: str):
    """Retreat from the raid early - still keeps accumulated rewards"""
    raid = await db.guild_raids.find_one({"id": raid_id, "guild_id": guild_id})
    if not raid:
        raise HTTPException(status_code=404, detail="Raid not found")
    
    if raid["leader_id"] != player_id:
        raise HTTPException(status_code=403, detail="Only the raid leader can end the raid early")
    
    if raid["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Raid is not in progress")
    
    participants = raid["participants"]
    combat_log = raid.get("combat_log", [])
    accumulated = raid["accumulated_rewards"]
    
    combat_log.append(f"🏳️ Party retreats from the raid at Level {raid['current_level']}.")
    
    # Distribute accumulated rewards
    num_participants = len(participants)
    share_cash = accumulated["cash"] // num_participants
    share_xp = accumulated["xp"] // num_participants
    share_rep = accumulated["reputation"] // num_participants
    
    for p in participants:
        await db.players.update_one(
            {"id": p["player_id"]},
            {"$inc": {
                "cash": share_cash,
                "xp": share_xp,
                "reputation": share_rep
            }}
        )
    
    await db.guild_raids.update_one(
        {"id": raid_id},
        {"$set": {
            "status": "retreated",
            "ended_at": datetime.utcnow(),
            "combat_log": combat_log,
            "final_rewards_per_player": {
                "cash": share_cash,
                "xp": share_xp,
                "reputation": share_rep
            }
        }}
    )
    
    updated_raid = await db.guild_raids.find_one({"id": raid_id})
    return serialize_doc(updated_raid)


# ============== IMAGE UPLOAD ENDPOINTS ==============
from fastapi import File, UploadFile
from fastapi.responses import Response

@api_router.post("/upload/guild-icon/{guild_id}")
async def upload_guild_icon(guild_id: str, player_id: str, file: UploadFile = File(...)):
    """Upload a custom guild icon - only guild leader can do this"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    guild = await db.guilds.find_one({"id": guild_id})
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    if guild.get("leader_id") != player_id:
        raise HTTPException(status_code=403, detail="Only the guild leader can change the guild icon")
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {allowed_types}")
    
    # Read file content
    content = await file.read()
    
    # Size limit (2MB)
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 2MB")
    
    # Generate storage path
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    storage_path = f"{APP_NAME}/guilds/{guild_id}/icon.{ext}"
    
    try:
        # Upload to storage
        result = await run_in_threadpool(put_object, storage_path, content, file.content_type)
        
        # Update guild with icon path
        await db.guilds.update_one(
            {"id": guild_id},
            {"$set": {"icon_path": storage_path}}
        )
        
        return {"message": "Guild icon uploaded successfully", "path": storage_path}
    except Exception as e:
        logger.error(f"Failed to upload guild icon: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")


@api_router.post("/upload/profile-picture/{player_id}")
async def upload_profile_picture(player_id: str, file: UploadFile = File(...)):
    """Upload a player's profile picture"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {allowed_types}")
    
    # Read file content
    content = await file.read()
    
    # Size limit (2MB)
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 2MB")
    
    # Generate storage path
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    storage_path = f"{APP_NAME}/players/{player_id}/profile.{ext}"
    
    try:
        # Upload to storage
        result = await run_in_threadpool(put_object, storage_path, content, file.content_type)
        
        # Update player with profile picture path
        await db.players.update_one(
            {"id": player_id},
            {"$set": {"profile_picture": storage_path}}
        )
        
        return {"message": "Profile picture uploaded successfully", "path": storage_path}
    except Exception as e:
        logger.error(f"Failed to upload profile picture: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")


@api_router.get("/images/{path:path}")
async def get_image(path: str):
    """Retrieve an image from storage"""
    try:
        content, content_type = await run_in_threadpool(get_object, path)
        return Response(content=content, media_type=content_type)
    except Exception as e:
        logger.error(f"Failed to get image {path}: {e}")
        raise HTTPException(status_code=404, detail="Image not found")


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
    """Spawn banks near a location — very rare, only 10% of areas have one"""
    # Use a grid-based seed so the same area always gives the same result
    grid_lat = round(latitude * 200) / 200  # ~500m grid cells
    grid_lng = round(longitude * 200) / 200
    area_seed = hash(f"bank_{grid_lat}_{grid_lng}")
    rng = random.Random(area_seed)
    
    # Only spawn in ~10% of areas (banks are very rare - a significant opportunity)
    if rng.random() > 0.10:
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
    
    # Bank rewards scale with player level (reduced by 50% for balance)
    base_reward = int((500 + (player_level * 100)) * 0.5)
    
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
    """Attempt to rob a bank — success chance affected by luck"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    bank = await db.banks.find_one({"id": bank_id})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    # Check cooldown (60 minutes per player per bank - banks are a rare opportunity)
    cooldown_key = f"bank_cooldowns.{bank_id}"
    last_rob = player.get("bank_cooldowns", {}).get(bank_id)
    if last_rob:
        try:
            last_dt = datetime.fromisoformat(last_rob)
            mins_since = (datetime.utcnow() - last_dt).total_seconds() / 60
            if mins_since < 60:
                remaining = round(60 - mins_since, 1)
                raise HTTPException(
                    status_code=400,
                    detail=f"The heat is still on from your last job here! Wait {remaining} minutes."
                )
        except (ValueError, TypeError):
            pass
    
    player_level = player.get("level", 1)
    player_cash = player.get("cash", 0)
    
    # Get effective stats (luck affects success chance)
    effective_stats = await get_effective_stats(player)
    luck_val = effective_stats.get("luck", 5)
    
    # Calculate rewards based on player level (reduced by 50% for balance)
    base_reward = int((500 + (player_level * 100)) * 0.5)
    min_reward = int(base_reward * 0.5)
    max_reward = int(base_reward * 1.5)
    
    # Success chance: 50% base, modified by luck
    # 0 luck (broken accessory) = 20% success chance
    # Each luck point adds ~2% success chance up to max 70%
    if luck_val <= 0:
        success_chance = 0.20  # Very low chance with broken accessory
    else:
        success_chance = min(0.70, 0.50 + (luck_val * 0.02))  # 50% base + 2% per luck
    
    success = random.random() < success_chance
    
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
        
        # Extra message if luck was low
        fail_message = f"🚔 BUSTED! The cops caught you at {bank['name']}! You paid ${actual_fine} in fines."
        if luck_val <= 0:
            fail_message += " (Bad luck from broken accessory!)"
        
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
            "message": fail_message,
            "bank_name": bank["name"],
            "fine": actual_fine,
            "cash": new_cash,
        }


# ============== CASINO SYSTEM ==============

CASINO_NAMES = [
    "Golden Chip Casino", "Lucky Seven Casino", "The High Roller", "Diamond Palace",
    "Jackpot Junction", "Royal Flush Casino", "Fortune's Edge", "The Strip Club Casino",
    "Neon Nights Casino", "Big Stakes Casino", "The Betting Baron", "Cash King Casino",
]

SLOT_SYMBOLS = ["banana", "eggplant", "peach", "coconut", "hush_logo", "appsolut_logo", "street_legends"]
# Symbol weights: fruit symbols are common, hush_logo is rare, appsolut_logo and street_legends are jackpot (rarest)
SLOT_WEIGHTS = [25, 25, 25, 20, 3, 1, 1]  # Total: 100

# Slot payouts: {symbol: {3_match: multiplier, 2_match: multiplier}}
SLOT_PAYOUTS = {
    "banana": {"3": 5, "2": 1.5},
    "eggplant": {"3": 5, "2": 1.5},
    "peach": {"3": 6, "2": 1.5},
    "coconut": {"3": 8, "2": 2},
    "hush_logo": {"3": 25, "2": 5},
    "appsolut_logo": {"3": 100, "2": 10},
    "street_legends": {"3": 100, "2": 10},
}

@api_router.get("/casinos/spawn")
async def spawn_casinos(latitude: float, longitude: float, player_level: int = 1):
    """Spawn casinos near a location — uncommon, only 15% of areas have one"""
    grid_lat = round(latitude * 200) / 200
    grid_lng = round(longitude * 200) / 200
    area_seed = hash(f"casino_{grid_lat}_{grid_lng}")
    rng = random.Random(area_seed)
    
    # Only spawn in ~15% of areas
    if rng.random() > 0.15:
        return []
    
    # Check if casinos already exist nearby
    existing = await db.casinos.find({
        "latitude": {"$gte": latitude - 0.005, "$lte": latitude + 0.005},
        "longitude": {"$gte": longitude - 0.005, "$lte": longitude + 0.005},
    }).to_list(10)
    
    if existing:
        for casino in existing:
            casino.pop("_id", None)
        return existing
    
    lat_offset = rng.uniform(-0.003, 0.003)
    lng_offset = rng.uniform(-0.003, 0.003)
    
    casino = {
        "id": str(uuid.uuid4()),
        "name": rng.choice(CASINO_NAMES),
        "latitude": latitude + lat_offset,
        "longitude": longitude + lng_offset,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.casinos.insert_one(casino)
    casino.pop("_id", None)
    return [casino]


@api_router.post("/casinos/slots")
async def play_slots(player_id: str, bet_amount: int):
    """Play slot machine - spin 3 reels"""
    if bet_amount not in [10, 50, 100]:
        raise HTTPException(status_code=400, detail="Bet must be $10, $50, or $100")
    
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player_cash = player.get("cash", 0)
    if player_cash < bet_amount:
        raise HTTPException(status_code=400, detail=f"Not enough cash. You have ${player_cash}")
    
    # Get effective stats (luck affects slot outcomes)
    effective_stats = await get_effective_stats(player)
    luck_val = effective_stats.get("luck", 5)
    
    # Spin 3 reels using weighted random
    # If luck is 0 (broken accessory), heavily weight towards losses
    if luck_val <= 0:
        # Bad luck weights - much higher chance of low-value symbols
        bad_luck_weights = [30, 35, 25, 5, 3, 1, 0.5, 0.4, 0.1]  # Heavily favors losses
        reels = random.choices(SLOT_SYMBOLS, weights=bad_luck_weights, k=3)
    else:
        # Normal weights with slight luck bonus
        adjusted_weights = list(SLOT_WEIGHTS)
        # Better luck slightly improves high-value symbol chances
        luck_bonus = luck_val * 0.02
        for i in range(len(adjusted_weights)):
            if i >= 5:  # High value symbols (indices 5+)
                adjusted_weights[i] *= (1 + luck_bonus)
        reels = random.choices(SLOT_SYMBOLS, weights=adjusted_weights, k=3)
    
    # Calculate winnings
    winnings = 0
    result_type = "loss"
    
    # Check for 3 of a kind
    if reels[0] == reels[1] == reels[2]:
        multiplier = SLOT_PAYOUTS[reels[0]]["3"]
        winnings = int(bet_amount * multiplier)
        result_type = "jackpot" if reels[0] in ["hush_logo", "appsolut_logo", "street_legends"] else "big_win"
    # Check for 2 of a kind (first two or last two)
    elif reels[0] == reels[1] or reels[1] == reels[2]:
        matching_symbol = reels[0] if reels[0] == reels[1] else reels[1]
        multiplier = SLOT_PAYOUTS[matching_symbol]["2"]
        winnings = int(bet_amount * multiplier)
        result_type = "small_win"
    
    # Calculate net change
    net_change = winnings - bet_amount
    new_cash = player_cash + net_change
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"cash": new_cash}}
    )
    
    return {
        "reels": reels,
        "bet": bet_amount,
        "winnings": winnings,
        "net_change": net_change,
        "new_cash": new_cash,
        "result_type": result_type,
    }


@api_router.post("/casinos/blackjack/start")
async def start_blackjack(player_id: str, bet_amount: int):
    """Start a new blackjack game"""
    if bet_amount < 10 or bet_amount > 1000:
        raise HTTPException(status_code=400, detail="Bet must be between $10 and $1000")
    
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player_cash = player.get("cash", 0)
    if player_cash < bet_amount:
        raise HTTPException(status_code=400, detail=f"Not enough cash. You have ${player_cash}")
    
    # Create a deck and shuffle
    suits = ["hearts", "diamonds", "clubs", "spades"]
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    deck = [{"suit": s, "rank": r} for s in suits for r in ranks]
    random.shuffle(deck)
    
    # Deal initial cards
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]
    
    def calculate_hand_value(cards):
        value = 0
        aces = 0
        for card in cards:
            rank = card["rank"]
            if rank in ["J", "Q", "K"]:
                value += 10
            elif rank == "A":
                aces += 1
                value += 11
            else:
                value += int(rank)
        # Adjust for aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        return value
    
    player_value = calculate_hand_value(player_cards)
    dealer_value = calculate_hand_value([dealer_cards[0]])  # Only show first card
    
    # Check for natural blackjack
    is_blackjack = player_value == 21
    
    game = {
        "id": str(uuid.uuid4()),
        "player_id": player_id,
        "bet": bet_amount,
        "deck": deck,
        "player_cards": player_cards,
        "dealer_cards": dealer_cards,
        "player_value": player_value,
        "status": "blackjack" if is_blackjack else "playing",
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.blackjack_games.insert_one(game)
    
    # If blackjack, pay out immediately
    if is_blackjack:
        winnings = int(bet_amount * 2.5)  # 1.5x profit + original bet
        new_cash = player_cash + winnings - bet_amount
        await db.players.update_one({"id": player_id}, {"$set": {"cash": new_cash}})
        
        return {
            "game_id": game["id"],
            "player_cards": player_cards,
            "dealer_cards": [dealer_cards[0], {"suit": "hidden", "rank": "?"}],
            "dealer_full_cards": dealer_cards,
            "player_value": player_value,
            "dealer_value": calculate_hand_value(dealer_cards),
            "status": "blackjack",
            "message": "BLACKJACK! You win!",
            "winnings": winnings,
            "new_cash": new_cash,
        }
    
    return {
        "game_id": game["id"],
        "player_cards": player_cards,
        "dealer_cards": [dealer_cards[0], {"suit": "hidden", "rank": "?"}],
        "player_value": player_value,
        "dealer_value": dealer_value,
        "status": "playing",
    }


@api_router.post("/casinos/blackjack/{game_id}/action")
async def blackjack_action(game_id: str, action: str):
    """Perform a blackjack action: hit, stand, or double"""
    game = await db.blackjack_games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game["status"] != "playing":
        raise HTTPException(status_code=400, detail="Game is already over")
    
    player = await db.players.find_one({"id": game["player_id"]})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player_cash = player.get("cash", 0)
    bet = game["bet"]
    deck = game["deck"]
    player_cards = game["player_cards"]
    dealer_cards = game["dealer_cards"]
    
    def calculate_hand_value(cards):
        value = 0
        aces = 0
        for card in cards:
            rank = card["rank"]
            if rank in ["J", "Q", "K"]:
                value += 10
            elif rank == "A":
                aces += 1
                value += 11
            else:
                value += int(rank)
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        return value
    
    if action == "hit":
        player_cards.append(deck.pop())
        player_value = calculate_hand_value(player_cards)
        
        if player_value > 21:
            # Bust - player loses
            new_cash = player_cash - bet
            await db.players.update_one({"id": player["id"]}, {"$set": {"cash": new_cash}})
            await db.blackjack_games.update_one({"id": game_id}, {"$set": {"status": "bust", "player_cards": player_cards}})
            
            return {
                "player_cards": player_cards,
                "dealer_cards": dealer_cards,
                "player_value": player_value,
                "dealer_value": calculate_hand_value(dealer_cards),
                "status": "bust",
                "message": "BUST! You lose!",
                "winnings": -bet,
                "new_cash": new_cash,
            }
        
        await db.blackjack_games.update_one({"id": game_id}, {"$set": {"player_cards": player_cards, "deck": deck}})
        
        return {
            "player_cards": player_cards,
            "dealer_cards": [dealer_cards[0], {"suit": "hidden", "rank": "?"}],
            "player_value": player_value,
            "status": "playing",
        }
    
    elif action == "double":
        if player_cash < bet * 2:
            raise HTTPException(status_code=400, detail="Not enough cash to double down")
        
        bet = bet * 2
        player_cards.append(deck.pop())
        player_value = calculate_hand_value(player_cards)
        
        if player_value > 21:
            new_cash = player_cash - bet
            await db.players.update_one({"id": player["id"]}, {"$set": {"cash": new_cash}})
            await db.blackjack_games.update_one({"id": game_id}, {"$set": {"status": "bust", "player_cards": player_cards, "bet": bet}})
            
            return {
                "player_cards": player_cards,
                "dealer_cards": dealer_cards,
                "player_value": player_value,
                "dealer_value": calculate_hand_value(dealer_cards),
                "status": "bust",
                "message": "BUST! You lose!",
                "winnings": -bet,
                "new_cash": new_cash,
            }
        
        # Fall through to stand logic
        action = "stand"
        await db.blackjack_games.update_one({"id": game_id}, {"$set": {"player_cards": player_cards, "bet": bet, "deck": deck}})
    
    if action == "stand":
        player_value = calculate_hand_value(player_cards)
        
        # Dealer plays - hits on 16, stands on 17
        dealer_value = calculate_hand_value(dealer_cards)
        while dealer_value < 17:
            dealer_cards.append(deck.pop())
            dealer_value = calculate_hand_value(dealer_cards)
        
        # Determine winner
        if dealer_value > 21:
            status = "dealer_bust"
            message = "Dealer busts! You win!"
            winnings = bet
        elif dealer_value > player_value:
            status = "dealer_wins"
            message = "Dealer wins!"
            winnings = -bet
        elif player_value > dealer_value:
            status = "player_wins"
            message = "You win!"
            winnings = bet
        else:
            status = "push"
            message = "Push! It's a tie."
            winnings = 0
        
        new_cash = player_cash + winnings
        await db.players.update_one({"id": player["id"]}, {"$set": {"cash": new_cash}})
        await db.blackjack_games.update_one({"id": game_id}, {"$set": {"status": status, "dealer_cards": dealer_cards}})
        
        return {
            "player_cards": player_cards,
            "dealer_cards": dealer_cards,
            "player_value": player_value,
            "dealer_value": dealer_value,
            "status": status,
            "message": message,
            "winnings": winnings,
            "new_cash": new_cash,
        }
    
    raise HTTPException(status_code=400, detail="Invalid action. Use 'hit', 'stand', or 'double'")


@api_router.post("/casinos/roulette")
async def play_roulette(player_id: str, bet_amount: int, bet_type: str, bet_value: str = ""):
    """Play roulette - spin the wheel"""
    if bet_amount < 10 or bet_amount > 1000:
        raise HTTPException(status_code=400, detail="Bet must be between $10 and $1000")
    
    valid_bet_types = ["number", "red", "black", "odd", "even", "1-12", "13-24", "25-36", "1-18", "19-36"]
    if bet_type not in valid_bet_types:
        raise HTTPException(status_code=400, detail=f"Invalid bet type. Use: {', '.join(valid_bet_types)}")
    
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player_cash = player.get("cash", 0)
    if player_cash < bet_amount:
        raise HTTPException(status_code=400, detail=f"Not enough cash. You have ${player_cash}")
    
    # Roulette wheel numbers (0-36, with 0 being green)
    red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    black_numbers = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
    
    # Spin the wheel
    result_number = random.randint(0, 36)
    
    if result_number == 0:
        result_color = "green"
    elif result_number in red_numbers:
        result_color = "red"
    else:
        result_color = "black"
    
    # Determine winnings
    winnings = 0
    win = False
    
    if bet_type == "number":
        try:
            bet_num = int(bet_value)
            if bet_num < 0 or bet_num > 36:
                raise HTTPException(status_code=400, detail="Number must be 0-36")
            if result_number == bet_num:
                winnings = bet_amount * 35
                win = True
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid number")
    
    elif bet_type == "red":
        if result_color == "red":
            winnings = bet_amount * 2
            win = True
    
    elif bet_type == "black":
        if result_color == "black":
            winnings = bet_amount * 2
            win = True
    
    elif bet_type == "odd":
        if result_number != 0 and result_number % 2 == 1:
            winnings = bet_amount * 2
            win = True
    
    elif bet_type == "even":
        if result_number != 0 and result_number % 2 == 0:
            winnings = bet_amount * 2
            win = True
    
    elif bet_type == "1-12":
        if 1 <= result_number <= 12:
            winnings = bet_amount * 3
            win = True
    
    elif bet_type == "13-24":
        if 13 <= result_number <= 24:
            winnings = bet_amount * 3
            win = True
    
    elif bet_type == "25-36":
        if 25 <= result_number <= 36:
            winnings = bet_amount * 3
            win = True
    
    elif bet_type == "1-18":
        if 1 <= result_number <= 18:
            winnings = bet_amount * 2
            win = True
    
    elif bet_type == "19-36":
        if 19 <= result_number <= 36:
            winnings = bet_amount * 2
            win = True
    
    net_change = winnings - bet_amount
    new_cash = player_cash + net_change
    
    await db.players.update_one({"id": player_id}, {"$set": {"cash": new_cash}})
    
    return {
        "result_number": result_number,
        "result_color": result_color,
        "bet_type": bet_type,
        "bet_value": bet_value,
        "bet_amount": bet_amount,
        "win": win,
        "winnings": winnings,
        "net_change": net_change,
        "new_cash": new_cash,
    }


class RouletteBetsRequest(BaseModel):
    bets: dict


@api_router.post("/casinos/roulette/spin")
async def spin_american_roulette(player_id: str, request: RouletteBetsRequest):
    """Play American roulette with multiple bets - includes 0 and 00"""
    bets = request.bets
    
    if not bets:
        raise HTTPException(status_code=400, detail="No bets placed")
    
    total_bet = sum(bets.values())
    if total_bet < 1:
        raise HTTPException(status_code=400, detail="Total bet must be at least $1")
    
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player_cash = player.get("cash", 0)
    if player_cash < total_bet:
        raise HTTPException(status_code=400, detail=f"Not enough cash. You have ${player_cash}, need ${total_bet}")
    
    # Get effective stats (luck affects outcomes)
    effective_stats = await get_effective_stats(player)
    luck_val = effective_stats.get("luck", 5)
    
    # American roulette wheel - includes 0 and 00
    wheel_numbers = ['0', '00'] + [str(i) for i in range(1, 37)]
    red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    
    # Spin the wheel - luck affects the outcome
    if luck_val <= 0:
        # Bad luck: 40% chance to land on 0 or 00 (house edge)
        if random.random() < 0.40:
            winning_number = random.choice(['0', '00'])
        else:
            winning_number = random.choice(wheel_numbers)
    else:
        # Normal spin
        winning_number = random.choice(wheel_numbers)
    
    # Determine winning number properties
    if winning_number in ['0', '00']:
        winning_color = 'green'
        winning_int = -1 if winning_number == '00' else 0
    else:
        winning_int = int(winning_number)
        winning_color = 'red' if winning_int in red_numbers else 'black'
    
    # Calculate winnings for each bet
    total_winnings = 0
    winning_bets = []
    
    for bet_type, bet_amount in bets.items():
        payout = 0
        
        # Single number bets (num_X format)
        if bet_type.startswith('num_'):
            bet_num = bet_type.replace('num_', '')
            if bet_num == winning_number:
                payout = bet_amount * 36  # 35:1 plus original bet
                winning_bets.append(bet_type)
        
        # Color bets
        elif bet_type == 'red':
            if winning_color == 'red':
                payout = bet_amount * 2
                winning_bets.append(bet_type)
        elif bet_type == 'black':
            if winning_color == 'black':
                payout = bet_amount * 2
                winning_bets.append(bet_type)
        
        # Even/Odd bets (0 and 00 lose)
        elif bet_type == 'even':
            if winning_int > 0 and winning_int % 2 == 0:
                payout = bet_amount * 2
                winning_bets.append(bet_type)
        elif bet_type == 'odd':
            if winning_int > 0 and winning_int % 2 == 1:
                payout = bet_amount * 2
                winning_bets.append(bet_type)
        
        # 1-18 / 19-36 bets
        elif bet_type == '1-18':
            if 1 <= winning_int <= 18:
                payout = bet_amount * 2
                winning_bets.append(bet_type)
        elif bet_type == '19-36':
            if 19 <= winning_int <= 36:
                payout = bet_amount * 2
                winning_bets.append(bet_type)
        
        # Dozen bets
        elif bet_type == '1st12':
            if 1 <= winning_int <= 12:
                payout = bet_amount * 3
                winning_bets.append(bet_type)
        elif bet_type == '2nd12':
            if 13 <= winning_int <= 24:
                payout = bet_amount * 3
                winning_bets.append(bet_type)
        elif bet_type == '3rd12':
            if 25 <= winning_int <= 36:
                payout = bet_amount * 3
                winning_bets.append(bet_type)
        
        # Column bets (1st: 1,4,7... 2nd: 2,5,8... 3rd: 3,6,9...)
        elif bet_type == 'col1':
            if winning_int > 0 and winning_int % 3 == 1:
                payout = bet_amount * 3
                winning_bets.append(bet_type)
        elif bet_type == 'col2':
            if winning_int > 0 and winning_int % 3 == 2:
                payout = bet_amount * 3
                winning_bets.append(bet_type)
        elif bet_type == 'col3':
            if winning_int > 0 and winning_int % 3 == 0:
                payout = bet_amount * 3
                winning_bets.append(bet_type)
        
        total_winnings += payout
    
    # Calculate net change (winnings minus total bet)
    net_change = total_winnings - total_bet
    new_cash = player_cash + net_change
    
    await db.players.update_one({"id": player_id}, {"$set": {"cash": new_cash}})
    
    return {
        "winning_number": winning_number,
        "winning_color": winning_color,
        "total_bet": total_bet,
        "total_winnings": total_winnings,
        "net_change": net_change,
        "new_cash": new_cash,
        "winning_bets": winning_bets,
        "bets_placed": list(bets.keys()),
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
    """Get all active cooldowns for mini-games (castles, car chases, runaways, package grabs, and shootouts)"""
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
    
    # Get runaway cooldowns
    runaway_cooldowns = player.get("runaway_cooldowns", {})
    for runaway_id, last_attempt in runaway_cooldowns.items():
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            secs_since = (now - last_dt).total_seconds()
            if secs_since < cooldown_duration:
                remaining = int(cooldown_duration - secs_since)
                cooldowns[f"runaway_{runaway_id}"] = {
                    "type": "runaway",
                    "marker_id": runaway_id,
                    "remaining_seconds": remaining,
                    "expires_at": (last_dt + timedelta(seconds=cooldown_duration)).isoformat(),
                }
        except (ValueError, TypeError):
            pass
    
    # Get package grab cooldowns
    packagegrab_cooldowns = player.get("packagegrab_cooldowns", {})
    for grab_id, last_attempt in packagegrab_cooldowns.items():
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            secs_since = (now - last_dt).total_seconds()
            if secs_since < cooldown_duration:
                remaining = int(cooldown_duration - secs_since)
                cooldowns[f"packagegrab_{grab_id}"] = {
                    "type": "packagegrab",
                    "marker_id": grab_id,
                    "remaining_seconds": remaining,
                    "expires_at": (last_dt + timedelta(seconds=cooldown_duration)).isoformat(),
                }
        except (ValueError, TypeError):
            pass
    
    # Get shootout cooldowns
    shootout_cooldowns = player.get("shootout_cooldowns", {})
    for shootout_id, last_attempt in shootout_cooldowns.items():
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            secs_since = (now - last_dt).total_seconds()
            if secs_since < cooldown_duration:
                remaining = int(cooldown_duration - secs_since)
                cooldowns[f"shootout_{shootout_id}"] = {
                    "type": "shootout",
                    "marker_id": shootout_id,
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
        "total_members": random_level + 2,  # Base enemies scale with level
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
async def complete_castle_game(game_id: str, members_eliminated: int, won: bool, standalone: bool = False):
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
    
    # Set cooldown regardless of win/lose (only for map-based games, not standalone)
    if not standalone:
        await db.players.update_one(
            {"id": game["player_id"]},
            {"$set": {f"castle_cooldowns.{castle_id}": datetime.utcnow().isoformat()}}
        )
    
    if won:
        # Calculate rewards based on difficulty and members eliminated
        difficulty = game["difficulty"]
        total_members = game.get("total_members", difficulty + 2)  # Safe fallback
        
        # Cash scales with difficulty
        base_cash = random.randint(game["min_reward"], game["max_reward"])
        cash_reward = base_cash
        
        xp_reward = game["xp_reward"]
        rep_reward = game["rep_reward"]
        
        # Apply 50% reduction for standalone/options panel games
        if standalone:
            cash_reward = cash_reward // 2
            xp_reward = xp_reward // 2
            rep_reward = max(1, rep_reward // 2)
        
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
            "standalone": standalone,
        }
    else:
        return {
            "success": True,
            "won": False,
            "message": f"💥 DEFEAT! The gang at {game['castle_name']} held their ground!",
            "castle_name": game["castle_name"],
            "members_eliminated": members_eliminated,
            "total_members": game.get("total_members", game["difficulty"] + 2),
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
async def complete_car_chase(game_id: str, won: bool, distance_traveled: int, standalone: bool = False):
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
    
    # Set cooldown (only for map-based games, not standalone)
    if not standalone:
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
        
        # Apply 50% reduction for standalone/options panel games
        if standalone:
            cash_reward = cash_reward // 2
            xp_reward = xp_reward // 2
            rep_reward = max(1, rep_reward // 2)
        
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
            "standalone": standalone,
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


# ============== RUNAWAY SIMULATOR MINI-GAME ==============

RUNAWAY_NAMES = [
    "Downtown Dash", "Alley Escape", "Street Sprint", "Metro Run",
    "Subway Getaway", "Backstreet Bolt", "Night Runner", "Urban Flight",
    "Side Street Slip", "Avenue Pursuit", "Block Runner", "City Chase",
]

@api_router.get("/runaways/spawn")
async def spawn_runaways(latitude: float, longitude: float, player_level: int = 1):
    """Spawn runaway simulator markers near the player"""
    # Create deterministic ID based on grid location
    grid_lat = round(latitude * 100) / 100
    grid_lng = round(longitude * 100) / 100
    area_seed = hash(f"runaway_{grid_lat}_{grid_lng}")
    random.seed(area_seed)
    
    runaway_id = f"runaway_{abs(area_seed) % 100000}"
    
    # Check if runaway already exists
    existing = await db.runaways.find({
        "latitude": {"$gte": grid_lat - 0.01, "$lte": grid_lat + 0.01},
        "longitude": {"$gte": grid_lng - 0.01, "$lte": grid_lng + 0.01}
    }).to_list(length=10)
    
    if existing:
        return [serialize_doc(r) for r in existing]
    
    # Generate a new runaway location
    # Difficulty scales with player level (1-20 range)
    difficulty = min(20, max(1, (player_level // 3) + random.randint(1, 5)))
    
    runaway = {
        "id": runaway_id,
        "name": RUNAWAY_NAMES[abs(area_seed) % len(RUNAWAY_NAMES)],
        "latitude": grid_lat + (random.random() - 0.5) * 0.005,
        "longitude": grid_lng + (random.random() - 0.5) * 0.005,
        "difficulty": difficulty,
        "hideout_distance": 2500 + difficulty * 200,  # Matching frontend calculation
        "min_reward": 60 + difficulty * 20,
        "max_reward": 120 + difficulty * 30,
        "xp_reward": 40 + difficulty * 15,
        "rep_reward": 3 + difficulty // 3,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.runaways.insert_one(runaway)
    runaway.pop("_id", None)
    return [runaway]


@api_router.post("/runaways/{runaway_id}/start")
async def start_runaway(runaway_id: str, player_id: str):
    """Start a runaway simulator game"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    runaway = await db.runaways.find_one({"id": runaway_id})
    if not runaway:
        raise HTTPException(status_code=404, detail="Runaway location not found")
    
    # Check cooldown (15 minutes per player per runaway)
    last_attempt = player.get("runaway_cooldowns", {}).get(runaway_id)
    if last_attempt:
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            secs_since = (datetime.utcnow() - last_dt).total_seconds()
            if secs_since < 900:  # 15 minutes
                remaining = int(900 - secs_since)
                mins = remaining // 60
                secs = remaining % 60
                raise HTTPException(
                    status_code=400,
                    detail=f"Cooldown active. Wait {mins}:{secs:02d} before trying again."
                )
        except ValueError:
            pass
    
    # Create game session
    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "player_id": player_id,
        "runaway_id": runaway_id,
        "runaway_name": runaway["name"],
        "difficulty": runaway["difficulty"],
        "hideout_distance": runaway["hideout_distance"],
        "min_reward": runaway["min_reward"],
        "max_reward": runaway["max_reward"],
        "xp_reward": runaway["xp_reward"],
        "rep_reward": runaway["rep_reward"],
        "status": "active",
        "started_at": datetime.utcnow().isoformat(),
    }
    
    await db.runaway_games.insert_one(game)
    
    return {
        "game_id": game_id,
        "runaway_name": runaway["name"],
        "difficulty": runaway["difficulty"],
        "hideout_distance": runaway["hideout_distance"],
    }


@api_router.post("/runaways/game/{game_id}/complete")
async def complete_runaway(game_id: str, won: bool, distance_traveled: int, standalone: bool = False):
    """Complete a runaway game and award rewards if won"""
    game = await db.runaway_games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    if game["status"] != "active":
        raise HTTPException(status_code=400, detail="Game already completed")
    
    player = await db.players.find_one({"id": game["player_id"]})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    runaway_id = game["runaway_id"]
    
    # Update game status
    await db.runaway_games.update_one(
        {"id": game_id},
        {"$set": {
            "status": "completed",
            "won": won,
            "distance_traveled": distance_traveled,
            "completed_at": datetime.utcnow().isoformat(),
        }}
    )
    
    # Set cooldown (15 minutes win or lose) - only for map-based games, not standalone
    if not standalone:
        await db.players.update_one(
            {"id": game["player_id"]},
            {"$set": {f"runaway_cooldowns.{runaway_id}": datetime.utcnow().isoformat()}}
        )
    
    if won:
        # Calculate rewards based on difficulty (1-20)
        # NEW: Distance-based difficulty with exponential rewards
        difficulty = game["difficulty"]
        
        # Base rewards + scaling with level (matches frontend calculation)
        base_cash = 60
        base_xp = 30
        base_rep = 2
        level_multiplier = 1 + (difficulty - 1) * 0.2  # 1.0 at L1, 4.8 at L20
        
        cash_reward = int(base_cash * level_multiplier + difficulty * 15)
        xp_reward = int(base_xp * level_multiplier + difficulty * 10)
        rep_reward = int(base_rep + difficulty / 2)
        
        # Apply 50% reduction for standalone/options panel games
        if standalone:
            cash_reward = cash_reward // 2
            xp_reward = xp_reward // 2
            rep_reward = max(1, rep_reward // 2)
        
        await db.players.update_one(
            {"id": game["player_id"]},
            {"$inc": {"cash": cash_reward, "xp": xp_reward, "reputation": rep_reward}}
        )
        
        updated_player = await db.players.find_one({"id": game["player_id"]})
        
        return {
            "success": True,
            "won": True,
            "message": f"🏠💨 ESCAPED! You made it to the hideout on {game['runaway_name']}!",
            "runaway_name": game["runaway_name"],
            "distance_traveled": distance_traveled,
            "rewards": {
                "cash": cash_reward,
                "xp": xp_reward,
                "reputation": rep_reward,
            },
            "cash": updated_player.get("cash", 0),
            "standalone": standalone,
        }
    else:
        return {
            "success": True,
            "won": False,
            "message": f"🚔 BUSTED! The cops caught you on {game['runaway_name']}!",
            "runaway_name": game["runaway_name"],
            "distance_traveled": distance_traveled,
            "rewards": None,
        }


# ============== PACKAGE GRAB MINI-GAME ==============

PACKAGE_GRAB_NAMES = [
    "Downtown Delivery", "Express Route", "Cargo Run", "Harbor Haul",
    "Industrial Pickup", "Warehouse Dash", "Freight Frenzy", "Dock Delivery",
    "Market Run", "District Drop", "City Cargo", "Night Shift",
]

@api_router.get("/packagegrabs/spawn")
async def spawn_package_grabs(latitude: float, longitude: float, player_level: int = 1):
    """Spawn package grab markers near the player"""
    # Create deterministic ID based on grid location
    grid_lat = round(latitude * 100) / 100
    grid_lng = round(longitude * 100) / 100
    area_seed = hash(f"packagegrab_{grid_lat}_{grid_lng}")
    random.seed(area_seed)
    
    grab_id = f"packagegrab_{abs(area_seed) % 100000}"
    
    # Check if package grab already exists
    existing = await db.packagegrabs.find({
        "latitude": {"$gte": grid_lat - 0.01, "$lte": grid_lat + 0.01},
        "longitude": {"$gte": grid_lng - 0.01, "$lte": grid_lng + 0.01}
    }).to_list(length=10)
    
    if existing:
        return [serialize_doc(r) for r in existing]
    
    # Generate a new package grab location
    grab = {
        "id": grab_id,
        "name": PACKAGE_GRAB_NAMES[abs(area_seed) % len(PACKAGE_GRAB_NAMES)],
        "latitude": grid_lat + (random.random() - 0.5) * 0.006,
        "longitude": grid_lng + (random.random() - 0.5) * 0.006,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.packagegrabs.insert_one(grab)
    grab.pop("_id", None)
    return [grab]


@api_router.post("/packagegrabs/{grab_id}/start")
async def start_package_grab(grab_id: str, player_id: str):
    """Start a package grab game"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    grab = await db.packagegrabs.find_one({"id": grab_id})
    if not grab:
        raise HTTPException(status_code=404, detail="Package grab location not found")
    
    # Check cooldown (15 minutes per player per grab)
    last_attempt = player.get("packagegrab_cooldowns", {}).get(grab_id)
    if last_attempt:
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            secs_since = (datetime.utcnow() - last_dt).total_seconds()
            if secs_since < 900:  # 15 minutes
                remaining = int(900 - secs_since)
                mins = remaining // 60
                secs = remaining % 60
                raise HTTPException(
                    status_code=400,
                    detail=f"Cooldown active. Wait {mins}:{secs:02d} before trying again."
                )
        except ValueError:
            pass
    
    # Create game session
    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "player_id": player_id,
        "grab_id": grab_id,
        "grab_name": grab["name"],
        "status": "active",
        "started_at": datetime.utcnow().isoformat(),
    }
    
    await db.packagegrab_games.insert_one(game)
    
    return {
        "game_id": game_id,
        "grab_name": grab["name"],
    }


@api_router.post("/packagegrabs/game/{game_id}/complete")
async def complete_package_grab(game_id: str, won: bool, boxes_collected: int, distance_traveled: int, standalone: bool = False):
    """Complete a package grab game and award rewards if won"""
    game = await db.packagegrab_games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    if game["status"] != "active":
        raise HTTPException(status_code=400, detail="Game already completed")
    
    player = await db.players.find_one({"id": game["player_id"]})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    grab_id = game["grab_id"]
    
    # Update game status
    await db.packagegrab_games.update_one(
        {"id": game_id},
        {"$set": {
            "status": "completed",
            "won": won,
            "boxes_collected": boxes_collected,
            "distance_traveled": distance_traveled,
            "completed_at": datetime.utcnow().isoformat(),
        }}
    )
    
    # Set cooldown (15 minutes win or lose) - only for map-based games, not standalone
    if not standalone:
        await db.players.update_one(
            {"id": game["player_id"]},
            {"$set": {f"packagegrab_cooldowns.{grab_id}": datetime.utcnow().isoformat()}}
        )
    
    if won:
        # Calculate rewards based on boxes collected
        # Get level from player's stored preference or use default
        level = player.get("packagegrab_level", 1)
        
        # Base reward for finishing
        base_finish_reward = 20
        
        # Box bonus - each box is worth more at higher levels
        per_box_value = 8 + level * 2
        box_bonus = boxes_collected * per_box_value
        
        # Level multiplier
        level_multiplier = 1 + (level - 1) * 0.12
        level_bonus = int((base_finish_reward + box_bonus) * (level_multiplier - 1))
        
        cash_reward = base_finish_reward + box_bonus + level_bonus
        
        # XP based on boxes collected
        base_xp = 15 + boxes_collected * 3
        xp_reward = int(base_xp * level_multiplier)
        
        # Reputation
        rep_reward = max(1, boxes_collected // 5 + level // 4)
        
        # Apply 50% reduction for standalone/options panel games
        if standalone:
            cash_reward = cash_reward // 2
            xp_reward = xp_reward // 2
            rep_reward = max(1, rep_reward // 2)
        
        await db.players.update_one(
            {"id": game["player_id"]},
            {"$inc": {"cash": cash_reward, "xp": xp_reward, "reputation": rep_reward}}
        )
        
        updated_player = await db.players.find_one({"id": game["player_id"]})
        
        return {
            "success": True,
            "won": True,
            "message": f"📦🚚 DELIVERY COMPLETE! {boxes_collected} boxes delivered on {game['grab_name']}!",
            "grab_name": game["grab_name"],
            "boxes_collected": boxes_collected,
            "distance_traveled": distance_traveled,
            "rewards": {
                "cash": cash_reward,
                "xp": xp_reward,
                "reputation": rep_reward,
            },
            "cash": updated_player.get("cash", 0),
            "standalone": standalone,
        }
    else:
        return {
            "success": True,
            "won": False,
            "message": f"💥 CRASHED! Lost {boxes_collected} boxes on {game['grab_name']}!",
            "grab_name": game["grab_name"],
            "boxes_collected": 0,
            "distance_traveled": distance_traveled,
            "rewards": None,
        }


# ============== SHOOTOUT SIMULATOR MINI-GAME ==============

SHOOTOUT_NAMES = [
    "Back Alley Brawl", "Street Showdown", "Gang Turf", "Warehouse Fight",
    "Dock Shootout", "Corner Clash", "Night Battle", "Urban Warfare",
    "Block War", "Territory Dispute", "Street Justice", "Gang Rumble",
]

@api_router.get("/shootouts/spawn")
async def spawn_shootouts(latitude: float, longitude: float, player_level: int = 1):
    """Spawn shootout simulator markers near the player"""
    # Create deterministic ID based on grid location
    grid_lat = round(latitude * 100) / 100
    grid_lng = round(longitude * 100) / 100
    area_seed = hash(f"shootout_{grid_lat}_{grid_lng}")
    random.seed(area_seed)
    
    shootout_id = f"shootout_{abs(area_seed) % 100000}"
    
    # Check if shootout already exists
    existing = await db.shootouts.find({
        "latitude": {"$gte": grid_lat - 0.01, "$lte": grid_lat + 0.01},
        "longitude": {"$gte": grid_lng - 0.01, "$lte": grid_lng + 0.01}
    }).to_list(length=10)
    
    if existing:
        return [serialize_doc(r) for r in existing]
    
    # Generate a new shootout location
    shootout = {
        "id": shootout_id,
        "name": SHOOTOUT_NAMES[abs(area_seed) % len(SHOOTOUT_NAMES)],
        "latitude": grid_lat + (random.random() - 0.5) * 0.007,
        "longitude": grid_lng + (random.random() - 0.5) * 0.007,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    await db.shootouts.insert_one(shootout)
    shootout.pop("_id", None)
    return [shootout]


@api_router.post("/shootouts/{shootout_id}/start")
async def start_shootout(shootout_id: str, player_id: str):
    """Start a shootout simulator game"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    shootout = await db.shootouts.find_one({"id": shootout_id})
    if not shootout:
        raise HTTPException(status_code=404, detail="Shootout location not found")
    
    # Check cooldown (15 minutes per player per shootout)
    last_attempt = player.get("shootout_cooldowns", {}).get(shootout_id)
    if last_attempt:
        try:
            last_dt = datetime.fromisoformat(last_attempt)
            secs_since = (datetime.utcnow() - last_dt).total_seconds()
            if secs_since < 900:  # 15 minutes
                remaining = int(900 - secs_since)
                mins = remaining // 60
                secs = remaining % 60
                raise HTTPException(
                    status_code=400,
                    detail=f"Cooldown active. Wait {mins}:{secs:02d} before trying again."
                )
        except ValueError:
            pass
    
    # Create game session
    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "player_id": player_id,
        "shootout_id": shootout_id,
        "shootout_name": shootout["name"],
        "status": "active",
        "started_at": datetime.utcnow().isoformat(),
    }
    
    await db.shootout_games.insert_one(game)
    
    return {
        "game_id": game_id,
        "shootout_name": shootout["name"],
    }


@api_router.post("/shootouts/standalone/start")
async def start_standalone_shootout(player_id: str, level: int = 1):
    """Start a standalone shootout game from the options menu"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Create game session for standalone mode
    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "player_id": player_id,
        "shootout_id": "standalone",
        "shootout_name": f"Training Level {level}",
        "status": "active",
        "started_at": datetime.utcnow().isoformat(),
        "standalone": True,
        "level": level,
    }
    
    await db.shootout_games.insert_one(game)
    
    return {
        "game_id": game_id,
        "shootout_name": game["shootout_name"],
    }


@api_router.post("/shootouts/game/{game_id}/complete")
async def complete_shootout(game_id: str, hits: int, standalone: bool = False):
    """Complete a shootout game and award rewards based on hits"""
    game = await db.shootout_games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    if game["status"] != "active":
        raise HTTPException(status_code=400, detail="Game already completed")
    
    player = await db.players.find_one({"id": game["player_id"]})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    shootout_id = game["shootout_id"]
    
    # Update game status
    await db.shootout_games.update_one(
        {"id": game_id},
        {"$set": {
            "status": "completed",
            "hits": hits,
            "completed_at": datetime.utcnow().isoformat(),
        }}
    )
    
    # Set cooldown (15 minutes win or lose) - only for map-based games, not standalone
    if not standalone:
        await db.players.update_one(
            {"id": game["player_id"]},
            {"$set": {f"shootout_cooldowns.{shootout_id}": datetime.utcnow().isoformat()}}
        )
    
    if hits > 0:
        # Calculate rewards based on hits and level
        level = player.get("shootout_level", 1)
        
        # Rewards per hit scale with level
        hit_reward = 5 + level * 2
        xp_per_hit = 2 + level // 2
        
        cash_reward = hits * hit_reward
        xp_reward = hits * xp_per_hit
        rep_reward = max(1, hits // 3 + level // 5)
        
        # Apply 50% reduction for standalone/options panel games
        if standalone:
            cash_reward = cash_reward // 2
            xp_reward = xp_reward // 2
            rep_reward = max(1, rep_reward // 2)
        
        await db.players.update_one(
            {"id": game["player_id"]},
            {"$inc": {"cash": cash_reward, "xp": xp_reward, "reputation": rep_reward}}
        )
        
        updated_player = await db.players.find_one({"id": game["player_id"]})
        
        return {
            "success": True,
            "hits": hits,
            "message": f"🎯🔫 SHOOTOUT COMPLETE! {hits} hits on {game['shootout_name']}!",
            "shootout_name": game["shootout_name"],
            "rewards": {
                "cash": cash_reward,
                "xp": xp_reward,
                "reputation": rep_reward,
            },
            "cash": updated_player.get("cash", 0),
            "standalone": standalone,
        }
    else:
        return {
            "success": True,
            "hits": 0,
            "message": f"💨 NO HITS! Better luck next time at {game['shootout_name']}!",
            "shootout_name": game["shootout_name"],
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
    equipment_durability = player.get("equipment_durability", {})
    
    equipped = {}
    for slot, item_id in equipment.items():
        if item_id:
            item = ALL_ITEMS.get(item_id)
            if item:
                # Get durability from equipment_durability dict
                max_durability = get_max_durability(item_id)
                durability = equipment_durability.get(slot, max_durability)
                
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


@api_router.post("/players/{player_id}/repair-equipped/{slot}")
async def repair_equipped_item(player_id: str, slot: str):
    """Repair an equipped item (restores durability)"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if slot not in EQUIPMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid equipment slot")
    
    equipment = player.get("equipment", {})
    item_id = equipment.get(slot)
    
    if not item_id:
        raise HTTPException(status_code=400, detail="No item equipped in that slot")
    
    equipment_durability = player.get("equipment_durability", {})
    current_durability = equipment_durability.get(slot, get_max_durability(item_id))
    max_durability = get_max_durability(item_id)
    
    if current_durability >= max_durability:
        raise HTTPException(status_code=400, detail="Item is already at full durability")
    
    repair_cost = calculate_repair_cost(item_id, current_durability)
    
    if player.get("cash", 0) < repair_cost:
        raise HTTPException(status_code=400, detail=f"Not enough cash. Repair costs ${repair_cost}")
    
    # Repair the equipped item
    equipment_durability[slot] = max_durability
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"equipment_durability": equipment_durability}, "$inc": {"cash": -repair_cost}}
    )
    
    item = ALL_ITEMS.get(item_id, {})
    return {
        "message": f"Repaired equipped {item.get('name', 'item')} for ${repair_cost}",
        "repair_cost": repair_cost,
        "item_name": item.get("name", "Unknown"),
        "slot": slot,
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
    equipment_durability = player.get("equipment_durability", {})
    
    # Create inventory item for unequipped gear with current durability
    item_durability = equipment_durability.get(slot, get_max_durability(current_item))
    unequipped_item = create_inventory_item(current_item, item_durability)
    inventory.append(unequipped_item)
    
    # Clear the durability for this slot
    if slot in equipment_durability:
        del equipment_durability[slot]
    
    await db.players.update_one(
        {"id": player_id},
        {"$set": {
            f"equipment.{slot}": None, 
            "equipment_durability": equipment_durability,
            "inventory": inventory
        }}
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
    item_durability = None
    for idx, inv_item in enumerate(inventory):
        i_id = inv_item.get("item_id") if isinstance(inv_item, dict) else inv_item
        if i_id == equipment_id:
            item_index = idx
            item_durability = inv_item.get("durability", get_max_durability(equipment_id))
            # Check if item is broken
            if is_item_broken(inv_item):
                raise HTTPException(status_code=400, detail="Cannot equip broken item. Repair it first!")
            break
    
    if item_index is None:
        raise HTTPException(status_code=400, detail="Item not in inventory")
    
    slot = equipment["equipment_type"]
    current_equipped = player["equipment"].get(slot)
    equipment_durability = player.get("equipment_durability", {})
    
    # Get the item being equipped (to preserve durability)
    equipped_item = inventory[item_index]
    
    # Remove item from inventory
    inventory.pop(item_index)
    
    # Move old item back to inventory if exists
    if current_equipped:
        # Get durability of the previously equipped item
        old_durability = equipment_durability.get(slot, get_max_durability(current_equipped))
        old_item = create_inventory_item(current_equipped, old_durability)
        inventory.append(old_item)
    
    # Set durability for newly equipped item
    equipment_durability[slot] = item_durability
    
    # Update equipment, durability, and inventory
    await db.players.update_one(
        {"id": player_id},
        {"$set": {
            f"equipment.{slot}": equipment_id, 
            "equipment_durability": equipment_durability,
            "inventory": inventory
        }}
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
    territories = await db.territories.find({"owner_id": player_id}).to_list(length=None)  # No limit - unlimited territories
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


@api_router.post("/fitness/{player_id}/sync-distance")
async def sync_travel_distance(player_id: str, distance_meters: int):
    """
    Sync traveled distance to all active travel_distance missions.
    Also applies vehicle durability loss (10 per full km).
    Returns updated mission progresses and vehicle durability.
    """
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if distance_meters <= 0:
        return {"synced_distance": 0, "missions_updated": [], "vehicle_damage": 0}
    
    # Get all active travel_distance missions for this player
    active_ids = player.get("active_missions", [])
    missions_updated = []
    
    if active_ids:
        missions = await db.missions.find({
            "id": {"$in": active_ids}, 
            "mission_type": "travel_distance"
        }).to_list(50)
        
        for m in missions:
            pp = m.get("player_progress", {})
            player_data = pp.get(player_id, {"progress": 0})
            old_progress = player_data.get("progress", 0)
            new_progress = min(old_progress + distance_meters, m.get("goal_target", 999999))
            
            player_data["progress"] = new_progress
            pp[player_id] = player_data
            
            await db.missions.update_one(
                {"id": m["id"]},
                {"$set": {"player_progress": pp}}
            )
            
            missions_updated.append({
                "mission_id": m["id"],
                "title": m.get("title", "Unknown"),
                "old_progress": old_progress,
                "new_progress": new_progress,
                "target": m.get("goal_target", 0),
                "completed": new_progress >= m.get("goal_target", 0)
            })
    
    # Apply vehicle durability loss: 10 durability per full km
    full_km = distance_meters // 1000
    vehicle_damage = 0
    vehicle_new_durability = None
    
    if full_km > 0:
        equipment = player.get("equipment", {})
        vehicle_id = equipment.get("vehicle")
        
        if vehicle_id:
            # Use equipment_durability dict (same as battle durability system)
            equipment_durability = player.get("equipment_durability", {})
            
            # Initialize vehicle durability if not present
            if "vehicle" not in equipment_durability:
                max_dur = get_max_durability(vehicle_id)
                equipment_durability["vehicle"] = max_dur
            
            current_dur = equipment_durability.get("vehicle", 100)
            
            # 10 durability loss per km
            vehicle_damage = full_km * 10
            new_dur = max(0, current_dur - vehicle_damage)
            equipment_durability["vehicle"] = new_dur
            vehicle_new_durability = new_dur
            
            await db.players.update_one(
                {"id": player_id},
                {"$set": {"equipment_durability": equipment_durability}}
            )
    
    return {
        "synced_distance": distance_meters,
        "missions_updated": missions_updated,
        "vehicle_damage": vehicle_damage,
        "vehicle_new_durability": vehicle_new_durability
    }


# Background removal endpoint for shootout character sprites
@api_router.get("/sprites/remove-bg")
async def remove_background_from_sprite(url: str):
    """Remove background from a sprite image and return as PNG with transparency"""
    import hashlib
    import requests
    from PIL import Image
    from io import BytesIO
    
    try:
        # Create a hash of the URL to use as filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_dir = STATIC_DIR / "sprites"
        cache_dir.mkdir(exist_ok=True)
        cache_path = cache_dir / f"{url_hash}.png"
        
        # Check if already cached
        if cache_path.exists():
            return FileResponse(cache_path, media_type="image/png")
        
        # Download the image
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        
        # Process with rembg
        from rembg import remove
        
        input_image = Image.open(BytesIO(response.content))
        output_image = remove(input_image)
        
        # Save to cache
        output_image.save(cache_path, "PNG")
        
        return FileResponse(cache_path, media_type="image/png")
    except Exception as e:
        logging.error(f"Error removing background: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")


# ========== PRIVACY POLICY API ==========
@api_router.get("/privacy")
async def get_privacy_policy():
    """Return the privacy policy for Street Legends - publicly accessible"""
    return {
        "app_name": "Street Legends",
        "last_updated": "2026-09-20",
        "contact_email": "hushmusicent419@gmail.com",
        "policy": {
            "introduction": "Street Legends ('we', 'our', or 'us') is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you use our mobile game.",
            "data_collected": {
                "account_info": [
                    "Username and display name",
                    "Email address (if provided)",
                    "Profile picture (optional)",
                    "Password (encrypted, never stored in plain text)"
                ],
                "gameplay_data": [
                    "Character stats and progress",
                    "In-game currency and inventory",
                    "Guild membership and social interactions",
                    "Battle history and achievements",
                    "Mission completion data"
                ],
                "location_data": "GPS location is used for gameplay features like finding missions, monsters, and territories. Location is processed in real-time and not permanently stored.",
                "device_info": "Basic device information for app compatibility and crash reporting"
            },
            "how_data_is_used": [
                "Provide and maintain core gameplay features",
                "Track your progress, stats, and achievements",
                "Enable multiplayer features like guilds and PvP",
                "Improve app performance and user experience",
                "Respond to support requests"
            ],
            "data_storage": {
                "where_stored": "Data is stored securely on MongoDB Atlas cloud servers with encryption at rest",
                "security_measures": [
                    "Encrypted data transmission (HTTPS/TLS)",
                    "Secure cloud infrastructure with 24/7 monitoring",
                    "Regular security updates and assessments",
                    "Access controls limiting data access"
                ]
            },
            "third_party_services": [
                {"name": "MongoDB Atlas", "purpose": "Secure database hosting"},
                {"name": "Emergent Object Storage", "purpose": "Profile picture and asset storage"},
                {"name": "OpenStreetMap/Leaflet", "purpose": "Map data for location-based gameplay"},
                {"name": "Expo/EAS", "purpose": "App distribution and updates"}
            ],
            "data_sharing": "We do NOT sell your personal data to third parties. Data is only shared with service providers under strict confidentiality agreements, or if required by law.",
            "data_deletion": {
                "how_to_request": [
                    "Use the Delete Account option in the app's Settings/Options menu",
                    "Email us at hushmusicent419@gmail.com with your username"
                ],
                "process": "Upon receiving a deletion request, we will verify your identity, delete your account and personal data within 30 days, and send confirmation once complete."
            },
            "contact": {
                "email": "hushmusicent419@gmail.com",
                "response_time": "We aim to respond to all inquiries within 5 business days"
            }
        }
    }


# =============================================================================
# ADMIN ENDPOINTS (Protected with secret key)
# =============================================================================

ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "")

@api_router.delete("/admin/delete-players-by-name")
async def admin_delete_players_by_name(
    name: str = Query(..., description="Name to search for (case-insensitive)"),
    admin_key: str = Query(..., description="Admin secret key for authorization")
):
    """
    Admin endpoint to delete player accounts by name and free their territories.
    Requires admin_key for authorization.
    """
    # Verify admin key
    if not ADMIN_SECRET_KEY or admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Find players matching the name (case-insensitive)
    players = await db.players.find({
        "$or": [
            {"name": {"$regex": name, "$options": "i"}},
            {"username": {"$regex": name, "$options": "i"}}
        ]
    }).to_list(length=100)
    
    if not players:
        return {"message": f"No players found matching '{name}'", "deleted": 0, "territories_freed": 0}
    
    player_ids = [p['id'] for p in players]
    player_names = [f"{p.get('name', 'Unknown')} ({p.get('username', 'no-username')})" for p in players]
    
    # Free up territories owned by these players
    territory_result = await db.territories.update_many(
        {"owner_id": {"$in": player_ids}},
        {"$set": {"owner_id": None, "owner_name": None, "captured_at": None}}
    )
    
    # Delete the player accounts
    delete_result = await db.players.delete_many({"id": {"$in": player_ids}})
    
    # Clean up related game data
    cleanup_collections = ['battles', 'missions', 'car_chases', 'shootouts', 'runaways', 'package_grabs', 'castle_games']
    for collection in cleanup_collections:
        try:
            await db[collection].delete_many({"player_id": {"$in": player_ids}})
        except Exception:
            pass
    
    return {
        "message": f"Successfully deleted {delete_result.deleted_count} player(s) matching '{name}'",
        "deleted_players": player_names,
        "deleted_count": delete_result.deleted_count,
        "territories_freed": territory_result.modified_count
    }

@api_router.delete("/admin/reset-all-data")
async def admin_reset_all_data(
    admin_key: str = Query(..., description="Admin secret key for authorization"),
    confirm: str = Query(..., description="Type 'CONFIRM_RESET' to proceed")
):
    """
    Admin endpoint to reset ALL game data (players, territories, game sessions).
    Use with extreme caution - this cannot be undone!
    """
    # Verify admin key
    if not ADMIN_SECRET_KEY or admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Require confirmation
    if confirm != "CONFIRM_RESET":
        raise HTTPException(status_code=400, detail="You must set confirm='CONFIRM_RESET' to proceed")
    
    results = {}
    
    # Delete all players
    player_result = await db.players.delete_many({})
    results["players_deleted"] = player_result.deleted_count
    
    # Free all territories
    territory_result = await db.territories.update_many(
        {},
        {"$set": {"owner_id": None, "owner_name": None, "captured_at": None}}
    )
    results["territories_freed"] = territory_result.modified_count
    
    # Clear game sessions
    cleanup_collections = ['battles', 'missions', 'shops', 'casino_games', 'car_chases', 'shootouts', 'runaways', 'package_grabs', 'castle_games']
    for collection in cleanup_collections:
        try:
            r = await db[collection].delete_many({})
            results[f"{collection}_cleared"] = r.deleted_count
        except Exception:
            pass
    
    return {
        "message": "Database reset complete!",
        "results": results
    }


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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        await run_in_threadpool(init_storage)
        logger.info("Storage initialized on startup")
    except Exception as e:
        logger.warning(f"Storage initialization failed on startup: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
