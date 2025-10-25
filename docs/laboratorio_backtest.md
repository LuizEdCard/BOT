# 🔬 Laboratório de Otimização de Backtest

## Visão Geral

O `backtest.py` foi evoluído para se tornar um **Laboratório de Otimização Interativo**, permitindo que você experimente diferentes configurações de timeframes para suas estratégias sem precisar editar manualmente arquivos de configuração JSON.

## Funcionalidades Principais

### 1. Seleção de Arquivos
- **Arquivo de Configuração (.json)**: Escolha qual configuração de bot usar como base
- **Arquivo de Dados (.csv)**: Selecione o conjunto de dados históricos para o backtest
- **Timeframe Base**: Identifique qual o timeframe do arquivo CSV (1m, 5m, 15m, 1h, 4h, 1d)

### 2. Configuração de Capital e Taxas
- **Saldo Inicial**: Defina o capital inicial em USDT
- **Taxa da Exchange**: Configure a taxa de transação (padrão: 0.1%)

### 3. Seleção de Estratégias
Escolha quais estratégias testar:
- **Ambas**: DCA + Giro Rápido
- **DCA**: Apenas estratégia de acumulação
- **Giro Rápido**: Apenas estratégia de swing trade

### 4. Personalização de Timeframes (Override)

Esta é a **funcionalidade principal** do laboratório. Após carregar a configuração, você pode sobrescrever os timeframes das estratégias:

#### Para DCA (se ativa):
- **Timeframe da SMA**: Escolha qual timeframe usar para calcular a SMA de referência
  - Valores atuais da configuração são mostrados como padrão
  - Opções: 1m, 5m, 15m, 30m, 1h, 4h, 1d
  
- **Timeframe do RSI** (se filtro RSI estiver habilitado): Escolha qual timeframe usar para o RSI

#### Para Giro Rápido (se ativo):
- **Timeframe Principal**: Escolha qual timeframe usar para identificar oportunidades de swing trade
  - O padrão da configuração é mostrado
  - Permite testar estratégias mais rápidas (5m) ou mais lentas (1h)

- **Timeframe do RSI** (se filtro RSI estiver habilitado): Escolha qual timeframe usar para confirmar entradas

## Fluxo de Uso

```
1. Selecionar arquivo de configuração
2. Selecionar arquivo de dados históricos
3. Informar timeframe base do CSV
4. Definir saldo inicial
5. Definir taxa da exchange
6. Escolher estratégias para testar
7. Personalizar timeframes (overrides)
8. Confirmar e executar
9. Analisar resultados
```

## Exemplo de Uso

### Cenário: Testando DCA com diferentes timeframes de SMA

```bash
python backtest.py
```

**Passo a passo:**
1. Selecione `configs/bot_ada_binance.json`
2. Selecione `dados/historicos/ADAUSDT_1m_2024.csv`
3. Informe que o CSV é de **1 minuto** (1m)
4. Saldo inicial: 1000 USDT
5. Taxa: 0.1%
6. Estratégia: Selecione "DCA (Acumulação)"
7. **Override de timeframes:**
   - SMA do DCA: Teste com **4h** (ao invés do padrão 1h)
   - RSI do DCA: Mantenha em **1h**
8. Confirme e aguarde os resultados

### Cenário: Otimizando Giro Rápido

```bash
python backtest.py
```

1. Selecione `configs/backtest_template.json`
2. Selecione `dados/historicos/ADAUSDT_5m_2024.csv`
3. Informe que o CSV é de **5 minutos** (5m)
4. Saldo inicial: 1000 USDT
5. Taxa: 0.1%
6. Estratégia: Selecione "Giro Rápido (Swing Trade)"
7. **Override de timeframes:**
   - Giro Rápido: Teste com **30m** (ao invés de 15m)
   - RSI do Giro: Teste com **15m**
8. Confirme e execute

## Relatório de Resultados

Ao final da simulação, você receberá:

### 📊 Informações Gerais
- Período simulado (início e fim)
- Total de velas processadas

### 💰 Resultados da Estratégia
- Saldo final em USDT e no ativo
- Lucro/Prejuízo total e percentual
- Número de compras e vendas
- Volume total negociado

### 🎯 Análise de Saídas
- Quantas vendas foram por Stop Loss
- Quantas foram por Trailing Stop Loss
- Quantas atingiram metas de lucro

### 📈 Benchmark Buy & Hold
- Comparação com a estratégia de "comprar e segurar"
- Diferença de performance (absoluta e relativa)

## Dicas de Otimização

### Testando SMA
- **Timeframes maiores** (4h, 1d) → Sinais mais confiáveis, mas menos frequentes
- **Timeframes menores** (15m, 1h) → Mais oportunidades, mas mais ruído

### Testando Giro Rápido
- **Timeframes menores** (5m, 15m) → Mais trades, maior risco
- **Timeframes maiores** (1h, 4h) → Menos trades, movimentos maiores

### Combinações Sugeridas

#### Acumulação Conservadora
- SMA: 4h ou 1d
- RSI: 1h ou 4h

#### Acumulação Agressiva
- SMA: 1h
- RSI: 15m ou 30m

#### Giro Rápido - Day Trade
- Principal: 5m ou 15m
- RSI: 5m

#### Giro Rápido - Swing Trade
- Principal: 1h ou 4h
- RSI: 1h

## Arquivos Modificados

### `backtest.py`
- Adicionadas funções `listar_timeframes_disponiveis()`
- Adicionada função `perguntar_override_timeframes()` para coleta interativa
- Adicionada função `aplicar_overrides_timeframes()` para aplicar as mudanças
- Fluxo principal atualizado para incluir etapa de personalização

### `src/exchange/simulated_api.py`
- Construtor atualizado para aceitar `timeframe_base` como parâmetro
- Cache de resampling otimizado com timeframe base
- Documentação atualizada

## Limitações e Considerações

1. **Timeframe Base do CSV**: É crucial informar corretamente o timeframe do CSV. Se informado incorretamente, o resampling não funcionará adequadamente.

2. **Compatibilidade de Timeframes**: Ao fazer resampling, certifique-se de que o timeframe de destino é maior que o timeframe base (ex: não tente criar 1h a partir de 4h).

3. **Memória**: CSVs muito grandes com resampling para múltiplos timeframes podem consumir bastante memória.

4. **Validação**: O sistema não valida se a combinação de timeframes escolhida faz sentido. Isso fica a cargo do usuário.

## Próximos Passos

Possíveis melhorias futuras:
- [ ] Salvar configurações de override favoritas
- [ ] Executar múltiplas simulações em batch
- [ ] Gráficos de comparação de performance
- [ ] Matriz de otimização (testar todas as combinações)
- [ ] Export de resultados para CSV/Excel
- [ ] Análise de drawdown e outras métricas avançadas

## Suporte

Para dúvidas ou problemas:
1. Verifique se o CSV está no formato correto (timestamp, open, high, low, close, volume)
2. Confirme se o timeframe base foi informado corretamente
3. Revise os logs gerados durante a simulação
4. Consulte o arquivo de configuração JSON para entender os valores padrão
