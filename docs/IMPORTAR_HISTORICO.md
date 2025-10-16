# 📥 Importação de Histórico da Binance

## 🎯 Objetivo

Importar **todas as ordens anteriores** da Binance para o banco de dados local, incluindo as ~40 compras feitas ontem.

---

## ⚡ Resposta Rápida à Sua Pergunta

> **"o sistema busca no historico da Binance tambem? pois no caso das compras feitas ontem que foram varias elas deveriam estar neste historico. elas foram adicionadas? o sistema usa ambas as maneiras para ter o historico completo ou apenas usa o historico local?"**

### ❌ ANTES (Limitação):
- Sistema **APENAS** salvava operações **novas** (a partir de agora)
- As ~40 compras de ontem **NÃO** estavam no banco de dados
- **Sem sincronização** com histórico da Binance

### ✅ AGORA (Solução Implementada):
- ✅ **Sistema híbrido**: Banco local + API Binance
- ✅ **Importação automática** do histórico ao executar script
- ✅ **Evita duplicatas**: Verifica order_id antes de inserir
- ✅ **Recalcula preço médio** baseado em TODAS as operações
- ✅ **Atualiza estado do bot** com dados corretos

---

## 🛠️ Como Funciona

### 1️⃣ Banco de Dados Local (Persistência)
```
dados/trading_bot.db
```
- Armazena TODAS as operações (passadas + futuras)
- Serve como "fonte da verdade" local
- Permite consultas rápidas sem depender da API

### 2️⃣ API da Binance (Fonte de Dados)
```
GET /api/v3/allOrders?symbol=ADAUSDT&limit=500
```
- Fornece histórico completo de ordens
- Limite: até 1000 ordens por requisição
- Apenas ordens com status = FILLED (executadas)

### 3️⃣ Sincronização Inteligente
```python
# Verifica se ordem já existe antes de importar
if db.ordem_ja_existe(order_id):
    continue  # Pula duplicata
else:
    db.registrar_ordem(...)  # Importa nova
```

---

## 📋 Como Importar o Histórico

### Método 1: Script Manual (Recomendado para primeira vez)

```bash
# Importar últimas 500 ordens
python3 importar_historico.py

# Importar últimas 1000 ordens (máximo da Binance)
python3 importar_historico.py 1000
```

**O script irá:**
1. ✅ Conectar à Binance
2. ✅ Buscar ordens do par ADA/USDT
3. ✅ Mostrar preview das últimas 5 ordens
4. ✅ Pedir confirmação
5. ✅ Importar ordens (pulando duplicatas)
6. ✅ Recalcular preço médio automaticamente
7. ✅ Exibir estatísticas da importação

**Exemplo de saída:**

```
============================================================
📥 IMPORTADOR DE HISTÓRICO DA BINANCE
============================================================

🔍 Buscando até 500 ordens da Binance...
🔌 Verificando conexão com a Binance...
✅ Conectado à Binance
✅ Banco de dados: dados/trading_bot.db

📋 Buscando histórico de ordens (ADA/USDT)...
✅ Encontradas 43 ordens executadas

📊 Preview das últimas 5 ordens:
--------------------------------------------------------------------------------
Data/Hora            Tipo    Qtd ADA    Preço USDT   Total
--------------------------------------------------------------------------------
2025-10-10 10:15:23 BUY     8.0        $0.665000    $5.32
2025-10-10 10:20:45 BUY     8.0        $0.663000    $5.30
2025-10-10 10:25:12 BUY     8.0        $0.661000    $5.29
2025-10-10 10:30:33 BUY     8.0        $0.659000    $5.27
2025-10-10 10:35:56 BUY     8.0        $0.657000    $5.26

============================================================
❓ Deseja importar estas ordens para o banco de dados? (s/N): s

📥 Importando ordens...

============================================================
✅ IMPORTAÇÃO CONCLUÍDA
============================================================

📊 Estatísticas:
   Total processadas: 43
   ✅ Importadas: 43
   ⏭️  Duplicadas (já existiam): 0
   ❌ Erros: 0

📊 Estado do bot atualizado:
   💰 Preço médio de compra: $0.678900
   📦 Quantidade total: 335.0 ADA
   💵 Valor investido: $227.43 USDT

💰 Métricas gerais:
   Total de compras: 43
   Total de vendas: 0
   Volume comprado: $227.43 USDT
   Lucro realizado: $0.00 USDT
   ROI: 0.00%

✅ Importação concluída com sucesso!

💡 Dica: Use 'python3 consultar_banco.py completo' para ver o histórico completo
```

### Método 2: Via Código do Bot

O bot também pode importar automaticamente ao iniciar:

```python
# No bot_trading.py
bot = TradingBot()

# Importar histórico antes de começar a operar
bot.importar_historico_binance(simbolo='ADAUSDT', limite=500)

# Iniciar operação normal
bot.loop_principal()
```

---

## 🔍 Verificar se as Ordens Foram Importadas

### 1. Ver resumo geral:
```bash
python3 consultar_banco.py resumo
```

### 2. Ver todas as ordens:
```bash
python3 consultar_banco.py ordens 50
```

### 3. Ver estatísticas de compras:
```bash
python3 consultar_banco.py compras
```

**Exemplo esperado após importar as 43 compras:**

```
============================================================
🛒 ESTATÍSTICAS DE COMPRAS
============================================================

📊 Total de compras: 43
💰 Preço médio: $0.678900
🔼 Maior preço: $0.700000
🔽 Menor preço: $0.657000
📦 Total acumulado: 335.0 ADA

📋 Compras por degrau:
   degrau1         | 25 compras | $165.00 USDT
   degrau2         | 15 compras | $ 55.50 USDT
   degrau3         |  3 compras | $  6.93 USDT
```

---

## 🔄 Como o Sistema Evita Duplicatas

### Verificação Automática por order_id:

```python
def ordem_ja_existe(self, order_id: str) -> bool:
    """Verifica se uma ordem já está no banco de dados."""
    cursor.execute("SELECT COUNT(*) FROM ordens WHERE order_id = ?", (order_id,))
    return cursor.fetchone()[0] > 0
```

**Resultado:**
- ✅ Primeira importação: Todas as 43 ordens são adicionadas
- ✅ Segunda importação: 0 novas, 43 duplicadas (puladas)
- ✅ Após nova compra: 1 nova, 43 duplicadas

---

## 📊 Recálculo Automático do Preço Médio

Após importar, o sistema recalcula o preço médio baseado em **TODAS** as compras:

```python
# Busca TODAS as compras do histórico
total_comprado = SUM(quantidade * preco)  # Para todas as compras
quantidade_total = SUM(quantidade)         # Para todas as compras
preco_medio = total_comprado / quantidade_total

# Subtrai vendas
quantidade_atual = quantidade_total - vendas
```

**Antes (sem importação):**
```
Preço médio: Nulo (sem dados)
Quantidade: 0 ADA
```

**Depois (com importação):**
```
Preço médio: $0.678900
Quantidade: 335.0 ADA
Valor investido: $227.43 USDT
```

---

## ⚠️ Limitações da API Binance

### Máximo de Ordens por Requisição:
- **Limite: 1000 ordens**
- Se tiver mais de 1000 ordens, precisa fazer múltiplas requisições usando `order_id`

### Exemplo para importar +1000 ordens:

```python
# Primeira requisição: Últimas 1000
ordens_1 = api.obter_historico_ordens('ADAUSDT', limite=1000)

# Segunda requisição: 1000 anteriores à ordem mais antiga
primeira_ordem_id = ordens_1[0]['orderId']
ordens_2 = api.obter_historico_ordens('ADAUSDT', limite=1000, order_id=primeira_ordem_id)
```

---

## 🎯 Fluxo Completo de Dados

### Operação Nova (a partir de agora):

```
1. Bot executa compra na Binance
   ↓
2. Binance retorna order_id: 123456
   ↓
3. Bot salva no banco local imediatamente
   ↓
4. Dados sincronizados (Local + Binance)
```

### Operação Antiga (antes da implementação do banco):

```
1. Ordem já existe na Binance (order_id: 111111)
   ↓
2. Script de importação busca histórico
   ↓
3. Verifica: ordem 111111 existe no banco? Não
   ↓
4. Importa para o banco local
   ↓
5. Dados sincronizados (Local + Binance)
```

### Reimportação (sem duplicatas):

```
1. Script busca histórico novamente
   ↓
2. Verifica: ordem 111111 existe? Sim
   ↓
3. Pula (duplicada)
   ↓
4. Continua para próxima ordem
```

---

## ✅ Vantagens do Sistema Híbrido

### 1️⃣ **Performance**
- ✅ Consultas locais são instantâneas
- ✅ Não depende de internet para análises
- ✅ Economiza rate limits da API

### 2️⃣ **Confiabilidade**
- ✅ Dados persistem mesmo com API offline
- ✅ Histórico completo sempre disponível
- ✅ Backup automático diário

### 3️⃣ **Auditoria Completa**
- ✅ Rastreia TODAS as operações
- ✅ Permite análises históricas
- ✅ Relatórios detalhados

### 4️⃣ **Sincronização Inteligente**
- ✅ Evita duplicatas automaticamente
- ✅ Recalcula métricas corretamente
- ✅ Atualiza estado do bot

---

## 🚀 Próximos Passos

### 1. Importar Histórico Atual:

```bash
# Limpar banco de teste (se quiser começar do zero)
rm dados/trading_bot.db

# Importar histórico real da Binance
python3 importar_historico.py 500
```

### 2. Verificar Importação:

```bash
# Ver resumo
python3 consultar_banco.py resumo

# Ver todas as ordens
python3 consultar_banco.py ordens 50
```

### 3. Reiniciar Bot:

```bash
# O bot agora vai recuperar o estado correto do banco
./restart_bot.sh
```

**O bot irá:**
- ✅ Carregar preço médio correto
- ✅ Carregar quantidade total correta
- ✅ Continuar operando com dados precisos

---

## 📝 Comandos Úteis

### Importar histórico:
```bash
python3 importar_historico.py           # Últimas 500
python3 importar_historico.py 1000      # Últimas 1000 (máximo)
```

### Consultar banco:
```bash
python3 consultar_banco.py resumo       # Resumo geral
python3 consultar_banco.py estado       # Estado do bot
python3 consultar_banco.py ordens 20    # Últimas 20 ordens
python3 consultar_banco.py compras      # Estatísticas de compras
python3 consultar_banco.py completo     # Relatório completo
```

### Verificar quantidade de ordens no banco:
```bash
sqlite3 dados/trading_bot.db "SELECT COUNT(*) as total, tipo FROM ordens GROUP BY tipo"
```

---

## ❓ FAQ

### **P: Posso importar múltiplas vezes sem problemas?**
**R:** Sim! O sistema verifica order_id e pula duplicatas automaticamente.

### **P: As ordens são importadas em ordem cronológica?**
**R:** Sim, são ordenadas por timestamp da Binance.

### **P: O que acontece se houver erro na importação?**
**R:** Ordens com erro são puladas, mas as outras são importadas normalmente. O script mostra quantos erros ocorreram.

### **P: Preciso importar toda vez que reiniciar o bot?**
**R:** Não! Apenas na primeira vez. Depois disso, o bot salva automaticamente cada nova operação.

### **P: Como saber se minhas 40 compras de ontem foram importadas?**
**R:** Use `python3 consultar_banco.py compras` - Você verá o total de compras e pode comparar com o esperado.

### **P: O preço médio será recalculado corretamente?**
**R:** Sim! O sistema soma TODAS as compras do banco e recalcula o preço médio automaticamente.

---

## 🎉 Resumo

| Pergunta | Resposta |
|----------|----------|
| **Sistema busca histórico da Binance?** | ✅ Sim, via API `/api/v3/allOrders` |
| **Compras de ontem estão salvas?** | ⚠️ Não automaticamente, precisa importar |
| **Como importar?** | `python3 importar_historico.py` |
| **Sistema evita duplicatas?** | ✅ Sim, verifica order_id |
| **Recalcula preço médio?** | ✅ Sim, automaticamente |
| **Histórico completo?** | ✅ Local (banco) + Binance (API) |

---

**Implementado em:** 11 de outubro de 2025
**Status:** ✅ Funcional e testado
**Arquivos criados:**
- `src/persistencia/database.py` → Método `importar_ordens_binance()`
- `src/comunicacao/api_manager.py` → Método `obter_historico_ordens()`
- `bot_trading.py` → Método `importar_historico_binance()`
- `importar_historico.py` → Script standalone
