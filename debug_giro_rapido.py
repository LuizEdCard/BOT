#!/usr/bin/env python3
"""
Script de debug para rastrear fluxo de configuração do Giro Rápido
Simula as respostas do usuário através de stdin
"""

import sys
import subprocess
import json
from pathlib import Path

# Configurações de teste
config_file = "configs/backtest_template.json"
csv_file = "dados/historicos/BINANCE_ADAUSDT_5m_2017-01-01_2025-10-25.csv"

# Simulações de entrada (as respostas que o usuário daria)
entrada_stdin = """estrategia_exemplo_giro_rapido.json
{csv_file}
5m
1000
0.1
giro_rapido
n
y
35.0
5m
1.0
0.5
2.5
50
y
""".format(csv_file=csv_file)

print("=" * 80)
print("🐛 DEBUG: Rastreando fluxo de configuração do Giro Rápido")
print("=" * 80)
print("\nSimulando entrada do usuário...")
print(f"  Config: estrategia_exemplo_giro_rapido.json")
print(f"  CSV: {csv_file}")
print(f"  Timeframe: 5m")
print(f"  Saldo: 1000")
print(f"  Taxa: 0.1%")
print(f"  Estratégia: giro_rapido")
print(f"  Alocação de Capital solicitada: 50%")
print()

# Executar backtest.py com stdin simulado
proc = subprocess.Popen(
    ["python", "backtest.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd="/home/cardoso/Documentos/BOT"
)

# Enviar entrada
stdout, _ = proc.communicate(input=entrada_stdin)

# Processar output
output_lines = stdout.split('\n')

# Procurar pelos debug statements
print("📋 Output de debug encontrado:")
print("-" * 80)

for i, line in enumerate(output_lines):
    # Procurar por linhas de debug
    if '[DEBUG]' in line or 'RESUMO' in line or 'Alocação' in line or 'TSL Gatilho' in line:
        print(line)
        # Imprimir próximas 10 linhas se for RESUMO
        if 'RESUMO' in line:
            for j in range(i+1, min(i+15, len(output_lines))):
                print(output_lines[j])
            break

print("\n" + "=" * 80)
print("🔍 Análise:")
print("=" * 80)

# Procurar pela alocação de capital no resumo
for i, line in enumerate(output_lines):
    if 'Alocação de Capital:' in line and 'Giro Rápido' in output_lines[max(0, i-5):i][-1]:
        print(f"\n✅ Encontrado: {line}")
        # Checar se é 50% ou 20%
        if '50%' in line:
            print("✅ Alocação CORRETA (50% conforme configurado)")
        elif '20%' in line:
            print("❌ Alocação INCORRETA (20% em vez de 50%)")
            print("   Problema: Parâmetro não foi aplicado!")
        break

print()
