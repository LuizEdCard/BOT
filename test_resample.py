#!/usr/bin/env python3
"""
Script de teste para validar o resampling de timeframe na SimulatedExchangeAPI
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from src.exchange.simulated_api import SimulatedExchangeAPI

def test_resample():
    """Testa o resampling de diferentes timeframes"""
    
    # Usar arquivo de dados históricos
    csv_path = "dados/historicos/BINANCE_adausdt_30m_2017-01-01_2025-10-24.csv"
    
    print("=" * 80)
    print("🧪 TESTE DE RESAMPLING - SimulatedExchangeAPI")
    print("=" * 80)
    
    try:
        # Criar API simulada
        print(f"\n📂 Carregando dados: {csv_path}")
        api = SimulatedExchangeAPI(
            caminho_csv=csv_path,
            saldo_inicial=1000,
            taxa_pct=0.1
        )
        print(f"✅ API carregada com {len(api.dados)} barras")
        
        # Testar obter_klines para diferentes timeframes
        timeframes = ['1h', '4h', '1d']
        simbolo = 'ADAUSDT'
        limite = 100
        
        for tf in timeframes:
            print(f"\n{'=' * 80}")
            print(f"📊 Testando timeframe: {tf}")
            print(f"{'=' * 80}")
            
            # Obter klines
            klines = api.obter_klines(
                simbolo=simbolo,
                intervalo=tf,
                limite=limite
            )
            
            if klines:
                print(f"✅ Obtidos {len(klines)} candles de {tf}")
                
                # Mostrar primeira e última barra
                primeira = klines[0]
                ultima = klines[-1]
                
                print(f"\n📅 Primeira barra:")
                print(f"   Timestamp: {primeira[0]}")
                print(f"   Open: {primeira[1]}")
                print(f"   High: {primeira[2]}")
                print(f"   Low: {primeira[3]}")
                print(f"   Close: {primeira[4]}")
                print(f"   Volume: {primeira[5]}")
                
                print(f"\n📅 Última barra:")
                print(f"   Timestamp: {ultima[0]}")
                print(f"   Open: {ultima[1]}")
                print(f"   High: {ultima[2]}")
                print(f"   Low: {ultima[3]}")
                print(f"   Close: {ultima[4]}")
                print(f"   Volume: {ultima[5]}")
            else:
                print(f"❌ Erro: Nenhum candle obtido para {tf}")
        
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
    success = test_resample()
    sys.exit(0 if success else 1)
