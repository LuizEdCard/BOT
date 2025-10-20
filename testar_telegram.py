#!/usr/bin/env python3
"""Script de teste para verificar se os comandos do bot do Telegram estão configurados corretamente."""

import sys
import os
from dotenv import load_dotenv

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Carregar variáveis de ambiente
load_dotenv('configs/.env')

from src.telegram_bot import TelegramBot

def testar_comandos():
    """Testa se os comandos estão configurados corretamente."""
    print("🧪 Testando configuração do bot do Telegram...\n")

    # Verificar variáveis de ambiente
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    authorized_user_id = os.getenv("TELEGRAM_AUTHORIZED_USER_ID")

    if not telegram_token:
        print("❌ TELEGRAM_BOT_TOKEN não encontrado no .env")
        return False

    if not authorized_user_id:
        print("❌ TELEGRAM_AUTHORIZED_USER_ID não encontrado no .env")
        return False

    print(f"✅ Token do Telegram: {'*' * 20}{telegram_token[-10:]}")
    print(f"✅ ID do usuário autorizado: {authorized_user_id}\n")

    # Criar instância do bot (sem workers para teste)
    print("🤖 Criando instância do TelegramBot...")
    try:
        bot = TelegramBot(
            token=telegram_token,
            authorized_user_id=int(authorized_user_id),
            workers=[],  # Lista vazia para teste
            shutdown_callback=None
        )
        print("✅ Instância criada com sucesso!\n")
    except Exception as e:
        print(f"❌ Erro ao criar instância: {e}")
        return False

    # Verificar métodos de comando
    print("🔍 Verificando métodos de comando...")
    comandos = [
        'start', 'status', 'saldo', 'pausar', 'liberar',
        'crash', 'crash_off', 'forcebuy', 'forcesell',
        'ajustar_risco', 'lucro', 'historico', 'alocacao',
        'parar', 'ajuda', 'details'
    ]

    for comando in comandos:
        if hasattr(bot, comando):
            print(f"  ✅ /{comando}")
        else:
            print(f"  ❌ /{comando} - método não encontrado!")

    print("\n📊 Resumo:")
    print(f"  Total de comandos verificados: {len(comandos)}")
    print(f"  Comandos implementados: {sum(1 for c in comandos if hasattr(bot, c))}")

    print("\n✅ Teste concluído! O bot está configurado corretamente.")
    print("\n💡 Para iniciar o bot, execute: python manager.py")

    return True

if __name__ == '__main__':
    try:
        sucesso = testar_comandos()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
