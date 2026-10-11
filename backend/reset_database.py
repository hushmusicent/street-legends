"""
Database Reset Script for Play Store Launch
Clears all player profiles and frees up all territories.
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def reset_database():
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGO_URL')
    if not mongo_url:
        print("ERROR: MONGO_URL not found in environment")
        return False
    
    client = AsyncIOMotorClient(mongo_url)
    db = client.gta_quest
    
    print("=" * 50)
    print("DATABASE RESET FOR PLAY STORE LAUNCH")
    print("=" * 50)
    
    # Count existing data
    player_count = await db.players.count_documents({})
    territory_count = await db.territories.count_documents({})
    
    print(f"\nCurrent data:")
    print(f"  - Players: {player_count}")
    print(f"  - Territories: {territory_count}")
    
    # Delete all players
    print("\n[1/4] Deleting all player profiles...")
    result = await db.players.delete_many({})
    print(f"  ✓ Deleted {result.deleted_count} players")
    
    # Clear all territory ownership
    print("\n[2/4] Freeing up all territories (removing owners)...")
    result = await db.territories.update_many(
        {},
        {"$set": {"owner_id": None, "owner_name": None, "captured_at": None}}
    )
    print(f"  ✓ Freed up {result.modified_count} territories")
    
    # Clear any game sessions
    print("\n[3/4] Clearing game sessions...")
    collections_to_clear = [
        'battles', 'missions', 'shops', 'casino_games',
        'car_chases', 'shootouts', 'runaways', 'package_grabs', 'castle_games'
    ]
    for collection_name in collections_to_clear:
        try:
            result = await db[collection_name].delete_many({})
            if result.deleted_count > 0:
                print(f"  ✓ Cleared {result.deleted_count} from {collection_name}")
        except Exception as e:
            pass  # Collection might not exist
    
    # Verify reset
    print("\n[4/4] Verifying reset...")
    final_player_count = await db.players.count_documents({})
    territories_with_owners = await db.territories.count_documents({"owner_id": {"$ne": None}})
    
    print(f"\nFinal state:")
    print(f"  - Players: {final_player_count}")
    print(f"  - Owned territories: {territories_with_owners}")
    
    if final_player_count == 0 and territories_with_owners == 0:
        print("\n✅ DATABASE RESET SUCCESSFUL!")
        print("Your game is ready for fresh Play Store players!")
        return True
    else:
        print("\n⚠️ Reset may be incomplete. Please check.")
        return False

if __name__ == "__main__":
    asyncio.run(reset_database())
