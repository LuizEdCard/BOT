#!/usr/bin/env python3
"""Debug de ordem USDT/BRL"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import requests
import hashlib
import hmac
import time
from urllib.parse import urlencode
from config.settings import settings

# Parâmetros
api_key = settings.BINANCE_API_KEY
api_secret = settings.BINANCE_API_SECRET
base_url = settings.BINANCE_API_URL

# Testar informações do símbolo primeiro
print("=" * 60)
print("1. Verificando informações do símbolo USDTBRL...")
print("=" * 60)

try:
    response = requests.get(
        f"{base_url}/api/v3/exchangeInfo",
        params={'symbol': 'USDTBRL'},
        timeout=30
    )
    info = response.json()

    if 'symbols' in info and info['symbols']:
        symbol_info = info['symbols'][0]
        print(f"✅ Símbolo: {symbol_info['symbol']}")
        print(f"   Status: {symbol_info['status']}")
        print(f"   Base: {symbol_info['baseAsset']}")
        print(f"   Quote: {symbol_info['quoteAsset']}")

        print("\n   Filtros:")
        for filter_info in symbol_info['filters']:
            if filter_info['filterType'] == 'LOT_SIZE':
                print(f"   - LOT_SIZE:")
                print(f"     Min Qty: {filter_info['minQty']}")
                print(f"     Max Qty: {filter_info['maxQty']}")
                print(f"     Step Size: {filter_info['stepSize']}")
            elif filter_info['filterType'] == 'MIN_NOTIONAL':
                print(f"   - MIN_NOTIONAL:")
                print(f"     Min Notional: {filter_info['minNotional']}")
except Exception as e:
    print(f"❌ Erro: {e}")

# Testar ordem
print("\n" + "=" * 60)
print("2. Tentando criar ordem BUY MARKET 17.91 USDTBRL...")
print("=" * 60)

def criar_assinatura(query_string: str) -> str:
    return hmac.new(
        api_secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

params = {
    'symbol': 'USDTBRL',
    'side': 'BUY',
    'type': 'MARKET',
    'quantity': 17.91,
    'timestamp': int(time.time() * 1000)
}

query_string = urlencode(params)
params['signature'] = criar_assinatura(query_string)

try:
    response = requests.post(
        f"{base_url}/api/v3/order",
        params=params,
        headers={'X-MBX-APIKEY': api_key},
        timeout=30
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 200:
        print("✅ Ordem executada com sucesso!")
        print(response.json())
    else:
        print("❌ Erro na ordem:")
        try:
            erro = response.json()
            print(f"   Code: {erro.get('code')}")
            print(f"   Msg: {erro.get('msg')}")
        except:
            print(f"   {response.text}")

except Exception as e:
    print(f"❌ Exceção: {e}")
