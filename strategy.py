import pandas as pd
import numpy as np

class CrossSectionalSwingEngine:
    def __init__(self, data_dict, initial_capital=100000, max_tranches=4, max_hold_days=90):
        self.data = data_dict
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_tranches = max_tranches
        self.max_hold_days = max_hold_days
        self.trade_amount = initial_capital / 60
        
        self.positions = {} 
        self.history = []
        self.completed_trades = [] # <--- NEW: Tracks completed trades
        
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
            
            # --- RULE 1: EXIT LOGIC ---
            tickers_to_remove = []
            for ticker, pos in self.positions.items():
                current_price = day_closes.get(ticker, np.nan)
                if pd.isna(current_price): continue
                
                is_profit_target = current_price >= pos['avg_price'] * 1.06
                is_time_stop = pos['days_held'] >= self.max_hold_days
                
                if is_profit_target or is_time_stop:
                    # Record the completed trade
                    pnl = (current_price - pos['avg_price']) * pos['shares']
                    roi = ((current_price - pos['avg_price']) / pos['avg_price']) * 100
                    exit_reason = "6% Target" if is_profit_target else "30-Day Stop"
                    
                    self.completed_trades.append({
                        'Entry Date': pos['first_buy_date'].strftime('%Y-%m-%d'),
                        'Exit Date': date.strftime('%Y-%m-%d'),
                        'Symbol': ticker,
                        'Shares': round(pos['shares'], 4),
                        'Avg Entry Price': round(pos['avg_price'], 2),
                        'Exit Price': round(current_price, 2),
                        'Gross PnL (₹)': round(pnl, 2),
                        'ROI (%)': round(roi, 2),
                        'Tranches': pos['tranches'],
                        'Exit Reason': exit_reason
                    })
                    
                    self.cash += pos['shares'] * current_price
                    tickers_to_remove.append(ticker)
                    
            for ticker in tickers_to_remove:
                del self.positions[ticker]
                
            # --- RULE 2: ENTRY LOGIC ---
            valid_dists = day_dists.dropna().sort_values() 
            
            bought_today = False
            for ticker, dist in valid_dists.items():
                if bought_today: break 
                
                current_price = day_closes.get(ticker, np.nan)
                if pd.isna(current_price): continue
                
                if self.cash < self.trade_amount:
                    break
                    
                shares_to_buy = self.trade_amount / current_price
                
                if ticker not in self.positions:
                    self.positions[ticker] = {
                        'shares': shares_to_buy,
                        'avg_price': current_price,
                        'last_buy_price': current_price,
                        'tranches': 1,      
                        'days_held': 0,
                        'first_buy_date': date # <--- NEW: Track when we first bought it
                    }
                    self.cash -= self.trade_amount
                    bought_today = True
                    
                else:
                    # RULE 3: AVERAGING LOGIC
                    pos = self.positions[ticker]
                    if (current_price <= pos['last_buy_price'] * 0.975) and (pos['tranches'] < self.max_tranches):
                        total_cost = (pos['shares'] * pos['avg_price']) + self.trade_amount
                        pos['shares'] += shares_to_buy
                        pos['avg_price'] = total_cost / pos['shares'] 
                        pos['last_buy_price'] = current_price         
                        pos['tranches'] += 1                          
                        self.cash -= self.trade_amount
                        bought_today = True
                        
            # --- METRICS TRACKING ---
            portfolio_value = self.cash
            for ticker, pos in self.positions.items():
                pos['days_held'] += 1
                cp = day_closes.get(ticker, 0)
                if not pd.isna(cp):
                    portfolio_value += pos['shares'] * cp
                    
            self.history.append({
                'Date': date, 
                'Portfolio_Value': portfolio_value, 
                'Cash': self.cash
            })
            
        equity_df = pd.DataFrame(self.history).set_index('Date')
        trades_df = pd.DataFrame(self.completed_trades)
        
        # Return both the equity curve AND the trade log
        return equity_df, trades_df
