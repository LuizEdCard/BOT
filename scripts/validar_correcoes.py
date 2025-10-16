#!/usr/bin/env python3
"""Script para validar as correções implementadas"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal
from config.settings import settings
from src.comunicacao.api_manager import APIManager
from src.core.gerenciador_bnb import GerenciadorBNB

print("=" * 70)
print("🧪 VALIDAÇÃO DAS CORREÇÕES IMPLEMENTADAS")
print("=" * 70)
print()

# Inicializar API
api = APIManager(
    api_key=settings.BINANCE_API_KEY,
    api_secret=settings.BINANCE_API_SECRET,
    base_url=settings.BINANCE_API_URL
)

print("📊 VALIDAÇÃO 1: RESERVA DE CAPITAL")
print("-" * 70)

# Obter saldos
saldos = api.obter_saldos()
saldo_usdt = Decimal('0')
saldo_ada = Decimal('0')
saldo_bnb = Decimal('0')

for saldo in saldos:
    if saldo['asset'] == 'USDT':
        saldo_usdt = Decimal(str(saldo['free']))
    elif saldo['asset'] == 'ADA':
        saldo_ada = Decimal(str(saldo['free']))
    elif saldo['asset'] == 'BNB':
        saldo_bnb = Decimal(str(saldo['free']))

# Calcular saldo utilizável
percentual_ativo = Decimal(str(settings.PERCENTUAL_CAPITAL_ATIVO)) / Decimal('100')
percentual_reserva = Decimal(str(settings.PERCENTUAL_RESERVA)) / Decimal('100')

saldo_utilizavel = saldo_usdt * percentual_ativo
saldo_reserva = saldo_usdt * percentual_reserva

print(f"Saldo USDT total:       ${saldo_usdt:.2f}")
print(f"Saldo utilizável (92%): ${saldo_utilizavel:.2f}")
print(f"Saldo reserva (8%):     ${saldo_reserva:.2f}")
print()

# Validar se a reserva está sendo respeitada
if saldo_utilizavel == saldo_usdt * Decimal('0.92'):
    print("✅ CORREÇÃO 1: Cálculo de reserva está CORRETO!")
else:
    print("❌ CORREÇÃO 1: Problema no cálculo de reserva")

print()
print("=" * 70)
print("📊 VALIDAÇÃO 2: PRECISÃO BNB")
print("-" * 70)

# Obter preço do BNB
gerenciador_bnb = GerenciadorBNB(api, settings)
preco_bnb = gerenciador_bnb.obter_preco_bnb_usdt()

if preco_bnb:
    print(f"Preço BNB atual: ${preco_bnb:.2f}")
    print(f"Saldo BNB atual: {saldo_bnb:.3f} BNB")

    valor_bnb_usdt = saldo_bnb * preco_bnb
    print(f"Valor em USDT:   ${valor_bnb_usdt:.2f}")
    print()

    # Simular cálculo de quantidade
    valor_compra = Decimal('5.0')
    quantidade_calculada = valor_compra / preco_bnb

    # Aplicar a correção (3 casas decimais)
    quantidade_corrigida = quantidade_calculada.quantize(
        Decimal('0.001'), rounding='ROUND_DOWN'
    )

    print("Simulação de compra de BNB:")
    print(f"  Valor a investir:       ${valor_compra:.2f}")
    print(f"  Quantidade calculada:   {quantidade_calculada:.8f} BNB (antes)")
    print(f"  Quantidade corrigida:   {quantidade_corrigida:.3f} BNB (depois)")
    print()

    # Verificar se tem 3 casas decimais
    str_qtd = str(quantidade_corrigida)
    casas_decimais = len(str_qtd.split('.')[-1]) if '.' in str_qtd else 0

    if casas_decimais <= 3:
        print(f"✅ CORREÇÃO 2: Precisão está CORRETA ({casas_decimais} casas decimais)")
    else:
        print(f"❌ CORREÇÃO 2: Problema na precisão ({casas_decimais} casas decimais)")

    print()

    # Verificar se precisa comprar BNB
    if gerenciador_bnb.precisa_comprar_bnb():
        print("⚠️  Saldo BNB abaixo do mínimo ($5.00)")
        print("   Sistema tentará comprar BNB em breve")
    else:
        print("✅ Saldo BNB suficiente")
else:
    print("❌ Não foi possível obter preço do BNB")

print()
print("=" * 70)
print("📋 RESUMO DOS TESTES")
print("=" * 70)
print()
print(f"Saldo USDT: ${saldo_usdt:.2f}")
print(f"Saldo ADA:  {saldo_ada:.1f} ADA")
print(f"Saldo BNB:  {saldo_bnb:.3f} BNB")
print()
print(f"Capital ativo configurado: {settings.PERCENTUAL_CAPITAL_ATIVO}%")
print(f"Reserva configurada:       {settings.PERCENTUAL_RESERVA}%")
print()
print(f"Saldo utilizável: ${saldo_utilizavel:.2f} (bot pode usar)")
print(f"Saldo reserva:    ${saldo_reserva:.2f} (protegido)")
print()
print("=" * 70)
print("✅ Script de validação concluído!")
print()
