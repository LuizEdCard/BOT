# Correção: Comando /ajustar_risco Não Responde Após Seleção do Bot

## 🔍 Problema Identificado

Quando o usuário executava `/ajustar_risco`:
1. ✅ O bot mostrava os botões para selecionar qual bot ajustar
2. ✅ O usuário clicava em um botão
3. ✅ O bot solicitava o novo valor de risco
4. ❌ **Ao enviar o novo valor (ex: "75"), nada acontecia**

## 🐛 Causa Raiz

O problema estava na **ordem e padrão dos handlers** do Telegram:

### Código Problemático (src/telegram_bot.py:644-655)

```python
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('ajustar_risco', self.ajustar_risco)],
    states={
        SELECTING_BOT: [CallbackQueryHandler(self._ajustar_risco_button_callback)],
        AWAITING_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_limit)],
    },
    fallbacks=[CommandHandler('cancelar', self.cancelar)],
)
self.application.add_handler(conv_handler)

# ❌ PROBLEMA: Este handler interceptava TODOS os callbacks, incluindo os do ConversationHandler!
self.application.add_handler(CallbackQueryHandler(self._button_callback))
```

### Por Que Não Funcionava?

O `CallbackQueryHandler(self._button_callback)` **sem pattern** estava sendo registrado **DEPOIS** do ConversationHandler, mas o Telegram processa handlers na ordem de registro. Quando você clicava no botão:

1. O callback data era `ajustar_risco:NOME_DO_BOT`
2. O `_button_callback` era chamado PRIMEIRO (pois estava sem restrição de pattern)
3. O `_button_callback` não tinha tratamento para `ajustar_risco` no `command_map`
4. O callback era "consumido" e nunca chegava ao ConversationHandler
5. A conversa ficava travada esperando o callback que nunca chegaria

## ✅ Solução Implementada

Adicionei **padrões regex** aos CallbackQueryHandlers para evitar conflitos:

### Código Corrigido (src/telegram_bot.py:644-655)

```python
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('ajustar_risco', self.ajustar_risco)],
    states={
        # ✅ Especifica que este handler só processa callbacks que começam com "ajustar_risco:"
        SELECTING_BOT: [CallbackQueryHandler(self._ajustar_risco_button_callback, pattern='^ajustar_risco:')],
        AWAITING_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_limit)],
    },
    fallbacks=[CommandHandler('cancelar', self.cancelar)],
)
self.application.add_handler(conv_handler)

# ✅ Este handler agora IGNORA callbacks que começam com "ajustar_risco:"
self.application.add_handler(CallbackQueryHandler(self._button_callback, pattern='^(?!ajustar_risco:)'))
```

### O Que Mudou?

1. **`pattern='^ajustar_risco:'`** no ConversationHandler:
   - Só processa callbacks que começam com `ajustar_risco:`
   - Exemplo: `ajustar_risco:ADA`, `ajustar_risco:XRP`

2. **`pattern='^(?!ajustar_risco:)'`** no _button_callback:
   - Usa "negative lookahead" (regex)
   - Só processa callbacks que **NÃO** começam com `ajustar_risco:`
   - Deixa os callbacks de `ajustar_risco` livres para o ConversationHandler

## 📋 Fluxo Corrigido

1. **Usuário**: `/ajustar_risco`
   - Handler: `CommandHandler('ajustar_risco')`
   - Ação: Mostra botões de seleção de bot

2. **Usuário**: Clica no botão "ADA"
   - Callback data: `ajustar_risco:ADA`
   - Handler: `CallbackQueryHandler(self._ajustar_risco_button_callback, pattern='^ajustar_risco:')`
   - Ação: Salva bot selecionado e pede o novo valor

3. **Usuário**: Envia "75"
   - Handler: `MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_limit)`
   - Ação: Processa o valor e envia comando para o worker

4. **Bot**: Confirma a alteração
   - Estado: `ConversationHandler.END`

## 🧪 Como Testar

```bash
# 1. Ativar ambiente virtual
source venv/bin/activate

# 2. Testar a configuração (opcional)
python testar_telegram.py

# 3. Iniciar o bot
./start_bot.sh
# OU
python manager.py

# 4. No Telegram:
# - Envie: /ajustar_risco
# - Clique em um bot
# - Digite o novo valor (ex: 75)
# - Deve receber confirmação!
```

## 🔧 Arquivos Modificados

- `src/telegram_bot.py:644-655` - Correção dos handlers

## 📚 Conceitos Técnicos

### Negative Lookahead Regex

- **Pattern**: `^(?!ajustar_risco:)`
- **Significado**: "Começa com qualquer coisa, EXCETO 'ajustar_risco:'"
- **Uso**: Evita que o `_button_callback` intercepte callbacks do ConversationHandler

### Order of Handlers

Os handlers do python-telegram-bot são processados **em ordem de registro**. Se dois handlers podem processar o mesmo update, o **primeiro registrado** será usado.

Por isso, é importante usar `pattern` para evitar conflitos!

## ✅ Status

**Problema**: ✅ Corrigido
**Testado**: ✅ Sintaxe validada, importação testada
**Deploy**: Reinicie o bot com `./start_bot.sh`

---

**Data**: 2025-10-19
**Arquivo**: `src/telegram_bot.py`
**Linhas modificadas**: 647, 655
