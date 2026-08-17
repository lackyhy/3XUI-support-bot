from typing import Optional, Dict, Any, List
import json
from urllib.parse import urlparse
from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.api_client import ThreeXUIClient, format_bytes, ensure_dict
import core.crypto_storage as crypto_storage
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

def extract_utls(stream_settings: dict) -> str:
    tls_set = ensure_dict(stream_settings.get("tlsSettings"))
    fp = tls_set.get("fingerprint") or tls_set.get("utls")
    if not fp:
        inner_tls = ensure_dict(tls_set.get("settings"))
        fp = inner_tls.get("fingerprint") or inner_tls.get("utls")
    if fp:
        return str(fp)

    real_set = ensure_dict(stream_settings.get("realitySettings"))
    fp = real_set.get("fingerprint") or real_set.get("utls")
    if not fp:
        inner_real = ensure_dict(real_set.get("settings"))
        fp = inner_real.get("fingerprint") or inner_real.get("utls")
    if fp:
        return str(fp)

    fp = stream_settings.get("fingerprint") or stream_settings.get("utls")
    if fp:
        return str(fp)

    return "—"

def extract_tls_versions(stream_settings: dict) -> str:
    tls_set = ensure_dict(stream_settings.get("tlsSettings"))
    real_set = ensure_dict(stream_settings.get("realitySettings"))
    h_set = ensure_dict(stream_settings.get("hysteriaSettings") or stream_settings.get("hysteria2Settings"))
    
    inner_tls = ensure_dict(tls_set.get("settings"))
    inner_real = ensure_dict(real_set.get("settings"))
    inner_h = ensure_dict(h_set.get("settings"))

    sources = [tls_set, inner_tls, real_set, inner_real, h_set, inner_h, stream_settings]

    min_v = ""
    max_v = ""

    for s in sources:
        if not min_v:
            min_v = str(s.get("minVersion") or s.get("min_version") or s.get("minVer") or "")
        if not max_v:
            max_v = str(s.get("maxVersion") or s.get("max_version") or s.get("maxVer") or "")

    min_v = min_v.replace("VersionTLS", "").replace("TLS", "").replace("v", "").strip()
    max_v = max_v.replace("VersionTLS", "").replace("TLS", "").replace("v", "").strip()

    if min_v in ["12", "1.2"]: min_v = "1.2"
    elif min_v in ["13", "1.3"]: min_v = "1.3"
    elif min_v in ["10", "1.0"]: min_v = "1.0"
    elif min_v in ["11", "1.1"]: min_v = "1.1"

    if max_v in ["12", "1.2"]: max_v = "1.2"
    elif max_v in ["13", "1.3"]: max_v = "1.3"
    elif max_v in ["10", "1.0"]: max_v = "1.0"
    elif max_v in ["11", "1.1"]: max_v = "1.1"

    if min_v and max_v:
        return min_v if min_v == max_v else f"{min_v} / {max_v}"
    elif min_v:
        return f"≥ {min_v}"
    elif max_v:
        return f"≤ {max_v}"
    
    return "1.2 / 1.3"

def build_protocol_details_text(protocol: str, inbound: dict, lang: str) -> str:
    proto_upper = protocol.upper()
    settings = ensure_dict(inbound.get("settings"))
    stream_settings = ensure_dict(inbound.get("streamSettings"))
    net = stream_settings.get("network", "tcp")
    sec = stream_settings.get("security", "none")

    lines = []

    if proto_upper in ["VLESS", "VMESS", "TROJAN"]:
        lines.append(f"🌐 **Network:** `{net}` / `{sec}`")
        utls = extract_utls(stream_settings)

        if sec == "reality":
            real_set = ensure_dict(stream_settings.get("realitySettings"))
            target = real_set.get("target") or "—"
            xver = str(real_set.get("xver", 0))
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
            sni = tls_set.get("serverName") or "—"
            alpn = tls_set.get("alpn")
            alpn_str = ", ".join(alpn) if isinstance(alpn, list) and alpn else "—"
            tls_ver = extract_tls_versions(stream_settings)

            lines.append(f"🔑 **uTLS:** `{utls}`")
            lines.append(f"🌐 **SNI:** `{sni}`")
            if tls_ver:
                lines.append(f"🔒 **TLS Version:** `{tls_ver}`")
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
        lines.append(f"🌐 **Network:** `{net}` / `{sec}`")
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
        lines.append(f"🌐 **Network:** `{net}` / `{sec}`")
        
        h_set = ensure_dict(stream_settings.get("hysteriaSettings") or stream_settings.get("hysteria2Settings"))
        obfs = h_set.get("obfs") or h_set.get("obfsType") or "—"
        up_mbps = h_set.get("up_mbps") or h_set.get("up")
        down_mbps = h_set.get("down_mbps") or h_set.get("down")

        utls = extract_utls(stream_settings)

        if sec == "tls":
            tls_set = ensure_dict(stream_settings.get("tlsSettings"))
            sni = tls_set.get("serverName") or "—"
            alpn = tls_set.get("alpn")
            alpn_str = ", ".join(alpn) if isinstance(alpn, list) and alpn else "—"
            tls_ver = extract_tls_versions(stream_settings)

            lines.append(f"🔑 **uTLS:** `{utls}`")
            lines.append(f"🌐 **SNI:** `{sni}`")
            if tls_ver:
                lines.append(f"🔒 **TLS Version:** `{tls_ver}`")
            if alpn_str != "—":
                lines.append(f"📜 **ALPN:** `{alpn_str}`")
        elif sec != "none":
            if utls != "—":
                lines.append(f"🔑 **uTLS:** `{utls}`")
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

    elif proto_upper in ["MTPROTO", "MTP"]:
        st_dicts = [settings, ensure_dict(stream_settings.get("settings")), stream_settings, inbound]
        
        sni = ""
        f_ip = ""
        f_port = ""
        f_proxy = None
        acc_proxy = None
        pref_ip = ""
        debug_log = None
        max_conn = None
        xray_route = None
        pub_v4 = ""
        pub_v6 = ""
        secret = ""

        for d in st_dicts:
            if not isinstance(d, dict): continue
            if not sni:
                sni = str(d.get("sni") or d.get("domain") or d.get("fakeTls") or d.get("fake_tls") or d.get("host") or "")
            if not f_ip:
                f_ip = str(d.get("frontingIp") or d.get("fronting_ip") or d.get("domainFrontingIp") or d.get("domain_fronting_ip") or "")
            if not f_port:
                f_port = str(d.get("frontingPort") or d.get("fronting_port") or d.get("domainFrontingPort") or d.get("domain_fronting_port") or "")
            if f_proxy is None and ("frontingProxy" in d or "domainFrontingProxy" in d or "fronting_proxy" in d):
                f_proxy = bool(d.get("frontingProxy") or d.get("domainFrontingProxy") or d.get("fronting_proxy"))
            if acc_proxy is None and ("acceptProxy" in d or "accept_proxy" in d):
                acc_proxy = bool(d.get("acceptProxy") or d.get("accept_proxy"))
            if not pref_ip:
                pref_ip = str(d.get("preferIp") or d.get("prefer_ip") or d.get("domainStrategy") or "")
            if debug_log is None and ("debug" in d or "debugLog" in d or "debug_log" in d):
                debug_log = bool(d.get("debug") or d.get("debugLog") or d.get("debug_log"))
            if max_conn is None and ("maxConnections" in d or "maxClients" in d or "max_connections" in d):
                max_conn = d.get("maxConnections") or d.get("maxClients") or d.get("max_connections")
            if xray_route is None and ("xray" in d or "routingThroughXray" in d or "xrayRouting" in d):
                xray_route = bool(d.get("xray") or d.get("routingThroughXray") or d.get("xrayRouting"))
            if not pub_v4:
                pub_v4 = str(d.get("publicIPv4") or d.get("public_ipv4") or d.get("publicIp") or d.get("public_ip") or d.get("ip4") or "")
            if not pub_v6:
                pub_v6 = str(d.get("publicIPv6") or d.get("public_ipv6") or d.get("publicIp6") or d.get("public_ip6") or d.get("ip6") or "")
            if not secret:
                secret = str(d.get("secret") or "")

        if (not sni or sni == "—") and secret and len(secret) > 32:
            try:
                if secret.startswith("ee"):
                    domain_part = secret[34:]
                    decoded_domain = bytes.fromhex(domain_part).decode("ascii", errors="ignore")
                    if decoded_domain and "." in decoded_domain:
                        sni = decoded_domain.strip()
            except Exception:
                pass

        if not sni: sni = "www.cloudflare.com"
        if not f_ip: f_ip = "127.0.0.1"
        if not f_port: f_port = "443"
        if not pref_ip: pref_ip = "prefer-ipv4"
        if max_conn is None: max_conn = 0

        bool_fmt = lambda b: ("🟢 YES" if lang == "en" else "🟢 ДА") if b else ("⚪ NO" if lang == "en" else "⚪ НЕТ")

        lines.append(f"🌐 **FakeTLS (SNI):** `{sni}`")
        lines.append(f"🖥 **Domain Fronting:** `{f_ip}:{f_port}`")
        if f_proxy is not None:
            lines.append(f"⚡ **Fronting PROXY:** {bool_fmt(f_proxy)}")
        if acc_proxy is not None:
            lines.append(f"⚡ **Accept PROXY:** {bool_fmt(acc_proxy)}")
        lines.append(f"⚙️ **IP Preference:** `{pref_ip}`")
        if debug_log is not None:
            lines.append(f"📜 **Debug Log:** {bool_fmt(debug_log)}")
        lines.append(f"👥 **Max Connections:** `{max_conn}`")
        if xray_route is not None:
            lines.append(f"🔀 **Xray Routing:** {bool_fmt(xray_route)}")
        lines.append(f"🌐 **Public IPv4:** `{pub_v4 if pub_v4 else '1.2.3.4'}`")
        lines.append(f"🌐 **Public IPv6:** `{pub_v6 if pub_v6 else '2001:db8::1'}`")

    elif proto_upper == "TUN":
        iface = settings.get("name") or settings.get("interfaceName") or settings.get("interface") or "xray0"
        mtu = settings.get("mtu", 1500)
        gw = settings.get("gateway") or settings.get("gateways") or "—"
        gw_str = ", ".join(gw) if isinstance(gw, list) else str(gw)
        dns_val = settings.get("dns") or "—"
        dns_str = ", ".join(dns_val) if isinstance(dns_val, list) else str(dns_val)
        out_iface = settings.get("outgoing") or settings.get("outgoingInterface") or "auto"

        lines.append(f"🔌 **Interface:** `{iface}`")
        lines.append(f"📦 **MTU:** `{mtu}`")
        if gw_str != "—":
            lines.append(f"🌐 **Gateway:** `{gw_str}`")
        if dns_str != "—":
            lines.append(f"📡 **DNS:** `{dns_str}`")
        lines.append(f"⚙️ **Outgoing Interface:** `{out_iface}`")

    elif proto_upper == "TUNNEL":
        addr = settings.get("address") or settings.get("rewriteAddress") or settings.get("targetAddress") or "—"
        r_port = settings.get("port") or settings.get("rewritePort") or settings.get("targetPort") or "—"
        net_allowed = settings.get("network") or settings.get("allowedNetwork") or "TCP, UDP"
        redirect = settings.get("followRedirect") or settings.get("redirect") or False
        redir_str = "🟢 YES" if (redirect and lang == "en") else ("🟢 ДА" if redirect else ("⚪ NO" if lang == "en" else "⚪ НЕТ"))

        lines.append(f"🎯 **Rewrite Address:** `{addr}`")
        lines.append(f"🔌 **Rewrite Port:** `{r_port}`")
        lines.append(f"🌐 **Allowed Network:** `{net_allowed}`")
        lines.append(f"🔀 **Follow Redirect:** {redir_str}")

    else:
        lines.append(f"🌐 **Network:** `{net}` / `{sec}`")

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

    parsed_host = urlparse(client_api.host)
    host_display = parsed_host.hostname or parsed_host.netloc or client_api.host
    creds = crypto_storage.load_credentials() or {}
    srv_name = creds.get("name")
    if srv_name and srv_name not in ["3x-ui Server", "3x-ui", "Основной сервер"]:
        server_name = srv_name
    else:
        server_name = host_display
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
        f"{lbl_proto} `{protocol}` (Port: `{port}`)\n\n"
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
