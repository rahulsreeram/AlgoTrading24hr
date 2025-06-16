import streamlit as st
import pandas as pd
import numpy as np
import threading
import time
import logging
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from bot import PairsTradingBot

# Configure page
st.set_page_config(
    page_title="Pairs Trading Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

# Initialize session state variables
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'bot_thread' not in st.session_state:
    st.session_state.bot_thread = None
if 'bot_instance' not in st.session_state:
    st.session_state.bot_instance = None
if 'current_data' not in st.session_state:
    st.session_state.current_data = {}
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'api_secret' not in st.session_state:
    st.session_state.api_secret = ""

# Initialize trading parameters with defaults
if 'trading_params' not in st.session_state:
    st.session_state.trading_params = {
        "USDT_AMOUNT_PER_LEG": 4000.0,
        "ENTRY_ZSCORE": 1.5,
        "EXIT_ZSCORE": 0.5,
        "STOP_LOSS_ZSCORE_THRESHOLD": 3.0,
        "MAX_HOLD_PERIOD_BARS": 48,
        "PARTIAL_EXIT_PCT": 0.5,
        "ROLLING_WINDOW": 48
    }

def validate_parameters():
    """Validate trading parameters for logical consistency"""
    params = st.session_state.trading_params
    
    if params["EXIT_ZSCORE"] >= params["ENTRY_ZSCORE"]:
        st.error("⚠️ Exit Z-Score should be less than Entry Z-Score")
        return False
    
    if params["STOP_LOSS_ZSCORE_THRESHOLD"] <= params["ENTRY_ZSCORE"]:
        st.error("⚠️ Stop Loss Z-Score should be greater than Entry Z-Score")
        return False
    
    return True

def run_bot():
    """Run the trading bot in a background thread"""
    # Check if required session state variables exist
    if 'api_key' not in st.session_state or 'api_secret' not in st.session_state:
        logging.error("API credentials not found in session state")
        st.session_state.bot_running = False
        return
    
    # Check if API credentials are provided
    if not st.session_state.api_key or not st.session_state.api_secret:
        logging.error("API credentials are empty")
        st.session_state.bot_running = False
        return
    
    try:
        bot = PairsTradingBot(
            api_key=st.session_state.api_key,
            api_secret=st.session_state.api_secret,
            usdt_amount_per_leg=st.session_state.trading_params["USDT_AMOUNT_PER_LEG"],
            rolling_window=st.session_state.trading_params["ROLLING_WINDOW"],
            entry_zscore=st.session_state.trading_params["ENTRY_ZSCORE"],
            exit_zscore=st.session_state.trading_params["EXIT_ZSCORE"],
            stop_loss_zscore_threshold=st.session_state.trading_params["STOP_LOSS_ZSCORE_THRESHOLD"],
            partial_exit_pct=st.session_state.trading_params["PARTIAL_EXIT_PCT"],
            max_hold_period_bars=st.session_state.trading_params["MAX_HOLD_PERIOD_BARS"]
        )
        
        st.session_state.bot_instance = bot
        logging.info("Bot started from Streamlit")
        
        while st.session_state.bot_running:
            try:
                current_data = bot.run_single_iteration()
                if current_data is not None:
                    st.session_state.current_data = current_data.to_dict()
                time.sleep(60)  # Wait 1 minute between iterations
            except Exception as e:
                logging.error(f"Error in bot iteration: {e}")
                time.sleep(60)
        
        logging.info("Bot stopped from Streamlit")
        
    except Exception as e:
        logging.error(f"Error starting bot: {e}")
        st.session_state.bot_running = False

def stop_bot():
    """Stop the trading bot"""
    st.session_state.bot_running = False
    if st.session_state.bot_thread and st.session_state.bot_thread.is_alive():
        st.session_state.bot_thread.join(timeout=5)
    st.session_state.bot_instance = None

# Sidebar - API Configuration
st.sidebar.header("🔑 API Configuration")
st.session_state.api_key = st.sidebar.text_input(
    "Binance API Key",
    value=st.session_state.api_key,
    type="password",
    help="Enter your Binance API key"
)

st.session_state.api_secret = st.sidebar.text_input(
    "Binance API Secret",
    value=st.session_state.api_secret,
    type="password",
    help="Enter your Binance API secret"
)

# Sidebar - Trading Parameters
st.sidebar.header("🔧 Trading Parameters")

st.session_state.trading_params["USDT_AMOUNT_PER_LEG"] = st.sidebar.number_input(
    "USDT Amount Per Leg",
    min_value=100.0,
    max_value=50000.0,
    value=st.session_state.trading_params["USDT_AMOUNT_PER_LEG"],
    step=100.0,
    help="Amount of USDT to use for each leg of the pairs trade"
)

st.session_state.trading_params["ENTRY_ZSCORE"] = st.sidebar.number_input(
    "Entry Z-Score Threshold",
    min_value=0.5,
    max_value=5.0,
    value=st.session_state.trading_params["ENTRY_ZSCORE"],
    step=0.1,
    help="Z-score threshold to trigger trade entry"
)

st.session_state.trading_params["EXIT_ZSCORE"] = st.sidebar.number_input(
    "Exit Z-Score Threshold",
    min_value=0.1,
    max_value=2.0,
    value=st.session_state.trading_params["EXIT_ZSCORE"],
    step=0.1,
    help="Z-score threshold to trigger trade exit"
)

st.session_state.trading_params["STOP_LOSS_ZSCORE_THRESHOLD"] = st.sidebar.number_input(
    "Stop Loss Z-Score Threshold",
    min_value=2.0,
    max_value=10.0,
    value=st.session_state.trading_params["STOP_LOSS_ZSCORE_THRESHOLD"],
    step=0.1,
    help="Z-score threshold to trigger stop loss"
)

st.session_state.trading_params["MAX_HOLD_PERIOD_BARS"] = st.sidebar.number_input(
    "Max Hold Period (Bars)",
    min_value=1,
    max_value=200,
    value=st.session_state.trading_params["MAX_HOLD_PERIOD_BARS"],
    step=1,
    help="Maximum number of bars to hold a position"
)

st.session_state.trading_params["PARTIAL_EXIT_PCT"] = st.sidebar.slider(
    "Partial Exit Percentage",
    min_value=0.1,
    max_value=1.0,
    value=st.session_state.trading_params["PARTIAL_EXIT_PCT"],
    step=0.05,
    help="Percentage of position to exit on partial exit signal"
)

st.session_state.trading_params["ROLLING_WINDOW"] = st.sidebar.number_input(
    "Rolling Window",
    min_value=10,
    max_value=200,
    value=st.session_state.trading_params["ROLLING_WINDOW"],
    step=1,
    help="Rolling window size for calculations"
)

# Reset button
if st.sidebar.button("🔄 Reset to Defaults"):
    st.session_state.trading_params = {
        "USDT_AMOUNT_PER_LEG": 4000.0,
        "ENTRY_ZSCORE": 1.5,
        "EXIT_ZSCORE": 0.5,
        "STOP_LOSS_ZSCORE_THRESHOLD": 3.0,
        "MAX_HOLD_PERIOD_BARS": 48,
        "PARTIAL_EXIT_PCT": 0.5,
        "ROLLING_WINDOW": 48
    }
    st.rerun()

# Display current parameters
st.sidebar.markdown("### Current Parameters")
for key, value in st.session_state.trading_params.items():
    st.sidebar.text(f"{key}: {value}")

# Main interface
st.title("📈 Pairs Trading Bot")
st.markdown("Automated ETH/SOL pairs trading bot with real-time monitoring")

# Bot control buttons
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("🚀 Start Bot", disabled=st.session_state.bot_running, use_container_width=True):
        if not st.session_state.api_key or not st.session_state.api_secret:
            st.error("Please enter your API credentials before starting the bot!")
        elif not validate_parameters():
            st.error("Please fix parameter validation errors before starting the bot.")
        else:
            st.session_state.bot_running = True
            st.session_state.bot_thread = threading.Thread(target=run_bot, daemon=True)
            st.session_state.bot_thread.start()
            st.success("Bot started!")
            st.rerun()

with col2:
    if st.button("🛑 Stop Bot", disabled=not st.session_state.bot_running, use_container_width=True):
        stop_bot()
        st.success("Bot stopped!")
        st.rerun()

with col3:
    status = "🟢 Running" if st.session_state.bot_running else "🔴 Stopped"
    st.markdown(f"**Status:** {status}")

# Display current data if available
if st.session_state.current_data:
    st.header("📊 Current Market Data")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("ETH Price", f"${st.session_state.current_data.get('eth_price', 0):.2f}")
    
    with col2:
        st.metric("SOL Price", f"${st.session_state.current_data.get('sol_price', 0):.2f}")
    
    with col3:
        st.metric("Spread", f"{st.session_state.current_data.get('spread', 0):.4f}")
    
    with col4:
        zscore = st.session_state.current_data.get('spread_zscore', 0)
        st.metric("Z-Score", f"{zscore:.2f}")

# Position information
if st.session_state.bot_instance:
    st.header("💼 Current Positions")
    
    try:
        # Get position info from bot instance
        positions = st.session_state.bot_instance.get_positions()
        if positions:
            df_positions = pd.DataFrame(positions)
            st.dataframe(df_positions, use_container_width=True)
        else:
            st.info("No active positions")
    except:
        st.info("Position data not available")

# Trading history
st.header("📈 Trading Performance")

# Placeholder for performance metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Trades", "0")

with col2:
    st.metric("Win Rate", "0%")

with col3:
    st.metric("Total PnL", "$0.00")

with col4:
    st.metric("Today's PnL", "$0.00")

# Auto-refresh
if st.session_state.bot_running:
    time.sleep(5)
    st.rerun()
