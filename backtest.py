import pandas as pd
import matplotlib.pyplot as plt
from data_loader import get_trading_universe, download_historical_data
from strategy import CrossSectionalSwingEngine

def calculate_metrics(equity_curve):
    """Calculates basic performance metrics from the equity curve."""
    initial = equity_curve['Portfolio_Value'].iloc[0]
    final = equity_curve['Portfolio_Value'].iloc[-1]
    total_return = ((final - initial) / initial) * 100
    
    # Calculate Drawdown
    peak = equity_curve['Portfolio_Value'].cummax()
    drawdown = (equity_curve['Portfolio_Value'] - peak) / peak
    max_drawdown = drawdown.min() * 100
    
    print("\n" + "="*30)
    print("BACKTEST RESULTS")
    print("="*30)
    print(f"Initial Capital:  ₹{initial:,.2f}")
    print(f"Final Capital:    ₹{final:,.2f}")
    print(f"Total Return:     {total_return:.2f}%")
    print(f"Max Drawdown:     {max_drawdown:.2f}%")
    print("="*30)

def main():
    # 1. Load the pristine universe created from the Excel file
    universe = get_trading_universe("Filtered_Best_ETFs_For_Trading.xlsx")
    
    # 2. Download historical data
    print(f"Fetching data for {len(universe)} ETFs...")
    raw_data = download_historical_data(universe, period="3y", interval="1d")
    
    # 3. Format data dictionary for the engine (Updated to be version-proof)
    data_dict = {}
    for ticker in universe:
        try:
            # Handle different versions of yfinance MultiIndex output safely
            if isinstance(raw_data.columns, pd.MultiIndex):
                # Check if Tickers are in the first level (group_by='ticker')
                if ticker in raw_data.columns.get_level_values(0):
                    df = raw_data[ticker].copy()
                # Check if Tickers are in the second level (default)
                elif ticker in raw_data.columns.get_level_values(1):
                    df = raw_data.xs(ticker, level=1, axis=1).copy()
                else:
                    continue
            else:
                # Fallback if only one ticker was loaded
                df = raw_data.copy()
            
            # Drop days where the market was closed or data is missing
            if 'Close' in df.columns:
                df = df.dropna(subset=['Close'])
                
            # Ensure we have enough data for the 20 DMA
            if not df.empty and len(df) > 50: 
                data_dict[ticker] = df
                
        except Exception as e:
            pass # Skip tickers that failed to download or format properly
            
    # 4. Initialize and Run Strategy
    print(f"Valid ETFs loaded: {len(data_dict)}")
    engine = CrossSectionalSwingEngine(data_dict, initial_capital=100000)
    equity_curve = engine.run_backtest()
    
    # 5. Output Metrics and Plot
    if not equity_curve.empty:
        calculate_metrics(equity_curve)
        
        # Plotting
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve.index, equity_curve['Portfolio_Value'], label='Strategy Equity')
        plt.title('ETF Swing Strategy (20 DMA / 6% Target / 2.5% Avg)')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value')
        plt.legend()
        plt.grid(True)
        # plt.show() # Uncomment if running locally. Keep commented for GitHub actions.
        plt.savefig("equity_curve.png") # Saves the plot as an image in the action runner
        print("Plot saved as equity_curve.png")
    else:
        print("Error: Equity curve is empty. Not enough data to run the backtest.")

if __name__ == "__main__":
    main()
