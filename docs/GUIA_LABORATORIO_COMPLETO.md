# 🔬 Guia Completo do Laboratório de Otimização Interativo

## Visão Geral

O `backtest.py` é agora um **Laboratório de Otimização Completo** que permite personalizar **TODOS** os parâmetros principais das estratégias de trading de forma interativa, sem editar arquivos JSON manualmente.

---

## 🎯 Fluxo Completo de Uso

### Passo 1: Seleção de Arquivos Base
```
1. Arquivo de configuração (.json)
2. Arquivo de dados históricos (.csv)
3. Timeframe base do CSV
4. Saldo inicial (USDT)
5. Taxa da exchange (%)
6. Estratégias para testar
```

### Passo 2: Personalização de Parâmetros

Após a seleção básica, o laboratório entra no **modo de otimização** onde você pode personalizar cada parâmetro.

---

## 📊 Parâmetros da Estratégia DCA (Acumulação)

### 1. **Filtro RSI**
- **Pergunta**: "Ativar filtro RSI do DCA?"
- **Tipo**: Sim/Não
- **Padrão**: Valor do config
- **Descrição**: Define se o RSI será usado como filtro de entrada

#### Se RSI ativado:

**1.1. Limite do RSI**
- **Pergunta**: "Qual o limite do RSI para compra?"
- **Tipo**: Número
- **Padrão**: 35
- **Dica**: Valores menores (20-30) = mais conservador; Valores maiores (35-45) = mais agressivo

**1.2. Timeframe do RSI**
- **Pergunta**: "Qual o timeframe do RSI?"
- **Opções**: 1m, 5m, 15m, 30m, 1h, 4h, 1d
- **Padrão**: 1h
- **Dica**: Timeframes maiores dão sinais mais confiáveis

### 2. **Timeframe da SMA de Referência**
- **Pergunta**: "Qual o timeframe da SMA de referência?"
- **Opções**: 1m, 5m, 15m, 30m, 1h, 4h, 1d
- **Padrão**: 4h
- **Descrição**: Define qual timeframe usar para calcular a SMA de 28 dias
- **Dica**: 
  - 1h ou 4h = Ideal para análise de médio prazo
  - 1d = Análise de longo prazo, menos sensível

### 3. **Percentual Mínimo de Melhora do PM**
- **Pergunta**: "Qual o % mínimo de melhora do Preço Médio para comprar?"
- **Tipo**: Número (%)
- **Padrão**: 1.25%
- **Descrição**: Evita compras que pioram pouco o PM
- **Dica**: 
  - 0.5-1.0% = Mais agressivo
  - 1.5-2.5% = Mais conservador

### 4. **Trailing Stop Loss**
- **Pergunta**: "Qual a distância do Trailing Stop Loss (%)?"
- **Tipo**: Número (%)
- **Padrão**: 2.0%
- **Descrição**: Distância percentual do pico para ativar venda
- **Dica**:
  - 1.0-1.5% = TSL apertado, protege lucros rapidamente
  - 2.5-4.0% = TSL largo, dá espaço para volatilidade

### 5. **Stop Loss Catastrófico**
- **Pergunta**: "Qual o Stop Loss catastrófico (%)?"
- **Tipo**: Número (%)
- **Padrão**: 10.0%
- **Descrição**: Limite máximo de perda antes de venda forçada
- **Dica**: 
  - 5-8% = Proteção apertada
  - 10-15% = Mais tolerante a quedas

---

## 💨 Parâmetros da Estratégia Giro Rápido (Swing Trade)

### 1. **Timeframe Principal**
- **Pergunta**: "Qual o timeframe principal do Giro Rápido?"
- **Opções**: 1m, 5m, 15m, 30m, 1h, 4h, 1d
- **Padrão**: 15m
- **Descrição**: Timeframe usado para identificar oportunidades
- **Dica**:
  - 5m ou 15m = Day trading, alta frequência
  - 1h ou 4h = Swing trading, posições mais longas

### 2. **Gatilho de Compra**
- **Pergunta**: "Qual o gatilho de compra (% de queda)?"
- **Tipo**: Número (%)
- **Padrão**: 2.0%
- **Descrição**: Queda percentual necessária para disparar compra
- **Dica**:
  - 1.0-1.5% = Mais oportunidades, maior risco
  - 2.5-4.0% = Menos oportunidades, quedas maiores

### 3. **Filtro RSI de Entrada**
- **Pergunta**: "Ativar filtro RSI de entrada?"
- **Tipo**: Sim/Não
- **Padrão**: Sim
- **Descrição**: Confirma entrada com RSI em zona de sobrevenda

#### Se RSI ativado:

**3.1. Limite do RSI**
- **Pergunta**: "Qual o limite do RSI de entrada?"
- **Tipo**: Número
- **Padrão**: 30
- **Dica**: 25-30 = conservador; 35-40 = mais trades

**3.2. Timeframe do RSI**
- **Pergunta**: "Qual o timeframe do RSI de entrada?"
- **Opções**: 1m, 5m, 15m, 30m, 1h, 4h, 1d
- **Padrão**: 15m
- **Dica**: Usar o mesmo timeframe da estratégia principal

### 4. **Stop Loss Inicial**
- **Pergunta**: "Qual o Stop Loss inicial (%)?"
- **Tipo**: Número (%)
- **Padrão**: 2.5%
- **Descrição**: Distância do preço de entrada para o stop inicial
- **Dica**:
  - 1.5-2.0% = Apertado, protege mais
  - 3.0-4.0% = Largo, tolera mais volatilidade

### 5. **Trailing Stop**
- **Pergunta**: "Qual a distância do Trailing Stop (%)?"
- **Tipo**: Número (%)
- **Padrão**: 0.8%
- **Descrição**: Distância do pico para o TSL
- **Dica**:
  - 0.5-0.8% = Agressivo, captura lucros rápido
  - 1.0-1.5% = Conservador, dá espaço ao movimento

### 6. **Alocação de Capital**
- **Pergunta**: "Qual o % de capital para Giro Rápido?"
- **Tipo**: Número (%)
- **Padrão**: 20%
- **Descrição**: Percentual do capital total dedicado ao swing trade
- **Dica**:
  - 10-15% = Conservador
  - 20-30% = Balanceado
  - 35-50% = Agressivo

---

## 📋 Resumo Final

Antes de executar, o laboratório mostra um **resumo completo** de todos os parâmetros que serão usados:

```
📋 RESUMO FINAL DA CONFIGURAÇÃO
================================================================================
   Arquivo de configuração: configs/lab_otimizacao.json
   Arquivo de dados: dados/historicos/ADAUSDT_1m_2024.csv
   Timeframe base do CSV: 1m
   Saldo inicial: $1000.00 USDT
   Taxa da exchange: 0.1%
   Estratégias selecionadas: ambas

   📊 Parâmetros Finais das Estratégias:

      📊 DCA (Acumulação):
         Filtro RSI: Ativo
         RSI Limite: 35
         RSI Timeframe: 1h
         SMA Timeframe: 4h
         Melhora PM Mínima: 1.25%
         Trailing Stop: 2.0%
         Stop Loss Catastrófico: 10.0%

      💨 Giro Rápido (Swing Trade):
         Timeframe Principal: 15m
         Gatilho de Compra: 2.0%
         Filtro RSI: Ativo
         RSI Limite: 30
         RSI Timeframe: 15m
         Stop Loss Inicial: 2.5%
         Trailing Stop: 0.8%
         Alocação de Capital: 20%

================================================================================
```

---

## 🎓 Exemplos de Configurações

### Exemplo 1: DCA Conservador + Giro Equilibrado

**DCA:**
- RSI: Ativo, Limite 35, Timeframe 1h
- SMA: 4h
- Melhora PM: 1.5%
- TSL: 2.5%
- SL Catastrófico: 10%

**Giro Rápido:**
- Timeframe: 1h
- Gatilho: 2.5%
- RSI: Ativo, Limite 30, Timeframe 1h
- SL Inicial: 3.0%
- TSL: 1.0%
- Alocação: 20%

**Perfil**: Acumulação sólida com swing trades moderados

---

### Exemplo 2: DCA Agressivo + Giro Day Trade

**DCA:**
- RSI: Ativo, Limite 40, Timeframe 15m
- SMA: 1h
- Melhora PM: 0.75%
- TSL: 1.5%
- SL Catastrófico: 8%

**Giro Rápido:**
- Timeframe: 5m
- Gatilho: 1.5%
- RSI: Ativo, Limite 35, Timeframe 5m
- SL Inicial: 2.0%
- TSL: 0.6%
- Alocação: 30%

**Perfil**: Alta frequência de operações, requer dados de alta resolução

---

### Exemplo 3: Apenas DCA Ultra Conservador

**DCA:**
- RSI: Ativo, Limite 30, Timeframe 4h
- SMA: 1d
- Melhora PM: 2.0%
- TSL: 3.0%
- SL Catastrófico: 15%

**Giro Rápido:** Desabilitado

**Perfil**: Acumulação de longo prazo com máxima segurança

---

### Exemplo 4: Apenas Giro Rápido Agressivo

**DCA:** Desabilitado

**Giro Rápido:**
- Timeframe: 15m
- Gatilho: 1.8%
- RSI: Inativo
- SL Inicial: 2.0%
- TSL: 0.7%
- Alocação: 50%

**Perfil**: Foco total em swing trades rápidos

---

## 💡 Dicas de Otimização

### Para Mercados Voláteis:
- ↑ Aumentar distância dos stops (TSL e SL)
- ↑ Aumentar gatilhos de compra
- ↓ Diminuir RSI limite (mais conservador)

### Para Mercados Laterais:
- ↓ Diminuir gatilhos de compra
- ↓ Diminuir distância dos stops
- ↑ Aumentar alocação de Giro Rápido

### Para Mercados em Alta:
- ↑ Aumentar RSI limite
- ↓ Diminuir melhora PM mínima
- ↓ Diminuir TSL para capturar lucros

### Para Mercados em Queda:
- ↓ Diminuir RSI limite
- ↑ Aumentar melhora PM mínima
- ↑ Usar SMA de timeframes maiores

---

## 🚀 Execução

```bash
# Iniciar o laboratório
python backtest.py

# O script irá guiá-lo através de todas as perguntas
# Use as setas para navegar, ENTER para confirmar
# Os valores padrão sempre vêm da configuração carregada
```

---

## ⚙️ Validação e Testes

Todos os valores inseridos são validados:
- ✅ Números devem ser válidos
- ✅ Percentuais devem ser >= 0
- ✅ Timeframes devem ser escolhidos da lista
- ✅ Valores padrão sempre disponíveis (pressione ENTER)

---

## 📊 Análise dos Resultados

Após a execução, compare:
1. **Lucro/Prejuízo da Estratégia** vs **Buy & Hold**
2. **Número de trades** executados
3. **Motivos de saída** (SL, TSL, Meta de Lucro)
4. **Volume operado**

Use estas informações para refinar os parâmetros na próxima simulação!

---

## 🔄 Iteração e Aprendizado

O laboratório incentiva um processo iterativo:

```
1. Executar com parâmetros padrão
2. Analisar resultados
3. Identificar pontos de melhoria
4. Ajustar parâmetros específicos
5. Comparar resultados
6. Repetir até encontrar configuração ótima
```

---

## 📝 Notas Importantes

- ⚠️ Todos os valores inseridos sobrescrevem a configuração **apenas em memória**
- ⚠️ O arquivo JSON original **nunca é modificado**
- ⚠️ Cada execução é independente
- ⚠️ Resultados de backtest **não garantem** performance futura

---

## 🆘 Resolução de Problemas

### Muitas perguntas?
→ Use valores padrão (pressione ENTER) nas perguntas que não quer modificar

### Não sei qual valor usar?
→ Comece com os valores padrão do config e ajuste gradualmente

### Quero testar múltiplas configurações?
→ Anote os parâmetros usados em cada teste para comparação

### Resultados ruins?
→ Verifique se os parâmetros fazem sentido para o período histórico testado

---

## 📞 Suporte

Consulte também:
- `CHANGELOG_LABORATORIO.md` - Changelog detalhado
- `docs/laboratorio_backtest.md` - Documentação básica
- `configs/lab_otimizacao.json` - Exemplo de configuração

---

**Versão**: 2.0 - Laboratório Completo  
**Data**: 2025-10-24  
**Status**: ✅ Totalmente Funcional
