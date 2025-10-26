# Exemplo de Execução Interativa - Phase 5

**Como usar a nova interface interativa com o parâmetro `tsl_gatilho_lucro_pct`**

---

## 🎯 Exemplo Prático: Configurando Giro Rápido

### Passo 1: Inicie o Backtest
```bash
$ source venv/bin/activate
$ python backtest.py
```

### Passo 2: Selecione a Configuração
```
================================================================================
🔬 LABORATÓRIO DE OTIMIZAÇÃO DE BACKTEST
================================================================================

? 📁 Selecione o arquivo de configuração do bot: (Use arrow keys)
 » estrategia_exemplo_giro_rapido.json
   backtest_template.json
   ...
```

### Passo 3: Nova Interface - SEÇÃO 2: PARÂMETROS DE SAÍDA

Após selecionar data e timeframe, você verá:

```
================================================================================
💨 CONFIGURAÇÃO DE PARÂMETROS - GIRO RÁPIDO (SWING TRADE v2.0)
================================================================================

ARQUITETURA: Stop Promovido com Separação de Responsabilidades

✅ ENTRADA: Baseada em RSI (Relative Strength Index)
✅ SAÍDA: 100% gerenciada pelo BotWorker
   - Fase 1: Stop Loss Inicial após compra
   - Fase 2: Promoção para TSL com gatilho de lucro mínimo (v3.0)
   - Fase 3: TSL segue preço dinamicamente

================================================================================
──────────────────────────────────────────────────────────────────────────────
🛡️  PARÂMETROS DE SAÍDA (STOP PROMOVIDO)
──────────────────────────────────────────────────────────────────────────────

   Stop Loss Inicial? (atual: 2.5%)
   ℹ️  Proteção após compra - ativado automaticamente
   Exemplo: Compra $1.00 → SL em $0.975 (-2.5%)
   ? Qual o Stop Loss inicial (%): 2.5
   ✅ Stop Loss Inicial: 2.5%

   Trailing Stop Distance? (atual: 0.8%)
   ℹ️  Distância TSL do pico - ativado quando gatilho de lucro é atingido
   Exemplo: Pico $1.010 → TSL em $1.002 (-0.8%)
   ? Qual a distância do TSL (%): 0.8
   ✅ Trailing Stop Distance: 0.8%

   ┌─────────────────────────────────────────────────────────────────────┐
   │ 🆕 NOVO PARÂMETRO - TSL Gatilho de Lucro                           │
   └─────────────────────────────────────────────────────────────────────┘

   TSL Gatilho de Lucro? (atual: 1.5%)
   ℹ️  Lucro mínimo (%) necessário para promover Stop Loss → Trailing Stop Loss
   ⚠️  ANTES: Promovia no breakeven (0%), causando muitos ganhos pequenos
   ✅ AGORA: Promove apenas com lucro mínimo garantido

   Exemplos de valores:
      • 0.5%  → Agressivo (promove rápido, mas com pouco lucro garantido)
      • 1.0%  → Moderado-agressivo
      • 1.5%  → Moderado (padrão, melhor balanço)
      • 2.0%  → Moderado-conservador
      • 2.5%  → Conservador (promove devagar, lucro garantido alto)

   ? Qual o lucro mínimo para promover SL → TSL (%): 1.5
   ✅ TSL Gatilho de Lucro: 1.5%
```

---

## 📊 Exemplo de Diferentes Escolhas

### Cenário A: Trader Agressivo
```
   TSL Gatilho de Lucro? (atual: 1.5%)
   ? Qual o lucro mínimo para promover SL → TSL (%): 0.5
   ✅ TSL Gatilho de Lucro: 0.5%

Resultado:
   • Mais trades promovidos para TSL
   • Menos trades com SL (melhor)
   • Ganho médio pode ser menor
   • Ideal: Quando TSL está ganhando muito
```

### Cenário B: Trader Moderado (Padrão)
```
   TSL Gatilho de Lucro? (atual: 1.5%)
   ? Qual o lucro mínimo para promover SL → TSL (%): 1.5
   ✅ TSL Gatilho de Lucro: 1.5%

Resultado:
   • Balanço entre SL e TSL
   • Proteção razoável de ganhos
   • Ganho médio moderado
   • Ideal: Maioria dos casos
```

### Cenário C: Trader Conservador
```
   TSL Gatilho de Lucro? (atual: 1.5%)
   ? Qual o lucro mínimo para promover SL → TSL (%): 2.5
   ✅ TSL Gatilho de Lucro: 2.5%

Resultado:
   • Mais trades com SL
   • Maior lucro mínimo garantido
   • Menos trades total
   • Ideal: Evitar grandes perdas
```

---

## 📋 Resumo Final - Que Você Verá Depois

Após responder todas as perguntas, verá:

```
================================================================================
📋 RESUMO FINAL
================================================================================

   📊 Parâmetros Finais das Estratégias:

      💨 Giro Rápido (Swing Trade v3.0):
         Timeframe Principal: 15m
         Gatilho de Compra: 2.0%
         Filtro RSI: Ativo
         RSI Limite: 30
         RSI Timeframe: 15m
         Stop Loss Inicial: 2.5%
         Trailing Stop Distance: 0.8%
         TSL Gatilho de Lucro: 1.5% (NEW) ← NOVO PARÂMETRO
         Alocação de Capital: 20%

================================================================================
🔄 INICIANDO SIMULAÇÃO...
================================================================================
```

---

## 📊 Resultado Final do Backtest

Depois de rodar o backtest, você verá (NOVO!):

```
🎯 Análise de Saídas (Lucro/Prejuízo por Motivo):

   Stop Loss (SL):
      Quantidade: 500 (44.5%)
      Lucro/Prejuízo Total: $-125.45
      Lucro/Prejuízo Médio: $-0.25 (-0.04%)

   Trailing Stop Loss (TSL):
      Quantidade: 400 (35.6%)
      Lucro/Prejuízo Total: $+480.20
      Lucro/Prejuízo Médio: $+1.20 (+0.18%)

   Meta de Lucro:
      Quantidade: 100 (8.9%)
      Lucro/Prejuízo Total: $+45.80
      Lucro/Prejuízo Médio: $+0.46 (+0.07%)

   Outros:
      Quantidade: 121 (10.8%)
      Lucro/Prejuízo Total: $-8.90
      Lucro/Prejuízo Médio: $-0.07 (-0.01%)
```

---

## 🔄 Fluxo Completo de Testes

### Teste 1: Agressivo (0.5%)
```bash
$ python backtest.py
...
? Qual o lucro mínimo para promover SL → TSL (%): 0.5
✅ TSL Gatilho de Lucro: 0.5%
...
# Resultado: Taxa de Vitória 72%, Lucro Total $380
```

### Teste 2: Padrão (1.5%)
```bash
$ python backtest.py
...
? Qual o lucro mínimo para promover SL → TSL (%): 1.5
✅ TSL Gatilho de Lucro: 1.5%
...
# Resultado: Taxa de Vitória 75%, Lucro Total $391 ← MELHOR
```

### Teste 3: Conservador (2.5%)
```bash
$ python backtest.py
...
? Qual o lucro mínimo para promover SL → TSL (%): 2.5
✅ TSL Gatilho de Lucro: 2.5%
...
# Resultado: Taxa de Vitória 77%, Lucro Total $340
```

### Tabela Comparativa
```
┌─────────────────────────────────────────────────────────┐
│ GATILHO │ TRADES │ WIN RATE │ LUCRO │ SL MÉDIO │ TSL MÉD │
├─────────────────────────────────────────────────────────┤
│ 0.5%    │ 1200   │ 72%      │ $380  │ -$0.18   │ $1.15   │
│ 1.0%    │ 1150   │ 74%      │ $410  │ -$0.20   │ $1.22   │
│ 1.5%    │ 1121   │ 75%      │ $391  │ -$0.25   │ $1.20   │ ✅
│ 2.0%    │ 1080   │ 76%      │ $365  │ -$0.28   │ $1.18   │
│ 2.5%    │ 1040   │ 77%      │ $340  │ -$0.30   │ $1.15   │
└─────────────────────────────────────────────────────────┘

✅ Valor ótimo: 1.5% - Melhor balanço entre Win Rate e Lucro
```

---

## 🎯 Interpretação dos Resultados

### Quando Vejo SL com -$0.25 Médio e TSL com +$1.20 Médio:

**Significa:**
- SL está prejudicando a estratégia
- TSL é o motor de ganhos
- Preciso reduzir SL ou aumentar TSL

**Ação:**
```
OPÇÃO 1: Aumentar tsl_gatilho_lucro_pct
   De: 1.5% → 2.0%
   Efeito: Menos trades com SL, mais com TSL

OPÇÃO 2: Reduzir stop_loss_inicial_pct
   De: 2.5% → 2.0%
   Efeito: Perdas menores quando SL disparar

OPÇÃO 3: Aumentar trailing_stop_distancia_pct
   De: 0.8% → 1.2%
   Efeito: TSL ganha mais antes de disparar
```

---

## 📝 Template para Documentar Seus Testes

```
DATA: 2025-10-25
ATIVO: ADA/USDT
PERÍODO: 2025-01-01 a 2025-02-01

TESTE 1: Gatilho 0.5% (Agressivo)
   Trades Total: 1200
   Taxa de Vitória: 72%
   Lucro SL Médio: -$0.18
   Lucro TSL Médio: $1.15
   Lucro Total: $380
   Drawdown: 8.5%

TESTE 2: Gatilho 1.5% (Padrão) ✅ MELHOR
   Trades Total: 1121
   Taxa de Vitória: 75%
   Lucro SL Médio: -$0.25
   Lucro TSL Médio: $1.20
   Lucro Total: $391
   Drawdown: 7.2%

TESTE 3: Gatilho 2.5% (Conservador)
   Trades Total: 1040
   Taxa de Vitória: 77%
   Lucro SL Médio: -$0.30
   Lucro TSL Médio: $1.15
   Lucro Total: $340
   Drawdown: 5.8%

CONCLUSÃO:
   Valor ótimo: 1.5%
   Motivo: Melhor balanço entre Win Rate (75%) e Lucro Total ($391)
   Próximo Passo: Validar em período diferente
```

---

## ✅ Checklist de Otimização

- [ ] Executar backtest com valor padrão (1.5%)
- [ ] Executar backtest com valor agressivo (0.5%)
- [ ] Executar backtest com valor conservador (2.5%)
- [ ] Documentar resultados em tabela
- [ ] Comparar Win Rate vs Lucro Total
- [ ] Identificar valor ótimo
- [ ] Testar em período diferente para validar
- [ ] Ajustar outros parâmetros se necessário (SL, TSL)
- [ ] Implementar em produção com valor ótimo
- [ ] Monitorar resultados reais em tradução

---

## 🚀 Comandos Rápidos

```bash
# Ativar ambiente
source venv/bin/activate

# Rodar testes automatizados
python test_exit_analysis.py

# Rodar backtest interativo
python backtest.py

# Compilar para verificar erros
python -m py_compile backtest.py
python -m py_compile src/core/bot_worker.py
```

---

**Versão:** 1.0
**Data:** 2025-10-25
**Pronto para Usar:** ✅
