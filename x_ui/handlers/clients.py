from typing import List, Dict, Any, Optional, Tuple
import io
import json
import uuid
import datetime
import qrcode
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from x_ui.core.api_client import ThreeXUIClient, format_bytes, ensure_dict, extract_external_sub
from x_ui.core import crypto_storage
from x_ui.keyboards import inline as keyboards
from x_ui.states.states import AddClientStates, SearchClientStates, EditClientGBStates, EditClientExpiryStates, SetSubPortStates

router = Router()

from x_ui.core import bot_settings
from x_ui.core.i18n import t

def format_timestamp(ms: int, lang: str = "en") -> str:
    if not ms or ms <= 0:
        return t("unlimited", lang)
    dt = datetime.datetime.fromtimestamp(ms / 1000.0)
    return dt.strftime("%d.%m.%Y %H:%M")

@router.callback_query(F.data == "menu_clients_hub")
async def cb_clients_hub(callback: CallbackQuery):
    client_api = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client_api:
        await callback.answer("Auth error" if lang == "en" else "Ошибка авторизации", show_alert=True)
        return

    await callback.answer("Loading clients hub..." if lang == "en" else "Загрузка раздела клиентов...")
    clients_res = await client_api.get_clients_list()
    if not clients_res.get("success"):
        res = await client_api.get_inbounds()
        await client_api.close()
        if not res.get("success"):
            await callback.message.edit_text(
                f"❌ **Error loading data:**\n`{res.get('msg')}`" if lang == "en" else f"❌ **Ошибка загрузки данных:**\n`{res.get('msg')}`",
                reply_markup=keyboards.main_menu_kb(lang=lang),
                parse_mode="Markdown"
            )
            return
        inbounds = res.get("obj", [])
        unique_clients = set()
        for ib in inbounds:
            settings = ensure_dict(ib.get("settings"))
            for c in settings.get("clients", []):
                unique_clients.add(c.get("email", "no-name"))
        total_clients = len(unique_clients)
    else:
        await client_api.close()
        master_clients = clients_res.get("obj", [])
        total_clients = len(master_clients)

    text = (
        f"{t('clients_hub_title', lang)}\n\n"
        f"{t('total_clients_in_system', lang, count=total_clients)}\n\n"
        + ("Choose an option below to view all clients or filter by group:" if lang == "en" else "Выберите команду ниже для просмотра всех клиентов или фильтрации по группам:")
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.clients_hub_kb(total_clients, lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_client_groups")
async def cb_menu_client_groups(callback: CallbackQuery):
    client_api = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client_api:
        await callback.answer("Auth error" if lang == "en" else "Ошибка авторизации", show_alert=True)
        return

    await callback.answer("Loading groups..." if lang == "en" else "Загрузка групп...")
    clients_res = await client_api.get_clients_list()
    unique_clients = {}

    if clients_res.get("success") and isinstance(clients_res.get("obj"), list):
        await client_api.close()
        for c in clients_res.get("obj", []):
            email = c.get("email", "no-name")
            grp = c.get("group")
            if not grp or str(grp).strip() == "" or str(grp).lower() in ["none", "null", "undefined", "—", "-"]:
                grp = "none"
            else:
                grp = str(grp).strip()
            unique_clients[email] = grp
    else:
        res = await client_api.get_inbounds()
        await client_api.close()
        if res.get("success"):
            for ib in res.get("obj", []):
                settings = ensure_dict(ib.get("settings"))
                for c in settings.get("clients", []):
                    email = c.get("email", "no-name")
                    grp = c.get("group") or c.get("group_name") or c.get("clientGroup") or c.get("client_group") or "none"
                    if not grp or str(grp).strip() == "" or str(grp).lower() in ["none", "null", "undefined", "—", "-"]:
                        grp = "none"
                    else:
                        grp = str(grp).strip()
                    if email not in unique_clients or (unique_clients[email] == "none" and grp != "none"):
                        unique_clients[email] = grp

    group_counts = {}
    for email, grp in unique_clients.items():
        group_counts[grp] = group_counts.get(grp, 0) + 1

    groups_summary = [(grp, count) for grp, count in group_counts.items()]

    text = (
        "📁 **Client Groups**\n\nSelect a group below to view its clients:" if lang == "en" else "📁 **Группы клиентов**\n\nВыберите группу для просмотра списка клиентов:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.client_groups_list_kb(groups_summary, lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("mgc:"))
@router.callback_query(F.data.startswith("menu_grp_clients:"))
async def cb_menu_group_clients(callback: CallbackQuery):
    parts = callback.data.split(":")
    group_filter = parts[1]
    page = int(parts[2])
    await render_all_clients_page(callback, page=page, group_filter=group_filter)

@router.callback_query(F.data.startswith("mac:"))
@router.callback_query(F.data.startswith("menu_all_clients:"))
async def cb_menu_all_clients(callback: CallbackQuery):
    parts = callback.data.split(":")
    page = int(parts[1])
    await render_all_clients_page(callback, page=page, group_filter=None)

@router.callback_query(F.data.startswith("menu_group_clients_"))
async def cb_menu_group_clients_legacy(callback: CallbackQuery):
    parts = callback.data.split("_")
    page = int(parts[-1])
    group_filter = "_".join(parts[3:-1])
    await render_all_clients_page(callback, page=page, group_filter=group_filter)

@router.callback_query(F.data.startswith("menu_all_clients_"))
async def cb_menu_all_clients_legacy(callback: CallbackQuery):
    parts = callback.data.split("_")
    page = int(parts[-1])
    await render_all_clients_page(callback, page=page, group_filter=None)

async def render_all_clients_page(callback: CallbackQuery, page: int = 0, group_filter: Optional[str] = None):
    lang = bot_settings.get_language()
    client_api = ThreeXUIClient.from_storage()

    if not client_api:
        await callback.answer("Auth error" if lang == "en" else "Ошибка авторизации", show_alert=True)
        return

    res = await client_api.get_inbounds()
    if not res.get("success"):
        await client_api.close()
        await callback.message.edit_text(
            f"❌ **Error loading inbounds:**\n`{res.get('msg')}`" if lang == "en" else f"❌ **Ошибка загрузки инбаундов:**\n`{res.get('msg')}`",
            reply_markup=keyboards.main_menu_kb(lang=lang),
            parse_mode="Markdown"
        )
        return

    inbounds = res.get("obj", [])
    unique_clients = {}

    clients_res = await client_api.get_clients_list()
    await client_api.close()

    if clients_res.get("success") and isinstance(clients_res.get("obj"), list):
        for c in clients_res.get("obj", []):
            email = c.get("email", "no-name")
            uuid_val = c.get("uuid") or c.get("id") or c.get("password") or ""
            grp = c.get("group")
            if not grp or str(grp).strip() == "" or str(grp).lower() in ["none", "null", "undefined", "—", "-"]:
                grp = "none"
            else:
                grp = str(grp).strip()

            if email not in unique_clients:
                unique_clients[email] = {
                    "email": email,
                    "uuid": uuid_val,
                    "enable": c.get("enable", True),
                    "group": grp,
                    "inbound_id": c.get("inboundIds", [0])[0] if isinstance(c.get("inboundIds"), list) and c.get("inboundIds") else 0
                }
    else:
        for ib in inbounds:
            ib_id = ib.get("id")
            settings = ensure_dict(ib.get("settings"))
            clients = settings.get("clients", [])
            for c in clients:
                email = c.get("email", "no-name")
                uuid_val = c.get("id") or c.get("password") or ""
                enable = c.get("enable", True)
                grp = c.get("group") or c.get("group_name") or c.get("clientGroup") or c.get("client_group") or "none"
                if not grp or str(grp).strip() == "" or str(grp).lower() in ["none", "null", "undefined", "—", "-"]:
                    grp = "none"
                else:
                    grp = str(grp).strip()

                if email not in unique_clients or (unique_clients[email]["group"] == "none" and grp != "none"):
                    unique_clients[email] = {
                        "email": email,
                        "uuid": uuid_val,
                        "enable": enable,
                        "group": grp,
                        "inbound_id": ib_id
                    }

    all_items = list(unique_clients.values())
    if group_filter:
        items = [item for item in all_items if item["group"] == group_filter]
    else:
        items = all_items

    active_count = sum(1 for item in items if item.get("enable", True))
    filter_disp = f"`{group_filter}`" if group_filter else ("All" if lang == "en" else "Все")

    text = (
        f"🌐 **{t('clients_list_title', lang, filter_name=filter_disp)}**\n\n"
        f"{t('unique_users', lang, total=len(items), active=active_count)}\n"
        f"{t('select_client_to_manage', lang)}"
    )

    markup = keyboards.all_clients_paginated_kb(items, page=page, group_filter=group_filter, lang=lang)
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

async def render_client_detail(callback: CallbackQuery, inbound_id: int, uuid_val: str, group_filter: Optional[str] = None):
    client_api = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client_api:
        await callback.answer("Auth error" if lang == "en" else "Ошибка авторизации", show_alert=True)
        return

    res = await client_api.get_inbounds()
    clients_res = await client_api.get_clients_list()
    await client_api.close()

    if not res.get("success"):
        await callback.message.edit_text("❌ Error loading inbounds." if lang == "en" else "❌ Ошибка загрузки инбаундов.", reply_markup=keyboards.main_menu_kb(lang=lang))
        return

    inbounds = res.get("obj", [])
    attached_inbounds = []
    target_client = None

    for ib in inbounds:
        ib_id = ib.get("id")
        ib_remark = ib.get("remark", f"#{ib_id}")
        protocol = ib.get("protocol", "").upper()
        port = ib.get("port")
        settings = ensure_dict(ib.get("settings"))
        clients = settings.get("clients", [])
        
        for c in clients:
            if (str(c.get("id")) == str(uuid_val)) or (str(c.get("password")) == str(uuid_val)):
                attached_inbounds.append(f"• `{ib_remark}` (`{protocol}:{port}`)")
                if not target_client:
                    target_client = c

    if not target_client:
        await callback.message.edit_text("❌ Client not found." if lang == "en" else "❌ Клиент не найден.", reply_markup=keyboards.inbound_detail_kb(inbound_id, lang=lang))
        return

    email = target_client.get("email", "no-name")
    is_enabled = target_client.get("enable", True)
    status_str = t("status_active", lang) if is_enabled else t("status_disabled", lang)
    group_name = "—"

    if clients_res.get("success") and isinstance(clients_res.get("obj"), list):
        for c in clients_res.get("obj", []):
            c_uuid = str(c.get("uuid") or c.get("id") or "")
            c_email = str(c.get("email") or "")
            if (c_uuid and c_uuid == str(uuid_val)) or (c_email and c_email == email):
                grp = c.get("group")
                if grp and str(grp).strip() and str(grp).strip().lower() not in ["—", "-", "none", "null", "undefined"]:
                    group_name = str(grp).strip()
                    break

    import time
    now_ms = time.time() * 1000
    used_up = 0
    used_down = 0
    last_online_ts = 0

    for ib in inbounds:
        client_stats = ib.get("clientStats", [])
        for stat in client_stats:
            if stat.get("email") == email or str(stat.get("uuid")) == str(uuid_val) or str(stat.get("id")) == str(uuid_val):
                used_up = max(used_up, stat.get("up", 0))
                used_down = max(used_down, stat.get("down", 0))
                last_on = stat.get("lastOnline", 0)
                if last_on > last_online_ts:
                    last_online_ts = last_on

    is_online = False
    if last_online_ts > 0:
        diff_sec = (now_ms - last_online_ts) / 1000
        if 0 <= diff_sec <= 300:
            is_online = True

    online_str = t("online_active", lang) if is_online else t("online_inactive", lang)
    used_total = used_up + used_down
    lbl_used = t("used_traffic", lang)
    traffic_str = f"{lbl_used} `{format_bytes(used_total)}` (⬆️ {format_bytes(used_up)} | ⬇️ {format_bytes(used_down)})"

    total_gb_limit = target_client.get("totalGB", 0)
    limit_str = format_bytes(total_gb_limit) if total_gb_limit > 0 else t("unlimited", lang)
    expiry_str = format_timestamp(target_client.get("expiryTime", 0), lang=lang)
    limit_ip = target_client.get("limitIp", 0)
    dev_word = "devices" if lang == "en" else "устройства"
    limit_ip_str = f"{limit_ip} {dev_word}" if limit_ip > 0 else t("no_limit", lang)

    attached_count = len(attached_inbounds)
    not_bound_msg = "• *Not attached to any inbound*" if lang == "en" else "• *Не привязан ни к одному инбаунду*"
    attached_text = "\n".join(attached_inbounds) if attached_inbounds else not_bound_msg

    import urllib.parse
    active_panel = crypto_storage.get_active_panel()
    sub_port = active_panel.get("sub_port") if active_panel else None
    parsed_host = urllib.parse.urlparse(client_api.host).hostname

    sub_url = client_api.generate_subscription_link(target_client, parsed_host, sub_port=sub_port)

    lbl_prof = t("client_profile_title", lang, email=email)
    lbl_uuid = t("client_uuid", lang)
    lbl_group = t("client_group", lang)
    lbl_online = t("client_online_status", lang)
    lbl_status = t("client_status", lang)
    lbl_attached = t("attached_inbounds", lang, count=attached_count)
    lbl_sub = t("sub_link", lang)
    lbl_limit = t("traffic_limit", lang)
    lbl_exp = t("expires_at", lang)
    lbl_ip = t("ip_limit", lang)

    text = (
        f"{lbl_prof}\n\n"
        f"{lbl_uuid} `{uuid_val}`\n"
        f"{lbl_group} `{group_name}`\n"
        f"{lbl_online} **{online_str}**\n"
        f"{lbl_status} **{status_str}**\n\n"
        f"{lbl_attached}\n"
        f"{attached_text}\n\n"
        f"{lbl_sub}\n`{sub_url}`\n\n"
        f"{traffic_str}\n"
        f"{lbl_limit} `{limit_str}`\n"
        f"{lbl_exp} `{expiry_str}`\n"
        f"{lbl_ip} `{limit_ip_str}`\n"
    )

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(
            text,
            reply_markup=keyboards.client_detail_kb(inbound_id, uuid_val, email, is_enabled, group_filter=group_filter, lang=lang),
            parse_mode="Markdown"
        )
    else:
        from aiogram.exceptions import TelegramBadRequest
        try:
            await callback.message.edit_text(
                text,
                reply_markup=keyboards.client_detail_kb(inbound_id, uuid_val, email, is_enabled, group_filter=group_filter, lang=lang),
                parse_mode="Markdown"
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                pass
            else:
                await callback.message.answer(
                    text,
                    reply_markup=keyboards.client_detail_kb(inbound_id, uuid_val, email, is_enabled),
                    parse_mode="Markdown"
                )

@router.callback_query(F.data.startswith("cv:"))
@router.callback_query(F.data.startswith("client_view:"))
@router.callback_query(F.data.startswith("client_view_"))
async def cb_client_detail(callback: CallbackQuery):
    if ":" in callback.data:
        parts = callback.data.split(":")
        inbound_id = int(parts[1])
        uuid_val = parts[2]
        group_filter = parts[3] if len(parts) > 3 else None
    else:
        parts = callback.data.split("_")
        inbound_id = int(parts[2])
        uuid_val = parts[3]
        group_filter = parts[4] if len(parts) > 4 else None

    await callback.answer("Loading profile..." if bot_settings.get_language() == "en" else "Загрузка профиля...")
    await render_client_detail(callback, inbound_id, uuid_val, group_filter=group_filter)

@router.callback_query(F.data.startswith("client_key_select_"))
async def cb_client_key_select(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[3])
    uuid_val = parts[4]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    inbound = await client_api.get_inbound(inbound_id)
    await client_api.close()

    email = "пользователя"
    if inbound:
        settings = ensure_dict(inbound.get("settings"))
        clients = settings.get("clients", [])
        target_client = next((c for c in clients if c.get("id") == uuid_val or c.get("password") == uuid_val), None)
        if target_client:
            email = target_client.get("email", "no-name")

    await callback.message.edit_text(
        f"🔑 **Выберите тип ключа для `{email}`:**\n\n"
        f"1️⃣ **🌐 Ссылка подписки (Subscription)**\n"
        f"Авто-обновляемая ссылка подписки для Happ, v2rayNG, Streisand, NekoBox.\n\n"
        f"2️⃣ **🔌 Прямой коннект (Direct Link)**\n"
        f"Прямая ссылка ключа (`vless://`, `vmess://`, `trojan://`) для быстрой вставки.",
        reply_markup=keyboards.client_key_choice_kb(inbound_id, uuid_val),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("client_key_type_"))
async def cb_generate_key(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    key_type = parts[3]
    inbound_id = int(parts[4])
    uuid_val = parts[5]

    active_panel = crypto_storage.get_active_panel()
    sub_port = active_panel.get("sub_port") if active_panel else None

    # If generating subscription link for the first time and sub_port is not set:
    if key_type == "sub" and not sub_port:
        await state.update_data(sub_inbound_id=inbound_id, sub_uuid_val=uuid_val, panel_id=active_panel.get("id"))
        await state.set_state(SetSubPortStates.waiting_for_sub_port)

        import urllib.parse
        parsed = urllib.parse.urlparse(active_panel.get("host", ""))
        default_port = parsed.port or 2096

        await callback.message.edit_text(
            f"🌐 **Первоначальная настройка Порта Подписок (Subscription Port)**\n\n"
            f"Укажите **Порт подписок** вашего сервера 3x-ui (например: `2096`, `2053`, `8080`, `8443` или `{default_port}`):\n\n"
            f"*(Бот автоматически сохранит этот порт для сервера `{active_panel.get('name')}`)*",
            reply_markup=keyboards.cancel_kb(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    await callback.answer("Генерация ключа и QR-кода...")
    inbound = await client_api.get_inbound(inbound_id)
    if not inbound:
        await callback.message.answer("❌ Инбаунд не найден.")
        await client_api.close()
        return

    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    target_client = next((c for c in clients if c.get("id") == uuid_val or c.get("password") == uuid_val), None)

    if not target_client:
        await callback.message.answer("❌ Клиент не найден.")
        await client_api.close()
        return

    import urllib.parse
    parsed_host = urllib.parse.urlparse(client_api.host).hostname

    if key_type == "sub":
        # Check if client already has external sub URL set in panel (via externalLinks or subLink)
        client_detail_res = await client_api.get_client(target_client.get("email", ""))
        ext_sub = extract_external_sub(client_detail_res) or extract_external_sub(target_client)
        if ext_sub:
            link = ext_sub
        else:
            link = client_api.generate_subscription_link(target_client, parsed_host, sub_port=sub_port)
        title_str = f"🌐 **Ссылка подписки для `{target_client.get('email')}`**"
    else:
        link = client_api.generate_client_link(inbound, target_client, parsed_host)
        title_str = f"🔌 **Ссылка подключения (Direct) для `{target_client.get('email')}`**"

    await client_api.close()

    # Generate QR Code image
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    photo_file = BufferedInputFile(img_buffer.getvalue(), filename=f"{target_client.get('email', 'vpn')}.png")

    caption = (
        f"{title_str}\n\n"
        f"```\n{link}\n```\n"
        "Отсканируйте QR-код приложением (Happ, v2rayNG, Streisand, NekoBox, FoXray)."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К профилю клиента", callback_data=f"client_view_{inbound_id}_{uuid_val}")]
    ])

    await callback.message.answer_photo(
        photo=photo_file,
        caption=caption,
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.message(SetSubPortStates.waiting_for_sub_port)
async def process_set_sub_port(message: Message, state: FSMContext):
    try:
        sub_port = int(message.text.strip())
        if sub_port <= 0 or sub_port > 65535:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Укажите корректный порт числом от 1 до 65535 (например `2096`):", reply_markup=keyboards.cancel_kb())
        return

    data = await state.get_data()
    await state.clear()

    panel_id = data.get("panel_id")
    inbound_id = data.get("sub_inbound_id")
    uuid_val = data.get("sub_uuid_val")

    if panel_id:
        crypto_storage.update_sub_port(panel_id, sub_port)

    status_msg = await message.answer("🔄 **Генерация ссылки подписки...**", parse_mode="Markdown")
    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await status_msg.edit_text("❌ Ошибка авторизации.")
        return

    inbound = await client_api.get_inbound(inbound_id)
    if not inbound:
        await status_msg.edit_text("❌ Инбаунд не найден.")
        await client_api.close()
        return

    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    target_client = next((c for c in clients if c.get("id") == uuid_val or c.get("password") == uuid_val), None)

    if not target_client:
        await status_msg.edit_text("❌ Клиент не найден.")
        await client_api.close()
        return

    import urllib.parse
    parsed_host = urllib.parse.urlparse(client_api.host).hostname
    link = client_api.generate_subscription_link(target_client, parsed_host, sub_port=sub_port)
    await client_api.close()

    # Generate QR Code image
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    photo_file = BufferedInputFile(img_buffer.getvalue(), filename=f"{target_client.get('email', 'vpn')}.png")

    caption = (
        f"🌐 **Ссылка подписки для `{target_client.get('email')}`**\n\n"
        f"```\n{link}\n```\n"
        "Отсканируйте QR-код приложением (Happ, v2rayNG, Streisand, NekoBox, FoXray)."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К профилю клиента", callback_data=f"client_view_{inbound_id}_{uuid_val}")]
    ])

    await message.answer_photo(
        photo=photo_file,
        caption=caption,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await status_msg.delete()

@router.callback_query(F.data.startswith("client_toggle_"))
async def cb_toggle_client(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[2])
    uuid_val = parts[3]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    inbound = await client_api.get_inbound(inbound_id)
    if not inbound:
        await callback.answer("Инбаунд не найден!", show_alert=True)
        await client_api.close()
        return

    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    target = next((c for c in clients if c.get("id") == uuid_val or c.get("password") == uuid_val), None)

    if not target:
        await callback.answer("Клиент не найден!", show_alert=True)
        await client_api.close()
        return

    new_state = not target.get("enable", True)
    res = await client_api.update_client(
        inbound_id=inbound_id,
        uuid_str=uuid_val,
        email=target.get("email"),
        total_gb=(target.get("totalGB", 0) / (1024**3)),
        limit_ip=target.get("limitIp", 0),
        enable=new_state,
        flow=target.get("flow", "xtls-rprx-vision")
    )
    await client_api.close()

    if res.get("success"):
        state_text = "включен" if new_state else "отключен"
        await callback.answer(f"Клиент {state_text}!")
        await render_client_detail(callback, inbound_id, uuid_val)
    else:
        await callback.answer(f"Ошибка: {res.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("client_reset_"))
async def cb_reset_client(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[2])
    email = parts[3]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    res = await client_api.reset_client_traffic(inbound_id, email)
    await client_api.close()

    if res.get("success"):
        await callback.answer(f"Трафик клиента {email} сброшен!", show_alert=True)
    else:
        await callback.answer(f"Ошибка сброса: {res.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("client_clearip_"))
async def cb_clear_ip(callback: CallbackQuery):
    email = callback.data.split("_")[2]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    res = await client_api.clear_client_ips(email)
    await client_api.close()

    if res.get("success"):
        await callback.answer(f"IP привязки для {email} очищены!", show_alert=True)
    else:
        await callback.answer(f"Ошибка: {res.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("client_delete_confirm_"))
async def cb_confirm_delete(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[3])
    uuid_val = parts[4]

    await callback.message.edit_text(
        "⚠️ **Вы уверены, что хотите удалить этого клиента?**\nЭто действие нельзя будет отменить.",
        reply_markup=keyboards.confirm_delete_client_kb(inbound_id, uuid_val),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("client_delete_do_"))
async def cb_do_delete(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[3])
    uuid_val = parts[4]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    inbound = await client_api.get_inbound(inbound_id)
    email = None
    if inbound:
        settings = ensure_dict(inbound.get("settings"))
        clients = settings.get("clients", [])
        target = next((c for c in clients if c.get("id") == uuid_val or c.get("password") == uuid_val), None)
        if target:
            email = target.get("email")

    res = await client_api.delete_client(inbound_id, uuid_val, email=email)
    await client_api.close()

    if res.get("success"):
        await callback.message.edit_text(
            "✅ **Клиент успешно удален!**",
            reply_markup=keyboards.inbound_detail_kb(inbound_id),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            f"❌ **Ошибка при удалении клиента:**\n`{res.get('msg')}`",
            reply_markup=keyboards.inbound_detail_kb(inbound_id),
            parse_mode="Markdown"
        )
    await callback.answer()

# ADD CLIENT FSM WIZARD
@router.callback_query(F.data == "menu_add_client")
async def cb_add_client_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Auth error" if lang == "en" else "Ошибка авторизации", show_alert=True)
        return

    res = await client_api.get_inbounds()
    await client_api.close()

    inbounds = res.get("obj", []) if res.get("success") else []
    if not inbounds:
        await callback.message.edit_text("❌ No available inbounds for client creation." if lang == "en" else "❌ Нет доступных инбаундов для добавления клиента.", reply_markup=keyboards.main_menu_kb(lang=lang))
        await callback.answer()
        return

    selected_ids = []
    await state.update_data(all_inbounds=inbounds, selected_inbound_ids=selected_ids)

    msg_txt = (
        "➕ **Select Inbounds for New Client:**\n\n"
        "Click on connections to add ➕ or remove ✅ checkmark.\n"
        "You can select one, multiple, or ALL inbounds at once!" if lang == "en" else "➕ **Выберите инбаунды для добавления клиента:**\n\n"
        "Нажимайте на подключения, чтобы добавить ➕ или убрать ✅ галочку.\n"
        "Вы можете выбрать один, несколько или ВСЕ инбаунды сразу!"
    )

    await callback.message.edit_text(
        msg_txt,
        reply_markup=keyboards.add_client_inbounds_multiselect_kb(inbounds, selected_ids, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("add_client_toggle_ib_"))
async def cb_add_client_toggle_ib(callback: CallbackQuery, state: FSMContext):
    target_ib_id = int(callback.data.split("_")[4])
    data = await state.get_data()
    inbounds = data.get("all_inbounds", [])
    selected_ids = data.get("selected_inbound_ids", [])
    lang = bot_settings.get_language()

    if target_ib_id in selected_ids:
        selected_ids.remove(target_ib_id)
        await callback.answer("Inbound removed from selection" if lang == "en" else "Инбаунд убран из выбора")
    else:
        selected_ids.append(target_ib_id)
        await callback.answer("Inbound added to selection" if lang == "en" else "Инбаунд добавлен в выбор")

    await state.update_data(selected_inbound_ids=selected_ids)

    msg_txt = (
        "➕ **Select Inbounds for New Client:**\n\n"
        "Click on connections to add ➕ or remove ✅ checkmark.\n"
        "You can select one, multiple, or ALL inbounds at once!" if lang == "en" else "➕ **Выберите инбаунды для добавления клиента:**\n\n"
        "Нажимайте на подключения, чтобы добавить ➕ или убрать ✅ галочку.\n"
        "Вы можете выбрать один, несколько или ВСЕ инбаунды сразу!"
    )

    from aiogram.exceptions import TelegramBadRequest
    try:
        await callback.message.edit_text(
            msg_txt,
            reply_markup=keyboards.add_client_inbounds_multiselect_kb(inbounds, selected_ids, lang=lang),
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.startswith("add_client_toggle_all_"))
async def cb_add_client_toggle_all(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[4]
    data = await state.get_data()
    inbounds = data.get("all_inbounds", [])
    lang = bot_settings.get_language()

    if action == "on":
        selected_ids = [ib.get("id") for ib in inbounds]
        await callback.answer("All inbounds selected!" if lang == "en" else "Выбраны все инбаунды!")
    else:
        selected_ids = []
        await callback.answer("Selection cleared" if lang == "en" else "Выбор сброшен")

    await state.update_data(selected_inbound_ids=selected_ids)

    msg_txt = (
        "➕ **Select Inbounds for New Client:**\n\n"
        "Click on connections to add ➕ or remove ✅ checkmark.\n"
        "You can select one, multiple, or ALL inbounds at once!" if lang == "en" else "➕ **Выберите инбаунды для добавления клиента:**\n\n"
        "Нажимайте на подключения, чтобы добавить ➕ или убрать ✅ галочку.\n"
        "Вы можете выбрать один, несколько или ВСЕ инбаунды сразу!"
    )

    from aiogram.exceptions import TelegramBadRequest
    try:
        await callback.message.edit_text(
            msg_txt,
            reply_markup=keyboards.add_client_inbounds_multiselect_kb(inbounds, selected_ids, lang=lang),
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "add_client_confirm_inbounds")
async def cb_add_client_confirm_inbounds(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = data.get("selected_inbound_ids", [])
    lang = bot_settings.get_language()

    if not selected_ids:
        await callback.answer("⚠️ Please select at least one inbound!" if lang == "en" else "⚠️ Пожалуйста, выберите хотя бы один инбаунд!", show_alert=True)
        return

    await state.set_state(AddClientStates.waiting_for_email)
    msg_txt = (
        f"➕ **Add New Client** (Step 1 of 5)\n\nSelected inbounds: **{len(selected_ids)}**\n\nEnter **Client Email / Name** (e.g. `alex_vpn`):" if lang == "en" else f"➕ **Добавление нового клиента** (Шаг 1 из 5)\n\nВыбрано подключений: **{len(selected_ids)}**\n\nВведите **Email / Имя клиента** (например: `alex_vpn`):"
    )
    await callback.message.edit_text(
        msg_txt,
        reply_markup=keyboards.cancel_kb(lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("add_client_to_"))
async def cb_add_client_select_inbound(callback: CallbackQuery, state: FSMContext):
    inbound_id = int(callback.data.split("_")[3])
    await state.update_data(selected_inbound_ids=[inbound_id])
    await state.set_state(AddClientStates.waiting_for_email)
    lang = bot_settings.get_language()

    msg_txt = (
        "➕ **Add New Client** (Step 1 of 5)\n\nEnter **Client Email / Name** (e.g. `alex_vpn`):" if lang == "en" else "➕ **Добавление нового клиента** (Шаг 1 из 5)\n\nВведите **Email / Имя клиента** (например: `alex_vpn`):"
    )

    await callback.message.edit_text(
        msg_txt,
        reply_markup=keyboards.cancel_kb(lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AddClientStates.waiting_for_email)
async def process_add_email(message: Message, state: FSMContext):
    email = message.text.strip()
    lang = bot_settings.get_language()

    if not email:
        await message.answer("❌ Client name cannot be empty. Enter client name:" if lang == "en" else "❌ Имя клиента не может быть пустым. Введите новое имя:", reply_markup=keyboards.cancel_kb(lang=lang))
        return

    await state.update_data(email=email)
    await state.set_state(AddClientStates.waiting_for_limit_gb)

    msg_txt = (
        "➕ **Add New Client** (Step 2 of 5)\n\nSpecify **Traffic Limit in GB** (e.g. `50` or `0` for unlimited):" if lang == "en" else "➕ **Добавление нового клиента** (Шаг 2 из 5)\n\nУкажите **Лимит трафика в ГБ** (например: `50` или `0` для безлимита):"
    )

    await message.answer(
        msg_txt,
        reply_markup=keyboards.cancel_kb(lang=lang),
        parse_mode="Markdown"
    )

@router.message(AddClientStates.waiting_for_limit_gb)
async def process_add_gb(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    try:
        limit_gb = float(message.text.strip().replace(',', '.'))
        if limit_gb < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Enter traffic limit in GB (e.g. `100` or `0`):" if lang == "en" else "❌ Укажите число ГБ (например `100` или `0`):", reply_markup=keyboards.cancel_kb(lang=lang))
        return

    await state.update_data(limit_gb=limit_gb)
    await state.set_state(AddClientStates.waiting_for_expiry_days)

    msg_txt = (
        "➕ **Add New Client** (Step 3 of 5)\n\nSpecify **Validity period in days** (e.g. `30` or `0` for unlimited):" if lang == "en" else "➕ **Добавление нового клиента** (Шаг 3 из 5)\n\nУкажите **Срок действия в днях** (например: `30` или `0` для бессрочного):"
    )

    await message.answer(
        msg_txt,
        reply_markup=keyboards.cancel_kb(lang=lang),
        parse_mode="Markdown"
    )

@router.message(AddClientStates.waiting_for_expiry_days)
async def process_add_expiry(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    try:
        expiry_days = int(message.text.strip())
        if expiry_days < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Enter number of days (e.g. `30` or `0`):" if lang == "en" else "❌ Укажите количество дней числом (например `30` или `0`):", reply_markup=keyboards.cancel_kb(lang=lang))
        return

    await state.update_data(expiry_days=expiry_days)
    await state.set_state(AddClientStates.waiting_for_limit_ip)

    msg_txt = (
        "➕ **Add New Client** (Step 4 of 5)\n\nSpecify **IP / Devices Limit** (e.g. `2` or `0` for no limit):" if lang == "en" else "➕ **Добавление нового клиента** (Шаг 4 из 5)\n\nУкажите **Лимит IP / Устройств** (например: `2` или `0` для безлимита):"
    )

    await message.answer(
        msg_txt,
        reply_markup=keyboards.cancel_kb(lang=lang),
        parse_mode="Markdown"
    )

@router.message(AddClientStates.waiting_for_limit_ip)
async def process_add_limit_ip(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    try:
        limit_ip = int(message.text.strip())
        if limit_ip < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Enter device limit number (e.g. `2` or `0`):" if lang == "en" else "❌ Укажите лимит устройств числом (например `2` или `0`):", reply_markup=keyboards.cancel_kb(lang=lang))
        return

    await state.update_data(limit_ip=limit_ip)
    await state.set_state(AddClientStates.waiting_for_initial_status)

    msg_txt = (
        "➕ **Add New Client** (Step 5 of 5)\n\nSelect **Initial Connection Status**:\n\n• 🟢 **Enabled** (Active immediately)\n• 🔴 **Disabled** (Not active)" if lang == "en" else "➕ **Добавление нового клиента** (Шаг 5 из 5)\n\nВыберите **Начальный статус соединения**:\n\n• 🟢 **Включен** (Сразу активен)\n• 🔴 **Отключен** (Изначально не подключен ни к какому коннекту)"
    )

    await message.answer(
        msg_txt,
        reply_markup=keyboards.initial_status_kb(lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(AddClientStates.waiting_for_initial_status, F.data.startswith("client_init_enable_"))
async def cb_process_add_status(callback: CallbackQuery, state: FSMContext):
    enable_val = (callback.data.split("_")[3] == "1")
    lang = bot_settings.get_language()

    data = await state.get_data()
    await state.clear()

    selected_ids = data.get("selected_inbound_ids", [])
    if not selected_ids:
        selected_ids = [data.get("inbound_id", 1)]
    first_inbound_id = selected_ids[0]

    email = data.get("email")
    limit_gb = data.get("limit_gb")
    expiry_days = data.get("expiry_days")
    limit_ip = data.get("limit_ip")
    client_uuid = str(uuid.uuid4())

    status_msg = await callback.message.edit_text("🔄 **Creating new client...**" if lang == "en" else "🔄 **Создание нового клиента...**", parse_mode="Markdown")

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await status_msg.edit_text("❌ Auth error." if lang == "en" else "❌ Ошибка авторизации. Панель не настроена.")
        await callback.answer()
        return

    res = await client_api.add_client(
        inbound_id=first_inbound_id,
        email=email,
        uuid_str=client_uuid,
        total_gb=limit_gb,
        expiry_days=expiry_days,
        limit_ip=limit_ip,
        enable=enable_val
    )

    if res.get("success"):
        if len(selected_ids) > 1:
            await client_api.attach_client_to_inbounds(email, selected_ids)

        st_text = t("status_active", lang) if enable_val else t("status_disabled", lang)
        msg_txt = (
            f"✅ **Client `{email}` created successfully!**\n\n"
            f"🆔 UUID: `{client_uuid}`\n"
            f"Status: **{st_text}**\n"
            f"🌐 Attached inbounds: **{len(selected_ids)}**\n"
            f"📊 GB Limit: `{limit_gb if limit_gb > 0 else 'Unlimited'}`\n"
            f"📅 Period: `{expiry_days if expiry_days > 0 else 'Unlimited'} days`" if lang == "en" else f"✅ **Клиент `{email}` успешно создан!**\n\n"
            f"🆔 UUID: `{client_uuid}`\n"
            f"Статус соединения: **{st_text}**\n"
            f"🌐 Привязан к инбаундам: **{len(selected_ids)} шт.**\n"
            f"📊 Лимит ГБ: `{limit_gb if limit_gb > 0 else 'Безлимит'}`\n"
            f"📅 Срок: `{expiry_days if expiry_days > 0 else 'Бессрочно'} дн.`"
        )

        await status_msg.edit_text(
            msg_txt,
            reply_markup=keyboards.client_detail_kb(first_inbound_id, client_uuid, email, enable_val, lang=lang),
            parse_mode="Markdown"
        )
    else:
        await status_msg.edit_text(
            f"❌ **Error creating client:**\n`{res.get('msg')}`" if lang == "en" else f"❌ **Ошибка при создании клиента:**\n`{res.get('msg')}`",
            reply_markup=keyboards.inbound_detail_kb(first_inbound_id, lang=lang),
            parse_mode="Markdown"
        )
    await client_api.close()
    await callback.answer()

# SEARCH CLIENT
@router.callback_query(F.data == "menu_search_client")
async def cb_search_client_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    await state.set_state(SearchClientStates.waiting_for_query)
    msg_txt = (
        "🔍 **Search Client**\n\nEnter Client Name (Email) or UUID to search:" if lang == "en" else "🔍 **Поиск клиента**\n\nВведите Имя (Email) или UUID клиента для поиска:"
    )
    await callback.message.edit_text(
        msg_txt,
        reply_markup=keyboards.cancel_kb(lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(SearchClientStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip().lower()
    await state.clear()
    lang = bot_settings.get_language()

    status_msg = await message.answer("🔄 **Searching client across inbounds...**" if lang == "en" else "🔄 **Поиск клиента по всем инбаундам...**", parse_mode="Markdown")

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await status_msg.edit_text("❌ Auth error." if lang == "en" else "❌ Ошибка авторизации. Настройки не найдены.")
        return

    res = await client_api.get_inbounds()
    await client_api.close()

    if not res.get("success"):
        await status_msg.edit_text(f"❌ Search error: {res.get('msg')}" if lang == "en" else f"❌ Ошибка поиска: {res.get('msg')}")
        return

    inbounds = res.get("obj", [])
    found_items = []

    for ib in inbounds:
        ib_id = ib.get("id")
        settings = ensure_dict(ib.get("settings"))
        clients = settings.get("clients", [])
        for c in clients:
            c_email = str(c.get("email", "")).lower()
            c_id = str(c.get("id", "") or c.get("password", "")).lower()
            if query in c_email or query in c_id:
                found_items.append((ib_id, c))

    if not found_items:
        msg_txt = (
            f"🔍 **Search results for `{query}`:**\n\nNothing found." if lang == "en" else f"🔍 **Результаты поиска по запросу `{query}`:**\n\nНичего не найдено."
        )
        await status_msg.edit_text(
            msg_txt,
            reply_markup=keyboards.main_menu_kb(lang=lang),
            parse_mode="Markdown"
        )
        return

    buttons = []
    for ib_id, c in found_items[:10]:
        email = c.get("email", "no-name")
        uuid_val = c.get("id") or c.get("password") or ""
        enable = "🟢" if c.get("enable", True) else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{enable} {email} (Inbound #{ib_id})",
            callback_data=f"client_view_{ib_id}_{uuid_val}"
        )])

    buttons.append([InlineKeyboardButton(text=t("btn_main_menu", lang), callback_data="menu_main")])

    msg_txt = (
        f"🔍 **Search results for `{query}`:**\nFound matches: **{len(found_items)}**" if lang == "en" else f"🔍 **Результаты поиска по запросу `{query}`:**\nНайдено совпадений: **{len(found_items)}**"
    )

    await status_msg.edit_text(
        msg_txt,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )

# EDIT CLIENT GB LIMIT
@router.callback_query(F.data.startswith("client_edit_gb_"))
async def cb_edit_gb_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    inbound_id = int(parts[3])
    uuid_val = parts[4]

    await state.update_data(inbound_id=inbound_id, uuid_val=uuid_val)
    await state.set_state(EditClientGBStates.waiting_for_gb)

    await callback.message.edit_text(
        "📈 **Изменение лимита трафика**\n\n"
        "Введите новый лимит трафика в **ГБ** (например: `100` или `0` для безлимита):",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(EditClientGBStates.waiting_for_gb)
async def process_edit_gb(message: Message, state: FSMContext):
    try:
        new_gb = float(message.text.strip().replace(',', '.'))
        if new_gb < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Укажите количество ГБ числом (например `100` или `0`):", reply_markup=keyboards.cancel_kb())
        return

    data = await state.get_data()
    await state.clear()
    inbound_id = data.get("inbound_id")
    uuid_val = data.get("uuid_val")

    status_msg = await message.answer("🔄 **Обновление лимита трафика...**", parse_mode="Markdown")

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await status_msg.edit_text("❌ Ошибка авторизации.")
        return

    inbound = await client_api.get_inbound(inbound_id)
    if not inbound:
        await status_msg.edit_text("❌ Инбаунд не найден.")
        await client_api.close()
        return

    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    target = next((c for c in clients if c.get("id") == uuid_val or c.get("password") == uuid_val), None)

    if not target:
        await status_msg.edit_text("❌ Клиент не найден.")
        await client_api.close()
        return

    res = await client_api.update_client(
        inbound_id=inbound_id,
        uuid_str=uuid_val,
        email=target.get("email"),
        total_gb=new_gb,
        expiry_time_ms=target.get("expiryTime", 0),
        limit_ip=target.get("limitIp", 0),
        enable=target.get("enable", True),
        flow=target.get("flow", "xtls-rprx-vision")
    )
    await client_api.close()

    if res.get("success"):
        gb_str = f"{new_gb} ГБ" if new_gb > 0 else "Безлимитно"
        await status_msg.edit_text(
            f"✅ **Лимит трафика для `{target.get('email')}` успешно изменен на `{gb_str}`!**",
            reply_markup=keyboards.client_detail_kb(inbound_id, uuid_val, target.get('email'), target.get('enable', True)),
            parse_mode="Markdown"
        )
    else:
        await status_msg.edit_text(
            f"❌ **Ошибка при изменении лимита:**\n`{res.get('msg')}`",
            reply_markup=keyboards.client_detail_kb(inbound_id, uuid_val, target.get('email'), target.get('enable', True)),
            parse_mode="Markdown"
        )

# EDIT CLIENT EXPIRY DAYS
@router.callback_query(F.data.startswith("client_edit_exp_"))
async def cb_edit_exp_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    inbound_id = int(parts[3])
    uuid_val = parts[4]

    await state.update_data(inbound_id=inbound_id, uuid_val=uuid_val)
    await state.set_state(EditClientExpiryStates.waiting_for_days)

    await callback.message.edit_text(
        "📅 **Изменение срока действия**\n\n"
        "Введите количество **дней** с сегодняшнего дня (например: `30`, `90` или `0` для бессрочного):",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(EditClientExpiryStates.waiting_for_days)
async def process_edit_exp(message: Message, state: FSMContext):
    try:
        new_days = int(message.text.strip())
        if new_days < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Укажите количество дней числом (например `30` или `0`):", reply_markup=keyboards.cancel_kb())
        return

    data = await state.get_data()
    await state.clear()
    inbound_id = data.get("inbound_id")
    uuid_val = data.get("uuid_val")

    status_msg = await message.answer("🔄 **Обновление срока действия...**", parse_mode="Markdown")

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await status_msg.edit_text("❌ Ошибка авторизации.")
        return

    inbound = await client_api.get_inbound(inbound_id)
    if not inbound:
        await status_msg.edit_text("❌ Инбаунд не найден.")
        await client_api.close()
        return

    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    target = next((c for c in clients if c.get("id") == uuid_val or c.get("password") == uuid_val), None)

    if not target:
        await status_msg.edit_text("❌ Клиент не найден.")
        await client_api.close()
        return

    curr_gb = target.get("totalGB", 0) / (1024**3)

    res = await client_api.update_client(
        inbound_id=inbound_id,
        uuid_str=uuid_val,
        email=target.get("email"),
        total_gb=curr_gb,
        expiry_days=new_days,
        limit_ip=target.get("limitIp", 0),
        enable=target.get("enable", True),
        flow=target.get("flow", "xtls-rprx-vision")
    )
    await client_api.close()

    if res.get("success"):
        exp_str = f"{new_days} дней" if new_days > 0 else "Бессрочно"
        await status_msg.edit_text(
            f"✅ **Срок действия для `{target.get('email')}` успешно изменен на `{exp_str}`!**",
            reply_markup=keyboards.client_detail_kb(inbound_id, uuid_val, target.get('email'), target.get('enable', True)),
            parse_mode="Markdown"
        )
    else:
        await status_msg.edit_text(
            f"❌ **Ошибка при изменении срока:**\n`{res.get('msg')}`",
            reply_markup=keyboards.client_detail_kb(inbound_id, uuid_val, target.get('email'), target.get('enable', True)),
            parse_mode="Markdown"
        )

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer("Это текущее подключение клиента.")

# MOVE / CHANGE CLIENT INBOUND
@router.callback_query(F.data.startswith("client_move_inbound_"))
async def cb_move_inbound_start(callback: CallbackQuery):
    parts = callback.data.split("_")
    current_inbound_id = int(parts[3])
    uuid_val = parts[4]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    await callback.answer("Загрузка списка подключений...")
    res = await client_api.get_inbounds()
    await client_api.close()

    if not res.get("success"):
        await callback.message.edit_text(f"❌ Ошибка загрузки инбаундов: {res.get('msg')}")
        return

    inbounds = res.get("obj", [])
    if not inbounds:
        await callback.message.edit_text("❌ Нет доступных инбаундов.")
        return

    await callback.message.edit_text(
        "🌐 **Изменение подключения (Инбаунда) клиента**\n\n"
        "Выберите новое подключение, в которое нужно перенести клиента:",
        reply_markup=keyboards.select_new_inbound_kb(current_inbound_id, uuid_val, inbounds),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("client_do_move_"))
async def cb_do_move_inbound(callback: CallbackQuery):
    parts = callback.data.split("_")
    old_inbound_id = int(parts[3])
    new_inbound_id = int(parts[4])
    uuid_val = parts[5]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    await callback.answer("Перенос клиента...")

    # 1. Fetch client from old inbound
    old_inbound = await client_api.get_inbound(old_inbound_id)
    if not old_inbound:
        await callback.message.edit_text("❌ Старый инбаунд не найден.")
        await client_api.close()
        return

    settings = ensure_dict(old_inbound.get("settings"))
    clients = settings.get("clients", [])
    target = next((c for c in clients if c.get("id") == uuid_val or c.get("password") == uuid_val), None)

    if not target:
        await callback.message.edit_text("❌ Клиент не найден в старом инбаунде.")
        await client_api.close()
        return

    email = target.get("email")
    total_bytes = target.get("totalGB", 0)
    total_gb = total_bytes / (1024**3) if total_bytes > 0 else 0
    limit_ip = target.get("limitIp", 0)
    enable = target.get("enable", True)
    flow = target.get("flow", "xtls-rprx-vision")
    expiry_time_ms = target.get("expiryTime", 0)

    # 2. Add client to new inbound
    add_res = await client_api.add_client(
        inbound_id=new_inbound_id,
        email=email,
        uuid_str=uuid_val,
        total_gb=total_gb,
        expiry_days=0,
        limit_ip=limit_ip,
        flow=flow,
        enable=enable
    )

    if not add_res.get("success"):
        await callback.message.edit_text(
            f"❌ **Ошибка добавления в новый инбаунд:**\n`{add_res.get('msg')}`",
            reply_markup=keyboards.client_detail_kb(old_inbound_id, uuid_val, email, enable),
            parse_mode="Markdown"
        )
        await client_api.close()
        return

    # If expiry_time_ms was set, update client to preserve exact expiry timestamp
    if expiry_time_ms > 0:
        await client_api.update_client(
            inbound_id=new_inbound_id,
            uuid_str=uuid_val,
            email=email,
            total_gb=total_gb,
            expiry_time_ms=expiry_time_ms,
            limit_ip=limit_ip,
            enable=enable,
            flow=flow
        )

    # 3. Delete client from old inbound
    del_res = await client_api.delete_client(old_inbound_id, uuid_val)
    await client_api.close()

    new_inbound = await ThreeXUIClient.from_storage().get_inbound(new_inbound_id) if ThreeXUIClient.from_storage() else None
    new_remark = new_inbound.get("remark", f"#{new_inbound_id}") if new_inbound else f"#{new_inbound_id}"

    await callback.message.edit_text(
        f"✅ **Клиент `{email}` успешно перенесен в подключение `{new_remark}`!**",
        reply_markup=keyboards.client_detail_kb(new_inbound_id, uuid_val, email, enable),
        parse_mode="Markdown"
    )

# MANAGE CLIENT INBOUND ATTACHMENTS
@router.callback_query(F.data.startswith("client_manage_ibs_"))
async def cb_manage_client_inbounds(callback: CallbackQuery):
    parts = callback.data.split("_")
    curr_inbound_id = int(parts[3])
    uuid_val = parts[4]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    await callback.answer("Загрузка инбаундов...")
    res = await client_api.get_inbounds()
    await client_api.close()

    if not res.get("success"):
        await callback.message.edit_text("❌ Ошибка получения инбаундов.")
        return

    inbounds = res.get("obj", [])
    attached_ids = []
    target_client = None

    for ib in inbounds:
        ib_id = ib.get("id")
        settings = ensure_dict(ib.get("settings"))
        clients = settings.get("clients", [])
        for c in clients:
            if c.get("id") == uuid_val or c.get("password") == uuid_val:
                attached_ids.append(ib_id)
                if not target_client:
                    target_client = c

    if not target_client:
        await callback.message.edit_text("❌ Клиент не найден.")
        return

    email = target_client.get("email", "no-name")

    text = (
        f"🌐 **Привязка клиента к инбаундам** (`{email}`)\n\n"
        f"Нажмите на инбаунд для включения/отключения привязки:\n"
        f"• ✅ — Клиент подключен\n"
        f"• ❌ — Клиент не подключен"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.manage_client_inbounds_kb(curr_inbound_id, uuid_val, email, inbounds, attached_ids),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("client_ib_attach_") | F.data.startswith("client_ib_detach_"))
async def cb_toggle_attach_inbound(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[2]  # 'attach' or 'detach'
    
    if action == "attach" and parts[3] == "all":
        curr_inbound_id = int(parts[4])
        uuid_val = parts[5]
        target_ib_id = None
    else:
        curr_inbound_id = int(parts[3])
        target_ib_id = int(parts[4])
        uuid_val = parts[5]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    inbounds_res = await client_api.get_inbounds()
    inbounds = inbounds_res.get("obj", []) if inbounds_res.get("success") else []
    
    target_client = None
    for ib in inbounds:
        settings = ensure_dict(ib.get("settings"))
        clients = settings.get("clients", [])
        for c in clients:
            if c.get("id") == uuid_val or c.get("password") == uuid_val:
                target_client = c
                break
        if target_client:
            break

    if not target_client:
        await callback.answer("Клиент не найден!", show_alert=True)
        await client_api.close()
        return

    email = target_client.get("email")

    if action == "attach" and target_ib_id is not None:
        await callback.answer("Привязка инбаунда...")
        attach_res = await client_api.attach_client_to_inbounds(email, [target_ib_id])
        if not attach_res.get("success"):
            total_bytes = target_client.get("totalGB", 0)
            total_gb = total_bytes / (1024**3) if total_bytes > 0 else 0
            limit_ip = target_client.get("limitIp", 0)
            enable = target_client.get("enable", True)
            flow = target_client.get("flow", "xtls-rprx-vision")
            await client_api.add_client(
                inbound_id=target_ib_id,
                email=email,
                uuid_str=uuid_val,
                total_gb=total_gb,
                limit_ip=limit_ip,
                flow=flow,
                enable=enable
            )
    elif action == "detach" and target_ib_id is not None:
        await callback.answer("Отвязка инбаунда...")
        detach_res = await client_api.detach_client_from_inbounds(email, [target_ib_id])
        if not detach_res.get("success"):
            await client_api.delete_client(target_ib_id, uuid_val, email=email)
    elif action == "attach" and target_ib_id is None: # attach_all
        await callback.answer("Привязка ко всем инбаундам...")
        all_ids = [ib.get("id") for ib in inbounds]
        await client_api.attach_client_to_inbounds(email, all_ids)

    updated_res = await client_api.get_inbounds()
    await client_api.close()

    updated_inbounds = updated_res.get("obj", []) if updated_res.get("success") else []
    attached_ids = []
    for ib in updated_inbounds:
        settings = ensure_dict(ib.get("settings"))
        clients = settings.get("clients", [])
        for c in clients:
            if c.get("id") == uuid_val or c.get("password") == uuid_val:
                attached_ids.append(ib.get("id"))

    text = (
        f"🌐 **Привязка клиента к инбаундам** (`{email}`)\n\n"
        f"Нажмите на инбаунд для включения/отключения привязки:\n"
        f"• ✅ — Клиент подключен\n"
        f"• ❌ — Клиент не подключен"
    )

    from aiogram.exceptions import TelegramBadRequest
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.manage_client_inbounds_kb(curr_inbound_id, uuid_val, email, updated_inbounds, attached_ids),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise e
