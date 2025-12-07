#!/bin/bash
echo "🐳 Building Docker Image..."
docker build -t healthcare-assistant-backend .

echo ""
echo "🏃 Running Docker Container (Port 8765)..."
echo "   (Press Ctrl+C to stop)"
docker run -p 8765:8765 --env-file .env healthcare-assistant-backend
