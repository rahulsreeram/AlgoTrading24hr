# Streamlit Cloud Deployment Guide

## Quick Deployment Steps

### 1. Prepare Your Code

First, update your `bot.py` file to use environment variables for API keys:

```python
import os

# Replace the hardcoded API keys with environment variables
API_KEY = os.getenv("BINANCE_API_KEY", "your_default_key_here")
API_SECRET = os.getenv("BINANCE_API_SECRET", "your_default_secret_here")
```

### 2. Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and create a new repository
2. Upload these files to your repository:
   - `main.py`
   - `bot.py` (with environment variables)
   - `requirements.txt`
   - `README.md`

### 3. Deploy to Streamlit Cloud

1. **Visit Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

2. **Create New App**:
   - Click "New app"
   - Select your GitHub repository
   - Choose `main.py` as the main file
   - Click "Advanced settings"

3. **Configure Environment Variables**:
   Add these environment variables:
   ```
   BINANCE_API_KEY = your_binance_testnet_api_key
   BINANCE_API_SECRET = your_binance_testnet_api_secret
   ```

4. **Deploy**:
   - Click "Deploy!"
   - Wait for the deployment to complete
   - Your app will be available at a public URL

### 4. Access Your Deployed Bot

- Streamlit will provide a public URL (e.g., `https://your-app-name.streamlit.app`)
- The bot will be accessible 24/7
- You can start/stop the bot from anywhere with internet access

## Alternative Deployment Options

### Heroku Deployment

1. **Create Procfile**:
   ```
   web: streamlit run main.py --server.port=$PORT --server.address=0.0.0.0
   ```

2. **Deploy**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   heroku create your-app-name
   heroku config:set BINANCE_API_KEY=your_key
   heroku config:set BINANCE_API_SECRET=your_secret
   git push heroku main
   ```

### Railway Deployment

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically

## Security Best Practices

1. **Never commit API keys to GitHub**
2. **Use Binance Testnet for testing**
3. **Set up IP restrictions on your API keys**
4. **Monitor your bot regularly**
5. **Use minimal API permissions**

## Monitoring Your Deployed Bot

- Access the dashboard via the public URL
- Monitor trade logs and bot status
- Check raw logs for any issues
- Set up alerts for important events

Your bot will now be running 24/7 in the cloud!

