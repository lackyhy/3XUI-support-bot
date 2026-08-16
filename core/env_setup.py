import os
import base64
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet

def ensure_env_file() -> None:
    """
    Checks if .env file exists with all required configuration variables.
    If missing or incomplete, interactively prompts user in terminal to provide them.
    """
    env_file = Path(__file__).resolve().parent.parent / ".env"
    
    bot_token = ""
    admin_id = ""
    encryption_key = ""

    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("BOT_TOKEN="):
                    bot_token = line.split("=", 1)[1].strip()
                elif line.startswith("ADMIN_ID="):
                    admin_id = line.split("=", 1)[1].strip()
                elif line.startswith("ENCRYPTION_KEY="):
                    encryption_key = line.split("=", 1)[1].strip()

    if bot_token and admin_id and encryption_key:
        return

    print("\n" + "=" * 65)
    print("🚀 ПЕРВОНАЧАЛЬНАЯ НАСТРОЙКА BOTA (Конфигурация .env не найдена)")
    print("=" * 65)

    if not bot_token:
        while not bot_token:
            bot_token = input("\n👉 Введите Telegram Bot Token (от @BotFather): ").strip()
            if not bot_token:
                print("❌ Токен бота не может быть пустым!")

    if not admin_id:
        while not admin_id:
            val = input("👉 Введите ваш Telegram Admin ID (число, например 123456789): ").strip()
            if val.isdigit():
                admin_id = val
            else:
                print("❌ Admin ID должен содержать только цифры!")

    if not encryption_key:
        print("\n🔐 **Настройка ключа шифрования Fernet AES-256 (ENCRYPTION_KEY)**")
        print("• Нажмите [ENTER] — автоматически сгенерировать 256-битный ключ.")
        print("• Или введите свою секретную фразу/пароль (~20-25 символов).")
        user_key = input("👉 Ваш выбор (или секретная фраза): ").strip()

        if not user_key:
            encryption_key = Fernet.generate_key().decode('utf-8')
            print(f"✨ Сгенерирован 256-битный Fernet ключ: {encryption_key}")
        else:
            # Convert user phrase into 32-byte URL-safe base64 key
            key_bytes = hashlib.sha256(user_key.encode('utf-8')).digest()
            encryption_key = base64.urlsafe_b64encode(key_bytes).decode('utf-8')
            print(f"✅ Секретная фраза обработана в Fernet AES-256 ключ.")

    env_content = (
        f"BOT_TOKEN={bot_token}\n"
        f"ADMIN_ID={admin_id}\n"
        f"ENCRYPTION_KEY={encryption_key}\n"
    )
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(env_content)

    print("\n✅ Конфигурация .env успешно создана и сохранена!")
    print("=" * 65 + "\n")
