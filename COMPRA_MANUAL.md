# 💰 Compra Manual de ADA

Sistema de compra manual fora da estratégia automática.

## Como Usar

### 1. Compra com valor padrão ($5 USDT)
```bash
source venv/bin/activate
python comprar_manual.py
```

### 2. Compra especificando valor em USDT
```bash
source venv/bin/activate
python comprar_manual.py --usdt 10
```
Exemplo: `--usdt 10` vai gastar $10 USDT e calcular quantos ADA comprar.

### 3. Compra especificando quantidade em ADA
```bash
source venv/bin/activate
python comprar_manual.py --ada 15.5
```
Exemplo: `--ada 15.5` vai comprar exatamente 15.5 ADA.

## Características

- ✅ **Confirmação interativa**: Solicita confirmação antes de executar a compra
- ✅ **Validação de saldo**: Verifica se há USDT suficiente
- ✅ **Ajuste automático**: Garante que o valor mínimo da ordem seja $5.00 USDT
- ✅ **Step size correto**: Arredonda para múltiplos de 0.1 ADA (requisito Binance)
- ✅ **Log detalhado**: Mostra preço, quantidade e confirmação da ordem
- ✅ **Atualização de saldo**: Exibe novos saldos após a compra

## Limites da Binance

- **Valor mínimo da ordem**: $5.00 USDT (NOTIONAL mínimo)
- **Quantidade mínima**: 1.0 ADA
- **Step size**: 0.1 ADA (só aceita múltiplos de 0.1)

## Exemplos de Uso

### Exemplo 1: Compra rápida com valor padrão
```bash
$ source venv/bin/activate
$ python comprar_manual.py
💰 COMPRA MANUAL DE ADA
✅ Conectado à Binance
📊 Preço atual ADA: $0.648300
💵 Valor padrão: $5.00 USDT
🔢 Quantidade: 7.71 ADA
⚠️ Ajustando quantidade para valor mínimo ($5.00 USDT)
🔢 Nova quantidade: 7.8 ADA
💼 Saldo USDT disponível: $10.52

⚠️  CONFIRMAR COMPRA MANUAL
   Quantidade: 7.80 ADA
   Preço: $0.648300
   Total: $5.06 USDT

🔔 Confirmar compra? (S/n): S
✅ COMPRA MANUAL EXECUTADA COM SUCESSO!
   Order ID: 7907732932
💼 Novo saldo USDT: $5.46
🪙 Novo saldo ADA: 327.47 ADA
```

### Exemplo 2: Compra com valor específico
```bash
$ python comprar_manual.py --usdt 20
💵 Valor a gastar: $20.00 USDT
🔢 Quantidade calculada: 30.84 ADA
🔔 Confirmar compra? (S/n): S
✅ Compra executada!
```

### Exemplo 3: Compra com quantidade específica
```bash
$ python comprar_manual.py --ada 50
🔢 Quantidade: 50.00 ADA
💵 Valor aproximado: $32.42 USDT
🔔 Confirmar compra? (S/n): S
✅ Compra executada!
```

## Cancelar Compra

Para cancelar durante a confirmação, digite:
- `n` ou `N`
- `nao` ou `não`
- `no`

Ou pressione `Ctrl+C` a qualquer momento.

## Notas Importantes

1. **Ambiente virtual obrigatório**: Sempre ative o `venv` antes de executar
2. **Compra instantânea**: Usa ordem de mercado (MARKET) para execução imediata
3. **Sem stop loss**: Esta é uma compra manual simples, sem proteções automáticas
4. **Fora da estratégia**: Não interfere com o bot automático
5. **Log persistente**: Todas as operações são registradas em `logs/`

## Solução de Problemas

### Erro: "Saldo insuficiente"
- Verifique seu saldo USDT disponível
- Reduza o valor da compra

### Erro: "Quantidade muito baixa"
- Aumente o valor USDT
- Mínimo recomendado: $5.00 USDT

### Erro: "ModuleNotFoundError"
- Ative o ambiente virtual: `source venv/bin/activate`
- Instale dependências: `pip install -r requirements.txt`

## Segurança

- ✅ Usa as mesmas credenciais API do bot principal
- ✅ Confirmação interativa antes de executar
- ✅ Logs detalhados de todas as operações
- ✅ Validação de saldo antes da compra

---

**Desenvolvido para trading manual flexível** 🚀
