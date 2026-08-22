from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from x_ui.core import crypto_storage, bot_settings
from remnawave.core.api_client import RemnawaveClient
from remnawave.keyboards import inline as keyboards
from remnawave.states.states import RemnaPanelStates

router = Router()

@router.callback_query(F.data == "remna_menu_panels")
async def cb_panels_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = bot_settings.get_language()
    
    client = RemnawaveClient.from_storage()
    if not client:
        await callback.answer("Error" if lang == "en" else "Ошибка", show_alert=True)
        return
        
    res = await client.get_subpage_configs()
    await client.close()
    
    if not res.get("success"):
        await callback.message.edit_text(
            f"❌ Error: {res.get('msg')}",
            reply_markup=keyboards.cancel_kb(lang=lang)
        )
        await callback.answer()
        return
        
    response_data = res.get("response", {})
    configs = response_data.get("configs", []) if isinstance(response_data, dict) else []
    text = (
        "🎛 **Remnawave Subscription Panels (Page Configs)**\nSelect a panel to manage:"
        if lang == "en" else
        "🎛 **Панели подписок Remnawave (Конфиги страниц)**\nВыберите панель для управления:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.panels_list_kb(configs, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remna_panel_view_"))
async def cb_panel_view(callback: CallbackQuery):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_panel_view_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client._request("GET", f"/api/subscription-page-configs/{uuid}")
    await client.close()
    
    if not res.get("success"):
        await callback.answer(f"Error: {res.get('msg')}", show_alert=True)
        return
        
    config = res.get("response", {})
    name = config.get("name", "Panel")
    html = config.get("html", "")
    html_preview = html[:100] + "..." if len(html) > 100 else (html or "—")
    
    text = (
        f"🎛 **Subscription Panel: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **UUID**: `{uuid}`\n"
        f"📝 **HTML Preview**:\n`{html_preview}`"
        if lang == "en" else
        f"🎛 **Панель подписки: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **UUID**: `{uuid}`\n"
        f"📝 **Превью HTML**:\n`{html_preview}`"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.panel_detail_kb(uuid, lang=lang),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remna_panel_clone_"))
async def cb_panel_clone(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_panel_clone_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client.clone_subpage_config(uuid)
    await client.close()
    
    if res.get("success"):
        await callback.answer("Panel cloned successfully!" if lang == "en" else "Панель успешно клонирована!", show_alert=True)
        await cb_panels_list(callback, state)
    else:
        await callback.answer(f"Failed: {res.get('msg')}", show_alert=True)

@router.callback_query(F.data.startswith("remna_panel_delete_"))
async def cb_panel_delete(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    uuid = callback.data.replace("remna_panel_delete_", "")
    
    client = RemnawaveClient.from_storage()
    res = await client.delete_subpage_config(uuid)
    await client.close()
    
    if res.get("success"):
        await callback.answer("Panel deleted!" if lang == "en" else "Панель удалена!", show_alert=True)
        await cb_panels_list(callback, state)
    else:
        await callback.answer(f"Failed: {res.get('msg')}", show_alert=True)

# CREATE PANEL FLOW
@router.callback_query(F.data == "remna_panel_create")
async def cb_panel_create_start(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    await state.set_state(RemnaPanelStates.waiting_for_name)
    text = (
        "🎛 **Create Subscription Panel** (Step 1 of 2)\n\nEnter panel name:"
        if lang == "en" else
        "🎛 **Создание панели подписок** (Шаг 1 из 2)\n\nВведите имя панели:"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.message(RemnaPanelStates.waiting_for_name)
async def process_create_panel_name(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    name = message.text.strip()
    await state.update_data(panel_name=name)
    await state.set_state(RemnaPanelStates.waiting_for_html)
    
    text = (
        f"🎛 **Creating Panel `{name}`** (Step 2 of 2)\n\nEnter HTML content for the subscription page, or send `/skip` to create empty panel:"
        if lang == "en" else
        f"🎛 **Создание панели `{name}`** (Шаг 2 из 2)\n\nВведите HTML-код для страницы подписки или отправьте `/skip` для создания пустой панели:"
    )
    await message.answer(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")

@router.message(RemnaPanelStates.waiting_for_html)
async def process_create_panel_html(message: Message, state: FSMContext):
    lang = bot_settings.get_language()
    html_input = message.text.strip()
    html = "" if html_input == "/skip" else html_input
    
    data = await state.get_data()
    name = data.get("panel_name")
    
    client = RemnawaveClient.from_storage()
    res = await client.create_subpage_config(name, html)
    await client.close()
    
    if res.get("success"):
        await message.answer("✅ Subscription panel successfully created!" if lang == "en" else "✅ Панель подписок успешно создана!")
    else:
        await message.answer(f"❌ Failed: {res.get('msg')}")
        
    await state.clear()
    from remnawave.handlers.start import show_remna_dashboard
    await show_remna_dashboard(message, state)
