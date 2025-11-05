#!/bin/bash
# MongoDB Startup Script for macOS
# This script starts MongoDB manually (not as a service)

echo "🚀 Starting MongoDB..."

# Detect architecture and set paths
if [[ $(uname -m) == 'arm64' ]]; then
    # Apple Silicon (M1/M2/M3)
    MONGODB_DATA="/opt/homebrew/var/mongodb"
    MONGODB_LOG="/opt/homebrew/var/log/mongodb"
else
    # Intel Mac
    MONGODB_DATA="/usr/local/var/mongodb"
    MONGODB_LOG="/usr/local/var/log/mongodb"
fi

# Create directories if they don't exist
mkdir -p "$MONGODB_DATA"
mkdir -p "$MONGODB_LOG"

# Check if MongoDB is already running
if lsof -i :27017 >/dev/null 2>&1; then
    echo "⚠️  MongoDB is already running on port 27017"
    echo "To stop it, run: ./stop_mongodb.sh"
    exit 1
fi

# Start MongoDB
echo "📂 Data directory: $MONGODB_DATA"
echo "📝 Log directory: $MONGODB_LOG"

# macOS doesn't support --fork, so we'll run in background
nohup mongod --dbpath "$MONGODB_DATA" --logpath "$MONGODB_LOG/mongo.log" > /dev/null 2>&1 &

# Check if started successfully
sleep 2
if lsof -i :27017 >/dev/null 2>&1; then
    echo "✅ MongoDB started successfully!"
    echo "📊 Connection: mongodb://localhost:27017"
    echo ""
    echo "Test connection: mongosh"
    echo "Stop MongoDB: ./stop_mongodb.sh"
    echo ""
    echo "⚠️  Note: MongoDB is running in the background"
    echo "   View logs: tail -f $MONGODB_LOG/mongo.log"
else
    echo "❌ MongoDB failed to start"
    echo "Check logs: cat $MONGODB_LOG/mongo.log"
    exit 1
fi
