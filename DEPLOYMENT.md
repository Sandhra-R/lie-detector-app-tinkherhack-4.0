# Deployment Guide - Render

This application is configured to deploy to [Render](https://render.com), a modern platform-as-a-service that's an excellent alternative to Heroku.

## Prerequisites

1. **GitHub Account** - Render deploys directly from GitHub repositories
2. **Render Account** - Sign up at https://render.com
3. **Git** - Version control to push your code to GitHub

## Step-by-Step Deployment

### 1. Push to GitHub

First, make sure your code is in a GitHub repository:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

If you don't have a GitHub repo yet:
- Create a new repository on https://github.com/new
- Follow GitHub's instructions to push your local code

### 2. Sign Up / Log In to Render

1. Go to https://render.com
2. Click "Sign up" and create an account (or log in)
3. Connect your GitHub account when prompted

### 3. Create a New Service

1. Click the **"New+"** button in the top right
2. Select **"Web Service"**
3. Select your lie-detector-app repository
4. Fill in the configuration:
   - **Name**: `lie-detector-app` (or your preferred name)
   - **Environment**: `Python 3`
   - **Region**: Choose the closest to your users (e.g., `USA, Ohio`)
   - **Branch**: `main` (or your main branch)
   - **Build Command**: `cd lie-detector-app/Backend && pip install -r requirements.txt`
   - **Start Command**: `cd lie-detector-app/Backend && gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`
   - **Plan**: Select `Free` for testing, or `Starter` for production ($7/month)

### 4. Configure Environment Variables (Optional)

1. Scroll down to **"Environment"**
2. Click **"Add Environment Variable"** if you need any
3. For now, you can leave this empty as the app has sensible defaults

### 5. Deploy

1. Click **"Create Web Service"**
2. Render will automatically start building and deploying your app
3. Wait for the build to complete (check the logs for any errors)
4. Once deployed, you'll get a URL like: `https://lie-detector-app.onrender.com`

## Important Notes

### WebSocket Support
- Render supports WebSocket connections automatically
- The app is configured with `eventlet` async mode for proper SocketIO functionality

### Dependencies
- MediaPipe and OpenCV are heavy dependencies but included
- Initial builds may take 2-3 minutes
- Free plans on Render may have memory constraints; consider upgrading if needed

### API Endpoints

Once deployed, your app will be available at your Render URL:

- **Frontend**: `https://your-app-name.onrender.com/`
- **API**: `https://your-app-name.onrender.com/api/*`
- **WebSocket**: Automatically upgrades HTTP connections for SocketIO

### Troubleshooting

1. **Build Fails**: Check the build logs in Render dashboard for errors
2. **App Crashes**: View runtime logs in the dashboard
3. **MediaPipe Issues**: The app gracefully falls back to demo mode if unavailable
4. **Memory Issues**: Free tier has 512MB RAM; upgrade to Starter plan if needed

## Updating Your Deployment

After making changes to your code:

```bash
git add .
git commit -m "Update features"
git push origin main
```

Render will automatically redeploy your app when you push to GitHub (if you've enabled auto-deploy).

## Next Steps

- Visit your deployed app URL
- Test the lie detector functionality
- Share the link with others
- Monitor the logs in Render dashboard for any issues

For more help: https://render.com/docs
