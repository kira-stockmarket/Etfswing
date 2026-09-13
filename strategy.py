import pandas as pd
import numpy as np

class CrossSectionalSwingEngine:
    def __init__(self, data_dict, initial_capital=1000000, max_tranches=4, max_hold_days=30):
        """
        data_dict: Dictionary mapping ticker symbols to pandas DataFrames (must contain 'Close')
        max_tranches: Maximum number of times to buy an ETF (1 initial + up to 3 average downs)
        max_hold_days: Maximum trading days to hold a position before a time-based exit
        """
        self.data = data_dict
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_tranches = max_tranches
        self.max_hold_days = max_hold_days
        
        # Rule: Daily amount to invest is Capital / 60
        self.trade_amount = initial_capital / 60
        
        # Tracks open trades. Format: 
        # { ticker: {'shares': float, 'avg_price': float, 'last_buy_price': float, 'tranches': int, 'days_held': int} }
        self.positions = {} 
        self.history = []
        
        # Align all dates across the ETF universe
        all_dates = pd.DatetimeIndex([])
        for df in self.data.values():
            all_dates = all_dates.union(df.index)
        self.dates = all_dates.sort_values()

    def run_backtest(self):
        print("Pre-computing 20 DMA and Distances...")
        dma_data = {}
        close_data = {}
        
        for ticker, df in self.data.items():
            df['20_DMA'] = df['Close'].rolling(window=20).mean()
            # Calculate how far the price has fallen from the 20 DMA
            df['Dist_DMA'] = (df['Close'] - df['20_DMA']) / df['20_DMA']
            dma_data[ticker] = df['Dist_DMA']
            close_data[ticker] = df['Close']
            
        dist_df = pd.DataFrame(dma_data)
        close_df = pd.DataFrame(close_data)
        
        print("Running daily simulation...")
        for date in self.dates:
            if date not in dist_df.index or date not in close_df.index:
                continue
                
            day_closes = close_df.loc[date]
            day_dists = dist_df.loc[date]
            
            # ---------------------------------------------------------
            # RULE 1: EXIT LOGIC (6% Profit Target OR Time-Based Stop)
            # ---------------------------------------------------------
            tickers_to_remove = []
            for ticker, pos in self.positions.items():
                current_price = day_closes.get(ticker, np.nan)
                if pd.isna(current_price): continue
                
                # Sell if 6% profit target is hit OR if max hold days is reached
                if (current_price >= pos['avg_price'] * 1.06) or (pos['days_held'] >= self.max_hold_days):
                    self.cash += pos['shares'] * current_price
                    tickers_to_remove.append(ticker)
                    
            for ticker in tickers_to_remove:
                del self.positions[ticker]
                
            # ---------------------------------------------------------
            # RULE 2: ENTRY LOGIC (Highest down from 20 DMA)
            # ---------------------------------------------------------
            # Drop NaNs and sort ascending (lowest negative value = highest down)
            valid_dists = day_dists.dropna().sort_values() 
            
            bought_today = False
            for ticker, dist in valid_dists.items():
                if bought_today: break # Rule: Buy exactly one ETF daily
                
                current_price = day_closes.get(ticker, np.nan)
                if pd.isna(current_price): continue
                
                # Ensure we have enough cash for the tranche
                if self.cash < self.trade_amount:
                    break
                    
                shares_to_buy = self.trade_amount / current_price
                
                if ticker not in self.positions:
                    # Not in portfolio -> Buy the highest down ETF
                    self.positions[ticker] = {
                        'shares': shares_to_buy,
                        'avg_price': current_price,
                        'last_buy_price': current_price,
                        'tranches': 1,      # Mark as the first tranche bought
                        'days_held': 0      # Initialize days held counter
                    }
                    self.cash -= self.trade_amount
                    bought_today = True
                    
                else:
                    # RULE 3: AVERAGING LOGIC (WITH TRANCHE CAP)
                    pos = self.positions[ticker]
                    
                    # Check if it fell 2.5% AND we haven't hit the max tranche limit
                    if (current_price <= pos['last_buy_price'] * 0.975) and (pos['tranches'] < self.max_tranches):
                        total_cost = (pos['shares'] * pos['avg_price']) + self.trade_amount
                        pos['shares'] += shares_to_buy
                        pos['avg_price'] = total_cost / pos['shares'] # Update average price
                        pos['last_buy_price'] = current_price         # Reset last buy price
                        pos['tranches'] += 1                          # Increment tranche count
                        self.cash -= self.trade_amount
                        bought_today = True
                        
                    # If it has maxed out its tranches, it skips buying and looks for the next ETF
                        
            # ---------------------------------------------------------
            # METRICS TRACKING & END OF DAY MAINTENANCE
            # ---------------------------------------------------------
            portfolio_value = self.cash
            for ticker, pos in self.positions.items():
                # Increment the hold time for all open positions at the end of the day
                pos['days_held'] += 1
                
                cp = day_closes.get(ticker, 0)
                if not pd.isna(cp):
                    portfolio_value += pos['shares'] * cp
                    
            self.history.append({
                'Date': date, 
                'Portfolio_Value': portfolio_value, 
                'Cash': self.cash,
                'Open_Positions': len(self.positions)
            })
            
        result_df = pd.DataFrame(self.history).set_index('Date')
        return result_df
