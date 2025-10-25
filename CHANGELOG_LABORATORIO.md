# 🔬 Changelog - Laboratório de Otimização Interativo

## Versão 2.0 - Laboratório Completo (2025-10-24)

### Resumo
O script `backtest.py` foi **completamente expandido** para se tornar um **Laboratório de Otimização Completo**, permitindo aos usuários personalizar **TODOS os parâmetros principais** das estratégias de forma interativa, sem precisar editar manualmente arquivos JSON.

### Novidades da Versão 2.0

#### 🆕 Nova Seção: Personalização Completa de Parâmetros

Além dos timeframes, agora é possível configurar:

**Para DCA:**
- Ativar/desativar filtro RSI
- Limite do RSI
- Timeframe do RSI
- Timeframe da SMA de referência
- Percentual mínimo de melhora do PM
- Distância do Trailing Stop Loss
- Stop Loss catastrófico

**Para Giro Rápido:**
- Timeframe principal
- Gatilho de compra (% de queda)
- Ativar/desativar filtro RSI de entrada
- Limite do RSI de entrada
- Timeframe do RSI de entrada
- Stop Loss inicial
- Distância do Trailing Stop
- Alocação de capital (%)

#### 📊 Resumo Detalhado de Parâmetros

Antes da execução, o sistema mostra um resumo completo de **todos** os parâmetros que serão usados, incluindo valores padrão e modificados.

---

## Versão 1.0 - Laboratório Básico (2025-10-24)

### Resumo Inicial
Primeira versão do laboratório com foco em personalização de timeframes.

---

## 🎯 Funcionalidades Implementadas

### 1. Identificação do Timeframe Base
- **Nova pergunta**: "Qual é o timeframe do arquivo CSV?"
- Opções: 1m, 5m, 15m, 30m, 1h, 4h, 1d
- Essencial para o resampling correto dos dados históricos

### 2. Override Interativo de Timeframes
Após carregar o arquivo de configuração, o sistema agora pergunta:

#### Para Estratégia DCA (se ativa):
- ✅ Timeframe da SMA de referência
  - Mostra valor atual do config como padrão
  - Permite escolher de 1m até 1d
  
- ✅ Timeframe do RSI (se filtro RSI habilitado)
  - Mostra valor atual do config como padrão
  - Sincronizado com as opções disponíveis

#### Para Estratégia Giro Rápido (se ativa):
- ✅ Timeframe principal da estratégia
  - Mostra valor atual do config como padrão
  - Permite testar de 5m até 4h

- ✅ Timeframe do RSI de entrada (se habilitado)
  - Mostra valor atual do config como padrão
  - Flexibilidade para day trade ou swing trade

### 3. Aplicação Automática dos Overrides
- Os valores escolhidos sobrescrevem a configuração **em memória**
- O arquivo JSON original permanece intacto
- Conversão automática de timeframes para valores internos do bot

---

## 📝 Modificações nos Arquivos

### `backtest.py`

#### Funções Adicionadas (v1.0):
```python
def listar_timeframes_disponiveis() -> list
```
- Retorna lista de timeframes disponíveis para seleção
- Formato: questionary.Choice com títulos amigáveis

```python
def aplicar_overrides_timeframes(config_bot: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]
```
- Aplica os overrides no dicionário de configuração
- Converte timeframes para formato interno (horas para SMA, strings para RSI)
- Atualiza tanto DCA quanto Giro Rápido

#### Funções Adicionadas (v2.0):
```python
def perguntar_parametros_dca(config_bot: Dict[str, Any]) -> Dict[str, Any]
```
- Interface interativa completa para parâmetros do DCA
- Perguntas condicionais (RSI só se ativado)
- Validação de entrada em tempo real
- Mostra valores atuais como padrão
- Retorna dicionário com parâmetros modificados

```python
def perguntar_parametros_giro_rapido(config_bot: Dict[str, Any]) -> Dict[str, Any]
```
- Interface interativa completa para parâmetros do Giro Rápido
- 8 perguntas cobrindo todos os parâmetros principais
- Validação de entrada em tempo real
- Mostra valores atuais como padrão
- Retorna dicionário com parâmetros modificados

```python
def aplicar_parametros_estrategias(config_bot: Dict[str, Any], params_dca: Dict[str, Any], params_giro: Dict[str, Any]) -> Dict[str, Any]
```
- Aplica todos os parâmetros personalizados na configuração
- Mescla parâmetros do DCA no nível raiz do config
- Mescla parâmetros do Giro no dicionário 'estrategia_giro_rapido'
- Preserva parâmetros não modificados

```python
def imprimir_resumo_parametros(config_bot: Dict[str, Any], estrategias_selecionadas: list)
```
- Imprime resumo visual de todos os parâmetros finais
- Organizado por estratégia (DCA e Giro Rápido)
- Mostra apenas estratégias selecionadas
- Formatação clara com emojis e indentação

#### Fluxo Principal Atualizado:
1. Seleção de arquivo de configuração
2. Seleção de arquivo de dados CSV
3. **[NOVO]** Identificação do timeframe base do CSV
4. Definição de saldo inicial
5. Definição de taxa
6. Seleção de estratégias
7. **[NOVO]** Personalização de timeframes (overrides)
8. Confirmação e resumo (agora mostra overrides aplicados)
9. Execução da simulação

### `src/exchange/simulated_api.py`

#### Modificações no Construtor:
```python
def __init__(self, caminho_csv: str, saldo_inicial: float, taxa_pct: float, timeframe_base: str = '1m')
```

**Novo parâmetro:**
- `timeframe_base`: Identifica o timeframe nativo do CSV
- Padrão: '1m' (compatibilidade com código antigo)

**Melhorias:**
- Cache otimizado: dados originais são armazenados com seu timeframe base
- Evita resampling desnecessário quando o timeframe solicitado = timeframe base
- Documentação atualizada

---

## 📦 Novos Arquivos Criados

### 1. `docs/laboratorio_backtest.md`
Documentação completa incluindo:
- Visão geral das funcionalidades
- Fluxo de uso detalhado
- Exemplos práticos de uso
- Dicas de otimização
- Combinações sugeridas de timeframes
- Limitações e considerações

### 2. `configs/lab_otimizacao.json`
Template de configuração otimizado para o laboratório:
- Comentários explicativos sobre cada seção
- Valores padrão balanceados
- Sugestões de testes no final do arquivo
- Pronto para uso com o novo sistema

### 3. `CHANGELOG_LABORATORIO.md`
Este arquivo, documentando todas as mudanças.

---

## 🚀 Como Usar

### Modo Rápido
```bash
python backtest.py
```
Siga as perguntas interativas. Use as setas para navegar, ESPAÇO para selecionar (em checkboxes), ENTER para confirmar.

### Exemplo de Sessão
```
1. Arquivo de config: configs/lab_otimizacao.json
2. Arquivo de dados: dados/historicos/ADAUSDT_1m_2024.csv
3. Timeframe base: 1m
4. Saldo inicial: 1000
5. Taxa: 0.1
6. Estratégias: ☑ DCA, ☑ Giro Rápido
7. Overrides:
   - DCA SMA: 4h
   - DCA RSI: 1h
   - Giro Principal: 15m
   - Giro RSI: 15m
8. Confirmar e executar!
```

---

## 🎓 Exemplos de Testes Sugeridos

### Teste 1: DCA Conservador
- **SMA**: 4h (sinais mais estáveis)
- **RSI**: 1h (confirmação adicional)
- **Perfil**: Menos trades, maior confiabilidade

### Teste 2: DCA Agressivo
- **SMA**: 1h (mais oportunidades)
- **RSI**: 15m (reage rápido)
- **Perfil**: Mais trades, aproveita pequenos movimentos

### Teste 3: Giro Day Trade
- **Principal**: 5m ou 15m
- **RSI**: 5m
- **Perfil**: Alta frequência, requer dados de 1m ou 5m

### Teste 4: Giro Swing Trade
- **Principal**: 1h ou 4h
- **RSI**: 1h
- **Perfil**: Posições mais longas, movimentos maiores

### Teste 5: Mix Balanceado
- **DCA**: SMA 4h + RSI 1h (conservador)
- **Giro**: 15m + RSI 15m (ativo)
- **Perfil**: Acumulação estável + trades rápidos

---

## 🔧 Detalhes Técnicos

### Conversão de Timeframes
O sistema converte automaticamente:
- `"1m"` → 1/60 horas
- `"5m"` → 5/60 horas
- `"15m"` → 15/60 horas
- `"1h"` → 1 hora
- `"4h"` → 4 horas
- `"1d"` → 24 horas

### Compatibilidade
- ✅ Código antigo continua funcionando (timeframe_base padrão = '1m')
- ✅ Arquivos JSON existentes não precisam ser modificados
- ✅ Overrides são opcionais (pressione ENTER para manter padrões)

### Validação
⚠️ **Importante**: O sistema NÃO valida se os timeframes escolhidos fazem sentido. É responsabilidade do usuário:
- Garantir que o timeframe de destino > timeframe base
- Escolher combinações lógicas para cada estratégia

---

## 🐛 Troubleshooting

### Problema: Resampling falha
**Solução**: Verifique se informou corretamente o timeframe base do CSV.

### Problema: Poucos trades executados
**Solução**: Pode ser devido a timeframes muito altos. Tente timeframes menores ou dados com período mais longo.

### Problema: Muitos trades (performance ruim)
**Solução**: Timeframes muito baixos podem gerar muitos sinais. Aumente os timeframes ou ajuste os gatilhos.

---

## 📈 Próximas Melhorias Possíveis

- [ ] Batch mode: executar múltiplas combinações automaticamente
- [ ] Salvar/carregar perfis de override favoritos
- [ ] Visualização gráfica dos resultados
- [ ] Matriz de otimização (grid search)
- [ ] Export de resultados para análise externa
- [ ] Métricas avançadas (Sharpe Ratio, Max Drawdown, etc.)

---

## 📞 Suporte

Para dúvidas sobre a implementação:
1. Leia `docs/laboratorio_backtest.md`
2. Verifique exemplos em `configs/lab_otimizacao.json`
3. Teste com dados pequenos primeiro
4. Revise os logs durante a simulação

---

## ✅ Checklist de Validação

- [x] Função de listagem de timeframes implementada
- [x] Pergunta de timeframe base adicionada
- [x] Interface de override de timeframes implementada
- [x] Aplicação de overrides na configuração
- [x] Atualização do resumo para mostrar overrides
- [x] SimulatedExchangeAPI aceita timeframe_base
- [x] Cache de resampling otimizado
- [x] Documentação completa criada
- [x] Exemplo de configuração criado
- [x] Compatibilidade com código existente mantida
- [x] Changelog documentado

---

**Status**: ✅ Implementação Completa e Funcional
