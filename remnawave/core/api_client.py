import json
from typing import Dict, Any, List, Optional, Tuple
import httpx
from x_ui.core import crypto_storage
from x_ui.core.api_client import format_bytes, ensure_dict

class RemnawaveClient:
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
    def from_storage(cls, panel_id: Optional[str] = None) -> Optional["RemnawaveClient"]:
        creds = crypto_storage.load_credentials(panel_id)
        if not creds or not creds.get("host"):
            return None
        return cls(
            host=creds["host"],
            username=creds.get("username"),
            password=creds.get("password"),
            token=creds.get("token"),
            auth_type=creds.get("auth_type", "credentials")
        )

    async def close(self):
        await self.client.aclose()

    async def login(self) -> Tuple[bool, str]:
        """
        Authenticates with Remnawave panel using Username/Password or checks Token.
        """
        if self.token:
            # Verify if existing token is valid
            try:
                headers = {"Authorization": f"Bearer {self.token}"}
                resp = await self.client.get(f"{self.host}/api/users", headers=headers)
                if resp.status_code == 200:
                    self._is_logged_in = True
                    return True, "Успешная авторизация по токену"
                # If token is invalid, attempt login with username/password if available
                if not (self.username and self.password):
                    return False, f"Токен недействителен (HTTP {resp.status_code})"
            except Exception as e:
                if not (self.username and self.password):
                    return False, f"Ошибка проверки токена: {str(e)}"

        if not self.username or not self.password:
            return False, "Не указаны данные авторизации"

        login_url = f"{self.host}/api/auth/login"
        try:
            resp = await self.client.post(
                login_url,
                json={"username": self.username, "password": self.password},
                headers={"Content-Type": "application/json"}
            )
            if resp.status_code in [200, 201]:
                res_data = resp.json()
                token = res_data.get("response", {}).get("accessToken")
                if token:
                    self.token = token
                    self._is_logged_in = True
                    return True, "Успешная авторизация"
                else:
                    return False, "В ответе отсутствует accessToken"
            else:
                try:
                    err_msg = resp.json().get("message", f"HTTP {resp.status_code}")
                except Exception:
                    err_msg = f"HTTP {resp.status_code}"
                return False, err_msg
        except Exception as e:
            return False, f"Ошибка подключения к панели: {str(e)}"

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Sends requests to Remnawave with JWT Bearer Token.
        """
        if not self._is_logged_in:
            success, msg = await self.login()
            if not success:
                return {"success": False, "msg": f"Ошибка авторизации: {msg}"}

        url = f"{self.host}{endpoint}"
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        headers["Content-Type"] = "application/json"

        for attempt in range(2):
            try:
                resp = await self.client.request(method, url, headers=headers, **kwargs)
                if resp.status_code in [401, 403]:
                    # Token might have expired, try to log in again if credentials are available
                    if self.username and self.password:
                        success, msg = await self.login()
                        if not success:
                            return {"success": False, "msg": f"Сессия истекла: {msg}"}
                        # Update headers with new token
                        headers["Authorization"] = f"Bearer {self.token}"
                        resp = await self.client.request(method, url, headers=headers, **kwargs)
                    else:
                        return {"success": False, "msg": "Неавторизован (401/403)"}

                if resp.status_code in [200, 201, 204]:
                    if resp.status_code == 204:
                        return {"success": True, "response": {}}
                    try:
                        return {"success": True, "response": resp.json().get("response", {})}
                    except Exception:
                        return {"success": True, "response": {}}
                else:
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("message", f"HTTP {resp.status_code}")
                    except Exception:
                        err_msg = f"HTTP {resp.status_code}"
                    return {"success": False, "msg": err_msg}
            except Exception as e:
                if attempt == 1:
                    return {"success": False, "msg": f"Ошибка запроса: {str(e)}"}
        return {"success": False, "msg": "Неизвестная ошибка запроса"}

    # ================== NODES ==================
    async def get_nodes(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/nodes")

    async def create_node(self, name: str, address: str, port: int, config_profile_uuid: str, active_inbounds: List[str] = None) -> Dict[str, Any]:
        if active_inbounds is None:
            active_inbounds = []
        payload = {
            "name": name,
            "address": address,
            "port": int(port),
            "configProfile": {
                "activeConfigProfileUuid": config_profile_uuid,
                "activeInbounds": active_inbounds
            }
        }
        return await self._request("POST", "/api/nodes", json=payload)

    async def update_node(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PATCH", f"/api/nodes/{uuid}", json=data)

    async def delete_node(self, uuid: str) -> Dict[str, Any]:
        return await self._request("DELETE", f"/api/nodes/{uuid}")

    async def enable_node(self, uuid: str) -> Dict[str, Any]:
        return await self._request("POST", f"/api/nodes/{uuid}/actions/enable")

    async def disable_node(self, uuid: str) -> Dict[str, Any]:
        return await self._request("POST", f"/api/nodes/{uuid}/actions/disable")

    async def restart_node(self, uuid: str) -> Dict[str, Any]:
        return await self._request("POST", f"/api/nodes/{uuid}/actions/restart")

    async def reset_node_traffic(self, uuid: str) -> Dict[str, Any]:
        return await self._request("POST", f"/api/nodes/{uuid}/actions/reset-traffic")

    # ================== CONFIG PROFILES ==================
    async def get_profiles(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/config-profiles")

    async def create_profile(self, name: str) -> Dict[str, Any]:
        return await self._request("POST", "/api/config-profiles", json={"name": name})

    async def update_profile(self, uuid: str, name: str) -> Dict[str, Any]:
        return await self._request("PATCH", f"/api/config-profiles/{uuid}", json={"name": name})

    async def delete_profile(self, uuid: str) -> Dict[str, Any]:
        return await self._request("DELETE", f"/api/config-profiles/{uuid}")

    async def get_profile_inbounds(self, uuid: str) -> Dict[str, Any]:
        return await self._request("GET", f"/api/config-profiles/{uuid}/inbounds")

    # ================== HOSTS ==================
    async def get_hosts(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/hosts")

    async def create_host(self, name: str, ip_or_domain: str, port: int, profile_uuid: str, inbound_uuid: str) -> Dict[str, Any]:
        payload = {
            "inbound": {
                "configProfileUuid": profile_uuid,
                "configProfileInboundUuid": inbound_uuid
            },
            "remark": name,
            "address": ip_or_domain,
            "port": int(port)
        }
        return await self._request("POST", "/api/hosts", json=payload)

    async def update_host(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PATCH", f"/api/hosts/{uuid}", json=data)

    async def delete_host(self, uuid: str) -> Dict[str, Any]:
        return await self._request("DELETE", f"/api/hosts/{uuid}")

    # ================== USERS ==================
    async def get_users(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/users")

    async def create_user(self, username: str, expire_at: str, traffic_limit_bytes: float = 0, hwid_limit: int = 0) -> Dict[str, Any]:
        payload = {
            "username": username,
            "expireAt": expire_at,
            "trafficLimitBytes": float(traffic_limit_bytes),
            "status": "ACTIVE"
        }
        if hwid_limit > 0:
            payload["hwidDeviceLimit"] = int(hwid_limit)
        return await self._request("POST", "/api/users", json=payload)

    async def update_user(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(data)
        payload["id"] = int(user_id)
        return await self._request("PATCH", "/api/users", json=payload)

    async def delete_user(self, user_id: int) -> Dict[str, Any]:
        return await self._request("DELETE", f"/api/users/{user_id}")

    async def enable_user(self, user_id: int) -> Dict[str, Any]:
        return await self._request("POST", f"/api/users/{user_id}/actions/enable")

    async def disable_user(self, user_id: int) -> Dict[str, Any]:
        return await self._request("POST", f"/api/users/{user_id}/actions/disable")

    async def reset_user_traffic(self, user_id: int) -> Dict[str, Any]:
        return await self._request("POST", f"/api/users/{user_id}/actions/reset-traffic")

    async def extend_user(self, user_id: int, days: int) -> Dict[str, Any]:
        return await self._request("POST", f"/api/users/{user_id}/actions/extend", json={"days": int(days)})

    async def revoke_user(self, user_id: int) -> Dict[str, Any]:
        return await self._request("POST", f"/api/users/{user_id}/actions/revoke")

    # ================== PANELS / SUBSCRIPTION PAGE CONFIGS ==================
    async def get_subpage_configs(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/subscription-page-configs")

    async def create_subpage_config(self, name: str, html_content: str = "") -> Dict[str, Any]:
        payload = {
            "name": name,
            "html": html_content
        }
        return await self._request("POST", "/api/subscription-page-configs", json=payload)

    async def update_subpage_config(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PATCH", f"/api/subscription-page-configs/{uuid}", json=data)

    async def delete_subpage_config(self, uuid: str) -> Dict[str, Any]:
        return await self._request("DELETE", f"/api/subscription-page-configs/{uuid}")

    async def clone_subpage_config(self, uuid: str) -> Dict[str, Any]:
        return await self._request("POST", f"/api/subscription-page-configs/{uuid}/clone")

    # ================== SYSTEM METRICS ==================
    async def get_system_stats(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/system/stats")

    async def get_system_bandwidth(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/system/stats/bandwidth")

    async def get_system_health(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/system/health")
