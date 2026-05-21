# War Machine - Futures Trading Bot

A futures trading bot for managing Bybit futures accounts via Telegram.

## Tech Stack

- Python 3.10+
- aiogram 3.x (Telegram Bot API)
- ccxt (library for cryptocurrency exchanges)
- python-dotenv (configuration)

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd war-machine

# Install dependencies with Poetry
poetry install

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

```bash
# Launch the bot
poetry run python bot/main.py
```

### Available commands

| Command | Description |
|---------|----------|
| `/start` | Greeting message |
| `/balance` | Show USDT balance |
| `/positions` | Open positions |
| `/ticker <symbol>` | Current price (for example, `/ticker BTCUSDT`) |
| `/buy <symbol> <amount>` | Buy (for example, `/buy BTCUSDT 0.001`) |
| `/sell <symbol> <amount>` | Sell (for example, `/sell BTCUSDT 0.001`) |

### Advanced orders

| Command | Description |
|---------|----------|
| `/sl <symbol> <amount> <stop_price> [limit_price]` | Stop-loss order |
| `/tp <symbol> <amount> <trigger_price> [limit_price]` | Take-profit order |
| `/trailing <symbol> <amount> <distance%> [limit_price]` | Trailing-stop order |
| `/cancel <symbol> <order_id>` | Cancel order |
| `/orders` | Show open orders |

## Project Structure

```
war-machine/
├── bot/
│   ├── main.py          # Entry point
│   ├── handlers/        # Telegram command handlers
│   │   ├── start.py     # Basic commands
│   │   └── orders.py    # Advanced orders (SL, TP, trailing)
│   ├── services/        # Business logic
│   │   ├── bybit_service.py
│   │   └── orders.py    # Order creation service
│   └── utils/           # Utilities
├── config/
│   └── settings.py      # Configuration
└── pyproject.toml
```
