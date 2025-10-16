#!/usr/bin/env python3
"""
Script para importar histórico de ordens da Binance para o banco de dados.

Uso:
    python3 importar_historico.py           # Importa últimas 500 ordens
    python3 importar_historico.py 1000      # Importa últimas 1000 ordens
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from src.comunicacao.api_manager import APIManager
from src.persistencia.database import DatabaseManager


def main():
    """Função principal."""
    print("\n" + "=" * 60)
    print("📥 IMPORTADOR DE HISTÓRICO DA BINANCE")
    print("=" * 60)

    # Verificar argumentos
    limite = 500
    if len(sys.argv) > 1:
        try:
            limite = int(sys.argv[1])
            if limite > 1000:
                print("⚠️ Limite máximo da Binance é 1000 ordens")
                limite = 1000
        except ValueError:
            print("❌ Argumento inválido. Use: python3 importar_historico.py [limite]")
            return

    print(f"\n🔍 Buscando até {limite} ordens da Binance...")

    # Inicializar API Manager
    api = APIManager(
        api_key=settings.BINANCE_API_KEY,
        api_secret=settings.BINANCE_API_SECRET,
        base_url=settings.BINANCE_API_URL
    )

    # Verificar conexão
    print("🔌 Verificando conexão com a Binance...")
    if not api.verificar_conexao():
        print("❌ Não foi possível conectar à API Binance")
        return

    print("✅ Conectado à Binance")

    # Inicializar Database Manager
    db = DatabaseManager(
        db_path=settings.DATABASE_PATH,
        backup_dir=settings.BACKUP_DIR
    )

    print(f"✅ Banco de dados: {settings.DATABASE_PATH}")

    # Buscar ordens da Binance
    print(f"\n📋 Buscando histórico de ordens (ADA/USDT)...")
    ordens = api.obter_historico_ordens(simbolo='ADAUSDT', limite=limite)

    if not ordens:
        print("📭 Nenhuma ordem encontrada no histórico")
        return

    print(f"✅ Encontradas {len(ordens)} ordens executadas")

    # Mostrar preview das primeiras ordens
    print("\n📊 Preview das últimas 5 ordens:")
    print("-" * 80)
    print(f"{'Data/Hora':<20} {'Tipo':<7} {'Qtd ADA':<10} {'Preço USDT':<12} {'Total':<12}")
    print("-" * 80)

    for ordem in ordens[-5:]:  # Últimas 5
        from datetime import datetime
        timestamp = datetime.fromtimestamp(ordem['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        tipo = ordem['side']
        quantidade = float(ordem['executedQty'])
        preco = float(ordem['cummulativeQuoteQty']) / quantidade if quantidade > 0 else 0
        total = float(ordem['cummulativeQuoteQty'])

        print(f"{timestamp:<20} {tipo:<7} {quantidade:<10.1f} ${preco:<11.6f} ${total:<11.2f}")

    # Perguntar confirmação
    print("\n" + "=" * 60)
    resposta = input("❓ Deseja importar estas ordens para o banco de dados? (s/N): ")

    if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
        print("❌ Importação cancelada")
        return

    # Importar ordens
    print("\n📥 Importando ordens...")
    resultado = db.importar_ordens_binance(ordens, recalcular_preco_medio=True)

    # Exibir resultado
    print("\n" + "=" * 60)
    print("✅ IMPORTAÇÃO CONCLUÍDA")
    print("=" * 60)
    print(f"\n📊 Estatísticas:")
    print(f"   Total processadas: {resultado['total_processadas']}")
    print(f"   ✅ Importadas: {resultado['importadas']}")
    print(f"   ⏭️  Duplicadas (já existiam): {resultado['duplicadas']}")
    print(f"   ❌ Erros: {resultado['erros']}")

    # Mostrar estado atualizado
    if resultado['importadas'] > 0:
        print("\n📊 Estado do bot atualizado:")
        estado = db.recuperar_estado_bot()

        if estado and estado['preco_medio_compra']:
            print(f"   💰 Preço médio de compra: ${estado['preco_medio_compra']:.6f}")
            print(f"   📦 Quantidade total: {estado['quantidade_total_ada']:.1f} ADA")

            if estado['preco_medio_compra'] and estado['quantidade_total_ada']:
                valor_investido = estado['preco_medio_compra'] * estado['quantidade_total_ada']
                print(f"   💵 Valor investido: ${valor_investido:.2f} USDT")

        # Mostrar métricas
        metricas = db.calcular_metricas()
        print(f"\n💰 Métricas gerais:")
        print(f"   Total de compras: {metricas['total_compras']}")
        print(f"   Total de vendas: {metricas['total_vendas']}")
        print(f"   Volume comprado: ${metricas['volume_comprado']:.2f} USDT")
        print(f"   Lucro realizado: ${metricas['lucro_realizado']:.2f} USDT")

        if metricas['volume_comprado'] > 0:
            print(f"   ROI: {metricas['roi_percentual']:.2f}%")

    print("\n✅ Importação concluída com sucesso!")
    print(f"\n💡 Dica: Use 'python3 consultar_banco.py completo' para ver o histórico completo")


if __name__ == '__main__':
    main()
