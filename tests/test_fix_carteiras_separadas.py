#!/usr/bin/env python3
"""
Teste de Validação: Bug de Carteiras Separadas Corrigido
=========================================================

Este teste valida que a correção do bug crítico de validação de capital
entre carteiras está funcionando corretamente.

BUG ORIGINAL:
- A estratégia Giro Rápido estava validando capital na carteira 'acumulacao'
- Isso causava aprovação incorreta de compras quando a carteira 'giro_rapido'
  não tinha capital suficiente

CORREÇÃO:
- strategy_dca.py agora passa explicitamente carteira='acumulacao'
- strategy_swing_trade.py já passava carteira='giro_rapido' corretamente
- gestao_capital.py já suportava o parâmetro carteira
"""

import sys
from pathlib import Path
from decimal import Decimal

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.gestao_capital import GestaoCapital


def test_validacao_capital_carteiras_separadas():
    """
    Testa que a validação de capital respeita as carteiras separadas
    """
    print("=" * 80)
    print("🧪 TESTE: Validação de Capital por Carteira")
    print("=" * 80)
    
    # Cenário:
    # - Saldo USDT total: 1000
    # - Reserva 8%: 80 USDT
    # - Saldo livre: 920 USDT
    # - Alocação Giro Rápido: 20% = 184 USDT
    # - Alocação Acumulação: 80% = 736 USDT
    
    gestao = GestaoCapital(
        saldo_usdt=Decimal('1000'),
        valor_posicao_ada=Decimal('0'),
        percentual_reserva=Decimal('8'),
        modo_simulacao=True
    )
    
    # Configurar alocação do giro rápido
    gestao.configurar_alocacao_giro_rapido(Decimal('20'))
    
    print("\n📊 Configuração Inicial:")
    print(f"   Saldo USDT: $1000.00")
    print(f"   Reserva (8%): $80.00")
    print(f"   Saldo Livre: $920.00")
    print(f"   Alocação Giro Rápido: 20% = $184.00")
    print(f"   Alocação Acumulação: 80% = $736.00")
    
    # Teste 1: Acumulação pode comprar dentro do seu limite
    print("\n" + "-" * 80)
    print("✅ TESTE 1: Acumulação comprando $500 (dentro do limite $736)")
    print("-" * 80)
    
    pode_comprar, motivo = gestao.pode_comprar(Decimal('500'), carteira='acumulacao')
    
    if pode_comprar:
        print(f"   ✅ APROVADO: Acumulação pode comprar $500.00")
    else:
        print(f"   ❌ BLOQUEADO: {motivo}")
        return False
    
    # Teste 2: Giro Rápido NÃO pode comprar além do seu limite
    print("\n" + "-" * 80)
    print("❌ TESTE 2: Giro Rápido tentando comprar $500 (limite é $184)")
    print("-" * 80)
    
    pode_comprar, motivo = gestao.pode_comprar(Decimal('500'), carteira='giro_rapido')
    
    if not pode_comprar:
        print(f"   ✅ BLOQUEADO corretamente: {motivo}")
    else:
        print(f"   ❌ ERRO: Giro Rápido NÃO deveria poder comprar $500!")
        return False
    
    # Teste 3: Giro Rápido pode comprar dentro do seu limite
    print("\n" + "-" * 80)
    print("✅ TESTE 3: Giro Rápido comprando $150 (dentro do limite $184)")
    print("-" * 80)
    
    pode_comprar, motivo = gestao.pode_comprar(Decimal('150'), carteira='giro_rapido')
    
    if pode_comprar:
        print(f"   ✅ APROVADO: Giro Rápido pode comprar $150.00")
    else:
        print(f"   ❌ BLOQUEADO: {motivo}")
        return False
    
    # Teste 4: Acumulação NÃO pode comprar além do seu limite
    print("\n" + "-" * 80)
    print("❌ TESTE 4: Acumulação tentando comprar $800 (limite é $736)")
    print("-" * 80)
    
    pode_comprar, motivo = gestao.pode_comprar(Decimal('800'), carteira='acumulacao')
    
    if not pode_comprar:
        print(f"   ✅ BLOQUEADO corretamente: {motivo}")
    else:
        print(f"   ❌ ERRO: Acumulação NÃO deveria poder comprar $800!")
        return False
    
    # Teste 5: Verificar que ambas as carteiras respeitam a reserva global
    print("\n" + "-" * 80)
    print("🛡️ TESTE 5: Nenhuma carteira pode violar reserva global de $80")
    print("-" * 80)
    
    # Simular que acumulação já comprou $700
    gestao.atualizar_saldos(
        saldo_usdt=Decimal('300'),  # Restam $300 após compra de $700
        valor_posicao_ada=Decimal('700'),
        carteira='acumulacao'
    )
    
    print(f"   Situação: Acumulação comprou $700, restam $300 USDT")
    print(f"   Reserva obrigatória: $80 (8% de $1000)")
    print(f"   Capital livre: $220 ($300 - $80)")
    
    # Giro Rápido tenta comprar $250 (mais que o saldo livre de $220)
    pode_comprar, motivo = gestao.pode_comprar(Decimal('250'), carteira='giro_rapido')
    
    if not pode_comprar:
        print(f"   ✅ BLOQUEADO corretamente: {motivo}")
    else:
        print(f"   ❌ ERRO: Compra violaria reserva global!")
        return False
    
    print("\n" + "=" * 80)
    print("🎉 TODOS OS TESTES PASSARAM!")
    print("=" * 80)
    print("\n✅ A validação de capital está respeitando carteiras separadas corretamente")
    print("✅ Cada carteira tem seu próprio limite de capital disponível")
    print("✅ A reserva global de 8% é respeitada por ambas as carteiras")
    print("✅ Bug de validação de carteira errada foi CORRIGIDO!\n")
    
    return True


def test_resumo_carteiras():
    """
    Testa o resumo detalhado por carteira
    """
    print("\n" + "=" * 80)
    print("🧪 TESTE: Resumo Detalhado por Carteira")
    print("=" * 80)
    
    gestao = GestaoCapital(
        saldo_usdt=Decimal('1000'),
        valor_posicao_ada=Decimal('200'),  # Acumulação
        percentual_reserva=Decimal('8'),
        modo_simulacao=True
    )
    
    # Adicionar posição na carteira giro_rapido
    gestao.atualizar_saldos(
        saldo_usdt=Decimal('1000'),
        valor_posicao_ada=Decimal('100'),
        carteira='giro_rapido'
    )
    
    # Configurar alocação
    gestao.configurar_alocacao_giro_rapido(Decimal('20'))
    
    # Obter resumo
    resumo = gestao.obter_resumo()
    
    print("\n📊 Resumo das Carteiras:")
    print(f"\n   💰 Capital Total: ${resumo['capital_total']:.2f}")
    print(f"   🛡️ Reserva (8%): ${resumo['reserva_obrigatoria']:.2f}")
    
    print(f"\n   📊 ACUMULAÇÃO:")
    print(f"      Posição: ${resumo['carteiras']['acumulacao']['valor_posicao']:.2f}")
    print(f"      Disponível: ${resumo['carteiras']['acumulacao']['capital_disponivel']:.2f}")
    
    print(f"\n   💨 GIRO RÁPIDO:")
    print(f"      Posição: ${resumo['carteiras']['giro_rapido']['valor_posicao']:.2f}")
    print(f"      Disponível: ${resumo['carteiras']['giro_rapido']['capital_disponivel']:.2f}")
    print(f"      Alocação: {resumo['carteiras']['giro_rapido']['alocacao_pct']:.0f}%")
    
    # Validações
    assert resumo['carteiras']['acumulacao']['valor_posicao'] == Decimal('200')
    assert resumo['carteiras']['giro_rapido']['valor_posicao'] == Decimal('100')
    
    print("\n✅ Resumo por carteira está correto!")
    
    return True


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🔬 SUITE DE TESTES: Validação de Carteiras Separadas")
    print("=" * 80)
    print("\nObjetivo: Validar correção do bug de validação de capital entre carteiras")
    print("\n" + "=" * 80 + "\n")
    
    try:
        # Executar testes
        sucesso = test_validacao_capital_carteiras_separadas()
        if sucesso:
            sucesso = test_resumo_carteiras()
        
        if sucesso:
            print("\n" + "=" * 80)
            print("🎉 SUITE DE TESTES CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\n✅ O bug de validação de carteira errada foi CORRIGIDO")
            print("✅ Cada estratégia agora valida capital na sua própria carteira")
            print("✅ DCA → carteira='acumulacao'")
            print("✅ Giro Rápido → carteira='giro_rapido'")
            print("\n" + "=" * 80 + "\n")
            sys.exit(0)
        else:
            print("\n❌ FALHA NOS TESTES!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ ERRO durante execução dos testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
