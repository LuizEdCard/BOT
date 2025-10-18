from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, MessageHandler, filters
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

class TelegramBot:
    def __init__(self, token: str, authorized_user_id: int, workers: list[BotWorker], shutdown_callback=None):
        self.token = token
        self.authorized_user_id = authorized_user_id
        self.workers = workers
        self.shutdown_callback = shutdown_callback
        self.application = Application.builder().token(token).build()

    def _format_status_message(self, status_dict):
        # Extrair dados principais
        nome_instancia = status_dict.get('nome_instancia', 'N/A')
        par = status_dict.get('par', 'N/A')
        estado_bot = status_dict.get('estado_bot', 'N/A')
        preco_atual = status_dict.get('preco_atual', 0)

        # Extrair dados da posição
        posicao = status_dict.get('status_posicao', {})
        quantidade_posicao = posicao.get('quantidade', 0)
        preco_medio = posicao.get('preco_medio', 0)
        lucro_percentual = posicao.get('lucro_percentual', 0)
        lucro_usdt = posicao.get('lucro_usdt', 0)

        # Extrair dados da última compra
        ultima_compra = status_dict.get('ultima_compra')
        compra_str = "N/A"
        if ultima_compra:
            compra_str = f"{ultima_compra.get('quantidade', 0):.2f} {par.split('/')[0]} @ ${ultima_compra.get('preco', 0):.4f} em {ultima_compra.get('timestamp', 'N/A')}"

        # Extrair dados da última venda
        ultima_venda = status_dict.get('ultima_venda')
        venda_str = "N/A"
        if ultima_venda:
            venda_str = f"{ultima_venda.get('quantidade', 0):.2f} {par.split('/')[0]} @ ${ultima_venda.get('preco', 0):.4f} em {ultima_venda.get('timestamp', 'N/A')}"

        # Montar a mensagem formatada
        message = (
            f"🤖 **Bot: {nome_instancia} ({par})**\n"
            f"🧠 **Estado:** {estado_bot}\n\n"
            f"📈 **Preço Atual:** ${preco_atual:.4f}\n"
            f"📊 **Posição:** {quantidade_posicao:.2f} {par.split('/')[0]} @ ${preco_medio:.4f} (PM)\n"
            f"💹 **L/P Posição:** {lucro_percentual:.2f}% (${lucro_usdt:.2f})\n\n"
            f"🟢 **Última Compra:** {compra_str}\n"
            f"🔴 **Última Venda:** {venda_str}\n"
            f"-----------------------------------"
        )
        return message

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
        await update.message.reply_text(response, parse_mode='Markdown')

    @restricted_access
    async def saldo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Exibe os saldos dos bots.

        Uso: /saldo [nome_do_bot] ou /saldo (modo interativo)
        """
        if context.args and len(context.args) > 0:
            nome_bot = " ".join(context.args)
            if nome_bot.upper() == 'TOTAL':
                total_usdt = 0
                total_posicao_usdt = 0
                for worker in self.workers:
                    status = worker.get_status_dict()
                    total_usdt += status.get('saldo_disponivel_usdt', 0)
                    total_posicao_usdt += status.get('status_posicao', {}).get('valor_total', 0)
                
                response = (
                    f"💰 **Saldo Total Consolidado**\n\n"
                    f"- **Valor em Posições:** ${total_posicao_usdt:.2f}\n"
                    f"- **Saldo USDT Disponível:** ${total_usdt:.2f}\n"
                    f"-----------------------------------\n"
                    f"**Total Geral:** **${total_posicao_usdt + total_usdt:.2f}**"
                )
                await update.message.reply_text(response, parse_mode='Markdown')
                return

            bot_encontrado = None
            for worker in self.workers:
                if worker.config.get('nome_instancia') == nome_bot:
                    bot_encontrado = worker
                    break
            
            if bot_encontrado:
                status = bot_encontrado.get_status_dict()
                posicao = status.get('status_posicao', {})
                response = (
                    f"💰 **Saldo do Bot: {status.get('nome_instancia')} ({status.get('par')})**\n\n"
                    f"- **Posição:** {posicao.get('quantidade', 0):.2f} {status.get('ativo_base', 'N/A')}\n"
                    f"- **Valor da Posição:** ${posicao.get('valor_total', 0):.2f}\n"
                    f"- **Saldo USDT Disponível:** ${status.get('saldo_disponivel_usdt', 0):.2f}"
                )
                await update.message.reply_text(response, parse_mode='Markdown')
            else:
                bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
                await update.message.reply_text(
                    f"❌ Bot '{nome_bot}' não encontrado.\n\n"
                    f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
                )
        else:
            if not self.workers or len(self.workers) == 0:
                await update.message.reply_text(
                    "❌ Nenhum bot ativo encontrado."
                )
                return

            keyboard = [
                [InlineKeyboardButton(text="💰 Saldo Total Consolidado", callback_data="saldo:TOTAL")]
            ]
            for worker in self.workers:
                nome = worker.config.get('nome_instancia', 'N/A')
                par = worker.config.get('par', 'N/A')
                button = InlineKeyboardButton(
                    text=f"Saldo {nome} ({par})",
                    callback_data=f"saldo:{nome}"
                )
                keyboard.append([button])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "*Selecione o saldo que deseja consultar:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    
    @restricted_access
    async def pausar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pausa as compras de um bot específico.

        Uso: /pausar [nome_do_bot] ou /pausar (modo interativo)
        """
        # Modo com argumento
        if context.args and len(context.args) > 0:
            nome_bot = " ".join(context.args)

            # Procurar o bot na lista de workers
            bot_encontrado = None
            for worker in self.workers:
                if worker.config.get('nome_instancia') == nome_bot:
                    bot_encontrado = worker
                    break

            if bot_encontrado:
                bot_encontrado.command_queue.put({'comando': 'pausar_compras'})
                await update.message.reply_text(
                    f"✅ Comando de pausa enviado para '{nome_bot}'.\n"
                    f"As compras foram pausadas."
                )
            else:
                # Listar bots disponíveis
                bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
                await update.message.reply_text(
                    f"❌ Bot '{nome_bot}' não encontrado.\n\n"
                    f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
                )
        else:
            # Modo interativo com botões
            if not self.workers or len(self.workers) == 0:
                await update.message.reply_text(
                    "❌ Nenhum bot ativo encontrado."
                )
                return

            keyboard = []
            for worker in self.workers:
                nome = worker.config.get('nome_instancia', 'N/A')
                par = worker.config.get('par', 'N/A')
                button = InlineKeyboardButton(
                    text=f"⏸️ Pausar {nome} ({par})",
                    callback_data=f"pause:{nome}"
                )
                keyboard.append([button])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🎮 *Selecione o bot para pausar:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    @restricted_access
    async def liberar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Libera as compras de um bot específico.

        Uso: /liberar [nome_do_bot] ou /liberar (modo interativo)
        """
        # Modo com argumento
        if context.args and len(context.args) > 0:
            nome_bot = " ".join(context.args)

            # Procurar o bot na lista de workers
            bot_encontrado = None
            for worker in self.workers:
                if worker.config.get('nome_instancia') == nome_bot:
                    bot_encontrado = worker
                    break

            if bot_encontrado:
                bot_encontrado.command_queue.put({'comando': 'liberar_compras'})
                await update.message.reply_text(
                    f"✅ Comando de liberação enviado para '{nome_bot}'.\n"
                    f"As compras foram reativadas."
                )
            else:
                # Listar bots disponíveis
                bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
                await update.message.reply_text(
                    f"❌ Bot '{nome_bot}' não encontrado.\n\n"
                    f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
                )
        else:
            # Modo interativo com botões
            if not self.workers or len(self.workers) == 0:
                await update.message.reply_text(
                    "❌ Nenhum bot ativo encontrado."
                )
                return

            keyboard = []
            for worker in self.workers:
                nome = worker.config.get('nome_instancia', 'N/A')
                par = worker.config.get('par', 'N/A')
                button = InlineKeyboardButton(
                    text=f"▶️ Liberar {nome} ({par})",
                    callback_data=f"resume:{nome}"
                )
                keyboard.append([button])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🎮 *Selecione o bot para liberar:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    @restricted_access
    async def crash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ativa o modo crash (compras agressivas) para um bot.
        
        Uso: /crash [nome_do_bot] ou /crash (modo interativo)
        """
        if context.args and len(context.args) > 0:
            nome_bot = " ".join(context.args)
            bot_encontrado = None
            for worker in self.workers:
                if worker.config.get('nome_instancia') == nome_bot:
                    bot_encontrado = worker
                    break
            
            if bot_encontrado:
                bot_encontrado.command_queue.put({'comando': 'ativar_modo_crash'})
                await update.message.reply_text(
                    f"💥 *MODO CRASH ATIVADO* para '{nome_bot}'\n\n"
                    f"⚠️ Compras agressivas liberadas!\n"
                    f"⚠️ Restrições de exposição e preço médio ignoradas.",
                    parse_mode='Markdown'
                )
            else:
                bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
                await update.message.reply_text(
                    f"❌ Bot '{nome_bot}' não encontrado.\n\n"
                    f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
                )
        else:
            if not self.workers or len(self.workers) == 0:
                await update.message.reply_text(
                    "❌ Nenhum bot ativo encontrado."
                )
                return

            keyboard = []
            for worker in self.workers:
                nome = worker.config.get('nome_instancia', 'N/A')
                par = worker.config.get('par', 'N/A')
                button = InlineKeyboardButton(
                    text=f"💥 Ativar Crash {nome} ({par})",
                    callback_data=f"crash:{nome}"
                )
                keyboard.append([button])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "*Selecione o bot para ativar o Modo Crash:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
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
            await update.message.reply_text(
                f"✅ *MODO CRASH DESATIVADO* para '{nome_bot}'\n\n"
                f"Retornando ao modo de operação normal.",
                parse_mode='Markdown'
            )
        else:
            bots_disponiveis = [w.config.get('nome_instancia', 'N/A') for w in self.workers]
            await update.message.reply_text(
                f"❌ Bot '{nome_bot}' não encontrado.\n\n"
                f"Bots disponíveis:\n" + "\n".join([f"• {b}" for b in bots_disponiveis])
            )
    
    @restricted_access
    async def parar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Para todos os bots e desliga o sistema graciosamente."""
        if self.shutdown_callback:
            # Usar context.bot.send_message para evitar AttributeError
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
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
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa callbacks dos botões inline."""
        query = update.callback_query
        await query.answer()
        
        # Verificar autorização
        user_id = update.effective_user.id
        if user_id != self.authorized_user_id:
            await query.edit_message_text(text="❌ Acesso não autorizado.")
            return
        
        data = query.data
        
        if data.startswith('pause:'):
            nome_bot = data.split(':', 1)[1]
            
            # Procurar o bot
            bot_encontrado = None
            for worker in self.workers:
                if worker.config.get('nome_instancia') == nome_bot:
                    bot_encontrado = worker
                    break
            
            if bot_encontrado:
                bot_encontrado.command_queue.put({'comando': 'pausar_compras'})
                await query.edit_message_text(
                    text=f"✅ *Compras pausadas* para '{nome_bot}'.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(text=f"❌ Bot '{nome_bot}' não encontrado.")
        
        elif data.startswith('resume:'):
            nome_bot = data.split(':', 1)[1]
            
            # Procurar o bot
            bot_encontrado = None
            for worker in self.workers:
                if worker.config.get('nome_instancia') == nome_bot:
                    bot_encontrado = worker
                    break
            
            if bot_encontrado:
                bot_encontrado.command_queue.put({'comando': 'liberar_compras'})
                await query.edit_message_text(
                    text=f"✅ *Compras liberadas* para '{nome_bot}'.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(text=f"❌ Bot '{nome_bot}' não encontrado.")
        
        elif data.startswith('saldo:'):
            nome_bot = data.split(':', 1)[1]
            if nome_bot.upper() == 'TOTAL':
                total_usdt = 0
                total_posicao_usdt = 0
                for worker in self.workers:
                    status = worker.get_status_dict()
                    total_usdt += status.get('saldo_disponivel_usdt', 0)
                    total_posicao_usdt += status.get('status_posicao', {}).get('valor_total', 0)
                
                response = (
                    f"💰 **Saldo Total Consolidado**\n\n"
                    f"- **Valor em Posições:** ${total_posicao_usdt:.2f}\n"
                    f"- **Saldo USDT Disponível:** ${total_usdt:.2f}\n"
                    f"-----------------------------------\n"
                    f"**Total Geral:** **${total_posicao_usdt + total_usdt:.2f}**"
                )
                await query.edit_message_text(response, parse_mode='Markdown')
                return

            bot_encontrado = None
            for worker in self.workers:
                if worker.config.get('nome_instancia') == nome_bot:
                    bot_encontrado = worker
                    break
            
            if bot_encontrado:
                status = bot_encontrado.get_status_dict()
                posicao = status.get('status_posicao', {})
                response = (
                    f"💰 **Saldo do Bot: {status.get('nome_instancia')} ({status.get('par')})**\n\n"
                    f"- **Posição:** {posicao.get('quantidade', 0):.2f} {status.get('ativo_base', 'N/A')}\n"
                    f"- **Valor da Posição:** ${posicao.get('valor_total', 0):.2f}\n"
                    f"- **Saldo USDT Disponível:** ${status.get('saldo_disponivel_usdt', 0):.2f}"
                )
                await query.edit_message_text(response, parse_mode='Markdown')
            else:
                await query.edit_message_text(text=f"❌ Bot '{nome_bot}' não encontrado.")

        elif data.startswith('crash:'):
            nome_bot = data.split(':', 1)[1]
            bot_encontrado = None
            for worker in self.workers:
                if worker.config.get('nome_instancia') == nome_bot:
                    bot_encontrado = worker
                    break
            
            if bot_encontrado:
                bot_encontrado.command_queue.put({'comando': 'ativar_modo_crash'})
                await query.edit_message_text(
                    text=f"💥 *MODO CRASH ATIVADO* para '{nome_bot}'.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(text=f"❌ Bot '{nome_bot}' não encontrado.")
    
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

    async def enviar_mensagem(self, user_id: int, mensagem: str):
        """Envia uma mensagem proativa para um usuário específico.
        
        Args:
            user_id: ID do usuário do Telegram
            mensagem: Texto da mensagem a ser enviada
        """
        await self.application.bot.send_message(chat_id=user_id, text=mensagem)

    async def run(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("saldo", self.saldo))
        self.application.add_handler(CommandHandler("pausar", self.pausar))
        self.application.add_handler(CommandHandler("liberar", self.liberar))
        self.application.add_handler(CommandHandler("crash", self.crash))
        self.application.add_handler(CommandHandler("crash_off", self.crash_off))
        self.application.add_handler(CommandHandler("parar", self.parar))
        self.application.add_handler(CommandHandler("ajuda", self.ajuda))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))

        # Adicionar um handler para comandos não reconhecidos
        self.application.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep the bot running
        import asyncio
        await asyncio.Event().wait()
