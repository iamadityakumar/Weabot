#!/usr/bin/env bash
# ==============================================================================
# Automated Production Deployment Script for Outdoor Activity Safety Advisor
# Oracle Cloud Infrastructure (OCI) Ubuntu 22.04 / 24.04 LTS
# ==============================================================================

set -euo pipefail

APP_DIR="/home/ubuntu/outdoor-safety-advisor"
WEB_DIR="/var/www/advisor"

echo "=== [1/6] Navigating to Application Directory ==="
cd "${APP_DIR}"

echo "=== [2/6] Syncing Python Virtual Environment Dependencies ==="
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [3/6] Building Production React Frontend ==="
cd frontend
npm ci || npm install
npm run build
cd ..

echo "=== [4/6] Syncing Static Assets to /var/www/advisor ==="
sudo mkdir -p "${WEB_DIR}/dist"
sudo rsync -av --delete frontend/dist/ "${WEB_DIR}/dist/"
sudo chown -R caddy:caddy "${WEB_DIR}" || sudo chown -R www-data:www-data "${WEB_DIR}"

echo "=== [5/6] Updating Systemd Backend Service ==="
sudo cp deployment/advisor-backend.service /etc/systemd/system/advisor-backend.service
sudo systemctl daemon-reload
sudo systemctl enable advisor-backend
sudo systemctl restart advisor-backend

echo "=== [6/6] Reloading Caddy Web Server ==="
if command -v caddy &> /dev/null; then
    sudo cp deployment/Caddyfile /etc/caddy/Caddyfile
    sudo systemctl reload caddy || sudo caddy reload --config /etc/caddy/Caddyfile
fi

echo "=== Deployment Complete! Verifying Backend Health ==="
sleep 2
curl -s http://127.0.0.1:8000/api/health | jq . || curl -s http://127.0.0.1:8000/api/health
echo ""
echo "Outdoor Activity Safety Advisor is online."
