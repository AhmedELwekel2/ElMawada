#!/bin/bash
# ============================================================
# Nginx + SSL Setup Script for ibdl.thetransformix.com
# Run this on your VPS as root or with sudo
# ============================================================

set -e

DOMAIN="ibdl.thetransformix.com"
EMAIL=""  # <-- SET YOUR EMAIL for Let's Encrypt notifications

echo "============================================"
echo " Setting up Nginx for $DOMAIN"
echo "============================================"

# Step 1: Install Nginx
echo ""
echo "[1/5] Installing Nginx..."
apt-get update
apt-get install -y nginx

# Step 2: Create web root for Let's Encrypt challenges
mkdir -p /var/www/html

# Step 3: Copy Nginx config
echo "[2/5] Copying Nginx configuration..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/nginx/${DOMAIN}.conf" "/etc/nginx/sites-available/${DOMAIN}"

# Enable the site
ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"

# Remove default site if exists (optional - won't break other sites)
# rm -f /etc/nginx/sites-enabled/default

# Test config
echo "[3/5] Testing Nginx configuration..."
nginx -t

# Reload Nginx
echo "[4/5] Reloading Nginx..."
systemctl enable nginx
systemctl reload nginx

# Step 5: Install certbot and get SSL certificate
echo "[5/5] Setting up SSL with Let's Encrypt..."
if [ -z "$EMAIL" ]; then
    echo "WARNING: No email set. Edit this script and set EMAIL variable, then run:"
    echo "  certbot --nginx -d $DOMAIN"
    echo ""
    echo "Or run now with email:"
    read -p "Enter your email for SSL notifications: " EMAIL
fi

if [ -n "$EMAIL" ]; then
    apt-get install -y certbot python3-certbot-nginx
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "$EMAIL" --redirect
    
    # Certbot modifies the config to add SSL, verify it works
    echo ""
    echo "SSL Certificate installed successfully!"
    echo "Auto-renewal is configured by certbot timer."
fi

echo ""
echo "============================================"
echo " SETUP COMPLETE!"
echo "============================================"
echo ""
echo "Your site should now be accessible at:"
echo "  http://$DOMAIN  (redirects to HTTPS)"
echo "  https://$DOMAIN"
echo ""
echo "Nginx proxies:"
echo "  /api/*  → 127.0.0.1:9005 (Backend)"
echo "  /*      → 127.0.0.1:9000 (Frontend)"
echo ""
echo "To check Nginx status:  systemctl status nginx"
echo "To view logs:           tail -f /var/log/nginx/error.log"
echo "To reload after config: nginx -t && systemctl reload nginx"
echo ""