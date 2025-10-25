# 🔬 Laboratório de Otimização de Backtest - README

## 🎯 O Que É?

Um sistema **completo e interativo** para otimizar estratégias de trading através de backtesting. Sem editar JSON, sem código, apenas perguntas e respostas.

## ⚡ Início Rápido

```bash
python backtest.py
```

Responda as perguntas, execute, analise resultados, ajuste e repita.

## 🌟 Principais Funcionalidades

### ✅ Personalização Total
- **13 parâmetros do DCA** (acumulação)
- **13 parâmetros do Giro Rápido** (swing trade)
- **Todos os timeframes** ajustáveis
- **Todos os stops e filtros** configuráveis

### ✅ Interface Amigável
- Perguntas claras e objetivas
- Valores padrão sempre visíveis
- Validação em tempo real
- Resumo completo antes de executar

### ✅ Resultados Profissionais
- Comparação com Buy & Hold
- Análise de trades (SL, TSL, Metas)
- Métricas de performance
- Relatório visual detalhado

## 📚 Documentação

### Para Iniciantes
→ Leia: [`docs/GUIA_LABORATORIO_COMPLETO.md`](docs/GUIA_LABORATORIO_COMPLETO.md)
- Explicação detalhada de cada parâmetro
- 4 exemplos prontos de configurações
- Dicas de otimização por tipo de mercado

### Para Desenvolvedores
→ Leia: [`CHANGELOG_LABORATORIO.md`](CHANGELOG_LABORATORIO.md)
- Detalhes técnicos da implementação
- Lista completa de funções
- Histórico de versões

### Documentação Básica
→ Leia: [`docs/laboratorio_backtest.md`](docs/laboratorio_backtest.md)
- Overview das funcionalidades (v1.0)
- Dicas de combinações de timeframes

## 🎓 Exemplos de Uso

### Exemplo 1: Teste Rápido com Padrões
```
1. Selecione config: configs/lab_otimizacao.json
2. Selecione dados: dados/historicos/ADAUSDT_1m.csv
3. Timeframe: 1m
4. Saldo: 1000
5. Taxa: 0.1
6. Estratégias: Ambas
7. Parâmetros: [Pressione ENTER em todas, usa padrões]
8. Confirme e execute!
```
**Tempo**: ~30 segundos

### Exemplo 2: Otimização Personalizada
```
1-6. [Mesmo do Exemplo 1]
7. Parâmetros DCA:
   - RSI: Sim → Limite 35 → Timeframe 1h
   - SMA: 4h
   - PM Mínimo: 1.5%
   - TSL: 2.0%
   - SL Catastrófico: 10%
8. Parâmetros Giro Rápido:
   - Timeframe: 15m
   - Gatilho: 2.0%
   - RSI: Sim → Limite 30 → Timeframe 15m
   - SL Inicial: 2.5%
   - TSL: 0.8%
   - Alocação: 20%
9. Confirme e execute!
```
**Tempo**: ~2 minutos

## 📊 Parâmetros Configuráveis

### DCA (Acumulação)
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| Filtro RSI | Sim/Não | Não | Ativar confirmação RSI |
| RSI Limite | Número | 35 | Limite para compra |
| RSI Timeframe | Select | 1h | Timeframe do RSI |
| SMA Timeframe | Select | 4h | Timeframe da SMA |
| PM Mínimo | % | 1.25 | Melhora mínima do PM |
| TSL | % | 2.0 | Trailing Stop Loss |
| SL Catastrófico | % | 10.0 | Stop Loss máximo |

### Giro Rápido (Swing Trade)
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| Timeframe | Select | 15m | Timeframe principal |
| Gatilho | % | 2.0 | Queda para comprar |
| Filtro RSI | Sim/Não | Sim | Confirmar com RSI |
| RSI Limite | Número | 30 | Limite RSI entrada |
| RSI Timeframe | Select | 15m | Timeframe RSI |
| SL Inicial | % | 2.5 | Stop Loss inicial |
| TSL | % | 0.8 | Trailing Stop |
| Alocação | % | 20 | % do capital |

## 🚀 Fluxo de Otimização

```
┌─────────────────────────────────────┐
│  1. Executar com padrões            │
│     (Baseline)                      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  2. Analisar resultados             │
│     - Lucro/Prejuízo                │
│     - Número de trades              │
│     - Motivos de saída              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. Identificar melhorias           │
│     - Muitos SL? ↑ Stops            │
│     - Poucos trades? ↓ Gatilhos     │
│     - Baixo retorno? Ajustar RSI    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  4. Ajustar 1-3 parâmetros          │
│     (Mudanças incrementais)         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  5. Executar novamente              │
│     (Comparar com baseline)         │
└──────────────┬──────────────────────┘
               │
               ▼
         [Repetir até ótimo]
```

## 💡 Dicas de Ouro

### ✅ DO (Faça):
- Comece com valores padrão
- Mude 1-3 parâmetros por vez
- Anote os resultados de cada teste
- Teste em diferentes períodos históricos
- Compare sempre com Buy & Hold

### ❌ DON'T (Não Faça):
- Mudar todos os parâmetros de uma vez
- Usar valores extremos sem justificativa
- Ignorar o contexto do mercado no período
- Assumir que backtest = futuro garantido
- Esquecer de considerar slippage e taxas

## 🔧 Arquivos Importantes

```
BOT/
├── backtest.py                        # Script principal ⭐
├── README_LABORATORIO.md              # Este arquivo
├── CHANGELOG_LABORATORIO.md           # Changelog técnico
├── test_laboratorio.py                # Testes de validação
├── configs/
│   └── lab_otimizacao.json           # Config exemplo
├── docs/
│   ├── GUIA_LABORATORIO_COMPLETO.md  # Guia detalhado ⭐
│   └── laboratorio_backtest.md        # Documentação v1.0
└── src/
    └── exchange/
        └── simulated_api.py           # API simulada (modificada)
```

## 📈 Resultados Esperados

### Exemplo de Saída
```
================================================================================
📊 RELATÓRIO FINAL DO BACKTEST
================================================================================

📅 Período Simulado:
   Início: 2024-01-01 00:00:00
   Fim: 2024-12-31 23:59:00
   Total de velas: 525,600

💰 Resultados da Estratégia:
   Saldo inicial: $1000.00 USDT
   Saldo final USDT: $1250.00
   Lucro/Prejuízo: $250.00 (+25.00%)

📈 Operações Executadas:
   Total de compras: 45
   Total de vendas: 42
   Total de trades: 87

🎯 Análise de Saídas:
   Stop Loss (SL): 8 (19.0%)
   Trailing Stop Loss (TSL): 24 (57.1%)
   Meta de Lucro: 10 (23.8%)

📊 Benchmark Buy & Hold:
   Lucro/Prejuízo: $150.00 (+15.00%)

🔍 Comparação:
   ✅ Estratégia superou Buy & Hold em $100.00 (+10.00pp)

================================================================================
```

## ⚠️ Avisos Importantes

1. **Backtest ≠ Realidade**: Resultados passados não garantem resultados futuros
2. **Overfitting**: Cuidado ao otimizar demais para um período específico
3. **Slippage**: API simulada assume execução perfeita (realidade pode variar)
4. **Custos**: Considere taxas, spread e custos operacionais reais
5. **Psicologia**: Backtest não testa sua disciplina emocional

## 🆘 Suporte e Ajuda

### Problema Comum #1: "Muitas Perguntas!"
**Solução**: Pressione ENTER para usar valores padrão nas perguntas que não quer modificar.

### Problema Comum #2: "Não sei qual valor usar"
**Solução**: Leia `docs/GUIA_LABORATORIO_COMPLETO.md` - tem dicas para cada parâmetro.

### Problema Comum #3: "Resultados ruins"
**Solução**: 
1. Verifique se o período histórico é representativo
2. Compare com Buy & Hold (talvez o mercado só caiu)
3. Revise se os parâmetros fazem sentido juntos

### Problema Comum #4: "Erro ao executar"
**Solução**:
1. Verifique formato do CSV (timestamp, OHLCV)
2. Confirme timeframe base correto
3. Execute `python test_laboratorio.py` para validar instalação

## 🎯 Próximos Passos

Após dominar o laboratório:

1. **Validação Cruzada**: Teste em múltiplos períodos
2. **Walk-Forward**: Otimize em período, valide no seguinte
3. **Análise de Sensibilidade**: Veja como pequenas mudanças afetam resultados
4. **Paper Trading**: Teste em tempo real com dinheiro virtual
5. **Live Trading**: Apenas após validação extensiva

## 📞 Contato e Contribuições

- **Documentação**: Veja arquivos em `docs/`
- **Issues**: Use sistema de issues do repositório
- **Melhorias**: Pull requests são bem-vindos!

## 📄 Licença

Veja LICENSE no repositório principal.

---

**Versão**: 2.0  
**Status**: ✅ Produção  
**Última Atualização**: 2025-10-24

**Desenvolvido com** 💙 **para otimização de estratégias de trading**
