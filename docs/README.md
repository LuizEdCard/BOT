# Trading Bot ADA/XRP

Bot de trading automatizado para acumulação de criptomoedas (ADA/XRP) usando estratégia de degraus de compra e metas de venda.

## Status do Projeto

**DIA 1: INFRAESTRUTURA - ✅ CONCLUÍDO**

- [x] Estrutura de pastas completa
- [x] Sistema de segurança (.gitignore com proteção de secrets)
- [x] Configurações (.env.example, estrategia.json, settings.py)
- [x] Sistema de logging robusto com cores
- [x] Ambiente virtual Python 3.13
- [x] Todas as dependências instaladas
- [x] Testes do logger funcionando

## Estrutura do Projeto

```
trading_bot/
├── config/                    # Configurações
│   ├── .env.example          # Template de variáveis de ambiente
│   ├── estrategia.json       # Degraus e metas de trading
│   └── settings.py           # Configurações centralizadas
├── src/
│   ├── core/                 # Lógica principal
│   ├── comunicacao/          # API e WebSocket
│   ├── persistencia/         # Banco de dados e logs
│   ├── utils/                # Utilitários (logger, etc)
│   └── modelos/              # Classes de dados
├── dados/                    # Banco de dados e backups
├── logs/                     # Logs do sistema
├── tests/                    # Testes
├── .gitignore               # Proteção de secrets
├── requirements.txt         # Dependências Python
└── README.md               # Este arquivo
```

## Instalação

### 1. Pré-requisitos

- Python 3.10 ou superior
- pip (gerenciador de pacotes Python)
- Conta na Binance com API keys

### 2. Configurar Ambiente

```bash
# Clonar/baixar o projeto
cd trading_bot

# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configurar API Keys

```bash
# Copiar template de configuração
cp config/.env.example config/.env

# Editar .env com suas credenciais
nano config/.env
# ou use seu editor preferido
```

**IMPORTANTE:** Configure suas API keys da Binance no arquivo `config/.env`:

```bash
BINANCE_API_KEY=sua_key_aqui
BINANCE_API_SECRET=seu_secret_aqui
AMBIENTE=TESTNET  # Ou PRODUCAO
```

### 4. Segurança da API Binance

Ao criar sua API key na Binance:

✅ **Habilitar:**
- Enable Reading
- Enable Spot & Margin Trading

❌ **DESABILITAR:**
- Enable Withdrawals (por segurança)
- Enable Futures (não usamos alavancagem)

Recomendações:
- Habilitar 2FA na conta
- Restringir API por IP (se possível)
- Usar apenas permissões necessárias

## Testar Instalação

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar teste do logger
python test_logger.py
```

Você deverá ver logs coloridos no terminal e um arquivo criado em `logs/`.

## Estratégia de Trading

### Degraus de Compra (7 níveis)

Compra automaticamente em quedas escalonadas:

| Degrau | Queda % | Quantidade ADA | Valor USD | Intervalo |
|--------|---------|----------------|-----------|-----------|
| 1 | -1.5% | 8 ADA | ~$6.50 | 1.5h |
| 2 | -3.0% | 13 ADA | ~$10.50 | 2h |
| 3 | -5.5% | 20 ADA | ~$16.00 | 3h |
| 4 | -8.5% | 28 ADA | ~$22.00 | 4h |
| 5 | -13% | 38 ADA | ~$30.00 | 8h |
| 6 | -19% | 50 ADA | ~$40.00 | 12h |
| 7 | -26% | 55 ADA | ~$44.00 | 24h |

### Metas de Venda (3 níveis)

Vende em alta para realizar lucros:

| Meta | Lucro % | Vende % | Descrição |
|------|---------|---------|-----------|
| 1 | +6% | 30% | Primeira realização |
| 2 | +11% | 40% | Segunda realização |
| 3 | +18% | 30% | Terceira realização |

### Gestão de Capital

- **Capital Ativo:** 92% para trading
- **Reserva:** 8% para emergências
- **Limite Diário:** $100 máximo de gasto
- **Reinvestimento:** 100% dos lucros

## Próximos Passos

**DIA 2: Banco de Dados**
- [ ] Schema SQL completo
- [ ] Classe Database
- [ ] Logger de texto (historico.txt)
- [ ] Testes CRUD

**DIA 3: Modelos de Dados**
- [ ] Classe Operacao
- [ ] Classe Saldo
- [ ] Funções de cálculo (Decimal)
- [ ] Validadores

**DIA 4-8:** Continuar conforme plano de implementação

## Segurança

⚠️ **NUNCA commite o arquivo `.env`!**

O `.gitignore` já está configurado para proteger:
- Arquivos `.env`
- API keys
- Banco de dados
- Logs
- Dados sensíveis

Antes de cada commit, verifique:

```bash
git status  # Não deve listar .env
git diff --cached  # Verificar mudanças
```

## Logs

Os logs são salvos em:
- **Console:** Logs coloridos em tempo real
- **Arquivo:** `logs/sistema_YYYY-MM-DD.log`

Níveis de log:
- `DEBUG`: Detalhes técnicos
- `INFO`: Operações normais
- `WARNING`: Avisos
- `ERROR`: Erros
- `CRITICAL`: Erros graves

## Configurações

### Arquivo: `config/estrategia.json`

Contém todos os degraus de compra, metas de venda e limites de segurança.

### Arquivo: `config/settings.py`

Classe centralizada que carrega todas as configurações do `.env` e `estrategia.json`.

## Tecnologias

- **Python 3.13**
- **websocket-client:** Streaming de preços
- **requests:** API REST Binance
- **python-dotenv:** Gerenciamento de variáveis de ambiente
- **colorama:** Logs coloridos
- **cryptography:** Assinatura HMAC para API
- **pytest:** Testes automatizados

## Comandos Úteis

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar testes
pytest tests/

# Formatar código
black src/

# Verificar estilo
flake8 src/

# Type checking
mypy src/

# Desativar ambiente virtual
deactivate
```

## Suporte

Para dúvidas ou problemas:
1. Verifique se o `.env` está configurado
2. Verifique se o ambiente virtual está ativo
3. Verifique os logs em `logs/`

## Licença

Este projeto é privado e confidencial.

---

**Desenvolvido com Claude Code**
Versão: 1.0.0
Data: Outubro 2025
