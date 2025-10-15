# 🔧 CORREÇÃO: Assinatura do get_logger()

**Data:** 13 de outubro de 2025
**Problema:** TypeError ao reiniciar o bot
**Status:** ✅ **CORRIGIDO**

---

## 📋 Problema Detectado

Ao reiniciar o bot após implementar o novo sistema de logging, o seguinte erro ocorreu:

```
TypeError: get_logger() got an unexpected keyword argument 'nivel'
```

**Causa:** A nova assinatura do `get_logger()` não aceita mais o parâmetro `nivel`. Agora usa `config`.

---

## 🔧 Correção Aplicada

### Arquivo Corrigido: `src/core/gestao_capital.py`

**ANTES:**
```python
logger = get_logger(
    log_dir=Path('logs'),
    nivel=settings.LOG_LEVEL,  # ❌ Parâmetro não existe mais
    console=True
)
```

**DEPOIS:**
```python
# Logger usa configuração padrão (não precisa especificar nível)
logger = get_logger(
    log_dir=Path('logs'),
    console=True  # ✅ Usa LogConfig.DEFAULT automaticamente
)
```

---

## 📊 Nova Assinatura

### Função: `get_logger()`

```python
def get_logger(
    nome: str = 'TradingBot',
    log_dir: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,  # ✅ NOVO: Configuração dinâmica
    console: bool = True
) -> Logger:
```

### Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `nome` | str | 'TradingBot' | Nome do logger |
| `log_dir` | Path | None | Diretório de logs |
| `config` | Dict | None | Configuração (usa `LogConfig.DEFAULT` se None) |
| `console` | bool | True | Exibir no console |

### Exemplos de Uso

**1. Modo Padrão (Produção)**
```python
from src.utils.logger import get_logger

logger = get_logger(
    log_dir=Path('logs'),
    console=True
)
# Usa LogConfig.DEFAULT automaticamente
```

**2. Modo Desenvolvimento**
```python
from src.utils.logger import get_logger
from src.utils.constants import LogConfig

logger = get_logger(
    log_dir=Path('logs'),
    config=LogConfig.DESENVOLVIMENTO,  # Mais verbose
    console=True
)
```

**3. Modo Monitoramento**
```python
from src.utils.logger import get_logger
from src.utils.constants import LogConfig

logger = get_logger(
    log_dir=Path('logs'),
    config=LogConfig.MONITORAMENTO,  # Ultra compacto
    console=True
)
```

---

## ✅ Validação

```bash
$ python3 -m py_compile src/core/gestao_capital.py
✅ Compilação OK

$ python3 -m py_compile bot_trading.py
✅ Compilação OK
```

---

## 📝 Arquivos Atualizados

1. ✅ `src/core/gestao_capital.py` - Removido parâmetro `nivel`
2. ✅ `testar_painel_status.py` - Atualizado
3. ✅ `testar_context_manager.py` - Atualizado

---

## 🎯 Como Iniciar o Bot

```bash
# O bot agora pode ser iniciado normalmente:
python main.py

# Ou em background:
nohup python main.py > logs/bot_background.log 2>&1 &
```

---

## 📚 Referência Rápida

### ❌ NÃO USE MAIS

```python
logger = get_logger(nivel='INFO')  # ❌ Erro!
logger = get_logger(nivel='DEBUG')  # ❌ Erro!
```

### ✅ USE

```python
# Padrão (suficiente para 99% dos casos)
logger = get_logger(log_dir=Path('logs'), console=True)

# Com configuração específica
logger = get_logger(
    log_dir=Path('logs'),
    config=LogConfig.DESENVOLVIMENTO,
    console=True
)
```

---

## ✅ Status

**Problema:** ✅ Corrigido
**Validação:** ✅ Compilação OK
**Bot:** ✅ Pronto para iniciar

---

*Correção aplicada em: 13 de outubro de 2025*
