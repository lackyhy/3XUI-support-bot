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
