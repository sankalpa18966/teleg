#!/bin/bash

# Telegram Media Hub - Direct VPS Setup (Without Docker)
# Python environment සමඟ directly run කරන්න

set -e

echo "=================================================="
echo "🚀 Setting up Telegram Media Hub (Direct Python)"
echo "=================================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "📦 Installing Python..."
    apt-get update
    apt-get install -y python3 python3-pip python3-venv
else
    echo "✅ Python3 already installed"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p session_data telegram_downloads
chmod -R 755 session_data telegram_downloads

echo ""
echo "=================================================="
echo "✅ Setup Complete!"
echo "=================================================="
echo ""
echo "🚀 To start the app:"
echo "   ./start-app.sh"
echo ""
echo "📌 Useful Commands:"
echo "   - Start:  ./start-app.sh"
echo "   - Stop:   ./stop-app.sh"
echo "   - Logs:   ./view-logs.sh"
echo "=================================================="
