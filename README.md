# War Machine - Futures Trading Bot

A futures trading bot for managing Bybit futures accounts via Telegram.

## Tech Stack

- Python 3.12+
- aiogram 3.x (Telegram Bot API)
- ccxt (library for cryptocurrency exchanges)
- python-dotenv (configuration)

## Installation

### With Docker (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd war-machine

# Create a .env file based on .env.example
cp .env.example .env

# Build and run with Docker Compose
docker compose up -d
# or: make run
```

### With Poetry

```bash
# Clone the repository
git clone <repo-url>
cd war-machine

# Install dependencies with Poetry
poetry install
# or: make install

# Create a .env file based on .env.example
cp .env.example .env
```

## Configuration

In the `.env` file, specify:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_SECRET_KEY=your_bybit_secret_key_here
BYBIT_TESTNET=true  # false for mainnet
```

## Usage

### With Docker

```bash
# Start the bot
docker compose up -d
# or: make docker-start

# View logs
docker compose logs -f
# or: make docker-logs

# Stop the bot
docker compose down
```

### With Poetry

```bash
# Launch the bot
poetry run python bot/main.py
# or: make run
```

### Available Commands

#### Basic Commands

| Command | Description |
|---------|----------|
| `/start` | Greeting message |
| `/commands` | Show all available commands |
| `/balance` | Show USDT balance |
| `/config` | Show balance, PnL & ROE |
| `/ticker <symbol>` | Asset price (e.g., `/ticker BTCUSDT`) |

#### Trading

| Command | Description |
|---------|----------|
| `/buy <symbol> <amount>` | Buy (e.g., `/buy BTCUSDT 0.001`) |
| `/sell <symbol> <amount>` | Sell (e.g., `/sell BTCUSDT 0.001`) |
| `/trading <symbol> <side>` | Open position based on strategy (`long` or `short`) |

#### Positions

| Command | Description |
|---------|----------|
| `/positions` | Show all open positions |
| `/positions long` | Show only long positions |
| `/positions short` | Show only short positions |
| `/positions profit` | Show only profitable positions |
| `/positions loss` | Show only loss positions |
| `/positions <symbol>` | Show positions for specific symbol |

#### Close Positions

| Command | Description |
|---------|----------|
| `/close all` | Close all positions |
| `/close long` | Close all long positions |
| `/close short` | Close all short positions |
| `/close profit` | Close all profitable positions |
| `/close loss` | Close all loss positions |
| `/close <symbol>` | Close specific position |

#### Orders

| Command | Description |
|---------|----------|
| `/orders` | Show all orders |
| `/orders open` | Show only open orders |
| `/orders filled` | Show only filled orders |
| `/orders cancelled` | Show only cancelled orders |
| `/orders active` | Show orders for symbols with active positions |
| `/orders <symbol>` | Show orders for specific symbol |

#### Advanced Orders

| Command | Description |
|---------|----------|
| `/sl <symbol> <amount> <stop_price> [limit_price]` | Stop-loss order |
| `/tp <symbol> <amount> <trigger_price> [limit_price]` | Take-profit order |
| `/trailing <symbol> <amount> <distance%> [limit_price]` | Trailing-stop order |
| `/cancel <symbol> <order_id>` | Cancel specific order |

#### Strategy Configuration

| Command | Description |
|---------|----------|
| `/strategy` | Show strategy configurations |
| `/strategy <symbol>` | Show config for symbol |
| `/strategy <symbol> <risk> <tp> <sl> <leverage>` | Set configuration |
| `/global_strategy` | Show/edit global strategy defaults |

#### Order Management

| Command | Description |
|---------|----------|
| `/cancel_symbol <symbol>` | Cancel all orders for a symbol |
| `/cancel_inactive` | Cancel orders for symbols without positions |

### Advanced Features

#### Strategy Configuration

The bot supports configurable trading strategies per symbol with:

- **Risk percentage** - Position size relative to balance
- **Take Profit (TP)** - Profit target percentage (supports multiple TP levels)
- **Stop Loss (SL)** - Loss limit with optional trailing stop
- **Leverage** - Custom leverage for each symbol

Set strategy for a symbol:
```bash
/strategy BTCUSDT 1 2 1 5
```
This sets 1% risk, 2% TP, 1% SL, 5x leverage for BTCUSDT.

Global defaults can be configured with `/global_strategy`.

### Makefile Commands

| Command | Description |
|---------|----------|
| `make docker-start` | Build and start with Docker Compose |
| `make docker-build` | Build Docker images |
| `make docker-up` | Start Docker Compose |
| `make docker-down` | Stop Docker Compose |
| `make docker-logs` | View Docker logs (follow mode) |
| `make docker-rebuild` | Rebuild and start |
| `make docker-clean` | Stop and remove volumes |
| `make run` | Run with Poetry |
| `make install` | Install dependencies with Poetry |

## Project Structure

```
war-machine/
├── bot/
│   ├── main.py          # Entry point
│   ├── handlers/        # Telegram command handlers
│   │   ├── start.py     # Basic commands (start, balance, ticker, buy, sell)
│   │   ├── commands.py  # Command listing
│   │   ├── orders.py    # Advanced orders (SL, TP, trailing, cancel)
│   │   ├── positions.py # Position management and closing
│   │   └── strategy.py  # Strategy configuration
│   ├── services/        # Business logic
│   │   ├── bybit_service.py
│   │   └── strategy_service.py
│   └── utils/           # Utilities
├── config/
│   ├── settings.py      # Configuration
│   └── strategy.py      # Strategy configuration store
├── Dockerfile           # Docker configuration
├── compose.yaml         # Docker Compose configuration
└── pyproject.toml
```
