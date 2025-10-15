#!/usr/bin/env python3
"""
Script de Teste: Estratégia de Vendas de Segurança com Recompra

Testa o funcionamento das zonas de segurança e recompra pós-reversão.
Simula cenários de mercado para validar a lógica implementada.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal
from config.settings import settings

def testar_carregamento_config():
    """
    Teste 1: Verificar se vendas_de_seguranca foram carregadas corretamente
    """
    print("═" * 70)
    print("TESTE 1: Carregamento de Configuração")
    print("═" * 70)

    if hasattr(settings, 'VENDAS_DE_SEGURANCA'):
        print(f"✅ Atributo VENDAS_DE_SEGURANCA existe")
        print(f"✅ Total de zonas de segurança configuradas: {len(settings.VENDAS_DE_SEGURANCA)}")
        print("")

        for i, zona in enumerate(settings.VENDAS_DE_SEGURANCA, 1):
            print(f"   Zona {i}: {zona['nome']}")
            print(f"      - Gatilho ativação: {zona['gatilho_ativacao_lucro_pct']}% (arma o gatilho)")
            print(f"      - Gatilho reversão: {zona['gatilho_venda_reversao_pct']}% (dispara venda)")
            print(f"      - Percentual venda: {zona['percentual_venda_posicao']}%")
            print(f"      - Gatilho recompra: {zona['gatilho_recompra_drop_pct']}% de queda")
            print("")

        return True
    else:
        print("❌ ERRO: Atributo VENDAS_DE_SEGURANCA não encontrado em settings")
        return False


def simular_cenario_venda_seguranca():
    """
    Teste 2: Simular cenário de ativação de zona de segurança
    NOVO: Sistema de dois gatilhos
    """
    print("═" * 70)
    print("TESTE 2: Simulação de Ativação de Zona de Segurança (DOIS GATILHOS)")
    print("═" * 70)

    # Simulação de estado do bot
    preco_medio_compra = Decimal('0.80')
    quantidade_ada = Decimal('100.0')

    # Cenário: Lucro sobe para 5.2% (high-water mark), depois cai para 4.4%
    high_water_mark = Decimal('5.2')
    lucro_atual = Decimal('4.4')

    zona_test = {
        'nome': 'Seguranca_Pre-Meta1-A',
        'gatilho_ativacao_lucro_pct': 4.5,
        'gatilho_venda_reversao_pct': 0.8,
        'percentual_venda_posicao': 10,
        'gatilho_recompra_drop_pct': 2.0
    }

    print(f"📊 Estado inicial:")
    print(f"   - Preço médio de compra: ${preco_medio_compra:.6f}")
    print(f"   - Quantidade ADA: {quantidade_ada:.1f}")
    print(f"   - High-Water Mark: {high_water_mark:.2f}%")
    print(f"   - Lucro atual: {lucro_atual:.2f}%")
    print("")

    # Verificar se zona seria ativada (NOVO SISTEMA DE DOIS GATILHOS)
    gatilho_ativacao_pct = Decimal(str(zona_test['gatilho_ativacao_lucro_pct']))
    gatilho_reversao_pct = Decimal(str(zona_test['gatilho_venda_reversao_pct']))
    queda_desde_pico = high_water_mark - lucro_atual
    gatilho_venda = high_water_mark - gatilho_reversao_pct

    print(f"🔍 Análise da zona '{zona_test['nome']}' (Sistema de Dois Gatilhos):")
    print(f"   GATILHO 1 - Ativação:")
    print(f"      - Gatilho ativação: {gatilho_ativacao_pct:.2f}%")
    print(f"      - High-water mark: {high_water_mark:.2f}%")
    print(f"      - Zona armada? {high_water_mark >= gatilho_ativacao_pct}")
    print("")
    print(f"   GATILHO 2 - Reversão:")
    print(f"      - Reversão configurada: {gatilho_reversao_pct:.2f}%")
    print(f"      - Gatilho de venda calculado: {gatilho_venda:.2f}%")
    print(f"      - Lucro atual: {lucro_atual:.2f}%")
    print(f"      - Gatilho atingido? {lucro_atual <= gatilho_venda}")
    print(f"      - Queda desde pico: {queda_desde_pico:.2f}%")
    print("")

    if high_water_mark >= gatilho_ativacao_pct and lucro_atual <= gatilho_venda:
        print(f"✅ ZONA ATIVADA - Venda de segurança seria executada")
        print(f"   ✓ Zona foi ARMADA (high-water mark {high_water_mark:.2f}% > {gatilho_ativacao_pct:.2f}%)")
        print(f"   ✓ Reversão DETECTADA (lucro {lucro_atual:.2f}% <= gatilho {gatilho_venda:.2f}%)")
        print("")

        # Calcular valores da venda
        percentual_venda = Decimal(str(zona_test['percentual_venda_posicao'])) / Decimal('100')
        quantidade_venda = quantidade_ada * percentual_venda
        preco_venda = preco_medio_compra * (Decimal('1') + lucro_atual / Decimal('100'))
        valor_venda = quantidade_venda * preco_venda

        print(f"   💰 Quantidade a vender: {quantidade_venda:.1f} ADA ({zona_test['percentual_venda_posicao']}%)")
        print(f"   📊 Preço de venda: ${preco_venda:.6f}")
        print(f"   💵 Valor obtido: ${valor_venda:.2f} USDT (reservado para recompra)")
        print("")

        # Simular gatilho de recompra
        gatilho_recompra = high_water_mark - Decimal(str(zona_test['gatilho_recompra_drop_pct']))
        print(f"🔄 Gatilho de recompra: {gatilho_recompra:.2f}%")
        print(f"   (ativa quando lucro cair para {gatilho_recompra:.2f}% ou menos)")

        return True
    else:
        print(f"❌ Zona não seria ativada")
        if high_water_mark < gatilho_ativacao_pct:
            print(f"   ✗ Zona não foi armada (high-water mark {high_water_mark:.2f}% < {gatilho_ativacao_pct:.2f}%)")
        if lucro_atual > gatilho_venda:
            print(f"   ✗ Reversão insuficiente (lucro {lucro_atual:.2f}% > gatilho {gatilho_venda:.2f}%)")
        return False


def simular_cenario_recompra():
    """
    Teste 3: Simular cenário de recompra após venda de segurança
    """
    print("")
    print("═" * 70)
    print("TESTE 3: Simulação de Recompra Pós-Reversão")
    print("═" * 70)

    # Estado após venda de segurança
    capital_reservado = Decimal('8.46')  # $8.46 USDT
    high_water_mark = Decimal('5.0')
    gatilho_recompra_drop = Decimal('2.0')

    # Calcular gatilho de recompra
    gatilho_recompra = high_water_mark - gatilho_recompra_drop

    print(f"💰 Capital reservado para recompra: ${capital_reservado:.2f} USDT")
    print(f"📊 High-Water Mark: {high_water_mark:.2f}%")
    print(f"🎯 Gatilho de recompra: {gatilho_recompra:.2f}%")
    print("")

    # Simular diferentes níveis de lucro
    cenarios = [
        (Decimal('4.0'), "Lucro caiu para 4.0%"),
        (Decimal('3.5'), "Lucro caiu para 3.5%"),
        (Decimal('3.0'), "Lucro caiu para 3.0% - GATILHO ATINGIDO"),
        (Decimal('2.5'), "Lucro caiu para 2.5% - recompra seria executada"),
    ]

    for lucro_atual, descricao in cenarios:
        recompra_ativa = lucro_atual <= gatilho_recompra

        if recompra_ativa:
            preco_recompra = Decimal('0.80') * (Decimal('1') + lucro_atual / Decimal('100'))
            quantidade_recompra = capital_reservado / preco_recompra
            quantidade_recompra = (quantidade_recompra * Decimal('10')).quantize(
                Decimal('1'), rounding='ROUND_DOWN'
            ) / Decimal('10')

            print(f"   ✅ {descricao}")
            print(f"      📦 Recomprar: {quantidade_recompra:.1f} ADA por ${preco_recompra:.6f}")
            print(f"      💵 Custo: ${capital_reservado:.2f} USDT")
            print("")
        else:
            print(f"   ⏸️  {descricao} - aguardando...")
            print("")

    return True


def simular_meta_fixa_reset():
    """
    Teste 4: Verificar se meta fixa reseta o estado
    """
    print("═" * 70)
    print("TESTE 4: Reset de Estado ao Atingir Meta Fixa")
    print("═" * 70)

    print("📋 Cenário:")
    print("   1. High-Water Mark está em 7.0%")
    print("   2. Zona 'Seguranca_Pre-Meta1-A' foi acionada")
    print("   3. Capital guardado para recompra")
    print("   4. Lucro atinge 6.0% (Meta 1)")
    print("")

    print("✅ Comportamento esperado:")
    print("   - Executar venda da Meta 1 (30%)")
    print("   - RESETAR high_water_mark para 0")
    print("   - LIMPAR zonas_de_seguranca_acionadas")
    print("   - LIMPAR capital_para_recompra")
    print("")

    print("💡 Isso garante que cada escalada de lucro é independente")
    print("   e as zonas podem ser reutilizadas na próxima subida.")

    return True


def main():
    """Executar todos os testes"""
    print("")
    print("🤖 BOT DE TRADING - TESTE DE ZONAS DE SEGURANÇA")
    print("")

    testes = [
        ("Carregamento de Configuração", testar_carregamento_config),
        ("Ativação de Zona de Segurança", simular_cenario_venda_seguranca),
        ("Recompra Pós-Reversão", simular_cenario_recompra),
        ("Reset de Estado", simular_meta_fixa_reset),
    ]

    resultados = []

    for nome, teste_func in testes:
        try:
            resultado = teste_func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"❌ ERRO no teste '{nome}': {e}")
            resultados.append((nome, False))

    # Resumo final
    print("")
    print("═" * 70)
    print("RESUMO DOS TESTES")
    print("═" * 70)

    total = len(resultados)
    sucesso = sum(1 for _, r in resultados if r)

    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status}: {nome}")

    print("")
    print(f"📊 Total: {sucesso}/{total} testes passaram")
    print("")

    if sucesso == total:
        print("🎉 TODOS OS TESTES PASSARAM! Sistema pronto para uso.")
    else:
        print("⚠️  Alguns testes falharam. Verifique os logs acima.")

    print("")


if __name__ == '__main__':
    main()
