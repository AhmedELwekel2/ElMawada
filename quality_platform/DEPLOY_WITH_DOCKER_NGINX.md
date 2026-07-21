# Deployment Guide for ibdl.thetransformix.com (Docker Nginx)

## Overview

Your VPS has an existing Docker Nginx container (`diomedia-nginx`) that serves other projects. This guide shows you how to add `ibdl.thetransformix.com` to it without disrupting existing services.

## Prerequisites

- VPS with `diomedia-nginx` container running
- Docker and Docker Compose installed
- Domain `ibdl.thetransformix.com` pointed to your VPS IP

## Architecture

```
Internet (443/80)
    ↓
diomedia-nginx (Docker)
    ├─ other domains
    └─ ibdl.thetransformix.com → host.docker.internal:9000 (frontend)
                                         ↓
                                  host.docker.internal:9005 (backend)
```

## Deployment Steps

### Step 1: Pull Latest Code

```bash
cd /root/IBDL_PLATFORM && git pull
```

### Step 2: Rebuild Frontend with New API URL

Important: Must rebuild to set `NEXT_PUBLIC_API_URL=https://ibdl.thetransformix.com`

```bash
cd /root/IBDL_PLATFORM
docker compose -f quality_platform/docker-compose.prod.yml build frontend
```

### Step 3: Restart Quality Platform Containers

```bash
cd /root/IBDL_PLATFORM
docker compose -f quality_platform/docker-compose.prod.yml down
docker compose -f quality_platform/docker-compose.prod.yml up -d
```

Verify containers are running:
```bash
docker ps | grep quality_platform
```

You should see:
- `quality_platform-backend-1` on port 9005
- `quality_platform-frontend-1` on port 9000

### Step 4: Add Server Block to Existing Nginx Config

Copy the server block content from `quality_platform/nginx/ibdl_server_block.conf`:

```bash
cat quality_platform/nginx/ibdl_server_block.conf
```

Then add it to your existing nginx config:
```bash
nano /root/diomedia-ai-assistant/nginx_vps.conf
```

Paste the server block at the bottom of the file, before the closing `}` if any.

Save and exit (Ctrl+X, then Y, then Enter).

### Step 5: Test Nginx Config

```bash
docker exec diomedia-nginx nginx -t
```

If you see `syntax is ok`, proceed. If not, fix the errors in the config file.

### Step 6: Reload Nginx

```bash
docker exec diomedia-nginx nginx -s reload
```

### Step 7: Get SSL Certificate with Let's Encrypt

Create a temporary container to run certbot:

```bash
mkdir -p /root/diomedia-ai-assistant/ssl/ibdl.thetransformix.com
docker run -it --rm \
  -v /root/diomedia-ai-assistant/ssl/ibdl.thetransformix.com:/etc/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly \
  --standalone \
  -d ibdl.thetransformix.com \
  --email YOUR_EMAIL@example.com \
  --agree-tos \
  --non-interactive
```

Replace `YOUR_EMAIL@example.com` with your actual email.

### Step 8: Enable SSL in Nginx Config

Edit the nginx config again:
```bash
nano /root/diomedia-ai-assistant/nginx_vps.conf
```

Uncomment the HTTPS server block and redirect section. The config should now have:
1. HTTPS server on port 443 (uncommented)
2. HTTP → HTTPS redirect (uncommented)
3. Comment out or remove the HTTP server block with `listen 80` that was for initial setup

Save and exit.

### Step 9: Reload Nginx Again

```bash
docker exec diomedia-nginx nginx -t
docker exec diomedia-nginx nginx -s reload
```

### Step 10: Verify Deployment

Visit `https://ibdl.thetransformix.com` in your browser.

Check Nginx logs if needed:
```bash
docker exec diomedia-nginx tail -f /var/log/nginx/error.log
```

## Troubleshooting

### Containers not accessible from nginx

Ensure ports are binding to `0.0.0.0`:
```bash
docker ps | grep quality_platform
```
Should show `0.0.0.0:9000->3000/tcp` and `0.0.0.0:9005->8000/tcp`

### SSL Certificate Issues

Check certificate files:
```bash
ls -la /root/diomedia-ai-assistant/ssl/ibdl.thetransformix.com/
```

Should contain:
- `fullchain.pem`
- `privkey.pem`

### Nginx Config Errors

Test config:
```bash
docker exec diomedia-nginx nginx -t
```

### Domain Not Resolving

Check DNS:
```bash
dig ibdl.thetransformix.com
```

Should point to your VPS IP.

### Check Container Health

```bash
docker logs quality_platform-backend-1
docker logs quality_platform-frontend-1
```

## SSL Certificate Auto-Renewal

Set up a cron job to renew certificates automatically:

```bash
crontab -e
```

Add this line (runs weekly):
```
0 3 * * 0 docker run --rm -v /root/diomedia-ai-assistant/ssl/ibdl.thetransformix.com:/etc/letsencrypt -p 80:80 certbot/certbot renew --quiet && docker exec diomedia-nginx nginx -s reload
```

## Summary

After completing these steps, your site will be accessible at:
- **HTTP**: `http://ibdl.thetransformix.com` (redirects to HTTPS)
- **HTTPS**: `https://ibdl.thetransformix.com`

The setup uses:
- **diomedia-nginx** container (ports 80/443) → reverse proxy
- **quality_platform-frontend** container (port 9000) → Next.js
- **quality_platform-backend** container (port 9005) → FastAPI
- **host.docker.internal** → allows nginx container to access host ports

Your existing projects on the same VPS are unaffected!