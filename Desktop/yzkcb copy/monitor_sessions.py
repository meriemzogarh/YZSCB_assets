#!/usr/bin/env python3
"""
Real-time Session Monitor
Watches MongoDB for session changes
"""

import time
from pymongo import MongoClient
from datetime import datetime

def monitor_sessions():
    """Monitor sessions in real-time"""
    
    client = MongoClient('mongodb://localhost:27017/')
    db = client['yazaki_chatbot']
    sessions = db['sessions']
    
    print("\n" + "="*70)
    print("👀 REAL-TIME SESSION MONITOR")
    print("="*70)
    print("\nWatching for session changes... (Ctrl+C to stop)\n")
    
    last_count = 0
    last_sessions = {}
    
    try:
        while True:
            current_count = sessions.count_documents({})
            all_sessions = list(sessions.find())
            
            # Check if count changed
            if current_count != last_count:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚡ SESSION COUNT CHANGED: {last_count} → {current_count}")
                last_count = current_count
            
            # Check each session for changes
            for s in all_sessions:
                sid = s['session_id']
                status = s['status']
                last_activity = s['last_activity']
                
                # Calculate inactive time
                now = datetime.now()
                inactive = (now - last_activity).total_seconds() / 60
                
                # Check if this is a new session or status changed
                if sid not in last_sessions:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🆕 NEW SESSION CREATED")
                    print(f"   ID: {sid[:16]}...")
                    print(f"   User: {s['user_info'].get('full_name', 'Unknown')}")
                    print(f"   Email: {s['user_info'].get('email', 'Unknown')}")
                    print(f"   Status: {status}")
                elif last_sessions[sid]['status'] != status:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 STATUS CHANGED")
                    print(f"   ID: {sid[:16]}...")
                    print(f"   {last_sessions[sid]['status']} → {status}")
                    if status == 'ended':
                        print(f"   ⏰ Session ended after {inactive:.1f} minutes of inactivity")
                        print(f"   📧 Email should be sent to admin!")
                
                # Update last known state
                last_sessions[sid] = {
                    'status': status,
                    'last_activity': last_activity,
                    'inactive': inactive
                }
            
            # Show periodic status
            time.sleep(5)
            
            # Print current state every 30 seconds
            if int(time.time()) % 30 == 0:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📊 Current State:")
                print(f"   Total sessions: {current_count}")
                print(f"   Active: {sessions.count_documents({'status': 'active'})}")
                print(f"   Ended: {sessions.count_documents({'status': 'ended'})}")
                
                for sid, data in last_sessions.items():
                    if data['status'] == 'active':
                        print(f"   • {sid[:12]}... - inactive for {data['inactive']:.1f} min")
                
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped\n")

if __name__ == "__main__":
    monitor_sessions()
