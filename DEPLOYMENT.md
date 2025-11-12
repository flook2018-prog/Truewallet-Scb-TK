# TrueWallet-TK Railway Deployment Guide

## Fixed Issues

### 1. Health Check Endpoint
- Added `/health` endpoint that returns 200 status without requiring authentication
- Updated `railway.toml` to use `/health` instead of `/` for health checks
- Added `/health/db` for detailed database connection testing

### 2. Database Connection
- Improved PostgreSQL connection handling for Railway environment
- Added retry logic for database initialization
- Better error handling for connection timeouts
- Support for Railway's `DATABASE_URL` environment variable

### 3. Application Startup
- Added comprehensive logging during startup
- Better error handling and retry logic
- Graceful fallback if database initialization fails

## Deployment Steps

1. **Push to Git Repository**
   ```bash
   git add .
   git commit -m "Fix Railway deployment health check and database issues"
   git push origin main
   ```

2. **Railway Configuration**
   - The app will automatically use Nixpacks as the builder
   - Health check endpoint: `/health`
   - Health check timeout: 300 seconds
   - Port: Uses `PORT` environment variable (automatically set by Railway)

3. **Environment Variables**
   - `RAILWAY_ENVIRONMENT` - Automatically set by Railway
   - `DATABASE_URL` - Automatically set if PostgreSQL database is connected
   - `PORT` - Automatically set by Railway

## Health Check Endpoints

- `GET /health` - Simple health check (no database test)
- `GET /health/db` - Health check with database connection test

## Troubleshooting

### If health check still fails:
1. Check Railway logs for startup errors
2. Test the health endpoint manually: `https://your-app.railway.app/health`
3. Check database connectivity: `https://your-app.railway.app/health/db`

### Common issues:
- **Database connection timeout**: Increase health check timeout in Railway
- **Port binding**: Ensure app uses `PORT` environment variable
- **Build failures**: Check that all dependencies in requirements.txt are correct

## Features Included

- TrueWallet transaction management
- SCB SMS monitoring
- Kbiz withdrawal notifications
- Notes system with PostgreSQL
- Real-time gold price scraping from Thai website
- File upload functionality
- User authentication system

## API Endpoints

- `/` - Main dashboard (requires login)
- `/login` - User authentication
- `/health` - Health check endpoint
- `/api/gold-price` - Gold price data
- `/api/sms` - SMS data management
- `/api/notes` - Notes CRUD operations
- `/webhook` - TrueWallet webhook endpoint
- `/api/kbiz_notifications` - Kbiz notifications

## Database

- **Production**: PostgreSQL (Railway)
- **Development**: SQLite
- Auto-migration on startup
- Retry logic for connection issues