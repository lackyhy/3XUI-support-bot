from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from x_ui.core import crypto_storage, bot_settings
from x_ui.core.api_client import format_bytes
from remnawave.core.api_client import RemnawaveClient
from remnawave.keyboards import inline as keyboards

router = Router()

def format_uptime(seconds: int, lang: str = "en") -> str:
    if not seconds or seconds < 0:
        return "0m" if lang == "en" else "0 мин"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d" if lang == "en" else f"{days} д")
    if hours > 0:
        parts.append(f"{hours}h" if lang == "en" else f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes}m" if lang == "en" else f"{minutes} мин")
    return " ".join(parts) if parts else ("< 1m" if lang == "en" else "< 1 мин")

def parse_to_gb(size_str: str) -> str:
    if not size_str:
        return "0.00 GB"
    try:
        parts = size_str.strip().split()
        if len(parts) != 2:
            val = float(size_str)
            return f"{val / (1024 ** 3):.2f} GB"
        value_str, unit = parts[0], parts[1].upper()
        value = float(value_str)
        
        if "TI" in unit or "TB" in unit:
            bytes_val = value * (1024 ** 4)
        elif "GI" in unit or "GB" in unit:
            bytes_val = value * (1024 ** 3)
        elif "MI" in unit or "MB" in unit:
            bytes_val = value * (1024 ** 2)
        elif "KI" in unit or "KB" in unit:
            bytes_val = value * 1024
        else:
            bytes_val = value
            
        gb_val = bytes_val / (1024 ** 3)
        return f"{gb_val:.2f} GB"
    except Exception:
        return size_str

async def show_remna_dashboard(event, state: FSMContext = None):
    if state:
        await state.clear()
        
    lang = bot_settings.get_language()
    active_panel = crypto_storage.get_active_panel()
    if not active_panel:
        text = (
            "❌ **No panel connected yet.**\nUse settings/setup to add a panel."
            if lang == "en" else
            "❌ **Нет подключенных панелей.**\nИспользуйте меню настройки для добавления панели."
        )
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=keyboards.remna_main_menu_kb("No Server", lang=lang), parse_mode="Markdown")
            await event.answer()
        else:
            await event.answer(text, reply_markup=keyboards.remna_main_menu_kb("No Server", lang=lang), parse_mode="Markdown")
        return

    name = active_panel.get("name", "Remnawave Server")
    host = active_panel.get("host")
    
    # Try fetching system stats
    client = RemnawaveClient.from_storage(active_panel.get("id"))
    stats_data = None
    if client:
        res = await client.get_system_stats()
        await client.close()
        if res.get("success", False):
            stats_data = res.get("response", {})

    if stats_data:
        cpu_cores = stats_data.get("cpu", {}).get("cores", "—")
        mem = stats_data.get("memory", {})
        total_mem = mem.get("total", 0)
        used_mem = mem.get("used", 0)
        
        mem_pct = 0
        if total_mem > 0:
            mem_pct = round((used_mem / total_mem) * 100, 1)
            
        ram_str = f"{format_bytes(used_mem)} / {format_bytes(total_mem)} ({mem_pct}%)"
        uptime = stats_data.get("uptime", 0)
        uptime_str = format_uptime(int(uptime), lang=lang)
        
        users_info = stats_data.get("users", {})
        total_users = users_info.get("totalUsers", 0)
        status_counts = users_info.get("statusCounts", {})
        active_u = status_counts.get("ACTIVE", 0)
        disabled_u = status_counts.get("DISABLED", 0)
        limited_u = status_counts.get("LIMITED", 0)
        expired_u = status_counts.get("EXPIRED", 0)
        
        online_now = stats_data.get("onlineStats", {}).get("onlineNow", 0)
        nodes_online = stats_data.get("nodes", {}).get("totalOnline", 0)
        lifetime_traffic = stats_data.get("nodes", {}).get("totalBytesLifetime", "0 B")
        try:
            if isinstance(lifetime_traffic, (int, float)):
                lifetime_traffic_str = format_bytes(float(lifetime_traffic))
                lifetime_traffic_str = parse_to_gb(lifetime_traffic_str)
            else:
                lifetime_traffic_str = parse_to_gb(str(lifetime_traffic))
        except Exception:
            lifetime_traffic_str = "—"
            
        text = (
            f"⚡ **Remnawave Dashboard: {name}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🌐 **Host**: `{host}`\n"
            f"🟢 **Status**: Online\n"
            f"⏳ **Uptime**: {uptime_str}\n"
            f"🖥 **CPU**: {cpu_cores} cores\n"
            f"📋 **RAM**: {ram_str}\n"
            f"👥 **Users**: {total_users} (🟢 {active_u} | 🔴 {disabled_u} | ⚠️ {limited_u} | ⏳ {expired_u})\n"
            f"👥 **Online Now**: `{online_now} users`\n"
            f"📡 **Nodes Online**: `{nodes_online}`\n"
            f"🚦 **Lifetime Traffic**: `{lifetime_traffic_str}`"
            if lang == "en" else
            f"⚡ **Панель управления Remnawave: {name}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🌐 **Адрес**: `{host}`\n"
            f"🟢 **Статус**: Онлайн\n"
            f"⏳ **Uptime**: {uptime_str}\n"
            f"🖥 **Процессор**: {cpu_cores} ядер\n"
            f"📋 **ОЗУ**: {ram_str}\n"
            f"👥 **Пользователи**: {total_users} (🟢 {active_u} | 🔴 {disabled_u} | ⚠️ {limited_u} | ⏳ {expired_u})\n"
            f"👥 **Онлайн сейчас**: `{online_now} польз.`\n"
            f"📡 **Активные ноды**: `{nodes_online}`\n"
            f"🚦 **Общий трафик**: `{lifetime_traffic_str}`"
        )
    else:
        text = (
            f"⚡ **Remnawave Dashboard: {name}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🌐 **Host**: `{host}`\n"
            f"🔴 **Status**: Offline / Unreachable\n"
            f"⏳ **Uptime**: —\n"
            f"🖥 **CPU**: —\n"
            f"📋 **RAM**: —\n"
            f"👥 **Users**: —"
            if lang == "en" else
            f"⚡ **Панель управления Remnawave: {name}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🌐 **Адрес**: `{host}`\n"
            f"🔴 **Статус**: Офлайн / Недоступен\n"
            f"⏳ **Uptime**: —\n"
            f"🖥 **Процессор**: —\n"
            f"📋 **ОЗУ**: —\n"
            f"👥 **Пользователи**: —"
        )

    try:
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=keyboards.remna_main_menu_kb(name, lang=lang), parse_mode="Markdown")
            await event.answer()
        else:
            await event.answer(text, reply_markup=keyboards.remna_main_menu_kb(name, lang=lang), parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            if isinstance(event, CallbackQuery):
                await event.answer()
        else:
            raise e

@router.callback_query(F.data == "remna_menu_settings")
async def cb_remna_settings(callback: CallbackQuery):
    lang = bot_settings.get_language()
    active_panel = crypto_storage.get_active_panel()
    name = active_panel.get("name", "Server") if active_panel else "—"
    
    text = (
        f"⚙️ **Remnawave Settings & Control Room**\n\n"
        f"Active panel: **{name}**\n\n"
        f"Here you can rename or remove this panel connection, or switch your interface language."
        if lang == "en" else
        f"⚙️ **Центр управления Remnawave**\n\n"
        f"Активный сервер: **{name}**\n\n"
        f"Здесь вы можете переименовать или удалить подключение к панели, или переключить язык бота."
    )
    await callback.message.edit_text(text, reply_markup=keyboards.remna_settings_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "remna_cancel")
async def cb_remna_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_remna_dashboard(callback, state)

@router.callback_query(F.data == "remna_menu_dashboard")
async def cb_remna_dashboard(callback: CallbackQuery, state: FSMContext):
    lang = bot_settings.get_language()
    active_panel = crypto_storage.get_active_panel()
    if not active_panel:
        await callback.answer("Error" if lang == "en" else "Ошибка", show_alert=True)
        return
        
    name = active_panel.get("name", "Remnawave Server")
    host = active_panel.get("host")
    
    client = RemnawaveClient.from_storage(active_panel.get("id"))
    if not client:
        await callback.answer("Error" if lang == "en" else "Ошибка", show_alert=True)
        return
        
    import asyncio
    results = await asyncio.gather(
        client.get_system_stats(),
        client.get_system_bandwidth(),
        client.get_system_health(),
        return_exceptions=True
    )
    await client.close()
    
    stats_data = None
    bandwidth_data = None
    health_data = None
    
    if not isinstance(results[0], Exception) and results[0].get("success"):
        stats_data = results[0].get("response", {})
    if not isinstance(results[1], Exception) and results[1].get("success"):
        bandwidth_data = results[1].get("response", {})
    if not isinstance(results[2], Exception) and results[2].get("success"):
        health_data = results[2].get("response", {})
        
    if not stats_data:
        await callback.answer("Error fetching dashboard data" if lang == "en" else "Ошибка получения данных дашборда", show_alert=True)
        return
        
    # Stats details
    cpu_cores = stats_data.get("cpu", {}).get("cores", "—")
    mem = stats_data.get("memory", {})
    total_mem = mem.get("total", 0)
    used_mem = mem.get("used", 0)
    
    mem_pct = 0
    if total_mem > 0:
        mem_pct = round((used_mem / total_mem) * 100, 1)
        
    ram_str = f"{format_bytes(used_mem)} / {format_bytes(total_mem)} ({mem_pct}%)"
    uptime = stats_data.get("uptime", 0)
    uptime_str = format_uptime(int(uptime), lang=lang)
    
    users_info = stats_data.get("users", {})
    total_users = users_info.get("totalUsers", 0)
    status_counts = users_info.get("statusCounts", {})
    active_u = status_counts.get("ACTIVE", 0)
    disabled_u = status_counts.get("DISABLED", 0)
    limited_u = status_counts.get("LIMITED", 0)
    expired_u = status_counts.get("EXPIRED", 0)
    
    online_now = stats_data.get("onlineStats", {}).get("onlineNow", 0)
    online_today = stats_data.get("onlineStats", {}).get("onlineToday") or online_now
    online_week = stats_data.get("onlineStats", {}).get("onlineThisWeek") or online_now
    never_online = stats_data.get("onlineStats", {}).get("neverOnline", 0)
    
    nodes_online = stats_data.get("nodes", {}).get("totalOnline", 0)
    lifetime_traffic = stats_data.get("nodes", {}).get("totalBytesLifetime", "0 B")
    try:
        if isinstance(lifetime_traffic, (int, float)):
            lifetime_traffic_str = format_bytes(float(lifetime_traffic))
            lifetime_traffic_str = parse_to_gb(lifetime_traffic_str)
        else:
            lifetime_traffic_str = parse_to_gb(str(lifetime_traffic))
    except Exception:
        lifetime_traffic_str = "—"
        
    # Health runtime metrics
    runtime_metrics = health_data.get("runtimeMetrics", []) if health_data else []
    total_processes = len(runtime_metrics)
    total_rss_bytes = sum(m.get("rss", 0) for m in runtime_metrics)
    total_heap_used_bytes = sum(m.get("heapUsed", 0) for m in runtime_metrics)
    avg_event_loop_delay = (
        sum(m.get("eventLoopDelayMs", 0) for m in runtime_metrics) / total_processes
        if total_processes > 0 else 0
    )
    
    proc_details_list = []
    runtime_details_list = []
    for m in runtime_metrics:
        p_name = m.get("instanceType") or m.get("instanceId") or "Process"
        p_rss = m.get("rss", 0)
        p_pid = m.get("pid", 0)
        p_heap_used = m.get("heapUsed", 0)
        p_heap_total = m.get("heapTotal", 0)
        p_ext = m.get("external", 0)
        p_buf = m.get("arrayBuffers", 0)
        p_el_delay = m.get("eventLoopDelayMs", 0)
        p_el_p99 = m.get("eventLoopP99Ms", 0)
        p_handles = m.get("activeHandles", 0)
        p_heap_pct = (p_heap_used / p_heap_total * 100) if p_heap_total else 0
        
        proc_details_list.append(f"• **{p_name}**: `{format_bytes(p_rss)}`")
        runtime_details_list.append(
            f"🔸 **{p_name}** (PID: `{p_pid}`):\n"
            f"  • Heap: `{format_bytes(p_heap_used)} / {format_bytes(p_heap_total)}` ({p_heap_pct:.1f}%)\n"
            f"  • RSS: `{format_bytes(p_rss)}` | Ext: `{format_bytes(p_ext)}` | Buf: `{format_bytes(p_buf)}`\n"
            f"  • Event Loop: `{p_el_delay:.2f} ms` (P99: `{p_el_p99:.2f} ms`)\n"
            f"  • Active Handles: `{p_handles}`"
        )
        
    proc_details_str = "\n".join(proc_details_list) if proc_details_list else "—"
    runtime_details_str = "\n\n".join(runtime_details_list) if runtime_details_list else "—"
    
    # Bandwidth Stats
    bw = bandwidth_data or {}
    def parse_bw_item(key: str) -> str:
        item = bw.get(key) or {}
        curr = item.get("current") or "—"
        prev = item.get("previous") or "—"
        diff = item.get("difference") or "—"
        return f"`{curr}` (vs prev: `{prev}`, diff: `{diff}`)"
        
    bw_today = parse_bw_item("bandwidthLastTwoDays")
    bw_7d = parse_bw_item("bandwidthLastSevenDays")
    bw_30d = parse_bw_item("bandwidthLast30Days")
    bw_month = parse_bw_item("bandwidthCalendarMonth")
    bw_year = parse_bw_item("bandwidthCurrentYear")
    
    text = (
        f"📊 **Remnawave Dashboard: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌐 **Host**: `{host}`\n"
        f"🟢 **Status**: Online\n"
        f"⏳ **Uptime**: {uptime_str}\n\n"
        
        f"🖥 **System & RAM**:\n"
        f"• **RAM Usage**: {ram_str}\n"
        f"• **CPU**: {cpu_cores} cores\n"
        f"• **Nodes Online**: `{nodes_online}`\n"
        f"• **Total Traffic**: `{lifetime_traffic_str}`\n\n"
        
        f"👥 **Users Summary**:\n"
        f"• **Total**: `{total_users}`\n"
        f"• **Active**: `{active_u}` | **Expired**: `{expired_u}`\n"
        f"• **Limited**: `{limited_u}` | **Disabled**: `{disabled_u}`\n\n"
        
        f"🟢 **Online Stats**:\n"
        f"• **Online Now**: `{online_now}`\n"
        f"• **Online Today**: `{online_today}`\n"
        f"• **Online This Week**: `{online_week}`\n"
        f"• **Never Online**: `{never_online}`\n\n"
        
        f"📈 **Bandwidth Usage**:\n"
        f"• **Today**: {bw_today}\n"
        f"• **Last 7 days**: {bw_7d}\n"
        f"• **Last 30 days**: {bw_30d}\n"
        f"• **Calendar Month**: {bw_month}\n"
        f"• **Current Year**: {bw_year}\n\n"
        
        f"⚙️ **Remnawave Runtime Usage**:\n"
        f"• **Processes**: `{total_processes}`\n"
        f"• **Total RAM (RSS)**: `{format_bytes(total_rss_bytes)}`\n"
        f"• **Heap Used**: `{format_bytes(total_heap_used_bytes)}`\n"
        f"• **Avg Event Loop Delay**: `{avg_event_loop_delay:.2f} ms`\n\n"
        
        f"📋 **Process Details**:\n"
        f"{proc_details_str}\n\n"
        
        f"🔍 **Runtime Details**:\n"
        f"{runtime_details_str}"
        if lang == "en" else
        f"📊 **Панель управления Remnawave: {name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌐 **Адрес**: `{host}`\n"
        f"🟢 **Статус**: Онлайн\n"
        f"⏳ **Uptime**: {uptime_str}\n\n"
        
        f"🖥 **Система и Память**:\n"
        f"• **Загрузка ОЗУ**: {ram_str}\n"
        f"• **Процессор**: {cpu_cores} ядер\n"
        f"• **Активные ноды**: `{nodes_online}`\n"
        f"• **Общий трафик**: `{lifetime_traffic_str}`\n\n"
        
        f"👥 **Сводка пользователей**:\n"
        f"• **Всего**: `{total_users}`\n"
        f"• **Активные**: `{active_u}` | **Истекшие**: `{expired_u}`\n"
        f"• **Ограниченные**: `{limited_u}` | **Отключенные**: `{disabled_u}`\n\n"
        
        f"🟢 **Статистика онлайна**:\n"
        f"• **Онлайн сейчас**: `{online_now}`\n"
        f"• **Онлайн сегодня**: `{online_today}`\n"
        f"• **Онлайн на этой неделе**: `{online_week}`\n"
        f"• **Ни разу не подключались**: `{never_online}`\n\n"
        
        f"📈 **Использование пропускной способности**:\n"
        f"• **Сегодня**: {bw_today}\n"
        f"• **За 7 дней**: {bw_7d}\n"
        f"• **За 30 дней**: {bw_30d}\n"
        f"• **Календарный месяц**: {bw_month}\n"
        f"• **Текущий год**: {bw_year}\n\n"
        
        f"⚙️ **Использование процессов Remnawave**:\n"
        f"• **Всего процессов**: `{total_processes}`\n"
        f"• **Всего ОЗУ (RSS)**: `{format_bytes(total_rss_bytes)}`\n"
        f"• **Используемый Heap**: `{format_bytes(total_heap_used_bytes)}`\n"
        f"• **Средняя задержка Event Loop**: `{avg_event_loop_delay:.2f} ms`\n\n"
        
        f"📋 **Детализация процессов**:\n"
        f"{proc_details_str}\n\n"
        
        f"🔍 **Детализация Runtime**:\n"
        f"{runtime_details_str}"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboards.cancel_kb(lang=lang), parse_mode="Markdown")
    await callback.answer()
