import aiohttp
import asyncio
from typing import Dict, Tuple

_GEO_CACHE: Dict[str, Tuple[str, str]] = {}  # ip -> (flag, country_name)

def country_code_to_flag(country_code: str) -> str:
    if not country_code or len(country_code) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c.upper())) for c in country_code)

async def get_ip_geo(ip: str) -> Tuple[str, str]:
    """Returns (flag_emoji, country_name). Uses in-memory caching."""
    if not ip or ip == "N/A" or ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168."):
        return "🌐", ""

    if ip in _GEO_CACHE:
        return _GEO_CACHE[ip]

    try:
        url = f"http://ip-api.com/json/{ip}?fields=countryCode,country"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=3.0) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    cc = data.get("countryCode", "")
                    country = data.get("country", "")
                    flag = country_code_to_flag(cc)
                    _GEO_CACHE[ip] = (flag, country)
                    return flag, country
    except Exception:
        pass

    return "🌐", ""

def format_ipv4_with_2ip(ipv4: str, flag: str = "🌐") -> str:
    """Formats IPv4 with country flag and 2ip.io markdown hyperlink."""
    if not ipv4 or ipv4 == "N/A":
        return "`N/A`"
    
    flag_str = f"{flag} " if flag and flag != "🌐" else ""
    return f"{flag_str}`{ipv4}` ([2ip.io](https://2ip.io/ip/{ipv4}))"
