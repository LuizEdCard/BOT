#!/usr/bin/env python3
"""
Teste completo simulando sincronização do bot com a exchange
"""

from pathlib import Path
from decimal import Decimal
from src.persistencia.database import DatabaseManager
from src.core.position_manager import PositionManager

# Inicializar
db = DatabaseManager(
    db_path=Path('dados/bot_trading.db'),
    backup_dir=Path('dados/backup')
)

pm = PositionManager(db)

print("="*80)
print("TESTE DE SINCRONIZAÇÃO - SIMULANDO COMPORTAMENTO DO BOT")
print("="*80)

# 1. Estado inicial do PositionManager
print("\n1️⃣ Estado inicial após carregar do banco:")
qtd_inicial = pm.get_quantidade_total('acumulacao')
pm_inicial = pm.get_preco_medio('acumulacao')
valor_inv_inicial = pm.get_valor_total_investido('acumulacao')

print(f"   Quantidade: {qtd_inicial:.2f} ADA")
print(f"   Preço médio: ${pm_inicial:.6f}" if pm_inicial else "   Preço médio: None")
print(f"   Valor investido: ${valor_inv_inicial:.2f}")

# 2. Simular saldo da exchange (diferente do banco)
saldo_exchange = Decimal('335.16')
diferenca = abs(saldo_exchange - qtd_inicial)
tolerancia = max(saldo_exchange * Decimal('0.01'), Decimal('0.1'))

print(f"\n2️⃣ Saldo da Exchange:")
print(f"   Saldo real API: {saldo_exchange:.2f} ADA")
print(f"   Diferença: {diferenca:.2f} ADA")
print(f"   Tolerância: {tolerancia:.2f} ADA")
print(f"   Divergência? {'SIM' if diferenca > tolerancia else 'NÃO'}")

# 3. Se houver divergência, forçar quantidade (como o bot faz)
if diferenca > tolerancia:
    print(f"\n3️⃣ Forçando quantidade para saldo da exchange...")
    pm.forcar_quantidade(saldo_exchange, 'acumulacao')

    qtd_forcada = pm.get_quantidade_total('acumulacao')
    pm_forcado = pm.get_preco_medio('acumulacao')
    valor_inv_forcado = pm.get_valor_total_investido('acumulacao')

    print(f"   Quantidade após forçar: {qtd_forcada:.2f} ADA")
    print(f"   Preço médio após forçar: ${pm_forcado:.6f}" if pm_forcado else "   Preço médio: None ❌")
    print(f"   Valor investido: ${valor_inv_forcado:.2f}")

    if pm_forcado:
        print(f"\n   ✅ Preço médio recalculado: ${valor_inv_forcado:.2f} / {qtd_forcada:.2f} = ${pm_forcado:.6f}")
    else:
        print(f"\n   ❌ PROBLEMA: Preço médio está None!")
        print(f"      Isso acontece porque valor_investido ({valor_inv_forcado}) não é suficiente")
        print(f"      para calcular PM correto com quantidade forçada ({qtd_forcada})")

print("\n" + "="*80)
