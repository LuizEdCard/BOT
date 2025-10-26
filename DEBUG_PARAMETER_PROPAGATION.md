# Debug: Propagação de Parâmetros Giro Rápido

**Data:** 2025-10-25
**Status:** 🔍 INVESTIGAÇÃO EM ANDAMENTO
**Problema:** Parâmetro `alocacao_capital_pct` não está sendo propagado corretamente

---

## 🐛 Problema Reportado

Ao configurar a alocação de capital do Giro Rápido para **50%** através da interface interativa, o resumo final exibe corretamente **"50%"**, mas o backtest executa com apenas **20%** (valor padrão do arquivo de configuração).

**Sintoma:**
```
📋 RESUMO FINAL DA CONFIGURAÇÃO
   ...
   Alocação de Capital: 50.0%  ✅ (correto)

[Inicia backtest...]
[Fim do backtest]

[Resultado: Apenas $200 de $1000 foram alocados (20%) em vez de $500 (50%)]  ❌
```

---

## 🔍 Investigação Realizada

### 1. Fluxo de Propagação de Parâmetros

```
┌─────────────────────────────────────────────────────┐
│ 1. perguntar_parametros_giro_rapido()               │
│    └─ Retorna: params_giro = {'alocacao_capital_pct': 50.0, ...}
├─────────────────────────────────────────────────────┤
│ 2. aplicar_parametros_estrategias()                 │
│    └─ Aplica params_giro em config['estrategia_giro_rapido']
├─────────────────────────────────────────────────────┤
│ 3. imprimir_resumo_parametros()                     │
│    └─ Exibe os valores (aparentemente corretos)
├─────────────────────────────────────────────────────┤
│ 4. BotWorker.__init__()                             │
│    └─ Lê config['estrategia_giro_rapido']['alocacao_capital_pct']
│       ├─ Linha 94 em bot_worker.py:                 │
│       │  alocacao_giro_pct = Decimal(str(         │
│       │    estrategia_giro_config.get('alocacao_capital_pct', 20)
│       │  ))
│       └─ DEVERIA ter 50, mas tem 20?
└─────────────────────────────────────────────────────┘
```

### 2. Pontos de Análise

#### ✅ Verificado: Função `perguntar_parametros_giro_rapido()`
- **Linhas:** 399-591
- **Status:** ✅ Parece retornar o valor correto
- **Adicionado DEBUG:** Imprime `params` antes de retornar

#### ✅ Verificado: Função `aplicar_parametros_estrategias()`
- **Linhas:** 594-626
- **Status:** ✅ Lógica parece correta (atribui params_giro em config['estrategia_giro_rapido'])
- **Adicionado DEBUG:** Imprime params_giro recebidos e config['estrategia_giro_rapido'] após aplicação

#### ✅ Verificado: Fluxo em `main()`
- **Linhas:** 1080-1095
- **Status:** ✅ Ordem correta (perguntar → aplicar → resumo)
- **Adicionado DEBUG:** Imprime config após aplicar e antes de iniciar BotWorker

#### ❓ A Verificar: Inicialização do BotWorker
- **Arquivo:** `src/core/bot_worker.py`
- **Linha:** 94
- **Questão:** O valor está chegando corretamente nesta linha?

---

## 🔧 Correções Adicionadas

### 1. Debug em `perguntar_parametros_giro_rapido()`
**Linha 587-589:**
```python
print(f"\n[DEBUG] perguntar_parametros_giro_rapido retornando:")
print(f"[DEBUG] params = {params}")
```

### 2. Debug em `aplicar_parametros_estrategias()`
**Linhas 616-623:**
```python
print(f"\n[DEBUG] aplicar_parametros_estrategias aplicando Giro Rápido:")
print(f"[DEBUG] params_giro = {params_giro}")
# ... para cada key, value ...
print(f"[DEBUG]   Aplicado: estrategia_giro_rapido['{key}'] = {value}")
print(f"[DEBUG] config_bot['estrategia_giro_rapido'] após aplicação = {config_bot['estrategia_giro_rapido']}")
```

### 3. Debug em `main()` - Após aplicação
**Linhas 1084-1086:**
```python
print("\n[DEBUG] Configuração de Giro Rápido após aplicar parâmetros:")
print(f"[DEBUG] config['estrategia_giro_rapido'] = {config.get('estrategia_giro_rapido', {})}")
```

### 4. Debug em `main()` - Antes de BotWorker
**Linhas 1187-1189:**
```python
print("\n[DEBUG] Configuração de Giro Rápido ANTES de iniciar BotWorker:")
print(f"[DEBUG] config['estrategia_giro_rapido'] = {config.get('estrategia_giro_rapido', {})}")
```

---

## 📊 Próximas Etapas de Debug

### Para o Usuário Executar:

1. **Execute o backtest com debug ativado:**
   ```bash
   python backtest.py
   # Selecione estrategia_exemplo_giro_rapido.json (ou backtest_template.json)
   # Selecione o CSV de dados
   # Selecione timeframe
   # Selecione Giro Rápido como estratégia
   # Configure alocação para 50%
   # Deixe o script rodar
   ```

2. **Procure por linhas com `[DEBUG]`** na saída e capture:
   - O valor retornado por `perguntar_parametros_giro_rapido()`
   - O valor aplicado em `aplicar_parametros_estrategias()`
   - O valor antes de iniciar BotWorker

3. **Compartilhe estes outputs:**
   ```
   [DEBUG] perguntar_parametros_giro_rapido retornando:
   [DEBUG] params = ...

   [DEBUG] aplicar_parametros_estrategias aplicando Giro Rápido:
   [DEBUG] params_giro = ...

   [DEBUG] Configuração de Giro Rápido ANTES de iniciar BotWorker:
   [DEBUG] config['estrategia_giro_rapido'] = ...
   ```

---

## 🎯 Hipóteses para Investigação

### Hipótese 1: Sobrescrita após aplicação ❓
**Possível causa:** Algo entre `aplicar_parametros_estrategias()` (linha 1081) e `BotWorker.__init__()` (linha 1193) está sobrescrevendo a configuração.

**Para verificar:** Compare os valores de debug antes e depois

### Hipótese 2: Carregamento de arquivo em segundo plano ❓
**Possível causa:** O BotWorker está carregando a configuração do arquivo JSON original em vez de usar o objeto `config` passado.

**Para verificar:** Veja se há um `json.load()` ou similar em `bot_worker.py` que recarrega a config.

### Hipótese 3: Atribuição incorreta em `perguntar_parametros_giro_rapido()` ❓
**Possível causa:** O parâmetro não está sendo armazenado em `params` corretamente.

**Para verificar:** Debug output mostrará `params = {'alocacao_capital_pct': 50}` ou vazio?

### Hipótese 4: Bug em `aplicar_parametros_estrategias()` ❓
**Possível causa:** A função está aplicando em um dicionário diferente ou com uma chave errada.

**Para verificar:** Debug output mostrará a aplicação correta?

---

## 📝 Checklist de Debug

- [ ] Executar backtest com debug ativado
- [ ] Capturar todos os `[DEBUG]` outputs
- [ ] Verificar se 50% está em `params` retornado
- [ ] Verificar se 50% está sendo aplicado em `config['estrategia_giro_rapido']`
- [ ] Verificar se 50% chega até antes de `BotWorker.__init__()`
- [ ] Se 50% desaparece entre a aplicação e BotWorker, procurar sobrescrita
- [ ] Se 50% nunca chega em `params`, problema é em `perguntar_parametros_giro_rapido()`

---

## 🔗 Arquivos Envolvidos

- **backtest.py:** Linhas 399-626 (perguntar + aplicar), 1080-1195 (fluxo principal)
- **bot_worker.py:** Linha 94 (lê alocação)
- **simulated_api.py:** Pode estar envolvido em inicializar alocação

---

## 📌 Status

**Compilação:** ✅ OK
**Debug Statements Adicionados:** ✅ 4 pontos de debug estratégicos
**Próximo Passo:** Executar com debug e capturar outputs

---

**Versão:** 1.0
**Data:** 2025-10-25
**Status:** 🔍 Aguardando output de debug para diagnóstico
