# 💥 Modo CRASH - Documentação Completa

## 📋 O que é o Modo Crash?

O **Modo Crash** é uma funcionalidade avançada de emergência que permite ao bot realizar **compras agressivas** durante quedas severas do mercado (crashes), ignorando restrições de segurança que normalmente limitariam as compras.

---

## ⚙️ Como Funciona

### 1. Ativação
```
/crash [nome_do_bot]
```
Exemplo: `/crash ADA`

**Localização no código**: `src/telegram_bot.py:177-211`

### 2. Desativação
```
/crash_off [nome_do_bot]
```
Exemplo: `/crash_off ADA`

**Localização no código**: `src/telegram_bot.py:214-247`

---

## 🔧 Comportamento Técnico

### Flag de Estado
Quando ativado, define `self.modo_crash_ativo = True` no BotWorker (`src/core/bot_worker.py:94`).

### Restrições Ignoradas

O modo crash modifica o comportamento da **Estratégia DCA** (`src/core/strategy_dca.py:79-96`):

#### 1. **Guardião de Exposição Máxima** ❌ DESLIGADO
- **Normal**: Quando você atinge 70% de exposição em ADA, compras param
- **Modo Crash**: Ignora completamente esse limite
- **Código**: `src/core/strategy_dca.py:86`
```python
if not modo_crash and not self._verificar_guardiao_exposicao():
    return self._verificar_oportunidades_extremas(preco_atual)
```

#### 2. **Verificação de Melhora do Preço Médio** ❌ DESLIGADO
- **Normal**: Bot só compra se melhorar o preço médio em 2%
- **Modo Crash**: Compra mesmo piorando temporariamente o preço médio
- **Código**: `src/core/strategy_dca.py:96`
```python
if not modo_crash and not self._verificar_dupla_condicao(degrau_ativo, preco_atual, distancia_sma):
    return None
```

#### 3. **Cooldowns** ✅ MANTIDOS
- Os intervalos entre compras (global e por degrau) continuam sendo respeitados
- Isso evita que o bot execute centenas de ordens em segundos

---

## 📊 Fluxo de Operação

```mermaid
graph TD
    A[/crash ADA via Telegram] --> B[TelegramBot.crash]
    B --> C[command_queue.put ativar_modo_crash]
    C --> D[BotWorker._processar_comandos]
    D --> E[modo_crash_ativo = True]
    E --> F[Loop principal do bot]
    F --> G[StrategyDCA.verificar_oportunidade]
    G --> H{modo_crash?}
    H -->|Sim| I[IGNORA guardião exposição]
    H -->|Sim| J[IGNORA melhora PM]
    I --> K[Compra agressiva permitida]
    J --> K
```

---

## ⚠️ Riscos e Cuidados

### Riscos
1. **Aumento drástico de exposição**: Pode chegar a 90-100% de capital em ADA
2. **Piora temporária do PM**: Compras podem piorar o preço médio
3. **Capital esgotado rapidamente**: Sem guardião, capital disponível pode ser usado totalmente

### Quando Usar
- ✅ Crashes severos do mercado (quedas > 20%)
- ✅ Você acredita fortemente que o ativo está subvalorizado
- ✅ Você tem saldo USDT disponível e quer acumular

### Quando NÃO Usar
- ❌ Quedas normais/moderadas (< 10%)
- ❌ Quando já está com exposição alta (> 70%)
- ❌ Sem certeza sobre a recuperação do mercado

---

## 🧪 Exemplo Prático

### Situação Antes do Crash Mode
```
Capital Total: $1000
Posição ADA: $700 (70% - LIMITE ATINGIDO)
Saldo USDT: $300
Preço Médio ADA: $0.50
Preço Atual: $0.40 (-20% da SMA)

Status: ⛔ Compras bloqueadas pelo guardião
```

### Ativação do Modo Crash
```
Telegram: /crash ADA
Bot: 💥 MODO CRASH ATIVADO para 'ADA'
     ⚠️ Compras agressivas liberadas!
     ⚠️ Restrições de exposição e preço médio ignoradas.
```

### Situação Após Compras no Modo Crash
```
Capital Total: $1000
Posição ADA: $950 (95% de exposição)
Saldo USDT: $50
Preço Médio ADA: $0.47 (melhorou de $0.50)
Preço Atual: $0.40

Status: ✅ Compras executadas ignorando guardião
```

### Desativação
```
Telegram: /crash_off ADA
Bot: ✅ MODO CRASH DESATIVADO para 'ADA'
     Retornando ao modo de operação normal.
```

---

## 📝 Log do Sistema

Quando o modo crash é ativado, você verá no console:

```
💥============================================================
💥 MODO CRASH ATIVADO!
💥 Compras agressivas liberadas
💥 Restrições de exposição e preço médio IGNORADAS
💥============================================================

💥 MODO CRASH: Ignorando restrições de exposição e preço médio
🎯 Degrau 3 ativado! Queda: -22.50%
✅ Compra executada com sucesso!
```

---

## 🔄 Comandos Relacionados

| Comando | Descrição |
|---------|-----------|
| `/crash [nome]` | Ativa modo crash (compras agressivas) |
| `/crash_off [nome]` | Desativa modo crash |
| `/pausar [nome]` | Pausa todas as compras (mais conservador) |
| `/liberar [nome]` | Libera compras pausadas |
| `/status` | Verifica estado atual do bot |

---

## 🛠️ Referências no Código

| Arquivo | Linha | Descrição |
|---------|-------|-----------|
| `src/telegram_bot.py` | 177-211 | Comando `/crash` |
| `src/telegram_bot.py` | 214-247 | Comando `/crash_off` |
| `src/core/bot_worker.py` | 94 | Flag `modo_crash_ativo` |
| `src/core/bot_worker.py` | 224-234 | Processamento dos comandos |
| `src/core/strategy_dca.py` | 79-96 | Lógica de ignorar restrições |

---

## 💡 Dica Profissional

Use o modo crash com moderação e sempre monitore:
1. **Exposição total** em ADA
2. **Preço médio** antes e depois
3. **Saldo USDT** restante

Considere desativar assim que a queda se estabilizar para permitir que o guardião proteja seu capital novamente.
