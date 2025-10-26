# Analysis: Parameter Propagation Issue in Giro Rápido

**Date:** 2025-10-25
**Status:** ✅ DEBUG STATEMENTS ADDED & READY FOR USER TESTING
**Issue:** `alocacao_capital_pct` parameter set by user (50%) shows correctly in RESUMO but backtest executes with default (20%)

---

## 🔍 Key Finding

**The parameter propagation logic is WORKING CORRECTLY** based on unit tests:

```
✅ Test 1: Parameter collection in perguntar_parametros_giro_rapido()
   - Correctly collects user input (50%)
   - Returns params dict with alocacao_capital_pct: 50.0

✅ Test 2: Parameter application in aplicar_parametros_estrategias()
   - Correctly applies all parameters to config['estrategia_giro_rapido']
   - After apply: config['estrategia_giro_rapido']['alocacao_capital_pct'] = 50.0

✅ Test 3: Tested with backtest_template.json (default 20%)
   - Before: alocacao_capital_pct = 20
   - After applying user params: alocacao_capital_pct = 50.0
   - ✅ CORRECT - Parameter properly updated
```

**This means the problem must be occurring AFTER line 1099** (when resumo is printed) **and BEFORE or DURING BotWorker initialization**.

---

## 📋 Flow Diagram with New Debug Points

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. perguntar_parametros_giro_rapido()  [Linhas 399-591]             │
│    User inputs: alocacao_capital_pct = 50%                          │
│    Returns: params_giro = {'alocacao_capital_pct': 50.0, ...}       │
│                                                                      │
│    [DEBUG 1] Line 587-588:                                          │
│    ✅ Imprime: params_giro = {'alocacao_capital_pct': 50.0, ...}    │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. aplicar_parametros_estrategias()  [Linhas 594-626]               │
│    Applies params_giro to config['estrategia_giro_rapido']          │
│    Result: config['estrategia_giro_rapido']['alocacao_capital_pct'] │
│             changes from 20 → 50                                    │
│                                                                      │
│    [DEBUG 2] Lines 616-623:                                         │
│    ✅ Imprime params_giro received                                  │
│    ✅ Imprime each parameter being applied                          │
│    ✅ Imprime config after application                              │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. imprimir_resumo_parametros()  [Line 1114]                        │
│    Reads from config['estrategia_giro_rapido']                      │
│    Prints: "Alocação de Capital: 50%"  (supposedly correct)         │
│                                                                      │
│    [DEBUG 3] Lines 1098-1099 (after apply, before resumo):         │
│    ✅ Imprime config['estrategia_giro_rapido'] full dict            │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4. [INVESTIGATION ZONE]  [Lines 1100-1200]                          │
│    - Confirmação (line 1123-1126)                                   │
│    - Benchmark calculation (line 1142)                              │
│    - Temporary file creation (lines 1147-1156)                      │
│    - ESTRATEGIAS structure setup (lines 1162-1185) ⚠️               │
│    - SimulatedExchangeAPI creation (line 1193)                      │
│                                                                      │
│    ❓ QUESTION: Is config being modified here?                      │
│    ❓ QUESTION: Is config['ESTRATEGIAS'] overwriting config?        │
│    ❓ QUESTION: Is SimulatedExchangeAPI modifying config?           │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 5. [DEBUG 4] Lines 1201-1202 (BEFORE BotWorker init):              │
│    ✅ Imprime: config['estrategia_giro_rapido']                     │
│    This will show if allocation is still 50% or reset to 20%        │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 6. BotWorker.__init__()  [Line 1207-1213]                          │
│    Reads config['estrategia_giro_rapido']['alocacao_capital_pct']   │
│    [Line 94 of bot_worker.py]:                                      │
│    alocacao_giro_pct = Decimal(str(                                 │
│        estrategia_giro_config.get('alocacao_capital_pct', 20)       │
│    ))                                                               │
│                                                                      │
│    If DEBUG 4 shows 50, but BotWorker uses 20:                     │
│    → Problem is inside BotWorker initialization                     │
│    → Or config object is being mutated                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 What We Need from User

Execute the backtest with debug output enabled and share the output of DEBUG 1-4:

```bash
# Run backtest interactively
python backtest.py

# When asked:
# 1. Select: backtest_template.json (has 20% default)
# 2. Select CSV file
# 3. Select timeframe
# 4. Select balance: 1000
# 5. Select fee: 0.1
# 6. Select strategy: giro_rapido
# 7. When asked about allocation: 50   (CHANGE FROM DEFAULT 20)
# 8. Continue with other parameters
# 9. Confirm to run
```

**Capture and share ALL `[DEBUG]` lines** from the output, specifically:

```
[DEBUG] perguntar_parametros_giro_rapido retornando:
[DEBUG] params = ...

[DEBUG] aplicar_parametros_estrategias aplicando Giro Rápido:
[DEBUG] params_giro = ...
[DEBUG] Aplicado: estrategia_giro_rapido['alocacao_capital_pct'] = ...
[DEBUG] config_bot['estrategia_giro_rapido'] após aplicação = ...

[DEBUG] Configuração de Giro Rápido após aplicar parâmetros:
[DEBUG] config['estrategia_giro_rapido'] = ...

[DEBUG] Configuração de Giro Rápido ANTES de iniciar BotWorker:
[DEBUG] config['estrategia_giro_rapido'] = ...

[RESUMO FINAL - Alocação de Capital line]
```

---

## 🔬 Hypotheses (in order of likelihood)

### Hypothesis 1: Config structure mismatch
The code might be using two different paths:
- **Applying to:** `config['estrategia_giro_rapido']`
- **BotWorker reads from:** `config['ESTRATEGIAS']['giro_rapido']`

**Evidence:** Lines 1176-1185 create `config['ESTRATEGIAS']` structure, but params applied to `config['estrategia_giro_rapido']`

**To test:** Check DEBUG 4 output - does `config['estrategia_giro_rapido']` still have 50%?

### Hypothesis 2: Config object being replaced
Between DEBUG 3 and DEBUG 4, the config object or a subsection is being reloaded or reset.

**Evidence:** Temporary file creation or SimulatedExchangeAPI init might trigger config reload

**To test:** Compare DEBUG 3 output with DEBUG 4 output - if DEBUG 4 shows 20%, something reset it

### Hypothesis 3: BotWorker internal reset
The BotWorker.__init__() might be reloading configuration from file.

**Evidence:** Would explain why resumo shows 50% but BotWorker uses 20%

**To test:** Check if BotWorker calls `carregar_configuracao()` or json.load() in __init__

### Hypothesis 4: User not seeing updated resumo
The resumo might be showing old value (20%) but user thinks it shows 50%.

**Evidence:** Unlikely given user's explicit statement "resumo final exibe corretamente '50%'"

**To test:** DEBUG 3 output will confirm

---

## ✅ Debug Statements Added

### Location 1: perguntar_parametros_giro_rapido()
**Lines 587-589:**
```python
print(f"\n[DEBUG] perguntar_parametros_giro_rapido retornando:")
print(f"[DEBUG] params = {params}")
```

### Location 2: aplicar_parametros_estrategias()
**Lines 616-623:**
```python
print(f"\n[DEBUG] aplicar_parametros_estrategias aplicando Giro Rápido:")
print(f"[DEBUG] params_giro = {params_giro}")
for key, value in params_giro.items():
    config_bot['estrategia_giro_rapido'][key] = value
    print(f"[DEBUG]   Aplicado: estrategia_giro_rapido['{key}'] = {value}")
print(f"[DEBUG] config_bot['estrategia_giro_rapido'] após aplicação = {config_bot['estrategia_giro_rapido']}")
```

### Location 3: main() - After apply
**Lines 1098-1099:**
```python
print("\n[DEBUG] Configuração de Giro Rápido após aplicar parâmetros:")
print(f"[DEBUG] config['estrategia_giro_rapido'] = {config.get('estrategia_giro_rapido', {})}")
```

### Location 4: main() - Before BotWorker
**Lines 1201-1202:**
```python
print("\n[DEBUG] Configuração de Giro Rápido ANTES de iniciar BotWorker:")
print(f"[DEBUG] config['estrategia_giro_rapido'] = {config.get('estrategia_giro_rapido', {})}")
```

---

## 📝 Unit Test Results

All parameter propagation tests PASSED:

```
Test 1: estrategia_exemplo_giro_rapido.json (50% default)
        ✅ PASS: Parameters correctly applied

Test 2: backtest_template.json (20% default → user sets 50%)
        ✅ PASS: alocacao_capital_pct correctly changed from 20 → 50.0

Test 3: Parameter collection
        ✅ PASS: perguntar_parametros_giro_rapido() returns correct dict

Test 4: Parameter application
        ✅ PASS: aplicar_parametros_estrategias() correctly updates config
```

---

## 🎬 Next Steps

1. **User runs backtest** with debug output visible
2. **User captures all `[DEBUG]` lines** from output
3. **User shares the output** with special focus on:
   - Does allocation change in each DEBUG point?
   - When does it change from 50% back to 20% (if it does)?
4. **Analyze output** to identify which hypothesis is correct
5. **Implement targeted fix** based on findings

---

## 📂 Files Modified

- `backtest.py` - Added 4 debug print statements at strategic points
- No production code modified yet (only debug statements)

---

## ⚙️ How to Run the Test

```bash
# Activate virtual environment
source venv/bin/activate

# Run backtest
python backtest.py

# Select: backtest_template.json (default 20%)
# [...follow prompts...]
# When asked "Qual o % de capital para Giro Rápido:" → Type: 50
# Continue with defaults for other questions
# Confirm to run

# IMPORTANT: Capture ALL output including [DEBUG] lines
```

---

## 📌 Status

**Code:** ✅ Compiles without errors
**Debug Statements:** ✅ All 4 added
**Parameter Propagation Logic:** ✅ Verified working in unit tests
**Root Cause:** ⏳ Awaiting user debug output
**Fix:** ⏳ Pending diagnosis from debug output

---

**Version:** 1.0
**Last Updated:** 2025-10-25
**Awaiting:** User to execute backtest with debug output

