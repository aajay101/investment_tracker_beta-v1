import logging
from stock_utils import get_stock_price, get_stock_symbols, get_stock_history

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_stock_utils():
    try:
        # Test stock symbol search
        print("Testing stock symbol search...")
        symbols = get_stock_symbols("REL")
        print(f"Found symbols: {symbols}")
        
        if len(symbols) > 0:
            # Test stock price
            symbol = symbols[0]
            print(f"\nTesting stock price for {symbol}...")
            price = get_stock_price(symbol)
            print(f"Current price for {symbol}: {price}")
            
            # Test stock history
            print(f"\nTesting stock history for {symbol}...")
            history = get_stock_history(symbol, period='1wk')
            print(f"Got {len(history)} history records")
            if len(history) > 0:
                print(f"First record: {history[0]}")
        
        print("\n✅ Stock utilities test completed!")
    except Exception as e:
        logger.error(f"Error testing stock utilities: {str(e)}")
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_stock_utils() 