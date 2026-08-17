import json
from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.api_client import ThreeXUIClient, format_bytes, ensure_dict
from core import bot_settings
from core.i18n import t
from keyboards import inline as keyboards

router = Router()

@router.callback_query(F.data == "menu_inbounds")
async def cb_list_inbounds(callback: CallbackQuery):
    client = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client:
        await callback.message.edit_text(
            "❌ Panel credentials not found." if lang == "en" else "❌ Данные панели не найдены.",
            reply_markup=keyboards.main_menu_kb(has_creds=False, lang=lang)
        )
        await callback.answer()
        return

    await callback.answer("Loading inbounds..." if lang == "en" else "Загрузка инбаундов...")
    res = await client.get_inbounds()
    await client.close()

    if not res.get("success"):
        await callback.message.edit_text(
            f"❌ **Error loading inbounds:**\n`{res.get('msg')}`" if lang == "en" else f"❌ **Ошибка загрузки инбаундов:**\n`{res.get('msg')}`",
            reply_markup=keyboards.main_menu_kb(lang=lang),
            parse_mode="Markdown"
        )
        return

    inbounds = res.get("obj", [])
    if not inbounds:
        await callback.message.edit_text(
            "🌐 **No inbounds found.**" if lang == "en" else "🌐 **Инбаунды не найдены.**\nВ панели еще не создано ни одного подключения.",
            reply_markup=keyboards.main_menu_kb(lang=lang),
            parse_mode="Markdown"
        )
        return

    title = t("inbounds_list_title", lang)
    cnt_lbl = t("total_inbounds_count", lang, count=len(inbounds))
    sub_lbl = t("select_inbound_to_manage", lang)

    text = f"{title}\n\n{cnt_lbl}\n{sub_lbl}"

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.inbounds_list_kb(inbounds, lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("inbound_view_"))
async def cb_view_inbound(callback: CallbackQuery):
    inbound_id = int(callback.data.split("_")[2])
    client = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client:
        await callback.answer("Auth error" if lang == "en" else "Ошибка авторизации", show_alert=True)
        return

    await callback.answer()
    inbound = await client.get_inbound(inbound_id)
    await client.close()

    if not inbound:
        await callback.message.edit_text("❌ Inbound not found." if lang == "en" else "❌ Инбаунд не найден.", reply_markup=keyboards.main_menu_kb(lang=lang))
        return

    from core import crypto_storage
    active_panel = crypto_storage.get_active_panel()
    server_name = active_panel.get("name", "—") if active_panel else "—"

    remark = inbound.get("remark", f"Inbound #{inbound_id}")
    protocol = inbound.get("protocol", "").upper()
    port = inbound.get("port")
    listen = inbound.get("listen") or ("0.0.0.0 (All interfaces)" if lang == "en" else "0.0.0.0 (Все интерфейсы)")
    enable = t("status_active", lang) if inbound.get("enable", True) else t("status_disabled", lang)
    up = format_bytes(inbound.get("up", 0))
    down = format_bytes(inbound.get("down", 0))
    total = format_bytes(inbound.get("up", 0) + inbound.get("down", 0))

    # Parse client count
    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    active_clients = sum(1 for c in clients if c.get("enable", True))

    stream_settings = ensure_dict(inbound.get("streamSettings"))
    net = stream_settings.get("network", "tcp")
    sec = stream_settings.get("security", "none")

    # Extended Security & Stream Details (Target, uTLS, Xver, SNI)
    target = "—"
    utls = "—"
    xver = "—"
    sni_str = "—"

    if sec == "reality":
        real_set = ensure_dict(stream_settings.get("realitySettings"))
        target = real_set.get("target") or "—"
        xver = str(real_set.get("xver", 0))
        inner_set = ensure_dict(real_set.get("settings"))
        utls = inner_set.get("fingerprint") or "—"
        server_names = real_set.get("serverNames", [])
        if server_names:
            first_sni = server_names[0]
            dom_word = "domains" if lang == "en" else "доменов"
            sni_str = f"`{first_sni}` (+{len(server_names)-1} {dom_word})" if len(server_names) > 1 else f"`{first_sni}`"
    elif sec == "tls":
        tls_set = ensure_dict(stream_settings.get("tlsSettings"))
        utls = tls_set.get("fingerprint") or "—"
        target = tls_set.get("serverName") or "—"
        if target != "—":
            sni_str = f"`{target}`"

    # Sniffing Details
    sniffing = ensure_dict(inbound.get("sniffing"))
    is_sniff_on = bool(sniffing.get("enabled", False))
    sniff_enabled = t("status_active", lang) if is_sniff_on else t("status_disabled", lang)

    lbl_card = t("inbound_card_title", lang, remark=remark)
    lbl_server = t("server_label", lang)
    lbl_node = t("node_listen", lang)
    lbl_proto = t("proto_port", lang)
    lbl_net = t("net_sec", lang)
    lbl_target = t("target_dest", lang)
    lbl_utls = t("utls_fp", lang)
    lbl_xver = t("proxy_xver", lang)
    lbl_sni = t("sni_names", lang)
    lbl_sniff = t("sniffing_info", lang)
    lbl_sniff_p = t("sniff_protocols", lang)
    lbl_used = t("used_traffic", lang)

    if is_sniff_on:
        dest_override = sniffing.get("destOverride") or []
        dest_str = ", ".join([str(d).upper() for d in dest_override]) if dest_override else "—"
        meta_only = "🟢 YES" if (sniffing.get("metadataOnly") and lang == "en") else ("🟢 ДА" if sniffing.get("metadataOnly") else ("⚪ NO" if lang == "en" else "⚪ НЕТ"))
        route_only = "🟢 YES" if (sniffing.get("routeOnly") and lang == "en") else ("🟢 ДА" if sniffing.get("routeOnly") else ("⚪ NO" if lang == "en" else "⚪ НЕТ"))
        sniff_details = (
            f"   {lbl_sniff_p} `{dest_str}`\n"
            f"   • **Metadata only:** {meta_only}\n"
            f"   • **Route only:** {route_only}\n"
        )
    else:
        sniff_details = ""

    text = (
        f"{lbl_card}\n\n"
        f"{lbl_server} `{server_name}`\n"
        f"{lbl_node} `{listen}`\n"
        f"🆔 **ID:** `{inbound_id}` | Status: **{enable}**\n"
        f"{lbl_proto} `{protocol}` (Port: `{port}`)\n"
        f"{lbl_net} `{net}` / `{sec}`\n\n"
        f"{lbl_target} `{target}`\n"
        f"{lbl_utls} `{utls}`\n"
        f"{lbl_xver} `{xver}`\n"
        f"{lbl_sni} {sni_str}\n\n"
        f"{lbl_sniff} {sniff_enabled}\n"
        f"{sniff_details}\n"
        f"{lbl_used} ⬆️ {up} | ⬇️ {down} | Total: `{total}`\n"
        f"👥 Clients: Total: **{len(clients)}** (Active: **{active_clients}**)\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.inbound_detail_kb(inbound_id, lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("clients_list_"))
async def cb_clients_list(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[2])
    page = int(parts[3])

    client = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client:
        await callback.answer("Auth error" if lang == "en" else "Ошибка авторизации", show_alert=True)
        return

    await callback.answer()
    inbound = await client.get_inbound(inbound_id)
    await client.close()

    if not inbound:
        await callback.message.edit_text("❌ Inbound not found." if lang == "en" else "❌ Инбаунд не найден.", reply_markup=keyboards.main_menu_kb(lang=lang))
        return

    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    remark = inbound.get("remark", f"#{inbound_id}")

    if not clients:
        await callback.message.edit_text(
            f"👥 **Inbound {remark} — Clients List**\n\nNo clients yet." if lang == "en" else f"👥 **Инбаунд {remark} — Список клиентов**\n\nКлиентов пока нет.",
            reply_markup=keyboards.inbound_detail_kb(inbound_id, lang=lang),
            parse_mode="Markdown"
        )
        return

    text = (
        f"👥 **Inbound {remark} — Clients List**\n\n"
        f"Total users: **{len(clients)}**\n"
        "Select a client below to view and manage:" if lang == "en" else f"👥 **Инбаунд {remark} — Список клиентов**\n\nВсего пользователей: **{len(clients)}**\nВыберите клиента из списка ниже для просмотра и управления:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.clients_list_kb(inbound_id, clients, page, lang=lang),
        parse_mode="Markdown"
    )
