#!/bin/bash
# =============================================================================
# Quality Platform VPS Deployment Script
# Run this on the VPS after uploading files via SCP
# =============================================================================

set -e

echo "============================================"
echo "  Quality Platform - VPS Deployment"
echo "============================================"

# 1. Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo ">> Installing Docker..."
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker $USER
    echo ">> Docker installed. You may need to re-login for group changes."
fi

# 2. Install Docker Compose plugin if not present
if ! docker compose version &> /dev/null; then
    echo ">> Installing Docker Compose plugin..."
    sudo apt-get install -y docker-compose-plugin
fi

echo ">> Docker version: $(docker --version)"
echo ">> Docker Compose version: $(docker compose version)"

# 3. Navigate to project directory
cd ~/quality-platform/quality_platform

# 4. Build and start containers using production compose file
echo ">> Building and starting containers..."
docker compose -f docker-compose.prod.yml up --build -d

# 5. Check status
echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "  Frontend: http://72.146.232.56:9000"
echo "  Backend:  http://72.146.232.56:9005"
echo ""
docker compose -f docker-compose.prod.yml ps
