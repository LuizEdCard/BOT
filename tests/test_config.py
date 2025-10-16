#!/usr/bin/env python3
"""
Teste de configuração - Verifica se .env está correto
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from config.settings import settings

    print("=" * 60)
    print("  TESTE DE CONFIGURAÇÃO")
    print("=" * 60)
    print()

    # Verificar se API keys estão configuradas
    if settings.BINANCE_API_KEY and settings.BINANCE_API_KEY != 'your_api_key_here':
        print("✅ BINANCE_API_KEY: Configurada")
    else:
        print("❌ BINANCE_API_KEY: NÃO configurada ou usando valor padrão")

    if settings.BINANCE_API_SECRET and settings.BINANCE_API_SECRET != 'your_api_secret_here':
        print("✅ BINANCE_API_SECRET: Configurada")
    else:
        print("❌ BINANCE_API_SECRET: NÃO configurada ou usando valor padrão")

    print()

    # Mostrar configurações (sem secrets)
    info = settings.info()

    print("📊 CONFIGURAÇÕES CARREGADAS:")
    print(f"   Ambiente: {info['ambiente']}")
    print(f"   Par Principal: {info['par_principal']}")
    print(f"   Capital Inicial: ${info['capital_inicial']:.2f}")
    print(f"   Capital Ativo: {info['capital_ativo_pct']}%")
    print(f"   Reserva: {info['reserva_pct']}%")
    print(f"   Limite Gasto Diário: ${info['limite_gasto_diario']:.2f}")
    print(f"   Degraus de Compra: {info['degraus_compra']}")
    print(f"   Metas de Venda: {info['metas_venda']}")
    print(f"   Log Level: {info['log_level']}")
    print()
    print(f"🌐 BINANCE:")
    print(f"   API URL: {info['api_url']}")
    print(f"   WebSocket URL: {info['ws_url']}")
    print()

    # Validar configurações
    print("🔍 VALIDANDO CONFIGURAÇÕES...")
    try:
        settings.validar()
        print("✅ Todas as validações passaram!")
    except ValueError as e:
        print(f"❌ Erro de validação:\n{e}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  ✅ CONFIGURAÇÃO OK - PRONTO PARA USAR!")
    print("=" * 60)

except FileNotFoundError as e:
    print(f"❌ ERRO: {e}")
    print()
    print("👉 Certifique-se de que config/.env existe")
    print("   Execute: cp config/.env.example config/.env")
    sys.exit(1)

except ValueError as e:
    print(f"❌ ERRO: {e}")
    sys.exit(1)

except Exception as e:
    print(f"❌ ERRO INESPERADO: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
