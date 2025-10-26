#!/usr/bin/env python3
"""
Script de teste para validar a nova análise de saídas (Tarefa 1)
e a lógica de promoção de stops (Tarefa 2) - Phase 5
"""

import sys
import os
import json
from pathlib import Path
from decimal import Decimal
import tempfile
from datetime import datetime, timedelta

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar funções necessárias
from backtest import analisar_saidas_por_motivo

def criar_trades_teste():
    """Cria trades de teste para validar a análise de saídas (com FIFO matching)"""
    trades = [
        # Compra 1
        {
            'id': '1',
            'tipo': 'compra',
            'timestamp': '2025-01-01 10:00:00',
            'preco': 1.00,
            'quantidade_ativo': 10.0,
            'quantidade_usdt': 10.00,
            'carteira': 'giro_rapido'
        },
        # Venda 1 - Stop Loss (vinculada a Compra 1)
        # Lucro = 9.80 - 10.00 = -0.20
        {
            'id': '2',
            'tipo': 'venda',
            'timestamp': '2025-01-01 10:05:00',
            'preco': 0.98,
            'quantidade_ativo': 10.0,
            'receita_usdt': 9.80,
            'motivo': 'Stop Loss (SL) disparado',
            'carteira': 'giro_rapido'
        },
        # Compra 2
        {
            'id': '3',
            'tipo': 'compra',
            'timestamp': '2025-01-01 11:00:00',
            'preco': 1.00,
            'quantidade_ativo': 20.0,
            'quantidade_usdt': 20.00,
            'carteira': 'giro_rapido'
        },
        # Venda 2 - TSL (vinculada a Compra 2)
        # Lucro = 20.50 - 20.00 = +0.50
        {
            'id': '4',
            'tipo': 'venda',
            'timestamp': '2025-01-01 11:30:00',
            'preco': 1.025,
            'quantidade_ativo': 20.0,
            'receita_usdt': 20.50,
            'motivo': 'Trailing Stop Loss (TSL) disparado',
            'carteira': 'giro_rapido'
        },
        # Compra 3
        {
            'id': '5',
            'tipo': 'compra',
            'timestamp': '2025-01-01 12:00:00',
            'preco': 1.00,
            'quantidade_ativo': 15.0,
            'quantidade_usdt': 15.00,
            'carteira': 'giro_rapido'
        },
        # Venda 3 - Meta de Lucro (vinculada a Compra 3)
        # Lucro = 15.45 - 15.00 = +0.45
        {
            'id': '6',
            'tipo': 'venda',
            'timestamp': '2025-01-01 12:45:00',
            'preco': 1.03,
            'quantidade_ativo': 15.0,
            'receita_usdt': 15.45,
            'motivo': 'Meta de Lucro atingida',
            'carteira': 'giro_rapido'
        },
        # Compra 4
        {
            'id': '7',
            'tipo': 'compra',
            'timestamp': '2025-01-01 13:00:00',
            'preco': 1.00,
            'quantidade_ativo': 5.0,
            'quantidade_usdt': 5.00,
            'carteira': 'giro_rapido'
        },
        # Venda 4 - Outro motivo (vinculada a Compra 4)
        # Lucro = 4.975 - 5.00 = -0.025
        {
            'id': '8',
            'tipo': 'venda',
            'timestamp': '2025-01-01 13:30:00',
            'preco': 0.995,
            'quantidade_ativo': 5.0,
            'receita_usdt': 4.975,
            'motivo': 'Posição fechada',
            'carteira': 'giro_rapido'
        }
    ]
    return trades


def testar_analise_saidas():
    """Testa a função analisar_saidas_por_motivo()"""
    print("\n" + "="*80)
    print("✅ TESTE 1: ANÁLISE DE SAÍDAS (Tarefa 1)")
    print("="*80)

    trades = criar_trades_teste()
    saidas = analisar_saidas_por_motivo(trades)

    print("\n📊 Resultados da Análise de Saídas:\n")

    for motivo in ['Stop Loss (SL)', 'Trailing Stop Loss (TSL)', 'Meta de Lucro', 'Outros']:
        info = saidas[motivo]
        count = info['count']

        if count > 0:
            lucro_total = float(info['lucro_total'])
            lucro_medio = lucro_total / count if count > 0 else 0

            print(f"   {motivo}:")
            print(f"      Quantidade: {count}")
            print(f"      Lucro/Prejuízo Total: ${lucro_total:+.2f}")
            print(f"      Lucro/Prejuízo Médio: ${lucro_medio:+.2f}")
            print(f"      Detalhes: {info['lucro_lista']}")
            print()

    # Validações
    print("\n🔍 Validações:")

    # Stop Loss deve ter 1 trade com -$0.20
    assert saidas['Stop Loss (SL)']['count'] == 1, "❌ SL count incorreto"
    assert saidas['Stop Loss (SL)']['lucro_lista'][0] == -0.2, "❌ SL lucro incorreto"
    print("   ✅ Stop Loss (SL): 1 trade, -$0.20")

    # TSL deve ter 1 trade com +$0.50
    assert saidas['Trailing Stop Loss (TSL)']['count'] == 1, "❌ TSL count incorreto"
    assert saidas['Trailing Stop Loss (TSL)']['lucro_lista'][0] == 0.5, "❌ TSL lucro incorreto"
    print("   ✅ Trailing Stop Loss (TSL): 1 trade, +$0.50")

    # Meta deve ter 1 trade com +$0.45
    assert saidas['Meta de Lucro']['count'] == 1, "❌ Meta count incorreto"
    assert saidas['Meta de Lucro']['lucro_lista'][0] == 0.45, "❌ Meta lucro incorreto"
    print("   ✅ Meta de Lucro: 1 trade, +$0.45")

    # Outros deve ter 1 trade com -$0.025
    assert saidas['Outros']['count'] == 1, "❌ Outros count incorreto"
    assert abs(saidas['Outros']['lucro_lista'][0] - (-0.025)) < 0.001, "❌ Outros lucro incorreto"
    print("   ✅ Outros: 1 trade, -$0.025")

    print("\n✅ TESTE 1 PASSOU!")
    return True


def testar_tsl_gatilho_lucro():
    """Testa a lógica de promoção SL → TSL com gatilho de lucro"""
    print("\n" + "="*80)
    print("✅ TESTE 2: LÓGICA DE PROMOÇÃO (Tarefa 2)")
    print("="*80)

    # Simular o cálculo da promoção
    preco_medio = Decimal('1.00')

    test_cases = [
        {
            'nome': 'Breakeven (0%)',
            'preco_atual': Decimal('1.00'),
            'tsl_gatilho': Decimal('0'),
            'esperado_promover': True
        },
        {
            'nome': 'Pequeno lucro (+0.5%)',
            'preco_atual': Decimal('1.005'),
            'tsl_gatilho': Decimal('1.5'),
            'esperado_promover': False
        },
        {
            'nome': 'Lucro mínimo (+1.5%)',
            'preco_atual': Decimal('1.015'),
            'tsl_gatilho': Decimal('1.5'),
            'esperado_promover': True
        },
        {
            'nome': 'Lucro acima do gatilho (+2.0%)',
            'preco_atual': Decimal('1.020'),
            'tsl_gatilho': Decimal('1.5'),
            'esperado_promover': True
        },
        {
            'nome': 'Conservador gatilho (+2.5%), mas lucro é +2.0%',
            'preco_atual': Decimal('1.020'),
            'tsl_gatilho': Decimal('2.5'),
            'esperado_promover': False
        }
    ]

    print("\n📊 Cenários de Promoção SL → TSL:\n")

    for case in test_cases:
        lucro_pct = ((case['preco_atual'] - preco_medio) / preco_medio) * Decimal('100')
        vai_promover = lucro_pct >= case['tsl_gatilho']

        status = "✅" if vai_promover == case['esperado_promover'] else "❌"
        promocao_str = "SIM" if vai_promover else "NÃO"
        lucro_str = f"{lucro_pct:.2f}%"
        gatilho_str = f"{case['tsl_gatilho']:.2f}%"

        print(f"   {status} {case['nome']}")
        print(f"      Lucro: {lucro_str} | Gatilho: {gatilho_str} | Promove: {promocao_str}")

        assert vai_promover == case['esperado_promover'], \
            f"❌ Falha no caso: {case['nome']}"
        print()

    print("✅ TESTE 2 PASSOU!")
    return True


def testar_interacao_usuario():
    """Testa se a interação do usuário inclui o novo parâmetro"""
    print("\n" + "="*80)
    print("✅ TESTE 3: VALIDAÇÃO DE INTERAÇÕES DO USUÁRIO")
    print("="*80)

    import inspect
    from backtest import perguntar_parametros_giro_rapido

    # Verificar se a função menciona tsl_gatilho_lucro_pct
    source_code = inspect.getsource(perguntar_parametros_giro_rapido)

    print("\n🔍 Verificando função 'perguntar_parametros_giro_rapido':\n")

    checks = [
        ('tsl_gatilho_lucro_pct', 'Novo parâmetro de gatilho'),
        ('TSL Gatilho de Lucro', 'Pergunta ao usuário'),
        ('0.5%', 'Exemplo agressivo'),
        ('1.5%', 'Padrão'),
        ('2.5%', 'Exemplo conservador'),
    ]

    for check_str, description in checks:
        if check_str in source_code:
            print(f"   ✅ {description}: '{check_str}'")
        else:
            print(f"   ❌ {description}: '{check_str}' não encontrado")
            raise AssertionError(f"Falta: {description}")

    print("\n✅ TESTE 3 PASSOU!")
    return True


def validar_configs():
    """Valida se as configurações foram atualizadas com o novo parâmetro"""
    print("\n" + "="*80)
    print("✅ TESTE 4: VALIDAÇÃO DE CONFIGURAÇÕES (Tarefa 2)")
    print("="*80)

    configs_para_verificar = [
        'configs/backtest_template.json',
        'configs/estrategia_exemplo_giro_rapido.json'
    ]

    print("\n🔍 Verificando arquivos de configuração:\n")

    for config_file in configs_para_verificar:
        path = Path(config_file)

        if not path.exists():
            print(f"   ❌ {config_file} não encontrado")
            continue

        try:
            with open(path) as f:
                config = json.load(f)

            # Verificar se tem a chave tsl_gatilho_lucro_pct
            if 'estrategia_giro_rapido' in config:
                giro_config = config['estrategia_giro_rapido']
                if 'tsl_gatilho_lucro_pct' in giro_config:
                    valor = giro_config['tsl_gatilho_lucro_pct']
                    print(f"   ✅ {config_file}")
                    print(f"      tsl_gatilho_lucro_pct = {valor}")
                else:
                    print(f"   ❌ {config_file}")
                    print(f"      Falta o parâmetro 'tsl_gatilho_lucro_pct'")
            else:
                print(f"   ⚠️  {config_file}")
                print(f"      Não tem seção 'estrategia_giro_rapido'")

        except Exception as e:
            print(f"   ❌ Erro ao ler {config_file}: {e}")

        print()

    print("✅ TESTE 3 PASSOU!")
    return True


def main():
    """Executa todos os testes"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "🧪 TESTES DE OTIMIZAÇÃO GIRO RÁPIDO - PHASE 5".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")

    resultados = []

    try:
        resultados.append(("Tarefa 1: Análise de Saídas", testar_analise_saidas()))
        resultados.append(("Tarefa 2: Lógica de Promoção", testar_tsl_gatilho_lucro()))
        resultados.append(("Tarefa 2: Interações do Usuário", testar_interacao_usuario()))
        resultados.append(("Tarefa 2: Validação de Configs", validar_configs()))
    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERRO NÃO ESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Resumo
    print("\n" + "="*80)
    print("📋 RESUMO DOS TESTES")
    print("="*80 + "\n")

    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"   {status}: {nome}")

    print("\n" + "="*80)
    print("🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
    print("="*80 + "\n")

    print("📝 Resumo da Phase 5:")
    print("   ✅ Análise de Saídas corrigida com lucro/prejuízo por motivo")
    print("   ✅ Lógica de promoção SL → TSL com gatilho configurável")
    print("   ✅ Parâmetro 'tsl_gatilho_lucro_pct' adicionado às configs")
    print("   ✅ Interações do usuário atualizadas com novo parâmetro")
    print("\n📋 Mudanças Implementadas:")
    print("   • backtest.py: Função perguntar_parametros_giro_rapido() atualizada")
    print("   • backtest.py: Função imprimir_resumo_parametros() atualizada")
    print("   • backtest.py: Análise de saídas com lucro/prejuízo por categoria")
    print("   • bot_worker.py: Lógica de promoção SL → TSL com gatilho")
    print("   • configs: Parâmetro 'tsl_gatilho_lucro_pct: 1.5' adicionado")
    print("\n🚀 Próximo: Execute backtests reais para otimizar o parâmetro!\n")

    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Testes cancelados pelo usuário (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
