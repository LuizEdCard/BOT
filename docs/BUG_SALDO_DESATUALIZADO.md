# BUG: Saldo Insuficiente Após Vendas - Análise e Solução

## Problema
Em backtests longos, após várias operações (compras e vendas), o bot começa a relatar "Saldo insuficiente" mesmo tendo capital disponível das vendas anteriores.

```
ERROR | Saldo insuficiente na carteira 'giro_rapido' para executar a ordem de compra
```

## Causa Raiz

### O Problema de Desincronização de Saldos

Em `src/core/gestao_capital.py` linhas 202-207:

```python
if carteira == 'giro_rapido':
    # 20% do capital total
    return self.saldo_usdt * (self.alocacao_giro_rapido_pct / Decimal('100'))
elif carteira == 'acumulacao':
    # 80% do capital total (100% - 20%)
    return self.saldo_usdt * ((Decimal('100') - self.alocacao_giro_rapido_pct) / Decimal('100'))
```

**O problema:**
1. `GestaoCapital.saldo_usdt` é um atributo interno que contém o saldo "base" (inicial)
2. A `SimulatedExchangeAPI` mantém seu próprio saldo separado em `saldos_por_carteira`
3. Quando uma venda executa, **APENAS** o saldo da API é atualizado
4. O `GestaoCapital.saldo_usdt` **NÃO é atualizado**!

### Fluxo de Desincronização

**Ciclo 1:** Compra executada
```
API: compra por $160 → saldo API = $840
GestaoCapital: não é atualizado → saldo_usdt = $1000
calcular_capital_disponivel() = $1000 * 0.20 = $200 ✅ (correto por acaso)
```

**Ciclo 2:** Venda executada
```
API: venda por $170 → saldo API = $1010
bot_worker.py linha 812: chama set_saldo_usdt_simulado($1010, 'giro_rapido')
```

Aqui está o problema! Vamos ver o que `set_saldo_usdt_simulado()` faz:

## Investigação do `set_saldo_usdt_simulado()`

Em `src/core/gestao_capital.py`, procuramos:

```python
def set_saldo_usdt_simulado(self, novo_saldo_usdt: Decimal, carteira: str):
    """Atualiza o saldo USDT em modo simulação"""
    self.saldo_usdt = novo_saldo_usdt
```

**O REAL PROBLEMA:** Quando você chama `set_saldo_usdt_simulado()` com o saldo de UMA CARTEIRA,
você está SOBRESCREVENDO o saldo TOTAL!

### Exemplo de Falha

1. **Inicialização:**
   - API giro_rapido: $200
   - API acumulacao: $800
   - GestaoCapital.saldo_usdt: $1000

2. **Após compra em giro_rapido ($160):**
   - API giro_rapido: $40
   - API acumulacao: $800
   - GestaoCapital.saldo_usdt: $1000

3. **Após venda em giro_rapido (+$170):**
   - API giro_rapido: $210
   - API acumulacao: $800
   - bot_worker chama: `set_saldo_usdt_simulado($210, 'giro_rapido')`
   - **GestaoCapital.saldo_usdt agora é $210!** ❌ ERRADO!

4. **Próxima verificação de capital:**
   ```python
   calcular_capital_disponivel('giro_rapido')
   = $210 * 0.20  # Deveria ser $210 (saldo real)
   = $42          # ❌ ERRADO! Muito menor que o real
   ```

## Solução

### Opção 1: Não sobrescrever o saldo_usdt total (RECOMENDADA)

Modificar `set_saldo_usdt_simulado()` para manter o saldo total e apenas rastrear por carteira:

```python
def set_saldo_usdt_simulado(self, novo_saldo_usdt: Decimal, carteira: str):
    """Atualiza o saldo USDT de uma carteira específica em modo simulação

    NÃO atualiza o saldo total, apenas sincroniza com a API
    """
    # Obter saldos atuais da API para ambas as carteiras
    saldo_giro = Decimal(str(self.exchange_api.saldos_por_carteira['giro_rapido']['saldo_usdt']))
    saldo_acum = Decimal(str(self.exchange_api.saldos_por_carteira['acumulacao']['saldo_usdt']))

    # O saldo total é a soma de ambas as carteiras
    self.saldo_usdt = saldo_giro + saldo_acum

    # Armazenar saldos por carteira para referência (opcional)
    if not hasattr(self, '_saldos_por_carteira_local'):
        self._saldos_por_carteira_local = {}
    self._saldos_por_carteira_local[carteira] = novo_saldo_usdt
```

### Opção 2: Usar saldo da API diretamente

Modificar `calcular_capital_disponivel()` para NÃO recalcular divisão:

```python
def calcular_capital_disponivel(self, carteira: str = 'acumulacao') -> Decimal:
    """Calcula capital disponível para trading por carteira"""

    if self.modo_simulacao:
        # Em simulação, usar DIRETO o saldo da API
        saldo_carteira = Decimal(str(
            self.exchange_api.saldos_por_carteira[carteira]['saldo_usdt']
        ))
        reserva = self.calcular_reserva_obrigatoria()
        return max(saldo_carteira - reserva, Decimal('0'))
    else:
        # Em modo real, usar lógica atual...
```

## Recomendação

Use a **Opção 1** porque:
1. Mantém consistência com o design atual
2. Não modifica a lógica de modo real
3. Apenas fixa o sincronismo de saldos
4. Menos risco de efeitos colaterais

## Teste de Verificação

Após aplicar a solução, adicione este debug log:

```python
self.logger.info(f"[DEBUG SALDO] carteira={carteira}, "
                 f"saldo_usdt_local={self.saldo_usdt}, "
                 f"saldo_api_giro={self.exchange_api.saldos_por_carteira['giro_rapido']['saldo_usdt']}, "
                 f"saldo_api_acum={self.exchange_api.saldos_por_carteira['acumulacao']['saldo_usdt']}, "
                 f"capital_disponível={capital_disponível}")
```

Isso permitirá você verificar quando o saldo local diverge do saldo da API.
