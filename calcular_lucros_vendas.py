#!/usr/bin/env python3
"""
Script para calcular e atualizar lucros de vendas no banco de dados
"""

import sqlite3
from decimal import Decimal
from pathlib import Path

def calcular_lucros_vendas(db_path: str):
    """
    Calcula o preço médio de compra até cada venda e atualiza o lucro.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Buscar todas as ordens em ordem cronológica
    cursor.execute("""
        SELECT id, timestamp, tipo, quantidade, preco, valor_total,
               lucro_percentual, lucro_usdt, preco_medio_antes
        FROM ordens
        ORDER BY timestamp ASC
    """)

    ordens = cursor.fetchall()

    # Variáveis para rastrear a posição
    quantidade_acumulada = Decimal('0')
    valor_investido_acumulado = Decimal('0')
    vendas_atualizadas = 0

    print(f"Processando {len(ordens)} ordens...")
    print("=" * 80)

    for ordem in ordens:
        ordem_id, timestamp, tipo, quantidade, preco, valor_total, lucro_pct, lucro_usdt, pm_antes = ordem

        quantidade = Decimal(str(quantidade))
        preco = Decimal(str(preco))

        if tipo == 'COMPRA':
            # Acumular compra
            valor_compra = quantidade * preco
            quantidade_acumulada += quantidade
            valor_investido_acumulado += valor_compra

            # Calcular preço médio atual
            if quantidade_acumulada > 0:
                pm_atual = valor_investido_acumulado / quantidade_acumulada
                print(f"  COMPRA: {quantidade:.2f} @ ${preco:.6f} | PM agora: ${pm_atual:.6f} | Qtd total: {quantidade_acumulada:.2f}")

        elif tipo == 'VENDA':
            # Verificar se já tem lucro calculado
            if lucro_usdt is not None and lucro_pct is not None:
                print(f"  VENDA: {quantidade:.2f} @ ${preco:.6f} | Lucro já calculado: ${lucro_usdt:.2f} ({lucro_pct:.2f}%)")
            else:
                # Calcular preço médio ANTES da venda
                if quantidade_acumulada > 0 and valor_investido_acumulado > 0:
                    pm_antes_venda = valor_investido_acumulado / quantidade_acumulada

                    # Calcular lucro
                    lucro_por_unidade = preco - pm_antes_venda
                    lucro_total = lucro_por_unidade * quantidade
                    lucro_percentual = ((preco - pm_antes_venda) / pm_antes_venda) * Decimal('100')

                    print(f"  VENDA: {quantidade:.2f} @ ${preco:.6f} | PM antes: ${pm_antes_venda:.6f}")
                    print(f"    → Lucro: ${lucro_total:.2f} ({lucro_percentual:.2f}%)")

                    # Atualizar no banco
                    cursor.execute("""
                        UPDATE ordens
                        SET lucro_percentual = ?,
                            lucro_usdt = ?,
                            preco_medio_antes = ?
                        WHERE id = ?
                    """, (float(lucro_percentual), float(lucro_total), float(pm_antes_venda), ordem_id))

                    vendas_atualizadas += 1
                else:
                    print(f"  VENDA: {quantidade:.2f} @ ${preco:.6f} | ⚠️ Sem posição anterior para calcular lucro")

            # Atualizar posição após venda (redução proporcional)
            if quantidade_acumulada > 0:
                proporcao_vendida = min(quantidade / quantidade_acumulada, Decimal('1'))
                quantidade_acumulada -= quantidade
                valor_investido_acumulado *= (Decimal('1') - proporcao_vendida)

                # Garantir que não ficou negativo
                if quantidade_acumulada < Decimal('0.0001'):
                    quantidade_acumulada = Decimal('0')
                    valor_investido_acumulado = Decimal('0')

    # Commit das alterações
    try:
        conn.commit()
        print("=" * 80)
        print(f"✅ Commit realizado com sucesso!")
        print(f"   Vendas atualizadas: {vendas_atualizadas}")

        # Verificar quantas vendas têm lucro calculado
        cursor.execute("SELECT COUNT(*) FROM ordens WHERE lucro_usdt IS NOT NULL AND tipo = 'VENDA'")
        vendas_com_lucro = cursor.fetchone()[0]
        print(f"   Vendas com lucro no banco: {vendas_com_lucro}")

    except Exception as e:
        print(f"❌ Erro ao fazer commit: {e}")
        conn.rollback()
    finally:
        conn.close()

    print(f"   Posição final: {quantidade_acumulada:.2f} ADA")
    if quantidade_acumulada > 0:
        pm_final = valor_investido_acumulado / quantidade_acumulada
        print(f"   Preço médio final: ${pm_final:.6f}")

if __name__ == '__main__':
    print("🔄 Calculando lucros de vendas no banco de dados ADA...")
    print()
    calcular_lucros_vendas('dados/bot_trading.db')
