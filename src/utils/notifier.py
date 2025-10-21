#!/usr/bin/env python3
"""
Notifier - Sistema de Notificações Proativas via Telegram
"""

import asyncio
import logging
from typing import Optional


class Notifier:
    """
    Sistema de notificações proativas para enviar mensagens ao usuário via Telegram.

    Responsabilidades:
    - Enviar notificações importantes para o usuário autorizado
    - Abstrair a comunicação com o TelegramBot
    - Fornecer interface simples para os workers enviarem alertas
    """

    def __init__(self, telegram_bot, authorized_user_id: int):
        """
        Inicializa o Notifier

        Args:
            telegram_bot: Instância do TelegramBot
            authorized_user_id: ID do usuário autorizado do Telegram
        """
        self.telegram_bot = telegram_bot
        self.authorized_user_id = authorized_user_id
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"📢 Notifier inicializado para user_id: {authorized_user_id}")

    def enviar_notificacao(self, mensagem: str) -> bool:
        """
        Envia uma notificação para o usuário autorizado via Telegram

        Args:
            mensagem: Texto da mensagem a ser enviada

        Returns:
            bool: True se a mensagem foi enviada com sucesso, False caso contrário
        """
        try:
            if not self.telegram_bot or not self.telegram_bot.loop:
                self.logger.warning("⚠️ TelegramBot não disponível para envio de notificação")
                return False

            # Enviar mensagem de forma assíncrona
            future = asyncio.run_coroutine_threadsafe(
                self.telegram_bot.enviar_mensagem(self.authorized_user_id, mensagem),
                self.telegram_bot.loop
            )

            # Aguardar resultado (timeout de 10 segundos)
            future.result(timeout=10)

            self.logger.debug(f"📤 Notificação enviada: {mensagem[:50]}...")
            return True

        except asyncio.TimeoutError:
            self.logger.error("❌ Timeout ao enviar notificação via Telegram")
            return False
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar notificação: {e}")
            return False

    def enviar_alerta(self, titulo: str, mensagem: str) -> bool:
        """
        Envia um alerta formatado para o usuário

        Args:
            titulo: Título do alerta
            mensagem: Corpo da mensagem

        Returns:
            bool: True se enviado com sucesso
        """
        texto_formatado = f"🚨 **{titulo}**\n\n{mensagem}"
        return self.enviar_notificacao(texto_formatado)

    def enviar_info(self, titulo: str, mensagem: str) -> bool:
        """
        Envia uma informação formatada para o usuário

        Args:
            titulo: Título da informação
            mensagem: Corpo da mensagem

        Returns:
            bool: True se enviado com sucesso
        """
        texto_formatado = f"ℹ️ **{titulo}**\n\n{mensagem}"
        return self.enviar_notificacao(texto_formatado)

    def enviar_sucesso(self, titulo: str, mensagem: str) -> bool:
        """
        Envia uma mensagem de sucesso formatada para o usuário

        Args:
            titulo: Título da mensagem
            mensagem: Corpo da mensagem

        Returns:
            bool: True se enviado com sucesso
        """
        texto_formatado = f"✅ **{titulo}**\n\n{mensagem}"
        return self.enviar_notificacao(texto_formatado)


if __name__ == '__main__':
    """Exemplo de uso"""
    print("Notifier - Sistema de Notificações Proativas")
    print("Este módulo deve ser usado em conjunto com TelegramBot")
