#!/usr/bin/env python3
"""
MongoDB Manager - Utility script for managing the Yazaki chatbot database

Usage:
    # User Registration Commands
    python scripts/mongodb_manager.py list                    # List all registrations
    python scripts/mongodb_manager.py count                   # Count total registrations
    python scripts/mongodb_manager.py stats                   # Show statistics
    python scripts/mongodb_manager.py search --name "John"    # Search by name
    python scripts/mongodb_manager.py search --email "john@example.com"  # Search by email
    python scripts/mongodb_manager.py search --company "ABC"  # Search by company
    python scripts/mongodb_manager.py export --format csv     # Export to CSV
    python scripts/mongodb_manager.py export --format json    # Export to JSON
    python scripts/mongodb_manager.py delete --id <id>        # Delete by ID
    python scripts/mongodb_manager.py clear                   # Clear all data (careful!)
    
    # Conversation Commands
    python scripts/mongodb_manager.py conversations                      # List recent conversations
    python scripts/mongodb_manager.py conversations --limit 50           # List last 50 conversations
    python scripts/mongodb_manager.py conversations --session-id <id>    # Filter by session
    python scripts/mongodb_manager.py conv-stats                         # Show conversation statistics
    python scripts/mongodb_manager.py session --session-id <id>          # View full session history
    python scripts/mongodb_manager.py clear-conversations                # Clear all conversations (careful!)
"""

import os
import sys
import json
import csv
from datetime import datetime
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
from bson import ObjectId

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DB = os.getenv('MONGODB_DB', 'yazaki_chatbot')
MONGODB_COLLECTION = os.getenv('MONGODB_COLLECTION', 'user_registrations')
MONGODB_CONVERSATIONS = os.getenv('MONGODB_CONVERSATIONS', 'conversations')

class MongoDBManager:
    """Manager class for MongoDB operations"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[MONGODB_DB]
            self.collection = self.db[MONGODB_COLLECTION]
            self.conversations = self.db[MONGODB_CONVERSATIONS]
            print(f"✅ Connected to MongoDB: {MONGODB_DB}")
            print(f"   Collections: {MONGODB_COLLECTION}, {MONGODB_CONVERSATIONS}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"❌ MongoDB connection failed: {e}")
            print("\nMake sure MongoDB is running:")
            print("  brew services start mongodb-community")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    
    def list_all(self, limit=None):
        """List all registrations"""
        try:
            query = self.collection.find().sort("registered_at", -1)
            if limit:
                query = query.limit(limit)
            
            registrations = list(query)
            
            if not registrations:
                print("📭 No registrations found")
                return
            
            print(f"\n📋 Found {len(registrations)} registration(s):\n")
            print("=" * 120)
            
            for i, reg in enumerate(registrations, 1):
                print(f"\n{i}. Registration ID: {reg['_id']}")
                print(f"   👤 Name: {reg.get('full_name', 'N/A')}")
                print(f"   📧 Email: {reg.get('email', 'N/A')}")
                print(f"   🏢 Company: {reg.get('company_name', 'N/A')}")
                print(f"   📁 Project: {reg.get('project_name', 'N/A')}")
                print(f"   🏷️  Type: {reg.get('supplier_type', 'N/A')}")
                
                location = reg.get('location', {})
                city = location.get('city', 'N/A')
                country = location.get('country', 'N/A')
                print(f"   📍 Location: {city}, {country}")
                
                registered = reg.get('registered_at', 'N/A')
                if registered != 'N/A':
                    registered = registered.strftime("%Y-%m-%d %H:%M:%S")
                print(f"   📅 Registered: {registered}")
            
            print("\n" + "=" * 120)
            
        except Exception as e:
            print(f"❌ Error listing registrations: {e}")
    
    def count_total(self):
        """Count total registrations"""
        try:
            total = self.collection.count_documents({})
            print(f"\n📊 Total Registrations: {total}")
            return total
        except Exception as e:
            print(f"❌ Error counting: {e}")
            return 0
    
    def show_statistics(self):
        """Show database statistics"""
        try:
            print("\n📊 Database Statistics")
            print("=" * 60)
            
            # Total count
            total = self.collection.count_documents({})
            print(f"\n📈 Total Registrations: {total}")
            
            if total == 0:
                print("\n📭 No data available yet")
                return
            
            # Count by supplier type
            print("\n🏷️  By Supplier Type:")
            pipeline = [
                {"$group": {"_id": "$supplier_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            for result in self.collection.aggregate(pipeline):
                print(f"   • {result['_id']}: {result['count']}")
            
            # Count by country
            print("\n🌍 By Country:")
            pipeline = [
                {"$group": {"_id": "$location.country", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            for result in self.collection.aggregate(pipeline):
                print(f"   • {result['_id']}: {result['count']}")
            
            # Count by company
            print("\n🏢 By Company (Top 10):")
            pipeline = [
                {"$group": {"_id": "$company_name", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            for result in self.collection.aggregate(pipeline):
                print(f"   • {result['_id']}: {result['count']}")
            
            # Recent registrations
            print("\n📅 Recent Activity:")
            recent = self.collection.find().sort("registered_at", -1).limit(5)
            for reg in recent:
                name = reg.get('full_name', 'Unknown')
                company = reg.get('company_name', 'Unknown')
                registered = reg.get('registered_at', '')
                if registered:
                    registered = registered.strftime("%Y-%m-%d %H:%M")
                print(f"   • {name} ({company}) - {registered}")
            
            print("\n" + "=" * 60)
            
        except Exception as e:
            print(f"❌ Error generating statistics: {e}")
    
    def search(self, name=None, email=None, company=None, supplier_type=None, city=None, country=None):
        """Search registrations"""
        try:
            query = {}
            
            if name:
                query['full_name'] = {'$regex': name, '$options': 'i'}
            if email:
                query['email'] = {'$regex': email, '$options': 'i'}
            if company:
                query['company_name'] = {'$regex': company, '$options': 'i'}
            if supplier_type:
                query['supplier_type'] = supplier_type
            if city:
                query['location.city'] = {'$regex': city, '$options': 'i'}
            if country:
                query['location.country'] = {'$regex': country, '$options': 'i'}
            
            if not query:
                print("⚠️  Please provide at least one search criterion")
                return
            
            results = list(self.collection.find(query))
            
            if not results:
                print(f"📭 No results found for: {query}")
                return
            
            print(f"\n🔍 Found {len(results)} result(s):")
            self._display_results(results)
            
        except Exception as e:
            print(f"❌ Error searching: {e}")
    
    def _display_results(self, results):
        """Display search results"""
        print("\n" + "=" * 120)
        for i, reg in enumerate(results, 1):
            print(f"\n{i}. ID: {reg['_id']}")
            print(f"   👤 {reg.get('full_name', 'N/A')} | 🏢 {reg.get('company_name', 'N/A')}")
            print(f"   📁 {reg.get('project_name', 'N/A')} | 🏷️  {reg.get('supplier_type', 'N/A')}")
            location = reg.get('location', {})
            print(f"   📍 {location.get('city', 'N/A')}, {location.get('country', 'N/A')}")
        print("\n" + "=" * 120)
    
    def export_csv(self, filename='registrations.csv'):
        """Export to CSV file"""
        try:
            registrations = list(self.collection.find())
            
            if not registrations:
                print("📭 No data to export")
                return
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'full_name', 'company_name', 'project_name', 
                             'supplier_type', 'city', 'country', 'registered_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for reg in registrations:
                    location = reg.get('location', {})
                    registered = reg.get('registered_at', '')
                    if registered:
                        registered = registered.strftime("%Y-%m-%d %H:%M:%S")
                    
                    writer.writerow({
                        'id': str(reg['_id']),
                        'full_name': reg.get('full_name', ''),
                        'company_name': reg.get('company_name', ''),
                        'project_name': reg.get('project_name', ''),
                        'supplier_type': reg.get('supplier_type', ''),
                        'city': location.get('city', ''),
                        'country': location.get('country', ''),
                        'registered_at': registered
                    })
            
            print(f"✅ Exported {len(registrations)} records to {filename}")
            
        except Exception as e:
            print(f"❌ Error exporting to CSV: {e}")
    
    def export_json(self, filename='registrations.json'):
        """Export to JSON file"""
        try:
            registrations = list(self.collection.find())
            
            if not registrations:
                print("📭 No data to export")
                return
            
            # Convert ObjectId and datetime to string
            for reg in registrations:
                reg['_id'] = str(reg['_id'])
                if 'registered_at' in reg:
                    reg['registered_at'] = reg['registered_at'].isoformat()
                if 'last_active' in reg:
                    reg['last_active'] = reg['last_active'].isoformat()
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(registrations, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"✅ Exported {len(registrations)} records to {filename}")
            
        except Exception as e:
            print(f"❌ Error exporting to JSON: {e}")
    
    def delete_by_id(self, record_id):
        """Delete a specific registration by ID"""
        try:
            result = self.collection.delete_one({'_id': ObjectId(record_id)})
            
            if result.deleted_count > 0:
                print(f"✅ Deleted registration: {record_id}")
            else:
                print(f"⚠️  No registration found with ID: {record_id}")
                
        except Exception as e:
            print(f"❌ Error deleting: {e}")
    
    def clear_all(self):
        """Clear all registrations (use with caution!)"""
        try:
            count = self.collection.count_documents({})
            
            if count == 0:
                print("📭 Collection is already empty")
                return
            
            confirm = input(f"⚠️  Are you sure you want to delete ALL {count} registrations? (yes/no): ")
            
            if confirm.lower() == 'yes':
                result = self.collection.delete_many({})
                print(f"✅ Deleted {result.deleted_count} registrations")
            else:
                print("❌ Operation cancelled")
                
        except Exception as e:
            print(f"❌ Error clearing collection: {e}")
    
    def list_conversations(self, session_id=None, limit=20):
        """List conversations, optionally filtered by session ID"""
        try:
            query = {}
            if session_id:
                query['session_id'] = session_id
            
            conversations = list(self.conversations.find(query).sort("timestamp", -1).limit(limit))
            
            if not conversations:
                print(f"📭 No conversations found{' for session ' + session_id[:8] + '...' if session_id else ''}")
                return
            
            print(f"\n💬 Found {len(conversations)} conversation(s):\n")
            print("=" * 120)
            
            for i, conv in enumerate(conversations, 1):
                session = conv.get('session_id', 'N/A')
                timestamp = conv.get('timestamp', 'N/A')
                if timestamp != 'N/A':
                    timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                user_msg = conv.get('user_message', 'N/A')
                assistant_msg = conv.get('assistant_message', 'N/A')
                user_info = conv.get('user_info', {})
                
                print(f"\n{i}. Conversation at {timestamp}")
                print(f"   🆔 Session: {session[:16]}..." if len(session) > 16 else f"   🆔 Session: {session}")
                print(f"   👤 User: {user_info.get('full_name', 'N/A')} ({user_info.get('company_name', 'N/A')})")
                print(f"   📝 User Message: {user_msg[:100]}{'...' if len(user_msg) > 100 else ''}")
                print(f"   🤖 Assistant Response: {assistant_msg[:150]}{'...' if len(assistant_msg) > 150 else ''}")
                
                metadata = conv.get('metadata', {})
                if metadata:
                    sources = metadata.get('sources', [])
                    if sources:
                        print(f"   📚 Sources: {', '.join(sources)}")
            
            print("\n" + "=" * 120)
            
        except Exception as e:
            print(f"❌ Error listing conversations: {e}")
    
    def conversation_stats(self):
        """Show conversation statistics"""
        try:
            print("\n💬 Conversation Statistics")
            print("=" * 60)
            
            total = self.conversations.count_documents({})
            print(f"\n📊 Total Conversations: {total}")
            
            if total == 0:
                print("\n📭 No conversations yet")
                return
            
            # Count by session
            print("\n🔢 By Session (Top 10):")
            pipeline = [
                {"$group": {"_id": "$session_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            for result in self.conversations.aggregate(pipeline):
                session_id = result['_id']
                count = result['count']
                # Get user info for this session
                conv = self.conversations.find_one({"session_id": session_id})
                user_name = "Unknown"
                if conv:
                    user_info = conv.get('user_info', {})
                    user_name = user_info.get('full_name', 'Unknown')
                print(f"   • {session_id[:12]}... ({user_name}): {count} messages")
            
            # Recent activity
            print("\n📅 Recent Conversations:")
            recent = self.conversations.find().sort("timestamp", -1).limit(5)
            for conv in recent:
                user_info = conv.get('user_info', {})
                name = user_info.get('full_name', 'Unknown')
                timestamp = conv.get('timestamp', '')
                if timestamp:
                    timestamp = timestamp.strftime("%Y-%m-%d %H:%M")
                user_msg = conv.get('user_message', '')[:50]
                print(f"   • {name} ({timestamp}): {user_msg}...")
            
            print("\n" + "=" * 60)
            
        except Exception as e:
            print(f"❌ Error generating conversation stats: {e}")
    
    def get_session_conversations(self, session_id):
        """Get all conversations for a specific session"""
        try:
            conversations = list(self.conversations.find({"session_id": session_id}).sort("timestamp", 1))
            
            if not conversations:
                print(f"📭 No conversations found for session {session_id[:8]}...")
                return
            
            # Get user info
            user_info = conversations[0].get('user_info', {})
            
            print(f"\n💬 Session Conversation History")
            print("=" * 100)
            print(f"🆔 Session ID: {session_id}")
            print(f"👤 User: {user_info.get('full_name', 'N/A')} from {user_info.get('company_name', 'N/A')}")
            print(f"📊 Total Messages: {len(conversations)}")
            print("=" * 100)
            
            for i, conv in enumerate(conversations, 1):
                timestamp = conv.get('timestamp', 'N/A')
                if timestamp != 'N/A':
                    timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                user_msg = conv.get('user_message', '')
                assistant_msg = conv.get('assistant_message', '')
                
                print(f"\n--- Exchange {i} ({timestamp}) ---")
                print(f"\n👤 USER:\n{user_msg}")
                print(f"\n🤖 ASSISTANT:\n{assistant_msg}")
                
                metadata = conv.get('metadata', {})
                if metadata.get('sources'):
                    print(f"\n📚 Sources: {', '.join(metadata['sources'])}")
                print("\n" + "-" * 100)
            
        except Exception as e:
            print(f"❌ Error retrieving session conversations: {e}")
    
    def clear_conversations(self):
        """Clear all conversations (with confirmation)"""
        try:
            total = self.conversations.count_documents({})
            
            if total == 0:
                print("📭 No conversations to clear")
                return
            
            print(f"\n⚠️  WARNING: This will delete all {total} conversations!")
            confirm = input("Type 'DELETE' to confirm: ")
            
            if confirm == 'DELETE':
                result = self.conversations.delete_many({})
                print(f"✅ Deleted {result.deleted_count} conversations")
            else:
                print("❌ Operation cancelled")
                
        except Exception as e:
            print(f"❌ Error clearing conversations: {e}")
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("\n👋 Connection closed")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='MongoDB Manager for Yazaki Chatbot')
    parser.add_argument('command', choices=[
        'list', 'count', 'stats', 'search', 'export', 'delete', 'clear',
        'conversations', 'conv-stats', 'session', 'clear-conversations'
    ], help='Command to execute')
    parser.add_argument('--name', help='Search by name')
    parser.add_argument('--email', help='Search by email')
    parser.add_argument('--company', help='Search by company')
    parser.add_argument('--type', help='Search by supplier type')
    parser.add_argument('--city', help='Search by city')
    parser.add_argument('--country', help='Search by country')
    parser.add_argument('--format', choices=['csv', 'json'], help='Export format')
    parser.add_argument('--id', help='Registration ID for deletion')
    parser.add_argument('--session-id', help='Session ID for filtering conversations')
    parser.add_argument('--limit', type=int, help='Limit number of results')
    parser.add_argument('--output', help='Output filename for export')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = MongoDBManager()
    
    try:
        if args.command == 'list':
            manager.list_all(limit=args.limit)
        
        elif args.command == 'count':
            manager.count_total()
        
        elif args.command == 'stats':
            manager.show_statistics()
        
        elif args.command == 'search':
            manager.search(
                name=args.name,
                email=args.email,
                company=args.company,
                supplier_type=args.type,
                city=args.city,
                country=args.country
            )
        
        elif args.command == 'export':
            if not args.format:
                print("❌ Please specify export format: --format csv or --format json")
            else:
                filename = args.output or f'registrations.{args.format}'
                if args.format == 'csv':
                    manager.export_csv(filename)
                else:
                    manager.export_json(filename)
        
        elif args.command == 'delete':
            if not args.id:
                print("❌ Please specify registration ID: --id <id>")
            else:
                manager.delete_by_id(args.id)
        
        elif args.command == 'clear':
            manager.clear_all()
        
        elif args.command == 'conversations':
            limit = args.limit or 20
            manager.list_conversations(session_id=args.session_id, limit=limit)
        
        elif args.command == 'conv-stats':
            manager.conversation_stats()
        
        elif args.command == 'session':
            if not args.session_id:
                print("❌ Please specify session ID: --session-id <id>")
            else:
                manager.get_session_conversations(args.session_id)
        
        elif args.command == 'clear-conversations':
            manager.clear_conversations()
    
    finally:
        manager.close()

if __name__ == '__main__':
    main()
