from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from core import crypto_storage
from keyboards import inline as keyboards
from states.states import PanelSetupStates, RenamePanelStates
from core.api_client import ThreeXUIClient

router = Router()

def get_main_menu_markup():
    has_creds = crypto_storage.has_credentials()
    active_panel = crypto_storage.get_active_panel()
    name = active_panel.get("name", "Основной сервер") if active_panel else "Без сервера"
    return keyboards.main_menu_kb(has_creds=has_creds, active_panel_name=name)

@router.callback_query(F.data == "setup_panel")
async def start_panel_setup(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PanelSetupStates.waiting_for_host)
    text = (
        "⚙️ **Добавление сервера 3x-ui** (Шаг 1 из 3)\n\n"
        "Введите **URL панели 3x-ui**.\n"
        "*(Имя сервера будет определено автоматически по IP/Домену, и его можно изменить в любой момент)*\n\n"
        "Примеры:\n"
        "• `http://1.2.3.4:2053`\n"
        "• `https://my-panel.domain.com:8441/webpath`"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(), parse_mode="Markdown")
    await callback.answer()

@router.message(PanelSetupStates.waiting_for_host)
async def process_host(message: Message, state: FSMContext):
    host = message.text.strip().rstrip('/')
    if not (host.startswith("http://") or host.startswith("https://")):
        await message.answer(
            "❌ Неверный формат URL. Укажите протокол `http://` или `https://`!\nПопробуйте еще раз:",
            reply_markup=keyboards.cancel_kb(),
            parse_mode="Markdown"
        )
        return

    default_name = crypto_storage.derive_default_panel_name(host)

    await state.update_data(host=host, default_name=default_name)
    await state.set_state(PanelSetupStates.waiting_for_auth_type)
    await message.answer(
        f"⚙️ **Добавление сервера** (`{default_name}`)\n\n"
        "Выберите способ авторизации в панели 3x-ui:\n\n"
        "🔑 **Bearer Token** (Если у вас есть API токен)\n"
        "👤 **Логин и Пароль** (Стандартный вход в панель)",
        reply_markup=keyboards.auth_type_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(PanelSetupStates.waiting_for_auth_type, F.data == "auth_mode_token")
async def process_auth_type_token(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PanelSetupStates.waiting_for_token)
    await callback.message.edit_text(
        "🔑 **Авторизация по Bearer Token** (Шаг 3 из 3)\n\n"
        "Отправьте ваш **Bearer Token** панели:\n"
        "*(Токен будет зашифрован алгоритмом AES-256)*",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(PanelSetupStates.waiting_for_auth_type, F.data == "auth_mode_creds")
async def process_auth_type_creds(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PanelSetupStates.waiting_for_username)
    await callback.message.edit_text(
        "👤 **Авторизация по Логину и Паролю**\n\n"
        "Введите **Логин** администратора панели:",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(PanelSetupStates.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    token = message.text.strip()
    try:
        await message.delete()  # Hide token for privacy
    except Exception:
        pass

    data = await state.get_data()
    host = data.get("host")
    name = data.get("default_name") or crypto_storage.derive_default_panel_name(host)

    status_msg = await message.answer("🔄 **Проверка Bearer Token в панели...**", parse_mode="Markdown")

    client = ThreeXUIClient(host=host, token=token, auth_type="token")
    success, msg = await client.login()
    await client.close()

    if not success:
        await status_msg.edit_text(
            f"❌ **Не удалось авторизоваться по токену!**\n\n"
            f"Причина: `{msg}`\n\n"
            "Пожалуйста, проверьте токен и попробуйте подключить панель заново.",
            reply_markup=get_main_menu_markup(),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    # Add new panel with derived default name
    crypto_storage.add_or_update_panel(
        name=name,
        host=host,
        auth_type="token",
        token=token
    )
    await state.clear()

    await status_msg.edit_text(
        f"✅ **Сервер `{name}` успешно подключен и выбран!**\n\n"
        "Все данные авторизации зашифрованы алгоритмом Fernet (AES-256).\n"
        "Имя сервера определено автоматически по IP/домену. Вы можете изменить его в Настройках.",
        reply_markup=get_main_menu_markup(),
        parse_mode="Markdown"
    )

@router.message(PanelSetupStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if not username:
        await message.answer("❌ Логин не может быть пустым! Введите логин:", reply_markup=keyboards.cancel_kb())
        return

    await state.update_data(username=username)
    await state.set_state(PanelSetupStates.waiting_for_password)
    await message.answer(
        "⚙️ **Авторизация по Логину и Паролю**\n\n"
        "Введите **Пароль** администратора панели:\n"
        "*(Сообщение с паролем будет сразу удалено из чата)*",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )

@router.message(PanelSetupStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    password = message.text.strip()
    try:
        await message.delete()  # Hide password for privacy
    except Exception:
        pass

    data = await state.get_data()
    host = data.get("host")
    username = data.get("username")
    name = data.get("default_name") or crypto_storage.derive_default_panel_name(host)

    status_msg = await message.answer("🔄 **Проверка подключения к 3x-ui...**", parse_mode="Markdown")

    client = ThreeXUIClient(host=host, username=username, password=password, auth_type="credentials")
    success, msg = await client.login()
    await client.close()

    if not success:
        await status_msg.edit_text(
            f"❌ **Не удалось авторизоваться в панели!**\n\n"
            f"Причина: `{msg}`\n\n"
            "Пожалуйста, проверьте данные и попробуйте нажать кнопку настройки заново.",
            reply_markup=get_main_menu_markup(),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    # Add new panel with derived default name
    crypto_storage.add_or_update_panel(
        name=name,
        host=host,
        auth_type="credentials",
        username=username,
        password=password,
        token=client.token
    )
    await state.clear()

    await status_msg.edit_text(
        f"✅ **Сервер `{name}` успешно подключен и выбран!**\n\n"
        "Данные зашифрованы алгоритмом Fernet (AES-256).\n"
        "Имя сервера определено автоматически по IP/домену. Вы можете изменить его в Настройках.",
        reply_markup=get_main_menu_markup(),
        parse_mode="Markdown"
    )

# RENAME ACTIVE SERVER
@router.callback_query(F.data == "rename_panel")
async def cb_rename_panel_start(callback: CallbackQuery, state: FSMContext):
    active_panel = crypto_storage.get_active_panel()
    if not active_panel:
        await callback.answer("Ошибка: Сервер не найден", show_alert=True)
        return

    current_name = active_panel.get("name", "Сервер")
    await state.update_data(panel_id=active_panel.get("id"))
    await state.set_state(RenamePanelStates.waiting_for_new_name)

    await callback.message.edit_text(
        f"✏️ **Изменение названия сервера**\n\n"
        f"Текущее имя: `{current_name}`\n\n"
        "Введите новое пользовательское имя для этого сервера (например: `Финляндия 1`, `Основной VPN`):",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(RenamePanelStates.waiting_for_new_name)
async def process_rename_panel(message: Message, state: FSMContext):
    new_name = message.text.strip()
    if not new_name:
        await message.answer("❌ Имя сервера не может быть пустым. Введите новое имя:", reply_markup=keyboards.cancel_kb())
        return

    data = await state.get_data()
    panel_id = data.get("panel_id")
    await state.clear()

    if crypto_storage.rename_panel(panel_id, new_name):
        await message.answer(
            f"✅ **Сервер успешно переименован в `{new_name}`!**",
            reply_markup=get_main_menu_markup(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❌ Ошибка при переименовании сервера.",
            reply_markup=get_main_menu_markup()
        )

# DOCUMENT IMPORT & BACKUP EXPORT
from aiogram.filters import Command
from states.states import ImportCredentialsStates
import io

async def import_credentials_bytes(message: Message, file_bytes: bytes, key_str: str, state: FSMContext):
    from cryptography.fernet import Fernet
    import base64, hashlib, json, config

    key = key_str.strip()
    payload = None
    derived_fernet_key = None

    # Try 1: Key as URL-safe base64 Fernet key
    try:
        f = Fernet(key.encode('utf-8'))
        decrypted = f.decrypt(file_bytes)
        payload = json.loads(decrypted.decode('utf-8'))
        derived_fernet_key = key
    except Exception:
        pass

    # Try 2: Key as raw user passphrase
    if payload is None:
        try:
            key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
            derived_fernet_key = base64.urlsafe_b64encode(key_bytes).decode('utf-8')
            f = Fernet(derived_fernet_key.encode('utf-8'))
            decrypted = f.decrypt(file_bytes)
            payload = json.loads(decrypted.decode('utf-8'))
        except Exception:
            pass

    if payload is None or not isinstance(payload, dict):
        await message.answer(
            "❌ **Ошибка расшифровки файла `credentials.enc`!**\n\n"
            "Предоставленный ключ не подходит к этому файлу.\n"
            "Пожалуйста, проверьте ключ и отправьте файл или ключ заново.",
            parse_mode="Markdown"
        )
        return

    # Save to data/credentials.enc
    config.CREDENTIALS_FILE.parent.mkdir(exist_ok=True)
    with open(config.CREDENTIALS_FILE, "wb") as f:
        f.write(file_bytes)

    # Update ENCRYPTION_KEY in .env file
    env_file = config.BASE_DIR / ".env"
    if env_file.exists():
        lines = []
        key_found = False
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("ENCRYPTION_KEY="):
                    lines.append(f"ENCRYPTION_KEY={derived_fernet_key}\n")
                    key_found = True
                else:
                    lines.append(line)
        if not key_found:
            lines.append(f"ENCRYPTION_KEY={derived_fernet_key}\n")
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # Update in-memory config & crypto_storage
    config.ENCRYPTION_KEY = derived_fernet_key
    crypto_storage.init_fernet(derived_fernet_key)

    await state.clear()

    panels_count = len(payload.get("panels", [])) if isinstance(payload, dict) else 0
    active_panel = crypto_storage.get_active_panel()
    active_name = active_panel.get("name", "Основной сервер") if active_panel else "—"

    await message.answer(
        f"✅ **Файл `credentials.enc` успешно импортирован!**\n\n"
        f"🔑 Ключ шифрования обновлён и сохранён в `.env`.\n"
        f"🖥 Загружено панелей 3x-ui: **{panels_count}**\n"
        f"🟢 Активный сервер: `{active_name}`",
        reply_markup=get_main_menu_markup(),
        parse_mode="Markdown"
    )

@router.message(F.document)
async def process_document_import(message: Message, state: FSMContext):
    doc = message.document
    filename = doc.file_name or ""
    if not (filename.endswith(".enc") or "credentials" in filename.lower()):
        return

    caption = (message.caption or "").strip()

    # Download file bytes
    bot = message.bot
    file_info = await bot.get_file(doc.file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    if isinstance(file_bytes_io, io.BytesIO):
        file_bytes = file_bytes_io.getvalue()
    else:
        file_bytes = file_bytes_io.read()

    if caption:
        await import_credentials_bytes(message, file_bytes, caption, state)
    else:
        await state.update_data(import_file_bytes=file_bytes)
        await state.set_state(ImportCredentialsStates.waiting_for_key)
        await message.answer(
            "📦 **Получен файл `credentials.enc`!**\n\n"
            "🔑 Пожалуйста, отправьте **ключ шифрования (ENCRYPTION_KEY)** для распаковки этого файла:",
            reply_markup=keyboards.cancel_kb(),
            parse_mode="Markdown"
        )

@router.message(ImportCredentialsStates.waiting_for_key)
async def process_import_key(message: Message, state: FSMContext):
    key = message.text.strip()
    data = await state.get_data()
    file_bytes = data.get("import_file_bytes")
    if not file_bytes:
        await message.answer("❌ Файл не найден. Отправьте `.enc` файл заново.")
        await state.clear()
        return

    await import_credentials_bytes(message, file_bytes, key, state)

@router.message(Command("export"))
@router.message(Command("backup"))
@router.callback_query(F.data == "export_credentials")
async def process_export_credentials(event):
    import config
    from aiogram.types import FSInputFile

    if not config.CREDENTIALS_FILE.exists():
        msg = "❌ Файл зашифрованной базы `data/credentials.enc` еще не создан."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    key_str = config.ENCRYPTION_KEY or "—"
    caption = (
        "📦 **Бэкап зашифрованной базы панелей 3x-ui**\n\n"
        f"🔑 **Ключ шифрования (ENCRYPTION_KEY):**\n`{key_str}`\n\n"
        "ℹ️ *Для восстановления на любом другом боте просто отправьте этот файл боту и вставьте этот ключ в подпись к файлу!*"
    )

    doc = FSInputFile(config.CREDENTIALS_FILE, filename="credentials.enc")
    if isinstance(event, CallbackQuery):
        await event.answer("Отправка бэкапа...")
        await event.message.answer_document(doc, caption=caption, parse_mode="Markdown")
    else:
        await event.answer_document(doc, caption=caption, parse_mode="Markdown")
