The repository is a Python automated trading bot (ADA/USDT, designed for Binance and KuCoin adapters).

Key goals for an AI assistant working here:
- Understand where runtime config lives: `configs/` and `config/`-style settings are loaded via `src/core/*` and `src/core/bot_trading.py` uses a `settings` module. Check `configs/*.json` and `config/settings.py` (or `src/config` if present).
- The main orchestrator for multiple bots is `manager.py` (spawns threads per bot using per-bot JSON in `configs/`). Single-bot entry point is `src/core/bot_trading.py`.

Important files and directories to reference:
- `manager.py` — launcher that reads `configs/config.json` and starts bot threads.
- `src/core/bot_trading.py` — primary trading logic: SMA reference, degraus (buy-steps), metas (sell targets), state management, buy/sell execution and safety checks.
- `src/exchange/` — exchange-specific adapters (e.g. `binance_api.py`, `kucoin_api.py`). Follow these to understand API method names used by the bot (`get_preco_atual`, `place_ordem_compra_market`, `get_info_conta`, `check_connection`, `get_historico_ordens`).
- `src/persistencia/` — database, state manager and backup logic. State is persisted in `dados/bot_state.json` by default.
- `src/utils/logger.py` — custom logger with structured helper methods used across the codebase (e.g. `logger.operacao_compra`, `logger.erro_api`, `panel_logger`). See and reuse these helpers when modifying logging behavior.
- `docs/README.md` — high-level architecture, install/test commands and strategy description; contains many explicit commands we should keep consistent with (virtualenv, pytest, requirements).

Developer workflows and commands (discoverable in repo):
- Setup: create and activate virtualenv, then `pip install -r requirements.txt` (see `docs/README.md`). Python 3.10+ is expected.
- Run single bot locally for debugging: edit a bot config in `configs/` and run `python src/core/bot_trading.py` or use `manager.py` to start multiple bots (the repo contains a `manager.py` launcher).
- Tests: `pytest tests/` (project already includes multiple tests; unit tests assume local venv and no real API credentials). Use `tests/*` to find examples of mocks and conventions.
- Formatting / linting: `black src/`, `flake8 src/`, `mypy src/` (see `requirements.txt`).

Project-specific conventions and patterns:
- Config sources: code expects a `settings` object (imported as `from config.settings import settings` or from `src/config`) and per-bot JSON config files under `configs/`. When changing config keys, update both `configs/*.json` and any code reading `settings`.
- Exchange adapter interface: treat `src/exchange/base.py` as the contract — methods names used in `bot_trading.py` must be implemented in adapters. When adding a new exchange adapter, match method names used by the bot.
- State & cooldowns: cooldowns and persistent flags live in `StateManager` under `src/persistencia/state_manager.py`. Prefer updating state through the StateManager rather than writing directly to `dados/bot_state.json`.
- Decimal/rounding rules: the code uses `decimal.Decimal` extensively and enforces step rounding (e.g., ADA step 0.1). Preserve Decimal math and rounding when editing calculations.
- Logging: use `get_loggers()` and the custom logger methods (`logger.operacao_compra`, `logger.operacao_venda`, `logger.erro_api`, `panel_logger.info(...)`) to keep consistent output and formatting.

Integration points and external dependencies:
- Exchanges: Binance and KuCoin adapters in `src/exchange/*`. They call external HTTP/WebSocket APIs and sign requests (HMAC). Do not attempt live calls in tests — mock `ExchangeAPI` methods.
- Environment: API keys are read from `.env` via `python-dotenv`. Never hard-code credentials in code or commit `.env`.
- Persistence: uses a local file-based DB and backups under `dados/` (see `src/persistencia/*`). Backups and imports are implemented (e.g., `importar_historico` flows).

Quick examples (copy/paste safe references):
- To locate where a buy-market order is placed: search for `place_ordem_compra_market` (defined in `src/exchange/*` and called from `TradingBot.executar_compra`).
- To change SMA timing: edit `TradingBot.atualizar_sma()` or `config['TAMANHO_BUFFER_PRECOS']` in `configs/`.
- To add a new safety rule for minimum capital, update `src/core/gestao_capital.py` and follow calls from `TradingBot.executar_compra` and `run()`.

Notes for AI edits:
- Keep changes minimal and localized. Maintain the adapter contract and StateManager usage.
- Preserve Decimal arithmetic and custom logger calls.
- Update `docs/README.md` and `configs/*.json` when changing runtime behavior or keys so maintainers can run the system with the same instructions.
- For tests, follow existing patterns in `tests/` — they assume unit-level logic and often mock exchange calls.

If anything in this file is unclear or you need examples of a specific change (e.g., adding an adapter, changing the buy/sell logic, or updating config keys), ask for the targeted area and I'll provide a short, concrete code plan and example edits.
