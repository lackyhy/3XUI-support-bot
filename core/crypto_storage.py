import json
import uuid
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
import config

def _get_fernet() -> Fernet:
    if not config.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY is not set in config!")
    return Fernet(config.ENCRYPTION_KEY.encode('utf-8'))

def load_raw_storage() -> Dict[str, Any]:
    """
    Loads raw encrypted storage dict with auto-migration to multi-panel format.
    """
    if not config.CREDENTIALS_FILE.exists():
        return {"active_panel_id": None, "panels": {}}
    try:
        fernet = _get_fernet()
        with open(config.CREDENTIALS_FILE, 'rb') as f:
            encrypted_data = f.read()
        data = json.loads(fernet.decrypt(encrypted_data).decode('utf-8'))

        # Auto-migrate single panel legacy format
        if "host" in data and "panels" not in data:
            panel_id = "panel_1"
            panel_obj = {
                "id": panel_id,
                "name": "Основной сервер",
                "host": data.get("host"),
                "auth_type": data.get("auth_type", "token"),
                "token": data.get("token"),
                "username": data.get("username"),
                "password": data.get("password")
            }
            migrated = {
                "active_panel_id": panel_id,
                "panels": {panel_id: panel_obj}
            }
            save_raw_storage(migrated)
            return migrated

        return data
    except Exception as e:
        print(f"Error decrypting credentials: {e}")
        return {"active_panel_id": None, "panels": {}}

def save_raw_storage(data: Dict[str, Any]) -> None:
    """
    Encrypts dictionary data and saves it to CREDENTIALS_FILE.
    """
    fernet = _get_fernet()
    json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
    encrypted_data = fernet.encrypt(json_bytes)
    
    config.CREDENTIALS_FILE.parent.mkdir(exist_ok=True)
    with open(config.CREDENTIALS_FILE, 'wb') as f:
        f.write(encrypted_data)

def get_panels() -> List[Dict[str, Any]]:
    storage = load_raw_storage()
    return list(storage.get("panels", {}).values())

def get_active_panel() -> Optional[Dict[str, Any]]:
    storage = load_raw_storage()
    active_id = storage.get("active_panel_id")
    panels = storage.get("panels", {})
    if active_id and active_id in panels:
        return panels[active_id]
    if panels:
        first_key = next(iter(panels))
        return panels[first_key]
    return None

def load_credentials(panel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if panel_id:
        storage = load_raw_storage()
        return storage.get("panels", {}).get(panel_id)
    return get_active_panel()

def add_or_update_panel(
    name: str,
    host: str,
    auth_type: str,
    token: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    panel_id: Optional[str] = None
) -> str:
    storage = load_raw_storage()
    if not panel_id:
        panel_id = f"panel_{uuid.uuid4().hex[:8]}"

    panel_obj = {
        "id": panel_id,
        "name": name if name else f"Сервер {len(storage.get('panels', {})) + 1}",
        "host": host,
        "auth_type": auth_type,
        "token": token,
        "username": username,
        "password": password
    }

    if "panels" not in storage:
        storage["panels"] = {}

    storage["panels"][panel_id] = panel_obj
    if not storage.get("active_panel_id"):
        storage["active_panel_id"] = panel_id

    save_raw_storage(storage)
    return panel_id

def set_active_panel(panel_id: str) -> bool:
    storage = load_raw_storage()
    if panel_id in storage.get("panels", {}):
        storage["active_panel_id"] = panel_id
        save_raw_storage(storage)
        return True
    return False

def delete_panel(panel_id: str) -> bool:
    storage = load_raw_storage()
    panels = storage.get("panels", {})
    if panel_id in panels:
        del panels[panel_id]
        if storage.get("active_panel_id") == panel_id:
            storage["active_panel_id"] = next(iter(panels)) if panels else None
        save_raw_storage(storage)
        return True
    return False

def rename_panel(panel_id: str, new_name: str) -> bool:
    storage = load_raw_storage()
    panels = storage.get("panels", {})
    if panel_id in panels:
        panels[panel_id]["name"] = new_name
        save_raw_storage(storage)
        return True
    return False

def toggle_panel_enabled(panel_id: str) -> Optional[bool]:
    storage = load_raw_storage()
    panels = storage.get("panels", {})
    if panel_id in panels:
        current = panels[panel_id].get("enabled", True)
        new_state = not current
        panels[panel_id]["enabled"] = new_state
        save_raw_storage(storage)
        return new_state
    return None

def update_sub_port(panel_id: str, sub_port: int) -> bool:
    storage = load_raw_storage()
    panels = storage.get("panels", {})
    if panel_id in panels:
        panels[panel_id]["sub_port"] = sub_port
        save_raw_storage(storage)
        return True
    return False

def derive_default_panel_name(host_url: str) -> str:
    import urllib.parse, socket
    try:
        parsed = urllib.parse.urlparse(host_url)
        raw_host = parsed.hostname or host_url
        try:
            name, _, _ = socket.gethostbyaddr(raw_host)
            if name:
                return name
        except Exception:
            pass
        return raw_host
    except Exception:
        return "Сервер 3x-ui"

def has_credentials() -> bool:
    return get_active_panel() is not None

def delete_credentials() -> bool:
    if config.CREDENTIALS_FILE.exists():
        config.CREDENTIALS_FILE.unlink()
        return True
    return False
