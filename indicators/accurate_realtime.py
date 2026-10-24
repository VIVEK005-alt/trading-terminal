# indicators/accurate_realtime.py
import pandas as pd
import pandas_ta as ta

def calculate_realtime_indicators(df):
    """
    Yeh function market data par sabse sateek aur real-time technical indicators apply karta hai.
    """
    if df is None or df.empty:
        return df

    # Exponential Moving Averages (EMA 9 & 21)
    df['EMA_9'] = ta.ema(df['close'], length=9)
    df['EMA_21'] = ta.ema(df['close'], length=21)
    
    # Relative Strength Index (RSI 14)
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    # Supertrend for precise trend direction
    supertrend = ta.supertrend(df['high'], df['low'], df['close'], length=7, multiplier=3)
    if supertrend is not None and not supertrend.empty:
        df = pd.concat([df, supertrend], axis=1)
        
    return df
