#!/usr/bin/env python3
"""
Clear all MongoDB collections for fresh testing
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DB = os.getenv('MONGODB_DB', 'yazaki_chatbot')

def clear_database():
    """Clear all collections in the MongoDB database"""
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')  # Test connection
        
        db = client[MONGODB_DB]
        
        # Get all collections
        collections = db.list_collection_names()
        
        if not collections:
            print("ℹ️  Database is already empty!")
            return
        
        print(f"📊 Found {len(collections)} collection(s) in '{MONGODB_DB}' database:")
        for coll in collections:
            count = db[coll].count_documents({})
            print(f"   - {coll}: {count} documents")
        
        print("\n⚠️  WARNING: This will delete ALL data from the database!")
        confirm = input("Type 'YES' to confirm deletion: ")
        
        if confirm.strip().upper() == 'YES':
            total_deleted = 0
            for coll in collections:
                result = db[coll].delete_many({})
                print(f"✅ Cleared {coll}: {result.deleted_count} documents deleted")
                total_deleted += result.deleted_count
            
            print(f"\n🎉 Successfully deleted {total_deleted} total documents!")
            print("✨ Database is now ready for fresh testing!")
        else:
            print("❌ Operation cancelled")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    clear_database()
