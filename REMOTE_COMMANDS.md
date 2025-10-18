# Sistema de Controle Remoto do BotWorker

## Visão Geral
O BotWorker agora possui um sistema de fila de comandos que permite controle remoto de suas operações.

## Comandos Disponíveis

### 1. Pausar Compras
```python
bot_worker.command_queue.put({'comando': 'pausar_compras'})
```
- Pausa todas as compras (DCA, oportunidades extremas, recompras)
- Define `compras_pausadas_manualmente = True`

### 2. Liberar Compras
```python
bot_worker.command_queue.put({'comando': 'liberar_compras'})
```
- Reativa as compras que foram pausadas manualmente
- Define `compras_pausadas_manualmente = False`

### 3. Suspender Guardião
```python
bot_worker.command_queue.put({'comando': 'suspender_guardiao'})
```
- Suspende temporariamente o guardião de exposição máxima
- Define `guardiao_suspenso_temporariamente = True`

### 4. Reativar Guardião
```python
bot_worker.command_queue.put({'comando': 'reativar_guardiao'})
```
- Reativa o guardião de exposição máxima
- Define `guardiao_suspenso_temporariamente = False`

## Fluxo de Processamento

1. **Início do Loop**: A cada ciclo do loop principal, `_processar_comandos()` é chamado
2. **Processamento**: Todos os comandos na fila são processados sequencialmente
3. **Execução**: Os flags de estado são atualizados conforme os comandos
4. **Verificação**: Antes de executar compras, o sistema verifica `compras_pausadas_manualmente`

## Estrutura Interna

### Atributos Adicionados
```python
self.command_queue = queue.Queue()              # Fila de comandos
self.compras_pausadas_manualmente = False       # Flag de pausa manual
self.guardiao_suspenso_temporariamente = False  # Flag de suspensão do guardião
```

### Método Principal
```python
def _processar_comandos(self):
    """Processa comandos da fila de comandos remotos"""
    # Processa todos os comandos pendentes na fila
    # Atualiza flags de estado
    # Registra logs informativos
```

## Ponto de Bloqueio
As compras são bloqueadas em `_executar_oportunidade_compra()`:
```python
if self.compras_pausadas_manualmente:
    self.logger.debug("⏸️  Compra bloqueada: compras pausadas manualmente")
    return False
```

## Exemplo de Uso via Telegram (Futuro)
```python
# No handler do Telegram
if comando == '/pausar':
    for worker in workers:
        worker.command_queue.put({'comando': 'pausar_compras'})
    await update.message.reply_text("✅ Compras pausadas em todos os bots")
```

## Notas Importantes
- Os comandos são processados de forma não-bloqueante (queue.get_nowait)
- Comandos desconhecidos geram warning no log
- O sistema é thread-safe (usando queue.Queue do Python)
- Comandos não afetam vendas, apenas compras
