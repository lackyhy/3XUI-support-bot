from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from x_ui.core import crypto_storage, bot_settings
from remnawave.core.api_client import RemnawaveClient
from remnawave.keyboards import inline as keyboards
from remnawave.states.states import RemnaHostStates

router = Router()

async def get_inbound_lookup(client: RemnawaveClient) -> dict:
    lookup = {}
    try:
        profiles_res = await client.get_profiles()
        if profiles_res.get("success"):
            response_data = profiles_res.get("response", {})
            profiles = response_data.get("configProfiles", []) if isinstance(response_data, dict) else []
            for p in profiles:
                p_uuid = p.get("uuid")
                p_name = p.get("name", "Profile")
                inbounds_res = await client.get_profile_inbounds(p_uuid)
                if inbounds_res.get("success"):
                    inb_data = inbounds_res.get("response", {})
                    inbounds = inb_data.get("inbounds", []) if isinstance(inb_data, dict) else []
                    for ib in inbounds:
                        ib_uuid = ib.get("uuid")
                        ib_tag = ib.get("tag", "Inbound")
                        lookup[(p_uuid, ib_uuid)] = f"{p_name} › {ib_tag}"
    except Exception:
        pass
    return lookup

@router.callback_query(F.data == "remna_menu_hosts")
async def cb_hosts_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = bot_settings.get_language()
    
    client = RemnawaveClient.from_storage()
    if not client:
        await callback.answer("Error" if lang == "en" else "Ошибка", show_alert=True)
        return
        
    hosts_res = await client.get_hosts()
    await client.close()
    
    if not hosts_res.get("success"):
        await callback.message.edit_text(
            f"❌ Error: {hosts_res.get('msg')}",
            reply_markup=keyboards.cancel_kb(lang=lang)
        )
        return
        
    hosts = hosts_res.get("response", [])
    
    text = (
        "🖥 **Remnawave Hosts**\n\nSelect a host below to view settings:"
        if lang == "en" else
        "🖥 **Хосты Remnawave**\n\nВыберите хост ниже для изменения настроек:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.hosts_list_kb(hosts, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remna_host_view_"))
async def cb_host_view(callback: CallbackQuery):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_host_view_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client._request("GET", f"/api/hosts/{uuid}")
    
    if not res.get("success"):
        await client.close()
        await callback.answer(f"Error: {res.get('msg')}", show_alert=True)
        return
        
    host = res.get("response", {})
    
    # Retrieve linked profile name and inbound tag
    ib = host.get("inbound", {})
    p_uuid = ib.get("configProfileUuid")
    ib_uuid = ib.get("configProfileInboundUuid")
    
    profile_name = "—"
    inbound_tag = "—"
    if p_uuid and ib_uuid:
        prof_res = await client._request("GET", f"/api/config-profiles/{p_uuid}")
        if prof_res.get("success"):
            profile_name = prof_res.get("response", {}).get("name", "Profile")
            
        inb_res = await client.get_profile_inbounds(p_uuid)
        if inb_res.get("success"):
            inb_data = inb_res.get("response", {})
            inbounds = inb_data.get("inbounds", []) if isinstance(inb_data, dict) else []
            for item in inbounds:
                if item.get("uuid") == ib_uuid:
                    inbound_tag = item.get("tag", "Inbound")
                    break
                    
    await client.close()
    
    name = host.get("remark") or host.get("name") or "Host"
    address = host.get("address") or host.get("ipOrDomain") or "—"
    port = host.get("port", "—")
    path = host.get("path") or "—"
    sni = host.get("sni") or "—"
    host_hdr = host.get("host") or "—"
    alpn = host.get("alpn") or "—"
    fingerprint = host.get("fingerprint") or "—"
    
    is_disabled = host.get("isDisabled", False)
    is_hidden = host.get("isHidden", False)
    
    tags = ", ".join(host.get("tags", [])) or "—"
    security_layer = host.get("securityLayer", "DEFAULT")
    vless_id = host.get("vlessRouteId")
    vless_id_str = f"{vless_id}" if vless_id is not None else "—"
    
    status_str = "🔴 Disabled" if is_disabled else "🟢 Enabled"
    hidden_str = "👁 Hidden" if is_hidden else "👁 Visible"
    if lang == "ru":
        status_str = "🔴 Отключен" if is_disabled else "🟢 Включен"
        hidden_str = "👁 Скрыт" if is_hidden else "👁 Виден"

    linked_str = f"{profile_name} › {inbound_tag}" if profile_name != "—" else "—"

    text = (
        f"🖥 **Host: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **UUID**: `{uuid}`\n"
        f"🌐 **Address**: `{address}:{port}`\n"
        f"📁 **Profile**: `{linked_str}`\n"
        f"🏷 **Tags**: `{tags}`\n"
        f"⚡ **Status**: {status_str} | {hidden_str}\n\n"
        f"⚙️ **Advanced Settings**:\n"
        f"• **SNI**: `{sni}`\n"
        f"• **Host Header**: `{host_hdr}`\n"
        f"• **Path**: `{path}`\n"
        f"• **ALPN**: `{alpn}`\n"
        f"• **Fingerprint**: `{fingerprint}`\n"
        f"• **Security Layer**: `{security_layer}`\n"
        f"• **VLESS Route ID**: `{vless_id_str}`"
        if lang == "en" else
        f"🖥 **Хост: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **UUID**: `{uuid}`\n"
        f"🌐 **Адрес**: `{address}:{port}`\n"
        f"📁 **Профиль**: `{linked_str}`\n"
        f"🏷 **Теги**: `{tags}`\n"
        f"⚡ **Статус**: {status_str} | {hidden_str}\n\n"
        f"⚙️ **Дополнительные настройки**:\n"
        f"• **SNI**: `{sni}`\n"
        f"• **Host Header**: `{host_hdr}`\n"
        f"• **Путь (Path)**: `{path}`\n"
        f"• **ALPN**: `{alpn}`\n"
        f"• **Fingerprint**: `{fingerprint}`\n"
        f"• **Шифрование (Security)**: `{security_layer}`\n"
        f"• **VLESS Route ID**: `{vless_id_str}`"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.host_detail_kb(uuid, is_disabled, is_hidden, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

# TOGGLE AND HIDE ACTIONS
@router.callback_query(F.data.startswith("remna_host_toggle_"))
async def cb_host_toggle(callback: CallbackQuery):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_host_toggle_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client._request("GET", f"/api/hosts/{uuid}")
    if not res.get("success"):
        await client.close()
        await callback.answer(f"Error: {res.get('msg')}", show_alert=True)
        return
        
    host = res.get("response", {})
    is_disabled = host.get("isDisabled", False)
    inbound = host.get("inbound", {})
    
    payload = {
        "inbound": {
            "configProfileUuid": inbound.get("configProfileUuid"),
            "configProfileInboundUuid": inbound.get("configProfileInboundUuid")
        },
        "isDisabled": not is_disabled
    }
    
    res_action = await client.update_host(uuid, payload)
    await client.close()
    
    if res_action.get("success"):
        await callback.answer("Status updated!" if lang == "en" else "Статус хоста обновлен!", show_alert=True)
        await cb_host_view(callback)
    else:
        await callback.answer(f"Failed: {res_action.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("remna_host_hide_"))
async def cb_host_hide(callback: CallbackQuery):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_host_hide_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client._request("GET", f"/api/hosts/{uuid}")
    if not res.get("success"):
        await client.close()
        await callback.answer(f"Error: {res.get('msg')}", show_alert=True)
        return
        
    host = res.get("response", {})
    is_hidden = host.get("isHidden", False)
    inbound = host.get("inbound", {})
    
    payload = {
        "inbound": {
            "configProfileUuid": inbound.get("configProfileUuid"),
            "configProfileInboundUuid": inbound.get("configProfileInboundUuid")
        },
        "isHidden": not is_hidden
    }
    
    res_action = await client.update_host(uuid, payload)
    await client.close()
    
    if res_action.get("success"):
        await callback.answer("Visibility updated!" if lang == "en" else "Видимость хоста обновлена!", show_alert=True)
        await cb_host_view(callback)
    else:
        await callback.answer(f"Failed: {res_action.get('msg')}", show_alert=True)

# EDIT HOST SETTINGS WIZARDS
async def start_host_edit(callback: CallbackQuery, state: FSMContext, next_state, prompt_en: str, prompt_ru: str):
    lang = bot_settings.get_language()
    uuid = callback.data.split("_")[-1]
    await state.update_data(host_uuid=uuid)
    await state.set_state(next_state)
    
    text = (
        f"{prompt_en}\n*(Send `/empty` or `/skip` to clear this field)*"
        if lang == "en" else
        f"{prompt_ru}\n*(Отправьте `/empty` или `/skip` для очистки)*"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("remna_host_edit_remark_"))
async def cb_edit_remark(callback: CallbackQuery, state: FSMContext):
    await start_host_edit(callback, state, RemnaHostStates.waiting_for_edit_remark,
                          "✏️ **Edit Host Remark (Name)**\nEnter new remark:",
                          "✏️ **Изменение имени (заметки) хоста**\nВведите новое имя:")

@router.callback_query(F.data.startswith("remna_host_edit_addr_"))
async def cb_edit_addr(callback: CallbackQuery, state: FSMContext):
    await start_host_edit(callback, state, RemnaHostStates.waiting_for_edit_address,
                          "🌐 **Edit Host Address**\nEnter new IP address or domain:",
                          "🌐 **Изменение адреса хоста**\nВведите новый IP или домен:")

@router.callback_query(F.data.startswith("remna_host_edit_port_"))
async def cb_edit_port(callback: CallbackQuery, state: FSMContext):
    await start_host_edit(callback, state, RemnaHostStates.waiting_for_edit_port,
                          "🔌 **Edit Host Port**\nEnter new port (1-65535):",
                          "🔌 **Изменение порта хоста**\nВведите новый порт (1-65535):")

@router.callback_query(F.data.startswith("remna_host_edit_path_"))
async def cb_edit_path(callback: CallbackQuery, state: FSMContext):
    await start_host_edit(callback, state, RemnaHostStates.waiting_for_edit_path,
                          "🗺 **Edit Host Path**\nEnter HTTP request path:",
                          "🗺 **Изменение пути (Path)**\nВведите HTTP-путь:")

@router.callback_query(F.data.startswith("remna_host_edit_sni_"))
async def cb_edit_sni(callback: CallbackQuery, state: FSMContext):
    await start_host_edit(callback, state, RemnaHostStates.waiting_for_edit_sni,
                          "📡 **Edit Host SNI**\nEnter new SNI domain:",
                          "📡 **Изменение SNI**\nВведите новый домен SNI:")

@router.callback_query(F.data.startswith("remna_host_edit_host_"))
async def cb_edit_host(callback: CallbackQuery, state: FSMContext):
    await start_host_edit(callback, state, RemnaHostStates.waiting_for_edit_host,
                          "🌐 **Edit Host Header**\nEnter new HTTP host header:",
                          "🌐 **Изменение Host заголовка**\nВведите новый заголовок Host:")

@router.callback_query(F.data.startswith("remna_host_edit_alpn_"))
async def cb_edit_alpn(callback: CallbackQuery, state: FSMContext):
    await start_host_edit(callback, state, RemnaHostStates.waiting_for_edit_alpn,
                          "⚡ **Edit Host ALPN**\nEnter new ALPN values (comma-separated, e.g. `h2,http/1.1`):",
                          "⚡ **Изменение ALPN**\nВведите значения ALPN (через запятую, например `h2,http/1.1`):")

@router.callback_query(F.data.startswith("remna_host_edit_fp_"))
async def cb_edit_fp(callback: CallbackQuery, state: FSMContext):
    await start_host_edit(callback, state, RemnaHostStates.waiting_for_edit_fingerprint,
                          "🔑 **Edit TLS Fingerprint**\nEnter TLS client fingerprint (e.g. `chrome`, `firefox`, `safari`):",
                          "🔑 **Изменение TLS Fingerprint**\nВведите TLS-отпечаток (например, `chrome`, `firefox`, `safari`):")

# MESSAGE PROCESSORS FOR EDITS
async def execute_host_update(message: Message, state: FSMContext, update_field: str, validate_func=None):
    lang = bot_settings.get_language()
    data = await state.get_data()
    uuid = data.get("host_uuid")
    text = message.text.strip()
    
    val = text
    if text in ["/empty", "/skip"]:
        val = None
        
    if val is not None and validate_func:
        valid, val = validate_func(val)
        if not valid:
            await message.answer("❌ Invalid input format!" if lang == "en" else "❌ Неверный формат ввода!")
            return

    client = RemnawaveClient.from_storage()
    # Fetch existing host config to get inbound structure
    host_res = await client._request("GET", f"/api/hosts/{uuid}")
    if not host_res.get("success"):
        await client.close()
        await message.answer(f"❌ Failed to fetch current host data: {host_res.get('msg')}")
        await state.clear()
        return
        
    host = host_res.get("response", {})
    inbound = host.get("inbound", {})
    
    # Construct full Dto payload
    payload = {
        "inbound": {
            "configProfileUuid": inbound.get("configProfileUuid"),
            "configProfileInboundUuid": inbound.get("configProfileInboundUuid")
        },
        update_field: val
    }
    
    res = await client.update_host(uuid, payload)
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ Host configuration updated!" if lang == "en" else "✅ Настройки хоста успешно изменены!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)

@router.message(RemnaHostStates.waiting_for_edit_remark)
async def proc_edit_remark(message: Message, state: FSMContext):
    await execute_host_update(message, state, "remark")

@router.message(RemnaHostStates.waiting_for_edit_address)
async def proc_edit_addr(message: Message, state: FSMContext):
    await execute_host_update(message, state, "address")

@router.message(RemnaHostStates.waiting_for_edit_port)
async def proc_edit_port(message: Message, state: FSMContext):
    def validate_port(val):
        try:
            port = int(val)
            if 1 <= port <= 65535:
                return True, port
        except ValueError:
            pass
        return False, val
    await execute_host_update(message, state, "port", validate_port)

@router.message(RemnaHostStates.waiting_for_edit_path)
async def proc_edit_path(message: Message, state: FSMContext):
    await execute_host_update(message, state, "path")

@router.message(RemnaHostStates.waiting_for_edit_sni)
async def proc_edit_sni(message: Message, state: FSMContext):
    await execute_host_update(message, state, "sni")

@router.message(RemnaHostStates.waiting_for_edit_host)
async def proc_edit_host(message: Message, state: FSMContext):
    await execute_host_update(message, state, "host")

@router.message(RemnaHostStates.waiting_for_edit_alpn)
async def proc_edit_alpn(message: Message, state: FSMContext):
    await execute_host_update(message, state, "alpn")

@router.message(RemnaHostStates.waiting_for_edit_fingerprint)
async def proc_edit_fp(message: Message, state: FSMContext):
    await execute_host_update(message, state, "fingerprint")

@router.callback_query(F.data.startswith("remna_host_delete_"))
async def cb_host_delete(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_host_delete_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client.delete_host(uuid)
    await client.close()
    
    if res.get("success"):
        await callback.answer("Host deleted!" if lang == "en" else "Хост удален!", show_alert=True)
        await cb_hosts_list(callback, state)
    else:
        await callback.answer(f"Failed: {res.get('msg')}", show_alert=True)

# WIZARD: CREATE HOST FLOW WITH INBOUND LINKAGE
@router.callback_query(F.data == "remna_host_create")
async def cb_host_create_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    await state.set_state(RemnaHostStates.waiting_for_name)
    text = (
        "🖥 **Create Host** (Step 1 of 5)\n\nEnter host remark / name:"
        if lang == "en" else
        "🖥 **Создание хоста** (Шаг 1 из 5)\n\nВведите имя (remark) хоста:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaHostStates.waiting_for_name)
async def process_create_host_name(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    name = message.text.strip()
    await state.update_data(host_name=name)
    await state.set_state(RemnaHostStates.waiting_for_address)
    
    text = (
        f"🖥 **Creating Host `{name}`** (Step 2 of 5)\n\nEnter IP address or domain name:"
        if lang == "en" else
        f"🖥 **Создание хоста `{name}`** (Шаг 2 из 5)\n\nВведите IP-адрес или домен хоста:"
    )
    await message.answer(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")

@router.message(RemnaHostStates.waiting_for_address)
async def process_create_host_address(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    addr = message.text.strip()
    await state.update_data(host_address=addr)
    await state.set_state(RemnaHostStates.waiting_for_port)
    
    text = (
        f"🖥 **Creating Host** (Step 3 of 5)\n\nEnter port number (default is 443):"
        if lang == "en" else
        f"🖥 **Создание хоста** (Шаг 3 из 5)\n\nВведите номер порта (по умолчанию 443):"
    )
    await message.answer(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")

@router.message(RemnaHostStates.waiting_for_port)
async def process_create_host_port(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    try:
        port = int(message.text.strip())
        if port < 1 or port > 65535:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Invalid port! Enter number 1-65535:" if lang == "en" else "❌ Некорректный порт! Введите число от 1 до 65535:")
        return
        
    await state.update_data(host_port=port)
    await state.set_state(RemnaHostStates.selecting_profile)
    
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
            "❌ No config profiles found! Please create a profile first before adding a host."
            if lang == "en" else
            "❌ Профили конфигурации не найдены! Создайте сначала профиль."
        )
        await state.clear()
        return
        
    await status_msg.delete()
    
    text = (
        "🖥 **Creating Host** (Step 4 of 5)\n\nSelect a config profile to link to this host:"
        if lang == "en" else
        "🖥 **Создание хоста** (Шаг 4 из 5)\n\nВыберите профиль конфигурации для привязки к этому хосту:"
    )
    await message.answer(text, reply_markup=keyboards.select_host_profile_kb(profiles, lang=lang), parse_mode="Markdown")

@router.callback_query(RemnaHostStates.selecting_profile, F.data.startswith("remna_host_select_prof_"))
async def cb_create_host_profile(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    profile_uuid = callback.data.replace("remna_host_select_prof_", "")
    await state.update_data(profile_uuid=profile_uuid)
    await state.set_state(RemnaHostStates.selecting_inbound)
    
    status_msg = await callback.message.edit_text(
        "🔄 **Fetching profile inbounds...**" if lang == "en" else "🔄 **Загрузка инбаундов профиля...**",
        parse_mode="Markdown"
    )
    
    client = RemnawaveClient.from_storage()
    inbounds_res = await client.get_profile_inbounds(profile_uuid)
    await client.close()
    
    if not inbounds_res.get("success"):
        await status_msg.edit_text(f"❌ Failed to fetch profile inbounds: {inbounds_res.get('msg')}")
        await state.clear()
        return
        
    inb_data = inbounds_res.get("response", {})
    inbounds = inb_data.get("inbounds", []) if isinstance(inb_data, dict) else []
    if not inbounds:
        await status_msg.edit_text(
            "❌ No inbounds found in this profile! Please create an inbound in this profile first."
            if lang == "en" else
            "❌ В выбранном профиле нет входящих подключений! Пожалуйста, сначала добавьте инбаунд."
        )
        await state.clear()
        return
        
    await status_msg.delete()
    
    text = (
        "🖥 **Creating Host** (Step 5 of 5)\n\nSelect an inbound mapping to link to this host:"
        if lang == "en" else
        "🖥 **Создание хоста** (Шаг 5 из 5)\n\nВыберите входящее подключение (Inbound) для привязки к хосту:"
    )
    await callback.message.answer(text, reply_markup=keyboards.select_inbound_kb(inbounds, lang=lang), parse_mode="Markdown")

@router.callback_query(RemnaHostStates.selecting_inbound, F.data.startswith("remna_host_select_inb_"))
async def cb_create_host_inbound(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    inbound_uuid = callback.data.replace("remna_host_select_inb_", "")
    
    data = await state.get_data()
    name = data.get("host_name")
    ip_or_domain = data.get("host_address")
    port = data.get("host_port")
    profile_uuid = data.get("profile_uuid")
    
    status_msg = await callback.message.edit_text(
        "🔄 **Registering host in Remnawave...**" if lang == "en" else "🔄 **Регистрация хоста в Remnawave...**",
        parse_mode="Markdown"
    )
    
    client = RemnawaveClient.from_storage()
    res = await client.create_host(name, ip_or_domain, port, profile_uuid, inbound_uuid)
    await client.close()
    
    if res.get("success"):
        await status_msg.edit_text(
            f"✅ **Host `{name}` successfully registered and linked!**"
            if lang == "en" else
            f"✅ **Хост `{name}` успешно создан и привязан!**"
        )
    else:
        await status_msg.edit_text(f"❌ **Failed to create host!**\n\nReason: `{res.get('msg')}`")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(callback, state)
