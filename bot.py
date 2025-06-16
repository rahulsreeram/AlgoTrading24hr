import pandas as pd
import numpy as np
import time
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Trading pair configuration
PAIRS = ['ETHUSDT', 'SOLUSDT']

# Lot size rules for the pairs
LOT_SIZE_RULES = {
    'ETHUSDT': {'minQty': 0.001, 'stepSize': 0.001},
    'SOLUSDT': {'minQty': 0.1, 'stepSize': 0.1}
}

class PairsTradingBot:
    def __init__(self, api_key: str, api_secret: str, usdt_amount_per_leg: float = 4000.0,
                 rolling_window: int = 48, entry_zscore: float = 1.5, exit_zscore: float = 0.5,
                 stop_loss_zscore_threshold: float = 3.0, partial_exit_pct: float = 0.5,
                 max_hold_period_bars: int = 48):
        
        self.client = Client(api_key, api_secret)
        self.USDT_AMOUNT_PER_LEG = usdt_amount_per_leg
        self.ROLLING_WINDOW = rolling_window
        self.ENTRY_ZSCORE = entry_zscore
        self.EXIT_ZSCORE = exit_zscore
        self.STOP_LOSS_ZSCORE_THRESHOLD = stop_loss_zscore_threshold
        self.PARTIAL_EXIT_PCT = partial_exit_pct
        self.MAX_HOLD_PERIOD_BARS = max_hold_period_bars
        
        # Initialize data storage
        self.price_data = pd.DataFrame()
        self.current_position = None
        self.position_entry_time = None
        self.position_entry_bar = 0
        self.partial_exit_executed = False
        
        logger.info("Pairs Trading Bot initialized")
        logger.info(f"Parameters: USDT_AMOUNT_PER_LEG={usdt_amount_per_leg}, "
                   f"ENTRY_ZSCORE={entry_zscore}, EXIT_ZSCORE={exit_zscore}")

    def get_current_prices(self) -> Dict[str, float]:
        """Get current prices for both pairs"""
        try:
            tickers = self.client.get_all_tickers()
            prices = {}
            for ticker in tickers:
                if ticker['symbol'] in PAIRS:
                    prices[ticker['symbol']] = float(ticker['price'])
            return prices
        except BinanceAPIException as e:
            logger.error(f"Error fetching prices: {e}")
            return {}

    def calculate_spread_metrics(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate spread and z-score"""
        if len(data) < 2:
            return data
            
        # Calculate log prices
        data['eth_log'] = np.log(data['ETHUSDT'])
        data['sol_log'] = np.log(data['SOLUSDT'])
        
        # Calculate spread (ETH - SOL in log space)
        data['spread'] = data['eth_log'] - data['sol_log']
        
        # Calculate rolling mean and std for z-score
        if len(data) >= self.ROLLING_WINDOW:
            data['spread_mean'] = data['spread'].rolling(window=self.ROLLING_WINDOW).mean()
            data['spread_std'] = data['spread'].rolling(window=self.ROLLING_WINDOW).std()
            data['spread_zscore'] = (data['spread'] - data['spread_mean']) / data['spread_std']
        else:
            data['spread_mean'] = data['spread'].expanding().mean()
            data['spread_std'] = data['spread'].expanding().std()
            data['spread_zscore'] = (data['spread'] - data['spread_mean']) / data['spread_std']
        
        return data

    def check_entry_conditions(self, current_data: pd.Series) -> Tuple[bool, str]:
        """Check if entry conditions are met"""
        zscore = current_data['spread_zscore']
        
        if zscore <= -self.ENTRY_ZSCORE:
            logger.info(f"ENTRY CONDITION MET (long): Z-score {zscore:.2f}")
            return True, "long"
        elif zscore >= self.ENTRY_ZSCORE:
            logger.info(f"ENTRY CONDITION MET (short): Z-score {zscore:.2f}")
            return True, "short"
        
        return False, ""

    def check_exit_conditions(self, current_data: pd.Series) -> Tuple[bool, str]:
        """Check if exit conditions are met"""
        if not self.current_position:
            return False, ""
        
        zscore = current_data['spread_zscore']
        position_type = self.current_position['type']
        bars_held = self.position_entry_bar
        
        # Check for normal exit conditions
        if position_type == "long" and zscore >= -self.EXIT_ZSCORE:
            logger.info(f"EXIT CONDITION MET (long position): Z-score {zscore:.2f}")
            return True, "normal_exit"
        elif position_type == "short" and zscore <= self.EXIT_ZSCORE:
            logger.info(f"EXIT CONDITION MET (short position): Z-score {zscore:.2f}")
            return True, "normal_exit"
        
        # Check for stop loss conditions
        if position_type == "long" and zscore >= self.STOP_LOSS_ZSCORE_THRESHOLD:
            logger.warning(f"STOP LOSS TRIGGERED (long position): Z-score {zscore:.2f}")
            return True, "stop_loss"
        elif position_type == "short" and zscore <= -self.STOP_LOSS_ZSCORE_THRESHOLD:
            logger.warning(f"STOP LOSS TRIGGERED (short position): Z-score {zscore:.2f}")
            return True, "stop_loss"
        
        # Check for max hold period
        if bars_held >= self.MAX_HOLD_PERIOD_BARS:
            logger.warning(f"MAX HOLD PERIOD REACHED: {bars_held} bars")
            return True, "max_hold_period"
        
        # Check for partial exit conditions
        if not self.partial_exit_executed:
            if position_type == "long" and zscore >= -self.EXIT_ZSCORE * 0.7:
                logger.info(f"PARTIAL EXIT CONDITION MET (long position): Z-score {zscore:.2f}")
                return True, "partial_exit"
            elif position_type == "short" and zscore <= self.EXIT_ZSCORE * 0.7:
                logger.info(f"PARTIAL EXIT CONDITION MET (short position): Z-score {zscore:.2f}")
                return True, "partial_exit"
        
        return False, ""

    def calculate_position_size(self, price: float, symbol: str) -> float:
        """Calculate position size based on USDT amount and lot size rules"""
        raw_quantity = self.USDT_AMOUNT_PER_LEG / price
        
        # Apply lot size rules
        if symbol in LOT_SIZE_RULES:
            min_qty = LOT_SIZE_RULES[symbol]['minQty']
            step_size = LOT_SIZE_RULES[symbol]['stepSize']
            
            # Round down to nearest step size
            quantity = (raw_quantity // step_size) * step_size
            
            # Ensure minimum quantity
            if quantity < min_qty:
                quantity = min_qty
        else:
            quantity = round(raw_quantity, 6)
        
        return quantity

    def execute_trade(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """Execute a trade"""
        try:
            logger.info(f"Executing {side} order: {quantity} {symbol}")
            
            order = self.client.order_market(
                symbol=symbol,
                side=side,
                quantity=quantity
            )
            
            logger.info(f"Order executed successfully: {order['orderId']}")
            return order
            
        except BinanceAPIException as e:
            logger.error(f"Error executing trade for {symbol}: {e}")
            return None

    def enter_position(self, position_type: str, current_prices: Dict[str, float]) -> bool:
        """Enter a new position"""
        try:
            eth_price = current_prices['ETHUSDT']
            sol_price = current_prices['SOLUSDT']
            
            eth_quantity = self.calculate_position_size(eth_price, 'ETHUSDT')
            sol_quantity = self.calculate_position_size(sol_price, 'SOLUSDT')
            
            if position_type == "long":
                # Long spread: Buy ETH, Sell SOL
                eth_order = self.execute_trade('ETHUSDT', 'BUY', eth_quantity)
                sol_order = self.execute_trade('SOLUSDT', 'SELL', sol_quantity)
            else:
                # Short spread: Sell ETH, Buy SOL
                eth_order = self.execute_trade('ETHUSDT', 'SELL', eth_quantity)
                sol_order = self.execute_trade('SOLUSDT', 'BUY', sol_quantity)
            
            if eth_order and sol_order:
                self.current_position = {
                    'type': position_type,
                    'eth_quantity': eth_quantity,
                    'sol_quantity': sol_quantity,
                    'entry_prices': current_prices.copy(),
                    'entry_time': datetime.now(),
                    'eth_order_id': eth_order['orderId'],
                    'sol_order_id': sol_order['orderId']
                }
                
                self.position_entry_time = datetime.now()
                self.position_entry_bar = 0
                self.partial_exit_executed = False
                
                logger.info(f"Position entered successfully: {position_type}")
                logger.info(f"ETH: {eth_quantity} at ${eth_price:.2f}")
                logger.info(f"SOL: {sol_quantity} at ${sol_price:.2f}")
                
                return True
            else:
                logger.error("Failed to execute both orders for position entry")
                return False
                
        except Exception as e:
            logger.error(f"Error entering position: {e}")
            return False

    def exit_position(self, exit_type: str, current_prices: Dict[str, float], partial: bool = False) -> bool:
        """Exit current position"""
        if not self.current_position:
            return False
        
        try:
            position_type = self.current_position['type']
            
            # Calculate quantities to exit
            if partial:
                eth_quantity = self.current_position['eth_quantity'] * self.PARTIAL_EXIT_PCT
                sol_quantity = self.current_position['sol_quantity'] * self.PARTIAL_EXIT_PCT
            else:
                eth_quantity = self.current_position['eth_quantity']
                sol_quantity = self.current_position['sol_quantity']
            
            # Adjust quantities according to lot size rules
            eth_quantity = self.calculate_position_size(current_prices['ETHUSDT'], 'ETHUSDT')
            sol_quantity = self.calculate_position_size(current_prices['SOLUSDT'], 'SOLUSDT')
            
            if position_type == "long":
                # Exit long spread: Sell ETH, Buy SOL
                eth_order = self.execute_trade('ETHUSDT', 'SELL', eth_quantity)
                sol_order = self.execute_trade('SOLUSDT', 'BUY', sol_quantity)
            else:
                # Exit short spread: Buy ETH, Sell SOL
                eth_order = self.execute_trade('ETHUSDT', 'BUY', eth_quantity)
                sol_order = self.execute_trade('SOLUSDT', 'SELL', sol_quantity)
            
            if eth_order and sol_order:
                if partial:
                    self.current_position['eth_quantity'] *= (1 - self.PARTIAL_EXIT_PCT)
                    self.current_position['sol_quantity'] *= (1 - self.PARTIAL_EXIT_PCT)
                    self.partial_exit_executed = True
                    logger.info(f"Partial position exit executed: {exit_type}")
                else:
                    logger.info(f"Full position exit executed: {exit_type}")
                    self.current_position = None
                    self.position_entry_time = None
                    self.position_entry_bar = 0
                    self.partial_exit_executed = False
                
                return True
            else:
                logger.error("Failed to execute both orders for position exit")
                return False
                
        except Exception as e:
            logger.error(f"Error exiting position: {e}")
            return False

    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        if self.current_position:
            return [self.current_position]
        return []

    def run_single_iteration(self) -> Optional[pd.Series]:
        """Run a single iteration of the trading bot"""
        try:
            # Get current prices
            current_prices = self.get_current_prices()
            if not current_prices or len(current_prices) != 2:
                logger.warning("Could not fetch current prices")
                return None
            
            # Create new data point
            timestamp = datetime.now()
            new_data = pd.DataFrame({
                'timestamp': [timestamp],
                'ETHUSDT': [current_prices['ETHUSDT']],
                'SOLUSDT': [current_prices['SOLUSDT']]
            })
            
            # Append to historical data
            if self.price_data.empty:
                self.price_data = new_data
            else:
                self.price_data = pd.concat([self.price_data, new_data], ignore_index=True)
            
            # Keep only recent data to manage memory
            if len(self.price_data) > 1000:
                self.price_data = self.price_data.tail(500).reset_index(drop=True)
            
            # Calculate spread metrics
            self.price_data = self.calculate_spread_metrics(self.price_data)
            
            # Get current data point
            current_data = self.price_data.iloc[-1]
            
            # Update position tracking
            if self.current_position:
                self.position_entry_bar += 1
            
            # Check for exit conditions first (if we have a position)
            if self.current_position:
                should_exit, exit_type = self.check_exit_conditions(current_data)
                if should_exit:
                    if exit_type == "partial_exit":
                        self.exit_position(exit_type, current_prices, partial=True)
                    else:
                        self.exit_position(exit_type, current_prices, partial=False)
            
            # Check for entry conditions (if we don't have a position)
            elif len(self.price_data) >= self.ROLLING_WINDOW:
                should_enter, position_type = self.check_entry_conditions(current_data)
                if should_enter:
                    self.enter_position(position_type, current_prices)
            
            # Add additional fields to current_data for display
            current_data_dict = current_data.to_dict()
            current_data_dict.update({
                'eth_price': current_prices['ETHUSDT'],
                'sol_price': current_prices['SOLUSDT'],
                'timestamp': timestamp,
                'has_position': self.current_position is not None,
                'position_type': self.current_position['type'] if self.current_position else None
            })
            
            return pd.Series(current_data_dict)
            
        except Exception as e:
            logger.error(f"Error in trading iteration: {e}")
            return None

    def run(self):
        """Main trading loop"""
        logger.info("Starting pairs trading bot...")
        
        try:
            while True:
                result = self.run_single_iteration()
                if result is not None:
                    logger.info(f"Iteration completed. Z-score: {result.get('spread_zscore', 'N/A'):.2f}")
                
                # Wait for next iteration (1 minute)
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            # Close any open positions
            if self.current_position:
                logger.info("Closing open position before shutdown...")
                current_prices = self.get_current_prices()
                if current_prices:
                    self.exit_position("shutdown", current_prices)

if __name__ == "__main__":
    # This would only run if bot.py is executed directly
    import os
    
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("Please set BINANCE_API_KEY and BINANCE_API_SECRET environment variables")
        exit(1)
    
    bot = PairsTradingBot(api_key, api_secret)
    bot.run()
