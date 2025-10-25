#!/usr/bin/env python3
"""
Script de debug para backtest - salva logs detalhados em arquivo
Útil para investigar problemas de saldo e operações
"""

import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime

def criar_debug_backtest():
    """Executa backtest salvando logs em arquivo"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(f"logs/backtest_debug_{timestamp}.log")
    log_file.parent.mkdir(exist_ok=True)

    print(f"🔍 Executando backtest com debug...")
    print(f"📝 Logs serão salvos em: {log_file}")
    print(f"⏳ Por favor aguarde o backtest terminar...")

    # Executar backtest com stdout/stderr redirecionados para arquivo
    cmd = [
        "python", "backtest.py",
        "--non-interactive",
        "--config", "configs/backtest_template.json",
        "--csv", "dados/historicos/BINANCE_ADAUSDT_1m_2025-01-01_2025-02-01.csv",
        "--timeframe", "1h",
        "--saldo", "1000",
        "--taxa", "0.1",
        "--estrategias", "ambas"
    ]

    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True
            )
            process.wait()

        print(f"\n✅ Backtest concluído!")
        print(f"📄 Arquivo de log criado: {log_file}")
        print(f"\n📊 Resumo do log:")
        print(f"   Linhas totais: {sum(1 for _ in open(log_file))}")

        # Mostrar as últimas linhas
        print(f"\n📋 Últimas 30 linhas do log:")
        print("=" * 80)
        with open(log_file, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
            for linha in linhas[-30:]:
                print(linha.rstrip())

        # Procurar por erros críticos
        print(f"\n🔴 Erros encontrados:")
        print("=" * 80)
        com_erro = False
        with open(log_file, 'r', encoding='utf-8') as f:
            for i, linha in enumerate(f, 1):
                if 'ERROR' in linha or 'Erro' in linha:
                    print(f"Linha {i}: {linha.rstrip()}")
                    com_erro = True

        if not com_erro:
            print("✅ Nenhum erro crítico encontrado!")

        # Análise de saldo
        print(f"\n💰 Análise de saldos:")
        print("=" * 80)
        with open(log_file, 'r', encoding='utf-8') as f:
            for linha in f:
                if 'Saldo insuficiente' in linha or 'Disponível:' in linha:
                    print(linha.rstrip())

        print(f"\n💡 Dica: Para analisar o arquivo completo, use:")
        print(f"   cat {log_file}")
        print(f"   grep 'ERROR' {log_file}")
        print(f"   grep 'Saldo insuficiente' {log_file}")
        print(f"   tail -100 {log_file}")

    except Exception as e:
        print(f"❌ Erro ao executar backtest: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(criar_debug_backtest())
