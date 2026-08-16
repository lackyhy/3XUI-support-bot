import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in environment or .env file!")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
CREDENTIALS_FILE = DATA_DIR / "credentials.enc"
