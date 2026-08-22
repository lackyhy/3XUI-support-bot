from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from x_ui.core.i18n import t

def remna_main_menu_kb(active_panel_name: str = "Server", lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = [
        [
            InlineKeyboardButton(text="📊 Dashboard" if cur_lang == "en" else "📊 Панель управления", callback_data="remna_menu_dashboard")
        ],
        [
            InlineKeyboardButton(text="👥 Users" if cur_lang == "en" else "👥 Пользователи", callback_data="remna_menu_users"),
            InlineKeyboardButton(text="📡 Nodes" if cur_lang == "en" else "📡 Ноды", callback_data="remna_menu_nodes")
        ],
        [
            InlineKeyboardButton(text="📁 Config Profiles" if cur_lang == "en" else "📁 Профили", callback_data="remna_menu_profiles"),
            InlineKeyboardButton(text="🖥 Hosts" if cur_lang == "en" else "🖥 Хосты", callback_data="remna_menu_hosts")
        ],
        [
            InlineKeyboardButton(text="🎛 Sub Panels" if cur_lang == "en" else "🎛 Панели подписок", callback_data="remna_menu_panels")
        ],
        [
            InlineKeyboardButton(text=t("btn_active_server", cur_lang, name=active_panel_name), callback_data="menu_select_panel")
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings & Info" if cur_lang == "en" else "⚙️ Настройки и инфо", callback_data="remna_menu_settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def remna_settings_kb(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = [
        [
            InlineKeyboardButton(text=t("btn_change_lang", cur_lang), callback_data="menu_toggle_lang"),
            InlineKeyboardButton(text="🖥 " + (t("btn_active_server", cur_lang, name="").split(":")[0].strip()), callback_data="menu_select_panel")
        ],
        [
            InlineKeyboardButton(text="✏️ Rename Server" if cur_lang == "en" else "✏️ Переименовать сервер", callback_data="rename_panel"),
            InlineKeyboardButton(text="🗑 Delete Server" if cur_lang == "en" else "🗑 Удалить этот сервер", callback_data="menu_delete_panel")
        ],
        [
            InlineKeyboardButton(text=t("btn_main_menu", cur_lang), callback_data="menu_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_kb(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="remna_cancel")]
    ])

def users_list_kb(users: List[Dict[str, Any]], page: int = 0, has_prev: bool = False, has_next: bool = False, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = []
    
    # User buttons
    for u in users:
        u_id = u.get("id")
        username = u.get("username", "Unknown")
        status = u.get("status", "ACTIVE")
        status_icon = "🟢" if status == "ACTIVE" else ("🔴" if status == "DISABLED" else "⚠️")
        buttons.append([InlineKeyboardButton(text=f"{status_icon} {username}", callback_data=f"remna_user_view_{u_id}")])

    # Navigation buttons
    nav_row = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️ Prev" if cur_lang == "en" else "⬅️ Пред", callback_data=f"remna_users_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"Page {page+1}" if cur_lang == "en" else f"Стр. {page+1}", callback_data="noop"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="Next ➡️" if cur_lang == "en" else "След ➡️", callback_data=f"remna_users_page_{page+1}"))
    buttons.append(nav_row)

    # Actions row
    buttons.append([
        InlineKeyboardButton(text="➕ Create" if cur_lang == "en" else "➕ Создать", callback_data="remna_user_create"),
        InlineKeyboardButton(text="🔍 Search" if cur_lang == "en" else "🔍 Поиск", callback_data="remna_user_search")
    ])
    
    buttons.append([InlineKeyboardButton(text=t("btn_main_menu", cur_lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def user_detail_kb(user_id: int, status: str, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = []

    toggle_txt = "🔴 Disable" if status == "ACTIVE" else "🟢 Enable"
    if cur_lang == "ru":
        toggle_txt = "🔴 Отключить" if status == "ACTIVE" else "🟢 Включить"

    buttons.append([
        InlineKeyboardButton(text=toggle_txt, callback_data=f"remna_user_toggle_{user_id}"),
        InlineKeyboardButton(text="⏳ Extend" if cur_lang == "en" else "⏳ Продлить", callback_data=f"remna_user_extend_{user_id}")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="🚦 Reset Traffic" if cur_lang == "en" else "🚦 Сбросить трафик", callback_data=f"remna_user_reset_{user_id}"),
        InlineKeyboardButton(text="✏️ Traffic Limit" if cur_lang == "en" else "✏️ Лимит трафика", callback_data=f"remna_user_limit_{user_id}")
    ])

    buttons.append([
        InlineKeyboardButton(text="📱 HWID Limit" if cur_lang == "en" else "📱 Лимит HWID", callback_data=f"remna_user_hwid_{user_id}"),
        InlineKeyboardButton(text="🗑 Delete" if cur_lang == "en" else "🗑 Удалить", callback_data=f"remna_user_delete_{user_id}")
    ])

    buttons.append([InlineKeyboardButton(text="🔙 Back to list" if cur_lang == "en" else "🔙 К списку", callback_data="remna_menu_users")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def nodes_list_kb(nodes: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = []
    
    for n in nodes:
        uuid = n.get("uuid")
        name = n.get("name", "Node")
        country = n.get("countryCode", "XX")
        # In Remnawave, check enable status or active connections? Usually there's an enabled/disabled toggle
        status_icon = "🟢" if n.get("status") == "ACTIVE" or n.get("isEnabled", True) else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{status_icon} {name} ({country})", callback_data=f"remna_node_view_{uuid}")])

    buttons.append([InlineKeyboardButton(text="➕ Add Node" if cur_lang == "en" else "➕ Добавить ноду", callback_data="remna_node_create")])
    buttons.append([InlineKeyboardButton(text=t("btn_main_menu", cur_lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def node_detail_kb(uuid: str, is_enabled: bool, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    toggle_txt = "🔴 Disable" if is_enabled else "🟢 Enable"
    if cur_lang == "ru":
        toggle_txt = "🔴 Отключить" if is_enabled else "🟢 Включить"

    buttons = [
        [
            InlineKeyboardButton(text=toggle_txt, callback_data=f"remna_node_toggle_{uuid}"),
            InlineKeyboardButton(text="⚡ Restart" if cur_lang == "en" else "⚡ Перезапуск", callback_data=f"remna_node_restart_{uuid}")
        ],
        [
            InlineKeyboardButton(text="🚦 Reset Traffic" if cur_lang == "en" else "🚦 Сброс трафика", callback_data=f"remna_node_reset_{uuid}"),
            InlineKeyboardButton(text="✏️ Edit Name" if cur_lang == "en" else "✏️ Изменить имя", callback_data=f"remna_node_edit_name_{uuid}")
        ],
        [
            InlineKeyboardButton(text="🌐 Edit Address" if cur_lang == "en" else "🌐 Изменить адрес", callback_data=f"remna_node_edit_addr_{uuid}"),
            InlineKeyboardButton(text="🔌 Edit Port" if cur_lang == "en" else "🔌 Изменить порт", callback_data=f"remna_node_edit_port_{uuid}")
        ],
        [
            InlineKeyboardButton(text="🗑 Delete" if cur_lang == "en" else "🗑 Удалить ноду", callback_data=f"remna_node_delete_{uuid}")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to list" if cur_lang == "en" else "🔙 К списку нод", callback_data="remna_menu_nodes")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_profile_kb(profiles: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = []
    for p in profiles:
        uuid = p.get("uuid")
        name = p.get("name", "Profile")
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"remna_node_select_prof_{uuid}")])
    buttons.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="remna_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profiles_list_kb(profiles: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = []
    
    for p in profiles:
        uuid = p.get("uuid")
        name = p.get("name", "Profile")
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"remna_profile_view_{uuid}")])

    buttons.append([InlineKeyboardButton(text="➕ Add Profile" if cur_lang == "en" else "➕ Добавить профиль", callback_data="remna_profile_create")])
    buttons.append([InlineKeyboardButton(text=t("btn_main_menu", cur_lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profile_detail_kb(uuid: str, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = [
        [
            InlineKeyboardButton(text="✏️ Rename" if cur_lang == "en" else "✏️ Переименовать", callback_data=f"remna_profile_rename_{uuid}"),
            InlineKeyboardButton(text="🗑 Delete" if cur_lang == "en" else "🗑 Удалить", callback_data=f"remna_profile_delete_{uuid}")
        ],
        [
            InlineKeyboardButton(text="📥 Export JSON" if cur_lang == "en" else "📥 Экспорт JSON", callback_data=f"remna_profile_export_{uuid}")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to list" if cur_lang == "en" else "🔙 К списку", callback_data="remna_menu_profiles")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def hosts_list_kb(hosts: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = []
    
    for h in hosts:
        uuid = h.get("uuid")
        name = h.get("remark") or h.get("name") or "Host"
        ip = h.get("address") or h.get("ipOrDomain") or "0.0.0.0"
        port = h.get("port", 443)
        buttons.append([InlineKeyboardButton(text=f"{name} ({ip}:{port})", callback_data=f"remna_host_view_{uuid}")])

    buttons.append([InlineKeyboardButton(text="➕ Add Host" if cur_lang == "en" else "➕ Добавить хост", callback_data="remna_host_create")])
    buttons.append([InlineKeyboardButton(text=t("btn_main_menu", cur_lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def host_detail_kb(uuid: str, is_disabled: bool, is_hidden: bool, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    
    toggle_txt = "🔴 Disable" if not is_disabled else "🟢 Enable"
    if cur_lang == "ru":
        toggle_txt = "🔴 Отключить" if not is_disabled else "🟢 Включить"
        
    hidden_txt = "👁 Hide" if not is_hidden else "👁 Show"
    if cur_lang == "ru":
        hidden_txt = "👁 Скрыть" if not is_hidden else "👁 Показать"

    buttons = [
        [
            InlineKeyboardButton(text=toggle_txt, callback_data=f"remna_host_toggle_{uuid}"),
            InlineKeyboardButton(text=hidden_txt, callback_data=f"remna_host_hide_{uuid}")
        ],
        [
            InlineKeyboardButton(text="✏️ Remark" if cur_lang == "en" else "✏️ Имя", callback_data=f"remna_host_edit_remark_{uuid}"),
            InlineKeyboardButton(text="🌐 Address" if cur_lang == "en" else "🌐 Адрес", callback_data=f"remna_host_edit_addr_{uuid}"),
            InlineKeyboardButton(text="🔌 Port" if cur_lang == "en" else "🔌 Порт", callback_data=f"remna_host_edit_port_{uuid}")
        ],
        [
            InlineKeyboardButton(text="🗺 Path" if cur_lang == "en" else "🗺 Путь", callback_data=f"remna_host_edit_path_{uuid}"),
            InlineKeyboardButton(text="📡 SNI", callback_data=f"remna_host_edit_sni_{uuid}"),
            InlineKeyboardButton(text="🌐 Host Header" if cur_lang == "en" else "🌐 Host заголовок", callback_data=f"remna_host_edit_host_{uuid}")
        ],
        [
            InlineKeyboardButton(text="⚡ ALPN", callback_data=f"remna_host_edit_alpn_{uuid}"),
            InlineKeyboardButton(text="🔑 Fingerprint" if cur_lang == "en" else "🔑 Отпечаток", callback_data=f"remna_host_edit_fp_{uuid}"),
            InlineKeyboardButton(text="🗑 Delete" if cur_lang == "en" else "🗑 Удалить", callback_data=f"remna_host_delete_{uuid}")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to list" if cur_lang == "en" else "🔙 К списку", callback_data="remna_menu_hosts")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_inbound_kb(inbounds: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = []
    for ib in inbounds:
        uuid = ib.get("uuid")
        tag = ib.get("tag", "Inbound")
        protocol = ib.get("protocol", "unknown")
        buttons.append([InlineKeyboardButton(text=f"{tag} ({protocol})", callback_data=f"remna_host_select_inb_{uuid}")])
    buttons.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="remna_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_host_profile_kb(profiles: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = []
    for p in profiles:
        uuid = p.get("uuid")
        name = p.get("name", "Profile")
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"remna_host_select_prof_{uuid}")])
    buttons.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="remna_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def panels_list_kb(configs: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = []
    
    for c in configs:
        uuid = c.get("uuid")
        name = c.get("name", "Panel")
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"remna_panel_view_{uuid}")])

    buttons.append([InlineKeyboardButton(text="➕ Add Panel" if cur_lang == "en" else "➕ Добавить панель", callback_data="remna_panel_create")])
    buttons.append([InlineKeyboardButton(text=t("btn_main_menu", cur_lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def panel_detail_kb(uuid: str, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = [
        [
            InlineKeyboardButton(text="👯 Clone" if cur_lang == "en" else "👯 Клонировать", callback_data=f"remna_panel_clone_{uuid}"),
            InlineKeyboardButton(text="🗑 Delete" if cur_lang == "en" else "🗑 Удалить", callback_data=f"remna_panel_delete_{uuid}")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to list" if cur_lang == "en" else "🔙 К списку", callback_data="remna_menu_panels")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
