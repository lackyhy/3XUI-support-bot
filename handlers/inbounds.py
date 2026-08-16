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

    remark = inbound.get("remark", f"Inbound #{inbound_id}")
    protocol = inbound.get("protocol", "").upper()
    port = inbound.get("port")
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

    text = (
        f"🌐 **Инбаунд: {remark}**\n\n"
        f"🆔 **ID:** `{inbound_id}`\n"
        f"Статус: {enable}\n"
        f"🛠 **Протокол:** `{protocol}`\n"
        f"🔌 **Порт:** `{port}`\n"
        f"🌐 **Сеть / Защита:** `{net}` / `{sec}`\n\n"
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
