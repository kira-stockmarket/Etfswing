import pandas as pd
import yfinance as yf
import os

def get_trading_universe(excel_path="Filtered_Best_ETFs_For_Trading.xlsx"):
    """
    Reads the filtered ETF excel file and extracts the symbols.
    Appends '.NS' to match Yahoo Finance ticker formatting for NSE India.
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Universe file {excel_path} not found.")
        
    df = pd.read_excel(excel_path)
    symbols = df['SYMBOL'].tolist()
    
    # Append .NS for Yahoo Finance
    yf_symbols = [f"{sym}.NS" for sym in symbols]
    return yf_symbols

def download_historical_data(tickers, period="5y", interval="1d"):
    """
    Downloads historical OHLCV data for the ETF universe.
    """
    print(f"Downloading data for {len(tickers)} ETFs...")
    data = yf.download(tickers, period=period, interval=interval, group_by='ticker')
    return data

if __name__ == "__main__":
    universe = get_trading_universe()
    print("Trading Universe:", universe)
    
    # Test download for the first 5 symbols
    df_historical = download_historical_data(universe[:5], period="1y")
    print(df_historical.head())
