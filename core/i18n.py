from typing import Dict, Any
from core import bot_settings

MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "menu_title": "🤖 **Bot Settings & Multi-Panel Dashboard**",
        "total_panels": "🖥 **Total Panels:**",
        "panels_status": "📊 **Panels Health:**",
        "active_panel": "🟢 **Active Server:**",
        "bot_proxy": "🌐 **Bot Proxy:**",
        "language": "🗣 **Interface Language:**",
        "panels_list_title": "📋 **Registered Panels Health:**",
        "btn_export_backup": "📦 Export Backup (credentials.enc)",
        "btn_switch_lang_ru": "🇷🇺 Switch to Russian (Русский)",
        "btn_switch_lang_en": "🇬🇧 Switch to English",
        "btn_switch_server": "🖥 Change Active Server",
        "btn_main_menu": "🔙 Main Menu",
        "lang_switched_en": "✅ Interface language changed to **English**! 🇬🇧",
        "lang_switched_ru": "✅ Язык интерфейса изменен на **Русский**! 🇷🇺",
        "btn_server_status": "📊 Server Status",
        "btn_clients": "👥 Clients",
        "btn_inbounds": "🌐 Inbounds (Connections)",
        "btn_add_client": "➕ Add New Client",
        "btn_search_client": "🔍 Search Client",
        "btn_restart_xray": "⚡ Restart Xray Core",
        "btn_settings": "⚙️ Access & Bot Settings",
        "btn_bot_menu": "⚙️ Bot Settings & Dashboard (/menu)",
    },
    "ru": {
        "menu_title": "🤖 **Настройки бота и Мониторинг панелей**",
        "total_panels": "🖥 **Всего панелей:**",
        "panels_status": "📊 **Статус панелей:**",
        "active_panel": "🟢 **Активный сервер:**",
        "bot_proxy": "🌐 **Прокси бота:**",
        "language": "🗣 **Язык интерфейса:**",
        "panels_list_title": "📋 **Состояние подключенных панелей:**",
        "btn_export_backup": "📦 Экспорт бэкапа (credentials.enc)",
        "btn_switch_lang_ru": "🇷🇺 Переключить на Русский",
        "btn_switch_lang_en": "🇬🇧 Switch to English",
        "btn_switch_server": "🖥 Сменить активный сервер",
        "btn_main_menu": "🔙 Главное меню",
        "lang_switched_en": "✅ Interface language changed to **English**! 🇬🇧",
        "lang_switched_ru": "✅ Язык интерфейса изменен на **Русский**! 🇷🇺",
        "btn_server_status": "📊 Статус сервера",
        "btn_clients": "👥 Клиенты",
        "btn_inbounds": "🌐 Инбаунды (Подключения)",
        "btn_add_client": "➕ Добавить нового клиента",
        "btn_search_client": "🔍 Поиск клиента",
        "btn_restart_xray": "⚡ Перезапустить Xray Core",
        "btn_settings": "⚙️ Настройки доступа и бота",
        "btn_bot_menu": "⚙️ Настройки бота и Панели (/menu)",
    }
}

def t(key: str, lang: str = None) -> str:
    if not lang:
        lang = bot_settings.get_language()
    lang_dict = MESSAGES.get(lang, MESSAGES["en"])
    return lang_dict.get(key, MESSAGES["en"].get(key, key))
