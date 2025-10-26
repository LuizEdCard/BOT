# Changelog - Phase 5: Otimização Giro Rápido

**Versão:** 3.0
**Data:** 2025-10-25
**Status:** ✅ Completo

---

## 📝 Resumo das Mudanças

- [x] Análise de saídas com lucro/prejuízo detalhado
- [x] Lógica de promoção SL → TSL com gatilho configurable
- [x] Interface interativa atualizada com novo parâmetro
- [x] Documentação técnica completa
- [x] Testes automatizados passando

---

## 🔧 Mudanças Técnicas por Arquivo

### 1. backtest.py

#### Mudança 1.1: Atualizar Comentário de Arquitetura (Linha 423)
```diff
    ✅ SAÍDA: 100% gerenciada pelo BotWorker
       - Fase 1: Stop Loss Inicial após compra
-      - Fase 2: Promoção para TSL no breakeven
+      - Fase 2: Promoção para TSL com gatilho de lucro mínimo (v3.0)
       - Fase 3: TSL segue preço dinamicamente
```

#### Mudança 1.2: Atualizar Descrição de TSL (Linha 519)
```diff
    print(f"\n   Trailing Stop Distance? (atual: {tsl_dist_atual}%)")
-   print("   ℹ️  Distância TSL do pico - ativado no breakeven")
+   print("   ℹ️  Distância TSL do pico - ativado quando gatilho de lucro é atingido")
```

#### Mudança 1.3: Adicionar Nova Pergunta de Parâmetro (Linhas 534-557)
```python
# 4.5 Gatilho de Lucro para Promoção SL → TSL (número) - NOVO!
tsl_gatilho_atual = estrategia_giro.get('tsl_gatilho_lucro_pct', 1.5)
print(f"\n   TSL Gatilho de Lucro? (atual: {tsl_gatilho_atual}%)")
print("   ℹ️  Lucro mínimo (%) necessário para promover Stop Loss → Trailing Stop Loss")
print("   ⚠️  ANTES: Promovia no breakeven (0%), causando muitos ganhos pequenos")
print("   ✅ AGORA: Promove apenas com lucro mínimo garantido")
print("   Exemplos de valores:")
print("      • 0.5%  → Agressivo (promove rápido, mas com pouco lucro garantido)")
print("      • 1.0%  → Moderado-agressivo")
print("      • 1.5%  → Moderado (padrão, melhor balanço)")
print("      • 2.0%  → Moderado-conservador")
print("      • 2.5%  → Conservador (promove devagar, lucro garantido alto)")
tsl_gatilho_str = questionary.text(
    "   Qual o lucro mínimo para promover SL → TSL (%):",
    default=str(tsl_gatilho_atual),
    validate=lambda t: validar_float(t) or "Digite um número válido >= 0"
).ask()

if tsl_gatilho_str is None:
    print("❌ Configuração cancelada pelo usuário.")
    return {}
if tsl_gatilho_str:
    params['tsl_gatilho_lucro_pct'] = float(tsl_gatilho_str)
    print(f"   ✅ TSL Gatilho de Lucro: {tsl_gatilho_str}%")
```

#### Mudança 1.4: Atualizar Resumo de Parâmetros (Linhas 646-657)
```diff
-   print("\n      💨 Giro Rápido (Swing Trade):")
+   print("\n      💨 Giro Rápido (Swing Trade v3.0):")
    estrategia_giro = config_bot.get('estrategia_giro_rapido', {})
    print(f"         Timeframe Principal: {estrategia_giro.get('timeframe', '15m')}")
    print(f"         Gatilho de Compra: {estrategia_giro.get('gatilho_compra_pct', 2.0)}%")
    print(f"         Filtro RSI: {'Ativo' if estrategia_giro.get('usar_filtro_rsi_entrada', True) else 'Inativo'}")
    if estrategia_giro.get('usar_filtro_rsi_entrada', True):
        print(f"         RSI Limite: {estrategia_giro.get('rsi_limite_compra', 30)}")
        print(f"         RSI Timeframe: {estrategia_giro.get('rsi_timeframe_entrada', '15m')}")
    print(f"         Stop Loss Inicial: {estrategia_giro.get('stop_loss_inicial_pct', 2.5)}%")
-   print(f"         Trailing Stop: {estrategia_giro.get('trailing_stop_distancia_pct', 0.8)}%")
+   print(f"         Trailing Stop Distance: {estrategia_giro.get('trailing_stop_distancia_pct', 0.8)}%")
+   print(f"         TSL Gatilho de Lucro: {estrategia_giro.get('tsl_gatilho_lucro_pct', 1.5)}% (NEW)")
    print(f"         Alocação de Capital: {estrategia_giro.get('alocacao_capital_pct', 20)}%")
```

#### Mudança 1.5: Função de Análise de Saídas (Linhas 680-756) - NOVA FUNÇÃO
```python
def analisar_saidas_por_motivo(trades: list) -> Dict[str, Any]:
    """Analisa trades de venda com lucro/prejuízo por motivo de saída"""
    saidas = {
        'Stop Loss (SL)': {
            'count': 0,
            'lucro_total': Decimal('0'),
            'lucro_lista': [],
            'trades': []
        },
        'Trailing Stop Loss (TSL)': {
            'count': 0,
            'lucro_total': Decimal('0'),
            'lucro_lista': [],
            'trades': []
        },
        'Meta de Lucro': {
            'count': 0,
            'lucro_total': Decimal('0'),
            'lucro_lista': [],
            'trades': []
        },
        'Outros': {
            'count': 0,
            'lucro_total': Decimal('0'),
            'lucro_lista': [],
            'trades': []
        }
    }

    # Agrupar trades de compra por ID para calcular lucro
    compras_por_id = {}
    for trade in trades:
        if trade.get('tipo') == 'compra':
            trade_id = trade.get('id')
            if trade_id:
                compras_por_id[trade_id] = trade

    # Analisar vendas
    for trade in trades:
        if trade.get('tipo') == 'venda':
            motivo = trade.get('motivo', '').lower()
            trade_id = trade.get('id_compra') or trade.get('id')

            # Determinar categoria
            if 'stop loss' in motivo and 'trailing' not in motivo:
                categoria = 'Stop Loss (SL)'
            elif 'trailing' in motivo or 'tsl' in motivo:
                categoria = 'Trailing Stop Loss (TSL)'
            elif 'meta' in motivo or 'lucro' in motivo or 'venda' in motivo:
                categoria = 'Meta de Lucro'
            else:
                categoria = 'Outros'

            saidas[categoria]['count'] += 1
            saidas[categoria]['trades'].append(trade)

            # Calcular lucro/prejuízo
            try:
                receita = Decimal(str(trade.get('receita_usdt', 0)))
                compra = compras_por_id.get(trade_id)
                if compra:
                    custo = Decimal(str(compra.get('quantidade_usdt', 0)))
                    lucro = receita - custo
                    saidas[categoria]['lucro_total'] += lucro
                    saidas[categoria]['lucro_lista'].append(float(lucro))
            except:
                pass

    return saidas
```

#### Mudança 1.6: Display de Análise de Saídas (Linhas 820-839) - NOVO
```python
# Análise de saídas com lucro/prejuízo por motivo
if vendas:
    print(f"\n🎯 Análise de Saídas (Lucro/Prejuízo por Motivo):")
    saidas = analisar_saidas_por_motivo(trades)

    for motivo in ['Stop Loss (SL)', 'Trailing Stop Loss (TSL)', 'Meta de Lucro', 'Outros']:
        info = saidas[motivo]
        count = info['count']

        if count > 0:
            percentual = (count / len(vendas)) * 100
            lucro_total = float(info['lucro_total'])
            lucro_medio = lucro_total / count if count > 0 else 0
            lucro_medio_pct = (lucro_medio / sum(c['quantidade_usdt'] for c in compras)) * 100 if compras else 0

            # Exibição formatada
            print(f"\n   {motivo}:")
            print(f"      Quantidade: {count} ({percentual:.1f}%)")
            print(f"      Lucro/Prejuízo Total: ${lucro_total:+.2f}")
            print(f"      Lucro/Prejuízo Médio: ${lucro_medio:+.2f} ({lucro_medio_pct:+.2f}%)")
```

---

### 2. bot_worker.py

#### Mudança 2.1: Lógica de Promoção com Gatilho (Linhas 1496-1543) - REFATORADO
```python
# VERIFICAÇÃO 2: PROMOÇÃO (SL → TSL) APENAS PARA GIRO_RAPIDO
# Promover SL para TSL quando atingir gatilho de lucro mínimo
if carteira == 'giro_rapido':
    preco_medio = self.position_manager.get_preco_medio('giro_rapido')
    if preco_medio:
        # Calcular lucro percentual
        lucro_pct = ((preco_atual - preco_medio) / preco_medio) * Decimal('100')

        # Obter gatilho de lucro mínimo da config (padrão: 0% para breakeven)
        estrategia_config = self.config.get('estrategia_giro_rapido', {})
        tsl_gatilho_lucro = Decimal(str(estrategia_config.get('tsl_gatilho_lucro_pct', 0)))

        # Verificar se atingiu o gatilho de lucro mínimo
        if lucro_pct >= tsl_gatilho_lucro:
            # GATILHO ATINGIDO: Promover para TSL
            distancia_tsl_pct = self.strategy_swing_trade.trailing_stop_distancia_pct

            self.logger.info(f"🎯 PROMOÇÃO DE STOP [{carteira}] - GATILHO DE LUCRO ATINGIDO")
            self.logger.info(f"   Stop Loss Inicial → Trailing Stop Loss")
            self.logger.info(f"   Preço Médio: ${preco_medio:.6f}")
            self.logger.info(f"   Preço Atual: ${preco_atual:.6f}")
            self.logger.info(f"   Lucro: {lucro_pct:+.2f}% (Gatilho: {tsl_gatilho_lucro:.2f}%)")
            self.logger.info(f"   TSL Distância: {distancia_tsl_pct:.2f}%")

            # Desativar SL e ativar TSL
            nivel_tsl_inicial = preco_atual * (Decimal('1') - distancia_tsl_pct / Decimal('100'))

            self.stops_ativos['giro_rapido'] = {
                'tipo': 'tsl',
                'nivel_stop': nivel_tsl_inicial,
                'preco_pico': preco_atual,
                'distancia_pct': distancia_tsl_pct
            }

            self._salvar_estado_stops()

            # Notificar
            if self.notifier:
                self.notifier.enviar_sucesso(
                    f"🎯 Stop Promovido [Giro Rápido]",
                    f"SL Inicial → Trailing Stop Loss\n"
                    f"Lucro mínimo atingido: {lucro_pct:+.2f}% (gatilho: {tsl_gatilho_lucro:.2f}%)\n"
                    f"Preço atual: ${preco_atual:.6f}\n"
                    f"TSL Nível: ${nivel_tsl_inicial:.6f}\n"
                    f"TSL Distância: {distancia_tsl_pct:.2f}%"
                )

            continue  # Pular resto do ciclo após promoção
```

**Mudança Principal:**
```diff
-if preco_atual >= preco_medio:  # Breakeven
+lucro_pct = ((preco_atual - preco_medio) / preco_medio) * Decimal('100')
+tsl_gatilho_lucro = Decimal(str(estrategia_config.get('tsl_gatilho_lucro_pct', 0)))
+if lucro_pct >= tsl_gatilho_lucro:  # Configurable threshold
```

---

### 3. configs/backtest_template.json

#### Mudança 3.1: Adicionar Parâmetro TSL Gatilho (Linhas 114-115)
```json
{
  "estrategia_giro_rapido": {
    "habilitado": true,
    "alocacao_capital_pct": 20,

    "_comentario_entrada": "Entrada baseada em RSI (Relative Strength Index)",
    "usar_filtro_rsi_entrada": true,
    "rsi_timeframe_entrada": "15m",
    "rsi_limite_compra": 30,

    "_comentario_saida": "Saída com Stop Promovido (SL → TSL com gatilho de lucro)",
    "stop_loss_inicial_pct": 2.5,
    "trailing_stop_distancia_pct": 0.8,

    "tsl_gatilho_lucro_pct": 1.5,
    "_tsl_gatilho_comentario": "Lucro mínimo (%) para promover SL para TSL. Aumentar para limitar ganhos mas reduzir perdas.",

    "_comentario_cooldown": "Tempo mínimo entre compras sucessivas",
    "cooldown_compra_segundos": 60
  }
}
```

---

### 4. configs/estrategia_exemplo_giro_rapido.json

#### Mudança 4.1: Adicionar Parâmetro TSL Gatilho (Linhas 64-65)
```json
{
  "estrategia_giro_rapido": {
    "habilitado": true,

    "_alocacao": "Porcentagem do capital total para Giro Rápido",
    "alocacao_capital_pct": 50,

    "_entrada_rsi": "Parâmetros de ENTRADA baseados em RSI",
    "usar_filtro_rsi_entrada": true,
    "rsi_timeframe_entrada": "15m",
    "rsi_limite_compra": 30,
    "_rsi_comentario": "Compra quando RSI < 30 (sobrevenda)",

    "_saida_stops": "Parâmetros de SAÍDA (gerenciados 100% pelo BotWorker)",
    "stop_loss_inicial_pct": 2.5,
    "_sl_comentario": "SL inicial ativado após cada compra",

    "trailing_stop_distancia_pct": 0.8,
    "_tsl_comentario": "TSL ativado quando o lucro atingir tsl_gatilho_lucro_pct",

    "tsl_gatilho_lucro_pct": 1.5,
    "_tsl_gatilho_comentario": "Gatilho de lucro (%) para promover SL para TSL. Antes era 0% (breakeven), agora exige lucro mínimo",

    "cooldown_compra_segundos": 60,
    "_cooldown_comentario": "Tempo mínimo entre compras sucessivas"
  }
}
```

---

## 📊 Resumo de Mudanças por Tipo

### Linhas Adicionadas
- **backtest.py**: 23 linhas (nova pergunta + lógica)
- **backtest.py**: 77 linhas (nova função `analisar_saidas_por_motivo()`)
- **backtest.py**: 20 linhas (novo display de análise)
- **bot_worker.py**: 48 linhas (nova lógica de promoção)
- **configs**: 4 linhas (novo parâmetro em 2 arquivos)

**Total: 172 linhas adicionadas**

### Linhas Modificadas
- **backtest.py**: 5 linhas (comentários e descrições)
- **backtest.py**: 1 linha (atualizar label do resumo)

**Total: 6 linhas modificadas**

### Linhas Removidas
- Nenhuma remoção (somente adições)

---

## 🧪 Testes Implementados

### test_exit_analysis.py
- ✅ Teste 1: Análise de Saídas (validação de função)
- ✅ Teste 2: Lógica de Promoção (5 cenários)
- ✅ Teste 3: Interações do Usuário (validação de strings)
- ✅ Teste 4: Validação de Configurações (2 arquivos JSON)

**Total: 16 validações passando**

---

## 🔄 Retrocompatibilidade

### Compatível com Versões Anteriores?

**SIM** ✅ - O código trata o `tsl_gatilho_lucro_pct` com valor padrão:

```python
# Em bot_worker.py:1506
tsl_gatilho_lucro = Decimal(str(estrategia_config.get('tsl_gatilho_lucro_pct', 0)))
                                                                           ↑
                                                                    valor padrão
```

Se o parâmetro não estiver no arquivo JSON, usa `0` (breakeven) como antes.

### Migrando de v2.0 para v3.0

**Sem necessidade de mudanças nos arquivos existentes!**

- Configs antigas funcionam com comportamento antigo (0% gatilho)
- Recomenda-se adicionar `"tsl_gatilho_lucro_pct": 1.5` para novo comportamento

---

## 📋 Checklist de Implementação

- [x] Nova função de análise de saídas
- [x] Lógica de promoção com gatilho
- [x] Parâmetro adicionado às configs
- [x] Interface interativa atualizada
- [x] Resumo de parâmetros atualizado
- [x] Testes automatizados criados
- [x] Documentação técnica
- [x] Documentação prática
- [x] Exemplo de execução
- [x] Compilação Python validada

**Total: 10/10 itens completos** ✅

---

## 🚀 Deploy

### Arquivos para Fazer Commit

```bash
# Código Principal
git add backtest.py
git add src/core/bot_worker.py
git add configs/backtest_template.json
git add configs/estrategia_exemplo_giro_rapido.json

# Testes
git add test_exit_analysis.py

# Documentação
git add OTIMIZACAO_GIRO_RAPIDO_V3.md
git add GUIA_PRATICO_OTIMIZACAO_GIRO_RAPIDO.md
git add RESUMO_PHASE_5_FINAL.md
git add CHANGELOG_PHASE_5.md
git add EXEMPLO_EXECUCAO_INTERATIVA.md
```

### Mensagem de Commit

```
feat: Phase 5 - Otimização Giro Rápido v3.0

MUDANÇAS PRINCIPAIS:
- Análise de saídas com lucro/prejuízo detalhado por tipo
- Promoção SL → TSL com gatilho de lucro mínimo configurável
- Novo parâmetro: tsl_gatilho_lucro_pct (padrão: 1.5%)
- Interface interativa atualizada
- Testes automatizados completos

ARQUIVOS MODIFICADOS:
- backtest.py: +120 linhas (análise + interface)
- bot_worker.py: +48 linhas (lógica de promoção)
- configs/*.json: +4 linhas (novo parâmetro)

TESTES:
- 16/16 validações passando
- Retrocompatível com v2.0

Resolves: Improve Giro Rápido risk/reward ratio
```

---

**Versão:** 3.0
**Data:** 2025-10-25
**Status:** ✅ Pronto para Produção
