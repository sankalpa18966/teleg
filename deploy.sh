#!/bin/bash

# Telegram Media Toolkit & Transfer Hub — VPS One-Click Deployment Script
set -e

echo "=================================================="
echo "🚀 Deploying Telegram Media Hub Web App..."
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    echo "📦 Docker Compose not found. Installing..."
    apt-get update && apt-get install -y docker-compose
fi

echo "✅ Docker and Docker Compose ready!"

# Create necessary directories
mkdir -p session_data
mkdir -p telegram_downloads
chmod -R 755 session_data telegram_downloads

# Build and start container
echo "🔨 Building Docker image and starting service..."
docker-compose down || true
docker-compose up -d --build

echo ""
echo "=================================================="
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "=================================================="
echo "🌐 Open your browser and navigate to:"
echo "   http://YOUR_VPS_IP:3000"
echo ""
echo "📌 Useful Commands:"
echo "   - View Logs:    docker-compose logs -f"
echo "   - Restart App:  docker-compose restart"
echo "   - Stop App:     docker-compose down"
echo "=================================================="
