#!/bin/bash

# Quick VPS Deployment Helper Script
# This script detects and uses the correct Docker Compose command

set -e

echo "🔍 Detecting Docker Compose..."

# Detect which Docker Compose command to use
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
    echo "✅ Using: docker compose (V2)"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
    echo "✅ Using: docker-compose (V1)"
else
    echo "❌ Docker Compose not found!"
    echo ""
    echo "Installing Docker Compose V2..."
    mkdir -p ~/.docker/cli-plugins/
    curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o ~/.docker/cli-plugins/docker-compose
    chmod +x ~/.docker/cli-plugins/docker-compose
    COMPOSE="docker compose"
    echo "✅ Docker Compose V2 installed"
fi

# Show command
echo ""
echo "=================================================="
echo "🚀 Quick Deploy Actions"
echo "=================================================="
echo ""
echo "Choose an action:"
echo "  1) Start/Deploy App"
echo "  2) View Logs"
echo "  3) Restart App"
echo "  4) Stop App"
echo "  5) Clean & Fresh Start"
echo "  6) Check Disk Space"
echo "  0) Exit"
echo ""
read -p "Enter choice [0-6]: " choice

case $choice in
    1)
        echo "🚀 Starting/Deploying..."
        mkdir -p session_data telegram_downloads
        chmod -R 755 session_data telegram_downloads
        $COMPOSE down 2>/dev/null || true
        $COMPOSE up -d --build
        echo ""
        echo "✅ App started!"
        echo "🌐 Access: http://$(hostname -I | awk '{print $1}'):3000"
        ;;
    2)
        echo "📋 Showing logs (Press Ctrl+C to exit)..."
        $COMPOSE logs -f
        ;;
    3)
        echo "🔄 Restarting..."
        $COMPOSE restart
        echo "✅ App restarted!"
        ;;
    4)
        echo "🛑 Stopping..."
        $COMPOSE down
        echo "✅ App stopped!"
        ;;
    5)
        echo "🧹 Cleaning everything..."
        $COMPOSE down
        rm -rf session_data/* telegram_downloads/*
        $COMPOSE up -d --build
        echo "✅ Fresh start complete!"
        echo "🌐 Access: http://$(hostname -I | awk '{print $1}'):3000"
        ;;
    6)
        echo "💾 Disk Space:"
        df -h
        echo ""
        echo "📁 Download folder size:"
        du -sh telegram_downloads/ 2>/dev/null || echo "0 (folder empty or not found)"
        ;;
    0)
        echo "👋 Bye!"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=================================================="
echo "💡 Tip: Run this script anytime with: ./quick-deploy.sh"
echo "=================================================="
