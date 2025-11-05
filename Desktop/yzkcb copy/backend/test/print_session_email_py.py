"""Print the HTML email that the Python SessionManager would send for a session.
This doesn't send email. It creates a transient session in the 'sessions' collection, builds the HTML via the manager, prints it, and cleans up.
Usage: python3 backend/test/print_session_email_py.py
"""
import os
from backend.src.session.session_manager import get_session_manager
from datetime import datetime

# Ensure we read .env if present
from dotenv import load_dotenv
load_dotenv()

# Get manager
mgr = get_session_manager(os.getenv('MONGODB_URI'), os.getenv('MONGODB_DB'))

# Create test session data
session_id = f"py-verify-{int(datetime.now().timestamp())}"
user_info = {
    "full_name": "Py Verify",
    "email": "py.verify@example.com",
    "company_name": "PyVerifyCo",
    "supplier_type": "New Supplier",
    # enhanced_gradio stores flat keys; manager will handle either shape
    "city": "Lisbon",
    "country": "Portugal"
}

# Create session
created = mgr.create_session(session_id, user_info)
print('Session created:', created)

# Retrieve the session document
session = mgr.sessions_collection.find_one({"session_id": session_id})

# Build HTML
html = mgr._build_email_html(session, [])

print('\n--- GENERATED EMAIL HTML ---\n')
print(html[:3000])
print('\n(HTML truncated)')

# Cleanup
mgr.sessions_collection.delete_one({"session_id": session_id})
print('Cleaned up session')
