import json
import base64
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
import httpx
from core import crypto_storage

def format_bytes(size: int) -> str:
    """Format byte sizes to human-readable strings."""
    if not size or size < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} EB"

def ensure_dict(val: Any) -> Dict[str, Any]:
    """Helper to safely parse dict or JSON string to dictionary."""
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return json.loads(val)
        except Exception:
            pass
    return {}

def extract_external_sub(client_data: Dict[str, Any]) -> Optional[str]:
    """Extracts external subscription URL from client dictionary or API response across all 3x-ui schema variations."""
    if not client_data or not isinstance(client_data, dict):
        return None

    obj = client_data.get("obj") if isinstance(client_data.get("obj"), dict) else client_data

    # 1. Check externalLinks array (Modern Sanaei 3x-ui v2.4+ schema!)
    ext_links = obj.get("externalLinks")
    if isinstance(ext_links, list) and ext_links:
        for link_obj in ext_links:
            if isinstance(link_obj, dict):
                val = link_obj.get("value") or link_obj.get("url") or link_obj.get("link")
                if val and isinstance(val, str) and val.startswith("http"):
                    return val.strip()

    # 2. Check inner client dict
    client = obj.get("client") if isinstance(obj.get("client"), dict) else obj

    for key in ['subLink', 'subUrl', 'externalSub', 'external_sub', 'externalSubscription', 'sub_url', 'sub_link']:
        val = client.get(key)
        if val and isinstance(val, str) and val.startswith('http'):
            return val.strip()

    comment = client.get('comment')
    if comment and isinstance(comment, str) and comment.startswith('http'):
        return comment.strip()

    reverse = client.get('reverse')
    if reverse:
        if isinstance(reverse, str):
            try:
                reverse = json.loads(reverse)
            except Exception:
                pass
        if isinstance(reverse, dict):
            for key in ['subLink', 'subUrl', 'externalSub', 'external_sub', 'url', 'link']:
                val = reverse.get(key)
                if val and isinstance(val, str) and val.startswith('http'):
                    return val.strip()
            ext_list = reverse.get('external_subscriptions') or reverse.get('externalSubscriptions') or reverse.get('subs')
            if isinstance(ext_list, list) and ext_list:
                first = ext_list[0]
                if isinstance(first, str) and first.startswith('http'):
                    return first.strip()
                elif isinstance(first, dict) and first.get('url'):
                    return str(first.get('url')).strip()
    return None

class ThreeXUIClient:
    def __init__(
        self,
        host: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        auth_type: str = "credentials",
        timeout: float = 15.0,
        proxy: Optional[str] = None
    ):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.token = token
        self.auth_type = auth_type
        self.timeout = timeout

        import config
        proxy_url = proxy or config.PANEL_PROXY
        if proxy_url:
            self.client = httpx.AsyncClient(
                verify=False,
                timeout=httpx.Timeout(timeout),
                follow_redirects=True,
                proxy=proxy_url
            )
        else:
            self.client = httpx.AsyncClient(
                verify=False,
                timeout=httpx.Timeout(timeout),
                follow_redirects=True
            )
        self._is_logged_in = True if self.token else False

    @classmethod
    def from_storage(cls, panel_id: Optional[str] = None) -> Optional["ThreeXUIClient"]:
        creds = crypto_storage.load_credentials(panel_id)
        if not creds or not creds.get("host"):
            return None
        return cls(
            host=creds["host"],
            username=creds.get("username"),
            password=creds.get("password"),
            token=creds.get("token"),
            auth_type=creds.get("auth_type", "token" if creds.get("token") else "credentials")
        )

    async def close(self):
        await self.client.aclose()

    async def login(self) -> Tuple[bool, str]:
        """
        Authenticates with 3x-ui panel using Bearer Token or Username/Password.
        """
        if self.token:
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                resp = await self.client.get(f"{self.host}/panel/api/inbounds/list", headers=headers)
                if resp.status_code == 200:
                    res_data = resp.json()
                    if res_data.get("success", False):
                        self._is_logged_in = True
                        return True, "Успешная авторизация по Bearer Token"
                    else:
                        return False, res_data.get("msg", "Неверный Bearer Token")
                return False, f"Ошибка HTTP {resp.status_code}"
            except Exception as e:
                return False, f"Ошибка проверки Bearer Token: {str(e)}"

        if not self.username or not self.password:
            return False, "Не указаны данные авторизации"

        login_url = f"{self.host}/login"
        try:
            resp = await self.client.post(
                login_url,
                data={"username": self.username, "password": self.password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if resp.status_code == 200:
                res_data = resp.json()
                if res_data.get("success", False):
                    self._is_logged_in = True
                    if isinstance(res_data.get("obj"), str):
                        self.token = res_data.get("obj")
                    elif isinstance(res_data.get("obj"), dict) and "token" in res_data["obj"]:
                        self.token = res_data["obj"]["token"]
                    return True, "Успешная авторизация"
                else:
                    return False, res_data.get("msg", "Неверный логин или пароль")
            return False, f"Ошибка HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Ошибка подключения к панели: {str(e)}"

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Internal wrapper to send requests with Bearer Token or cookie session with 1 automatic retry.
        """
        if not self._is_logged_in:
            success, msg = await self.login()
            if not success:
                return {"success": False, "msg": f"Ошибка авторизации: {msg}"}

        url = f"{self.host}{endpoint}"
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        last_error = None
        for attempt in range(2):
            try:
                resp = await self.client.request(method, url, headers=headers, **kwargs)
                if resp.status_code in [401, 403]:
                    if not self.token:
                        success, msg = await self.login()
                        if not success:
                            return {"success": False, "msg": f"Сессия истекла: {msg}"}
                        resp = await self.client.request(method, url, headers=headers, **kwargs)
                    else:
                        return {"success": False, "msg": "Недействительный Bearer Token (401/403)"}

                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except Exception:
                        return {"success": True, "data": resp.text}
                return {"success": False, "msg": f"HTTP {resp.status_code}: {resp.text}"}
            except Exception as e:
                last_error = e
                if attempt == 0:
                    import asyncio
                    await asyncio.sleep(0.5)
                    continue

        err_detail = str(last_error) if last_error and str(last_error).strip() else (type(last_error).__name__ if last_error else "Неизвестная ошибка")
        return {"success": False, "msg": f"Сетевая ошибка ({type(last_error).__name__}): {err_detail}"}

    async def get_server_status(self) -> Dict[str, Any]:
        """
        Fetches CPU, RAM, Disk, Uptime and Xray status.
        Tries GET and POST methods across panel server status endpoints.
        """
        endpoints = [
            ("GET", "/panel/api/server/status"),
            ("POST", "/panel/api/server/status"),
            ("GET", "/panel/api/status"),
            ("POST", "/panel/api/status")
        ]
        res = {}
        for method, ep in endpoints:
            res = await self._request(method, ep)
            if res.get("success") and "obj" in res:
                return res
        return res

    async def restart_xray(self) -> Dict[str, Any]:
        """
        Restarts Xray service core. Tries modern /panel/api/server/restartXrayService first,
        and falls back to /panel/api/server/restartXray.
        """
        res = await self._request("POST", "/panel/api/server/restartXrayService")
        if res.get("success"):
            return res
        return await self._request("POST", "/panel/api/server/restartXray")

    async def get_inbounds(self) -> Dict[str, Any]:
        return await self._request("GET", "/panel/api/inbounds/list")

    async def get_online_clients(self) -> List[str]:
        """
        Fetches list of active online client emails from 3x-ui panel via inbounds clientStats lastOnline timestamp.
        """
        import time
        now_ms = time.time() * 1000
        online_emails = set()

        res = await self.get_inbounds()
        if res.get("success") and isinstance(res.get("obj"), list):
            for ib in res["obj"]:
                c_stats = ib.get("clientStats")
                if isinstance(c_stats, list):
                    for c in c_stats:
                        if isinstance(c, dict):
                            last_on = c.get("lastOnline", 0)
                            email = c.get("email")
                            if last_on and email:
                                diff_sec = (now_ms - last_on) / 1000
                                if 0 <= diff_sec <= 300:
                                    online_emails.add(str(email))

        return list(online_emails)

    async def get_clients_list(self) -> Dict[str, Any]:
        """
        Fetches the master client database list directly from 3x-ui panel (/panel/api/clients/list).
        Contains exact client groups, traffic, attached inbounds, and UUIDs.
        """
        return await self._request("GET", "/panel/api/clients/list")

    async def get_inbound(self, inbound_id: int) -> Optional[Dict[str, Any]]:
        res = await self.get_inbounds()
        if res.get("success") and "obj" in res:
            for item in res["obj"]:
                if item.get("id") == inbound_id:
                    return item
        return None

    async def add_client(
        self,
        inbound_id: int,
        email: str,
        uuid_str: str,
        total_gb: float = 0,
        expiry_days: int = 0,
        limit_ip: int = 0,
        flow: str = "xtls-rprx-vision",
        enable: bool = True
    ) -> Dict[str, Any]:
        """
        Adds a new client. Tries modern /panel/api/clients/add API first,
        and falls back to /panel/api/inbounds/addClient for legacy 3x-ui panels.
        """
        total_bytes = int(total_gb * 1024 * 1024 * 1024) if total_gb > 0 else 0
        expiry_time = 0
        if expiry_days > 0:
            import time
            expiry_time = int((time.time() + (expiry_days * 86400)) * 1000)

        # 1. Try Modern Sanaei API /panel/api/clients/add
        modern_payload = {
            "client": {
                "id": uuid_str,
                "email": email,
                "totalGB": total_bytes,
                "expiryTime": expiry_time,
                "limitIp": limit_ip,
                "enable": enable,
                "flow": flow,
                "tgId": 0
            },
            "inboundIds": [inbound_id] if inbound_id else []
        }
        res = await self._request("POST", "/panel/api/clients/add", json=modern_payload)
        if res.get("success"):
            return res

        # 2. Fallback to Legacy API /panel/api/inbounds/addClient
        inbound = await self.get_inbound(inbound_id)
        if not inbound:
            return res

        protocol = inbound.get("protocol", "").lower()
        client_data: Dict[str, Any] = {
            "id": uuid_str,
            "email": email,
            "limitIp": limit_ip,
            "totalGB": total_bytes,
            "expiryTime": expiry_time,
            "enable": enable,
            "tgId": "",
            "subId": ""
        }
        if protocol == "vless":
            client_data["flow"] = flow
        elif protocol == "trojan":
            client_data["password"] = uuid_str
        elif protocol == "shadowsocks":
            client_data["cipher"] = "2022-blake3-aes-128-gcm"
            client_data["secret"] = uuid_str

        legacy_payload = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client_data]})
        }
        return await self._request("POST", "/panel/api/inbounds/addClient", json=legacy_payload)

    async def get_client(self, email: str) -> Dict[str, Any]:
        """
        Gets full client details including externalLinks via modern /panel/api/clients/get/{email} endpoint.
        """
        import urllib.parse
        quoted_email = urllib.parse.quote(email)
        return await self._request("GET", f"/panel/api/clients/get/{quoted_email}")

    async def update_client(
        self,
        inbound_id: int,
        uuid_str: str,
        email: str,
        total_gb: float = 0,
        expiry_days: Optional[int] = None,
        expiry_time_ms: Optional[int] = None,
        limit_ip: int = 0,
        enable: bool = True,
        flow: str = "xtls-rprx-vision"
    ) -> Dict[str, Any]:
        """
        Updates an existing client. Tries /panel/api/clients/update/{email} first,
        and falls back to /panel/api/inbounds/updateClient/{uuid} for legacy panels.
        """
        total_bytes = int(total_gb * 1024 * 1024 * 1024) if total_gb > 0 else 0
        expiry_time = 0
        if expiry_time_ms is not None:
            expiry_time = expiry_time_ms
        elif expiry_days is not None and expiry_days > 0:
            import time
            expiry_time = int((time.time() + (expiry_days * 86400)) * 1000)

        # 1. Try Modern Sanaei API /panel/api/clients/update/{email}
        modern_payload = {
            "email": email,
            "id": uuid_str,
            "totalGB": total_bytes,
            "expiryTime": expiry_time,
            "limitIp": limit_ip,
            "enable": enable,
            "flow": flow,
            "tgId": 0
        }
        res = await self._request("POST", f"/panel/api/clients/update/{email}", json=modern_payload)
        if res.get("success"):
            return res

        # 2. Fallback to Legacy API /panel/api/inbounds/updateClient/{uuid}
        client_data: Dict[str, Any] = {
            "id": uuid_str,
            "email": email,
            "limitIp": limit_ip,
            "totalGB": total_bytes,
            "expiryTime": expiry_time,
            "enable": enable,
            "flow": flow,
            "tgId": "",
            "subId": ""
        }
        legacy_payload = {
            "id": inbound_id,
            "settings": json.dumps({"clients": [client_data]})
        }
        return await self._request("POST", f"/panel/api/inbounds/updateClient/{uuid_str}", json=legacy_payload)

    async def delete_client(self, inbound_id: int, uuid_str: str, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Deletes client via modern /panel/api/clients/del/{email} or legacy inbound endpoint.
        """
        if email:
            res = await self._request("POST", f"/panel/api/clients/del/{email}")
            if res.get("success"):
                return res
        return await self._request("POST", f"/panel/api/inbounds/{inbound_id}/delUser/{uuid_str}")

    async def reset_client_traffic(self, inbound_id: int, email: str) -> Dict[str, Any]:
        """
        Resets client traffic via modern /panel/api/clients/resetTraffic/{email} or legacy endpoint.
        """
        res = await self._request("POST", f"/panel/api/clients/resetTraffic/{email}")
        if res.get("success"):
            return res
        return await self._request("POST", f"/panel/api/inbounds/{inbound_id}/resetClientTraffic/{email}")

    async def clear_client_ips(self, email: str) -> Dict[str, Any]:
        """
        Clears client IP bindings.
        """
        res = await self._request("POST", f"/panel/api/clients/clearIps/{email}")
        if res.get("success"):
            return res
        return await self._request("POST", f"/panel/api/inbounds/clearClientIps/{email}")

    async def attach_client_to_inbounds(self, email: str, inbound_ids: List[int]) -> Dict[str, Any]:
        """
        Attaches client to given inbound IDs via modern /panel/api/clients/{email}/attach API.
        """
        payload = {"inboundIds": inbound_ids}
        return await self._request("POST", f"/panel/api/clients/{email}/attach", json=payload)

    async def detach_client_from_inbounds(self, email: str, inbound_ids: List[int]) -> Dict[str, Any]:
        """
        Detaches client from given inbound IDs via modern /panel/api/clients/{email}/detach API.
        """
        payload = {"inboundIds": inbound_ids}
        return await self._request("POST", f"/panel/api/clients/{email}/detach", json=payload)

    def generate_client_link(self, inbound: Dict[str, Any], client: Dict[str, Any], host_domain: str) -> str:
        """
        Generates connection URI (vless://, vmess://, trojan://) for a client.
        """
        protocol = inbound.get("protocol", "").lower()
        port = inbound.get("port")
        remark = inbound.get("remark", "3X-UI")
        email = client.get("email", "")
        uuid = client.get("id") or client.get("password") or ""

        parsed_url = urllib.parse.urlparse(self.host)
        server_ip = host_domain if host_domain else parsed_url.hostname

        stream_settings = ensure_dict(inbound.get("streamSettings"))
        net = stream_settings.get("network", "tcp")
        security = stream_settings.get("security", "none")

        if protocol == "vless":
            params = {"type": net, "security": security}
            if security == "reality":
                reality_settings = stream_settings.get("realitySettings", {})
                params["pbk"] = reality_settings.get("publicKey", "")
                params["fp"] = reality_settings.get("settings", {}).get("fingerprint", "chrome")
                server_names = reality_settings.get("serverNames", [])
                if server_names:
                    params["sni"] = server_names[0]
                short_ids = reality_settings.get("shortIds", [])
                if short_ids:
                    params["sid"] = short_ids[0]
                params["spx"] = "/"
                flow = client.get("flow", "xtls-rprx-vision")
                if flow:
                    params["flow"] = flow
            elif security == "tls":
                tls_settings = stream_settings.get("tlsSettings", {})
                if tls_settings.get("serverName"):
                    params["sni"] = tls_settings.get("serverName")

            if net == "ws":
                ws_settings = stream_settings.get("wsSettings", {})
                params["path"] = ws_settings.get("path", "/")
                params["host"] = ws_settings.get("headers", {}).get("Host", "")
            elif net == "grpc":
                grpc_settings = stream_settings.get("grpcSettings", {})
                params["serviceName"] = grpc_settings.get("serviceName", "")

            query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
            title = f"{remark}-{email}"
            return f"vless://{uuid}@{server_ip}:{port}?{query}#{urllib.parse.quote(title)}"

        elif protocol == "vmess":
            vmess_data = {
                "v": "2",
                "ps": f"{remark}-{email}",
                "add": server_ip,
                "port": str(port),
                "id": uuid,
                "aid": "0",
                "net": net,
                "type": "none",
                "host": "",
                "path": "",
                "tls": security if security != "none" else ""
            }
            b64 = base64.b64encode(json.dumps(vmess_data).encode()).decode()
            return f"vmess://{b64}"

        elif protocol == "trojan":
            params = {"type": net, "security": security}
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
            title = f"{remark}-{email}"
            return f"trojan://{uuid}@{server_ip}:{port}?{query}#{urllib.parse.quote(title)}"

        return f"Неподдерживаемый протокол {protocol}"

    def generate_subscription_link(self, client: Dict[str, Any], host_domain: str, sub_port: Optional[int] = None) -> str:
        """
        Generates 3x-ui Subscription URL for a client.
        Format: http(s)://domain:sub_port/sub/{subId}
        """
        parsed_url = urllib.parse.urlparse(self.host)
        scheme = parsed_url.scheme or "http"
        server_ip = host_domain if host_domain else parsed_url.hostname

        if sub_port:
            port_str = f":{sub_port}"
        elif parsed_url.port:
            port_str = f":{parsed_url.port}"
        else:
            port_str = ""

        sub_id = client.get("subId") or client.get("email") or client.get("id") or ""
        return f"{scheme}://{server_ip}{port_str}/sub/{sub_id}"
