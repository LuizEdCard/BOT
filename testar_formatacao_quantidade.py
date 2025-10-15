#!/usr/bin/env python3
"""
Script de teste para validar formatação de quantidade nas ordens
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal

print("=" * 70)
print("TESTE DE FORMATAÇÃO DE QUANTIDADE PARA BINANCE")
print("=" * 70)
print()

# Simular diferentes quantidades que o bot pode calcular
test_cases = [
    Decimal('7.0'),
    Decimal('6.5'),
    Decimal('13.8'),
    Decimal('20.1'),
    Decimal('28.6'),
    Decimal('38.0'),
    Decimal('50.3'),
    Decimal('55.7'),
    Decimal('91.8') * Decimal('0.05'),  # 5% de 91.8 = 4.59
    Decimal('130.5') * Decimal('0.05'), # 5% de 130.5 = 6.525
]

print("Cenários de teste (step size = 0.1):")
print()

for i, quantidade in enumerate(test_cases, 1):
    # Arredondamento ATUAL do bot (linha 467 em bot_trading.py)
    quantidade_arredondada = (quantidade * Decimal('10')).quantize(
        Decimal('1'), rounding='ROUND_DOWN'
    ) / Decimal('10')

    # Formatação CORRIGIDA para API
    quantidade_formatada = f"{float(quantidade_arredondada):.1f}"

    # Validar se é múltiplo de 0.1
    valor_decimal = float(quantidade_formatada)
    eh_multiplo = (valor_decimal * 10) % 1 == 0

    status = "✅" if eh_multiplo else "❌"

    print(f"Teste {i}:")
    print(f"  Entrada:           {quantidade}")
    print(f"  Arredondado:       {quantidade_arredondada}")
    print(f"  Formatado API:     {quantidade_formatada}")
    print(f"  Múltiplo de 0.1:   {status} {eh_multiplo}")
    print()

print("=" * 70)
print("VALIDAÇÃO DOS FILTROS BINANCE")
print("=" * 70)
print()

# Filtros reais da Binance
LOT_SIZE_MIN = Decimal('0.10000000')
LOT_SIZE_MAX = Decimal('900000.00000000')
LOT_SIZE_STEP = Decimal('0.10000000')
MIN_NOTIONAL = Decimal('5.00000000')

print(f"LOT_SIZE:")
print(f"  minQty:    {LOT_SIZE_MIN}")
print(f"  maxQty:    {LOT_SIZE_MAX}")
print(f"  stepSize:  {LOT_SIZE_STEP}")
print()
print(f"NOTIONAL:")
print(f"  minNotional: {MIN_NOTIONAL}")
print()

# Testar validação completa
print("=" * 70)
print("VALIDAÇÃO COMPLETA (Quantidade + Valor Mínimo)")
print("=" * 70)
print()

preco_exemplo = Decimal('0.7140')  # Preço atual aproximado

for i, quantidade in enumerate(test_cases, 1):
    # Arredondamento
    quantidade_arredondada = (quantidade * Decimal('10')).quantize(
        Decimal('1'), rounding='ROUND_DOWN'
    ) / Decimal('10')

    # Formatar para API
    quantidade_formatada = f"{float(quantidade_arredondada):.1f}"
    quantidade_final = Decimal(quantidade_formatada)

    # Calcular valor da ordem
    valor_ordem = quantidade_final * preco_exemplo

    # Validações
    valida_min = quantidade_final >= LOT_SIZE_MIN
    valida_max = quantidade_final <= LOT_SIZE_MAX
    valida_step = (quantidade_final / LOT_SIZE_STEP) % 1 == 0
    valida_valor = valor_ordem >= MIN_NOTIONAL

    todas_validacoes = valida_min and valida_max and valida_step and valida_valor

    status = "✅ ORDEM VÁLIDA" if todas_validacoes else "❌ ORDEM INVÁLIDA"

    print(f"Teste {i}: {quantidade_formatada} ADA × ${preco_exemplo} = ${valor_ordem:.2f}")
    print(f"  {status}")

    if not todas_validacoes:
        if not valida_min:
            print(f"    ❌ Quantidade abaixo do mínimo ({LOT_SIZE_MIN})")
        if not valida_step:
            print(f"    ❌ Não é múltiplo de stepSize ({LOT_SIZE_STEP})")
        if not valida_valor:
            print(f"    ❌ Valor abaixo do mínimo (${MIN_NOTIONAL})")
    print()

print("=" * 70)
print("✅ Todos os testes concluídos!")
print("=" * 70)
