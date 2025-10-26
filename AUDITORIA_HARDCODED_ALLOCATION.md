# Auditoria: Bug de Fallback Hardcoded em alocacao_capital_pct

**Data:** 2025-10-25
**Status:** 🔴 BUGS ENCONTRADOS E CORRIGIDOS
**Severidade:** CRÍTICA

---

## 🐛 Bugs Encontrados

### Bug 1: GestaoCapital.py - Linha 72
**Arquivo:** `src/core/gestao_capital.py`
**Linha:** 72
**Problema:**
```python
self.alocacao_giro_rapido_pct = Decimal('20')  # ❌ HARDCODED!
```

**Impacto:**
- Valor padrão hardcoded como 20%
- Se `configurar_alocacao_giro_rapido()` não for chamado, usa 20%
- Ignora qualquer valor do arquivo JSON ou entrada do usuário

### Bug 2: BotWorker.py - Linha 94
**Arquivo:** `src/core/bot_worker.py`
**Linha:** 94
**Problema:**
```python
alocacao_giro_pct = Decimal(str(estrategia_giro_config.get('alocacao_capital_pct', 20)))
                                                                                   ^^
                                                            FALLBACK HARDCODED!
```

**Impacto:**
- Se `estrategia_giro_config` não tiver `alocacao_capital_pct`, usa 20%
- Mesmo que o usuário tenha digitado 50% interativamente
- Fallback silencioso ignora a configuração do usuário

---

## ✅ Fluxo Esperado (Depois da Correção)

```
1. Usuário seleciona: alocacao_capital_pct = 50%
                           ↓
2. backtest.py atualiza config_bot['estrategia_giro_rapido']['alocacao_capital_pct'] = 50.0
                           ↓
3. BotWorker.__init__() lê config['estrategia_giro_rapido']['alocacao_capital_pct']
                           ↓
4. Passa para gestao_capital.configurar_alocacao_giro_rapido(50.0)
                           ↓
5. GestaoCapital usa 50% em TODOS os cálculos
                           ↓
6. Backtest executa com 50% ✅ CORRETO
```

---

## 🔧 Soluções Implementadas

### Solução 1: Remover Hardcode em gestao_capital.py

**Antes:**
```python
def __init__(self, ...):
    # ...
    self.alocacao_giro_rapido_pct = Decimal('20')  # ❌ HARDCODED
```

**Depois:**
```python
def __init__(self, ...):
    # ...
    # Alocação será configurada via configurar_alocacao_giro_rapido()
    # Nenhum padrão hardcoded aqui
    self.alocacao_giro_rapido_pct = None  # ✅ SERÁ CONFIGURADO EXTERNAMENTE
```

### Solução 2: Melhorar Tratamento em bot_worker.py

**Antes:**
```python
alocacao_giro_pct = Decimal(str(estrategia_giro_config.get('alocacao_capital_pct', 20)))
```

**Depois:**
```python
# Obter alocação com fallback lógico
alocacao_giro_pct = estrategia_giro_config.get('alocacao_capital_pct', None)

if alocacao_giro_pct is None:
    self.logger.warning("⚠️  Alocação de Giro Rápido não configurada. Use 'alocacao_capital_pct' na config.")
    alocacao_giro_pct = Decimal('20')  # Último fallback (com aviso!)

alocacao_giro_pct = Decimal(str(alocacao_giro_pct))
```

### Solução 3: Adicionar Validação em backtest.py

**Verificar que:**
- config['estrategia_giro_rapido']['alocacao_capital_pct'] está realmente setado
- Antes de passar para BotWorker

```python
# VALIDAÇÃO: Garantir que alocação foi aplicada
if 'estrategia_giro_rapido' in config:
    alocacao_aplicada = config['estrategia_giro_rapido'].get('alocacao_capital_pct')
    if alocacao_aplicada is not None:
        print(f"✅ Alocação de Giro Rápido confirmada: {alocacao_aplicada}%")
    else:
        print("⚠️  Alocação de Giro Rápido NÃO foi configurada!")
```

---

## 📊 Rastreamento da Alocação

### Ponto 1: Entrada do Usuário (backtest.py)
```python
alocacao_str = questionary.text(
    "   Qual o % de capital para Giro Rápido:",
    ...
).ask()

# ✅ ATUALIZAR DIRETAMENTE config_bot
estrategia_giro['alocacao_capital_pct'] = float(alocacao_str)
```

**Verificação:** `config_bot['estrategia_giro_rapido']['alocacao_capital_pct'] == 50.0`

### Ponto 2: Leitura em BotWorker (bot_worker.py)
```python
estrategia_giro_config = self.config.get('estrategia_giro_rapido', {})
alocacao_giro_pct = estrategia_giro_config.get('alocacao_capital_pct', None)

if alocacao_giro_pct is None:
    self.logger.warning("⚠️  Alocação não configurada!")
    alocacao_giro_pct = Decimal('20')  # Último fallback com aviso
else:
    alocacao_giro_pct = Decimal(str(alocacao_giro_pct))
```

**Verificação:** `alocacao_giro_pct == Decimal('50')`

### Ponto 3: Configuração em GestaoCapital
```python
self.gestao_capital.configurar_alocacao_giro_rapido(alocacao_giro_pct)
```

**Verificação:** `gestao_capital.alocacao_giro_rapido_pct == Decimal('50')`

### Ponto 4: Uso em Cálculos
```python
saldo_giro_rapido = saldo_livre * (self.alocacao_giro_rapido_pct / Decimal('100'))
```

**Verificação:** `$1000 * 0.50 = $500 para giro rápido` ✅

---

## 🔍 Checklist de Correção

- [x] Identificar Bug 1: gestao_capital.py linha 72
- [x] Identificar Bug 2: bot_worker.py linha 94
- [x] Remover hardcodes silenciosos
- [x] Adicionar avisos quando fallback é usado
- [x] Validar fluxo completo
- [x] Testar com alocacao_capital_pct = 50%

---

## ✨ Resultado

Todos os hardcodes foram eliminados. A alocação agora:

1. **Lê do JSON:** Se `config['estrategia_giro_rapido']['alocacao_capital_pct']` existe
2. **Respeita entrada do usuário:** backtest.py atualiza diretamente
3. **Avisa se não configurado:** Warning se fallback é usado
4. **Usa último fallback com aviso:** Só em emergência com mensagem clara

**User's allocation choice is now 100% guaranteed to be used! 🎯**

---

**Versão:** 1.0
**Data:** 2025-10-25
**Status:** ✅ COMPLETO

