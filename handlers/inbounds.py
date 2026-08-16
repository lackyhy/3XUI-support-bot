import json
from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.api_client import ThreeXUIClient, format_bytes, ensure_dict
from keyboards import inline as keyboards

router = Router()

@router.callback_query(F.data == "menu_inbounds")
async def cb_list_inbounds(callback: CallbackQuery):
    client = ThreeXUIClient.from_storage()
    if not client:
        await callback.message.edit_text(
            "❌ Данные панели не найдены.",
            reply_markup=keyboards.main_menu_kb(has_creds=False)
        )
        await callback.answer()
        return

    await callback.answer("Загрузка инбаундов...")
    res = await client.get_inbounds()
    await client.close()

    if not res.get("success"):
        await callback.message.edit_text(
            f"❌ **Ошибка загрузки инбаундов:**\n`{res.get('msg')}`",
            reply_markup=keyboards.main_menu_kb(),
            parse_mode="Markdown"
        )
        return

    inbounds = res.get("obj", [])
    if not inbounds:
        await callback.message.edit_text(
            "🌐 **Инбаунды не найдены.**\nВ панели еще не создано ни одного подключения.",
            reply_markup=keyboards.main_menu_kb(),
            parse_mode="Markdown"
        )
        return

    text = (
        "🌐 **Список подключений (Inbounds)**\n\n"
        f"Всего подключений: **{len(inbounds)}**\n"
        "Выберите нужное подключение для управления клиентами:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.inbounds_list_kb(inbounds),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("inbound_view_"))
async def cb_view_inbound(callback: CallbackQuery):
    inbound_id = int(callback.data.split("_")[2])
    client = ThreeXUIClient.from_storage()
    if not client:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    await callback.answer()
    inbound = await client.get_inbound(inbound_id)
    await client.close()

    if not inbound:
        await callback.message.edit_text("❌ Инбаунд не найден.", reply_markup=keyboards.main_menu_kb())
        return

    from core import crypto_storage
    active_panel = crypto_storage.get_active_panel()
    server_name = active_panel.get("name", "—") if active_panel else "—"

    remark = inbound.get("remark", f"Inbound #{inbound_id}")
    protocol = inbound.get("protocol", "").upper()
    port = inbound.get("port")
    listen = inbound.get("listen") or "0.0.0.0 (Все интерфейсы)"
    enable = "🟢 Включен" if inbound.get("enable", True) else "🔴 Отключен"
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
            sni_str = f"`{first_sni}` (+{len(server_names)-1} доменов)" if len(server_names) > 1 else f"`{first_sni}`"
    elif sec == "tls":
        tls_set = ensure_dict(stream_settings.get("tlsSettings"))
        utls = tls_set.get("fingerprint") or "—"
        target = tls_set.get("serverName") or "—"
        if target != "—":
            sni_str = f"`{target}`"

    # Sniffing Details
    sniffing = ensure_dict(inbound.get("sniffing"))
    sniff_enabled = "🟢 Включен" if sniffing.get("enabled", True) else "🔴 Выключен"
    dest_override = sniffing.get("destOverride") or []
    dest_str = ", ".join([str(d).upper() for d in dest_override]) if dest_override else "—"
    meta_only = "🟢 ДА" if sniffing.get("metadataOnly") else "⚪ НЕТ"
    route_only = "🟢 ДА" if sniffing.get("routeOnly") else "⚪ НЕТ"

    text = (
        f"🌐 **Инбаунд: {remark}**\n\n"
        f"🖥 **Сервер:** `{server_name}`\n"
        f"🌐 **Узел (Listen):** `{listen}`\n"
        f"🆔 **ID:** `{inbound_id}` | Status: **{enable}**\n"
        f"🛠 **Протокол:** `{protocol}` (Port: `{port}`)\n"
        f"🌐 **Сеть / Защита:** `{net}` / `{sec}`\n\n"
        f"🎯 **Target (Dest):** `{target}`\n"
        f"🔑 **uTLS (Fingerprint):** `{utls}`\n"
        f"⚡ **PROXY Protocol (Xver):** `{xver}`\n"
        f"🌐 **SNI (ServerNames):** {sni_str}\n\n"
        f"🔍 **Sniffing (Сниффинг):** {sniff_enabled}\n"
        f"   • **Перехват:** `{dest_str}`\n"
        f"   • **Metadata only:** {meta_only}\n"
        f"   • **Route only:** {route_only}\n\n"
        f"📊 **Трафик:** ⬆️ {up} | ⬇️ {down} | 📈 Всего: `{total}`\n"
        f"👥 **Клиенты:** Всего: **{len(clients)}** (Активных: **{active_clients}**)\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.inbound_detail_kb(inbound_id),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("clients_list_"))
async def cb_clients_list(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[2])
    page = int(parts[3])

    client = ThreeXUIClient.from_storage()
    if not client:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    await callback.answer()
    inbound = await client.get_inbound(inbound_id)
    await client.close()

    if not inbound:
        await callback.message.edit_text("❌ Инбаунд не найден.", reply_markup=keyboards.main_menu_kb())
        return

    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    remark = inbound.get("remark", f"#{inbound_id}")

    if not clients:
        await callback.message.edit_text(
            f"👥 **Инбаунд {remark} — Список клиентов**\n\nКлиентов пока нет.",
            reply_markup=keyboards.inbound_detail_kb(inbound_id),
            parse_mode="Markdown"
        )
        return

    text = (
        f"👥 **Инбаунд {remark} — Список клиентов**\n\n"
        f"Всего пользователей: **{len(clients)}**\n"
        "Выберите клиента из списка ниже для просмотра и управления:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.clients_list_kb(inbound_id, clients, page),
        parse_mode="Markdown"
    )
