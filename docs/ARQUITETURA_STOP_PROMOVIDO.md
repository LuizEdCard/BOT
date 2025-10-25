# Arquitetura: Stop Promovido v2.0

## 📋 Visão Geral

O **Stop Promovido** é um sistema de gerenciamento de saída para a estratégia Giro Rápido que automaticamente:

1. **Ativa** um Stop Loss Inicial após cada compra
2. **Monitora** o progresso da posição no loop principal
3. **Promove** o SL para TSL quando a posição atinge breakeven
4. **Gerencia** o TSL dinamicamente até venda ou perda

## 🏗️ Separação de Responsabilidades

### StrategySwingTrade (v2.0)
**Responsabilidade ÚNICA:** Verificar oportunidades de COMPRA

```
┌─────────────────────────────────────────────────────────┐
│  StrategySwingTrade.verificar_oportunidade()            │
├─────────────────────────────────────────────────────────┤
│ 1. Tem posição?                                         │
│    SIM → return None (BotWorker gerencia saída)        │
│    NÃO → continua                                      │
│                                                         │
│ 2. Verificar cooldown entre compras                    │
│                                                         │
│ 3. Obter RSI via analise_tecnica.get_rsi()             │
│                                                         │
│ 4. RSI < 30?                                            │
│    SIM → return {tipo: 'compra', ...}                  │
│    NÃO → return None                                    │
└─────────────────────────────────────────────────────────┘
```

**Métodos:**
- `verificar_oportunidade()` - Verifica entrada (ÚNICO método importante)
- `registrar_compra_executada()` - Registra compra para cooldown

**Removido (v1.0 → v2.0):**
- ❌ `_verificar_oportunidade_venda()` - Agora em BotWorker
- ❌ `_obter_rsi_atual()` - Usa analise_tecnica.get_rsi()
- ❌ `_calcular_rsi_manual()` - Usa analise_tecnica.get_rsi()
- ❌ Qualquer lógica de stop/TSL

---

### BotWorker (v2.0)
**Responsabilidade:** Gerenciar COMPLETAMENTE stops, promoções e saídas

#### 1️⃣ Ativação de SL Inicial

**Quando:** Imediatamente após compra giro_rapido
**Onde:** `_executar_oportunidade_compra()` (após linha 628)

```python
# Código em bot_worker.py (linhas 630-648)
elif carteira == 'giro_rapido':
    # ... registrar compra na strategy ...

    # NOVO: ATIVAR STOP LOSS INICIAL
    stop_loss_inicial_pct = self.strategy_swing_trade.stop_loss_inicial_pct
    nivel_sl = preco_real * (Decimal('1') - stop_loss_inicial_pct / Decimal('100'))

    self.stops_ativos['giro_rapido'] = {
        'tipo': 'sl',
        'nivel_stop': nivel_sl,
        'preco_compra': preco_real
    }

    self._salvar_estado_stops()

    self.logger.info(f"🛡️ STOP LOSS INICIAL ATIVADO (Giro Rápido)")
    self.logger.info(f"   Preço de Compra: ${preco_real:.6f}")
    self.logger.info(f"   Nível SL: ${nivel_sl:.6f}")
    self.logger.info(f"   Distância: {stop_loss_inicial_pct:.2f}%")
```

#### 2️⃣ Verificação de SL no Loop Principal

**Quando:** A cada ciclo de decisão
**Onde:** `_executar_ciclo_decisao()` (linhas 1532-1577)

```
┌─────────────────────────────────────────────────────────┐
│  Loop: VERIFICAÇÃO DE STOP LOSS (tipo='sl')            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ CHECK 1: preço_atual <= nivel_sl?                      │
│   SIM → VENDER (SL disparado)                          │
│   NÃO → continua para CHECK 2                          │
│                                                         │
│ CHECK 2: preço_atual >= preco_medio? (breakeven)       │
│   SIM → PROMOVER PARA TSL (ver abaixo)                 │
│   NÃO → manter SL, aguardar próximo ciclo              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Código:**
```python
elif stop_ativo['tipo'] == 'sl':
    # VERIFICAÇÃO 1: Se SL foi disparado → VENDER
    if preco_atual <= stop_ativo['nivel_stop']:
        self.logger.warning(f"⚠️ Stop Loss ACIONADO [giro_rapido]!")
        self._executar_venda_stop('giro_rapido', 'sl')
        continue

    # VERIFICAÇÃO 2: PROMOÇÃO (SL → TSL) para giro_rapido
    if carteira == 'giro_rapido':
        preco_medio = self.position_manager.get_preco_medio('giro_rapido')
        if preco_medio and preco_atual >= preco_medio:
            # ✅ BREAKEVEN ATINGIDO: Promover para TSL
            # (ver próxima seção)
```

#### 3️⃣ Promoção de Stop (SL → TSL no Breakeven)

**Condição:** `preco_atual >= preco_medio` (lucro >= 0%)
**Ação:** Converter SL fixo em TSL dinâmico

```
ANTES (SL Inicial):
  Compra: $1.00
  SL Nível: $0.975 (-2.5% fixo)

DEPOIS (TSL):
  Pico: $1.005 (preço no breakeven)
  TSL Nível: $0.995 (-0.8% do pico)
  TSL segue o preço dinamicamente
```

**Código:**
```python
if carteira == 'giro_rapido':
    preco_medio = self.position_manager.get_preco_medio('giro_rapido')
    if preco_medio and preco_atual >= preco_medio:
        # PROMOÇÃO AUTOMÁTICA
        distancia_tsl_pct = self.strategy_swing_trade.trailing_stop_distancia_pct
        nivel_tsl_inicial = preco_atual * (Decimal('1') - distancia_tsl_pct / Decimal('100'))

        self.stops_ativos['giro_rapido'] = {
            'tipo': 'tsl',
            'nivel_stop': nivel_tsl_inicial,
            'preco_pico': preco_atual,
            'distancia_pct': distancia_tsl_pct
        }

        self._salvar_estado_stops()

        self.logger.info(f"🎯 PROMOÇÃO DE STOP [giro_rapido]")
        self.logger.info(f"   Stop Loss Inicial → Trailing Stop Loss")
        self.logger.info(f"   Preço Médio: ${preco_medio:.6f}")
        self.logger.info(f"   Preço Atual: ${preco_atual:.6f}")
        self.logger.info(f"   TSL Distância: {distancia_tsl_pct:.2f}%")
```

#### 4️⃣ TSL Update Loop

**Quando:** A cada ciclo quando TSL está ativo
**Onde:** `_executar_ciclo_decisao()` (linhas 1511-1527)

```
┌─────────────────────────────────────────────────────────┐
│  Loop: ATUALIZAÇÃO DE TRAILING STOP LOSS               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ CHECK 1: preço_atual > preco_pico?                     │
│   SIM → Novo pico! Atualizar:                          │
│          - preco_pico = preco_atual                    │
│          - nivel_stop = novo cálculo                   │
│   NÃO → manter nível                                   │
│                                                         │
│ CHECK 2: preço_atual <= nivel_stop?                    │
│   SIM → VENDER (TSL disparado)                         │
│   NÃO → manter TSL, aguardar próximo ciclo             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Código (já existente em bot_worker.py):**
```python
if stop_ativo['tipo'] == 'tsl':
    # a) Atualizar pico se preço subiu
    if preco_atual > stop_ativo['preco_pico']:
        stop_ativo['preco_pico'] = preco_atual
        stop_ativo['nivel_stop'] = preco_atual * (Decimal('1') - stop_ativo['distancia_pct'] / Decimal('100'))
        self._salvar_estado_stops()
        self.logger.debug(f"🔄 TSL ATUALIZADO: Pico ${preco_atual:.4f}, Nível ${stop_ativo['nivel_stop']:.4f}")

    # b) Verificar se preço caiu abaixo do nível
    if preco_atual <= stop_ativo['nivel_stop']:
        self.logger.warning(f"⚠️ Trailing Stop Loss ACIONADO!")
        self._executar_venda_stop('giro_rapido', 'tsl')
```

---

## 🔄 Fluxo Completo: Do Zero ao Resultado

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. COMPRA - StrategySwingTrade verifica entrada                  │
├──────────────────────────────────────────────────────────────────┤
│   RSI check → SIM, atingiu 28% (< 30%)                           │
│   return {tipo: 'compra', quantidade: 100, ...}                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 2. EXECUÇÃO - BotWorker executa compra                          │
├──────────────────────────────────────────────────────────────────┤
│   place_ordem_compra_market()                                    │
│   position_manager.atualizar_apos_compra()                       │
│                                                                  │
│   ✅ NEW: Ativar SL Inicial automaticamente                      │
│      - Compra: $1.00                                             │
│      - SL: $0.975 (-2.5%)                                        │
│      - stops_ativos['giro_rapido'] = {tipo: 'sl', ...}          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 3. MONITORAMENTO - BotWorker verifica stops em cada ciclo        │
├──────────────────────────────────────────────────────────────────┤
│   Ciclo N: Preço = $0.980 (acima de SL)                          │
│     → SL não disparou, preço ainda < preco_medio                 │
│     → Manter SL, continuar                                       │
│                                                                  │
│   Ciclo N+1: Preço = $1.002 (acima de preco_medio)               │
│     → ✅ BREAKEVEN ATINGIDO!                                     │
│     → PROMOVER SL para TSL:                                      │
│        * Desativar SL ($0.975)                                   │
│        * Ativar TSL com pico = $1.002                            │
│        * TSL Nível = $0.992 (-0.8% do pico)                      │
│                                                                  │
│   Ciclo N+2: Preço = $1.010 (novo pico!)                         │
│     → TSL Atualiza:                                              │
│        * preco_pico = $1.010 (novo pico)                         │
│        * nivel_stop = $1.000 (recalculado)                       │
│                                                                  │
│   Ciclo N+3: Preço = $0.998 (abaixo de TSL)                      │
│     → ✅ TSL DISPARADO!                                          │
│     → VENDER 100% da posição                                     │
│     → Lucro realizado: +0.8%                                     │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 4. SAÍDA - BotWorker executa venda e limpa stops                │
├──────────────────────────────────────────────────────────────────┤
│   place_ordem_venda_market()                                     │
│   position_manager.atualizar_apos_venda()                        │
│   stops_ativos['giro_rapido'] = None                             │
│   strategy_swing_trade.registrar_venda_executada()               │
│   → Resetar cooldown, permitir nova compra                       │
└──────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuração Recomendada

### Parâmetros Conservadores
```json
{
  "alocacao_capital_pct": 20,
  "stop_loss_inicial_pct": 3.0,
  "trailing_stop_distancia_pct": 1.0,
  "rsi_limite_compra": 35,
  "rsi_timeframe_entrada": "15m"
}
```

### Parâmetros Agressivos
```json
{
  "alocacao_capital_pct": 50,
  "stop_loss_inicial_pct": 2.0,
  "trailing_stop_distancia_pct": 0.5,
  "rsi_limite_compra": 25,
  "rsi_timeframe_entrada": "5m"
}
```

---

## 🧪 Testes Esperados

### Cenário 1: SL Disparado
```
Compra: $1.00
SL: $0.975
Preço cai para $0.970 → VENDER com -2.5%
```

### Cenário 2: Breakeven & Lucro com TSL
```
Compra: $1.00 → Preco Meio: $1.00
Sobe para $1.010 → Promover para TSL
TSL Pico: $1.010, Nível: $1.002
Sobe para $1.015 → TSL Atualiza (Pico: $1.015, Nível: $1.007)
Cai para $1.006 → VENDER com +0.6%
```

### Cenário 3: Promoção com Múltiplas Atualizações
```
Compra: $1.00
Sobe para $1.005 → Promover (Pico: $1.005, Nível: $0.995)
Sobe para $1.020 → Atualizar (Pico: $1.020, Nível: $1.010)
Sobe para $1.050 → Atualizar (Pico: $1.050, Nível: $1.040)
Cai para $1.038 → VENDER com +3.8%
```

---

## 📊 Logs Esperados

```
🛡️ STOP LOSS INICIAL ATIVADO (Giro Rápido)
   Preço de Compra: $1.000000
   Nível SL: $0.975000
   Distância: 2.50%

🎯 PROMOÇÃO DE STOP [giro_rapido] - BREAKEVEN ATINGIDO
   Stop Loss Inicial → Trailing Stop Loss
   Preço Médio: $1.000000
   Preço Atual: $1.005000
   TSL Distância: 0.80%

🔄 TSL ATUALIZADO [giro_rapido]: Pico $1.0150, Nível $1.0049

⚠️ Trailing Stop Loss ACIONADO [giro_rapido]!
   📈 Pico máximo: $1.015000
   📍 Nível stop: $1.004900
   📉 Preço atual: $1.003000
```

---

## 🚀 Próximas Melhorias

- [ ] Trailing Stop com passo dinâmico (ajusta distância conforme lucro)
- [ ] Martingale de tamanho (aumenta posição em quedas validadas)
- [ ] Breakeven com proteção (não permite perder do pico + 0.1%)
- [ ] Stop Loss técnico (baseado em suporte/resistência em vez de %)
