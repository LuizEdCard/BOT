#!/usr/bin/env python3
"""Script simplificado para importar histórico sem dependências complexas"""

import sqlite3
import requests
import hmac
import hashlib
import time
from datetime import datetime
from urllib.parse import urlencode

# Ler credenciais do .env
with open('config/.env', 'r') as f:
    for line in f:
        if line.startswith('BINANCE_API_KEY='):
            API_KEY = line.split('=')[1].strip().strip('"').strip("'")
        elif line.startswith('BINANCE_API_SECRET='):
            API_SECRET = line.split('=')[1].strip().strip('"').strip("'")

BASE_URL = 'https://api.binance.com'

def fazer_requisicao(endpoint, params=None):
    """Faz requisição assinada para a Binance"""
    params = params or {}
    params['timestamp'] = int(time.time() * 1000)

    query_string = urlencode(params)
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    params['signature'] = signature

    headers = {'X-MBX-APIKEY': API_KEY}
    response = requests.get(f"{BASE_URL}{endpoint}", params=params, headers=headers)
    response.raise_for_status()
    return response.json()

# Buscar histórico
print('🔍 Buscando histórico de ordens...')
ordens = fazer_requisicao('/api/v3/allOrders', {'symbol': 'ADAUSDT', 'limit': 100})
print(f'✅ Encontradas {len(ordens)} ordens\n')

# Filtrar apenas FILLED
ordens_filled = [o for o in ordens if o['status'] == 'FILLED']
print(f'✅ Ordens executadas: {len(ordens_filled)}\n')

# Separar por dia
ontem = {}
hoje = {}
outras = {}

for ordem in ordens_filled:
    timestamp = datetime.fromtimestamp(ordem['time'] / 1000)
    data = timestamp.strftime('%Y-%m-%d')

    if data == '2025-10-10':
        ontem[ordem['orderId']] = ordem
    elif data == '2025-10-11':
        hoje[ordem['orderId']] = ordem
    else:
        outras[ordem['orderId']] = ordem

print(f"📅 Ordens de 2025-10-10 (ontem): {len(ontem)}")
print(f"📅 Ordens de 2025-10-11 (hoje): {len(hoje)}")
print(f"📅 Outras datas: {len(outras)}\n")

# Calcular preço médio de ONTEM
compras_ontem = [o for o in ontem.values() if o['side'] == 'BUY']
vendas_ontem = [o for o in ontem.values() if o['side'] == 'SELL']

if compras_ontem:
    print("=" * 90)
    print("COMPRAS DE ONTEM (2025-10-10):")
    print("=" * 90)
    print(f"{'Hora':<10} {'Qtd ADA':<12} {'Preço':<14} {'Total USDT':<14} {'Order ID':<15}")
    print("-" * 90)

    total_ada = 0
    total_usdt = 0

    for ordem in sorted(compras_ontem, key=lambda x: x['time']):
        timestamp = datetime.fromtimestamp(ordem['time'] / 1000)
        hora = timestamp.strftime('%H:%M:%S')
        qtd = float(ordem['executedQty'])
        preco = float(ordem['cummulativeQuoteQty']) / qtd if qtd > 0 else 0
        total = float(ordem['cummulativeQuoteQty'])

        print(f"{hora:<10} {qtd:<12.1f} ${preco:<13.6f} ${total:<13.2f} {ordem['orderId']:<15}")

        total_ada += qtd
        total_usdt += total

    preco_medio = total_usdt / total_ada if total_ada > 0 else 0

    print("-" * 90)
    print(f"{'TOTAIS:':<10} {total_ada:<12.1f} {'':<14} ${total_usdt:<13.2f}")
    print("=" * 90)
    print(f"\n💰 PREÇO MÉDIO DE COMPRA (ONTEM): ${preco_medio:.6f}")
    print(f"📦 TOTAL COMPRADO: {total_ada:.1f} ADA")
    print(f"💵 VALOR INVESTIDO: ${total_usdt:.2f} USDT\n")

if vendas_ontem:
    print(f"🔴 VENDAS DE ONTEM: {len(vendas_ontem)}")
    total_vendido_ada = 0
    total_vendido_usdt = 0
    for ordem in vendas_ontem:
        qtd = float(ordem['executedQty'])
        total = float(ordem['cummulativeQuoteQty'])
        total_vendido_ada += qtd
        total_vendido_usdt += total
    print(f"   Total vendido: {total_vendido_ada:.1f} ADA por ${total_vendido_usdt:.2f} USDT\n")

print("=" * 90)
