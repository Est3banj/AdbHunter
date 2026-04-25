"""
Settings y Configuración
=========================
Gestiona la whitelist y settings del usuario.
"""

import json
import os
from pathlib import Path
from typing import Set, Optional
from dataclasses import dataclass, asdict


# ============== CONSTANTS ==============
# Whitelist hardcodeada - Apps del sistema que NUNCA se pueden borrar
# Esta lista se carga siempre, más allá del config.json
SYSTEM_WHITELIST = {
    # Sistema core Android
    "com.android.systemui",
    "com.android.launcher",
    "com.android.launcher2",
    "com.android.launcher3",
    "com.android.launcher4",
    "com.android.settings",
    "com.android.settings",
    "com.android.quicksearchbox",
    "com.android.server.telecom",
    "com.android.dialer",
    "com.android.phone",
    "com.android.contacts",
    "com.android.mms",
    "com.android短信",
    
    # Google Services
    "com.google.android.gms",
    "com.google.android.gsf",
    "com.google.android.gms.location",
    "com.google.android.play",
    "com.android.vending",  # Play Store
    "com.google.android.sync", 
    "com.google.android.gms.persistent",
    
    # Chrome
    "com.android.chrome",
    "com.google.android.apps.chrome",
    
    # Samsung (común en devices Samsung)
    "com.samsung.android.app.launcher",
    "com.samsung.android.sm.devicesecurity",
    "com.samsung.android.lool",
    "com.sec.android.app.launcher",
    "com.sec.android.dialer",
    
    # Xiaomi (común en devices Xiaomi)
    "com.miui.home",
    "com.miui.securitycenter",
    "com.miui.systemui",
    
    # Huawei
    "com.huawei.systemmanager",
    "com.huawei.systemmanager.launch",
    "com.huawei.android.launcher",
    
    # Generic launchers comunes
    "com.actionlauncher",
    "com.buzzfeed",
    "org.adw.launcher",
    "com.gaugo.launcher",
    "com.teslacoilsw.launcher",
}

# Usuarios comunes - Apps que el usuario probablemente quiere conservar
# Estas se cargan desde config.json
DEFAULT_USER_WHITELIST = {
    "com.whatsapp",
    "org.telegram.messenger",
    "com.instagram.android",
    "com.facebook.katana",
    "com.twitter.android",
    "com.facebook.lite",
    "com.zhiliaoapp.musically",
    "com.snapchat.android",
    "com.linkedin.android",
    "com.google.android.apps.docs",
    "com.google.android.apps.photos",
    "com.google.android.apps.maps",
    "com.netflix.mediaclient",
    "com.spotify.music",
    "com.amazon.mShop.android.shopping",
}

# Ratelimit - Máximo de desinstalaciones en 1 hora
MAX_UNINSTALLS_PER_HOUR = 3


# ============== CONFIG ==============
@dataclass
class AppConfig:
    """Configuración del usuario"""
    poll_interval: float = 0.5  # segundos entre polls
    show_system_apps: bool = False  # mostrar apps de sistema en log
    user_whitelist: list = None
    
    def __post_init__(self):
        if self.user_whitelist is None:
            self.user_whitelist = list(DEFAULT_USER_WHITELIST)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        if not data:
            return cls()
        # Filtrar solo campos conocidos
        known_fields = {"poll_interval", "show_system_apps", "user_whitelist"}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


# ============== PERSISTENCIA ==============
def get_config_path() -> Path:
    """Obtiene la ruta al config.json"""
    # ~/AdbHunter/config.json
    home = Path.home()
    config_dir = home / ".adbhunter"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.json"


def load_config() -> AppConfig:
    """Carga configuración desde archivo"""
    config_path = get_config_path()
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
            return AppConfig.from_dict(data)
        except Exception:
            pass
    
    return AppConfig()


def save_config(config: AppConfig):
    """Guarda configuración a archivo"""
    config_path = get_config_path()
    
    with open(config_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)


# ============== WHITELIST ==============
def get_full_whitelist() -> Set[str]:
    """
    Obtiene la whitelist completa (sistema + usuario).
    La whitelist que se usa realmente para filtrar.
    """
    config = load_config()
    
    whitelist = set(SYSTEM_WHITELIST)
    whitelist.update(config.user_whitelist)
    
    return whitelist


def is_whitelisted(package_id: str) -> bool:
    """Checkea si un package está en whitelist"""
    return package_id in get_full_whitelist()


def add_to_user_whitelist(package_id: str):
    """Agrega un package a la whitelist del usuario"""
    config = load_config()
    
    if package_id not in config.user_whitelist:
        config.user_whitelist.append(package_id)
        save_config(config)


def remove_from_user_whitelist(package_id: str):
    """Remueve un package de la whitelist del usuario"""
    config = load_config()
    
    if package_id in config.user_whitelist:
        config.user_whitelist.remove(package_id)
        save_config(config)


# ============== RATELIMIT ==============
@dataclass
class UninstallLog:
    """Registro de desinstalación"""
    package_id: str
    timestamp: str
    action: str
    user_confirmed: bool


def get_uninstall_log_path() -> Path:
    """Ruta al log de desinstalaciones"""
    home = Path.home()
    return home / ".adbhunter" / "uninstalls.json"


def log_uninstall(package_id: str, action: str = "uninstall", user_confirmed: bool = True):
    """Loggea una desinstalación para ratelimit"""
    log_path = get_uninstall_log_path()
    
    # Cargar logs existentes
    logs = []
    if log_path.exists():
        try:
            with open(log_path, "r") as f:
                logs = json.load(f)
        except Exception:
            pass
    
    # Agregar nuevo log
    from datetime import datetime
    logs.append({
        "package_id": package_id,
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "user_confirmed": user_confirmed
    })
    
    # Guardar (max 100 entries)
    with open(log_path, "w") as f:
        json.dump(logs[-100:], f, indent=2)


def get_recent_uninstall_count() -> int:
    """Cuenta desinstalaciones en la última hora"""
    from datetime import datetime, timedelta
    
    log_path = get_uninstall_log_path()
    
    if not log_path.exists():
        return 0
    
    try:
        with open(log_path, "r") as f:
            logs = json.load(f)
    except Exception:
        return 0
    
    # Filtrar última hora
    one_hour_ago = datetime.now() - timedelta(hours=1)
    
    count = 0
    for log in logs:
        try:
            ts = datetime.fromisoformat(log["timestamp"])
            if ts >= one_hour_ago:
                count += 1
        except Exception:
            continue
    
    return count


def can_uninstall() -> bool:
    """Checkea si se puede desinstalar (ratelimit)"""
    return get_recent_uninstall_count() < MAX_UNINSTALLS_PER_HOUR