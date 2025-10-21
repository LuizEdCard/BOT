# Sistema de Notificações Proativas - Notifier

## Visão Geral

O `Notifier` é um sistema de notificações proativas que permite aos workers enviarem mensagens ao usuário via Telegram de forma simples e direta.

## Arquitetura

```
┌──────────────┐
│ BotWorker    │
│              │
│ self.notifier│─────┐
└──────────────┘     │
                     │
┌──────────────┐     │      ┌─────────────┐      ┌──────────────┐
│ BotWorker    │     ├─────>│  Notifier   │─────>│ TelegramBot  │─────> Usuario
│              │     │      └─────────────┘      └──────────────┘
│ self.notifier│─────┘
└──────────────┘
```

## Como Usar

### 1. Acesso ao Notifier

Todos os `BotWorker` agora têm acesso ao notifier através de `self.notifier`:

```python
# Em qualquer método do BotWorker
if self.notifier:
    self.notifier.enviar_notificacao("Mensagem para o usuário")
```

### 2. Métodos Disponíveis

#### `enviar_notificacao(mensagem: str) -> bool`
Envia uma mensagem simples para o usuário.

```python
if self.notifier:
    sucesso = self.notifier.enviar_notificacao(
        "🎯 Nova oportunidade de compra detectada!"
    )
```

#### `enviar_alerta(titulo: str, mensagem: str) -> bool`
Envia um alerta formatado (com ícone de alerta).

```python
if self.notifier:
    self.notifier.enviar_alerta(
        titulo="Exposição Máxima Atingida",
        mensagem="Bot ADA atingiu 90% de exposição. Compras suspensas."
    )
```

#### `enviar_info(titulo: str, mensagem: str) -> bool`
Envia uma informação formatada (com ícone de informação).

```python
if self.notifier:
    self.notifier.enviar_info(
        titulo="Sistema Atualizado",
        mensagem="Nova versão do bot instalada com sucesso."
    )
```

#### `enviar_sucesso(titulo: str, mensagem: str) -> bool`
Envia uma mensagem de sucesso formatada (com ícone de check).

```python
if self.notifier:
    self.notifier.enviar_sucesso(
        titulo="Meta de Lucro Atingida",
        mensagem="Bot XRP: Venda executada com +5.2% de lucro!"
    )
```

## Exemplos Práticos

### Exemplo 1: Notificar sobre Divergência de Saldo

```python
# Em bot_worker.py - método _sincronizar_saldos_exchange()
def _sincronizar_saldos_exchange(self):
    # ... código existente ...

    if diferenca_absoluta > tolerancia:
        # Log normal
        self.logger.warning("⚠️ DIVERGÊNCIA DETECTADA!")

        # Notificação proativa ao usuário
        if self.notifier:
            self.notifier.enviar_alerta(
                titulo="Divergência de Saldo Detectada",
                mensagem=f"Bot {self.config.get('nome_instancia')}\n"
                        f"Diferença: {diferenca_absoluta:.2f} {base_currency}\n"
                        f"Iniciando auto-correção..."
            )
```

### Exemplo 2: Notificar sobre Guardião de Exposição

```python
# Em strategy_dca.py - método _verificar_guardiao_exposicao()
def _verificar_guardiao_exposicao(self) -> bool:
    # ... código existente ...

    if alocacao_atual > limite_exposicao:
        if not self.notificou_exposicao_maxima:
            self.logger.warning(f"🛡️ GUARDIÃO ATIVADO")

            # Notificar o usuário via Notifier
            if self.worker.notifier:
                self.worker.notifier.enviar_alerta(
                    titulo="Guardião de Exposição Ativado",
                    mensagem=f"Bot: {self.worker.config.get('nome_instancia')}\n"
                            f"Exposição atual: {alocacao_atual:.1f}%\n"
                            f"Limite: {limite_exposicao}%\n\n"
                            f"Compras normais suspensas."
                )
```

### Exemplo 3: Notificar sobre Oportunidade Extrema

```python
# Em strategy_dca.py - método _verificar_oportunidades_extremas()
def _verificar_oportunidades_extremas(self, preco_atual: Decimal):
    # ... código existente ...

    if gatilho_atingido:
        self.logger.info(f"🚨 {motivo.upper()} DETECTADA!")

        # Notificar o usuário sobre oportunidade extrema
        if self.worker.notifier:
            self.worker.notifier.enviar_info(
                titulo="Oportunidade Extrema Detectada",
                mensagem=f"Bot: {self.worker.config.get('nome_instancia')}\n"
                        f"{motivo}\n"
                        f"Preço atual: ${preco_atual:.6f}\n"
                        f"Valor da compra: ${valor_compra_usdt:.2f}"
            )
```

### Exemplo 4: Notificar sobre Modo Crash

```python
# Em bot_worker.py - método _processar_comandos()
elif comando.get('comando') == 'ativar_modo_crash':
    self.modo_crash_ativo = True
    self.logger.warning("💥 MODO CRASH ATIVADO!")

    # Notificar usuário sobre ativação
    if self.notifier:
        self.notifier.enviar_alerta(
            titulo="Modo Crash Ativado",
            mensagem=f"Bot: {self.config.get('nome_instancia')}\n\n"
                    f"⚠️ Compras agressivas liberadas\n"
                    f"⚠️ Restrições de exposição IGNORADAS\n"
                    f"⚠️ Verificação de PM DESABILITADA"
        )
```

### Exemplo 5: Notificar sobre Erro Crítico

```python
# Em bot_worker.py - método run()
except Exception as e:
    self.logger.error(f"❌ Erro crítico no bot: {e}")

    # Notificar usuário sobre erro
    if self.notifier:
        self.notifier.enviar_alerta(
            titulo="Erro Crítico no Bot",
            mensagem=f"Bot: {self.config.get('nome_instancia')}\n\n"
                    f"Erro: {str(e)[:200]}\n\n"
                    f"O bot foi interrompido."
        )
```

## Boas Práticas

1. **Sempre verifique se o notifier existe** antes de usar:
   ```python
   if self.notifier:
       self.notifier.enviar_notificacao("...")
   ```

2. **Use o método apropriado** para cada tipo de notificação:
   - `enviar_alerta()` → Problemas, avisos importantes
   - `enviar_info()` → Informações gerais, mudanças de estado
   - `enviar_sucesso()` → Confirmações de sucesso
   - `enviar_notificacao()` → Mensagens genéricas

3. **Seja conciso** nas mensagens:
   - Título: 3-5 palavras
   - Mensagem: 1-4 linhas

4. **Evite spam** de notificações:
   - Não envie notificação a cada ciclo do loop
   - Use flags para notificar apenas uma vez por evento

5. **Inclua contexto relevante**:
   - Nome do bot
   - Par de trading
   - Valores específicos

## Formato das Mensagens

### Alerta
```
🚨 **Título do Alerta**

Corpo da mensagem
```

### Info
```
ℹ️ **Título da Informação**

Corpo da mensagem
```

### Sucesso
```
✅ **Título do Sucesso**

Corpo da mensagem
```

## Integração Completa

O Notifier está totalmente integrado:

1. ✅ Classe `Notifier` criada em `src/utils/notifier.py`
2. ✅ `BotWorker` modificado para aceitar `notifier`
3. ✅ `manager.py` cria instância do `Notifier`
4. ✅ `Notifier` injetado em todos os workers

Agora você pode usar `self.notifier` em qualquer método do `BotWorker` ou acessar via `self.worker.notifier` nas estratégias!
