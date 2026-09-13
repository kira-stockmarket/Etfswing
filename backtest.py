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
    
    # 2. Download historical data (e.g., last 3 years)
    print("Fetching data...")
    raw_data = download_historical_data(universe, period="3y", interval="1d")
    
    # 3. Format data dictionary for the engine
    data_dict = {}
    for ticker in universe:
        # Extract the specific ticker's data, drop rows with missing closing prices
        df = raw_data.xs(ticker, level='ticker', axis=1).dropna(subset=['Close'])
        if not df.empty and len(df) > 50: # Ensure we have enough data for 20 DMA
            data_dict[ticker] = df
            
    # 4. Initialize and Run Strategy
    engine = CrossSectionalSwingEngine(data_dict, initial_capital=100000)
    equity_curve = engine.run_backtest()
    
    # 5. Output Metrics and Plot
    calculate_metrics(equity_curve)
    
    # Plotting
    plt.figure(figsize=(12, 6))
    plt.plot(equity_curve.index, equity_curve['Portfolio_Value'], label='Strategy Equity')
    plt.title('ETF Swing Strategy (20 DMA / 6% Target / 2.5% Avg)')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()
