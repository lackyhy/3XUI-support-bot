from typing import Dict, Any
from core import bot_settings

MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        # Main Menu
        "main_menu_title": "🔐 **3x-ui Server Management Menu**",
        "current_server": "Current server:",
        "choose_action": "Select an action:",
        "btn_active_server": "🖥 Server: {name}",
        "btn_server_status": "📊 Server Status",
        "btn_clients": "👥 Clients",
        "btn_inbounds": "🌐 Inbounds (Connections)",
        "btn_add_client": "➕ Add New Client",
        "btn_search_client": "🔍 Search Client",
        "btn_restart_xray": "⚡ Restart Xray Core",
        "btn_settings": "⚙️ Access & Bot Settings",
        "btn_setup_panel": "⚙️ Connect 3x-ui Panel",
        "btn_main_menu": "🔙 Main Menu",
        "btn_cancel": "❌ Cancel",
        "btn_refresh": "🔄 Refresh",

        # Server Status
        "server_status_title": "📊 **Server Status & System Metrics**",
        "hostname": "💻 Hostname:",
        "xui_ver": "🚀 X-UI Version:",
        "xray_ver": "📡 Xray Version:",
        "server_uptime": "⏳ Server Uptime:",
        "server_load": "📈 System Load:",
        "server_ram": "📋 Server RAM:",
        "server_disk": "💾 Server Disk:",
        "online_clients": "🌐 Clients Online:",
        "tcp_conn": "🔹 TCP Connections:",
        "udp_conn": "🔸 UDP Connections:",
        "server_traffic": "🚦 Network Traffic:",
        "xray_status": "ℹ️ Xray Status:",

        # Clients Hub
        "clients_hub_title": "👥 **Client Management Hub**",
        "all_clients_btn": "🌐 All Clients ({count})",
        "group_btn": "📁 Group: {name} ({count})",
        "no_group_btn": "📂 Without Group ({count})",
        "back_to_hub": "🔙 Back to Categories",
        "clients_list_title": "👥 **Client List ({filter_name})**",
        "page_info": "Page {current} of {total}",

        # Client Profile
        "client_profile_title": "👤 **Client Profile: {email}**",
        "client_uuid": "🆔 UUID / Pass:",
        "client_group": "👥 Group:",
        "client_status": "Status:",
        "status_active": "🟢 Active",
        "status_disabled": "🔴 Disabled",
        "attached_inbounds": "🌐 Attached Inbounds ({count}):",
        "sub_link": "🌐 Subscription URL:",
        "used_traffic": "📊 Used Traffic:",
        "traffic_limit": "📈 Traffic Limit:",
        "unlimited": "♾ Unlimited",
        "expires_at": "📅 Expires:",
        "ip_limit": "📱 IP Limit:",
        "no_limit": "♾ No limit",
        "btn_toggle_client": "🟢/🔴 Toggle Status",
        "btn_edit_client": "✏️ Edit Client",
        "btn_reset_traffic": "🔄 Reset Traffic",
        "btn_delete_client": "🗑 Delete Client",
        "btn_qr_code": "📱 QR Code",
        "btn_back_to_clients": "🔙 Back to Client List",

        # Inbounds
        "inbounds_list_title": "🌐 **Inbound Connections List**",
        "total_inbounds": "Total connections: **{count}**",
        "inbound_card_title": "🌐 **Inbound: {remark}**",
        "node_listen": "🌐 **Node (Listen):**",
        "proto_port": "🛠 **Protocol:**",
        "net_sec": "🌐 **Network / Security:**",
        "target_dest": "🎯 **Target (Dest):**",
        "utls_fp": "🔑 **uTLS (Fingerprint):**",
        "proxy_xver": "⚡ **PROXY Protocol (Xver):**",
        "sni_names": "🌐 **SNI (ServerNames):**",
        "sniffing_info": "🔍 **Sniffing:**",
        "sniff_protocols": "• **Protocols:**",
        "btn_view_inbound_clients": "👥 Inbound Clients",

        # Bot Dashboard
        "menu_title": "🤖 **Bot Settings & Multi-Panel Dashboard**",
        "total_panels": "🖥 **Total Panels:**",
        "panels_status": "📊 **Panels Health:**",
        "active_panel": "🟢 **Active Server:**",
        "bot_proxy": "🌐 **Bot Proxy:**",
        "language": "🗣 **Interface Language:**",
        "btn_export_backup": "📦 Export Backup (credentials.enc)",
        "btn_switch_lang_ru": "🇷🇺 Switch to Russian",
        "btn_switch_lang_en": "🇬🇧 Switch to English",
        "btn_switch_server": "🖥 Change Active Server",
        "lang_switched_en": "✅ Interface language changed to **English**! 🇬🇧",
        "lang_switched_ru": "✅ Язык интерфейса изменен на **Русский**! 🇷🇺",
        "btn_bot_menu": "⚙️ Bot Settings & Dashboard (/menu)",
    },
    "ru": {
        # Главное меню
        "main_menu_title": "🔐 **Главное меню управления 3x-ui**",
        "current_server": "Текущий сервер:",
        "choose_action": "Выберите действие:",
        "btn_active_server": "🖥 Сервер: {name}",
        "btn_server_status": "📊 Статус сервера",
        "btn_clients": "👥 Клиенты",
        "btn_inbounds": "🌐 Инбаунды (Подключения)",
        "btn_add_client": "➕ Добавить нового клиента",
        "btn_search_client": "🔍 Поиск клиента",
        "btn_restart_xray": "⚡ Перезапустить Xray Core",
        "btn_settings": "⚙️ Настройки доступа",
        "btn_setup_panel": "⚙️ Подключить панель 3x-ui",
        "btn_main_menu": "🔙 Главное меню",
        "btn_cancel": "❌ Отмена",
        "btn_refresh": "🔄 Обновить",

        # Статус сервера
        "server_status_title": "📊 **Статус сервера и системы**",
        "hostname": "💻 Имя хоста:",
        "xui_ver": "🚀 Версия X-UI:",
        "xray_ver": "📡 Версия Xray:",
        "server_uptime": "⏳ Время работы сервера:",
        "server_load": "📈 Нагрузка сервера:",
        "server_ram": "📋 ОЗУ сервера:",
        "server_disk": "💾 Диск сервера:",
        "online_clients": "🌐 Клиентов онлайн:",
        "tcp_conn": "🔹 TCP-соединения:",
        "udp_conn": "🔸 UDP-соединения:",
        "server_traffic": "🚦 Сетевой трафик:",
        "xray_status": "ℹ️ Состояние Xray:",

        # Клиенты Hub
        "clients_hub_title": "👥 **Центр управления клиентами**",
        "all_clients_btn": "🌐 Все клиенты ({count})",
        "group_btn": "📁 Группа: {name} ({count})",
        "no_group_btn": "📂 Без группы ({count})",
        "back_to_hub": "🔙 К категориям",
        "clients_list_title": "👥 **Список клиентов ({filter_name})**",
        "page_info": "Страница {current} из {total}",

        # Профиль клиента
        "client_profile_title": "👤 **Профиль клиента: {email}**",
        "client_uuid": "🆔 UUID / Pass:",
        "client_group": "👥 Группа:",
        "client_status": "Статус:",
        "status_active": "🟢 Активен",
        "status_disabled": "🔴 Отключен",
        "attached_inbounds": "🌐 Привязан к инбаундам ({count}):",
        "sub_link": "🌐 Ссылка подписки:",
        "used_traffic": "📊 Использовано:",
        "traffic_limit": "📈 Лимит трафика:",
        "unlimited": "♾ Безлимитно",
        "expires_at": "📅 Истекает:",
        "ip_limit": "📱 Лимит IP:",
        "no_limit": "♾ Без ограничений",
        "btn_toggle_client": "🟢/🔴 Вкл/Выкл",
        "btn_edit_client": "✏️ Редактировать",
        "btn_reset_traffic": "🔄 Сброс трафика",
        "btn_delete_client": "🗑 Удалить клиента",
        "btn_qr_code": "📱 QR-код",
        "btn_back_to_clients": "🔙 К списку клиентов",

        # Инбаунды
        "inbounds_list_title": "🌐 **Список подключений (Inbounds)**",
        "total_inbounds": "Всего подключений: **{count}**",
        "inbound_card_title": "🌐 **Инбаунд: {remark}**",
        "node_listen": "🌐 **Узел (Listen):**",
        "proto_port": "🛠 **Протокол:**",
        "net_sec": "🌐 **Сеть / Защита:**",
        "target_dest": "🎯 **Target (Dest):**",
        "utls_fp": "🔑 **uTLS (Fingerprint):**",
        "proxy_xver": "⚡ **PROXY Protocol (Xver):**",
        "sni_names": "🌐 **SNI (ServerNames):**",
        "sniffing_info": "🔍 **Сниффинг:**",
        "sniff_protocols": "• **Перехват:**",
        "btn_view_inbound_clients": "👥 Клиенты инбаунда",

        # Дашборд бота
        "menu_title": "🤖 **Настройки бота и Мониторинг панелей**",
        "total_panels": "🖥 **Всего панелей:**",
        "panels_status": "📊 **Статус панелей:**",
        "active_panel": "🟢 **Активный сервер:**",
        "bot_proxy": "🌐 **Прокси бота:**",
        "language": "🗣 **Язык интерфейса:**",
        "btn_export_backup": "📦 Экспорт бэкапа (credentials.enc)",
        "btn_switch_lang_ru": "🇷🇺 Переключить на Русский",
        "btn_switch_lang_en": "🇬🇧 Switch to English",
        "btn_switch_server": "🖥 Сменить активный сервер",
        "lang_switched_en": "✅ Interface language changed to **English**! 🇬🇧",
        "lang_switched_ru": "✅ Язык интерфейса изменен на **Русский**! 🇷🇺",
        "btn_bot_menu": "⚙️ Настройки бота и Дашборд (/menu)",
    }
}

def t(key: str, lang: str = None, **kwargs) -> str:
    if not lang:
        lang = bot_settings.get_language()
    lang_dict = MESSAGES.get(lang, MESSAGES["en"])
    text = lang_dict.get(key, MESSAGES["en"].get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text
