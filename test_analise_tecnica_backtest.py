#!/usr/bin/env python3
"""
Script de teste para validar integração AnaliseTecnica com SimulatedExchangeAPI
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.exchange.simulated_api import SimulatedExchangeAPI
from src.core.analise_tecnica import AnaliseTecnica

def test_analise_tecnica_com_backtest():
    """Testa cálculo de SMA usando dados simulados"""
    
    # Usar arquivo de dados históricos
    csv_path = "dados/historicos/BINANCE_adausdt_30m_2017-01-01_2025-10-24.csv"
    
    print("=" * 80)
    print("🧪 TESTE INTEGRAÇÃO - AnaliseTecnica + SimulatedExchangeAPI")
    print("=" * 80)
    
    try:
        # Criar API simulada
        print(f"\n📂 Carregando dados: {csv_path}")
        api = SimulatedExchangeAPI(
            caminho_csv=csv_path,
            saldo_inicial=1000,
            taxa_pct=0.1
        )
        print(f"✅ API carregada com {len(api.dados)} barras (timeframe original: 30m)")
        
        # Criar AnaliseTecnica usando a API simulada
        print(f"\n🔧 Criando AnaliseTecnica...")
        analise = AnaliseTecnica(api)
        print(f"✅ AnaliseTecnica criada")
        
        # Testar cálculo de SMA em múltiplos timeframes
        simbolo = 'ADAUSDT'
        periodo_dias = 28  # 4 semanas
        
        print(f"\n{'=' * 80}")
        print(f"📊 Calculando SMAs para {periodo_dias} dias")
        print(f"{'=' * 80}")
        
        smas = analise.calcular_sma_multiplos_timeframes(
            simbolo=simbolo,
            periodo_dias=periodo_dias
        )
        
        if smas:
            print(f"\n✅ SMAs calculadas com sucesso:")
            print(f"   SMA 1h:  ${smas['1h']:.6f}")
            print(f"   SMA 4h:  ${smas['4h']:.6f}")
            print(f"   Média ponderada: ${smas['media']:.6f}")
        else:
            print(f"❌ Erro ao calcular SMAs")
            return False
        
        # Testar estatísticas do período
        print(f"\n{'=' * 80}")
        print(f"📊 Obtendo estatísticas do período")
        print(f"{'=' * 80}")
        
        stats = analise.obter_estatisticas_periodo(
            simbolo=simbolo,
            intervalo='4h',
            periodo_dias=periodo_dias
        )
        
        if stats:
            print(f"\n✅ Estatísticas obtidas:")
            print(f"   SMA: ${stats['sma']:.6f}")
            print(f"   Preço máximo: ${stats['preco_maximo']:.6f}")
            print(f"   Preço mínimo: ${stats['preco_minimo']:.6f}")
            print(f"   Volatilidade: {stats['volatilidade']:.2f}%")
            print(f"   Candles analisados: {stats['num_candles']}")
        else:
            print(f"❌ Erro ao obter estatísticas")
            return False
        
        print(f"\n{'=' * 80}")
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print(f"{'=' * 80}")
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_analise_tecnica_com_backtest()
    sys.exit(0 if success else 1)
