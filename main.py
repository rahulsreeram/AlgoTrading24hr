import streamlit as st
import time
import json
import pandas as pd
import threading
import os
import logging
from datetime import datetime

# Import the bot logic
from bot import PairsTradingBot, TradeLogger

# Configure Streamlit page
st.set_page_config(
    page_title="Pairs Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
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

# Function to run the bot in a separate thread
def run_bot():
    """Run the trading bot in a background thread"""
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
            # Update market data
            current_data = bot.update_market_data()
            
            # Store current data for display (convert to dict for JSON serialization)
            st.session_state.current_data = {
                'timestamp': datetime.now().isoformat(),
                'ETHUSDT': float(current_data['ETHUSDT']) if 'ETHUSDT' in current_data else 0,
                'SOLUSDT': float(current_data['SOLUSDT']) if 'SOLUSDT' in current_data else 0,
                'spread': float(current_data['spread']) if 'spread' in current_data else 0,
                'spread_zscore': float(current_data['spread_zscore']) if 'spread_zscore' in current_data else 0,
                'position': bot.position is not None
            }
            
            # Check for exit conditions if in position
            if bot.position:
                exit_triggered, reason, partial = bot.check_exit_conditions(current_data)
                if exit_triggered:
                    bot.exit_position(reason, current_data, partial)
            else:
                # Check for entry conditions if not in position
                entry_triggered, side = bot.check_entry_conditions(current_data)
                if entry_triggered:
                    bot.enter_position(side, current_data)
            
            # Sleep for 60 seconds before next iteration
            time.sleep(60)
            
        except Exception as e:
            logging.error(f"Bot error: {e}")
            st.session_state.bot_running = False
            break
    
    logging.info("Bot stopped from Streamlit")

# Main dashboard
st.title("📈 Pairs Trading Bot Dashboard")
st.markdown("---")

# Sidebar controls
with st.sidebar:
    st.header("Bot Controls")
    
    # Start/Stop buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Start Bot", disabled=st.session_state.bot_running, use_container_width=True):
            st.session_state.bot_running = True
            st.session_state.bot_thread = threading.Thread(target=run_bot, daemon=True)
            st.session_state.bot_thread.start()
            st.success("Bot started!")
            st.rerun()
    
    with col2:
        if st.button("⏹️ Stop Bot", disabled=not st.session_state.bot_running, use_container_width=True):
            st.session_state.bot_running = False
            if st.session_state.bot_thread and st.session_state.bot_thread.is_alive():
                st.session_state.bot_thread.join(timeout=2)
            st.info("Bot stopped!")
            st.rerun()
    
    st.markdown("---")
    
    st.subheader("API Credentials")
    api_key = st.text_input("API Key", type="password", value=st.session_state.get("api_key", ""))
    api_secret = st.text_input("API Secret", type="password", value=st.session_state.get("api_secret", ""))

    st.session_state.api_key = api_key
    st.session_state.api_secret = api_secret

    st.markdown("---")
    
    # Bot status
    st.subheader("Bot Status")
    if st.session_state.bot_running:
        st.success("🟢 Running")
    else:
        st.error("🔴 Stopped")
    
    # Auto-refresh
    if st.session_state.bot_running:
        st.markdown("*Auto-refreshing every 30 seconds...*")
        time.sleep(30)
        st.rerun()

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📊 Market Data")
    
    if st.session_state.current_data:
        # Display current market data
        data_col1, data_col2, data_col3, data_col4 = st.columns(4)
        
        with data_col1:
            st.metric("ETH/USDT", f"${st.session_state.current_data.get('ETHUSDT', 0):.2f}")
        
        with data_col2:
            st.metric("SOL/USDT", f"${st.session_state.current_data.get('SOLUSDT', 0):.2f}")
        
        with data_col3:
            spread = st.session_state.current_data.get('spread', 0)
            st.metric("Spread", f"{spread:.4f}")
        
        with data_col4:
            zscore = st.session_state.current_data.get('spread_zscore', 0)
            st.metric("Z-Score", f"{zscore:.2f}")
        
        # Position status
        if st.session_state.current_data.get('position', False):
            st.success("📍 Currently in position")
        else:
            st.info("📍 No active position")
        
        st.text(f"Last updated: {st.session_state.current_data.get('timestamp', 'Never')}")
    else:
        st.info("No market data available. Start the bot to begin collecting data.")

with col2:
    st.subheader("⚙️ Configuration")
    
    # Editable trading parameters
    st.markdown("**Trading Parameters:**")
    
    usdt_amount_per_leg = st.number_input(
        "USDT Amount Per Leg",
        min_value=100.0,
        max_value=10000.0,
        value=4000.0,
        step=100.0,
        key="usdt_amount_per_leg"
    )
    
    entry_zscore = st.number_input(
        "Entry Z-Score",
        min_value=0.1,
        max_value=5.0,
        value=1.5,
        step=0.1,
        key="entry_zscore"
    )
    
    exit_zscore = st.number_input(
        "Exit Z-Score",
        min_value=0.1,
        max_value=5.0,
        value=0.5,
        step=0.1,
        key="exit_zscore"
    )
    
    stop_loss_zscore_threshold = st.number_input(
        "Stop Loss Z-Score Threshold",
        min_value=1.0,
        max_value=10.0,
        value=3.0,
        step=0.1,
        key="stop_loss_zscore_threshold"
    )
    
    max_hold_period_bars = st.number_input(
        "Max Hold Period (bars)",
        min_value=1,
        max_value=200,
        value=48,
        step=1,
        key="max_hold_period_bars"
    )
    
    partial_exit_pct = st.slider(
        "Partial Exit Percentage",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        format="%d%%",
        key="partial_exit_pct"
    )
    
    rolling_window = st.number_input(
        "Rolling Window (bars)",
        min_value=10,
        max_value=200,
        value=48,
        step=1,
        key="rolling_window"
    )

    # Store parameters in session state for bot to access
    st.session_state.trading_params = {
        "USDT_AMOUNT_PER_LEG": usdt_amount_per_leg,
        "ENTRY_ZSCORE": entry_zscore,
        "EXIT_ZSCORE": exit_zscore,
        "STOP_LOSS_ZSCORE_THRESHOLD": stop_loss_zscore_threshold,
        "MAX_HOLD_PERIOD_BARS": max_hold_period_bars,
        "PARTIAL_EXIT_PCT": partial_exit_pct / 100.0, # Convert percentage to decimal
        "ROLLING_WINDOW": rolling_window
    }

# Trade log section
st.markdown("---")
st.subheader("📋 Trade Log")

# Load and display trade logs
try:
    trade_logger = TradeLogger()
    trade_logger.load_trades()
    
    if trade_logger.trades:
        # Convert trades to DataFrame for better display
        df_trades = pd.DataFrame(trade_logger.trades)
        
        # Display summary statistics
        total_trades = len(df_trades)
        completed_trades = len(df_trades[df_trades['status'] == 'COMPLETED'])
        
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        
        with summary_col1:
            st.metric("Total Trades", total_trades)
        
        with summary_col2:
            st.metric("Completed Trades", completed_trades)
        
        with summary_col3:
            if completed_trades > 0:
                # Calculate total PnL from completed trades
                total_pnl = 0
                for trade in trade_logger.trades:
                    if trade['status'] == 'COMPLETED' and trade.get('pnl_analysis'):
                        pnl = trade['pnl_analysis'].get('total_pnl', 0)
                        if isinstance(pnl, (int, float)):
                            total_pnl += pnl
                st.metric("Total PnL", f"${total_pnl:.2f}")
            else:
                st.metric("Total PnL", "$0.00")
        
        # Display detailed trade log
        st.dataframe(
            df_trades[['trade_id', 'timestamp', 'status', 'symbol1', 'symbol2', 'side']],
            use_container_width=True
        )
        
        # Show detailed view of selected trade
        if not df_trades.empty:
            selected_trade_id = st.selectbox("Select trade for details:", df_trades['trade_id'].tolist())
            selected_trade = df_trades[df_trades['trade_id'] == selected_trade_id].iloc[0]
            
            st.json(selected_trade.to_dict())
    else:
        st.info("No trades logged yet. Start the bot to begin trading.")
        
except Exception as e:
    st.error(f"Error loading trade log: {e}")

# Raw log display
st.markdown("---")
st.subheader("📝 Raw Bot Log")

if os.path.exists('trading_bot.log'):
    with open('trading_bot.log', 'r') as f:
        log_content = f.read()
    
    # Show only the last 50 lines to avoid overwhelming the display
    log_lines = log_content.split('\n')
    if len(log_lines) > 50:
        log_content = '\n'.join(log_lines[-50:])
        st.info("Showing last 50 lines of log file")
    
    st.code(log_content, language='text')
else:
    st.info("Trading bot log file not found.")

# Footer
st.markdown("---")
st.markdown("*Pairs Trading Bot - ETH/USDT vs SOL/USDT*")


