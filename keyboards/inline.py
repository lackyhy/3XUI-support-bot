from typing import List, Dict, Any, Tuple, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.i18n import t

def main_menu_kb(has_creds: bool = True, active_panel_name: str = "Main Server", lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = []
    if has_creds:
        buttons.append([
            InlineKeyboardButton(text=t("btn_active_server", lang, name=active_panel_name), callback_data="menu_select_panel")
        ])
        buttons.append([
            InlineKeyboardButton(text=t("btn_server_status", lang), callback_data="menu_server")
        ])
        buttons.append([
            InlineKeyboardButton(text=t("btn_clients", lang), callback_data="menu_clients_hub")
        ])
        buttons.append([
            InlineKeyboardButton(text=t("btn_inbounds", lang), callback_data="menu_inbounds")
        ])
        buttons.append([
            InlineKeyboardButton(text=t("btn_add_client", lang), callback_data="menu_add_client")
        ])
        buttons.append([
            InlineKeyboardButton(text=t("btn_search_client", lang), callback_data="menu_search_client")
        ])
        buttons.append([
            InlineKeyboardButton(text=t("btn_restart_xray", lang), callback_data="action_restart_xray")
        ])
        buttons.append([
            InlineKeyboardButton(text=t("btn_settings", lang), callback_data="menu_settings")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text=t("btn_setup_panel", lang), callback_data="setup_panel")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def panels_list_kb(panels: List[Dict[str, Any]], active_id: Optional[str], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = []
    suffix_active = t("active_suffix", cur_lang)
    for p in panels:
        p_id = p.get("id")
        p_name = p.get("name", "Server")
        is_active = (p_id == active_id)
        is_enabled = p.get("enabled", True)

        if not is_enabled:
            prefix = "🔴 "
            dis_label = " (Disabled)" if cur_lang == "en" else " (Отключена)"
            btn_text = f"{prefix}{p_name}{dis_label}"
        elif is_active:
            prefix = "🟢 "
            btn_text = f"{prefix}{p_name}{suffix_active}"
        else:
            prefix = "⚪ "
            btn_text = f"{prefix}{p_name}"

        if not is_active:
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"switch_panel_{p_id}")])
        else:
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data="noop")])

    btn_toggle = "👁 Enable/Disable" if cur_lang == "en" else "👁 Вкл/Выкл панели"
    buttons.append([
        InlineKeyboardButton(text=t("btn_add_server", cur_lang), callback_data="setup_panel"),
        InlineKeyboardButton(text=btn_toggle, callback_data="menu_toggle_panels"),
        InlineKeyboardButton(text=t("btn_delete_server", cur_lang), callback_data="menu_delete_panel")
    ])
    buttons.append([InlineKeyboardButton(text=t("btn_main_menu", cur_lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def toggle_panels_kb(panels: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    buttons = []
    for p in panels:
        p_id = p.get("id")
        p_name = p.get("name", "Server")
        is_enabled = p.get("enabled", True)
        status_icon = "🟢" if is_enabled else "🔴"
        action_text = "Enabled (Click to disable)" if is_enabled else "Disabled (Click to enable)"
        if cur_lang == "ru":
            action_text = "Включена (Нажмите для выкл)" if is_enabled else "Отключена (Нажмите для вкл)"
        
        buttons.append([InlineKeyboardButton(text=f"{status_icon} {p_name}: {action_text}", callback_data=f"toggle_panel_enable_{p_id}")])

    buttons.append([InlineKeyboardButton(text=t("btn_back_to_servers", cur_lang), callback_data="menu_select_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def delete_panels_kb(panels: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = []
    btn_del = "🗑 Delete" if (lang or "en") == "en" else "🗑 Удалить"
    for p in panels:
        p_id = p.get("id")
        p_name = p.get("name", "Server")
        buttons.append([InlineKeyboardButton(text=f"{btn_del} {p_name}", callback_data=f"do_delete_panel_{p_id}")])

    buttons.append([InlineKeyboardButton(text=t("btn_back_to_servers", lang), callback_data="menu_select_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_kb(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="cancel_action")]
    ])

def initial_status_kb(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    btn_enable = "🟢 Enabled (Active immediately)" if (lang or "en") == "en" else "🟢 Включен (Сразу активен)"
    btn_disable = "🔴 Disabled (No connection)" if (lang or "en") == "en" else "🔴 Отключен (Без подключения)"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_enable, callback_data="client_init_enable_1")],
        [InlineKeyboardButton(text=btn_disable, callback_data="client_init_enable_0")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="cancel_action")]
    ])

def auth_type_kb(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Bearer Token", callback_data="auth_mode_token")],
        [InlineKeyboardButton(text="👤 Login / Password" if (lang or "en") == "en" else "👤 Логин и Пароль", callback_data="auth_mode_creds")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="cancel_action")]
    ])

def settings_menu_kb(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_bot_menu", lang), callback_data="menu_bot_dashboard")],
        [InlineKeyboardButton(text=t("btn_rename_panel", lang), callback_data="rename_panel")],
        [InlineKeyboardButton(text=t("btn_edit_setup", lang), callback_data="setup_panel")],
        [InlineKeyboardButton(text=t("btn_reset_credentials", lang), callback_data="delete_credentials")],
        [InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="menu_main")]
    ])

def bot_menu_kb(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    cur_lang = lang or "en"
    target_lang = "ru" if cur_lang == "en" else "en"
    btn_all_status = "📊 Status of All Panels" if cur_lang == "en" else "📊 Статус всех панелей"
    btn_switch = t("btn_switch_lang_ru", cur_lang) if cur_lang == "en" else t("btn_switch_lang_en", cur_lang)

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_all_status, callback_data="menu_all_panels_status")],
        [InlineKeyboardButton(text=t("btn_export_backup", cur_lang), callback_data="export_credentials")],
        [InlineKeyboardButton(text=btn_switch, callback_data=f"set_lang_{target_lang}")],
        [InlineKeyboardButton(text=t("btn_switch_server", cur_lang), callback_data="menu_select_panel")],
        [InlineKeyboardButton(text=t("btn_main_menu", cur_lang), callback_data="menu_main")]
    ])

def server_menu_kb(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_refresh", lang), callback_data="menu_server"),
            InlineKeyboardButton(text=t("btn_restart_xray", lang), callback_data="action_restart_xray")
        ],
        [InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="menu_main")]
    ])

def all_panels_status_kb(lang: Optional[str] = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_refresh", lang), callback_data="menu_all_panels_status"),
            InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="menu_main")
        ]
    ])

def inbounds_list_kb(inbounds: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
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
        InlineKeyboardButton(text=t("btn_add_client", lang), callback_data="menu_add_client"),
        InlineKeyboardButton(text=t("btn_refresh", lang), callback_data="menu_inbounds")
    ])
    buttons.append([InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def inbound_detail_kb(inbound_id: int, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_view_inbound_clients", lang), callback_data=f"clients_list_{inbound_id}_0")],
        [InlineKeyboardButton(text=t("btn_add_client_to_inbound", lang), callback_data=f"add_client_to_{inbound_id}")],
        [InlineKeyboardButton(text=t("btn_back_to_inbounds", lang), callback_data="menu_inbounds")]
    ])

def clients_hub_kb(groups_summary: List[Tuple[str, int]], total_clients: int, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=t("all_clients_btn", lang, count=total_clients), callback_data="menu_all_clients_0")
        ]
    ]

    for g_name, count in groups_summary:
        if g_name != "none":
            disp_name = t("group_btn", lang, name=g_name, count=count)
        else:
            disp_name = t("no_group_btn", lang, count=count)
        buttons.append([
            InlineKeyboardButton(text=disp_name, callback_data=f"menu_group_clients_{g_name}_0")
        ])

    buttons.append([
        InlineKeyboardButton(text=t("btn_add_client", lang), callback_data="menu_add_client"),
        InlineKeyboardButton(text=t("btn_search_client", lang), callback_data="menu_search_client")
    ])
    buttons.append([InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def all_clients_paginated_kb(
    items: List[Dict[str, Any]],
    page: int = 0,
    page_size: int = 8,
    group_filter: Optional[str] = None,
    lang: Optional[str] = None
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
        nav_buttons.append(InlineKeyboardButton(text=t("btn_prev", lang), callback_data=f"{cb_prefix}{page-1}"))
    if end_idx < total_clients:
        nav_buttons.append(InlineKeyboardButton(text=t("btn_next", lang), callback_data=f"{cb_prefix}{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text=t("btn_add_client", lang), callback_data="menu_add_client"),
        InlineKeyboardButton(text=t("btn_search_client", lang), callback_data="menu_search_client")
    ])
    buttons.append([InlineKeyboardButton(text=t("back_to_hub", lang), callback_data="menu_clients_hub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def clients_list_kb(inbound_id: int, clients: List[Dict[str, Any]], page: int = 0, page_size: int = 8, lang: Optional[str] = None) -> InlineKeyboardMarkup:
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
        nav_buttons.append(InlineKeyboardButton(text=t("btn_prev", lang), callback_data=f"clients_list_{inbound_id}_{page-1}"))
    if end_idx < total_clients:
        nav_buttons.append(InlineKeyboardButton(text=t("btn_next", lang), callback_data=f"clients_list_{inbound_id}_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text=t("btn_back_to_inbounds", lang), callback_data=f"inbound_view_{inbound_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def client_detail_kb(inbound_id: int, uuid_val: str, email: str, is_enabled: bool, group_filter: str = "all", lang: Optional[str] = None) -> InlineKeyboardMarkup:
    status_btn_text = t("btn_deactivate", lang) if is_enabled else t("btn_activate", lang)
    if group_filter.startswith("inbound"):
        ib_num = group_filter.replace("inbound", "")
        back_cb = f"clients_list_{ib_num}_0"
    elif group_filter == "all":
        back_cb = "menu_all_clients_0"
    else:
        back_cb = f"menu_group_clients_{group_filter}_0"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_qr_code", lang), callback_data=f"client_key_select_{inbound_id}_{uuid_val}"),
            InlineKeyboardButton(text=status_btn_text, callback_data=f"client_toggle_{inbound_id}_{uuid_val}")
        ],
        [
            InlineKeyboardButton(text=t("btn_inbound_binding", lang), callback_data=f"client_manage_ibs_{inbound_id}_{uuid_val}")
        ],
        [
            InlineKeyboardButton(text=t("btn_edit_limit_gb", lang), callback_data=f"client_edit_gb_{inbound_id}_{uuid_val}"),
            InlineKeyboardButton(text=t("btn_edit_expiry", lang), callback_data=f"client_edit_exp_{inbound_id}_{uuid_val}")
        ],
        [
            InlineKeyboardButton(text=t("btn_reset_traffic", lang), callback_data=f"client_reset_{inbound_id}_{email}"),
            InlineKeyboardButton(text=t("btn_reset_ip", lang), callback_data=f"client_clearip_{email}")
        ],
        [InlineKeyboardButton(text=t("btn_delete_client", lang), callback_data=f"client_delete_confirm_{inbound_id}_{uuid_val}")],
        [InlineKeyboardButton(text=t("btn_back_to_clients", lang), callback_data=back_cb)]
    ])

def client_key_choice_kb(inbound_id: int, uuid_val: str, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    btn_sub = "🌐 1. Subscription URL" if (lang or "en") == "en" else "🌐 1. Ссылка подписки (Subscription)"
    btn_direct = "🔌 2. Direct VLESS/VMess Key" if (lang or "en") == "en" else "🔌 2. Прямой коннект (Direct VLESS/VMess)"
    btn_back = "🔙 Back to Client Profile" if (lang or "en") == "en" else "🔙 К профилю клиента"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_sub, callback_data=f"client_key_type_sub_{inbound_id}_{uuid_val}")],
        [InlineKeyboardButton(text=btn_direct, callback_data=f"client_key_type_direct_{inbound_id}_{uuid_val}")],
        [InlineKeyboardButton(text=btn_back, callback_data=f"client_view_{inbound_id}_{uuid_val}")]
    ])

def manage_client_inbounds_kb(
    curr_inbound_id: int,
    uuid_val: str,
    email: str,
    all_inbounds: List[Dict[str, Any]],
    attached_inbound_ids: List[int],
    lang: Optional[str] = None
) -> InlineKeyboardMarkup:
    buttons = []
    btn_attach_all = "🌐 Attach to ALL Inbounds" if (lang or "en") == "en" else "🌐 Привязать КО ВСЕМ инбаундам"
    btn_back = "🔙 Back to Client Profile" if (lang or "en") == "en" else "🔙 К профилю клиента"

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
            text=btn_attach_all,
            callback_data=f"client_ib_attach_all_{curr_inbound_id}_{uuid_val}"
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            text=btn_back,
            callback_data=f"client_view_{curr_inbound_id}_{uuid_val}"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def add_client_inbounds_multiselect_kb(
    inbounds: List[Dict[str, Any]],
    selected_ids: List[int],
    lang: Optional[str] = None
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
        btn_deselect_all = "❌ Deselect ALL" if (lang or "en") == "en" else "❌ Снять выбор со ВСЕХ"
        buttons.append([InlineKeyboardButton(
            text=btn_deselect_all,
            callback_data="add_client_toggle_all_off"
        )])
    else:
        btn_select_all = "🌐 Select ALL Inbounds" if (lang or "en") == "en" else "🌐 Выбрать ВСЕ инбаунды"
        buttons.append([InlineKeyboardButton(
            text=btn_select_all,
            callback_data="add_client_toggle_all_on"
        )])

    count = len(selected_ids)
    btn_continue = f"✅ Continue (selected: {count})" if (lang or "en") == "en" else f"✅ Продолжить (выбрано: {count})"
    buttons.append([InlineKeyboardButton(
        text=btn_continue,
        callback_data="add_client_confirm_inbounds"
    )])
    buttons.append([InlineKeyboardButton(
        text=t("btn_cancel", lang),
        callback_data="cancel_action"
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_new_inbound_kb(current_inbound_id: int, uuid_val: str, inbounds: List[Dict[str, Any]], lang: Optional[str] = None) -> InlineKeyboardMarkup:
    buttons = []
    curr_label = "📍 (Current) " if (lang or "en") == "en" else "📍 (Текущий) "
    for ib in inbounds:
        ib_id = ib.get("id")
        remark = ib.get("remark", f"Inbound #{ib_id}")
        protocol = ib.get("protocol", "").upper()
        port = ib.get("port")
        is_current = (ib_id == current_inbound_id)
        prefix = curr_label if is_current else "🔌 "
        
        btn_text = f"{prefix}{remark} ({protocol}:{port})"
        if not is_current:
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"client_do_move_{current_inbound_id}_{ib_id}_{uuid_val}")])
        else:
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data="noop")])

    buttons.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=f"client_view_{current_inbound_id}_{uuid_val}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_delete_client_kb(inbound_id: int, uuid_val: str, lang: Optional[str] = None) -> InlineKeyboardMarkup:
    btn_yes = "✅ Yes, delete!" if (lang or "en") == "en" else "✅ Да, удалить!"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=btn_yes, callback_data=f"client_delete_do_{inbound_id}_{uuid_val}"),
            InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=f"client_view_{inbound_id}_{uuid_val}")
        ]
    ])
