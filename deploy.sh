#!/bin/bash

# VPS Deployment Script
# මේක VPS එකේ run කරන්න ඕනි

set -e  # Exit on error

echo "🚀 Deploying Telegram Media Transfer Service..."

# Variables
PROJECT_DIR="/root/telegram-transfer"

# Create directory if not exists
echo "📁 Creating project directory..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Check if Docker is installed
echo "🐳 Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Installing..."
    apt install docker-compose -y
fi

echo "✅ Docker and Docker Compose are installed"

# Create necessary directories
echo "📂 Creating directories..."
mkdir -p session_data
mkdir -p telegram_downloads

# Set permissions
chmod -R 755 session_data
chmod -R 755 telegram_downloads

# Build Docker image
echo "🔨 Building Docker image..."
docker-compose build

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Edit docker-compose.yml with your credentials:"
echo "   nano docker-compose.yml"
echo ""
echo "2. First time login (to verify channels):"
echo "   docker-compose run --rm telegram-transfer python find_channel_id.py"
echo ""
echo "3. Start the service:"
echo "   docker-compose up -d"
echo ""
echo "4. View logs:"
echo "   docker-compose logs -f"
echo ""
