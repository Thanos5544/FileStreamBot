#!/bin/bash
echo "========================================="
echo "  Starting bgutil POT Token Server..."
echo "========================================="

cd /opt/bgutil/server

# Try different entry points
if [ -f "build/index.js" ]; then
    echo "Found build/index.js"
    node build/index.js &
elif [ -f "dist/index.js" ]; then
    echo "Found dist/index.js"
    node dist/index.js &
elif [ -f "src/index.ts" ]; then
    echo "Found src/index.ts, using ts-node"
    npx ts-node src/index.ts &
else
    echo "⚠️ No server entry point found!"
    ls -la
fi

SERVER_PID=$!
echo "POT Server PID: $SERVER_PID"

# Wait for server to start
sleep 5

# Check if server is running
if curl -s http://127.0.0.1:4416/ping > /dev/null 2>&1; then
    echo "✅ POT Server is RUNNING on port 4416!"
else
    echo "⚠️ POT Server might not be running, trying anyway..."
fi

echo "========================================="
echo "  Starting Bot..."
echo "========================================="

cd /app
python -m FileStream
