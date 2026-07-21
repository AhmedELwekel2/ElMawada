# Fix for /api/api/ URL Duplication Issue

## Problem
The frontend was making requests to `https://ibdl.thetransformix.com/api/api/auth/login` instead of `https://ibdl.thetransformix.com/api/auth/login`, resulting in 404 errors.

## Root Cause
In `docker-compose.prod.yml`, the `NEXT_PUBLIC_API_URL` build argument had a trailing slash:
```yaml
NEXT_PUBLIC_API_URL=https://ibdl.thetransformix.com/
```

When the frontend code appends `/api/auth/login` to this URL, it creates:
```
https://ibdl.thetransformix.com//api/auth/login
```

Browsers normalize double slashes to single slashes, resulting in the duplicated `/api/api/` path.

## Solution
Removed the trailing slash from the `NEXT_PUBLIC_API_URL` in all configuration files:

### 1. docker-compose.prod.yml
```yaml
args:
  - NEXT_PUBLIC_API_URL=https://ibdl.thetransformix.com
```

### 2. .env.example
```env
NEXT_PUBLIC_API_URL=https://ibdl.thetransformix.com
```

## Deployment Instructions

### Step 1: Pull the latest code
```bash
cd /path/to/quality_platform
git pull
```

### Step 2: Rebuild and restart containers
```bash
cd quality_platform
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache frontend
docker-compose -f docker-compose.prod.yml up -d
```

**Important**: You must rebuild the frontend container because `NEXT_PUBLIC_API_URL` is a build-time environment variable. Changes to it require rebuilding the Docker image.

### Step 3: Verify the fix
1. Open browser DevTools (F12)
2. Go to Network tab
3. Try to log in
4. Check that requests now go to:
   ```
   https://ibdl.thetransformix.com/api/auth/login
   ```
   NOT:
   ```
   https://ibdl.thetransformix.com/api/api/auth/login
   ```

## Notes
- Backend and nginx configuration were already correct
- Only the frontend build argument needed to be fixed
- The fix is backward compatible with all existing API endpoints