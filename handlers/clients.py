import io
import json
import uuid
import datetime
import qrcode
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from core.api_client import ThreeXUIClient, format_bytes, ensure_dict
from keyboards import inline as keyboards
from states.states import AddClientStates, SearchClientStates, EditClientGBStates, EditClientExpiryStates

router = Router()

def format_timestamp(ms: int) -> str:
    if not ms or ms <= 0:
        return "♾ Безлимитно"
    dt = datetime.datetime.fromtimestamp(ms / 1000.0)
    return dt.strftime("%d.%m.%Y %H:%M")

@router.callback_query(F.data.startswith("menu_all_clients_"))
async def cb_all_clients(callback: CallbackQuery):
    page = int(callback.data.split("_")[3])

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    await callback.answer("Загрузка списка всех клиентов...")
    res = await client_api.get_inbounds()
    await client_api.close()

    if not res.get("success"):
        await callback.message.edit_text(
            f"❌ **Ошибка загрузки инбаундов:**\n`{res.get('msg')}`",
            reply_markup=keyboards.main_menu_kb(),
            parse_mode="Markdown"
        )
        return

    inbounds = res.get("obj", [])
    all_clients = []
    for ib in inbounds:
        ib_id = ib.get("id")
        ib_remark = ib.get("remark", f"#{ib_id}")
        settings = ensure_dict(ib.get("settings"))
        clients = settings.get("clients", [])
        for c in clients:
            all_clients.append((ib_id, ib_remark, c))

    if not all_clients:
        await callback.message.edit_text(
            "👥 **Список всех клиентов**\n\nКлиентов пока нет ни в одном инбаунде.",
            reply_markup=keyboards.main_menu_kb(),
            parse_mode="Markdown"
        )
        return

    active_count = sum(1 for _, _, c in all_clients if c.get("enable", True))

    text = (
        f"👥 **Все клиенты панели 3x-ui**\n\n"
        f"Всего пользователей: **{len(all_clients)}** (Активных: **{active_count}**)\n"
        "Выберите клиента для управления:"
    )

    from aiogram.exceptions import TelegramBadRequest
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.all_clients_paginated_kb(all_clients, page),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise e

@router.callback_query(F.data.startswith("client_view_"))
async def cb_view_client(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[2])
    uuid_val = parts[3]

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer(" Ошибка авторизации", show_alert=True)
        return

    await callback.answer()
    inbound = await client_api.get_inbound(inbound_id)
    await client_api.close()

    if not inbound:
        await callback.message.edit_text("❌ Инбаунд не найден.", reply_markup=keyboards.main_menu_kb())
        return

    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    
    target_client = None
    for c in clients:
        if (c.get("id") == uuid_val) or (c.get("password") == uuid_val):
            target_client = c
            break

    if not target_client:
        await callback.message.edit_text("❌ Клиент не найден.", reply_markup=keyboards.inbound_detail_kb(inbound_id))
        return

    email = target_client.get("email", "no-name")
    is_enabled = target_client.get("enable", True)
    status_str = "🟢 Активен" if is_enabled else "🔴 Отключен"

    # Search client traffic in clientStats
    client_stats = inbound.get("clientStats", [])
    used_up = 0
    used_down = 0
    for stat in client_stats:
        if stat.get("email") == email:
            used_up = stat.get("up", 0)
            used_down = stat.get("down", 0)
            break

    used_total = used_up + used_down
    total_gb_limit = target_client.get("totalGB", 0)
    limit_str = format_bytes(total_gb_limit) if total_gb_limit > 0 else "♾ Безлимитно"
    expiry_str = format_timestamp(target_client.get("expiryTime", 0))
    limit_ip = target_client.get("limitIp", 0)
    limit_ip_str = f"{limit_ip} устройства" if limit_ip > 0 else "♾ Без ограничений"

    text = (
        f"👤 **Профиль клиента: {email}**\n\n"
        f"🆔 **UUID / Pass:** `{uuid_val}`\n"
        f"Статус: **{status_str}**\n\n"
        f"📊 **Использовано:** `{format_bytes(used_total)}` (⬆️ {format_bytes(used_up)} | ⬇️ {format_bytes(used_down)})\n"
        f"📈 **Лимит трафика:** `{limit_str}`\n"
        f"📅 **Истекает:** `{expiry_str}`\n"
        f"📱 **Лимит IP:** `{limit_ip_str}`\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.client_detail_kb(inbound_id, uuid_val, email, is_enabled),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("client_key_"))
async def cb_client_key(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[2])
    uuid_val = parts[3]

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

    # Extract host or IP from panel host
    import urllib.parse
    parsed_host = urllib.parse.urlparse(client_api.host).hostname

    link = client_api.generate_client_link(inbound, target_client, parsed_host)
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
        f"🔑 **Ссылка подключения для `{target_client.get('email')}`**\n\n"
        f"```\n{link}\n```\n"
        "Отсканируйте QR-код приложением (v2rayNG, Happ, Streisand, NekoBox, FoXray)."
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
        # Refresh screen
        await cb_view_client(callback)
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
    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await callback.answer("Ошибка авторизации", show_alert=True)
        return

    res = await client_api.get_inbounds()
    await client_api.close()

    inbounds = res.get("obj", []) if res.get("success") else []
    if not inbounds:
        await callback.message.edit_text("❌ Нет доступных инбаундов для добавления клиента.", reply_markup=keyboards.main_menu_kb())
        await callback.answer()
        return

    if len(inbounds) == 1:
        # Auto select single inbound
        await state.update_data(inbound_id=inbounds[0].get("id"))
        await state.set_state(AddClientStates.waiting_for_email)
        await callback.message.edit_text(
            "➕ **Добавление нового клиента** (Шаг 1 из 4)\n\nВведите **Email / Имя клиента** (например: `alex_vpn`):",
            reply_markup=keyboards.cancel_kb(),
            parse_mode="Markdown"
        )
    else:
        buttons = []
        for ib in inbounds:
            btn_text = f"{ib.get('remark')} ({ib.get('protocol').upper()}:{ib.get('port')})"
            buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"add_client_to_{ib.get('id')}")])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")])

        await callback.message.edit_text(
            "➕ **Выберите инбаунд для добавления клиента:**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="Markdown"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("add_client_to_"))
async def cb_add_client_select_inbound(callback: CallbackQuery, state: FSMContext):
    inbound_id = int(callback.data.split("_")[3])
    await state.update_data(inbound_id=inbound_id)
    await state.set_state(AddClientStates.waiting_for_email)

    await callback.message.edit_text(
        "➕ **Добавление нового клиента** (Шаг 1 из 4)\n\nВведите **Email / Имя клиента** (например: `alex_vpn`):",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AddClientStates.waiting_for_email)
async def process_add_email(message: Message, state: FSMContext):
    email = message.text.strip()
    if not email:
        await message.answer("❌ Имя клиента не может быть пустым. Введите новое имя:", reply_markup=keyboards.cancel_kb())
        return

    await state.update_data(email=email)
    await state.set_state(AddClientStates.waiting_for_limit_gb)

    await message.answer(
        "➕ **Добавление нового клиента** (Шаг 2 из 4)\n\n"
        "Укажите **Лимит трафика в ГБ** (например: `50` или `0` для безлимита):",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )

@router.message(AddClientStates.waiting_for_limit_gb)
async def process_add_gb(message: Message, state: FSMContext):
    try:
        limit_gb = float(message.text.strip().replace(',', '.'))
        if limit_gb < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Укажите число ГБ (например `100` или `0`):", reply_markup=keyboards.cancel_kb())
        return

    await state.update_data(limit_gb=limit_gb)
    await state.set_state(AddClientStates.waiting_for_expiry_days)

    await message.answer(
        "➕ **Добавление нового клиента** (Шаг 3 из 4)\n\n"
        "Укажите **Срок действия в днях** (например: `30` или `0` для бессрочного):",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )

@router.message(AddClientStates.waiting_for_expiry_days)
async def process_add_expiry(message: Message, state: FSMContext):
    try:
        expiry_days = int(message.text.strip())
        if expiry_days < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Укажите количество дней числом (например `30` или `0`):", reply_markup=keyboards.cancel_kb())
        return

    await state.update_data(expiry_days=expiry_days)
    await state.set_state(AddClientStates.waiting_for_limit_ip)

    await message.answer(
        "➕ **Добавление нового клиента** (Шаг 4 из 4)\n\n"
        "Укажите **Лимит IP / Устройств** (например: `2` или `0` для безлимита):",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )

@router.message(AddClientStates.waiting_for_limit_ip)
async def process_add_limit_ip(message: Message, state: FSMContext):
    try:
        limit_ip = int(message.text.strip())
        if limit_ip < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Укажите лимит устройств числом (например `2` или `0`):", reply_markup=keyboards.cancel_kb())
        return

    await state.update_data(limit_ip=limit_ip)
    await state.set_state(AddClientStates.waiting_for_initial_status)

    await message.answer(
        "➕ **Добавление нового клиента** (Шаг 5 из 5)\n\n"
        "Выберите **Начальный статус соединения**:\n\n"
        "• 🟢 **Включен** (Сразу активен)\n"
        "• 🔴 **Отключен** (Изначально не подключен ни к какому коннекту)",
        reply_markup=keyboards.initial_status_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(AddClientStates.waiting_for_initial_status, F.data.startswith("client_init_enable_"))
async def cb_process_add_status(callback: CallbackQuery, state: FSMContext):
    enable_val = (callback.data.split("_")[3] == "1")

    data = await state.get_data()
    await state.clear()

    inbound_id = data.get("inbound_id")
    email = data.get("email")
    limit_gb = data.get("limit_gb")
    expiry_days = data.get("expiry_days")
    limit_ip = data.get("limit_ip")
    client_uuid = str(uuid.uuid4())

    status_msg = await callback.message.edit_text("🔄 **Создание нового клиента...**", parse_mode="Markdown")

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await status_msg.edit_text("❌ Ошибка авторизации. Панель не настроена.")
        await callback.answer()
        return

    res = await client_api.add_client(
        inbound_id=inbound_id,
        email=email,
        uuid_str=client_uuid,
        total_gb=limit_gb,
        expiry_days=expiry_days,
        limit_ip=limit_ip,
        enable=enable_val
    )

    if res.get("success"):
        st_text = "🟢 Включен (Активен)" if enable_val else "🔴 Отключен (Не подключен)"
        await status_msg.edit_text(
            f"✅ **Клиент `{email}` успешно создан!**\n\n"
            f"🆔 UUID: `{client_uuid}`\n"
            f"Статус соединения: **{st_text}**\n"
            f"📊 Лимит ГБ: `{limit_gb if limit_gb > 0 else 'Безлимит'}`\n"
            f"📅 Срок: `{expiry_days if expiry_days > 0 else 'Бессрочно'} дн.`",
            reply_markup=keyboards.client_detail_kb(inbound_id, client_uuid, email, enable_val),
            parse_mode="Markdown"
        )
    else:
        await status_msg.edit_text(
            f"❌ **Ошибка при создании клиента:**\n`{res.get('msg')}`",
            reply_markup=keyboards.inbound_detail_kb(inbound_id),
            parse_mode="Markdown"
        )
    await client_api.close()
    await callback.answer()

# SEARCH CLIENT
@router.callback_query(F.data == "menu_search_client")
async def cb_search_client_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchClientStates.waiting_for_query)
    await callback.message.edit_text(
        "🔍 **Поиск клиента**\n\nВведите Имя (Email) или UUID клиента для поиска:",
        reply_markup=keyboards.cancel_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(SearchClientStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip().lower()
    await state.clear()

    status_msg = await message.answer("🔄 **Поиск клиента по всем инбаундам...**", parse_mode="Markdown")

    client_api = ThreeXUIClient.from_storage()
    if not client_api:
        await status_msg.edit_text("❌ Ошибка авторизации. Настройки не найдены.")
        return

    res = await client_api.get_inbounds()
    await client_api.close()

    if not res.get("success"):
        await status_msg.edit_text(f"❌ Ошибка поиска: {res.get('msg')}")
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
        await status_msg.edit_text(
            f"🔍 **Результаты поиска по запросу `{query}`:**\n\nНичего не найдено.",
            reply_markup=keyboards.main_menu_kb(),
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

    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu_main")])

    await status_msg.edit_text(
        f"🔍 **Результаты поиска по запросу `{query}`:**\nНайдено совпадений: **{len(found_items)}**",
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
