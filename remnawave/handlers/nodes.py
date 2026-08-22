from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from x_ui.core import crypto_storage, bot_settings
from x_ui.core.api_client import format_bytes
from remnawave.core.api_client import RemnawaveClient
from remnawave.keyboards import inline as keyboards
from remnawave.states.states import RemnaNodeStates

router = Router()

@router.callback_query(F.data == "remna_menu_nodes")
async def cb_nodes_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = bot_settings.get_language()
    
    client = RemnawaveClient.from_storage()
    if not client:
        await callback.answer("Error" if lang == "en" else "Ошибка", show_alert=True)
        return
        
    res = await client.get_nodes()
    await client.close()
    
    if not res.get("success"):
        await callback.message.edit_text(
            f"❌ Error: {res.get('msg')}",
            reply_markup=keyboards.cancel_kb(lang=lang)
        )
        await callback.answer()
        return
        
    nodes = res.get("response", [])
    text = (
        "📡 **Remnawave Nodes**\nSelect a node to inspect and manage:"
        if lang == "en" else
        "📡 **Ноды Remnawave**\nВыберите ноду для управления:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.nodes_list_kb(nodes, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

def format_uptime(seconds: float) -> str:
    s = int(seconds)
    days = s // 86400
    hours = (s % 86400) // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)

@router.callback_query(F.data.startswith("remna_node_view_"))
async def cb_node_view(callback: CallbackQuery):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_node_view_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client._request("GET", f"/api/nodes/{uuid}")
    await client.close()
    
    if not res.get("success"):
        await callback.answer(f"Error: {res.get('msg')}", show_alert=True)
        return
        
    node = res.get("response", {})
    name = node.get("name", "Node")
    address = node.get("address", "—")
    port = node.get("port", "—")
    country = node.get("countryCode", "—")
    
    is_connected = node.get("isConnected", False)
    is_disabled = node.get("isDisabled", False)
    
    status_str = "🟢 Online" if is_connected else "🔴 Offline"
    if is_disabled:
        status_str = "⚪️ Disabled"
        
    if lang == "ru":
        status_str = "🟢 Онлайн" if is_connected else "🔴 Офлайн"
        if is_disabled:
            status_str = "⚪️ Отключена"

    traffic_used = node.get("trafficUsedBytes", 0)
    traffic_limit = node.get("trafficLimitBytes", 0)
    
    traffic_limit_str = format_bytes(traffic_limit) if traffic_limit and traffic_limit > 0 else ("Unlimited" if lang == "en" else "Безлимит")
    traffic_used_str = format_bytes(traffic_used) if traffic_used else "0 B"
    
    status_msg = node.get("lastStatusMessage") or "—"
    
    # Extract System Metrics
    system = node.get("system") or {}
    sys_info = system.get("info") or {}
    sys_stats = system.get("stats") or {}
    
    cpu_model = sys_info.get("cpuModel") or "—"
    cpu_cores = sys_info.get("cpus") or 0
    cpu_str = f"{cpu_cores} x {cpu_model}" if cpu_cores else "—"
    
    mem_total = sys_info.get("memoryTotal") or 0
    mem_used = sys_stats.get("memoryUsed") or 0
    mem_pct = (mem_used / mem_total * 100) if mem_total else 0
    mem_str = f"{format_bytes(mem_used)} / {format_bytes(mem_total)} ({mem_pct:.1f}%)" if mem_total else "—"
    
    uptime = sys_stats.get("uptime") or 0
    uptime_str = format_uptime(uptime) if uptime else "—"
    
    platform = sys_info.get("platform") or "—"
    arch = sys_info.get("arch") or "—"
    kernel = sys_info.get("release") or "—"
    
    # Interface Bandwidth
    iface = sys_stats.get("interface") or {}
    iface_name = iface.get("interface") or "—"
    rx_speed = iface.get("rxBytesPerSec") or 0
    tx_speed = iface.get("txBytesPerSec") or 0
    rx_total = iface.get("rxTotal") or 0
    tx_total = iface.get("txTotal") or 0
    
    if iface_name != "—":
        iface_str = (
            f"  • Interface: `{iface_name}`\n"
            f"  • RX: `{format_bytes(rx_speed)}/s` (Total: `{format_bytes(rx_total)}`)\n"
            f"  • TX: `{format_bytes(tx_speed)}/s` (Total: `{format_bytes(tx_total)}`)"
        )
    else:
        iface_str = "  —"
        
    # Core Configurations / Inbounds
    config_profile = node.get("configProfile") or {}
    active_inbounds = config_profile.get("activeInbounds") or []
    
    inbounds_list = []
    for ib in active_inbounds:
        ib_tag = ib.get("tag", "Inbound")
        ib_port = ib.get("port", "—")
        ib_type = ib.get("type", "—")
        ib_net = ib.get("network") or "—"
        ib_sec = ib.get("security") or "—"
        inbounds_list.append(f"• `{ib_tag}` (Port: `{ib_port}`, `{ib_type}/{ib_net}/{ib_sec}`)")
        
    inbounds_str = "\n".join(inbounds_list) if inbounds_list else "—"
    
    text = (
        f"📡 **Node: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌐 **Address**: `{address}:{port}`\n"
        f"🌍 **Country**: `{country}`\n"
        f"⚡ **Status**: {status_str}\n"
        f"🚦 **Traffic**: {traffic_used_str} / {traffic_limit_str}\n"
        f"ℹ️ **Message**: `{status_msg}`\n\n"
        f"📁 **Core Configuration**:\n"
        f"{inbounds_str}\n\n"
        f"🖥 **System Info**:\n"
        f"• **OS / Arch**: `{platform} / {arch}`\n"
        f"• **Kernel**: `{kernel}`\n"
        f"• **Uptime**: `{uptime_str}`\n"
        f"• **CPU**: `{cpu_str}`\n"
        f"• **Memory**: `{mem_str}`\n"
        f"• **Bandwidth**:\n{iface_str}"
        if lang == "en" else
        f"📡 **Нода: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌐 **Адрес**: `{address}:{port}`\n"
        f"🌍 **Страна**: `{country}`\n"
        f"⚡ **Статус**: {status_str}\n"
        f"🚦 **Трафик**: {traffic_used_str} / {traffic_limit_str}\n"
        f"ℹ️ **Сообщение**: `{status_msg}`\n\n"
        f"📁 **Конфигурация Ядра**:\n"
        f"{inbounds_str}\n\n"
        f"🖥 **Системная Информация**:\n"
        f"• **ОС / Архитектура**: `{platform} / {arch}`\n"
        f"• **Ядро**: `{kernel}`\n"
        f"• **Аптайм**: `{uptime_str}`\n"
        f"• **Процессор**: `{cpu_str}`\n"
        f"• **Память**: `{mem_str}`\n"
        f"• **Сеть**:\n{iface_str}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.node_detail_kb(uuid, not is_disabled, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remna_node_toggle_"))
async def cb_node_toggle(callback: CallbackQuery):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_node_toggle_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client._request("GET", f"/api/nodes/{uuid}")
    if not res.get("success"):
        await client.close()
        await callback.answer(f"Error: {res.get('msg')}", show_alert=True)
        return
        
    node = res.get("response", {})
    is_disabled = node.get("isDisabled", False)
    
    if is_disabled:
        res_action = await client.enable_node(uuid)
    else:
        res_action = await client.disable_node(uuid)
        
    await client.close()
    
    if res_action.get("success"):
        await callback.answer("Status updated!" if lang == "en" else "Статус ноды обновлен!", show_alert=True)
        await cb_node_view(callback)
    else:
        await callback.answer(f"Failed: {res_action.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("remna_node_restart_"))
async def cb_node_restart(callback: CallbackQuery):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_node_restart_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client.restart_node(uuid)
    await client.close()
    
    if res.get("success"):
        await callback.answer("Restart signal sent!" if lang == "en" else "Сигнал перезапуска отправлен!", show_alert=True)
        await cb_node_view(callback)
    else:
        await callback.answer(f"Failed: {res.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("remna_node_reset_"))
async def cb_node_reset(callback: CallbackQuery):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_node_reset_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client.reset_node_traffic(uuid)
    await client.close()
    
    if res.get("success"):
        await callback.answer("Traffic reset!" if lang == "en" else "Трафик сброшен!", show_alert=True)
        await cb_node_view(callback)
    else:
        await callback.answer(f"Failed: {res.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("remna_node_delete_"))
async def cb_node_delete(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_node_delete_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client.delete_node(uuid)
    await client.close()
    
    if res.get("success"):
        await callback.answer("Node deleted!" if lang == "en" else "Нода удалена!", show_alert=True)
        await cb_nodes_list(callback, state)
    else:
        await callback.answer(f"Failed: {res.get('msg')}", show_alert=True)

# EDIT NODE DETAILS
@router.callback_query(F.data.startswith("remna_node_edit_name_"))
async def cb_node_edit_name_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_node_edit_name_", "")
    await state.update_data(node_uuid=uuid)
    await state.set_state(RemnaNodeStates.waiting_for_edit_name)
    
    text = (
        "✏️ **Edit Node Name**\n\nEnter new name for this node:"
        if lang == "en" else
        "✏️ **Изменение имени ноды**\n\nВведите новое имя для этой ноды:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaNodeStates.waiting_for_edit_name)
async def process_node_edit_name(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    data = await state.get_data()
    uuid = data.get("node_uuid")
    new_name = message.text.strip()
    
    client = RemnawaveClient.from_storage()
    res = await client.update_node(uuid, {"name": new_name})
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ Node name updated!" if lang == "en" else "✅ Имя ноды успешно обновлено!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)

@router.callback_query(F.data.startswith("remna_node_edit_addr_"))
async def cb_node_edit_addr_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_node_edit_addr_", "")
    await state.update_data(node_uuid=uuid)
    await state.set_state(RemnaNodeStates.waiting_for_edit_address)
    
    text = (
        "🌐 **Edit Node Address**\n\nEnter new IP address or domain name for this node:"
        if lang == "en" else
        "🌐 **Изменение адреса ноды**\n\nВведите новый IP или домен для этой ноды:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaNodeStates.waiting_for_edit_address)
async def process_node_edit_addr(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    data = await state.get_data()
    uuid = data.get("node_uuid")
    addr = message.text.strip()
    
    client = RemnawaveClient.from_storage()
    res = await client.update_node(uuid, {"address": addr})
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ Node address updated!" if lang == "en" else "✅ Адрес ноды успешно обновлен!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)

@router.callback_query(F.data.startswith("remna_node_edit_port_"))
async def cb_node_edit_port_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_node_edit_port_", "")
    await state.update_data(node_uuid=uuid)
    await state.set_state(RemnaNodeStates.waiting_for_edit_port)
    
    text = (
        "🔌 **Edit Node Port**\n\nEnter new port number (1-65535):"
        if lang == "en" else
        "🔌 **Изменение порта ноды**\n\nВведите новый номер порта (1-65535):"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaNodeStates.waiting_for_edit_port)
async def process_node_edit_port(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    data = await state.get_data()
    uuid = data.get("node_uuid")
    
    try:
        port = int(message.text.strip())
        if port < 1 or port > 65535:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid port! Must be between 1 and 65535:" if lang == "en" else "❌ Некорректный порт! Должен быть от 1 до 65535:")
        return
        
    client = RemnawaveClient.from_storage()
    res = await client.update_node(uuid, {"port": port})
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ Node port updated!" if lang == "en" else "✅ Порт ноды успешно обновлен!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)

# CREATE NODE FLOW
@router.callback_query(F.data == "remna_node_create")
async def cb_node_create_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    await state.set_state(RemnaNodeStates.waiting_for_name)
    text = (
        "📡 **Create Remnawave Node**\n\nEnter node name:"
        if lang == "en" else
        "📡 **Создание ноды Remnawave**\n\nВведите имя ноды:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaNodeStates.waiting_for_name)
async def process_create_node_name(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    name = message.text.strip()
    await state.update_data(node_name=name)
    await state.set_state(RemnaNodeStates.waiting_for_address)
    
    text = (
        f"📡 **Creating Node `{name}`**\n\nEnter IP address or domain name:"
        if lang == "en" else
        f"📡 **Создание ноды `{name}`**\n\nВведите IP-адрес или домен:"
    )
    await message.answer(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")

@router.message(RemnaNodeStates.waiting_for_address)
async def process_create_node_address(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    addr = message.text.strip()
    await state.update_data(node_address=addr)
    await state.set_state(RemnaNodeStates.waiting_for_port)
    
    text = (
        f"📡 **Creating Node**\n\nEnter port number (e.g. 443, 2053, etc.):"
        if lang == "en" else
        f"📡 **Создание ноды**\n\nВведите номер порта (например, 443, 2053):"
    )
    await message.answer(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")

@router.message(RemnaNodeStates.waiting_for_port)
async def process_create_node_port(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    try:
        port = int(message.text.strip())
        if port < 1 or port > 65535:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid port! Enter number 1-65535:" if lang == "en" else "❌ Некорректный порт! Введите число от 1 до 65535:")
        return
        
    await state.update_data(node_port=port)
    await state.set_state(RemnaNodeStates.selecting_profile)
    
    status_msg = await message.answer("🔄 **Fetching config profiles...**" if lang == "en" else "🔄 **Загрузка профилей конфигурации...**")
    
    client = RemnawaveClient.from_storage()
    res = await client.get_profiles()
    await client.close()
    
    if not res.get("success"):
        await status_msg.edit_text(f"❌ Failed to fetch config profiles: {res.get('msg')}")
        await state.clear()
        return
        
    response_data = res.get("response", {})
    profiles = response_data.get("configProfiles", []) if isinstance(response_data, dict) else []
    if not profiles:
        await status_msg.edit_text(
            "❌ No config profiles found! Please create a profile first before adding a node."
            if lang == "en" else
            "❌ Профили конфигурации не найдены! Пожалуйста, создайте сначала профиль."
        )
        await state.clear()
        return
        
    await status_msg.delete()
    
    text = (
        "📡 **Creating Node**\n\nSelect a config profile to link to this node:"
        if lang == "en" else
        "📡 **Создание ноды**\n\nВыберите профиль конфигурации для привязки к этой ноде:"
    )
    await message.answer(text, reply_markup=keyboards.select_profile_kb(profiles, lang=lang), parse_mode="Markdown")

@router.callback_query(RemnaNodeStates.selecting_profile, F.data.startswith("remna_node_select_prof_"))
async def cb_create_node_profile(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    profile_uuid = callback.data.replace("remna_node_select_prof_", "")
    
    data = await state.get_data()
    name = data.get("node_name")
    address = data.get("node_address")
    port = data.get("node_port")
    
    status_msg = await callback.message.edit_text(
        "🔄 **Creating node and linking inbounds...**" if lang == "en" else "🔄 **Создание ноды и привязка инбаундов...**",
        parse_mode="Markdown"
    )
    
    client = RemnawaveClient.from_storage()
    # Fetch inbounds from profile to enable them all by default
    inbound_uuids = []
    res_inbounds = await client.get_profile_inbounds(profile_uuid)
    if res_inbounds.get("success"):
        inbound_uuids = [ib.get("uuid") for ib in res_inbounds.get("response", []) if "uuid" in ib]
        
    res_node = await client.create_node(name, address, port, profile_uuid, inbound_uuids)
    await client.close()
    
    if res_node.get("success"):
        await status_msg.edit_text(
            f"✅ **Node `{name}` successfully created and active!**"
            if lang == "en" else
            f"✅ **Нода `{name}` успешно создана и запущена!**"
        )
    else:
        await status_msg.edit_text(f"❌ **Failed to create node!**\n\nReason: `{res_node.get('msg')}`")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(callback, state)
