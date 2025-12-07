#!/bin/bash
echo "🚀 Starting HealthCare Plus Environment..."

# 1. Check if virtualenv is active, if not, activate it
if [[ "$VIRTUAL_ENV" == "" ]]; then
    if [ -d "venv" ]; then
        echo "📦 Activating virtual environment..."
        source venv/bin/activate
    else
        echo "⚠️  No 'venv' found. Please run 'python3 -m venv venv' and install requirements first."
        exit 1
    fi
fi

# 2. Start Backend in Background
echo "🧠 Starting Backend Server (main.py)..."
python main.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"

# 3. Start Frontend Server
echo "🎨 Starting Frontend Server (port 8000)..."
echo "   Opening browser to http://localhost:8000"
sleep 2
open http://localhost:8000

python -m http.server 8000 --directory client

# Cleanup on exit
kill $BACKEND_PID
