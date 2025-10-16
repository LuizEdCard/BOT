# Implementação: Estratégia de Vendas com Zonas de Segurança e Recompra Pós-Reversão

## Resumo Executivo

Foi implementado com sucesso um sistema avançado de vendas progressivas com zonas de segurança e recompra automática pós-reversão no bot de trading ADA/USDT.

**Status**: ✅ Implementação completa e testada
**Data**: 13/10/2025
**Testes**: 4/4 passaram com sucesso

---

## 🎯 Funcionalidades Implementadas

### 1. High-Water Mark de Lucro

O bot agora rastreia continuamente o **pico de lucro percentual** durante uma escalada de preço:

```python
self.high_water_mark_profit: Decimal = Decimal('0')  # Maior lucro % na escalada atual
```

- Atualizado automaticamente sempre que o lucro atual supera o recorde anterior
- Resetado a zero quando uma meta fixa (6%, 11%, 18%) é atingida
- Usado como referência para detectar reversões de mercado

### 2. Zonas de Segurança Configuráveis

5 zonas de segurança foram configuradas em `estrategia.json`:

| Zona | Gatilho Venda | % Venda | Gatilho Recompra | Descrição |
|------|---------------|---------|------------------|-----------|
| Pre-Meta1-A | 4.5% | 10% | -2.0% | Antes da meta 6% |
| Pre-Meta1-B | 5.5% | 10% | -2.0% | Antes da meta 6% |
| Pre-Meta2-A | 8.5% | 15% | -2.5% | Antes da meta 11% |
| Pre-Meta2-B | 10.0% | 15% | -2.5% | Antes da meta 11% |
| Pre-Meta3 | 15.0% | 20% | -3.0% | Antes da meta 18% |

**Lógica de Ativação:**
1. High-water mark deve ultrapassar o gatilho da zona
2. Lucro atual deve cair ao menos **0.3%** desde o pico (detecta reversão)
3. Zona não pode ter sido acionada anteriormente na mesma escalada

### 3. Sistema de Recompra Inteligente

Quando uma zona de segurança é ativada:

**Na Venda:**
- Capital obtido (USDT) é **reservado** para recompra futura
- Zona é marcada como "acionada" (não repete na mesma escalada)
- High-water mark e gatilho de recompra são salvos

**Na Recompra:**
- Monitora continuamente o lucro atual
- Quando lucro cai abaixo do gatilho: `lucro_atual <= (high_water_mark - gatilho_recompra_drop_pct)`
- Executa ordem de compra usando o capital reservado
- Acumula mais ADA a preço médio potencialmente melhor

### 4. Prioridades de Execução

O sistema opera com ordem de prioridade clara:

```
PRIORIDADE 1: Metas Fixas (18%, 11%, 6%)
   ↓ Se atingida: VENDA + RESET completo do estado

PRIORIDADE 2: Zonas de Segurança (vendas parciais)
   ↓ Se ativada: VENDA PARCIAL + guardar capital

PRIORIDADE 3: Sistema Adaptativo (3-6%)
   ↓ Venda pequena (5%) se ordem >= $5.00
```

---

## 📂 Arquivos Modificados

### 1. `bot_trading.py`

**Novos atributos no `__init__`:**
```python
self.high_water_mark_profit: Decimal = Decimal('0')
self.zonas_de_seguranca_acionadas: set = set()
self.capital_para_recompra: Dict[str, Dict] = {}
```

**Novos métodos:**
- `verificar_recompra_de_seguranca(preco_atual)` - Verifica gatilhos de recompra (bot_trading.py:771)
- `_executar_recompra(nome_zona, quantidade_ada, ...)` - Executa ordem de recompra (bot_trading.py:845)

**Métodos refatorados:**
- `encontrar_meta_ativa(...)` - Agora inclui lógica de zonas de segurança (bot_trading.py:501)
- `executar_venda(...)` - Guarda capital para recompra em vendas de segurança (bot_trading.py:630)
- `loop_principal()` - Chama `verificar_recompra_de_seguranca` a cada ciclo (bot_trading.py:1233)

### 2. `config/estrategia.json`

Adicionada nova seção `vendas_de_seguranca`:

```json
"vendas_de_seguranca": [
  {
    "nome": "Seguranca_Pre-Meta1-A",
    "gatilho_venda_lucro_pct": 4.5,
    "percentual_venda_posicao": 10,
    "gatilho_recompra_drop_pct": 2.0,
    "descricao": "Venda de segurança A antes da meta 1 (6%)"
  },
  ...
]
```

### 3. `config/settings.py`

Adicionado carregamento da nova configuração:

```python
self.VENDAS_DE_SEGURANCA = self.estrategia.get('vendas_de_seguranca', [])
```

### 4. `testar_zonas_seguranca.py` (NOVO)

Script de teste com 4 cenários de validação:
- ✅ Carregamento de configuração
- ✅ Ativação de zona de segurança
- ✅ Recompra pós-reversão
- ✅ Reset de estado ao atingir meta fixa

---

## 🔄 Fluxo de Execução

### Cenário Exemplo: Escalada de Lucro

```
Passo 1: Compras executadas → Preço médio: $0.80
         Mercado sobe → Lucro: 4.0%
         High-water mark: 4.0%

Passo 2: Mercado continua subindo → Lucro: 5.0%
         High-water mark: 5.0% ✅

Passo 3: REVERSÃO! Preço cai levemente → Lucro: 4.6%
         High-water mark: 5.0% (mantém pico)

         Zona "Pre-Meta1-A" detecta:
         - High-water mark (5.0%) > Gatilho (4.5%) ✅
         - Queda desde pico: 5.0% - 4.6% = 0.4% ✅
         - Queda >= 0.3% (threshold) ✅

         🛡️ VENDA DE SEGURANÇA EXECUTADA!
         - Vende: 10% da posição
         - Obtém: $8.37 USDT
         - Guarda para recompra se cair para 3.0%

Passo 4: Reversão continua → Lucro: 3.0%

         🔄 RECOMPRA ATIVADA!
         - Compra: ~10.2 ADA por $0.824
         - Usa: $8.46 USDT reservados
         - Resultado: Acumulou ~0.2 ADA extras!

Passo 5: Mercado se recupera → Lucro: 6.0%

         🎯 META 1 ATINGIDA!
         - Vende: 30% da posição
         - RESET: high_water_mark → 0
         - LIMPA: zonas acionadas
         - LIMPA: capital de recompra
```

---

## 💡 Vantagens da Estratégia

### 1. Proteção contra Reversões
- Vende parcialmente quando detecta início de queda
- Preserva lucros antes de reversão completa
- Mantém exposição caso recupere

### 2. Acumulação Inteligente
- Capital da venda de segurança é **sempre** reinvestido
- Recompra em preço potencialmente melhor
- Aumenta quantidade de ADA no longo prazo

### 3. Gestão de Risco Progressiva
- Vendas maiores (20%) apenas em picos altos (15%+)
- Vendas menores (10%) em lucros moderados (4-5%)
- Metas fixas continuam sendo priori dade máxima

### 4. Estado Independente por Escalada
- Cada ciclo de lucro é tratado separadamente
- Reset automático ao atingir meta fixa
- Zonas podem ser reutilizadas infinitamente

---

## 🧪 Testes e Validação

Todos os testes passaram com sucesso:

```bash
$ python3 testar_zonas_seguranca.py

🎉 TODOS OS TESTES PASSARAM! Sistema pronto para uso.

📊 Total: 4/4 testes passaram
```

### Teste 1: Carregamento
- ✅ 5 zonas carregadas corretamente
- ✅ Todos os parâmetros válidos

### Teste 2: Ativação
- ✅ Zona ativada corretamente (5% → 4.6%)
- ✅ Valores de venda calculados corretamente
- ✅ Capital reservado para recompra

### Teste 3: Recompra
- ✅ Gatilho calculado: 3.0% (5.0% - 2.0%)
- ✅ Recompra ativada quando lucro ≤ 3.0%
- ✅ Quantidade e preço calculados corretamente

### Teste 4: Reset
- ✅ Estado limpo ao atingir meta fixa
- ✅ High-water mark resetado
- ✅ Capital de recompra removido

---

## 📊 Banco de Dados

### Registros de Vendas de Segurança

```sql
tipo = 'VENDA'
meta = 'seguranca_Seguranca_Pre-Meta1-A'
observacao = "Venda de Segurança 'Seguranca_Pre-Meta1-A' - Lucro 4.60% (capital reservado para recompra)"
```

### Registros de Recompras

```sql
tipo = 'COMPRA'
meta = 'recompra_seguranca_Seguranca_Pre-Meta1-A'
observacao = "Recompra de Segurança zona 'Seguranca_Pre-Meta1-A' - Diferença -1.44% vs venda original"
```

---

## ⚙️ Configuração Personalizada

Para ajustar a estratégia, edite `config/estrategia.json`:

```json
{
  "nome": "MinhaZona",
  "gatilho_venda_lucro_pct": 7.0,        // Aciona quando high-water > 7%
  "percentual_venda_posicao": 12,        // Vende 12% da posição
  "gatilho_recompra_drop_pct": 1.5,      // Recompra quando cair 1.5% do pico
  "descricao": "Minha zona personalizada"
}
```

### Parâmetros Ajustáveis

| Parâmetro | Descrição | Recomendação |
|-----------|-----------|--------------|
| `gatilho_venda_lucro_pct` | % de lucro para ativar zona | Entre metas fixas |
| `percentual_venda_posicao` | % da posição a vender | 10-20% |
| `gatilho_recompra_drop_pct` | Queda % desde pico para recomprar | 1.5-3.0% |

---

## 🚀 Próximos Passos

### Uso Imediato
O sistema está **pronto para produção**. Para ativar:

```bash
python3 bot_trading.py
```

### Monitoramento Sugerido

Observe nos logs:
- `🛡️ ZONA DE SEGURANÇA 'XXX' ATIVADA!` - Venda de segurança executada
- `🔄 GATILHO DE RECOMPRA ATIVADO` - Recompra sendo executada
- `📊 High-Water Mark atualizado` - Novo pico de lucro registrado

### Ajustes Finos (Opcionais)

1. **Threshold de reversão**: Atualmente 0.3% - ajustar em `bot_trading.py:570`
2. **Adicionar mais zonas**: Editar `estrategia.json` para zonas extras
3. **Logging avançado**: Já implementado - use logs para análise

---

## 📚 Documentação Técnica

### Estrutura de Dados

**capital_para_recompra:**
```python
{
  'nome_zona': {
    'capital_usdt': Decimal,        # Capital em USDT da venda
    'high_water_mark': Decimal,     # Pico de lucro % registrado
    'gatilho_recompra_pct': Decimal,# Queda % para ativar recompra
    'quantidade_vendida': Decimal,  # ADA vendidos
    'preco_venda': Decimal          # Preço da venda original
  }
}
```

### Métodos Principais

| Método | Arquivo | Linha | Descrição |
|--------|---------|-------|-----------|
| `encontrar_meta_ativa` | bot_trading.py | 501 | Verifica metas e zonas |
| `executar_venda` | bot_trading.py | 630 | Executa venda + reserva capital |
| `verificar_recompra_de_seguranca` | bot_trading.py | 771 | Monitora gatilhos de recompra |
| `_executar_recompra` | bot_trading.py | 845 | Executa ordem de recompra |

---

## ✅ Checklist de Implementação

- [x] Adicionar atributos de estado no `__init__`
- [x] Implementar rastreamento de High-Water Mark
- [x] Refatorar `encontrar_meta_ativa` para zonas
- [x] Modificar `executar_venda` para guardar capital
- [x] Implementar `verificar_recompra_de_seguranca`
- [x] Implementar `_executar_recompra`
- [x] Integrar verificação no loop principal
- [x] Adicionar configuração em `estrategia.json`
- [x] Atualizar `settings.py` para carregar config
- [x] Criar script de testes
- [x] Executar e validar testes
- [x] Documentar implementação

---

## 🎓 Conceitos Aplicados

### High-Water Mark
Técnica comum em fundos hedge para rastrear máxima performance e cobrar taxas apenas sobre novos lucros. Aqui, usado para detectar reversões.

### Trailing Stop Progressivo
Similar a trailing stop-loss, mas com múltiplos níveis e recompra automática.

### Dollar Cost Averaging (DCA) Reverso
Recompra em queda maximiza acumulação - o inverso do DCA tradicional.

---

## 📞 Suporte

Para dúvidas ou ajustes:
1. Consulte os logs do bot (`logs/`)
2. Execute testes: `python3 testar_zonas_seguranca.py`
3. Revise este documento

---

**Desenvolvido com:** Python 3.10+ | Decimal Precision | Binance API
**Compatível com:** Bot Trading ADA/USDT v2.0+
**Licença:** Uso interno do projeto

---

*Documento gerado em 13/10/2025 - Implementação completa e testada*
