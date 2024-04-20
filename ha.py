import ta
import os
import time
from datetime import datetime
from keys import api, secret
import numpy as np
import talib
from binance.client import Client
from binance.enums import *

# Binance API keys
api_key = api
api_secret = secret

# Symbols to trade with respective quantities and signals
symbol_data = [
    {'symbol': 'BTCUSDT', 'quantity': 0.003, 'buy_signal': True, 'sell_signal': True},  # Example for BTCUSDT
    {'symbol': 'ETHUSDT', 'quantity': 0.050, 'buy_signal': True, 'sell_signal': True},  # Example for ETHUSDT
    # Add more symbols as needed
]

# Initialize Binance client
client = Client(api_key, api_secret)

# Constants
interval = Client.KLINE_INTERVAL_15MINUTE
ema_period = 21
heikin_ashi_period = 14
supertrend_period = 10
supertrend_multiplier = 3.0

# Function to get Heikin Ashi candles
def get_heikin_ashi_candles(klines):
    heikin_ashi_candles = []
    for kline in klines:
        heikin_ashi = {
            'timestamp': kline[0],
            'open': (float(kline[1]) + float(kline[2])) / 2,
            'close': (float(kline[1]) + float(kline[2]) + float(kline[3]) + float(kline[4])) / 4,
            'high': max(float(kline[2]), float(kline[4])),
            'low': min(float(kline[1]), float(kline[3]))
        }
        heikin_ashi_candles.append(heikin_ashi)
    return heikin_ashi_candles

# Function to calculate SuperTrend indicator
def calculate_supertrend(candles, period, multiplier):
    high = np.array([candle['high'] for candle in candles])
    low = np.array([candle['low'] for candle in candles])
    close = np.array([candle['close'] for candle in candles])
    
    atr = talib.ATR(high, low, close, timeperiod=period)
    hl2 = (high + low) / 2
    
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    uptrend = []
    for i in range(len(candles)):
        if i == 0:
            uptrend.append(True)
        elif close[i - 1] > upper_band[i - 1]:
            uptrend.append(True)
        elif close[i - 1] < lower_band[i - 1]:
            uptrend.append(False)
        else:
            uptrend.append(uptrend[i - 1])
    
    return uptrend, upper_band, lower_band

# Function to get current position
def get_position(symbol):
    try:
        position = client.futures_position_information(symbol=symbol)
        for pos in position:
            if pos['symbol'] == symbol:
                return float(pos['positionAmt'])
        return 0.0
    except Exception as e:
        print("Error fetching position:", e)
        return 0.0

# Function to place a long order
def place_long_order(symbol, quantity):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        print("Long order placed for", symbol, ":", order)
    except Exception as e:
        print("Error placing long order for", symbol, ":", e)

# Function to place a short order
def place_short_order(symbol, quantity):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        print("Short order placed for", symbol, ":", order)
    except Exception as e:
        print("Error placing short order for", symbol, ":", e)

# Function to close long position
def close_long_position(symbol):
    try:
        position = get_position(symbol)
        if position > 0:
            place_short_order(symbol, abs(position))
    except Exception as e:
        print("Error closing long position for", symbol, ":", e)

# Function to close short position
def close_short_position(symbol):
    try:
        position = get_position(symbol)
        if position < 0:
            place_long_order(symbol, abs(position))
    except Exception as e:
        print("Error closing short position for", symbol, ":", e)

# Main function
def main():
    while True:
        try:
            for symbol_info in symbol_data:
                symbol = symbol_info['symbol']
                buy_signal = symbol_info['buy_signal']
                sell_signal = symbol_info['sell_signal']
                quantity = symbol_info['quantity']
                
                position = get_position(symbol)
                
                # Get historical kline data
                klines = client.futures_klines(symbol=symbol, interval=interval, limit=heikin_ashi_period + ema_period)

                # Extract Heikin Ashi candles
                heikin_ashi_candles = get_heikin_ashi_candles(klines)

                # Calculate EMA
                close_prices = np.array([candle['close'] for candle in heikin_ashi_candles])
                ema = talib.EMA(close_prices, timeperiod=ema_period)

                # Calculate SuperTrend
                uptrend, upper_band, lower_band = calculate_supertrend(heikin_ashi_candles, supertrend_period, supertrend_multiplier)

                # Latest Heikin Ashi candle
                latest_heikin_ashi = heikin_ashi_candles[-1]

                # Buy signal if close price crosses above EMA
                if buy_signal and latest_heikin_ashi['close'] > ema[-1] and uptrend[-1]:
                    if position <= 0:
                        close_short_position(symbol)
                        place_long_order(symbol, quantity)
                        print("Buy signal detected for", symbol, "- Opening long position and Close short position")

                # Sell signal if close price crosses below EMA
                elif sell_signal and latest_heikin_ashi['close'] < ema[-1] and not uptrend[-1]:
                    if position >= 0:
                        close_long_position(symbol)
                        place_short_order(symbol, quantity)
                        print("Sell signal detected for", symbol, "- Opening short position and Close long position")
                
                # Print current position
                print('=================================================================================================')
                if position > 0:
                    print("Long position for", symbol, ":", position)
                elif position < 0:
                    print("Short position for", symbol, ":", position)
                print('=================================================================================================')
                # Sleep for some time
                time.sleep(60)  # Sleep for 1 minute
        except Exception as e:
            print("Error occurred:", e)

if __name__ == "__main__":
    main()
