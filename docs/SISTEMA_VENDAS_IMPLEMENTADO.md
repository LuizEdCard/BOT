# ✅ Sistema de Vendas Automáticas Implementado

## 🎯 Regras de Ouro

### 1. **NUNCA vende com prejuízo**
```
Se lucro <= 0% → NÃO VENDE (aguarda recuperação)
```

### 2. **Só vende quando atingir metas de lucro**
```
Meta 1: +6% → Vende 10% da posição
Meta 2: +12% → Vende 15% da posição
Meta 3: +20% → Vende 20% da posição
```

### 3. **Acumula em quedas, realiza em altas**
```
Queda: Compra nos degraus (acumula posição)
Alta: Vende nas metas (realiza lucro progressivo)
```

---

## 📊 Como Funciona

### Rastreamento de Preço Médio

O bot agora rastreia automaticamente:
- **Preço médio de compra**: Média ponderada de todas as compras
- **Quantidade total comprada**: Total de ADA acumulado
- **Valor total investido**: Total em USDT gasto

**Fórmula do preço médio:**
```
Preço médio = Valor total investido / Quantidade total comprada
```

**Exemplo:**
```
Compra 1: 10 ADA × $0.65 = $6.50
Compra 2: 8 ADA × $0.67 = $5.36
────────────────────────────────────
Total: 18 ADA por $11.86
Preço médio: $11.86 / 18 = $0.6589
```

### Cálculo de Lucro

**Fórmula:**
```
Lucro % = ((Preço atual - Preço médio) / Preço médio) × 100
```

**Exemplo atual:**
```
Preço médio: $0.678967
Preço atual: $0.657300
Lucro: ((0.657300 - 0.678967) / 0.678967) × 100 = -3.19%
```
❌ Lucro negativo → Bot **NÃO VENDE**

---

## 🎯 Metas de Venda

| Meta | Lucro Necessário | Preço Alvo* | Ação | Quantidade |
|------|------------------|-------------|------|------------|
| **Meta 1** | +6% | $0.719705 | Vende 10% | ~33.5 ADA |
| **Meta 2** | +12% | $0.760443 | Vende 15% | ~50.3 ADA |
| **Meta 3** | +20% | $0.814760 | Vende 20% | ~67.1 ADA |

*Baseado no preço médio atual de $0.678967

### Proteções de Segurança

1. **Dupla verificação de lucro**
   - Calcula lucro antes de buscar meta
   - Recalcula lucro antes de executar venda

2. **Validações de quantidade**
   - Mínimo: 1.0 ADA
   - Step size: 0.1 ADA
   - Valor mínimo da ordem: $5.00 USDT

3. **Atualização automática de posição**
   - Após venda, ajusta quantidade total
   - Ajusta valor investido proporcional
   - Mantém preço médio correto

---

## 💻 Implementação Técnica

### 1. Rastreamento de Posição

```python
# Variáveis de estado (bot_trading.py)
self.preco_medio_compra: Optional[Decimal] = None
self.quantidade_total_comprada: Decimal = Decimal('0')
self.valor_total_investido: Decimal = Decimal('0')
```

### 2. Atualização Após Compra

```python
def atualizar_preco_medio_compra(self, quantidade: Decimal, preco: Decimal):
    """Atualiza preço médio após nova compra"""
    valor_compra = quantidade * preco

    self.valor_total_investido += valor_compra
    self.quantidade_total_comprada += quantidade

    if self.quantidade_total_comprada > 0:
        self.preco_medio_compra = self.valor_total_investido / self.quantidade_total_comprada
```

### 3. Verificação de Lucro

```python
def calcular_lucro_atual(self, preco_atual: Decimal) -> Optional[Decimal]:
    """Calcula lucro % baseado no preço médio"""
    if self.preco_medio_compra is None or self.preco_medio_compra == 0:
        return None

    lucro_pct = ((preco_atual - self.preco_medio_compra) / self.preco_medio_compra) * Decimal('100')
    return lucro_pct
```

### 4. Busca de Meta Ativa

```python
def encontrar_meta_ativa(self, lucro_pct: Decimal) -> Optional[Dict]:
    """
    Encontra meta de venda correspondente

    REGRA: Só vende se houver LUCRO (nunca com prejuízo)
    """
    if lucro_pct <= 0:
        return None  # Sem lucro, não vende

    for meta in settings.METAS_VENDA:
        if lucro_pct >= Decimal(str(meta['lucro_percentual'])):
            return meta
    return None
```

### 5. Execução de Venda Protegida

```python
def executar_venda(self, meta: Dict, preco_atual: Decimal, saldo_ada: Decimal):
    """
    Executa venda na meta

    PROTEÇÃO: Só executa se houver lucro confirmado
    """
    # Verificar lucro novamente antes de vender
    lucro_pct = self.calcular_lucro_atual(preco_atual)

    if lucro_pct is None or lucro_pct <= 0:
        logger.warning(f"🛡️ VENDA BLOQUEADA: Sem lucro")
        return False

    # ... executa venda ...

    # Ajustar posição após venda
    self.quantidade_total_comprada -= quantidade_venda
    self.valor_total_investido -= valor_medio_compra
```

### 6. Loop Principal

```python
# LÓGICA DE VENDA (só vende com lucro!)
if self.preco_medio_compra and saldos['ada'] >= Decimal('1'):
    # Calcular lucro atual
    lucro_atual = self.calcular_lucro_atual(preco_atual)

    if lucro_atual and lucro_atual > 0:
        # Buscar meta de venda ativa
        meta = self.encontrar_meta_ativa(lucro_atual)

        if meta:
            logger.info(f"🎯 Meta {meta['meta']} atingida! Lucro: +{lucro_atual:.2f}%")

            # Tentar executar venda
            if self.executar_venda(meta, preco_atual, saldos['ada']):
                logger.info("✅ Venda executada com lucro!")
    else:
        # Log informativo a cada 20 ciclos quando não há lucro
        if contador_ciclos % 20 == 0:
            logger.info(f"🛡️ Aguardando lucro (atual: {lucro_atual:+.2f}%)")
```

---

## 📈 Exemplo de Operação Completa

### Cenário: Mercado em Recuperação

**Situação inicial:**
- Preço médio: $0.678967
- Quantidade: 335.46 ADA
- Investido: $227.76 USDT
- Lucro atual: -3.19% ❌

**O preço sobe para $0.72:**
1. **Cálculo de lucro:**
   ```
   Lucro = ((0.72 - 0.678967) / 0.678967) × 100 = +6.05%
   ```

2. **Meta 1 ativada (+6%):**
   ```
   🎯 Meta 1 atingida! Lucro: +6.05%
   ```

3. **Venda executada:**
   ```
   Quantidade: 33.5 ADA (10% de 335.46)
   Preço: $0.72
   Total recebido: $24.12 USDT
   Lucro da venda: $1.37
   ```

4. **Posição atualizada:**
   ```
   Quantidade restante: 301.96 ADA
   Preço médio: $0.678967 (mantém)
   Valor investido ajustado: $205.01
   ```

**O preço continua subindo para $0.76:**
5. **Cálculo de lucro:**
   ```
   Lucro = ((0.76 - 0.678967) / 0.678967) × 100 = +11.94%
   ```
   ⏳ Aguardando +12% para Meta 2...

**O preço atinge $0.761:**
6. **Meta 2 ativada (+12%):**
   ```
   🎯 Meta 2 atingida! Lucro: +12.09%
   ```

7. **Segunda venda:**
   ```
   Quantidade: 45.3 ADA (15% de 301.96)
   Preço: $0.761
   Total recebido: $34.47 USDT
   Lucro da venda: $3.72
   ```

**Resultado final parcial:**
- **Vendido**: 78.8 ADA (23.5% da posição original)
- **Lucro realizado**: $5.09 USDT
- **ADA restante**: 256.66 ADA
- **Aguardando**: Meta 3 (+20%) em $0.815

---

## 🛡️ Proteções Implementadas

### ✅ Nunca vende com prejuízo
```python
if lucro_pct <= 0:
    return None  # Bloqueia venda
```

### ✅ Valida lucro duas vezes
```python
# Antes de buscar meta
lucro_atual = self.calcular_lucro_atual(preco_atual)

# Antes de executar venda
lucro_pct = self.calcular_lucro_atual(preco_atual)
if lucro_pct is None or lucro_pct <= 0:
    return False  # Bloqueia
```

### ✅ Quantidade mínima (1 ADA)
```python
if quantidade_venda < Decimal('1'):
    logger.warning("⚠️ Quantidade abaixo do mínimo")
    return False
```

### ✅ Valor mínimo da ordem ($5.00)
```python
if valor_ordem < settings.VALOR_MINIMO_ORDEM:
    logger.warning("⚠️ Valor abaixo do mínimo")
    return False
```

### ✅ Atualização correta de posição
```python
# Reduz quantidade e valor proporcional
self.quantidade_total_comprada -= quantidade_venda
self.valor_total_investido -= (quantidade_venda * self.preco_medio_compra)
```

---

## 📊 Monitoramento

### Logs de Compra
```
🟢 COMPRA | ADA/USDT | Qtd: 8.0000 | Preço: $0.650500 | Degrau: 1
📊 Preço médio atualizado: $0.678967 (335.5 ADA)
```

### Logs de Venda
```
🎯 Meta 1 atingida! Lucro: +6.05%
🔴 VENDA | ADA/USDT | Qtd: 33.5000 | Preço: $0.720000 | Meta: 1 | Lucro: $1.37
📊 Posição atualizada: 302.0 ADA (preço médio: $0.678967)
```

### Logs de Aguardo
```
🛡️ Aguardando lucro (atual: -3.19% | preço médio: $0.678967)
```

---

## 🚀 Status Atual

**✅ Sistema de vendas ATIVO**
- Rastreamento de preço médio: ✅ Implementado
- Cálculo de lucro: ✅ Implementado
- Detecção de metas: ✅ Implementado
- Proteção contra prejuízo: ✅ Implementado
- Venda automática: ✅ Implementado

**💰 Situação da Carteira**
- Preço médio de compra: $0.678967
- Quantidade total: 335.46 ADA
- Valor atual: ~$220.44 USDT (ao preço de $0.657)
- Lucro não realizado: -3.19%
- Saldo USDT: $0.26 (esgotado)

**🎯 Próxima Venda**
- Preço precisa subir para: **$0.719705** (+6%)
- Quantidade a vender: **33.5 ADA** (10%)
- Lucro estimado: **$1.37 USDT**

---

**Desenvolvido em:** 2025-10-11
**Status:** ✅ Em produção - Aguardando recuperação do mercado para realizar lucros
