# Pairs Trading Bot - Streamlit Dashboard

A comprehensive Streamlit dashboard for managing and monitoring a pairs trading bot that trades ETH/USDT vs SOL/USDT on Binance Testnet.

## Features

- **Start/Stop Bot Controls**: Easy-to-use buttons to start and stop the trading bot
- **Real-time Market Data**: Live display of ETH/USDT and SOL/USDT prices, spread, and Z-score
- **Position Monitoring**: Shows current position status and trading activity
- **Trade Log**: Comprehensive logging of all trades with detailed information
- **Configuration Display**: Shows all trading parameters and settings
- **Raw Bot Log**: Real-time access to detailed bot logs for debugging

## Files Structure

```
├── main.py              # Main Streamlit application
├── bot.py               # Trading bot logic and classes
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── trade_logs.json     # Trade log file (created automatically)
└── trading_bot.log     # Bot log file (created automatically)
```

## Installation and Setup

### Prerequisites

- Python 3.8 or higher
- Binance Testnet account with API keys
- Internet connection for market data

### Local Installation

1. **Clone or download the files** to your local machine

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Keys**:
   - Open `bot.py`
   - Replace the API_KEY and API_SECRET with your Binance Testnet credentials:
   ```python
   API_KEY = "your_binance_testnet_api_key"
   API_SECRET = "your_binance_testnet_api_secret"
   ```

4. **Run the application**:
   ```bash
   streamlit run main.py
   ```

5. **Access the dashboard**:
   - Open your browser and go to `http://localhost:8501`
   - The dashboard will load with all controls and monitoring features

## Streamlit Cloud Deployment

### Option 1: Streamlit Community Cloud (Recommended)

1. **Prepare your repository**:
   - Create a GitHub repository
   - Upload all files (`main.py`, `bot.py`, `requirements.txt`)
   - **Important**: Remove or replace API keys with environment variables

2. **Set up environment variables**:
   - Modify `bot.py` to use environment variables:
   ```python
   import os
   API_KEY = os.getenv("BINANCE_API_KEY", "your_default_key")
   API_SECRET = os.getenv("BINANCE_API_SECRET", "your_default_secret")
   ```

3. **Deploy to Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository and `main.py`
   - Add environment variables in the "Advanced settings":
     - `BINANCE_API_KEY`: Your Binance Testnet API key
     - `BINANCE_API_SECRET`: Your Binance Testnet API secret
   - Click "Deploy"

4. **Access your deployed app**:
   - Streamlit will provide a public URL
   - The app will be available 24/7

### Option 2: Other Cloud Platforms

#### Heroku
1. Create a `Procfile`:
   ```
   web: streamlit run main.py --server.port=$PORT --server.address=0.0.0.0
   ```
2. Deploy using Heroku CLI or GitHub integration

#### Railway
1. Connect your GitHub repository
2. Set environment variables in Railway dashboard
3. Deploy automatically

#### DigitalOcean App Platform
1. Create a new app from GitHub
2. Configure environment variables
3. Deploy with automatic scaling

## Trading Configuration

The bot uses the following default parameters (configurable in `bot.py`):

- **USDT_AMOUNT_PER_LEG**: 4000 USDT per trade leg
- **ENTRY_ZSCORE**: 1.5 (entry threshold)
- **EXIT_ZSCORE**: 0.5 (exit threshold)
- **STOP_LOSS_ZSCORE**: 3.0 (stop loss threshold)
- **MAX_HOLD_PERIOD**: 48 bars (maximum holding time)
- **PARTIAL_EXIT_PCT**: 50% (partial exit percentage)
- **ROLLING_WINDOW**: 48 bars (for statistical calculations)

## Usage Instructions

### Starting the Bot

1. Open the Streamlit dashboard
2. Check that the bot status shows "🔴 Stopped"
3. Click the "🚀 Start Bot" button in the sidebar
4. The status will change to "🟢 Running"
5. Market data will begin updating every minute

### Monitoring Trading Activity

- **Market Data**: Real-time prices, spread, and Z-score
- **Position Status**: Shows if the bot is currently in a position
- **Trade Log**: Detailed history of all trades with PnL information
- **Raw Bot Log**: Technical logs for debugging and monitoring

### Stopping the Bot

1. Click the "⏹️ Stop Bot" button in the sidebar
2. The bot will stop after completing any current operations
3. Status will change to "🔴 Stopped"

## Security Considerations

### API Key Security

- **Never commit API keys to public repositories**
- Use environment variables for production deployments
- Consider using Binance Testnet for development and testing
- Regularly rotate API keys

### Recommended Security Practices

1. **Use Testnet**: Start with Binance Testnet for testing
2. **Environment Variables**: Store sensitive data in environment variables
3. **IP Restrictions**: Configure API key IP restrictions in Binance
4. **Limited Permissions**: Only enable necessary API permissions
5. **Regular Monitoring**: Monitor bot activity and logs regularly

## Troubleshooting

### Common Issues

1. **Bot won't start**:
   - Check API key configuration
   - Verify internet connection
   - Check Binance API status

2. **No market data**:
   - Verify API keys are correct
   - Check if Binance Testnet is accessible
   - Review bot logs for error messages

3. **Streamlit app crashes**:
   - Check Python version compatibility
   - Verify all dependencies are installed
   - Review error messages in terminal

### Log Files

- **trading_bot.log**: Contains detailed bot operation logs
- **trade_logs.json**: Contains structured trade data
- Check these files for debugging information

## Support and Maintenance

### Regular Maintenance

1. **Monitor Performance**: Check trade logs and PnL regularly
2. **Update Dependencies**: Keep packages updated for security
3. **Backup Data**: Regularly backup trade logs and configuration
4. **Review Parameters**: Adjust trading parameters based on performance

### Getting Help

- Check the raw bot logs in the dashboard for error messages
- Review Binance API documentation for API-related issues
- Monitor Streamlit community forums for deployment issues

## Disclaimer

This trading bot is for educational and testing purposes. Always:
- Test thoroughly on Binance Testnet before using real funds
- Understand the risks involved in automated trading
- Monitor the bot's performance regularly
- Never invest more than you can afford to lose

## License

This project is provided as-is for educational purposes. Use at your own risk.

