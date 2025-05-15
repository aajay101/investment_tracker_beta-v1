import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
import requests
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache stock prices for 5 minutes to avoid excessive API calls
@lru_cache(maxsize=128)
def get_stock_price_cached(symbol, timestamp=None):
    """Get the current price of a stock symbol with caching"""
    # If timestamp not provided, round to nearest 5 minutes to enable caching
    if timestamp is None:
        # Round to nearest 5 minutes for cache effectiveness
        now = datetime.now()
        timestamp = int((now.replace(second=0, microsecond=0).timestamp() // 300) * 300)
    
    try:
        logger.info(f"Fetching price for {symbol} at timestamp {timestamp}")
        
        # For Indian stocks, add .NS suffix if not present for NSE stocks
        if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
            ticker_symbol = f"{symbol}.NS"
        else:
            ticker_symbol = symbol
        
        # Try to get the ticker data
        ticker = yf.Ticker(ticker_symbol)
        
        # Get the latest price
        data = ticker.history(period="1d")
        
        if data.empty:
            logger.warning(f"No data returned for {ticker_symbol}, trying fallback")
            # If NSE fails, try BSE
            if ticker_symbol.endswith('.NS'):
                bse_symbol = symbol + '.BO'
                ticker = yf.Ticker(bse_symbol)
                data = ticker.history(period="1d")
                
        if data.empty:
            logger.error(f"No data available for {symbol}")
            return None
        
        # Use Close price if available, otherwise use the last available price
        if 'Close' in data.columns and len(data['Close']) > 0:
            price = data['Close'].iloc[-1]
            # Ensure we return a plain float, not a numpy float or other non-serializable type
            return float(price)
        else:
            return None
    except Exception as e:
        logger.error(f"Error fetching stock price for {symbol}: {str(e)}")
        return None

def get_stock_price(symbol):
    """Non-cached version that calls the cached function with current timestamp"""
    # Round to nearest 5 minutes for cache effectiveness
    now = datetime.now()
    timestamp = int((now.replace(second=0, microsecond=0).timestamp() // 300) * 300)
    
    try:
        result = get_stock_price_cached(symbol, timestamp)
        # Ensure we return a JSON serializable value (float or None)
        if result is not None:
            return float(result)
        return None
    except Exception as e:
        logger.error(f"Error in get_stock_price for {symbol}: {str(e)}")
        return None

def get_daily_change(symbol):
    """Get the daily change and percent change for a stock"""
    try:
        # For Indian stocks, add .NS suffix if not present
        if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
            ticker_symbol = f"{symbol}.NS"
        else:
            ticker_symbol = symbol
        
        ticker = yf.Ticker(ticker_symbol)
        
        # Get the latest data
        data = ticker.history(period="2d")
        
        if len(data) < 2:
            # Try BSE if NSE fails
            if ticker_symbol.endswith('.NS'):
                bse_symbol = symbol + '.BO'
                ticker = yf.Ticker(bse_symbol)
                data = ticker.history(period="2d")
        
        if len(data) < 2:
            logger.warning(f"Insufficient data to calculate daily change for {symbol}")
            return 0, 0
        
        # Calculate the change
        prev_close = float(data['Close'].iloc[-2])
        current = float(data['Close'].iloc[-1])
        change = current - prev_close
        change_percent = (change / prev_close) * 100 if prev_close > 0 else 0
        
        return float(change), float(change_percent)
    except Exception as e:
        logger.error(f"Error calculating daily change for {symbol}: {str(e)}")
        return 0, 0

def get_stock_history(symbol, period='1mo'):
    """Get historical price data for a stock"""
    valid_periods = {'1d': '1d', '1wk': '1wk', '1mo': '1mo', '3mo': '3mo', '6mo': '6mo', '1y': '1y', 'max': 'max'}
    if period not in valid_periods:
        period = '1mo'  # Default to 1 month
    
    try:
        # For Indian stocks, add .NS suffix if not present
        if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
            ticker_symbol = f"{symbol}.NS"
        else:
            ticker_symbol = symbol
        
        # Get historical data
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period=valid_periods[period])
        
        if data.empty:
            # Try BSE if NSE fails
            if ticker_symbol.endswith('.NS'):
                bse_symbol = symbol + '.BO'
                ticker = yf.Ticker(bse_symbol)
                data = ticker.history(period=valid_periods[period])
        
        if data.empty:
            logger.error(f"No historical data available for {symbol}")
            return []
        
        # Convert data to a list of dictionaries for JSON serialization
        result = []
        for date, row in data.iterrows():
            result.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })
        
        return result
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        return []

@lru_cache(maxsize=1)
def get_all_stock_symbols_cached(timestamp=None):
    """Get a list of all stock symbols with caching"""
    # Cache for 24 hours by default
    if timestamp is None:
        timestamp = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    
    try:
        # Common Indian stocks (fallback list)
        common_symbols = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "HINDUNILVR", "ICICIBANK", "HDFC", 
            "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC", "BAJFINANCE", "WIPRO", "AXISBANK",
            "LT", "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN", "NTPC", "BAJAJFINSV",
            "TATAMOTORS", "ULTRACEMCO", "INDUSINDBK", "POWERGRID", "JSWSTEEL", "ADANIPORTS",
            "HCLTECH", "TECHM", "GRASIM", "DRREDDY", "NESTLEIND", "SHREECEM", "BRITANNIA",
            "DIVIDHARL", "CIPLA", "M&M", "BAJAJ-AUTO", "UPL", "HINDALCO", "TATASTEEL",
            "IOC", "BPCL", "ONGC", "COALINDIA", "GAIL", "HEROMOTOCO", "EICHERMOT"
        ]
        return common_symbols
    except Exception as e:
        logger.error(f"Error fetching all stock symbols: {str(e)}")
        # Return a small default list as fallback
        return ["RELIANCE", "TCS", "HDFCBANK", "INFY", "HINDUNILVR"]

def get_stock_symbols(query):
    """Search for stock symbols matching the query"""
    # Get cached list of symbols (cached for 24 hours)
    timestamp = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    all_symbols = get_all_stock_symbols_cached(timestamp)
    
    # Filter symbols based on the query
    query = query.upper()
    matching_symbols = [s for s in all_symbols if query in s]
    
    # Limit results to top 10
    return matching_symbols[:10]
