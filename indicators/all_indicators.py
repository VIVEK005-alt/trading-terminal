# indicators/all_indicators.py
import pandas as pd
import pandas_ta as ta

def calculate_all_indicators(df):
    """
    Yeh function global usage volumes ke hisaab se top indicators (MACD, Bollinger Bands, Stochastic, VWAP) calculate karta hai.
    """
    if df is None or df.empty:
        return df

    # 1. MACD (Moving Average Convergence Divergence)
    macd = ta.macd(df['close'])
    if macd is not None and not macd.empty:
        df = pd.concat([df, macd], axis=1)

    # 2. Bollinger Bands
    bbands = ta.bbands(df['close'], length=20, std=2)
    if bbands is not None and not bbands.empty:
        df = pd.concat([df, bbands], axis=1)

    # 3. Stochastic Oscillator
    stoch = ta.stoch(df['high'], df['low'], df['close'])
    if stoch is not None and not stoch.empty:
        df = pd.concat([df, stoch], axis=1)

    # 4. VWAP (Volume Weighted Average Price) agar volume available ho
    if 'volume' in df.columns:
        df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])

    return df
