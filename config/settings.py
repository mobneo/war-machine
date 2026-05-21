import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    bybit_api_key = os.getenv("BYBIT_API_KEY")
    bybit_secret_key = os.getenv("BYBIT_SECRET_KEY")
    bybit_testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"


settings = Settings()
