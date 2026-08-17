import json
from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.api_client import ThreeXUIClient, format_bytes, ensure_dict
from core import bot_settings
from core.i18n import t
from keyboards import inline as keyboards

router = Router()

@router.callback_query(F.data == "menu_inbounds")
async def cb_list_inbounds(callback: CallbackQuery):
    client = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client:
        await callback.message.edit_text(
            "❌ Panel credentials not found." if lang == "en" else "❌ Данные панели не найдены.",
            reply_markup=keyboards.main_menu_kb(has_creds=False, lang=lang)
        )
        await callback.answer()
        return

    await callback.answer("Loading inbounds..." if lang == "en" else "Загрузка инбаундов...")
    res = await client.get_inbounds()
    await client.close()

    if not res.get("success"):
        await callback.message.edit_text(
            f"❌ **Error loading inbounds:**\n`{res.get('msg')}`" if lang == "en" else f"❌ **Ошибка загрузки инбаундов:**\n`{res.get('msg')}`",
            reply_markup=keyboards.main_menu_kb(lang=lang),
            parse_mode="Markdown"
        )
        return

    inbounds = res.get("obj", [])
    if not inbounds:
        await callback.message.edit_text(
            "🌐 **No inbounds found.**" if lang == "en" else "🌐 **Инбаунды не найдены.**\nВ панели еще не создано ни одного подключения.",
            reply_markup=keyboards.main_menu_kb(lang=lang),
            parse_mode="Markdown"
        )
        return

    title = t("inbounds_list_title", lang)
    cnt_lbl = t("total_inbounds_count", lang, count=len(inbounds))
    sub_lbl = t("select_inbound_to_manage", lang)

    text = f"{title}\n\n{cnt_lbl}\n{sub_lbl}"

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.inbounds_list_kb(inbounds, lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("inbound_view_"))
async def cb_view_inbound(callback: CallbackQuery):
    inbound_id = int(callback.data.split("_")[2])
    await render_inbound_card(callback, inbound_id)

def build_protocol_details_text(protocol: str, inbound: dict, lang: str) -> str:
    proto_upper = protocol.upper()
    settings = ensure_dict(inbound.get("settings"))
    stream_settings = ensure_dict(inbound.get("streamSettings"))
    net = stream_settings.get("network", "tcp")
    sec = stream_settings.get("security", "none")

    lines = []

    if proto_upper in ["VLESS", "VMESS", "TROJAN"]:
        lines.append(f"🌐 **Network:** `{net}` / `{sec}`\n")
        if sec == "reality":
            real_set = ensure_dict(stream_settings.get("realitySettings"))
            target = real_set.get("target") or "—"
            xver = str(real_set.get("xver", 0))
            inner_set = ensure_dict(real_set.get("settings"))
            utls = inner_set.get("fingerprint") or "—"
            server_names = real_set.get("serverNames", [])
            if server_names:
                first_sni = server_names[0]
                dom_word = "domains" if lang == "en" else "доменов"
                sni_str = f"`{first_sni}` (+{len(server_names)-1} {dom_word})" if len(server_names) > 1 else f"`{first_sni}`"
            else:
                sni_str = "—"
            
            lines.append(f"🎯 **Target:** `{target}`")
            lines.append(f"🔑 **uTLS:** `{utls}`")
            lines.append(f"⚡ **Xver:** `{xver}`")
            lines.append(f"🌐 **SNI:** {sni_str}")

        elif sec == "tls":
            tls_set = ensure_dict(stream_settings.get("tlsSettings"))
            utls = tls_set.get("fingerprint") or "—"
            sni = tls_set.get("serverName") or "—"
            alpn = tls_set.get("alpn")
            alpn_str = ", ".join(alpn) if isinstance(alpn, list) and alpn else "—"
            lines.append(f"🔑 **uTLS:** `{utls}`")
            lines.append(f"🌐 **SNI:** `{sni}`")
            if alpn_str != "—":
                lines.append(f"📜 **ALPN:** `{alpn_str}`")

        if net == "ws":
            ws_set = ensure_dict(stream_settings.get("wsSettings"))
            path = ws_set.get("path", "/")
            headers = ensure_dict(ws_set.get("headers"))
            host = headers.get("Host", "—")
            lines.append(f"📁 **WS Path:** `{path}`")
            if host != "—":
                lines.append(f"🌐 **WS Host:** `{host}`")
        elif net == "grpc":
            grpc_set = ensure_dict(stream_settings.get("grpcSettings"))
            service_name = grpc_set.get("serviceName", "—")
            lines.append(f"📡 **gRPC Service:** `{service_name}`")
        elif net in ["http", "xhttp"]:
            http_set = ensure_dict(stream_settings.get("httpSettings") or stream_settings.get("xhttpSettings"))
            path = http_set.get("path", "/")
            host = http_set.get("host", ["—"])
            host_str = ", ".join(host) if isinstance(host, list) else str(host)
            lines.append(f"📁 **HTTP Path:** `{path}`")
            if host_str != "—":
                lines.append(f"🌐 **HTTP Host:** `{host_str}`")

    elif proto_upper == "SHADOWSOCKS":
        method = settings.get("method") or settings.get("cipher") or "—"
        passwd = settings.get("password") or "—"
        lines.append(f"🌐 **Network:** `{net}` / `{sec}`\n")
        lines.append(f"🔑 **Cipher / Method:** `{method}`")
        if passwd != "—":
            lines.append(f"🔒 **Password:** `{passwd}`")

    elif proto_upper in ["DOKODEMO-DOOR", "DOKODEMO"]:
        addr = settings.get("address", "—")
        f_port = settings.get("port", "—")
        f_net = settings.get("network", "tcp,udp")
        lines.append(f"🎯 **Forward Address:** `{addr}`")
        lines.append(f"🔌 **Forward Port:** `{f_port}`")
        lines.append(f"🌐 **Forward Network:** `{f_net}`")

    elif proto_upper in ["SOCKS", "HTTP"]:
        accounts = settings.get("accounts", [])
        auth_req = ("🟢 YES" if lang == "en" else "🟢 ДА") if accounts else ("⚪ NO" if lang == "en" else "⚪ НЕТ")
        lines.append(f"👤 **Auth Required:** {auth_req}")
        if accounts:
            usernames = [a.get("user", "") for a in accounts if isinstance(a, dict) and a.get("user")]
            if usernames:
                lines.append(f"👥 **Users:** `{', '.join(usernames)}`")

    elif proto_upper in ["HYSTERIA", "HYSTERIA2"]:
        lines.append(f"🌐 **Network:** `{net}` / `{sec}`\n")
        
        h_set = ensure_dict(stream_settings.get("hysteriaSettings") or stream_settings.get("hysteria2Settings"))
        obfs = h_set.get("obfs") or h_set.get("obfsType") or "—"
        up_mbps = h_set.get("up_mbps") or h_set.get("up")
        down_mbps = h_set.get("down_mbps") or h_set.get("down")

        if sec == "tls":
            tls_set = ensure_dict(stream_settings.get("tlsSettings"))
            utls = tls_set.get("fingerprint") or "—"
            sni = tls_set.get("serverName") or "—"
            alpn = tls_set.get("alpn")
            alpn_str = ", ".join(alpn) if isinstance(alpn, list) and alpn else "—"
            lines.append(f"🔑 **uTLS:** `{utls}`")
            lines.append(f"🌐 **SNI:** `{sni}`")
            if alpn_str != "—":
                lines.append(f"📜 **ALPN:** `{alpn_str}`")
        elif sec != "none":
            lines.append(f"🔒 **Security:** `{sec}`")

        if obfs != "—":
            lines.append(f"🛡 **Obfs:** `{obfs}`")
        if up_mbps or down_mbps:
            lines.append(f"🚀 **Speed Limit:** ⬆️ `{up_mbps or '∞'}` Mbps | ⬇️ `{down_mbps or '∞'}` Mbps")

    elif proto_upper == "WIREGUARD":
        mtu = settings.get("mtu", 1420)
        pub_key = settings.get("pubKey") or settings.get("publicKey") or "—"
        lines.append(f"📦 **MTU:** `{mtu}`")
        if pub_key != "—":
            lines.append(f"🔑 **Public Key:** `{pub_key}`")

    else:
        lines.append(f"🌐 **Network:** `{net}` / `{sec}`\n")

    return "\n".join(lines)

async def render_inbound_card(callback: CallbackQuery, inbound_id: int):
    client_api = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client_api:
        await callback.answer("Auth error" if lang == "en" else "Ошибка авторизации", show_alert=True)
        return

    inbound = await client_api.get_inbound(inbound_id)
    server_info = await client_api.get_server_status()
    await client_api.close()

    if not inbound:
        await callback.message.edit_text("❌ Inbound not found." if lang == "en" else "❌ Инбаунд не найден.", reply_markup=keyboards.inbounds_list_kb([], lang=lang))
        return

    server_name = server_info.get("obj", {}).get("hostname", "3x-ui Server")
    remark = inbound.get("remark", f"Inbound #{inbound_id}")
    protocol = inbound.get("protocol", "").upper()
    port = inbound.get("port")
    listen = inbound.get("listen") or ("0.0.0.0 (All interfaces)" if lang == "en" else "0.0.0.0 (Все интерфейсы)")
    enable = t("status_active", lang) if inbound.get("enable", True) else t("status_disabled", lang)
    up = format_bytes(inbound.get("up", 0))
    down = format_bytes(inbound.get("down", 0))
    total = format_bytes(inbound.get("up", 0) + inbound.get("down", 0))

    # Parse client count
    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    active_clients = sum(1 for c in clients if c.get("enable", True))

    # Protocol-specific technical details
    proto_details = build_protocol_details_text(protocol, inbound, lang)

    # Sniffing Details
    sniffing = ensure_dict(inbound.get("sniffing"))
    is_sniff_on = bool(sniffing.get("enabled", False))
    sniff_enabled = t("status_active", lang) if is_sniff_on else t("status_disabled", lang)

    lbl_card = t("inbound_card_title", lang, remark=remark)
    lbl_server = t("server_label", lang)
    lbl_node = t("node_listen", lang)
    lbl_proto = t("proto_port", lang)
    lbl_sniff = t("sniffing_info", lang)
    lbl_sniff_p = t("sniff_protocols", lang)
    lbl_used = t("used_traffic", lang)

    if is_sniff_on:
        dest_override = sniffing.get("destOverride") or []
        dest_str = ", ".join([str(d).upper() for d in dest_override]) if dest_override else "—"
        meta_only = "🟢 YES" if (sniffing.get("metadataOnly") and lang == "en") else ("🟢 ДА" if sniffing.get("metadataOnly") else ("⚪ NO" if lang == "en" else "⚪ НЕТ"))
        route_only = "🟢 YES" if (sniffing.get("routeOnly") and lang == "en") else ("🟢 ДА" if sniffing.get("routeOnly") else ("⚪ NO" if lang == "en" else "⚪ НЕТ"))
        sniff_details = (
            f"   {lbl_sniff_p} `{dest_str}`\n"
            f"   • **Metadata only:** {meta_only}\n"
            f"   • **Route only:** {route_only}\n"
        )
    else:
        sniff_details = ""

    text = (
        f"{lbl_card}\n\n"
        f"{lbl_server} `{server_name}`\n"
        f"{lbl_node} `{listen}`\n"
        f"🆔 **ID:** `{inbound_id}` | Status: **{enable}**\n"
        f"{lbl_proto} `{protocol}` (Port: `{port}`)\n"
        f"{proto_details}\n\n"
        f"{lbl_sniff} {sniff_enabled}\n"
        f"{sniff_details}\n"
        f"{lbl_used} ⬆️ {up} | ⬇️ {down} | Total: `{total}`\n"
        f"👥 Clients: Total: **{len(clients)}** (Active: **{active_clients}**)\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.inbound_detail_kb(inbound_id, lang=lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("clients_list_"))
async def cb_clients_list(callback: CallbackQuery):
    parts = callback.data.split("_")
    inbound_id = int(parts[2])
    page = int(parts[3])

    client = ThreeXUIClient.from_storage()
    lang = bot_settings.get_language()

    if not client:
        await callback.answer("Auth error" if lang == "en" else "Ошибка авторизации", show_alert=True)
        return

    await callback.answer()
    inbound = await client.get_inbound(inbound_id)
    await client.close()

    if not inbound:
        await callback.message.edit_text("❌ Inbound not found." if lang == "en" else "❌ Инбаунд не найден.", reply_markup=keyboards.main_menu_kb(lang=lang))
        return

    settings = ensure_dict(inbound.get("settings"))
    clients = settings.get("clients", [])
    remark = inbound.get("remark", f"#{inbound_id}")

    if not clients:
        await callback.message.edit_text(
            f"👥 **Inbound {remark} — Clients List**\n\nNo clients yet." if lang == "en" else f"👥 **Инбаунд {remark} — Список клиентов**\n\nКлиентов пока нет.",
            reply_markup=keyboards.inbound_detail_kb(inbound_id, lang=lang),
            parse_mode="Markdown"
        )
        return

    text = (
        f"👥 **Inbound {remark} — Clients List**\n\n"
        f"Total users: **{len(clients)}**\n"
        "Select a client below to view and manage:" if lang == "en" else f"👥 **Инбаунд {remark} — Список клиентов**\n\nВсего пользователей: **{len(clients)}**\nВыберите клиента из списка ниже для просмотра и управления:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboards.clients_list_kb(inbound_id, clients, page, lang=lang),
        parse_mode="Markdown"
    )
