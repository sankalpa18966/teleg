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
else
    echo "✅ Docker already installed"
fi

# Check Docker Compose (v2 or v1)
COMPOSE_CMD=""
if docker compose version &> /dev/null; then
    echo "✅ Docker Compose V2 detected"
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose V1 detected"
    COMPOSE_CMD="docker-compose"
else
    echo "📦 Docker Compose not found. Installing Docker Compose V2..."
    # Docker Compose V2 comes with Docker by default in newer versions
    # If not available, install it as a plugin
    mkdir -p ~/.docker/cli-plugins/
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
    chmod +x ~/.docker/cli-plugins/docker-compose
    COMPOSE_CMD="docker compose"
    echo "✅ Docker Compose V2 installed"
fi

echo "✅ Docker ready! Using: $COMPOSE_CMD"

# Create necessary directories
mkdir -p session_data
mkdir -p telegram_downloads
chmod -R 755 session_data telegram_downloads

# Build and start container
echo "🔨 Building Docker image and starting service..."
$COMPOSE_CMD down 2>/dev/null || true
$COMPOSE_CMD up -d --build

echo ""
echo "=================================================="
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "=================================================="
echo "🌐 Open your browser and navigate to:"
echo "   http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "📌 Useful Commands:"
echo "   - View Logs:    $COMPOSE_CMD logs -f"
echo "   - Restart App:  $COMPOSE_CMD restart"
echo "   - Stop App:     $COMPOSE_CMD down"
echo "   - Disk Space:   df -h"
echo "=================================================="
