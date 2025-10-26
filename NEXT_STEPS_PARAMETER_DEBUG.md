# Next Steps: Debugging Parameter Propagation Issue

## 🎯 Your Task

Execute the backtest with debugging enabled to help identify where the `alocacao_capital_pct` parameter is being lost or reset.

---

## 📋 Step-by-Step Instructions

### 1. Open Terminal and Navigate to Project

```bash
cd /home/cardoso/Documentos/BOT
source venv/bin/activate
```

### 2. Run the Backtest Script

```bash
python backtest.py
```

### 3. Follow the Interactive Prompts

**Important:** These are the exact selections you should make:

```
1️⃣  Config file:
    → Select: backtest_template.json
    (This has the default 20% allocation)

2️⃣  CSV file:
    → Select any CSV file with historical data
    (e.g., BINANCE_ADAUSDT_5m_...)

3️⃣  Timeframe:
    → Select: 5m (or any timeframe)

4️⃣  Initial balance:
    → Type: 1000

5️⃣  Exchange fee:
    → Type: 0.1

6️⃣  Strategies:
    → Select: giro_rapido (space to select, enter to confirm)

7️⃣  Strategy timeframe selection:
    → Use defaults or select any timeframe

8️⃣  RSI questions:
    → Confirm: yes
    → RSI limit: 35
    → RSI timeframe: 5m

9️⃣  Stop Loss Inicial:
    → Type: 1.0

🔟  Trailing Stop Distance:
    → Type: 0.5

1️⃣1️⃣  TSL Gatilho de Lucro:
    → Type: 2.5

1️⃣2️⃣  **MOST IMPORTANT** - Alocação de Capital:
    → Type: 50
    (Change from the displayed default of 20 to 50)

1️⃣3️⃣  Confirmação final:
    → Type: y (or just press Enter)
```

---

## 🔍 What to Look For

### CRITICAL DEBUG OUTPUT

The script will print several `[DEBUG]` sections. **Please capture ALL of them**, but pay special attention to:

#### Debug Point 1: Parameter Collection
```
[DEBUG] perguntar_parametros_giro_rapido retornando:
[DEBUG] params = {...'alocacao_capital_pct': 50.0...}
```
✅ **Expected:** Should show `alocacao_capital_pct': 50.0`

#### Debug Point 2: Parameter Application
```
[DEBUG] aplicar_parametros_estrategias aplicando Giro Rápido:
[DEBUG] params_giro = {...'alocacao_capital_pct': 50.0...}
[DEBUG]   Aplicado: estrategia_giro_rapido['alocacao_capital_pct'] = 50.0
[DEBUG] config_bot['estrategia_giro_rapido'] após aplicação = {
    ...
    'alocacao_capital_pct': 50.0,
    ...
}
```
✅ **Expected:** Should show `50.0` being applied

#### Debug Point 3: After Application (in RESUMO section)
```
[DEBUG] Configuração de Giro Rápido após aplicar parâmetros:
[DEBUG] config['estrategia_giro_rapido'] = {
    ...
    'alocacao_capital_pct': 50.0,
    ...
}
```
✅ **Expected:** Should show `50.0`

#### Debug Point 4: Before BotWorker (CRITICAL)
```
[DEBUG] Configuração de Giro Rápido ANTES de iniciar BotWorker:
[DEBUG] config['estrategia_giro_rapido'] = {
    ...
    'alocacao_capital_pct': ???,  ← WATCH THIS VALUE!
    ...
}
```
⚠️ **CRITICAL:** Does this show `50.0` or `20`?

---

## 📊 What the Output Should Tell Us

| Scenario | Debug Point 4 Shows | Diagnosis |
|----------|-------------------|-----------|
| ✅ Works correctly | `'alocacao_capital_pct': 50.0` | Parameter is applied correctly - issue might be elsewhere |
| ❌ Parameter lost | `'alocacao_capital_pct': 20` | Parameter is being reset somewhere between points 3 and 4 |
| ⚠️ Wrong location | Different structure entirely | Config structure mismatch issue |

---

## 📸 How to Capture Output

### Option 1: Copy from Terminal (Simplest)
1. Run the backtest
2. When it completes, scroll up to find all `[DEBUG]` lines
3. Copy them and paste into a text file or directly share with me

### Option 2: Save to File
```bash
python backtest.py > backtest_output.log 2>&1
```
Then open `backtest_output.log` and look for `[DEBUG]` lines

### Option 3: Real-Time Capture
Keep the terminal window open during execution and screenshot/copy the debug output

---

## 🎬 Example of Expected Output

When you set allocation to 50 and everything works correctly, you should see:

```
Alocação de Capital? (atual: 20%)
   ℹ️  Porcentagem do capital total para Giro Rápido
   Qual o % de capital para Giro Rápido: 50
   ✅ Alocação de Capital: 50%

[DEBUG] perguntar_parametros_giro_rapido retornando:
[DEBUG] params = {'usando_filtro_rsi_entrada': True, 'rsi_limite_compra': 35.0, ..., 'alocacao_capital_pct': 50.0}

[... more debug output ...]

[DEBUG] Configuração de Giro Rápido após aplicar parâmetros:
[DEBUG] config['estrategia_giro_rapido'] = {..., 'alocacao_capital_pct': 50.0, ...}

[... backtest summary section ...]

📋 RESUMO FINAL DA CONFIGURAÇÃO
   ...
   💨 Giro Rápido (Swing Trade v3.0):
      ...
      Alocação de Capital: 50.0%    ← Should show 50 here!
      ...

[DEBUG] Configuração de Giro Rápido ANTES de iniciar BotWorker:
[DEBUG] config['estrategia_giro_rapido'] = {..., 'alocacao_capital_pct': 50.0, ...}
                                                                              ^^^^ CRITICAL - Should be 50
```

---

## 🚨 If Execution Fails

If the script crashes or has an error:

1. **Take a screenshot** of the error message
2. **Note the line number** where the error occurred
3. **Share the full error message**

---

## ✉️ What to Share With Me

Please provide:

1. ✅ **All `[DEBUG]` output** (paste the lines or the output file)
2. ✅ **The RESUMO FINAL section** showing the allocation value
3. ✅ **The final backtest results** showing how much capital was actually allocated

---

## ⏱️ Estimated Time

- Running the backtest: ~5-30 seconds (depends on data size)
- Copying debug output: ~2 minutes
- **Total: Less than 5 minutes**

---

## 📌 Important Notes

- **Don't worry about the backtest results** - we're just focused on the debug output
- **All parameters except allocation can use defaults** - we only care about allocation = 50%
- **If you see errors**, that's okay - just share the error messages
- **The debug output is harmless** - it won't affect the actual backtest logic

---

**Ready to debug? Let's go! 🚀**

Once you run this and share the output, we'll be able to identify exactly where the parameter is being lost or reset.

