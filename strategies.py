import pandas as pd

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df['EMA5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['SMA50'] = df['close'].rolling(50).mean()
    df['SMA200'] = df['close'].rolling(200).mean()
    df['STD20'] = df['close'].rolling(20).std()
    df['UpperBB'] = df['close'].rolling(20).mean() + 2 * df['STD20']
    df['LowerBB'] = df['close'].rolling(20).mean() - 2 * df['STD20']
    
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['SignalLine'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df.dropna()

def get_signal(df: pd.DataFrame) -> dict:
    df = calculate_indicators(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # === STRATEGY AGREEMENT CHECK ===
    conditions_buy = [
        last['EMA5'] > last['EMA20'] and last['close'] > last['EMA5'],  # EMA crossover
        last['EMA50'] > last['EMA200'],                                 # Trend
        last['close'] < last['LowerBB'],                                # Bollinger low
        last['RSI'] < 30,                                               # RSI oversold
        prev['MACD'] < prev['SignalLine'] and last['MACD'] > last['SignalLine']  # MACD cross up
    ]
    
    conditions_sell = [
        last['EMA5'] < last['EMA20'] and last['close'] < last['EMA5'],  # EMA crossover down
        last['EMA50'] < last['EMA200'],                                 # Down trend
        last['close'] > last['UpperBB'],                                # Bollinger high
        last['RSI'] > 70,                                               # RSI overbought
        prev['MACD'] > prev['SignalLine'] and last['MACD'] < last['SignalLine']  # MACD cross down
    ]

    if all(conditions_buy):
        return {
            "direction": "BUY",
            "confidence": 100,
            "strategies": ["EMA Crossover", "Bull Trend", "Bollinger Breakout Down", "RSI Oversold", "MACD Bull"]
        }
    elif all(conditions_sell):
        return {
            "direction": "SELL",
            "confidence": 100,
            "strategies": ["EMA Crossdown", "Bear Trend", "Bollinger Breakout Up", "RSI Overbought", "MACD Bear"]
        }

    return None
