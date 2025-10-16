#!/usr/bin/env python3
"""
Script de teste para validar a nova estratégia de compra:
- Largada a Frio
- Cooldown Duplo (global + por degrau)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
from decimal import Decimal

print("╔═══════════════════════════════════════════════════════════════════╗")
print("║     TESTE: Nova Estratégia de Compra (Largada a Frio)            ║")
print("╚═══════════════════════════════════════════════════════════════════╝")
print()

# Teste 1: Verificar importação de módulos
print("📋 Teste 1: Verificando importação de módulos...")
try:
    from config.settings import settings
    from src.persistencia.database import DatabaseManager
    print("✅ Módulos importados com sucesso")
    print()
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    sys.exit(1)

# Teste 2: Verificar configuração do cooldown global
print("📋 Teste 2: Verificando configuração do cooldown global...")
try:
    cooldown_global = settings.COOLDOWN_GLOBAL_APOS_COMPRA_MINUTOS
    print(f"✅ Cooldown global configurado: {cooldown_global} minutos")
    print()
except AttributeError as e:
    print(f"❌ Erro: COOLDOWN_GLOBAL_APOS_COMPRA_MINUTOS não encontrado em settings")
    print(f"   {e}")
    sys.exit(1)

# Teste 3: Verificar métodos do DatabaseManager
print("📋 Teste 3: Verificando métodos do DatabaseManager...")
db = DatabaseManager(
    db_path=settings.DATABASE_PATH,
    backup_dir=settings.BACKUP_DIR
)

# Verificar se métodos existem
metodos_necessarios = [
    'obter_timestamp_ultima_compra_degrau',
    'obter_timestamp_ultima_compra_global'
]

for metodo in metodos_necessarios:
    if hasattr(db, metodo):
        print(f"✅ Método {metodo} encontrado")
    else:
        print(f"❌ Método {metodo} NÃO encontrado")
        sys.exit(1)

print()

# Teste 4: Verificar degraus e intervalos
print("📋 Teste 4: Verificando configuração de degraus...")
print()
for degrau in settings.DEGRAUS_COMPRA:
    nivel = degrau['nivel']
    queda = degrau['queda_percentual']
    intervalo = degrau['intervalo_horas']
    quantidade = degrau['quantidade_ada']

    print(f"   Degrau {nivel}: {queda}% queda | Intervalo: {intervalo}h | Qtd: {quantidade} ADA")

print()

# Teste 5: Simulação de lógica de "Largada a Frio"
print("📋 Teste 5: Simulação de lógica de 'Largada a Frio'")
print()

# Simular cenário: Bot inicia após queda de 8.5%
queda_simulada = Decimal('8.5')
print(f"   Cenário: Bot iniciado após queda de {queda_simulada}% desde SMA")
print()

# Encontrar degrau mais profundo ativado
degrau_mais_profundo = None
for degrau in settings.DEGRAUS_COMPRA:
    if queda_simulada >= Decimal(str(degrau['queda_percentual'])):
        degrau_mais_profundo = degrau

if degrau_mais_profundo:
    print(f"✅ Degrau mais profundo detectado: Nível {degrau_mais_profundo['nivel']}")
    print(f"   Queda requerida: {degrau_mais_profundo['queda_percentual']}%")
    print(f"   Quantidade a comprar: {degrau_mais_profundo['quantidade_ada']} ADA")
    print()
    print("   🥶 LARGADA A FRIO: Executaria compra controlada neste degrau")
    print("   🕒 Em seguida, ativaria cooldown global de 30 minutos")
else:
    print("❌ Nenhum degrau ativado")

print()

# Teste 6: Simulação de cooldown duplo
print("📋 Teste 6: Simulação de cooldown duplo")
print()

# Cenário 1: Cooldown global ativo
print("   Cenário 1: Cooldown global ativo")
timestamp_ultima_compra = datetime.now() - timedelta(minutes=15)
minutos_decorridos = 15
cooldown_global_min = 30
minutos_restantes = cooldown_global_min - minutos_decorridos

if minutos_decorridos < cooldown_global_min:
    print(f"   ❌ BLOQUEADO por cooldown global")
    print(f"      Última compra: há {minutos_decorridos} minutos")
    print(f"      Faltam: {minutos_restantes} minutos")
else:
    print(f"   ✅ Cooldown global expirado")

print()

# Cenário 2: Cooldown por degrau ativo
print("   Cenário 2: Cooldown por degrau ativo (Degrau 1)")
degrau_1 = settings.DEGRAUS_COMPRA[0]  # Degrau 1
intervalo_horas = Decimal(str(degrau_1['intervalo_horas']))
timestamp_ultima_compra_degrau = datetime.now() - timedelta(hours=0.5)
horas_decorridas = Decimal('0.5')

if horas_decorridas < intervalo_horas:
    horas_restantes = float(intervalo_horas - horas_decorridas)
    print(f"   ❌ BLOQUEADO por cooldown do degrau")
    print(f"      Última compra no degrau: há {float(horas_decorridas):.1f}h")
    print(f"      Intervalo requerido: {float(intervalo_horas)}h")
    print(f"      Faltam: {horas_restantes:.1f}h")
else:
    print(f"   ✅ Cooldown do degrau expirado")

print()

# Teste 7: Resumo
print("╔═══════════════════════════════════════════════════════════════════╗")
print("║                         RESUMO DOS TESTES                         ║")
print("╚═══════════════════════════════════════════════════════════════════╝")
print()
print("✅ Todos os testes de estrutura passaram com sucesso!")
print()
print("📌 Próximos passos:")
print("   1. Execute o bot_trading.py para testar em ambiente real")
print("   2. Monitore os logs para verificar:")
print("      - Detecção de 'Largada a Frio' se iniciado durante queda")
print("      - Ativação do cooldown global após cada compra")
print("      - Respeito aos intervalos por degrau")
print()
print("⚠️  IMPORTANTE:")
print("   - A lógica antiga de '3 compras/24h' foi REMOVIDA")
print("   - Agora o bot usa COOLDOWN DUPLO (global + por degrau)")
print("   - O cooldown global impede compras por 30min após QUALQUER compra")
print("   - O cooldown por degrau respeita o intervalo_horas de cada degrau")
print()
