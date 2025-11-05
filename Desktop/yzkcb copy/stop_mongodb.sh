#!/bin/bash
# MongoDB Stop Script for macOS
# This script stops MongoDB gracefully

echo "🛑 Stopping MongoDB..."

# Check if MongoDB is running
if ! lsof -i :27017 >/dev/null 2>&1; then
    echo "ℹ️  MongoDB is not running"
    exit 0
fi

# Try graceful shutdown first
echo "Attempting graceful shutdown..."
mongosh --quiet --eval "use admin; db.shutdownServer(); quit()" 2>/dev/null

# Wait a moment
sleep 2

# Check if still running
if lsof -i :27017 >/dev/null 2>&1; then
    echo "⚠️  Graceful shutdown failed, forcing shutdown..."
    # Get the PID
    PID=$(lsof -ti :27017)
    if [ ! -z "$PID" ]; then
        kill -9 $PID
        echo "✅ MongoDB process killed (PID: $PID)"
    fi
else
    echo "✅ MongoDB stopped successfully!"
fi

# Final check
sleep 1
if lsof -i :27017 >/dev/null 2>&1; then
    echo "❌ Failed to stop MongoDB"
    echo "You may need to manually kill the process:"
    echo "  lsof -ti :27017 | xargs kill -9"
    exit 1
else
    echo "✅ Port 27017 is now free"
fi
