from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from core import crypto_storage
from keyboards import inline as keyboards

router = Router()

from core import bot_settings
from core.i18n import t

def get_main_menu_markup():
    has_creds = crypto_storage.has_credentials()
    active_panel = crypto_storage.get_active_panel()
    name = active_panel.get("name", "Main Server") if active_panel else "No Server"
    lang = bot_settings.get_language()
    return keyboards.main_menu_kb(has_creds=has_creds, active_panel_name=name, lang=lang)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    has_creds = crypto_storage.has_credentials()
    active_panel = crypto_storage.get_active_panel()
    lang = bot_settings.get_language()
    
    if lang == "en":
        text = "🔐 **3x-ui Bot Management Panel**\n\nWelcome, Administrator!\n"
        if has_creds and active_panel:
            panel_name = active_panel.get("name", "Server")
            text += f"Active server: **{panel_name}**\nSelect a section from the menu below:"
        else:
            text += "❌ **No panel credentials configured yet.**\nClick the button below to connect your first panel."
    else:
        text = "🔐 **Панель управления 3x-ui Bot**\n\nПриветствую, Администратор!\n"
        if has_creds and active_panel:
            panel_name = active_panel.get("name", "Сервер")
            text += f"Активный сервер: **{panel_name}**\nВыберите нужный раздел в меню ниже:"
        else:
            text += "❌ **Данные панелей еще не заданы.**\nНажмите кнопку ниже, чтобы добавить первую панель."

    await message.answer(
        text,
        reply_markup=get_main_menu_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_main")
async def cb_menu_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb_menu_select_panel(callback)

# MULTI-PANEL SWITCHING MENU
@router.callback_query(F.data == "menu_select_panel")
async def cb_menu_select_panel(callback: CallbackQuery):
    lang = bot_settings.get_language()
    panels = crypto_storage.get_panels()
    active_panel = crypto_storage.get_active_panel()
    active_id = active_panel.get("id") if active_panel else None

    title = t("panels_list_title", lang)
    select_lbl = t("select_server_to_switch", lang)

    text = f"{title}\n\n{select_lbl}"
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.panels_list_kb(panels, active_id, lang=lang),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise e
    await callback.answer()

@router.callback_query(F.data.startswith("switch_panel_"))
async def cb_switch_panel(callback: CallbackQuery):
    panel_id = callback.data.replace("switch_panel_", "")
    success = crypto_storage.set_active_panel(panel_id)
    
    if success:
        active_panel = crypto_storage.get_active_panel()
        p_name = active_panel.get("name", "Сервер")
        await callback.answer(f"Переключено на сервер {p_name}!")
        await callback.message.edit_text(
            f"✅ **Управление переключено на сервер `{p_name}`!**",
            reply_markup=get_main_menu_markup(),
            parse_mode="Markdown"
        )
    else:
        await callback.answer("Ошибка переключения сервера", show_alert=True)

@router.callback_query(F.data == "menu_toggle_panels")
async def cb_menu_toggle_panels(callback: CallbackQuery):
    lang = bot_settings.get_language()
    panels = crypto_storage.get_panels()

    text = (
        "👁 **Enable / Disable Servers in Statistics**\n\n"
        "Click a server to toggle its visibility in global statistics:" if lang == "en" else "👁 **Включение / Отключение серверов в статистике**\n\n"
        "Нажмите на сервер, чтобы включить или отключить его учет в общей статистике:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.toggle_panels_kb(panels, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_delete_panel")
async def cb_menu_delete_panel(callback: CallbackQuery):
    panels = crypto_storage.get_panels()
    if not panels:
        await callback.answer("Нет серверов для удаления", show_alert=True)
        return

    await callback.message.edit_text(
        "🗑 **Удаление сервера из бота**\n\nВыберите сервер, который хотите удалить:",
        reply_markup=keyboards.delete_panels_kb(panels),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("do_delete_panel_"))
async def cb_do_delete_panel(callback: CallbackQuery):
    panel_id = callback.data.replace("do_delete_panel_", "")
    success = crypto_storage.delete_panel(panel_id)

    if success:
        await callback.answer("Сервер удален!")
        has_creds = crypto_storage.has_credentials()
        await callback.message.edit_text(
            "✅ **Сервер успешно удален из списка!**",
            reply_markup=get_main_menu_markup(),
            parse_mode="Markdown"
        )
    else:
        await callback.answer("Ошибка при удалении сервера", show_alert=True)

@router.callback_query(F.data == "menu_settings")
async def cb_menu_settings(callback: CallbackQuery):
    creds = crypto_storage.load_credentials()
    if not creds:
        await callback.message.edit_text(
            "❌ **Данные панели не заданы.**",
            reply_markup=keyboards.main_menu_kb(has_creds=False),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    panel_name = creds.get("name", "Основной сервер")
    host = creds.get("host", "Не задан")
    auth_type = creds.get("auth_type", "token" if creds.get("token") else "credentials")
    
    if auth_type == "token":
        auth_info = f"🔑 **Тип авторизации:** `Bearer Token`\n🔒 **Токен:** `••••••••` (AES-256)\n"
    else:
        username = creds.get("username", "Не задан")
        auth_info = f"🔑 **Тип авторизации:** `Логин / Пароль`\n👤 **Логин:** `{username}`\n🔒 **Пароль:** `••••••••` (AES-256)\n"

    text = (
        "⚙️ **Настройки активного сервера**\n\n"
        f"🖥 **Имя сервера:** `{panel_name}`\n"
        f"🌐 **Адрес панели:** `{host}`\n"
        f"{auth_info}"
        f"📂 **Файл хранилища:** `data/credentials.enc`\n\n"
        "Вы можете изменить параметры активного сервера или сбросить всё."
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.settings_menu_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "delete_credentials")
async def cb_delete_credentials(callback: CallbackQuery):
    crypto_storage.delete_credentials()
    await callback.message.edit_text(
        "🗑 **Зашифрованное хранилище серверов очищено.**\n\nДля работы требуется заново подключить панель.",
        reply_markup=keyboards.main_menu_kb(has_creds=False),
        parse_mode="Markdown"
    )
    await callback.answer("Все серверы удалены!")

@router.callback_query(F.data == "cancel_action")
async def cb_cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ **Действие отменено.**",
        reply_markup=get_main_menu_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()
