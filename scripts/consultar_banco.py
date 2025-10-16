#!/usr/bin/env python3
"""
Script para consultar o banco de dados e gerar relatórios.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import sqlite3
from decimal import Decimal
from datetime import datetime

# Caminho padrão do banco
DB_PATH = Path(__file__).parent / 'dados' / 'trading_bot.db'


class ConsultorBanco:
    """Classe para consultar e gerar relatórios do banco de dados."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _conectar(self):
        """Conecta ao banco de dados."""
        if not self.db_path.exists():
            print(f"❌ Banco de dados não encontrado: {self.db_path}")
            return None

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def resumo_geral(self):
        """Exibe resumo geral das operações."""
        conn = self._conectar()
        if not conn:
            return

        cursor = conn.cursor()

        print("\n" + "=" * 60)
        print("📊 RESUMO GERAL DAS OPERAÇÕES")
        print("=" * 60)

        # Total de ordens
        cursor.execute("SELECT COUNT(*) as total FROM ordens WHERE tipo = 'COMPRA'")
        total_compras = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM ordens WHERE tipo = 'VENDA'")
        total_vendas = cursor.fetchone()['total']

        print(f"\n📈 Total de operações:")
        print(f"   Compras: {total_compras}")
        print(f"   Vendas:  {total_vendas}")

        # Volume operado
        cursor.execute("SELECT COALESCE(SUM(valor_total), 0) as total FROM ordens WHERE tipo = 'COMPRA'")
        volume_comprado = cursor.fetchone()['total']

        cursor.execute("SELECT COALESCE(SUM(valor_total), 0) as total FROM ordens WHERE tipo = 'VENDA'")
        volume_vendido = cursor.fetchone()['total']

        print(f"\n💰 Volume operado:")
        print(f"   Comprado: ${volume_comprado:.2f} USDT")
        print(f"   Vendido:  ${volume_vendido:.2f} USDT")

        # Lucro realizado
        cursor.execute("SELECT COALESCE(SUM(lucro_usdt), 0) as total FROM ordens WHERE tipo = 'VENDA'")
        lucro_total = cursor.fetchone()['total']

        print(f"\n💵 Lucro realizado: ${lucro_total:.2f} USDT")

        # ROI
        if volume_comprado > 0:
            roi = (lucro_total / volume_comprado) * 100
            print(f"📊 ROI: {roi:.2f}%")

        # Taxas pagas
        cursor.execute("SELECT COALESCE(SUM(taxa), 0) as total FROM ordens")
        taxas = cursor.fetchone()['total']
        print(f"💸 Taxas pagas: ${taxas:.4f} USDT")

        conn.close()

    def ultimas_ordens(self, limite: int = 10):
        """Lista as últimas N ordens."""
        conn = self._conectar()
        if not conn:
            return

        cursor = conn.cursor()

        print("\n" + "=" * 60)
        print(f"📋 ÚLTIMAS {limite} OPERAÇÕES")
        print("=" * 60)

        cursor.execute("""
            SELECT timestamp, tipo, quantidade, preco, valor_total, meta, lucro_percentual, lucro_usdt
            FROM ordens
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limite,))

        ordens = cursor.fetchall()

        if not ordens:
            print("\n❌ Nenhuma ordem encontrada")
            conn.close()
            return

        print("\n{:<20} {:<7} {:<10} {:<10} {:<12} {:<12} {:<8}".format(
            "Data/Hora", "Tipo", "Qtd ADA", "Preço", "Total USDT", "Meta", "Lucro"
        ))
        print("-" * 90)

        for ordem in ordens:
            timestamp = ordem['timestamp'][:19]  # Remove microsegundos
            tipo = ordem['tipo']
            qtd = ordem['quantidade']
            preco = ordem['preco']
            total = ordem['valor_total']
            meta = ordem['meta'] or '-'

            if ordem['lucro_percentual']:
                lucro = f"+{ordem['lucro_percentual']:.2f}%"
            else:
                lucro = "-"

            print(f"{timestamp} {tipo:7} {qtd:10.1f} ${preco:8.4f} ${total:10.2f} {meta:12} {lucro:8}")

        conn.close()

    def estado_atual(self):
        """Exibe o estado atual do bot."""
        conn = self._conectar()
        if not conn:
            return

        cursor = conn.cursor()

        print("\n" + "=" * 60)
        print("🤖 ESTADO ATUAL DO BOT")
        print("=" * 60)

        cursor.execute("SELECT * FROM estado_bot WHERE id = 1")
        estado = cursor.fetchone()

        if estado:
            print(f"\n📊 Última atualização: {estado['timestamp_atualizacao'][:19]}")

            if estado['preco_medio_compra']:
                print(f"💰 Preço médio de compra: ${estado['preco_medio_compra']:.6f}")

            if estado['quantidade_total_ada']:
                print(f"📦 Quantidade total: {estado['quantidade_total_ada']:.1f} ADA")

                if estado['preco_medio_compra']:
                    valor_investido = estado['preco_medio_compra'] * estado['quantidade_total_ada']
                    print(f"💵 Valor investido: ${valor_investido:.2f} USDT")
        else:
            print("\n❌ Nenhum estado encontrado")

        conn.close()

    def estatisticas_vendas(self):
        """Exibe estatísticas das vendas."""
        conn = self._conectar()
        if not conn:
            return

        cursor = conn.cursor()

        print("\n" + "=" * 60)
        print("📈 ESTATÍSTICAS DE VENDAS")
        print("=" * 60)

        cursor.execute("""
            SELECT
                COUNT(*) as total_vendas,
                COALESCE(AVG(lucro_percentual), 0) as lucro_medio,
                COALESCE(MAX(lucro_percentual), 0) as maior_lucro,
                COALESCE(MIN(lucro_percentual), 0) as menor_lucro,
                COALESCE(SUM(lucro_usdt), 0) as lucro_total
            FROM ordens
            WHERE tipo = 'VENDA'
        """)

        stats = cursor.fetchone()

        if stats['total_vendas'] > 0:
            print(f"\n📊 Total de vendas: {stats['total_vendas']}")
            print(f"💰 Lucro médio: {stats['lucro_medio']:.2f}%")
            print(f"🚀 Maior lucro: {stats['maior_lucro']:.2f}%")
            print(f"📉 Menor lucro: {stats['menor_lucro']:.2f}%")
            print(f"💵 Lucro total: ${stats['lucro_total']:.2f} USDT")

            # Vendas por meta
            print("\n📋 Vendas por meta:")
            cursor.execute("""
                SELECT meta, COUNT(*) as qtd, COALESCE(SUM(lucro_usdt), 0) as lucro
                FROM ordens
                WHERE tipo = 'VENDA'
                GROUP BY meta
                ORDER BY qtd DESC
            """)

            vendas_por_meta = cursor.fetchall()
            for venda in vendas_por_meta:
                print(f"   {venda['meta']:15} | {venda['qtd']:2} vendas | ${venda['lucro']:6.2f} USDT")
        else:
            print("\n❌ Nenhuma venda registrada ainda")

        conn.close()

    def estatisticas_compras(self):
        """Exibe estatísticas das compras."""
        conn = self._conectar()
        if not conn:
            return

        cursor = conn.cursor()

        print("\n" + "=" * 60)
        print("🛒 ESTATÍSTICAS DE COMPRAS")
        print("=" * 60)

        cursor.execute("""
            SELECT
                COUNT(*) as total_compras,
                COALESCE(AVG(preco), 0) as preco_medio,
                COALESCE(MAX(preco), 0) as maior_preco,
                COALESCE(MIN(preco), 0) as menor_preco,
                COALESCE(SUM(quantidade), 0) as total_ada
            FROM ordens
            WHERE tipo = 'COMPRA'
        """)

        stats = cursor.fetchone()

        if stats['total_compras'] > 0:
            print(f"\n📊 Total de compras: {stats['total_compras']}")
            print(f"💰 Preço médio: ${stats['preco_medio']:.6f}")
            print(f"🔼 Maior preço: ${stats['maior_preco']:.6f}")
            print(f"🔽 Menor preço: ${stats['menor_preco']:.6f}")
            print(f"📦 Total acumulado: {stats['total_ada']:.1f} ADA")

            # Compras por degrau
            print("\n📋 Compras por degrau:")
            cursor.execute("""
                SELECT meta, COUNT(*) as qtd, COALESCE(SUM(valor_total), 0) as total
                FROM ordens
                WHERE tipo = 'COMPRA'
                GROUP BY meta
                ORDER BY meta
            """)

            compras_por_degrau = cursor.fetchall()
            for compra in compras_por_degrau:
                print(f"   {compra['meta']:15} | {compra['qtd']:2} compras | ${compra['total']:6.2f} USDT")
        else:
            print("\n❌ Nenhuma compra registrada ainda")

        conn.close()

    def relatorio_completo(self):
        """Gera relatório completo."""
        self.resumo_geral()
        self.estado_atual()
        self.ultimas_ordens(limite=15)
        self.estatisticas_compras()
        self.estatisticas_vendas()


def main():
    """Função principal."""
    consultor = ConsultorBanco(DB_PATH)

    if len(sys.argv) > 1:
        comando = sys.argv[1]

        if comando == 'resumo':
            consultor.resumo_geral()
        elif comando == 'estado':
            consultor.estado_atual()
        elif comando == 'ordens':
            limite = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            consultor.ultimas_ordens(limite=limite)
        elif comando == 'vendas':
            consultor.estatisticas_vendas()
        elif comando == 'compras':
            consultor.estatisticas_compras()
        elif comando == 'completo':
            consultor.relatorio_completo()
        else:
            print(f"❌ Comando desconhecido: {comando}")
            print("\nUso: python3 consultar_banco.py [comando]")
            print("\nComandos disponíveis:")
            print("  resumo    - Resumo geral das operações")
            print("  estado    - Estado atual do bot")
            print("  ordens    - Últimas ordens (padrão: 10)")
            print("  vendas    - Estatísticas de vendas")
            print("  compras   - Estatísticas de compras")
            print("  completo  - Relatório completo")
    else:
        # Se não passar comando, mostrar relatório completo
        consultor.relatorio_completo()


if __name__ == '__main__':
    main()
