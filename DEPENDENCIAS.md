# 📦 Dependências do Projeto - Trading Bot

## 🎯 Visão Geral

Este documento lista todas as dependências Python necessárias para executar o Trading Bot, incluindo suas funções e versões.

---

## ✅ Dependências Obrigatórias

### 🔌 CORE - APIs e Exchanges

| Pacote | Versão | Descrição | Uso no Projeto |
|--------|--------|-----------|----------------|
| **requests** | 2.31.0 | Cliente HTTP | Requisições para APIs da Binance e KuCoin |
| **websocket-client** | 1.6.4 | Cliente WebSocket | Streaming de preços em tempo real |
| **cryptography** | 41.0.5 | Biblioteca de criptografia | Assinatura HMAC para autenticação nas APIs |

### 📱 TELEGRAM BOT

| Pacote | Versão | Descrição | Uso no Projeto |
|--------|--------|-----------|----------------|
| **python-telegram-bot** | 21.0.1 | Framework para Telegram Bot | Comandos remotos (/pausar, /status, /crash) e relatórios horários |

### ⚙️ CONFIGURAÇÃO E AMBIENTE

| Pacote | Versão | Descrição | Uso no Projeto |
|--------|--------|-----------|----------------|
| **python-dotenv** | 1.0.0 | Carregador de variáveis .env | Carregar API keys e configurações sensíveis |

### 🛠️ UTILIDADES

| Pacote | Versão | Descrição | Uso no Projeto |
|--------|--------|-----------|----------------|
| **python-dateutil** | 2.8.2 | Manipulação de datas | Parsing e cálculos de timestamps |
| **pytz** | 2024.1 | Timezone | Conversão de horários UTC/local |
| **colorama** | 0.4.6 | Cores no terminal | Logs coloridos e formatados |
| **psutil** | 5.9.8 | Monitoramento de sistema | CPU, memória e processos (relatório horário) |

---

## 🧪 Dependências de Desenvolvimento (Opcionais)

| Pacote | Versão | Descrição | Uso no Projeto |
|--------|--------|-----------|----------------|
| **pytest** | 7.4.3 | Framework de testes | Testes unitários e de integração |
| **black** | 23.11.0 | Code formatter | Formatação automática de código Python |
| **flake8** | 6.1.0 | Linter | Análise estática de código |
| **mypy** | 1.7.0 | Type checker | Verificação de tipos estáticos |

---

## 📊 Dependências Opcionais (Comentadas)

### Análise Técnica

```python
# ta==0.11.0          # Indicadores técnicos (RSI, MACD, Bollinger, etc)
# pandas==2.2.0       # Manipulação de dataframes
# numpy==1.26.4       # Operações numéricas avançadas
```

### Visualização

```python
# matplotlib==3.8.3   # Gráficos estáticos
# plotly==5.19.0      # Gráficos interativos
```

---

## 📚 Bibliotecas Built-in (Não Precisam Instalação)

As seguintes bibliotecas fazem parte da biblioteca padrão do Python e **não precisam** ser instaladas:

### Manipulação de Dados
- `json` - Parsing JSON
- `sqlite3` - Banco de dados SQLite
- `decimal` - Aritmética decimal precisa
- `collections` - Estruturas de dados (deque, defaultdict)

### Sistema
- `os` - Operações do sistema operacional
- `sys` - Parâmetros e funções do sistema
- `pathlib` - Manipulação de caminhos
- `shutil` - Operações de alto nível em arquivos

### Concorrência
- `threading` - Threads e concorrência
- `queue` - Filas thread-safe

### Utilitários
- `time` - Tempo e sleep
- `datetime` - Datas e horários
- `logging` - Sistema de logs
- `hashlib` - Hashes criptográficos
- `hmac` - HMAC para autenticação
- `urllib` - Parsing de URLs
- `contextlib` - Context managers
- `functools` - Programação funcional
- `typing` - Type hints
- `abc` - Classes abstratas

---

## 🚀 Instalação

### Instalação Completa (Produção)

```bash
pip install -r requirements.txt
```

### Instalação Limpa (Remover Pacotes Antigos)

```bash
pip freeze | xargs pip uninstall -y
pip install -r requirements.txt
```

### Instalação com Ferramentas de Desenvolvimento

```bash
pip install -r requirements.txt
pip install pytest black flake8 mypy
```

### Instalação em Ambiente Virtual (Recomendado)

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

---

## 🔍 Verificação de Dependências

### Verificar Pacotes Instalados

```bash
pip list
```

### Verificar Conflitos

```bash
pip check
```

### Verificar Atualizações Disponíveis

```bash
pip list --outdated
```

### Atualizar Pacote Específico

```bash
pip install --upgrade <package>
```

---

## 📋 Mapeamento: Dependência → Código

### requests (2.31.0)

**Arquivos**:
- `src/exchange/binance_api.py`
- `src/exchange/kucoin_api.py`

**Uso**:
```python
import requests

response = requests.get(url, headers=headers)
response = requests.post(url, json=data, headers=headers)
```

### python-telegram-bot (21.0.1)

**Arquivos**:
- `src/telegram_bot.py`
- `manager.py`

**Uso**:
```python
from telegram import Update, InlineKeyboardButton
from telegram.ext import Application, CommandHandler

application = Application.builder().token(token).build()
```

### psutil (5.9.8)

**Arquivos**:
- `manager.py`

**Uso**:
```python
import psutil

cpu_percent = psutil.cpu_percent(interval=1)
memoria = psutil.virtual_memory()
```

### websocket-client (1.6.4)

**Arquivos**:
- `src/exchange/binance_api.py` (streaming de preços)

**Uso**:
```python
import websocket

ws = websocket.WebSocketApp(url, on_message=handler)
```

### cryptography (41.0.5)

**Arquivos**:
- `src/exchange/binance_api.py`
- `src/exchange/kucoin_api.py`

**Uso**:
```python
import hmac
import hashlib

signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
```

### python-dotenv (1.0.0)

**Arquivos**:
- `manager.py`

**Uso**:
```python
from dotenv import load_dotenv
import os

load_dotenv('configs/.env')
api_key = os.getenv('BINANCE_API_KEY')
```

### colorama (0.4.6)

**Arquivos**:
- `src/utils/logger.py`

**Uso**:
```python
from colorama import Fore, Style

print(f"{Fore.GREEN}✅ Sucesso{Style.RESET_ALL}")
```

---

## 🔧 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'X'"

**Solução**:
```bash
pip install -r requirements.txt
```

### Erro: "pip: command not found"

**Solução**:
```bash
# Instalar pip
python3 -m ensurepip --upgrade
```

### Erro: Conflito de Versões

**Solução**:
```bash
# Desinstalar tudo e reinstalar
pip freeze | xargs pip uninstall -y
pip install -r requirements.txt
```

### Erro: Permission Denied

**Solução**:
```bash
# Usar --user ou ambiente virtual
pip install --user -r requirements.txt

# OU criar ambiente virtual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📊 Tamanho das Dependências

| Pacote | Tamanho Aproximado |
|--------|-------------------|
| requests | ~200 KB |
| python-telegram-bot | ~1.5 MB |
| websocket-client | ~100 KB |
| cryptography | ~3 MB |
| psutil | ~500 KB |
| python-dotenv | ~30 KB |
| colorama | ~25 KB |
| pytz | ~500 KB |
| python-dateutil | ~300 KB |
| **TOTAL** | **~6 MB** |

---

## 🔐 Dependências de Segurança

### Pacotes Críticos para Segurança

1. **cryptography** - Assinatura HMAC para APIs
2. **python-dotenv** - Proteção de credenciais
3. **requests** - Comunicação HTTPS

### Boas Práticas

✅ **Fazer**:
- Manter dependências atualizadas
- Usar `pip check` regularmente
- Revisar vulnerabilidades conhecidas
- Usar ambiente virtual

❌ **Não Fazer**:
- Committar o arquivo `.env`
- Usar versões desatualizadas
- Instalar pacotes sem verificar fonte

---

## 📅 Última Atualização

**Data**: 2025-10-18
**Versão do Python**: 3.10+
**Total de Dependências Obrigatórias**: 9
**Total de Dependências Opcionais**: 8

---

## 🔗 Links Úteis

- [requests Documentation](https://requests.readthedocs.io/)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [psutil Documentation](https://psutil.readthedocs.io/)
- [PyPI - Python Package Index](https://pypi.org/)
- [PEP 508 - Dependency specification](https://peps.python.org/pep-0508/)
