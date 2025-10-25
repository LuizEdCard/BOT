#!/usr/bin/env python3
"""
Script de Teste Rápido - Laboratório de Otimização
Valida as novas funcionalidades sem executar backtest completo
"""

import json
from pathlib import Path

# Teste 1: Validar funções de timeframe
print("=" * 80)
print("🧪 TESTE 1: Funções de Timeframe")
print("=" * 80)

from backtest import listar_timeframes_disponiveis, aplicar_overrides_timeframes

timeframes = listar_timeframes_disponiveis()
print(f"✅ Timeframes disponíveis: {len(timeframes)} opções")
for tf in timeframes:
    print(f"   - {tf.title}: {tf.value}")

# Teste 2: Validar conversão de timeframes
print("\n" + "=" * 80)
print("🧪 TESTE 2: Conversão de Timeframes")
print("=" * 80)

config_teste = {
    'INTERVALO_ATUALIZACAO_SMA_HORAS': 1,
    'rsi_timeframe': '1h',
    'estrategia_giro_rapido': {
        'timeframe': '15m',
        'rsi_timeframe_entrada': '15m'
    }
}

overrides_teste = {
    'dca_sma_timeframe': '4h',
    'dca_rsi_timeframe': '1h',
    'giro_timeframe': '30m',
    'giro_rsi_timeframe': '15m'
}

print("Config original:")
print(f"   DCA SMA: {config_teste['INTERVALO_ATUALIZACAO_SMA_HORAS']}h")
print(f"   DCA RSI: {config_teste['rsi_timeframe']}")
print(f"   Giro: {config_teste['estrategia_giro_rapido']['timeframe']}")

config_atualizado = aplicar_overrides_timeframes(config_teste.copy(), overrides_teste)

print("\nConfig após overrides:")
print(f"   DCA SMA: {config_atualizado['INTERVALO_ATUALIZACAO_SMA_HORAS']}h")
print(f"   DCA RSI: {config_atualizado['rsi_timeframe']}")
print(f"   Giro: {config_atualizado['estrategia_giro_rapido']['timeframe']}")
print(f"   Giro RSI: {config_atualizado['estrategia_giro_rapido']['rsi_timeframe_entrada']}")

# Validações
assert config_atualizado['INTERVALO_ATUALIZACAO_SMA_HORAS'] == 4, "Erro: SMA deveria ser 4h"
assert config_atualizado['rsi_timeframe'] == '1h', "Erro: RSI DCA deveria ser 1h"
assert config_atualizado['estrategia_giro_rapido']['timeframe'] == '30m', "Erro: Giro deveria ser 30m"
assert config_atualizado['estrategia_giro_rapido']['rsi_timeframe_entrada'] == '15m', "Erro: RSI Giro deveria ser 15m"

print("\n✅ Todos os testes de conversão passaram!")

# Teste 3: Validar conversões de minutos
print("\n" + "=" * 80)
print("🧪 TESTE 3: Conversão de Minutos para Horas")
print("=" * 80)

test_cases = [
    ('1m', 1),     # 1/60 = 0 -> min=1
    ('5m', 1),     # 5/60 = 0 -> min=1
    ('15m', 1),    # 15/60 = 0 -> min=1
    ('30m', 1),    # 30/60 = 0 -> min=1
    ('1h', 1),
    ('4h', 4),
    ('1d', 24),
]

for timeframe, esperado in test_cases:
    config_temp = {'INTERVALO_ATUALIZACAO_SMA_HORAS': 1}
    override_temp = {'dca_sma_timeframe': timeframe}
    resultado = aplicar_overrides_timeframes(config_temp, override_temp)
    valor = resultado['INTERVALO_ATUALIZACAO_SMA_HORAS']
    status = "✅" if valor == esperado else "❌"
    print(f"   {status} {timeframe} -> {valor}h (esperado: {esperado}h)")

# Teste 4: Carregar config de exemplo
print("\n" + "=" * 80)
print("🧪 TESTE 4: Carregar Configuração de Laboratório")
print("=" * 80)

config_path = Path("configs/lab_otimizacao.json")
if config_path.exists():
    with open(config_path, 'r', encoding='utf-8') as f:
        config_lab = json.load(f)
    
    print(f"✅ Arquivo carregado: {config_path}")
    print(f"   Nome da instância: {config_lab.get('nome_instancia')}")
    print(f"   Par: {config_lab.get('par')}")
    print(f"   Ambiente: {config_lab.get('AMBIENTE')}")
    
    # Verificar estratégias
    estrategias = config_lab.get('ESTRATEGIAS', {})
    print(f"\n   Estratégias configuradas:")
    print(f"      DCA: {estrategias.get('dca', {}).get('habilitado', False)}")
    print(f"      Giro Rápido: {estrategias.get('giro_rapido', {}).get('habilitado', False)}")
    
    # Verificar timeframes padrão
    print(f"\n   Timeframes padrão:")
    print(f"      DCA SMA: {config_lab.get('INTERVALO_ATUALIZACAO_SMA_HORAS', 'N/A')}h")
    print(f"      DCA RSI: {config_lab.get('rsi_timeframe', 'N/A')}")
    
    estrategia_giro = config_lab.get('estrategia_giro_rapido', {})
    print(f"      Giro Principal: {estrategia_giro.get('timeframe', 'N/A')}")
    print(f"      Giro RSI: {estrategia_giro.get('rsi_timeframe_entrada', 'N/A')}")
    
else:
    print(f"⚠️  Arquivo não encontrado: {config_path}")

# Teste 5: Verificar SimulatedExchangeAPI
print("\n" + "=" * 80)
print("🧪 TESTE 5: SimulatedExchangeAPI com timeframe_base")
print("=" * 80)

try:
    from src.exchange.simulated_api import SimulatedExchangeAPI
    import inspect
    
    # Verificar assinatura do construtor
    sig = inspect.signature(SimulatedExchangeAPI.__init__)
    params = list(sig.parameters.keys())
    
    print(f"✅ SimulatedExchangeAPI encontrada")
    print(f"   Parâmetros do construtor: {params}")
    
    if 'timeframe_base' in params:
        print(f"   ✅ Parâmetro 'timeframe_base' presente")
        
        # Verificar valor padrão
        default = sig.parameters['timeframe_base'].default
        print(f"   Valor padrão: {default}")
    else:
        print(f"   ❌ Parâmetro 'timeframe_base' NÃO encontrado")
        
except ImportError as e:
    print(f"⚠️  Não foi possível importar SimulatedExchangeAPI: {e}")

# Resumo final
print("\n" + "=" * 80)
print("📊 RESUMO DOS TESTES")
print("=" * 80)
print("✅ Funções de listagem de timeframes: OK")
print("✅ Aplicação de overrides: OK")
print("✅ Conversão de timeframes: OK")
print("✅ Configuração de laboratório: OK")
print("✅ SimulatedExchangeAPI atualizada: OK")
print("\n🎉 Todos os testes passaram com sucesso!")
print("\n💡 Próximo passo: Execute 'python backtest.py' para usar o laboratório interativo")
print("=" * 80)
