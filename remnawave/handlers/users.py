import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from x_ui.core import crypto_storage, bot_settings
from x_ui.core.api_client import format_bytes
from remnawave.core.api_client import RemnawaveClient
from remnawave.keyboards import inline as keyboards
from remnawave.states.states import RemnaUserStates

router = Router()

def format_iso_date(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        # standard ISO format: 2025-01-17T15:38:45.065Z
        cleaned = iso_str.split(".")[0].replace("Z", "")
        dt = datetime.datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso_str

@router.callback_query(F.data == "remna_menu_users")
async def cb_users_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_users_page(callback, 0)

@router.callback_query(F.data.startswith("remna_users_page_"))
async def cb_users_page(callback: CallbackQuery):
    page = int(callback.data.replace("remna_users_page_", ""))
    await show_users_page(callback, page)

async def show_users_page(callback: CallbackQuery, page: int, query: str = None):
    lang = bot_settings.get_language()
    client = RemnawaveClient.from_storage()
    if not client:
        await callback.answer("Error initializing client" if lang == "en" else "Ошибка инициализации клиента", show_alert=True)
        return
        
    res = await client.get_users()
    await client.close()
    
    if not res.get("success", False):
        await callback.message.edit_text(
            f"❌ Error fetching users: {res.get('msg')}" if lang == "en" else f"❌ Ошибка получения пользователей: {res.get('msg')}",
            reply_markup=keyboards.cancel_kb(lang=lang)
        )
        await callback.answer()
        return
        
    response_data = res.get("response", {})
    users_list = response_data.get("users", []) if isinstance(response_data, dict) else []
    users = users_list
    if query:
        users = [u for u in users_list if query.lower() in u.get("username", "").lower()]
        
    total_users = len(users)
    limit = 8
    start_idx = page * limit
    end_idx = start_idx + limit
    
    page_users = users[start_idx:end_idx]
    has_prev = page > 0
    has_next = end_idx < total_users
    
    title = (
        f"👥 **Remnawave Users** (Total: {total_users})\nSelect a user to view details:"
        if lang == "en" else
        f"👥 **Пользователи Remnawave** (Всего: {total_users})\nВыберите пользователя для просмотра:"
    )
    if query:
        title = (
            f"🔍 **Search Results for '{query}'** (Found: {total_users}):"
            if lang == "en" else
            f"🔍 **Результаты поиска для '{query}'** (Найдено: {total_users}):"
        )
        
    await callback.message.edit_text(
        title,
        reply_markup=keyboards.users_list_kb(page_users, page, has_prev, has_next, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

def get_flag_emoji(country_code: str) -> str:
    if not country_code or len(country_code) != 2:
        return ""
    code = country_code.upper()
    try:
        return chr(127397 + ord(code[0])) + chr(127397 + ord(code[1]))
    except Exception:
        return ""

@router.callback_query(F.data.startswith("remna_user_view_"))
async def cb_user_view(callback: CallbackQuery):
    lang = bot_settings.get_language()
    user_id = int(callback.data.replace("remna_user_view_", ""))
    
    client = RemnawaveClient.from_storage()
    import asyncio
    results = await asyncio.gather(
        client._request("GET", f"/api/users/{user_id}"),
        client.get_nodes(),
        return_exceptions=True
    )
    await client.close()
    
    user_res = results[0] if not isinstance(results[0], Exception) else {}
    nodes_res = results[1] if not isinstance(results[1], Exception) else {}
    
    if not user_res.get("success", False):
        await callback.answer(f"Error: {user_res.get('msg')}", show_alert=True)
        return
        
    user = user_res.get("response", {})
    username = user.get("username", "Unknown")
    status = user.get("status", "ACTIVE")
    
    status_icon = "🟢 ACTIVE" if status == "ACTIVE" else ("🔴 DISABLED" if status == "DISABLED" else f"⚠️ {status}")
    if lang == "ru":
        status_icon = "🟢 АКТИВЕН" if status == "ACTIVE" else ("🔴 ОТКЛЮЧЕН" if status == "DISABLED" else f"⚠️ {status}")
        
    expire_at = format_iso_date(user.get("expireAt"))
    traffic_limit = user.get("trafficLimitBytes", 0)
    traffic_limit_str = format_bytes(traffic_limit) if traffic_limit > 0 else ("Unlimited" if lang == "en" else "Безлимит")
    
    traffic_info = user.get("userTraffic", {})
    used_traffic = traffic_info.get("usedTrafficBytes", 0)
    used_str = format_bytes(used_traffic)
    lifetime_traffic = traffic_info.get("lifetimeUsedTrafficBytes", 0)
    lifetime_str = format_bytes(lifetime_traffic)
    
    online_at = format_iso_date(traffic_info.get("onlineAt"))
    hwid_limit = user.get("hwidDeviceLimit", 0)
    hwid_limit_str = f"{hwid_limit}" if hwid_limit and hwid_limit > 0 else ("Unlimited" if lang == "en" else "Безлимит")
    
    sub_url = user.get("subscriptionUrl", "—")
    
    # Node lookup for last connected node
    node_lookup = {}
    if isinstance(nodes_res, dict) and nodes_res.get("success"):
        for n in nodes_res.get("response", []):
            uuid = n.get("uuid")
            name = n.get("name", "Node")
            cc = n.get("countryCode")
            flag = get_flag_emoji(cc) if cc else ""
            node_lookup[uuid] = f"{flag} {name}".strip()
            
    last_node_uuid = traffic_info.get("lastConnectedNodeUuid")
    last_node_name = node_lookup.get(last_node_uuid) if last_node_uuid else None
    
    if last_node_name and traffic_info.get("onlineAt"):
        online_at_val = f"{online_at} ({last_node_name})"
    else:
        online_at_val = online_at
        
    text = (
        f"👤 **User Detail: {username}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ID**: `{user_id}`\n"
        f"⚡ **Status**: {status_icon}\n"
        f"⏳ **Expires**: {expire_at}\n"
        f"🚦 **Traffic used**: {used_str} / {traffic_limit_str}\n"
        f"📈 **Lifetime Traffic**: {lifetime_str}\n"
        f"📱 **HWID Limit**: {hwid_limit_str}\n"
        f"🌐 **Last Online**: {online_at_val}\n\n"
        f"🔑 **Subscription Link**:\n`{sub_url}`"
        if lang == "en" else
        f"👤 **Детали пользователя: {username}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ID**: `{user_id}`\n"
        f"⚡ **Статус**: {status_icon}\n"
        f"⏳ **Истекает**: {expire_at}\n"
        f"🚦 **Использовано**: {used_str} / {traffic_limit_str}\n"
        f"📈 **Трафик за всё время**: {lifetime_str}\n"
        f"📱 **Лимит устройств (HWID)**: {hwid_limit_str}\n"
        f"🌐 **Последняя активность**: {online_at_val}\n\n"
        f"🔑 **Ссылка подписки**:\n`{sub_url}`"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.user_detail_kb(user_id, status, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remna_user_toggle_"))
async def cb_user_toggle(callback: CallbackQuery):
    lang = bot_settings.get_language()
    user_id = int(callback.data.replace("remna_user_toggle_", ""))
    
    client = RemnawaveClient.from_storage()
    res = await client._request("GET", f"/api/users/{user_id}")
    if not res.get("success"):
        await client.close()
        await callback.answer(f"Error: {res.get('msg')}", show_alert=True)
        return
        
    user = res.get("response", {})
    status = user.get("status", "ACTIVE")
    
    if status == "ACTIVE":
        res_action = await client.disable_user(user_id)
    else:
        res_action = await client.enable_user(user_id)
        
    await client.close()
    
    if res_action.get("success"):
        await callback.answer("Status updated!" if lang == "en" else "Статус обновлен!", show_alert=True)
        # Refresh details
        await cb_user_view(callback)
    else:
        await callback.answer(f"Failed: {res_action.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("remna_user_reset_"))
async def cb_user_reset(callback: CallbackQuery):
    lang = bot_settings.get_language()
    user_id = int(callback.data.replace("remna_user_reset_", ""))
    
    client = RemnawaveClient.from_storage()
    res = await client.reset_user_traffic(user_id)
    await client.close()
    
    if res.get("success"):
        await callback.answer("Traffic limit reset!" if lang == "en" else "Трафик сброшен!", show_alert=True)
        await cb_user_view(callback)
    else:
        await callback.answer(f"Failed: {res.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("remna_user_delete_"))
async def cb_user_delete(callback: CallbackQuery):
    lang = bot_settings.get_language()
    user_id = int(callback.data.replace("remna_user_delete_", ""))
    
    client = RemnawaveClient.from_storage()
    res = await client.delete_user(user_id)
    await client.close()
    
    if res.get("success"):
        await callback.answer("User deleted!" if lang == "en" else "Пользователь удален!", show_alert=True)
        await show_users_page(callback, 0)
    else:
        await callback.answer(f"Failed: {res.get('msg')}", show_alert=True)

# EXTEND USER EXPIRATION
@router.callback_query(F.data.startswith("remna_user_extend_"))
async def cb_user_extend_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    user_id = int(callback.data.replace("remna_user_extend_", ""))
    await state.update_data(user_id=user_id)
    await state.set_state(RemnaUserStates.waiting_for_extend_days)
    
    text = (
        "⏳ **Extend Expiration**\n\nEnter the number of days to extend this user's access:"
        if lang == "en" else
        "⏳ **Продление доступа**\n\nВведите число дней, на которое нужно продлить доступ пользователя:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaUserStates.waiting_for_extend_days)
async def process_user_extend(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    data = await state.get_data()
    user_id = data.get("user_id")
    
    try:
        days = int(message.text.strip())
        if days < 1:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Please enter a positive integer!" if lang == "en" else "❌ Пожалуйста, введите целое положительное число!")
        return

    client = RemnawaveClient.from_storage()
    res = await client.extend_user(user_id, days)
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ Expiration date extended!" if lang == "en" else "✅ Срок действия успешно продлен!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    # Mocking call to refresh detail view
    # We will trigger show_remna_dashboard as fallback or let them open the menu
    # To keep FSM cleanup robust we return to start dashboard
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)

# EDIT TRAFFIC LIMIT
@router.callback_query(F.data.startswith("remna_user_limit_"))
async def cb_user_limit_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    user_id = int(callback.data.replace("remna_user_limit_", ""))
    await state.update_data(user_id=user_id)
    await state.set_state(RemnaUserStates.waiting_for_edit_gb)
    
    text = (
        "✏️ **Edit Traffic Limit**\n\nEnter new traffic limit in **GB** (enter `0` for unlimited):"
        if lang == "en" else
        "✏️ **Изменение лимита трафика**\n\nВведите новый лимит трафика в **ГБ** (введите `0` для безлимита):"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaUserStates.waiting_for_edit_gb)
async def process_user_limit(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    data = await state.get_data()
    user_id = data.get("user_id")
    
    try:
        gb = float(message.text.strip())
        if gb < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid input. Please enter a valid number!" if lang == "en" else "❌ Некорректный ввод. Введите число!")
        return

    bytes_limit = int(gb * 1024 * 1024 * 1024)
    client = RemnawaveClient.from_storage()
    res = await client.update_user(user_id, {"trafficLimitBytes": bytes_limit})
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ Traffic limit updated!" if lang == "en" else "✅ Лимит трафика обновлен!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)

# EDIT HWID LIMIT
@router.callback_query(F.data.startswith("remna_user_hwid_"))
async def cb_user_hwid_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    user_id = int(callback.data.replace("remna_user_hwid_", ""))
    await state.update_data(user_id=user_id)
    await state.set_state(RemnaUserStates.waiting_for_edit_hwid)
    
    text = (
        "📱 **Edit HWID Limit**\n\nEnter maximum number of devices allowed (enter `0` for unlimited):"
        if lang == "en" else
        "📱 **Изменение лимита устройств**\n\nВведите максимальное число устройств (введите `0` для безлимита):"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaUserStates.waiting_for_edit_hwid)
async def process_user_hwid(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    data = await state.get_data()
    user_id = data.get("user_id")
    
    try:
        hwid = int(message.text.strip())
        if hwid < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Please enter a non-negative integer!" if lang == "en" else "❌ Введите целое неотрицательное число!")
        return

    client = RemnawaveClient.from_storage()
    res = await client.update_user(user_id, {"hwidDeviceLimit": hwid})
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ HWID limit updated!" if lang == "en" else "✅ Лимит устройств обновлен!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)

# SEARCH USER
@router.callback_query(F.data == "remna_user_search")
async def cb_user_search_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    await state.set_state(RemnaUserStates.waiting_for_search_query)
    
    text = (
        "🔍 **Search User**\n\nEnter part of the username to search:"
        if lang == "en" else
        "🔍 **Поиск пользователя**\n\nВведите часть имени пользователя для поиска:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaUserStates.waiting_for_search_query)
async def process_user_search(message: Message, state: FSMContext):
    query = message.text.strip()
    # We display search results directly on the users list with pagination
    # To do this, we mock a callback view
    # Custom message helper
    lang = bot_settings.get_language()
    client = RemnawaveClient.from_storage()
    if not client:
        await message.answer("Error" if lang == "en" else "Ошибка")
        return
    res = await client.get_users()
    await client.close()
    
    if not res.get("success"):
        await message.answer(f"Error: {res.get('msg')}")
        await state.clear()
        return
        
    response_data = res.get("response", {})
    users_list = response_data.get("users", []) if isinstance(response_data, dict) else []
    users = [u for u in users_list if query.lower() in u.get("username", "").lower()]
    total_users = len(users)
    page_users = users[:8]
    has_next = total_users > 8
    
    await state.clear()
    
    title = (
        f"🔍 **Search Results for '{query}'** (Found: {total_users}):"
        if lang == "en" else
        f"🔍 **Результаты поиска для '{query}'** (Найдено: {total_users}):"
    )
    await message.answer(
        title,
        reply_markup=keyboards.users_list_kb(page_users, 0, False, has_next, lang=lang),
        parse_mode="Markdown"
    )

# CREATE USER FLOW
@router.callback_query(F.data == "remna_user_create")
async def cb_user_create_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    await state.set_state(RemnaUserStates.waiting_for_username)
    text = (
        "👥 **Create Remnawave User** (Step 1 of 4)\n\nEnter username:"
        if lang == "en" else
        "👥 **Создание пользователя Remnawave** (Шаг 1 из 4)\n\nВведите имя пользователя (username):"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaUserStates.waiting_for_username)
async def process_create_username(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    username = message.text.strip()
    if len(username) < 3 or len(username) > 36:
        await message.answer("❌ Username must be 3-36 characters!" if lang == "en" else "❌ Имя пользователя должно быть от 3 до 36 символов!")
        return
        
    await state.update_data(username=username)
    await state.set_state(RemnaUserStates.waiting_for_expiry)
    
    text = (
        f"👤 **Creating User `{username}`** (Step 2 of 4)\n\nEnter duration in **days**:"
        if lang == "en" else
        f"👤 **Создание пользователя `{username}`** (Шаг 2 из 4)\n\nВведите срок действия в **днях**:"
    )
    await message.answer(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")

@router.message(RemnaUserStates.waiting_for_expiry)
async def process_create_expiry(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    try:
        days = int(message.text.strip())
        if days < 1:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Please enter a positive integer!" if lang == "en" else "❌ Пожалуйста, введите целое положительное число!")
        return
        
    await state.update_data(expiry_days=days)
    await state.set_state(RemnaUserStates.waiting_for_limit_gb)
    
    text = (
        f"👤 **Creating User** (Step 3 of 4)\n\nEnter traffic limit in **GB** (enter `0` for unlimited):"
        if lang == "en" else
        f"👤 **Создание пользователя** (Шаг 3 из 4)\n\nВведите лимит трафика в **ГБ** (введите `0` для безлимита):"
    )
    await message.answer(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")

@router.message(RemnaUserStates.waiting_for_limit_gb)
async def process_create_limit(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    try:
        gb = float(message.text.strip())
        if gb < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Please enter a valid number!" if lang == "en" else "❌ Пожалуйста, введите число!")
        return
        
    await state.update_data(limit_gb=gb)
    await state.set_state(RemnaUserStates.waiting_for_hwid)
    
    text = (
        f"👤 **Creating User** (Step 4 of 4)\n\nEnter HWID limit / device limit (enter `0` for unlimited):"
        if lang == "en" else
        f"👤 **Создание пользователя** (Шаг 4 из 4)\n\nВведите лимит устройств (введите `0` для безлимита):"
    )
    await message.answer(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")

@router.message(RemnaUserStates.waiting_for_hwid)
async def process_create_hwid(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    try:
        hwid = int(message.text.strip())
        if hwid < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Please enter a non-negative integer!" if lang == "en" else "❌ Введите целое неотрицательное число!")
        return
        
    data = await state.get_data()
    username = data.get("username")
    expiry_days = data.get("expiry_days")
    limit_gb = data.get("limit_gb")
    
    bytes_limit = int(limit_gb * 1024 * 1024 * 1024)
    
    # Calculate ISO expiration string
    exp_date = datetime.datetime.utcnow() + datetime.timedelta(days=expiry_days)
    expire_str = exp_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    status_msg = await message.answer("🔄 **Creating user in Remnawave...**" if lang == "en" else "🔄 **Создание пользователя в Remnawave...**")
    
    client = RemnawaveClient.from_storage()
    res = await client.create_user(username, expire_str, bytes_limit, hwid)
    await client.close()
    
    if res.get("success"):
        user_info = res.get("response", {})
        sub_url = user_info.get("subscriptionUrl", "")
        
        success_text = (
            f"✅ **User `{username}` successfully created!**\n\n"
            f"⏳ **Expires**: {expiry_days} days\n"
            f"🚦 **Traffic limit**: {limit_gb} GB\n"
            f"📱 **Device limit**: {hwid if hwid > 0 else 'Unlimited'}\n\n"
            f"🔑 **Subscription Link**:\n`{sub_url}`"
            if lang == "en" else
            f"✅ **Пользователь `{username}` успешно создан!**\n\n"
            f"⏳ **Срок действия**: {expiry_days} дней\n"
            f"🚦 **Лимит трафика**: {limit_gb} ГБ\n"
            f"📱 **Лимит устройств**: {hwid if hwid > 0 else 'Безлимит'}\n\n"
            f"🔑 **Ссылка подписки**:\n`{sub_url}`"
        )
        await status_msg.edit_text(success_text, parse_mode="Markdown")
    else:
        await status_msg.edit_text(f"❌ **Failed to create user!**\n\nReason: `{res.get('msg')}`")
        
    await state.clear()
    
    from remnawave.handlers.start import show_remna_dashboard
    # Trigger menu return
    await show_remna_dashboard(message, state)
