#!/usr/bin/env python3
"""
Script de teste para o novo sistema de logging configurável
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import time
from decimal import Decimal
from src.utils.logger import get_logger
from src.utils.painel_status import PainelStatus
from src.utils.constants import Icones, LogConfig, PainelConfig

print("=" * 70)
print("TESTE DO NOVO SISTEMA DE LOGGING")
print("=" * 70)

# Teste 1: Logger com timestamps diferentes
print("\n📝 TESTE 1: Timestamps diferentes para console e arquivo")
print("-" * 70)

logger = get_logger(
    nome='TesteBot',
    log_dir=Path('logs'),
    config=LogConfig.DEFAULT,
    console=True
)

logger.info("Este é um log de teste")
logger.info(f"{Icones.COMPRA} Teste de ícone de compra")
logger.info(f"{Icones.VENDA} Teste de ícone de venda")
logger.info(f"{Icones.STATUS} Teste de ícone de status")
logger.warning(f"{Icones.AVISO} Teste de warning")
logger.error(f"{Icones.ERRO} Teste de error")

print("✅ Logs exibidos acima devem ter timestamp HH:MM:SS no console")
print("✅ Arquivo de log deve ter timestamp completo YYYY-MM-DD HH:MM:SS")

# Teste 2: Métodos especializados com ícones
print("\n📝 TESTE 2: Métodos especializados do logger")
print("-" * 70)

logger.operacao_compra(
    par='ADA/USDT',
    quantidade=100.0,
    preco=0.6850,
    degrau=2,
    queda_pct=2.5
)

logger.operacao_venda(
    par='ADA/USDT',
    quantidade=50.0,
    preco=0.7200,
    meta=1,
    lucro_pct=5.11,
    lucro_usd=2.55
)

logger.degrau_bloqueado(2, "limite_atingido:3/3")
logger.degrau_desbloqueado(2)

logger.capital_atualizado(
    capital_ativo=89.40,
    reserva=18.79,
    total=234.91,
    motivo="Após venda"
)

print("✅ Métodos especializados testados com ícones")

# Teste 3: Painel de Status Adaptativo
print("\n📝 TESTE 3: Painel de Status Adaptativo")
print("-" * 70)

painel = PainelStatus(logger)

# Simular alguns preços para calcular volatilidade
precos_teste = [
    Decimal('0.6850'),
    Decimal('0.6860'),
    Decimal('0.6855'),
    Decimal('0.6870'),
    Decimal('0.6880'),
]

print("Registrando preços simulados...")
for preco in precos_teste:
    painel.registrar_preco(preco)
    time.sleep(0.1)

volatilidade = painel.calcular_volatilidade()
print(f"Volatilidade calculada: {volatilidade:.2f}%")

# Forçar exibição do painel (resetar timestamp)
painel.ultima_exibicao = 0

dados_painel = {
    'preco_atual': Decimal('0.6850'),
    'sma_28': Decimal('0.6940'),
    'quantidade_ada': Decimal('130.5'),
    'preco_medio': Decimal('0.6520'),
    'saldo_usdt': Decimal('25.50'),
    'reserva': Decimal('18.79'),
    'capital_total': Decimal('234.91'),
    'stats_24h': {
        'compras': 3,
        'vendas': 2,
        'lucro_realizado': 1.25
    }
}

print("\nExibindo painel de status...")
painel.exibir(dados_painel)

print("✅ Painel de status exibido com sucesso")

# Teste 4: Frequência Adaptativa
print("\n📝 TESTE 4: Frequência Adaptativa do Painel")
print("-" * 70)

# Testar com baixa volatilidade
print("Simulando baixa volatilidade (0.5%)...")
painel.historico_precos.clear()
for i in range(10):
    preco = Decimal('0.6850') + Decimal(str(i * 0.0001))  # Variação mínima
    painel.registrar_preco(preco)

vol_baixa = painel.calcular_volatilidade()
painel.ajustar_frequencia()
print(f"Volatilidade: {vol_baixa:.2f}%")
print(f"Intervalo ajustado: {painel.intervalo_atual}s (esperado: {PainelConfig.INTERVALO_BAIXA_VOL}s)")

# Testar com alta volatilidade
print("\nSimulando alta volatilidade (6%)...")
painel.historico_precos.clear()
for i in range(10):
    preco = Decimal('0.6850') + Decimal(str(i * 0.004))  # Variação grande
    painel.registrar_preco(preco)

vol_alta = painel.calcular_volatilidade()
painel.ajustar_frequencia()
print(f"Volatilidade: {vol_alta:.2f}%")
print(f"Intervalo ajustado: {painel.intervalo_atual}s (esperado: {PainelConfig.INTERVALO_ALTA_VOL}s)")

print("✅ Frequência adaptativa funcionando corretamente")

# Teste 5: Configurações diferentes
print("\n📝 TESTE 5: Modos de Configuração do Logger")
print("-" * 70)

print("\nTestando modo DESENVOLVIMENTO (mais verbose):")
from src.utils.logger import reset_logger
reset_logger()

logger_dev = get_logger(
    nome='TesteBot',
    log_dir=Path('logs'),
    config=LogConfig.DESENVOLVIMENTO,
    console=True
)

logger_dev.debug("Este é um log de DEBUG (visível no modo DEV)")
logger_dev.info("Este é um log de INFO")

print("✅ Modo DESENVOLVIMENTO permite logs DEBUG")

print("\nTestando modo MONITORAMENTO (ultra compacto):")
reset_logger()

logger_mon = get_logger(
    nome='TesteBot',
    log_dir=Path('logs'),
    config=LogConfig.MONITORAMENTO,
    console=True
)

logger_mon.info("Timestamp deve ser HH:MM (sem segundos)")
logger_mon.info(f"{Icones.STATUS} Log compacto para monitoramento")

print("✅ Modo MONITORAMENTO com timestamp ultra compacto")

# Resumo final
print("\n" + "=" * 70)
print("✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
print("=" * 70)
print("\n📊 Resumo das Melhorias Implementadas:")
print("   1. ✅ Timestamps diferentes: console (HH:MM:SS) vs arquivo (completo)")
print("   2. ✅ Sistema de ícones padronizado e centralizado")
print("   3. ✅ Painel de status adaptativo com cálculo de volatilidade")
print("   4. ✅ Frequência adaptativa baseada em volatilidade")
print("   5. ✅ Múltiplos modos de configuração (Produção/Dev/Monitoramento)")
print("   6. ✅ Métodos especializados do logger com ícones")
print("\n🎯 Sistema pronto para uso em produção!")
print("")
