# Bug do Event Loop no Telegram Bot

## Problema Identificado

O erro `RuntimeError: Event loop is closed` ocorre quando você usa o comando `/pausar` (modo interativo com botões). 

### Stack Trace
```
RuntimeError: Event loop is closed
telegram.error.NetworkError: Unknown error in HTTP implementation: RuntimeError('Event loop is closed')
```

## Causa Raiz

O problema acontece porque:

1. O bot do Telegram está rodando em um event loop dedicado em uma thread separada
2. Quando usamos `asyncio.run()` em `manager.py` para executar o bot, ele cria e gerencia seu próprio event loop
3. Tentativas de criar novos event loops ou usar o loop existente de forma incorreta causam conflitos

## Status Atual

✅ **Comandos que funcionam:**
- `/pausar [nome_bot]` - Com argumento direto
- `/liberar [nome_bot]` - Com argumento direto
- `/crash [nome_bot]`
- `/crash_off [nome_bot]`
- `/status`
- `/start`
- `/ajuda`
- `/parar`

⚠️ **Comandos com problema:**
- `/pausar` - Sem argumentos (botões interativos)
- `/liberar` - Sem argumentos (botões interativos)

## Solução Temporária Aplicada

O relatório horário automático foi **desabilitado temporariamente** para evitar conflitos de event loop. Os logs mostram o conteúdo do relatório, mas não enviam via Telegram.

## Soluções Permanentes Recomendadas

### Opção 1: Usar apenas comandos com argumentos (RECOMENDADO - SIMPLES)

Remover completamente a funcionalidade de botões inline e usar apenas comandos diretos:
- `/pausar ADA` ao invés de `/pausar` com botões
- `/liberar XRP` ao invés de `/liberar` com botões

**Vantagens:**
- Simples, direto, sem bugs
- Menor overhead
- Funciona perfeitamente

**Desvantagens:**
- Menos user-friendly
- Precisa lembrar nomes dos bots

### Opção 2: Implementar Message Queue para Comunicação

Criar um sistema de filas para comunicação entre o loop principal e o bot Telegram:

```python
# No manager.py
message_queue = queue.Queue()

# No TelegramBot
async def enviar_mensagem_queue(self, user_id, mensagem):
    # Adiciona à fila ao invés de enviar diretamente
    self.message_queue.put({'user_id': user_id, 'message': mensagem})

# No loop do Telegram, processar mensagens da fila
while True:
    if not message_queue.empty():
        msg = message_queue.get()
        await self.application.bot.send_message(...)
```

**Vantagens:**
- Mantém botões interativos
- Resolve conflitos de event loop
- Mais robusto

**Desvantagens:**
- Mais complexo de implementar
- Requer refatoração significativa

### Opção 3: Atualizar Arquitetura do Bot Telegram

Mudar de `asyncio.run()` para gerenciamento manual de event loop:

```python
# Ao invés de
asyncio.run(telegram_bot.run())

# Usar
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_forever()  # Não fechar o loop prematuramente
```

## Recomendação Final

**Para uso em produção imediato:**
- Use comandos com argumentos diretos: `/pausar ADA`, `/liberar XRP`
- Ignore o modo interativo com botões (está comentado mas pode ser removido)

**Para melhorias futuras:**
- Implemente a Opção 2 (Message Queue)
- Isso permitirá:
  - Botões interativos funcionando
  - Relatórios horários automáticos via Telegram
  - Sistema mais robusto e escalável

## Exemplo de Uso Atual (Funcional)

```
/pausar ADA          ✅ Funciona
/liberar ADA         ✅ Funciona
/crash XRP           ✅ Funciona
/crash_off XRP       ✅ Funciona
/status              ✅ Funciona
/parar               ✅ Funciona
```

## Arquivos Afetados

- `manager.py` - Relatório horário desabilitado (linha 283-288)
- `src/telegram_bot.py` - Botões inline implementados mas causam erro de event loop
