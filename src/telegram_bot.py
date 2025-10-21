from functools import wraps
import logging
import asyncio
from datetime import datetime
from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler, MessageHandler, filters
from src.core.bot_worker import BotWorker

def restricted_access(func):
    @wraps(func)
    async def wrapped(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != self.authorized_user_id:
            print(f"Unauthorized access denied for {user_id}.")
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapped

SELECTING_BOT, AWAITING_LIMIT = range(2)

class TelegramBot:
    def __init__(self, token: str, authorized_user_id: int, workers: list[BotWorker], shutdown_callback=None):
        self.token = token
        self.authorized_user_id = authorized_user_id
        self.workers = workers
        self.shutdown_callback = shutdown_callback
        self.application = Application.builder().token(token).build()
        self.loop = None  # Será definido quando run() for chamado

    def _format_status_message(self, status_dict):
        # Extrair dados principais
        nome_instancia = status_dict.get('nome_instancia', 'N/A')
        par = status_dict.get('par', 'N/A')
        estado_bot = status_dict.get('estado_bot', 'N/A')
        preco_atual = status_dict.get('preco_atual', 0)
        base_currency = par.split('/')[0]

        # Extrair dados da última compra
        ultima_compra = status_dict.get('ultima_compra')
        compra_str = "N/A"
        if ultima_compra:
            compra_str = f"{ultima_compra.get('quantidade', 0):.2f} {base_currency} @ ${ultima_compra.get('preco', 0):.4f} em {ultima_compra.get('timestamp', 'N/A')}"

        # Extrair dados da última venda
        ultima_venda = status_dict.get('ultima_venda')
        venda_str = "N/A"
        if ultima_venda:
            venda_str = f"{ultima_venda.get('quantidade', 0):.2f} {base_currency} @ ${ultima_venda.get('preco', 0):.4f} em {ultima_venda.get('timestamp', 'N/A')}"

        # Montar a mensagem formatada
        message = (
            f"🤖 **Bot: {nome_instancia} ({par})**\n"
            f"🧠 **Estado:** {estado_bot}\n\n"
            f"📈 **Preço Atual:** ${preco_atual:.4f}\n"
        )

        # Adicionar informações da carteira de Acumulação
        posicao_acumulacao = status_dict.get('status_posicao_acumulacao', {})
        quantidade_acumulacao = posicao_acumulacao.get('quantidade', 0)

        if quantidade_acumulacao and quantidade_acumulacao > 0:
            preco_medio_acum = posicao_acumulacao.get('preco_medio', 0)
            lucro_percentual_acum = posicao_acumulacao.get('lucro_percentual', 0)
            lucro_usdt_acum = posicao_acumulacao.get('lucro_usdt', 0)

            # Garantir que valores não sejam None antes de formatar
            preco_medio_acum = preco_medio_acum if preco_medio_acum is not None else 0
            lucro_percentual_acum = lucro_percentual_acum if lucro_percentual_acum is not None else 0
            lucro_usdt_acum = lucro_usdt_acum if lucro_usdt_acum is not None else 0

            message += (
                f"📊 **Posição Acumulação:** {quantidade_acumulacao:.2f} {base_currency} @ ${preco_medio_acum:.4f} (PM)\n"
                f"💹 **L/P Acumulação:** {lucro_percentual_acum:.2f}% (${lucro_usdt_acum:.2f})\n"
            )
        else:
            message += "📊 **Posição Acumulação:** Nenhuma Posição Aberta\n"

        # Adicionar informações da carteira de Giro Rápido (Especulação)
        posicao_giro = status_dict.get('status_posicao_giro_rapido', {})
        quantidade_giro = posicao_giro.get('quantidade', 0)

        if quantidade_giro and quantidade_giro > 0:
            preco_medio_giro = posicao_giro.get('preco_medio', 0)
            lucro_percentual_giro = posicao_giro.get('lucro_percentual', 0)
            lucro_usdt_giro = posicao_giro.get('lucro_usdt', 0)

            # Garantir que valores não sejam None antes de formatar
            preco_medio_giro = preco_medio_giro if preco_medio_giro is not None else 0
            lucro_percentual_giro = lucro_percentual_giro if lucro_percentual_giro is not None else 0
            lucro_usdt_giro = lucro_usdt_giro if lucro_usdt_giro is not None else 0

            message += (
                f"\n📈 **Posição Especulação:** {quantidade_giro:.2f} {base_currency} @ ${preco_medio_giro:.4f} (PM)\n"
                f"💹 **L/P Especulação:** {lucro_percentual_giro:.2f}% (${lucro_usdt_giro:.2f})\n"
            )
        else:
            message += "\n📈 **Posição Especulação:** Nenhuma Posição Aberta\n"

        message += (
            f"\n🟢 **Última Compra:** {compra_str}\n"
            f"🔴 **Última Venda:** {venda_str}\n"
            f"-----------------------------------"
        )
        return message

    async def _reply_text(self, update: Update, text: str, **kwargs):
        if update.callback_query:
            await update.callback_query.edit_message_text(text, **kwargs)
        else:
            await update.message.reply_text(text, **kwargs)

    def _format_timestamp(self, timestamp_str):
        if not timestamp_str:
            return ""
        now = datetime.now()
        ts = datetime.fromisoformat(timestamp_str)
        diff = now - ts
        if diff.days > 0:
            return f"há {diff.days}d"
        elif diff.seconds > 3600:
            return f"há {diff.seconds // 3600}h"
        else:
            return f"há {diff.seconds // 60}m"

    def _format_detailed_status_message(self, status_dict):
        nome_instancia = status_dict.get('nome_instancia', 'N/A')
        par = status_dict.get('par', 'N/A')
        cooldown_global = status_dict.get('cooldown_global_restante_min', 0)
        exposicao_maxima = status_dict.get('exposicao_maxima', 0)
        notificou_exposicao_maxima = status_dict.get('notificou_exposicao_maxima', False)
        degraus_bloqueados = status_dict.get('degraus_bloqueados', [])

        message = (
            f"🤖 **Bot: {nome_instancia} ({par}) - Detalhes**\n\n"
            f"**Gestão de Risco:**\n"
            f"- Exposição Máxima Configurada: {exposicao_maxima}%\n"
            f"- Notificou Exposição Máxima: {'Sim' if notificou_exposicao_maxima else 'Não'}\n\n"
            f"**Cooldowns:**\n"
            f"- Cooldown Global Restante: {cooldown_global} min\n"
            f"- Degraus Bloqueados: {degraus_bloqueados if degraus_bloqueados else 'Nenhum'}\n"
        )
        return message

    async def _handle_bot_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, command_name: str):
        if context.args and len(context.args) > 0:
            return context.args[0]
        
        keyboard = []
        for worker in self.workers:
            nome = worker.config.get('nome_instancia', 'N/A')
            button = InlineKeyboardButton(text=nome, callback_data=f"{command_name}:{nome}")
            keyboard.append([button])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Por favor, selecione o bot para o comando /{command_name}:",
            reply_markup=reply_markup
        )
        return None

    @restricted_access
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Bem-vindo ao Bot de Monitoramento!")

    @restricted_access
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        full_status_message = []
        for worker in self.workers:
            status_dict = worker.get_status_dict()
            formatted_message = self._format_status_message(status_dict)
            full_status_message.append(formatted_message)
        
        response = "\n\n".join(full_status_message)
        await self._reply_text(update, response, parse_mode='Markdown')
    @restricted_access
    async def details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command_name = 'details'
        bot_name = await self._handle_bot_selection(update, context, command_name)
        if not bot_name:
            return

        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == bot_name:
                bot_encontrado = worker
                break

        if bot_encontrado:
            status_detalhado = bot_encontrado.get_detailed_status_dict()
            response = self._format_detailed_status_message(status_detalhado)
            await self._reply_text(update, response, parse_mode='Markdown')
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update, 
                f"❌ Bot '{bot_name}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )

    @restricted_access
    async def saldo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command_name = 'saldo'
        bot_name = await self._handle_bot_selection(update, context, command_name)
        if not bot_name:
            return

        if bot_name.upper() == 'TOTAL':
            total_usdt = 0
            total_posicao_acumulacao = 0
            total_posicao_giro = 0

            for worker in self.workers:
                status = worker.get_status_dict()
                total_usdt += status.get('saldo_disponivel_usdt', 0)
                total_posicao_acumulacao += status.get('status_posicao_acumulacao', {}).get('valor_total', 0)
                total_posicao_giro += status.get('status_posicao_giro_rapido', {}).get('valor_total', 0)

            total_posicoes = total_posicao_acumulacao + total_posicao_giro
            total_geral = total_usdt + total_posicoes

            response = (
                f"💰 **Saldo Total Consolidado**\n\n"
                f"📊 **Acumulação:** ${total_posicao_acumulacao:.2f}\n"
                f"🎯 **Giro Rápido:** ${total_posicao_giro:.2f}\n"
                f"💵 **USDT Disponível:** ${total_usdt:.2f}\n"
                f"-----------------------------------\n"
                f"**Total Geral:** **${total_geral:.2f}**"
            )
            await self._reply_text(update, response, parse_mode='Markdown')
            return

        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == bot_name:
                bot_encontrado = worker
                break

        if bot_encontrado:
            status = bot_encontrado.get_status_dict()
            base_currency = status.get('ativo_base', 'N/A')

            # Carteira Acumulação
            posicao_acum = status.get('status_posicao_acumulacao', {})
            qtd_acum = posicao_acum.get('quantidade', 0)
            valor_acum = posicao_acum.get('valor_total', 0)

            # Carteira Giro Rápido
            posicao_giro = status.get('status_posicao_giro_rapido', {})
            qtd_giro = posicao_giro.get('quantidade', 0)
            valor_giro = posicao_giro.get('valor_total', 0)

            saldo_usdt = status.get('saldo_disponivel_usdt', 0)
            total = valor_acum + valor_giro + saldo_usdt

            response = (
                f"💰 **Saldo do Bot: {status.get('nome_instancia')} ({status.get('par')})**\n\n"
                f"📊 **Acumulação:**\n"
                f"  • Quantidade: {qtd_acum:.2f} {base_currency}\n"
                f"  • Valor: ${valor_acum:.2f}\n\n"
                f"🎯 **Giro Rápido:**\n"
                f"  • Quantidade: {qtd_giro:.2f} {base_currency}\n"
                f"  • Valor: ${valor_giro:.2f}\n\n"
                f"💵 **USDT Disponível:** ${saldo_usdt:.2f}\n"
                f"-----------------------------------\n"
                f"**Total:** **${total:.2f}**"
            )
            await self._reply_text(update, response, parse_mode='Markdown')
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update,
                f"❌ Bot '{bot_name}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )

    
    @restricted_access
    async def pausar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command_name = 'pausar'
        bot_name = await self._handle_bot_selection(update, context, command_name)
        if not bot_name:
            return

        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == bot_name:
                bot_encontrado = worker
                break

        if bot_encontrado:
            bot_encontrado.command_queue.put({'comando': 'pausar_compras'})
            await self._reply_text(update, f"✅ Comando de pausa enviado para '{bot_name}'.\nAs compras foram pausadas.")
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update, 
                f"❌ Bot '{bot_name}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )
    
    @restricted_access
    async def liberar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command_name = 'liberar'
        bot_name = await self._handle_bot_selection(update, context, command_name)
        if not bot_name:
            return

        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == bot_name:
                bot_encontrado = worker
                break

        if bot_encontrado:
            bot_encontrado.command_queue.put({'comando': 'liberar_compras'})
            await self._reply_text(update, f"✅ Comando de liberação enviado para '{bot_name}'.\nAs compras foram reativadas.")
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update, 
                f"❌ Bot '{bot_name}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )
    
    @restricted_access
    async def crash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command_name = 'crash'
        bot_name = await self._handle_bot_selection(update, context, command_name)
        if not bot_name:
            return

        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == bot_name:
                bot_encontrado = worker
                break

        if bot_encontrado:
            bot_encontrado.command_queue.put({'comando': 'ativar_modo_crash'})
            await self._reply_text(update, f"💥 *MODO CRASH ATIVADO* para '{bot_name}'\n\n⚠️ Compras agressivas liberadas!\n⚠️ Restrições de exposição e preço médio ignoradas.", parse_mode='Markdown')
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update, 
                f"❌ Bot '{bot_name}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )
    
    @restricted_access
    async def crash_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Desativa o modo crash para um bot.
        
        Uso: /crash_off [nome_do_bot]
        """
        if not context.args:
            await update.message.reply_text(
                "❌ Uso incorreto. Especifique o nome do bot.\n"
                "Exemplo: /crash_off ADA"
            )
            return
        
        nome_bot = " ".join(context.args)
        
        # Procurar o bot na lista de workers
        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == nome_bot:
                bot_encontrado = worker
                break
        
        if bot_encontrado:
            bot_encontrado.command_queue.put({'comando': 'desativar_modo_crash'})
            await self._reply_text(update, f"✅ *MODO CRASH DESATIVADO* para '{nome_bot}'\n\nRetornando ao modo de operação normal.", parse_mode='Markdown')
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update, 
                f"❌ Bot '{nome_bot}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )

    @restricted_access
    async def forcebuy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args or len(context.args) != 2:
            await update.message.reply_text("Uso: /forcebuy [nome_bot] [valor_usdt]")
            return

        nome_bot, valor_usdt = context.args
        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == nome_bot:
                bot_encontrado = worker
                break

        if bot_encontrado:
            keyboard = [[InlineKeyboardButton("Sim, tenho certeza", callback_data=f"confirm_forcebuy:{nome_bot}:{valor_usdt}"),
                         InlineKeyboardButton("Não", callback_data="cancel_forcebuy")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self._reply_text(update, f"Você tem certeza que deseja forçar a compra de {valor_usdt} USDT para o bot {nome_bot}?", reply_markup=reply_markup)
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update, 
                f"❌ Bot '{nome_bot}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )

    @restricted_access
    async def forcesell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args or len(context.args) != 2:
            await update.message.reply_text("Uso: /forcesell [nome_bot] [percentual]")
            return

        nome_bot, percentual = context.args
        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == nome_bot:
                bot_encontrado = worker
                break

        if bot_encontrado:
            bot_encontrado.command_queue.put({'comando': 'force_sell', 'percentual': percentual})
            await self._reply_text(update, f"✅ Comando de venda forçada de {percentual}% enviado para '{nome_bot}'.")
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update, 
                f"❌ Bot '{nome_bot}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )

    async def ajustar_risco_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Inicia o fluxo de ajuste de risco."""
        # Verificar autorização
        user_id = update.effective_user.id
        if user_id != self.authorized_user_id:
            return ConversationHandler.END

        # Construir teclado com os bots disponíveis
        keyboard = []
        for worker in self.workers:
            nome = worker.config.get('nome_instancia', 'N/A')
            button = InlineKeyboardButton(text=nome, callback_data=f"ajustar_risco:{nome}")
            keyboard.append([button])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Selecione o bot para ajustar o limite de risco:",
            reply_markup=reply_markup
        )
        return SELECTING_BOT

    async def ajustar_risco_bot_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Processa a seleção do bot e pede o novo limite."""
        query = update.callback_query
        await query.answer()

        # Extrair nome do bot do callback_data
        bot_name = query.data.split(':', 1)[1]
        context.user_data['ajustar_risco_bot'] = bot_name

        await query.edit_message_text(
            f"Bot selecionado: {bot_name}\n\n"
            f"Digite o novo limite de exposição (ex: 75 ou 75%):"
        )
        return AWAITING_LIMIT

    async def ajustar_risco_set_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Processa o novo limite de risco."""
        bot_name = context.user_data.get('ajustar_risco_bot')
        if not bot_name:
            await update.message.reply_text("❌ Erro: bot não selecionado. Use /ajustar_risco novamente.")
            return ConversationHandler.END

        # Processar o valor digitado
        novo_limite_str = update.message.text.strip().replace('%', '').replace(',', '.')
        try:
            novo_limite = float(novo_limite_str)
            if novo_limite < 0 or novo_limite > 100:
                await update.message.reply_text("❌ Valor inválido. Digite um número entre 0 e 100.")
                return AWAITING_LIMIT
        except ValueError:
            await update.message.reply_text("❌ Formato inválido. Digite apenas o número (ex: 75).")
            return AWAITING_LIMIT

        # Encontrar o worker e enviar comando
        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == bot_name:
                bot_encontrado = worker
                break

        if bot_encontrado:
            bot_encontrado.command_queue.put({
                'comando': 'ajustar_risco',
                'novo_limite': novo_limite
            })
            await update.message.reply_text(
                f"✅ Limite de risco do bot {bot_name} ajustado para {novo_limite}%"
            )
        else:
            await update.message.reply_text(f"❌ Erro: bot '{bot_name}' não encontrado.")

        # Limpar dados e encerrar
        context.user_data.pop('ajustar_risco_bot', None)
        return ConversationHandler.END

    async def ajustar_risco_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancela o fluxo de ajuste de risco."""
        await update.message.reply_text("Operação cancelada.")
        context.user_data.pop('ajustar_risco_bot', None)
        return ConversationHandler.END

    @restricted_access
    async def lucro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command_name = 'lucro'
        bot_name = await self._handle_bot_selection(update, context, command_name)
        if not bot_name:
            return

        dias = int(context.args[1]) if len(context.args) > 1 else 7

        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == bot_name:
                bot_encontrado = worker
                break

        if bot_encontrado:
            lucro = bot_encontrado.position_manager.get_lucro_realizado_periodo(dias)
            par = bot_encontrado.config.get('par', 'N/A')
            await self._reply_text(update, f"✅ Lucro Realizado ({par.split('/')[0]}) nos últimos {dias} dias: +${lucro:.2f} USDT")
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update, 
                f"❌ Bot '{bot_name}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )

    @restricted_access
    async def historico(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        command_name = 'historico'
        bot_name = await self._handle_bot_selection(update, context, command_name)
        if not bot_name:
            return

        limite = int(context.args[1]) if len(context.args) > 1 else 5

        bot_encontrado = None
        for worker in self.workers:
            if worker.config.get('nome_instancia') == bot_name:
                bot_encontrado = worker
                break

        if bot_encontrado:
            ordens = bot_encontrado.position_manager.get_ultimas_ordens(limite)
            response = f"**Histórico de Ordens para {bot_name}**\n\n"
            for ordem in ordens:
                tipo = "🟢 COMPRA" if ordem['tipo'] == 'COMPRA' else "🔴 VENDA"
                timestamp = self._format_timestamp(ordem['timestamp'])
                response += f"{tipo} | {ordem['quantidade']:.2f} {ordem['par'].split('/')[0]} @ ${ordem['preco']:.4f} | {timestamp}\n"
            await self._reply_text(update, response, parse_mode='Markdown')
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await self._reply_text(update, 
                f"❌ Bot '{bot_name}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )

    @restricted_access
    async def alocacao(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        total_usdt = Decimal('0')
        total_acumulacao = Decimal('0')
        total_giro_rapido = Decimal('0')
        alocacao_por_ativo_acumulacao = {}
        alocacao_por_ativo_giro = {}

        for worker in self.workers:
            status = worker.get_status_dict()
            par = status.get('par', 'N/A').split('/')[0]
            saldo_usdt = status.get('saldo_disponivel_usdt', 0)

            # Acumulação
            valor_acumulacao = status.get('status_posicao_acumulacao', {}).get('valor_total', 0)
            total_acumulacao += valor_acumulacao
            if valor_acumulacao > 0:
                if par not in alocacao_por_ativo_acumulacao:
                    alocacao_por_ativo_acumulacao[par] = Decimal('0')
                alocacao_por_ativo_acumulacao[par] += valor_acumulacao

            # Giro Rápido
            valor_giro = status.get('status_posicao_giro_rapido', {}).get('valor_total', 0)
            total_giro_rapido += valor_giro
            if valor_giro > 0:
                if par not in alocacao_por_ativo_giro:
                    alocacao_por_ativo_giro[par] = Decimal('0')
                alocacao_por_ativo_giro[par] += valor_giro

            total_usdt += saldo_usdt

        capital_total = total_usdt + total_acumulacao + total_giro_rapido
        if capital_total == 0:
            await self._reply_text(update, "Não há capital para analisar.")
            return

        percentual_usdt = (total_usdt / capital_total) * 100
        percentual_acumulacao = (total_acumulacao / capital_total) * 100
        percentual_giro = (total_giro_rapido / capital_total) * 100

        response = f"📊 **Alocação de Capital Total: ${capital_total:.2f}**\n\n"
        response += f"💵 **USDT:** ${total_usdt:.2f} ({percentual_usdt:.2f}%)\n"
        response += f"📊 **Acumulação:** ${total_acumulacao:.2f} ({percentual_acumulacao:.2f}%)\n"
        response += f"🎯 **Giro Rápido:** ${total_giro_rapido:.2f} ({percentual_giro:.2f}%)\n\n"

        # Breakdown por carteira e ativo
        if alocacao_por_ativo_acumulacao:
            response += "**📊 Acumulação por Ativo:**\n"
            for ativo, valor in alocacao_por_ativo_acumulacao.items():
                percentual_ativo = (valor / capital_total) * 100
                response += f"  • {ativo}: ${valor:.2f} ({percentual_ativo:.2f}%)\n"
            response += "\n"

        if alocacao_por_ativo_giro:
            response += "**🎯 Giro Rápido por Ativo:**\n"
            for ativo, valor in alocacao_por_ativo_giro.items():
                percentual_ativo = (valor / capital_total) * 100
                response += f"  • {ativo}: ${valor:.2f} ({percentual_ativo:.2f}%)\n"

        await self._reply_text(update, response, parse_mode='Markdown')
    
    @restricted_access
    async def parar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Para todos os bots e desliga o sistema graciosamente."""
        if self.shutdown_callback:
            chat_id = update.effective_chat.id
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "🛑 *Comando de desligamento recebido*\n\n"
                        "Parando todos os bots graciosamente...\n"
                        "O sistema será desligado em alguns segundos."
                    ),
                    parse_mode='Markdown'
                )
            
            # Executar callback em thread separada para não bloquear o Telegram
            import threading
            shutdown_thread = threading.Thread(target=self.shutdown_callback)
            shutdown_thread.start()
        else:
            await update.message.reply_text(
                "❌ Callback de desligamento não configurado."
            )
    
    async def _button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        parts = query.data.split(':', 1)
        command = parts[0]
        bot_name = parts[1] if len(parts) > 1 else None

        if bot_name:
            context.args = [bot_name]

        command_map = {
            'lucro': self.lucro,
            'historico': self.historico,
            'pausar': self.pausar,
            'liberar': self.liberar,
            'crash': self.crash,
            'details': self.details,
            'saldo': self.saldo,
        }

        if command in command_map:
            await command_map[command](update, context)
        elif command.startswith('confirm_forcebuy'):
            _, bot_name, valor_usdt = query.data.split(':')
            context.args = [bot_name, valor_usdt]
            await self.forcebuy(update, context)
        elif command == 'cancel_forcebuy':
            await query.edit_message_text(text="Operação cancelada.")
    
    @restricted_access
    async def ajuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Exibe a lista de comandos disponíveis."""
        help_text = (
            "📋 <b>Comandos Disponíveis</b>\n\n"
            "🔹 /start - Inicia o bot e exibe boas-vindas\n\n"
            "🔹 /status - Exibe o status detalhado de todos os bots\n\n"
            "🔹 /saldo [nome] - Exibe o saldo (sem args = modo interativo)\n"
            "   Exemplo: <code>/saldo ADA</code>\n\n"
            "🔹 /pausar [nome] - Pausa compras (sem args = modo interativo)\n"
            "   Exemplo: <code>/pausar ADA</code>\n\n"
            "🔹 /liberar [nome] - Libera compras (sem args = modo interativo)\n"
            "   Exemplo: <code>/liberar ADA</code>\n\n"
            "🔹 /crash [nome] - Ativa modo crash (sem args = modo interativo)\n"
            "   Exemplo: <code>/crash ADA</code>\n\n"
            "🔹 /crash_off [nome] - Desativa modo crash\n"
            "   Exemplo: <code>/crash_off ADA</code>\n\n"
            "🔹 /lucro [nome] [dias] - Exibe o lucro realizado (padrão 7 dias)\n"
            "   Exemplo: <code>/lucro ada_bot 30</code>\n\n"
            "🔹 /historico [nome] [limite] - Exibe as últimas ordens (padrão 5)\n"
            "   Exemplo: <code>/historico ada_bot 10</code>\n\n"
            "🔹 /alocacao - Exibe a alocação de capital total e por ativo\n\n"
            "🔹 /ajustar_risco [nome] [limite] - Ajusta o limite de exposição máximo\n"
            "   Exemplo: <code>/ajustar_risco ADA 80%</code>\n\n"
            "🔹 /parar - Para todos os bots e desliga o sistema\n\n"
            "🔹 /ajuda - Exibe esta mensagem de ajuda\n\n"
            "-----------------------------------\n\n"
            "💡 <b>Bots Ativos:</b>\n"
        )

        # Adicionar lista de bots disponíveis
        for worker in self.workers:
            nome = worker.config.get('nome_instancia', 'N/A')
            par = worker.config.get('par', 'N/A')
            help_text += f"• {nome} ({par})\n"

        await update.message.reply_text(help_text, parse_mode='HTML')

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Responde a comandos não reconhecidos."""
        await update.message.reply_text(
            "Comando não reconhecido. Use /ajuda para ver a lista de comandos disponíveis."
        )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Loga os erros causados por updates."""
        logging.error(f"Update '{update}' caused error '{context.error}'")

    async def enviar_mensagem(self, user_id: int, mensagem: str):
        """Envia uma mensagem proativa para um usuário específico.
        
        Args:
            user_id: ID do usuário do Telegram
            mensagem: Texto da mensagem a ser enviada
        """
        await self.application.bot.send_message(chat_id=user_id, text=mensagem)

    async def run(self):
        # Armazenar o loop da thread do Telegram
        self.loop = asyncio.get_running_loop()
        
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("saldo", self.saldo))
        self.application.add_handler(CommandHandler("pausar", self.pausar))
        self.application.add_handler(CommandHandler("liberar", self.liberar))
        self.application.add_handler(CommandHandler("crash", self.crash))
        self.application.add_handler(CommandHandler("crash_off", self.crash_off))
        self.application.add_handler(CommandHandler("parar", self.parar))
        self.application.add_handler(CommandHandler("ajuda", self.ajuda))
        self.application.add_handler(CommandHandler("details", self.details))
        self.application.add_handler(CommandHandler("forcebuy", self.forcebuy))
        self.application.add_handler(CommandHandler("forcesell", self.forcesell))
        self.application.add_handler(CommandHandler("lucro", self.lucro))
        self.application.add_handler(CommandHandler("historico", self.historico))
        self.application.add_handler(CommandHandler("alocacao", self.alocacao))

        # ConversationHandler para /ajustar_risco
        # Deve ser registrado ANTES de outros handlers de comando
        ajustar_risco_handler = ConversationHandler(
            entry_points=[CommandHandler('ajustar_risco', self.ajustar_risco_start)],
            states={
                SELECTING_BOT: [
                    CallbackQueryHandler(self.ajustar_risco_bot_selected, pattern='^ajustar_risco:')
                ],
                AWAITING_LIMIT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.ajustar_risco_set_limit)
                ],
            },
            fallbacks=[CommandHandler('cancelar', self.ajustar_risco_cancel)],
            per_message=False,
        )
        self.application.add_handler(ajustar_risco_handler)

        # Callback para todos os outros botões
        # O pattern garante que não interfira com o ConversationHandler
        self.application.add_handler(CallbackQueryHandler(
            self._button_callback,
            pattern='^(lucro|historico|pausar|liberar|crash|details|saldo|confirm_forcebuy|cancel_forcebuy):')
        )

        # IMPORTANTE: unknown_command deve ser o ÚLTIMO handler de comando
        # Excluir todos os comandos registrados para evitar conflitos
        comandos_registrados = (
            r'^/(start|status|saldo|pausar|liberar|crash|crash_off|parar|ajuda|'
            r'details|forcebuy|forcesell|lucro|historico|alocacao|ajustar_risco|cancelar)'
        )
        self.application.add_handler(
            MessageHandler(
                filters.COMMAND & ~filters.Regex(comandos_registrados),
                self.unknown_command
            ),
            group=1
        )

        # Adicionar um handler para erros
        self.application.add_error_handler(self.error_handler)

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep the bot running
        await asyncio.Event().wait()
