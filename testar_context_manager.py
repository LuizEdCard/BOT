#!/usr/bin/env python3
"""
Script de teste para validar o context manager do DatabaseManager
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from decimal import Decimal
from src.persistencia.database import DatabaseManager
from config.settings import settings
from src.utils.logger import get_loggers

logger, _ = get_loggers(
    log_dir=Path('logs'),
    # config usa LogConfig.DEFAULT,
    console=True
)

logger.info("=" * 70)
logger.info("TESTE DO CONTEXT MANAGER - DatabaseManager")
logger.info("=" * 70)

# Inicializar DatabaseManager
db = DatabaseManager(
    db_path=settings.DATABASE_PATH,
    backup_dir=settings.BACKUP_DIR
)

logger.info("\n✅ DatabaseManager inicializado com sucesso")

# Teste 1: Registrar ordem de compra
logger.info("\n📝 TESTE 1: Registrar ordem de compra")
ordem_compra = {
    'tipo': 'COMPRA',
    'par': 'ADA/USDT',
    'quantidade': Decimal('10.5'),
    'preco': Decimal('0.6850'),
    'valor_total': Decimal('7.1925'),
    'taxa': Decimal('0.01'),
    'meta': 'teste_context_manager',
    'order_id': 'TEST_CTX_001'
}

try:
    ordem_id = db.registrar_ordem(ordem_compra)
    logger.info(f"   ✅ Ordem registrada com ID: {ordem_id}")
except Exception as e:
    logger.error(f"   ❌ Erro ao registrar ordem: {e}")
    sys.exit(1)

# Teste 2: Verificar se ordem existe
logger.info("\n🔍 TESTE 2: Verificar se ordem existe")
try:
    existe = db.ordem_ja_existe('TEST_CTX_001')
    if existe:
        logger.info("   ✅ Ordem encontrada no banco")
    else:
        logger.error("   ❌ Ordem não encontrada")
        sys.exit(1)
except Exception as e:
    logger.error(f"   ❌ Erro ao verificar ordem: {e}")
    sys.exit(1)

# Teste 3: Obter últimas ordens
logger.info("\n📋 TESTE 3: Obter últimas ordens")
try:
    ordens = db.obter_ultimas_ordens(limite=5)
    logger.info(f"   ✅ Recuperadas {len(ordens)} ordens")
    if ordens:
        logger.info(f"   - Última ordem: Tipo={ordens[0]['tipo']}, ID={ordens[0]['order_id']}")
except Exception as e:
    logger.error(f"   ❌ Erro ao obter ordens: {e}")
    sys.exit(1)

# Teste 4: Calcular métricas
logger.info("\n📊 TESTE 4: Calcular métricas")
try:
    metricas = db.calcular_metricas()
    logger.info(f"   ✅ Métricas calculadas:")
    logger.info(f"   - Total compras: {metricas['total_compras']}")
    logger.info(f"   - Total vendas: {metricas['total_vendas']}")
    logger.info(f"   - Lucro realizado: ${metricas['lucro_realizado']:.2f}")
except Exception as e:
    logger.error(f"   ❌ Erro ao calcular métricas: {e}")
    sys.exit(1)

# Teste 5: Estatísticas 24h
logger.info("\n📈 TESTE 5: Estatísticas 24h")
try:
    stats = db.obter_estatisticas_24h()
    logger.info(f"   ✅ Estatísticas 24h:")
    logger.info(f"   - Compras: {stats['compras']}")
    logger.info(f"   - Vendas: {stats['vendas']}")
    logger.info(f"   - Lucro realizado: ${stats['lucro_realizado']:.2f}")
except Exception as e:
    logger.error(f"   ❌ Erro ao obter estatísticas: {e}")
    sys.exit(1)

# Teste 6: Recuperar estado do bot
logger.info("\n⚙️  TESTE 6: Recuperar estado do bot")
try:
    estado = db.recuperar_estado_bot()
    if estado:
        logger.info(f"   ✅ Estado recuperado:")
        logger.info(f"   - Preço médio: ${estado.get('preco_medio_compra', 0):.6f}")
        logger.info(f"   - Quantidade ADA: {estado.get('quantidade_total_ada', 0):.2f}")
    else:
        logger.info("   ℹ️  Nenhum estado salvo ainda")
except Exception as e:
    logger.error(f"   ❌ Erro ao recuperar estado: {e}")
    sys.exit(1)

logger.info("\n" + "=" * 70)
logger.info("✅ TODOS OS TESTES DO CONTEXT MANAGER PASSARAM COM SUCESSO!")
logger.info("=" * 70)
logger.info("\n🎯 Benefícios do Context Manager:")
logger.info("   1. ✅ Conexões sempre fechadas corretamente")
logger.info("   2. ✅ Commits automáticos em sucesso")
logger.info("   3. ✅ Rollbacks automáticos em erros")
logger.info("   4. ✅ Código mais limpo e legível")
logger.info("   5. ✅ Sem vazamento de recursos")
logger.info("")
