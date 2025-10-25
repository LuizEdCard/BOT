#!/usr/bin/env python3
"""
Script para analisar o problema de 'Saldo insuficiente'
Identifica quando/onde o problema ocorre nos logs
"""

import sys
from pathlib import Path
from collections import defaultdict

def analisar_saldo(arquivo_log):
    """Analisa logs procurando por problemas de saldo"""

    if not Path(arquivo_log).exists():
        print(f"❌ Arquivo não encontrado: {arquivo_log}")
        return 1

    print(f"📊 Analisando: {arquivo_log}\n")

    problemas_saldo = []
    vendas_executadas = []
    compras_bloqueadas_saldo = []
    compras_executadas = []
    carteira_saldos = defaultdict(lambda: {"usdt": 1000.0, "ativo": 0.0})

    with open(arquivo_log, 'r', encoding='utf-8') as f:
        for num_linha, linha in enumerate(f, 1):
            # Procurar compras executadas
            if "🟢 COMPRA" in linha and "Qtd:" in linha:
                compras_executadas.append((num_linha, linha.strip()))

            # Procurar vendas executadas
            elif "🔴 VENDA" in linha and "Qtd:" in linha:
                vendas_executadas.append((num_linha, linha.strip()))

            # Procurar erros de saldo
            elif "Saldo insuficiente" in linha:
                compras_bloqueadas_saldo.append((num_linha, linha.strip()))
                problemas_saldo.append(num_linha)

    print("=" * 100)
    print("📈 RESUMO")
    print("=" * 100)
    print(f"✅ Compras executadas: {len(compras_executadas)}")
    print(f"✅ Vendas executadas: {len(vendas_executadas)}")
    print(f"❌ Compras bloqueadas por saldo insuficiente: {len(compras_bloqueadas_saldo)}")

    if compras_bloqueadas_saldo:
        print(f"\n🔴 PRIMEIRA OCORRÊNCIA DE 'SALDO INSUFICIENTE':")
        print("=" * 100)
        linha_num, msg = compras_bloqueadas_saldo[0]
        print(f"Linha {linha_num}: {msg}")

        # Procurar contexto (compras/vendas anteriores)
        print(f"\n📍 CONTEXTO (últimas 5 operações antes do erro):")
        print("=" * 100)

        operacoes_antes = []
        for num, txt in compras_executadas + vendas_executadas:
            if num < linha_num:
                operacoes_antes.append((num, txt))

        for num, txt in sorted(operacoes_antes)[-5:]:
            tipo = "COMPRA" if "COMPRA" in txt else "VENDA"
            print(f"  Linha {num}: {tipo} - {txt[:100]}...")

        print(f"\n📊 PRÓXIMAS 3 ERROS DE SALDO:")
        print("=" * 100)
        for i, (linha_num, msg) in enumerate(compras_bloqueadas_saldo[:3]):
            print(f"{i+1}. Linha {linha_num}: {msg[:100]}...")

    # Procurar padrão: se as compras param mas as vendas continuam
    print(f"\n🔍 ANÁLISE DE PADRÃO:")
    print("=" * 100)

    if compras_bloqueadas_saldo:
        primeira_erro_linha = compras_bloqueadas_saldo[0][0]
        compras_antes_erro = [l for l, _ in compras_executadas if l < primeira_erro_linha]
        compras_depois_erro = [l for l, _ in compras_executadas if l > primeira_erro_linha]
        vendas_antes_erro = [l for l, _ in vendas_executadas if l < primeira_erro_linha]
        vendas_depois_erro = [l for l, _ in vendas_executadas if l > primeira_erro_linha]

        print(f"Antes do primeiro erro:")
        print(f"  - Compras: {len(compras_antes_erro)}")
        print(f"  - Vendas: {len(vendas_antes_erro)}")
        print(f"Depois do primeiro erro:")
        print(f"  - Compras: {len(compras_depois_erro)}")
        print(f"  - Vendas: {len(vendas_depois_erro)}")

        if len(compras_depois_erro) > 0:
            print(f"\n⚠️ AVISO: Bot continuou comprando após erro de saldo!")
        else:
            print(f"\n✅ Bot parou de comprar após atingir limite de saldo")

    # Procurar taxa cobrada
    print(f"\n💸 ANÁLISE DE TAXAS:")
    print("=" * 100)
    with open(arquivo_log, 'r', encoding='utf-8') as f:
        conteudo = f.read()
        if "taxa" in conteudo.lower():
            print("✅ Taxas estão sendo aplicadas no backtest")
        else:
            print("⚠️ Verificar se as taxas estão sendo aplicadas corretamente")

    # Procurar por resets de estado
    print(f"\n🔄 MUDANÇAS DE ESTADO:")
    print("=" * 100)
    resets = 0
    with open(arquivo_log, 'r', encoding='utf-8') as f:
        for num_linha, linha in enumerate(f, 1):
            if "Resetando" in linha or "reset" in linha.lower():
                resets += 1
                if resets <= 3:
                    print(f"Linha {num_linha}: {linha.strip()[:100]}")

    if resets > 3:
        print(f"... e mais {resets - 3} resets encontrados")

    print(f"\n💡 RECOMENDAÇÕES:")
    print("=" * 100)
    if compras_bloqueadas_saldo:
        print("1. ⚠️ Problema de saldo insuficiente detectado!")
        print("2. Verificar se as vendas estão creditando corretamente o saldo")
        print("3. Procurar por discrepâncias entre saldo esperado e real")
        print("4. Verificar se há retiradas de saldo não contabilizadas")
    else:
        print("✅ Nenhum problema de saldo detectado neste arquivo!")

    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Procurar pelo arquivo mais recente
        log_dir = Path("logs")
        if log_dir.exists():
            arquivos = sorted(log_dir.glob("backtest_debug_*.log"), key=lambda x: x.stat().st_mtime)
            if arquivos:
                arquivo = str(arquivos[-1])
                print(f"📂 Usando arquivo mais recente: {arquivo}\n")
            else:
                print("❌ Nenhum arquivo de log encontrado em logs/")
                sys.exit(1)
        else:
            print("❌ Diretório 'logs' não encontrado")
            sys.exit(1)
    else:
        arquivo = sys.argv[1]

    sys.exit(analisar_saldo(arquivo))
