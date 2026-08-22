from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from x_ui.core import crypto_storage, bot_settings
from remnawave.core.api_client import RemnawaveClient
from remnawave.keyboards import inline as keyboards
from remnawave.states.states import RemnaProfileStates

router = Router()

@router.callback_query(F.data == "remna_menu_profiles")
async def cb_profiles_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = bot_settings.get_language()
    
    client = RemnawaveClient.from_storage()
    if not client:
        await callback.answer("Error" if lang == "en" else "Ошибка", show_alert=True)
        return
        
    res = await client.get_profiles()
    await client.close()
    
    if not res.get("success"):
        await callback.message.edit_text(
            f"❌ Error: {res.get('msg')}",
            reply_markup=keyboards.cancel_kb(lang=lang)
        )
        await callback.answer()
        return
        
    response_data = res.get("response", {})
    profiles = response_data.get("configProfiles", []) if isinstance(response_data, dict) else []
    text = (
        "📁 **Remnawave Config Profiles**\nSelect a profile to view details:"
        if lang == "en" else
        "📁 **Профили конфигурации Remnawave**\nВыберите профиль для просмотра деталей:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.profiles_list_kb(profiles, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remna_profile_view_"))
async def cb_profile_view(callback: CallbackQuery):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_profile_view_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client._request("GET", f"/api/config-profiles/{uuid}")
    
    # Also fetch inbounds count
    inbound_res = await client.get_profile_inbounds(uuid)
    await client.close()
    
    if not res.get("success"):
        await callback.answer(f"Error: {res.get('msg')}", show_alert=True)
        return
        
    profile = res.get("response", {})
    name = profile.get("name", "Profile")
    
    response_data = inbound_res.get("response", {}) if inbound_res.get("success") else {}
    inbounds = response_data.get("inbounds", []) if isinstance(response_data, dict) else []
    inbounds_count = len(inbounds)
    
    # Format list of inbounds
    inbounds_list_str = ""
    if inbounds:
        inbounds_list_str = "\n".join([f"- `{ib.get('tag', 'unknown')}` ({ib.get('protocol', 'unknown')})" for ib in inbounds])
    else:
        inbounds_list_str = "—"
        
    text = (
        f"📁 **Config Profile: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **UUID**: `{uuid}`\n"
        f"📡 **Total Inbounds**: `{inbounds_count}`\n\n"
        f"📋 **Inbounds list**:\n{inbounds_list_str}"
        if lang == "en" else
        f"📁 **Профиль конфигурации: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **UUID**: `{uuid}`\n"
        f"📡 **Всего инбаундов**: `{inbounds_count}`\n\n"
        f"📋 **Список инбаундов**:\n{inbounds_list_str}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.profile_detail_kb(uuid, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remna_profile_rename_"))
async def cb_profile_rename_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_profile_rename_", "")
    await state.update_data(profile_uuid=uuid)
    await state.set_state(RemnaProfileStates.waiting_for_edit_name)
    
    text = (
        "✏️ **Rename Profile**\n\nEnter new name for this profile:"
        if lang == "en" else
        "✏️ **Переименование профиля**\n\nВведите новое имя для этого профиля:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaProfileStates.waiting_for_edit_name)
async def process_profile_rename(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    data = await state.get_data()
    uuid = data.get("profile_uuid")
    new_name = message.text.strip()
    
    client = RemnawaveClient.from_storage()
    res = await client.update_profile(uuid, new_name)
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ Profile successfully renamed!" if lang == "en" else "✅ Профиль успешно переименован!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)

@router.callback_query(F.data.startswith("remna_profile_delete_"))
async def cb_profile_delete(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_profile_delete_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client.delete_profile(uuid)
    await client.close()
    
    if res.get("success"):
        await callback.answer("Profile deleted!" if lang == "en" else "Профиль удален!", show_alert=True)
        await cb_profiles_list(callback, state)
    else:
        await callback.answer(f"Failed: {res.get('msg')}", show_alert=True)

# CREATE PROFILE
@router.callback_query(F.data == "remna_profile_create")
async def cb_profile_create_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    await state.set_state(RemnaProfileStates.waiting_for_name)
    text = (
        "📁 **Create Config Profile**\n\nEnter profile name:"
        if lang == "en" else
        "📁 **Создание профиля конфигурации**\n\nВведите имя профиля:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaProfileStates.waiting_for_name)
async def process_profile_create(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    name = message.text.strip()
    
    client = RemnawaveClient.from_storage()
    res = await client.create_profile(name)
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ Profile successfully created!" if lang == "en" else "✅ Профиль успешно создан!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)

@router.callback_query(F.data.startswith("remna_profile_export_"))
async def cb_profile_export(callback: CallbackQuery):
    import json
    from aiogram.types import BufferedInputFile
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_profile_export_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client._request("GET", f"/api/config-profiles/{uuid}")
    await client.close()
    
    if not res.get("success"):
        await callback.answer(f"Error: {res.get('msg')}", show_alert=True)
        return
        
    profile = res.get("response", {})
    name = profile.get("name", "Profile")
    config = profile.get("config", {})
    
    json_str = json.dumps(config, indent=2, ensure_ascii=False)
    
    # Send text block if short enough
    if len(json_str) < 3900:
        await callback.message.answer(
            f"📁 **Profile: {name}**\n\n```json\n{json_str}\n```",
            parse_mode="Markdown"
        )
    else:
        text = (
            f"📁 **Profile `{name}` configuration JSON is too large, sent as file below:**"
            if lang == "en" else
            f"📁 **Конфигурация профиля `{name}` слишком большая, отправлена файлом ниже:**"
        )
        await callback.message.answer(text, parse_mode="Markdown")
        
    # Send document anyway
    file_bytes = json_str.encode("utf-8")
    input_file = BufferedInputFile(file_bytes, filename=f"profile_{name}.json")
    await callback.message.answer_document(input_file)
    await callback.answer()
