import socket
import urllib.parse
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from core.api_client import ThreeXUIClient, format_bytes
from core import bot_settings
from core.i18n import t
from keyboards import inline as keyboards

router = Router()

def format_uptime_days(seconds: int, lang: str = "en") -> str:
    if not seconds:
        return f"0 {t('min', lang)}"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(f"{days} {t('days', lang)}")
    if hours > 0:
        parts.append(f"{hours} {t('hours', lang)}")
    if not parts or minutes > 0:
        parts.append(f"{minutes} {t('min', lang)}")
    return " ".join(parts)

def resolve_hostname(obj: dict, host_url: str) -> str:
    """Dynamically resolves system hostname using API payload or reverse DNS lookup."""
    for key in ["hostName", "hostname", "domain"]:
        val = obj.get(key)
        if val and str(val).strip() and str(val) != "None":
            return str(val).strip()

    public_ip = obj.get("publicIP")
    if isinstance(public_ip, dict):
        pub_h = public_ip.get("hostname")
        if pub_h and str(pub_h).strip() and str(pub_h) != "None":
            return str(pub_h).strip()

    parsed = urllib.parse.urlparse(host_url)
    raw_host = parsed.hostname or ""

    if raw_host:
        try:
            hostname, _, _ = socket.gethostbyaddr(raw_host)
            if hostname:
                return hostname
        except Exception:
            pass
        return raw_host

    return "N/A"

def resolve_xui_version(obj: dict) -> str:
    """Dynamically resolves X-UI panel version."""
    for key in ["xuiVersion", "appVersion", "version", "panelVersion"]:
        val = obj.get(key)
        if val and str(val).strip() and str(val) != "None":
            return str(val).strip()
    if isinstance(obj.get("xui"), dict):
        val = obj["xui"].get("version")
        if val and str(val).strip():
            return str(val).strip()
    return "N/A"

@router.callback_query(F.data == "menu_server")
async def cb_server_status(callback: CallbackQuery):
    client = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client:
        await callback.message.edit_text(
            "❌ Panel credentials not found." if lang == "en" else "❌ Данные панели не найдены.",
            reply_markup=keyboards.main_menu_kb(has_creds=False, lang=lang)
        )
        await callback.answer()
        return

    await callback.answer("Loading server status..." if lang == "en" else "Загрузка статуса сервера...")
    res = await client.get_server_status()

    if not res.get("success"):
        await client.close()
        await callback.message.edit_text(
            f"❌ **Error getting server status:**\n`{res.get('msg', 'Unknown Error')}`" if lang == "en" else f"❌ **Ошибка получения статуса сервера:**\n`{res.get('msg', 'Неизвестная ошибка')}`",
            reply_markup=keyboards.server_menu_kb(lang=lang),
            parse_mode="Markdown"
        )
        return

    obj = res.get("obj", {})

    # Extract Hostname & IPs dynamically
    hostname = resolve_hostname(obj, client.host)

    public_ip_obj = obj.get("publicIP") if isinstance(obj.get("publicIP"), dict) else {}
    parsed_host = urllib.parse.urlparse(client.host)
    ipv4 = public_ip_obj.get("ipv4") or obj.get("ipv4") or parsed_host.hostname or "N/A"
    ipv6 = public_ip_obj.get("ipv6") or obj.get("ipv6") or "N/A"
    if not ipv6 or ipv6 == "None":
        ipv6 = "N/A"

    # Versions
    xui_version = resolve_xui_version(obj)
    xray_obj = obj.get("xray", {}) if isinstance(obj.get("xray"), dict) else {}
    xray_version = xray_obj.get("version", "N/A")
    xray_state = xray_obj.get("state", "running")

    # Uptime & Load
    uptime_sec = obj.get("uptime", 0)
    uptime_str = format_uptime_days(uptime_sec, lang=lang)
    
    loads = obj.get("loads") or [0.0, 0.0, 0.0]
    if isinstance(loads, list) and len(loads) >= 3:
        load_str = f"{loads[0]:.2f}, {loads[1]:.2f}, {loads[2]:.2f}"
    else:
        cpu_val = obj.get("cpu", 0)
        load_str = f"{cpu_val:.2f}, 0.00, 0.00"

    # RAM Usage
    mem_obj = obj.get("mem", {}) if isinstance(obj.get("mem"), dict) else {}
    mem_total = mem_obj.get("total", 0)
    mem_used = mem_obj.get("current", 0)
    ram_str = f"{format_bytes(mem_used)}/{format_bytes(mem_total)}" if mem_total else "N/A"

    # Disk Usage
    disk_obj = obj.get("disk", {}) if isinstance(obj.get("disk"), dict) else {}
    disk_total = disk_obj.get("total", 0)
    disk_used = disk_obj.get("current", 0)
    if disk_total:
        disk_pct = int((disk_used / disk_total) * 100)
        disk_str = f"{format_bytes(disk_used)} / {format_bytes(disk_total)} ({disk_pct}%)"
    else:
        disk_str = "N/A"

    # Connections & Online Clients
    online_count = obj.get("onlineCount", 0)
    tcp_count = obj.get("tcpCount", 0)
    udp_count = obj.get("udpCount", 0)

    # Net Traffic (Total Data)
    net_traffic = obj.get("netTraffic") if isinstance(obj.get("netTraffic"), dict) else {}
    if net_traffic and ("sent" in net_traffic or "recv" in net_traffic):
        up_bytes = net_traffic.get("sent", 0)
        down_bytes = net_traffic.get("recv", 0)
    else:
        net_io = obj.get("netIO") if isinstance(obj.get("netIO"), dict) else {}
        up_bytes = net_io.get("up", 0) or net_io.get("sent", 0)
        down_bytes = net_io.get("down", 0) or net_io.get("recv", 0)

    total_bytes = up_bytes + down_bytes
    traffic_str = f"{format_bytes(total_bytes)} (↑{format_bytes(up_bytes)}, ↓{format_bytes(down_bytes)})"

    await client.close()

    text = (
        f"{t('hostname', lang)} `{hostname}`\n"
        f"{t('xui_ver', lang)} `{xui_version}`\n"
        f"{t('xray_ver', lang)} `{xray_version}`\n"
        f"🌐 **IPv4:** `{ipv4}`\n"
        f"🌐 **IPv6:** `{ipv6}`\n"
        f"{t('server_uptime', lang)} `{uptime_str}`\n"
        f"{t('server_load', lang)} `{load_str}`\n"
        f"{t('server_ram', lang)} `{ram_str}`\n"
        f"{t('server_disk', lang)} `{disk_str}`\n"
        f"{t('online_clients', lang)} `{online_count}`\n"
        f"{t('tcp_conn', lang)} `{tcp_count}`\n"
        f"{t('udp_conn', lang)} `{udp_count}`\n"
        f"{t('server_traffic', lang)} `{traffic_str}`\n"
        f"{t('xray_status', lang)} `{xray_state}`"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.server_menu_kb(lang=lang),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise e

@router.callback_query(F.data == "action_restart_xray")
async def cb_restart_xray(callback: CallbackQuery):
    client = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client:
        await callback.answer("Error: Credentials missing!" if lang == "en" else "Ошибка: Настройки не найдены!", show_alert=True)
        return

    await callback.answer("Restarting Xray..." if lang == "en" else "Перезапуск Xray...")
    res = await client.restart_xray()
    await client.close()

    if res.get("success"):
        await callback.message.answer("⚡ **Xray Core restarted successfully!**" if lang == "en" else "⚡ **Xray Core успешно перезапущен!**", parse_mode="Markdown")
    else:
        await callback.message.answer(
            f"❌ **Error restarting Xray:**\n`{res.get('msg')}`" if lang == "en" else f"❌ **Ошибка при перезапуске Xray:**\n`{res.get('msg')}`",
            parse_mode="Markdown"
        )
