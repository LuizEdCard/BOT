"""
StateManager - Gerenciador de estado operacional do bot em JSON.

Este módulo separa o estado operacional (cooldowns, timestamps) dos dados
transacionais (ordens, que permanecem no banco de dados SQLite).

Autor: Sistema de Trading ADA/USDT
Data: 2025-10-14
"""

import json
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """
    Gerencia o estado operacional do bot usando persistência em JSON.

    O estado é salvo imediatamente a cada alteração para garantir
    consistência mesmo em caso de interrupções (systemd restart, crashes, etc).

    Exemplos de uso:
        state = StateManager('dados/bot_state.json')
        state.set_state('ultima_compra_global_ts', datetime.now().isoformat())
        timestamp = state.get_state('ultima_compra_global_ts')
    """

    def __init__(self, state_file_path: str):
        """
        Inicializa o StateManager com o caminho do arquivo JSON.

        Args:
            state_file_path: Caminho completo para o arquivo JSON de estado
        """
        self.state_file_path = Path(state_file_path)
        self.state: dict = {}

        # Garante que o diretório existe
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Carrega estado existente ou cria novo
        self._load_state()

        logger.info(f"✅ StateManager inicializado: {self.state_file_path}")

    def _load_state(self) -> None:
        """
        Carrega o estado do arquivo JSON.

        Trata casos especiais:
        - Arquivo não existe: cria estado vazio
        - JSON corrompido: cria backup e reinicia estado
        - Permissões: loga erro e continua com estado vazio
        """
        if not self.state_file_path.exists():
            logger.info(f"📄 Arquivo de estado não encontrado. Criando novo: {self.state_file_path}")
            self.state = {}
            self._save_state()
            return

        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                self.state = json.load(f)

            logger.info(f"📖 Estado carregado: {len(self.state)} chaves encontradas")

        except json.JSONDecodeError as e:
            # JSON corrompido - cria backup e reinicia
            backup_path = self.state_file_path.with_suffix('.json.corrupted')
            logger.error(f"❌ JSON corrompido! Criando backup em: {backup_path}")

            try:
                self.state_file_path.rename(backup_path)
            except Exception as backup_error:
                logger.error(f"Erro ao criar backup: {backup_error}")

            self.state = {}
            self._save_state()

        except PermissionError as e:
            logger.error(f"❌ Erro de permissão ao ler estado: {e}")
            self.state = {}

        except Exception as e:
            logger.error(f"❌ Erro inesperado ao carregar estado: {e}")
            self.state = {}

    def _save_state(self) -> None:
        """
        Persiste o estado atual no arquivo JSON.

        Usa escrita atômica (write + rename) para evitar corrupção
        em caso de interrupção durante a escrita.
        """
        try:
            # Escreve em arquivo temporário primeiro
            temp_path = self.state_file_path.with_suffix('.json.tmp')

            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)

            # Rename atômico (sobrescreve o arquivo original)
            temp_path.replace(self.state_file_path)

        except PermissionError as e:
            logger.error(f"❌ Erro de permissão ao salvar estado: {e}")
            raise

        except Exception as e:
            logger.error(f"❌ Erro ao salvar estado: {e}")
            raise

    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Obtém um valor do estado.

        Args:
            key: Chave do estado a recuperar
            default: Valor padrão se a chave não existir

        Returns:
            Valor armazenado ou default se não encontrado

        Exemplo:
            timestamp = state.get_state('ultima_compra_global_ts', default=None)
        """
        value = self.state.get(key, default)

        if value is None and default is not None:
            logger.debug(f"Estado '{key}' não encontrado, usando default: {default}")

        return value

    def set_state(self, key: str, value: Any) -> None:
        """
        Define um valor no estado e persiste imediatamente.

        Args:
            key: Chave do estado
            value: Valor a armazenar (deve ser serializável em JSON)

        Raises:
            TypeError: Se o valor não for serializável em JSON

        Exemplo:
            state.set_state('ultima_compra_global_ts', datetime.now().isoformat())
        """
        # Validação: garante que o valor é serializável
        try:
            json.dumps(value)
        except (TypeError, ValueError) as e:
            logger.error(f"❌ Valor não serializável para chave '{key}': {e}")
            raise TypeError(f"Valor não serializável em JSON: {type(value)}")

        self.state[key] = value
        self._save_state()

        logger.debug(f"💾 Estado salvo: {key} = {value}")

    def delete_state(self, key: str) -> bool:
        """
        Remove uma chave do estado.

        Args:
            key: Chave a remover

        Returns:
            True se a chave foi removida, False se não existia
        """
        if key in self.state:
            del self.state[key]
            self._save_state()
            logger.debug(f"🗑️ Estado removido: {key}")
            return True

        return False

    def clear_state(self) -> None:
        """
        Limpa todo o estado (USE COM CUIDADO!).

        Remove todas as chaves e persiste estado vazio.
        """
        self.state = {}
        self._save_state()
        logger.warning("⚠️ Todo o estado foi limpo!")

    def get_all_state(self) -> dict:
        """
        Retorna uma cópia do estado completo.

        Returns:
            Dicionário com todo o estado atual
        """
        return self.state.copy()

    def __repr__(self) -> str:
        """Representação string do StateManager."""
        return f"StateManager(file={self.state_file_path}, keys={len(self.state)})"
