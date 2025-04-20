import os
import time
import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime
from binance.client import Client
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange

# 🔐 Binance API bilgileri
API_KEY = 'abw8VxsDeHJ0o7yFdeBzpgStA31dr5B7fOkKcaYnFPHVfGKCiYZYDV9Mm8I8ey0d'
API_SECRET = 'S8lm61McWnT6IpS7g4TYKMaDHGSLMwVrZxWUf4bYBLbULAZwVieNn7isBlsmZuQ9'
client = Client(API_KEY, API_SECRET)

# 🔐 Telegram bilgileri
TELEGRAM_TOKEN = '7720529606:AAG5dJ4DvCuaJ9G_LFLRUE51C-JtYZMbqDY'
CHAT_ID = None  # Otomatik alınır

# Ayarlar
symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
interval = '1h'
log_file = 'log.csv'
leverage = 15
test_mode = False  # True yaparsan geçmişi test eder

def get_chat_id():
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'
    r = requests.get(url).json()
    try:
        return r['result'][-1]['message']['chat']['id']
    except:
        return None

def send_message(text):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': text}
    requests.post(url, data=data)

def send_photo(path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(path, 'rb') as photo:
        data = {'chat_id': CHAT_ID}
        requests.post(url, files={'photo': photo}, data=data)

def get_data(symbol):
    candles = client.get_klines(symbol=symbol, interval=interval, limit=100)
    df = pd.DataFrame(candles, columns=['time','o','h','l','c','v','ct','q','n','tq','tqv','i'])
    df['close'] = df['c'].astype(float)
    df['high'] = df['h'].astype(float)
    df['low'] = df['l'].astype(float)
    return df

def apply_indicators(df):
    df['rsi'] = RSIIndicator(df['close']).rsi()
    macd = MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    bb = BollingerBands(df['close'])
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['adx'] = ADXIndicator(df['high'], df['low'], df['close']).adx()
    df['ema200'] = EMAIndicator(df['close'], window=200).ema_indicator()
    df['atr'] = AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
    return df

def plot_graph(df, symbol):
    plt.figure(figsize=(8,4))
    plt.plot(df['close'][-50:], label='Price')
    plt.plot(df['ema200'][-50:], label='EMA200')
    plt.title(f'{symbol} - Son 50 mum')
    plt.legend()
    plt.tight_layout()
    filename = f'{symbol}_chart.png'
    plt.savefig(filename)
    plt.close()
    return filename

def check_signal(df, symbol):
    latest = df.iloc[-1]
    price = latest['close']
    atr = latest['atr']
    adx = latest['adx']
    tp = sl = rr = None
    trend = 'YOK'
    direction = None

    if adx < 20: return None

    if price > latest['ema200']:
        trend = 'YUKARI'
        if latest['rsi'] > 60 and latest['macd'] > latest['macd_signal'] and price > latest['bb_upper']:
            tp = round(price + 2*atr, 2)
            sl = round(price - 1.3*atr, 2)
            rr = round((tp - price)/(price - sl), 2)
            if rr >= 1.5:
                direction = 'BUY'
    elif price < latest['ema200']:
        trend = 'AŞAĞI'
        if latest['rsi'] < 40 and latest['macd'] < latest['macd_signal'] and price < latest['bb_lower']:
            tp = round(price - 2*atr, 2)
            sl = round(price + 1.3*atr, 2)
            rr = round((price - tp)/(sl - price), 2)
            if rr >= 1.5:
                direction = 'SELL'

    if direction:
        return {
            'symbol': symbol,
            'entry': round(price, 2),
            'tp': tp,
            'sl': sl,
            'rr': rr,
            'trend': trend,
            'momentum': round(adx,1),
            'direction': direction
        }
    return None

def log_signal(sig):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    data = sig.copy()
    data['time'] = now
    df = pd.DataFrame([data])
    if not os.path.exists(log_file):
        df.to_csv(log_file, index=False)
    else:
        df.to_csv(log_file, mode='a', header=False, index=False)

def run_bot():
    global CHAT_ID
    CHAT_ID = get_chat_id()
    if not CHAT_ID:
        print("Lütfen Telegram botunu başlat (/start yaz) ve tekrar dene.")
        return

    while True:
        send_message("🔍 Yeni tarama başladı...")
        for symbol in symbols:
            df = get_data(symbol)
            df = apply_indicators(df)
            signal = check_signal(df, symbol)
            if signal:
                log_signal(signal)
                msg = f"{signal['symbol']} 💹 {signal['direction']} | Entry: {signal['entry']} | TP: {signal['tp']} | SL: {signal['sl']} | RR: {signal['rr']}:1"
                send_message(msg)
                chart_path = plot_graph(df, symbol)
                send_photo(chart_path)
                print(f"{symbol}: Sinyal gönderildi.")
            else:
                print(f"{symbol}: Sinyal yok.")
        time.sleep(900)

if not test_mode:
    run_bot()
else:
    print("📊 Test modu aktif. Kod simülasyona göre çalışıyor...")
def run_bot():
    global CHAT_ID
    CHAT_ID = get_chat_id()
    if not CHAT_ID:
        print("Telegram botunu başlat (/start yaz) ve tekrar dene.")
        return

    while True:
        try:
            send_message("🔍 Yeni tarama başladı...")
            for symbol in symbols:
                df = get_data(symbol)
                df = apply_indicators(df)
                signal = check_signal(df, symbol)
                if signal:
                    log_signal(signal)
                    msg = f"{signal['symbol']} 💹 {signal['direction']} | Entry: {signal['entry']} | TP: {signal['tp']} | SL: {signal['sl']} | RR: {signal['rr']}:1"
                    send_message(msg)
                    chart_path = plot_graph(df, symbol)
                    send_photo(chart_path)
                    print(f"{symbol}: Sinyal gönderildi.")
                else:
                    print(f"{symbol}: Sinyal yok.")
            print("Tarama bitti. 15 dakika uykuya geçiliyor...\n")
            time.sleep(900)

        except Exception as e:
            print(f"Bir hata oluştu: {e}")
            send_message(f"❌ Bot hata verdi: {str(e)}")
            time.sleep(900)
