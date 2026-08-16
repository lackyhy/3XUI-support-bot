from typing import List, Dict, Any, Tuple, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb(has_creds: bool = True, active_panel_name: str = "Основной сервер") -> InlineKeyboardMarkup:
    buttons = []
    if has_creds:
        buttons.append([
            InlineKeyboardButton(text=f"🖥 Сервер: {active_panel_name}", callback_data="menu_select_panel")
        ])
        buttons.append([
            InlineKeyboardButton(text="📊 Статус сервера", callback_data="menu_server")
        ])
        buttons.append([
            InlineKeyboardButton(text="👥 Клиенты", callback_data="menu_clients_hub")
        ])
        buttons.append([
            InlineKeyboardButton(text="🌐 Инбаунды (Подключения)", callback_data="menu_inbounds")
        ])
        buttons.append([
            InlineKeyboardButton(text="➕ Добавить нового клиента", callback_data="menu_add_client")
        ])
        buttons.append([
            InlineKeyboardButton(text="🔍 Поиск клиента", callback_data="menu_search_client")
        ])
        buttons.append([
            InlineKeyboardButton(text="⚡ Перезапустить Xray Core", callback_data="action_restart_xray")
        ])
        buttons.append([
            InlineKeyboardButton(text="⚙️ Настройки доступа", callback_data="menu_settings")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="⚙️ Подключить панель 3x-ui", callback_data="setup_panel")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def panels_list_kb(panels: List[Dict[str, Any]], active_id: Optional[str]) -> InlineKeyboardMarkup:
    buttons = []
    for p in panels:
        p_id = p.get("id")
        p_name = p.get("name", "Сервер")
        is_active = (p_id == active_id)
        prefix = "🟢 " if is_active else "⚪ "
        suffix = " (Активен)" if is_active else ""
        
        btn_text = f"{prefix}{p_name}{suffix}"
        if not is_active:
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"switch_panel_{p_id}")])
        else:
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data="noop")])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить сервер", callback_data="setup_panel"),
        InlineKeyboardButton(text="🗑 Удалить сервер", callback_data="menu_delete_panel")
    ])
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def delete_panels_kb(panels: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    buttons = []
    for p in panels:
        p_id = p.get("id")
        p_name = p.get("name", "Сервер")
        buttons.append([InlineKeyboardButton(text=f"🗑 Удалить {p_name}", callback_data=f"do_delete_panel_{p_id}")])

    buttons.append([InlineKeyboardButton(text="🔙 К списку серверов", callback_data="menu_select_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])

def initial_status_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Включен (Сразу активен)", callback_data="client_init_enable_1")],
        [InlineKeyboardButton(text="🔴 Отключен (Без подключения)", callback_data="client_init_enable_0")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])

def auth_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Bearer Token", callback_data="auth_mode_token")],
        [InlineKeyboardButton(text="👤 Логин и Пароль", callback_data="auth_mode_creds")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
    ])

def settings_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Скачать бэкап базы (credentials.enc)", callback_data="export_credentials")],
        [InlineKeyboardButton(text="✏️ Переименовать текущий сервер", callback_data="rename_panel")],
        [InlineKeyboardButton(text="✏️ Изменить параметры подключения", callback_data="setup_panel")],
        [InlineKeyboardButton(text="🗑 Сбросить зашифрованные данные", callback_data="delete_credentials")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")]
    ])

def server_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_server"),
            InlineKeyboardButton(text="⚡ Перезапустить Xray", callback_data="action_restart_xray")
        ],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")]
    ])

def inbounds_list_kb(inbounds: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    buttons = []
    for ib in inbounds:
        ib_id = ib.get("id")
        remark = ib.get("remark", f"Inbound {ib_id}")
        protocol = ib.get("protocol", "").upper()
        port = ib.get("port")
        enable = "🟢" if ib.get("enable", True) else "🔴"
        
        btn_text = f"{enable} {remark} ({protocol}:{port})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"inbound_view_{ib_id}")])
    
    buttons.append([
        InlineKeyboardButton(text="➕ Добавить клиента", callback_data="menu_add_client"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_inbounds")
    ])
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def inbound_detail_kb(inbound_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Список клиентов", callback_data=f"clients_list_{inbound_id}_0")],
        [InlineKeyboardButton(text="➕ Добавить клиента", callback_data=f"add_client_to_{inbound_id}")],
        [InlineKeyboardButton(text="🔙 К инбаундам", callback_data="menu_inbounds")]
    ])

def clients_hub_kb(groups_summary: List[Tuple[str, int]], total_clients: int) -> InlineKeyboardMarkup:
    """
    Keyboard for Clients Hub:
    - Все клиенты (N)
    - Group buttons (📁 Группа: Admins (1), 📁 Группа: server_connect (2), etc.)
    """
    buttons = [
        [
            InlineKeyboardButton(text=f"🌐 Все клиенты ({total_clients})", callback_data="menu_all_clients_0")
        ]
    ]

    for g_name, count in groups_summary:
        disp_name = f"📁 Группа: {g_name} ({count})" if g_name != "none" else f"📂 Без группы ({count})"
        buttons.append([
            InlineKeyboardButton(text=disp_name, callback_data=f"menu_group_clients_{g_name}_0")
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить клиента", callback_data="menu_add_client"),
        InlineKeyboardButton(text="🔍 Поиск", callback_data="menu_search_client")
    ])
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def all_clients_paginated_kb(
    items: List[Dict[str, Any]],
    page: int = 0,
    page_size: int = 8,
    group_filter: Optional[str] = None
) -> InlineKeyboardMarkup:
    buttons = []
    total_clients = len(items)
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_clients)

    grp_ctx = group_filter if group_filter else "all"

    page_items = items[start_idx:end_idx]
    for item in page_items:
        email = item.get("email", "no-name")
        ib_id = item.get("first_ib_id")
        uuid_val = item.get("uuid_val", "")
        enable_icon = "🟢" if item.get("enable", True) else "🔴"
        summary = item.get("inbounds_summary", "")
        
        btn_text = f"{enable_icon} {email} ({summary})" if summary else f"{enable_icon} {email}"
        buttons.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"client_view_{ib_id}_{uuid_val}_{grp_ctx}"
        )])

    # Pagination controls
    cb_prefix = f"menu_group_clients_{group_filter}_" if group_filter else "menu_all_clients_"
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"{cb_prefix}{page-1}"))
    if end_idx < total_clients:
        nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"{cb_prefix}{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить клиента", callback_data="menu_add_client"),
        InlineKeyboardButton(text="🔍 Поиск", callback_data="menu_search_client")
    ])
    buttons.append([InlineKeyboardButton(text="🔙 К разделу клиентов", callback_data="menu_clients_hub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def clients_list_kb(inbound_id: int, clients: List[Dict[str, Any]], page: int = 0, page_size: int = 8) -> InlineKeyboardMarkup:
    buttons = []
    total_clients = len(clients)
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_clients)
    
    page_clients = clients[start_idx:end_idx]
    for c in page_clients:
        email = c.get("email", "no-name")
        enable = "🟢" if c.get("enable", True) else "🔴"
        uuid_val = c.get("id") or c.get("password") or ""
        buttons.append([InlineKeyboardButton(
            text=f"{enable} {email}",
            callback_data=f"client_view_{inbound_id}_{uuid_val}_inbound{inbound_id}"
        )])

    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"clients_list_{inbound_id}_{page-1}"))
    if end_idx < total_clients:
        nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"clients_list_{inbound_id}_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="🔙 К инбаунду", callback_data=f"inbound_view_{inbound_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def client_detail_kb(inbound_id: int, uuid_val: str, email: str, is_enabled: bool, group_filter: str = "all") -> InlineKeyboardMarkup:
    status_btn_text = "🔴 Деактивировать" if is_enabled else "🟢 Активировать"
    if group_filter.startswith("inbound"):
        ib_num = group_filter.replace("inbound", "")
        back_cb = f"clients_list_{ib_num}_0"
    elif group_filter == "all":
        back_cb = "menu_all_clients_0"
    else:
        back_cb = f"menu_group_clients_{group_filter}_0"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔑 Ссылка и QR-код", callback_data=f"client_key_select_{inbound_id}_{uuid_val}"),
            InlineKeyboardButton(text=status_btn_text, callback_data=f"client_toggle_{inbound_id}_{uuid_val}")
        ],
        [
            InlineKeyboardButton(text="🌐 Привязка к инбаундам", callback_data=f"client_manage_ibs_{inbound_id}_{uuid_val}")
        ],
        [
            InlineKeyboardButton(text="📈 Изменить лимит ГБ", callback_data=f"client_edit_gb_{inbound_id}_{uuid_val}"),
            InlineKeyboardButton(text="📅 Изменить срок", callback_data=f"client_edit_exp_{inbound_id}_{uuid_val}")
        ],
        [
            InlineKeyboardButton(text="🔄 Сбросить трафик", callback_data=f"client_reset_{inbound_id}_{email}"),
            InlineKeyboardButton(text="🧹 Сбросить IP", callback_data=f"client_clearip_{email}")
        ],
        [InlineKeyboardButton(text="🗑 Удалить клиента", callback_data=f"client_delete_confirm_{inbound_id}_{uuid_val}")],
        [InlineKeyboardButton(text="🔙 К списку клиентов", callback_data=back_cb)]
    ])

def client_key_choice_kb(inbound_id: int, uuid_val: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🌐 1. Ссылка подписки (Subscription)",
                callback_data=f"client_key_type_sub_{inbound_id}_{uuid_val}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔌 2. Прямой коннект (Direct VLESS/VMess)",
                callback_data=f"client_key_type_direct_{inbound_id}_{uuid_val}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 К профилю клиента",
                callback_data=f"client_view_{inbound_id}_{uuid_val}"
            )
        ]
    ])

def manage_client_inbounds_kb(
    curr_inbound_id: int,
    uuid_val: str,
    email: str,
    all_inbounds: List[Dict[str, Any]],
    attached_inbound_ids: List[int]
) -> InlineKeyboardMarkup:
    buttons = []
    for ib in all_inbounds:
        ib_id = ib.get("id")
        remark = ib.get("remark", f"Inbound #{ib_id}")
        protocol = ib.get("protocol", "").upper()
        port = ib.get("port")
        is_attached = (ib_id in attached_inbound_ids)
        
        prefix = "✅ " if is_attached else "❌ "
        action = "detach" if is_attached else "attach"
        
        btn_text = f"{prefix}{remark} ({protocol}:{port})"
        buttons.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"client_ib_{action}_{curr_inbound_id}_{ib_id}_{uuid_val}"
        )])

    buttons.append([
        InlineKeyboardButton(
            text="🌐 Привязать КО ВСЕМ инбаундам",
            callback_data=f"client_ib_attach_all_{curr_inbound_id}_{uuid_val}"
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            text="🔙 К профилю клиента",
            callback_data=f"client_view_{curr_inbound_id}_{uuid_val}"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def add_client_inbounds_multiselect_kb(
    inbounds: List[Dict[str, Any]],
    selected_ids: List[int]
) -> InlineKeyboardMarkup:
    buttons = []
    for ib in inbounds:
        ib_id = ib.get("id")
        remark = ib.get("remark", f"Inbound #{ib_id}")
        protocol = ib.get("protocol", "").upper()
        port = ib.get("port")
        
        is_selected = (ib_id in selected_ids)
        prefix = "✅ " if is_selected else "➕ "
        
        btn_text = f"{prefix}{remark} ({protocol}:{port})"
        buttons.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"add_client_toggle_ib_{ib_id}"
        )])

    all_selected = (len(selected_ids) == len(inbounds))
    if all_selected:
        buttons.append([InlineKeyboardButton(
            text="❌ Снять выбор со ВСЕХ",
            callback_data="add_client_toggle_all_off"
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text="🌐 Выбрать ВСЕ инбаунды",
            callback_data="add_client_toggle_all_on"
        )])

    count = len(selected_ids)
    buttons.append([InlineKeyboardButton(
        text=f"✅ Продолжить (выбрано: {count})",
        callback_data="add_client_confirm_inbounds"
    )])
    buttons.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel_action"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_new_inbound_kb(current_inbound_id: int, uuid_val: str, inbounds: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    buttons = []
    for ib in inbounds:
        ib_id = ib.get("id")
        remark = ib.get("remark", f"Inbound #{ib_id}")
        protocol = ib.get("protocol", "").upper()
        port = ib.get("port")
        is_current = (ib_id == current_inbound_id)
        prefix = "📍 (Текущий) " if is_current else "🔌 "
        
        btn_text = f"{prefix}{remark} ({protocol}:{port})"
        if not is_current:
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"client_do_move_{current_inbound_id}_{ib_id}_{uuid_val}")])
        else:
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data="noop")])

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data=f"client_view_{current_inbound_id}_{uuid_val}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_delete_client_kb(inbound_id: int, uuid_val: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить!", callback_data=f"client_delete_do_{inbound_id}_{uuid_val}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"client_view_{inbound_id}_{uuid_val}")
        ]
    ])
