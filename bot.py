import pandas as pd
import math
import time
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from binance.client import Client
from binance.enums import *

# === CONFIG ===
class BinanceTestnetClient:
    def __init__(self, api_key: str, api_secret: str):
        # Use python-binance library with testnet=True
        self.client = Client(api_key, api_secret, testnet=True)
        
    def get_account_info(self):
        """Get futures account information"""
        return self.client.futures_account()
    
    def place_order(self, symbol: str, side: str, quantity: float, order_type: str = 'MARKET'):
        """Place order using python-binance library"""
        try:
            if order_type.upper() == 'MARKET':
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=side.upper(),
                    type=ORDER_TYPE_MARKET,
                    quantity=quantity
                )
            else:  # LIMIT order
                # You'd need to add price parameter for limit orders
                raise ValueError("LIMIT orders need price parameter")
                
            return order
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            raise e
    
    def get_position_info(self, symbol: str = None):
        """Get position information"""
        return self.client.futures_position_information(symbol=symbol)
    
    def get_trades(self, symbol: str, limit: int = 50):
        """Get trade history"""
        return self.client.futures_account_trades(symbol=symbol, limit=limit)

class TradeLogger:
    """Same TradeLogger class as your original"""
    def __init__(self, filename: str = 'trade_logs.json'):
        self.filename = filename
        self.trades = []
        self.load_trades()
    
    def load_trades(self):
        try:
            with open(self.filename, 'r') as f:
                self.trades = json.load(f)
        except FileNotFoundError:
            self.trades = []
    
    def save_trades(self):
        with open(self.filename, 'w') as f:
            json.dump(self.trades, f, indent=2, default=str)
    
    def log_trade_entry(self, trade_id: str, symbol1: str, symbol2: str, side: str, 
                       entry_data: dict, market_data: dict):
        trade_entry = {
            'trade_id': trade_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'ENTERED',
            'symbol1': symbol1,
            'symbol2': symbol2,
            'side': side,
            'entry_data': entry_data,
            'market_data': market_data,
            'orders': [],
            'exit_data': None,
            'pnl_analysis': None
        }
        self.trades.append(trade_entry)
        self.save_trades()
        logger.info(f"Trade entry logged: {trade_id}")
    
    def log_order(self, trade_id: str, order_response: dict, order_type: str):
        for trade in self.trades:
            if trade['trade_id'] == trade_id and trade['status'] == 'ENTERED':
                trade['orders'].append({
                    'timestamp': datetime.now().isoformat(),
                    'type': order_type,
                    'response': order_response
                })
                self.save_trades()
                break
    
    def log_trade_exit(self, trade_id: str, exit_data: dict, pnl_analysis: dict):
        for trade in self.trades:
            if trade['trade_id'] == trade_id:
                trade['status'] = 'COMPLETED'
                trade['exit_data'] = exit_data
                trade['pnl_analysis'] = pnl_analysis
                self.save_trades()
                logger.info(f"Trade exit logged: {trade_id}, PnL: ${pnl_analysis['total_pnl']:.2f}")
                break

class PairsTradingBot:
    """Same trading logic as your original, but using python-binance client"""
    def __init__(self, api_key: str, api_secret: str, symbol1: str = 'ETHUSDT', symbol2: str = 'SOLUSDT', 
                 usdt_amount_per_leg: float = 4000,
                 max_loss_total: float = 80,
                 rolling_window: int = 48,
                 entry_zscore: float = 1.5,
                 exit_zscore: float = 0.5,
                 stop_loss_zscore_threshold: float = 3.0,
                 partial_exit_pct: float = 0.5,
                 max_hold_period_bars: int = 48):
        self.client = BinanceTestnetClient(api_key, api_secret)
        self.trade_logger = TradeLogger()
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.position = None
        self.data_buffer = pd.DataFrame()

        # Dynamic trading parameters
        self.USDT_AMOUNT_PER_LEG = usdt_amount_per_leg
        self.MAX_LOSS_TOTAL = max_loss_total
        self.ROLLING_WINDOW = rolling_window
        self.ENTRY_ZSCORE = entry_zscore
        self.EXIT_ZSCORE = exit_zscore
        self.STOP_LOSS_ZSCORE_THRESHOLD = stop_loss_zscore_threshold
        self.PARTIAL_EXIT_PCT = partial_exit_pct
        self.MAX_HOLD_PERIOD_BARS = max_hold_period_bars
        
    def fetch_klines(self, symbol: str, interval: str = '1m', limit: int = 100):
        """Fetch klines using python-binance client"""
        klines = self.client.client.futures_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df.set_index('open_time', inplace=True)
        df['close'] = df['close'].astype(float)
        return df
    
    def adjust_qty_to_lot_size(self, qty: float, symbol: str) -> float:
        """Same lot size adjustment logic"""
        rules = LOT_SIZE_RULES.get(symbol)
        if not rules:
            return qty
        step = rules['stepSize']
        min_qty = rules['minQty']
        qty_adj = math.floor(qty / step) * step
        if qty_adj < min_qty:
            qty_adj = min_qty if qty >= min_qty else 0
        return qty_adj
    
    def calculate_equal_dollar_qtys(self, dollar_amount: float, price1: float, price2: float):
        """Same quantity calculation logic"""
        qty1 = dollar_amount / price1
        qty2 = dollar_amount / price2
        return qty1, qty2
    
    def calculate_percent_spread(self, price1: float, qty1: float, price2: float, qty2: float):
        """Same spread calculation logic"""
        value1 = price1 * qty1
        value2 = price2 * qty2
        avg = (value1 + value2) / 2
        if avg == 0:
            return 0
        return (value1 - value2) / avg
    
    def update_market_data(self):
        """Same market data update logic"""
        df1 = self.fetch_klines(self.symbol1, limit=self.ROLLING_WINDOW + 10)
        df2 = self.fetch_klines(self.symbol2, limit=self.ROLLING_WINDOW + 10)
        
        data = pd.DataFrame({
            self.symbol1: df1['close'],
            self.symbol2: df2['close']
        }).dropna()
        
        # Same calculations as your original
        data['qty1_raw'], data['qty2_raw'] = zip(*data.apply(
            lambda row: self.calculate_equal_dollar_qtys(self.USDT_AMOUNT_PER_LEG, row[self.symbol1], row[self.symbol2]), axis=1))
        data['qty1'] = data.apply(lambda row: self.adjust_qty_to_lot_size(row['qty1_raw'], self.symbol1), axis=1)
        data['qty2'] = data.apply(lambda row: self.adjust_qty_to_lot_size(row['qty2_raw'], self.symbol2), axis=1)
        
        data['spread'] = data.apply(lambda row: self.calculate_percent_spread(
            row[self.symbol1], row['qty1'], row[self.symbol2], row['qty2']), axis=1)
        
        # Same rolling statistics
        data['spread_mean'] = data['spread'].rolling(ROLLING_WINDOW).mean()
        data['spread_std'] = data['spread'].rolling(ROLLING_WINDOW).std()
        data['spread_zscore'] = (data['spread'] - data['spread_mean']) / data['spread_std']
        
        self.data_buffer = data
        return data.iloc[-1]
    
    def enter_position(self, side: str, current_data: pd.Series):
        """Same position entry logic"""
        trade_id = f"{side}_{int(time.time())}"
        
        price1 = current_data[self.symbol1]
        price2 = current_data[self.symbol2]
        qty1 = round(current_data['qty1'], 3)
        qty2 = round(current_data['qty2'], 0)
        
        logger.info(f"Attempting to enter {side} position - Trade ID: {trade_id}")
        logger.info(f"{self.symbol1}: {qty1:.4f} @ {price1:.4f}")
        logger.info(f"{self.symbol2}: {qty2:.4f} @ {price2:.4f}")
        
        try:
            # Same order placement logic
            if side == 'long':
                order1 = self.client.place_order(self.symbol1, 'BUY', qty1)
                self.trade_logger.log_order(trade_id, order1, 'ENTRY_LEG1_LONG')
                
                order2 = self.client.place_order(self.symbol2, 'SELL', qty2)
                self.trade_logger.log_order(trade_id, order2, 'ENTRY_LEG2_SHORT')
                
            else:
                order1 = self.client.place_order(self.symbol1, 'SELL', qty1)
                self.trade_logger.log_order(trade_id, order1, 'ENTRY_LEG1_SHORT')
                
                order2 = self.client.place_order(self.symbol2, 'BUY', qty2)
                self.trade_logger.log_order(trade_id, order2, 'ENTRY_LEG2_LONG')
            
            # Same trade logging
            entry_data = {
                'price1': price1,
                'price2': price2,
                'qty1': qty1,
                'qty2': qty2,
                'spread': current_data['spread'],
                'zscore': current_data['spread_zscore']
            }
            
            market_data = {
                'spread_mean': current_data['spread_mean'],
                'spread_std': current_data['spread_std']
            }
            
            self.trade_logger.log_trade_entry(trade_id, self.symbol1, self.symbol2, side, entry_data, market_data)
            
            # Same position state update
            self.position = {
                'trade_id': trade_id,
                'side': side,
                'entry_index': len(self.data_buffer) - 1,
                'entry_data': entry_data,
                'market_data': market_data,
                'partial_exited': False,
                'holding_bars': 0
            }
            
            logger.info(f"Position entered successfully: {trade_id}")
            
        except Exception as e:
            logger.error(f"Failed to enter position: {e}")
    
    def exit_position(self, reason: str, current_data: pd.Series, partial: bool = False):
        """Same exit logic as your original"""
        if not self.position:
            return
            
        trade_id = self.position['trade_id']
        side = self.position['side']
        
        try:
            # Same exit quantity calculations
            original_qty1 = self.position['entry_data']['qty1']
            original_qty2 = self.position['entry_data']['qty2']
            
            if partial:
                exit_qty1 = original_qty1 * self.PARTIAL_EXIT_PCT
                exit_qty2 = original_qty2 * self.PARTIAL_EXIT_PCT
                self.position['entry_data']['qty1'] *= (1 - PARTIAL_EXIT_PCT)
                self.position['entry_data']['qty2'] *= (1 - PARTIAL_EXIT_PCT)
                self.position['partial_exited'] = True
            else:
                exit_qty1 = self.position['entry_data']['qty1']
                exit_qty2 = self.position['entry_data']['qty2']
            
            exit_qty1 = self.adjust_qty_to_lot_size(exit_qty1, self.symbol1)
            exit_qty2 = self.adjust_qty_to_lot_size(exit_qty2, self.symbol2)
            
            logger.info(f"Exiting position ({reason}) - Trade ID: {trade_id}")
            
            # Same exit order logic
            if side == 'long':
                order1 = self.client.place_order(self.symbol1, 'SELL', exit_qty1)
                order_type1 = 'PARTIAL_EXIT_LEG1_SELL' if partial else 'EXIT_LEG1_SELL'
                self.trade_logger.log_order(trade_id, order1, order_type1)
                
                order2 = self.client.place_order(self.symbol2, 'BUY', exit_qty2)
                order_type2 = 'PARTIAL_EXIT_LEG2_BUY' if partial else 'EXIT_LEG2_BUY'
                self.trade_logger.log_order(trade_id, order2, order_type2)
                
            else:
                order1 = self.client.place_order(self.symbol1, 'BUY', exit_qty1)
                order_type1 = 'PARTIAL_EXIT_LEG1_BUY' if partial else 'EXIT_LEG1_BUY'
                self.trade_logger.log_order(trade_id, order1, order_type1)
                
                order2 = self.client.place_order(self.symbol2, 'SELL', exit_qty2)
                order_type2 = 'PARTIAL_EXIT_LEG2_SELL' if partial else 'EXIT_LEG2_SELL'
                self.trade_logger.log_order(trade_id, order2, order_type2)
            
            if not partial:
                # Same PnL calculation
                pnl_analysis = self.calculate_actual_pnl(trade_id)
                
                exit_data = {
                    'price1': current_data[self.symbol1],
                    'price2': current_data[self.symbol2],
                    'spread': current_data['spread'],
                    'zscore': current_data['spread_zscore'],
                    'reason': reason
                }
                
                self.trade_logger.log_trade_exit(trade_id, exit_data, pnl_analysis)
                self.position = None
                logger.info(f"Position closed: {trade_id}")
            else:
                logger.info(f"Partial exit completed: {trade_id}")
                
        except Exception as e:
            logger.error(f"Failed to exit position: {e}")
    
    def calculate_actual_pnl(self, trade_id: str) -> dict:
        """Same PnL calculation using python-binance client"""
        try:
            trades1 = self.client.get_trades(self.symbol1, limit=100)
            trades2 = self.client.get_trades(self.symbol2, limit=100)
            
            # Same PnL logic as your original
            trade_entry = None
            for trade in self.trade_logger.trades:
                if trade['trade_id'] == trade_id:
                    trade_entry = trade
                    break
            
            if not trade_entry:
                return {'error': 'Trade entry not found'}
            
            # Same time filtering and PnL calculation logic
            entry_time = datetime.fromisoformat(trade_entry['timestamp'])
            
            total_pnl = 0
            total_fees = 0
            
            for trade in trades1 + trades2:
                trade_time = datetime.fromtimestamp(int(trade['time']) / 1000)
                if abs((trade_time - entry_time).total_seconds()) < 3600:
                    total_pnl += float(trade['realizedPnl'])
                    total_fees += float(trade['commission'])
            
            return {
                'total_pnl': total_pnl,
                'total_fees': total_fees
            }
            
        except Exception as e:
            logger.error(f"Error calculating actual PnL: {e}")
            return {'error': str(e)}
    
    def check_exit_conditions(self, current_data: pd.Series) -> tuple:
        """Same exit condition logic"""
        if not self.position:
            return False, "", False
            
        zscore = current_data['spread_zscore']
        self.position['holding_bars'] += 1
        
        # Same exit condition checks
        current_spread = current_data['spread']
        entry_spread = self.position['entry_data']['spread']
        
        spread_change = current_spread - entry_spread
        
        # Stop Loss
        if abs(zscore) >= self.STOP_LOSS_ZSCORE_THRESHOLD:
            logger.warning(f"STOP LOSS TRIGGERED: Z-score {zscore:.2f}")
            return True, "STOP_LOSS", False
        
        # Exit Z-score
        if self.position["side"] == "long" and zscore <= self.EXIT_ZSCORE:
            logger.info(f"EXIT CONDITION MET (long): Z-score {zscore:.2f}")
            return True, "EXIT_ZSCORE", False
        elif self.position["side"] == "short" and zscore >= -self.EXIT_ZSCORE:
            logger.info(f"EXIT CONDITION MET (short): Z-score {zscore:.2f}")
            return True, "EXIT_ZSCORE", False
            
        # Max Hold Period
        if self.position["holding_bars"] >= self.MAX_HOLD_PERIOD_BARS:
            logger.info(f"MAX HOLD PERIOD REACHED: {self.position['holding_bars']} bars")
            return True, "MAX_HOLD_PERIOD", False
            
        # Partial Exit (if not already partially exited)
        if not self.position['partial_exited']:
            if self.position['side'] == 'long' and zscore <= 0:
                logger.info(f"PARTIAL EXIT TRIGGERED (long): Z-score {zscore:.2f}")
                return True, "PARTIAL_EXIT", True
            elif self.position['side'] == 'short' and zscore >= 0:
                logger.info(f"PARTIAL EXIT TRIGGERED (short): Z-score {zscore:.2f}")
                return True, "PARTIAL_EXIT", True
        
        return False, "", False
    
    def check_entry_conditions(self, current_data: pd.Series) -> tuple:
        """Same entry condition logic"""
        zscore = current_data['spread_zscore']
        
        if zscore <= -ENTRY_ZSCORE:
            logger.info(f"ENTRY CONDITION MET (long): Z-score {zscore:.2f}")
            return True, "long"
        elif zscore >= ENTRY_ZSCORE:
            logger.info(f"ENTRY CONDITION MET (short): Z-score {zscore:.2f}")
            return True, "short"
        
        return False, ""

    def run(self):
        """Main bot loop for continuous operation"""
        logger.info("Bot started. Waiting for market data...")
        while True:
            try:
                current_data = self.update_market_data()
                
                if self.position:
                    exit_triggered, reason, partial = self.check_exit_conditions(current_data)
                    if exit_triggered:
                        self.exit_position(reason, current_data, partial)
                else:
                    entry_triggered, side = self.check_entry_conditions(current_data)
                    if entry_triggered:
                        self.enter_position(side, current_data)
                
                time.sleep(60) # Run every minute
            except Exception as e:
                logger.error(f"An error occurred in the main loop: {e}")
                time.sleep(300) # Wait before retrying

if __name__ == "__main__":
    bot = PairsTradingBot()
    bot.run()


