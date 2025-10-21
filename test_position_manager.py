#!/usr/bin/env python3
"""
Script de teste para verificar cálculo do PositionManager
"""

from pathlib import Path
from src.persistencia.database import DatabaseManager
from src.core.position_manager import PositionManager

# Inicializar DB
db = DatabaseManager(
    db_path=Path('dados/bot_trading.db'),
    backup_dir=Path('dados/backup')
)

# Inicializar PositionManager
pm = PositionManager(db)

# Verificar carteira acumulacao
print("="*60)
print("TESTE DO POSITION MANAGER - CARTEIRA ACUMULAÇÃO")
print("="*60)

quantidade = pm.get_quantidade_total('acumulacao')
preco_medio = pm.get_preco_medio('acumulacao')
valor_investido = pm.get_valor_total_investido('acumulacao')

print(f"Quantidade total: {quantidade:.2f} ADA")
print(f"Preço médio: ${preco_medio:.6f}" if preco_medio else "Preço médio: None")
print(f"Valor investido: ${valor_investido:.2f}")

if preco_medio and quantidade > 0:
    print(f"✅ Preço médio calculado corretamente!")
    print(f"   Valor investido / Quantidade = ${valor_investido:.2f} / {quantidade:.2f} = ${valor_investido/quantidade:.6f}")
else:
    print(f"❌ Preço médio está None! Investigando...")

    # Debug: verificar estado interno
    print(f"\nEstado interno da carteira 'acumulacao':")
    print(f"  - quantidade_total: {pm.carteiras['acumulacao']['quantidade_total']}")
    print(f"  - preco_medio: {pm.carteiras['acumulacao']['preco_medio']}")
    print(f"  - valor_total_investido: {pm.carteiras['acumulacao']['valor_total_investido']}")
    print(f"  - posicao_carregada: {pm.carteiras['acumulacao']['posicao_carregada']}")

print("="*60)
