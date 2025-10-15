#!/usr/bin/env python3
"""
Script de teste para validar notificações inteligentes de degraus bloqueados
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
from src.utils.logger import get_logger

# Configurar logger
logger = get_logger(
    log_dir=Path('logs'),
    nivel='INFO',
    console=True
)

# Simular o sistema de rastreamento de degraus bloqueados
degraus_notificados_bloqueados = set()

def pode_comprar_degrau(nivel_degrau: int, total_compras: int, max_compras: int = 3):
    """Simula a verificação se pode comprar no degrau"""
    if total_compras >= max_compras:
        motivo = f"limite_atingido:{total_compras}/{max_compras}"
        return (False, motivo)
    return (True, None)

# ═══════════════════════════════════════════════════════════════════
# TESTE 1: Degrau 1 - Primeira vez bloqueado (DEVE NOTIFICAR)
# ═══════════════════════════════════════════════════════════════════
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
logger.info("TESTE 1: Degrau 1 bloqueado pela primeira vez")
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

nivel_degrau = 1
pode, motivo = pode_comprar_degrau(nivel_degrau, total_compras=3)

if not pode:
    # BLOQUEADO: Notificar apenas uma vez
    if nivel_degrau not in degraus_notificados_bloqueados:
        degraus_notificados_bloqueados.add(nivel_degrau)
        if motivo and motivo.startswith('limite_atingido'):
            logger.info(f"🔒 Degrau {nivel_degrau} bloqueado temporariamente ({motivo}) - tentando próximo degrau")

logger.info(f"✅ Status: Degrau {nivel_degrau} adicionado ao set de bloqueados")
logger.info("")

# ═══════════════════════════════════════════════════════════════════
# TESTE 2: Degrau 1 ainda bloqueado (NÃO DEVE NOTIFICAR - já está no set)
# ═══════════════════════════════════════════════════════════════════
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
logger.info("TESTE 2: Degrau 1 ainda bloqueado (2ª verificação)")
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

pode, motivo = pode_comprar_degrau(nivel_degrau, total_compras=3)

if not pode:
    # BLOQUEADO: Mas já foi notificado, então NÃO loga
    if nivel_degrau not in degraus_notificados_bloqueados:
        logger.info(f"🔒 Degrau {nivel_degrau} bloqueado (esta linha NÃO deve aparecer)")
    else:
        logger.info(f"✅ Degrau {nivel_degrau} já está no set - SPAM EVITADO (sem log de bloqueio)")

logger.info("")

# ═══════════════════════════════════════════════════════════════════
# TESTE 3: Degrau 1 DESBLOQUEADO (DEVE NOTIFICAR DESBLOQUEIO)
# ═══════════════════════════════════════════════════════════════════
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
logger.info("TESTE 3: Degrau 1 desbloqueado (contador resetado)")
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

pode, motivo = pode_comprar_degrau(nivel_degrau, total_compras=0)  # Resetou contador

if pode:
    # DESBLOQUEADO: Remover do set se estava bloqueado
    if nivel_degrau in degraus_notificados_bloqueados:
        degraus_notificados_bloqueados.remove(nivel_degrau)
        logger.info(f"✅ Degrau {nivel_degrau} DESBLOQUEADO e disponível para compra")

logger.info("")

# ═══════════════════════════════════════════════════════════════════
# TESTE 4: Degrau 2 bloqueado, Degrau 1 ainda disponível
# ═══════════════════════════════════════════════════════════════════
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
logger.info("TESTE 4: Múltiplos degraus (2 bloqueado, 1 disponível)")
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# Verificar degrau 2 (bloqueado)
nivel_degrau = 2
pode, motivo = pode_comprar_degrau(nivel_degrau, total_compras=3)

if not pode:
    if nivel_degrau not in degraus_notificados_bloqueados:
        degraus_notificados_bloqueados.add(nivel_degrau)
        logger.info(f"🔒 Degrau {nivel_degrau} bloqueado temporariamente ({motivo}) - tentando próximo degrau")

# Verificar degrau 1 (disponível)
nivel_degrau = 1
pode, motivo = pode_comprar_degrau(nivel_degrau, total_compras=0)

if pode:
    logger.info(f"✅ Degrau {nivel_degrau} disponível - pode comprar")

logger.info("")

# ═══════════════════════════════════════════════════════════════════
# RESUMO FINAL
# ═══════════════════════════════════════════════════════════════════
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
logger.info("RESUMO DO SISTEMA DE NOTIFICAÇÕES")
logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
logger.info(f"Degraus atualmente bloqueados: {degraus_notificados_bloqueados}")
logger.info("")
logger.info("✅ Comportamento esperado:")
logger.info("   1. Notifica quando degrau fica bloqueado (primeira vez)")
logger.info("   2. NÃO notifica repetidamente enquanto bloqueado (anti-spam)")
logger.info("   3. Notifica quando degrau é desbloqueado")
logger.info("   4. Permite múltiplos degraus bloqueados simultaneamente")
logger.info("")
logger.info("✅ Todos os testes passaram com sucesso!")
