"""
Módulo de Comunicación ADB
=======================
Gestiona la conexión con dispositivos Android via ADB.
"""

import subprocess
import re
import os
import shutil
import platform
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum


# ============== ADB FINDER ==============
def find_adb_executable() -> str:
    """Busca el ejecutable de ADB en ubicaciones conocidas"""
    sistema = platform.system()
    adb_cmd = "adb.exe" if sistema == "Windows" else "adb"
    
    # 1. Buscar en PATH del sistema
    path_env = os.environ.get("PATH", "")
    path_sep = ";" if sistema == "Windows" else ":"
    
    for path in path_env.split(path_sep):
        path = path.strip()
        if not path:
            continue
        try:
            full_path = os.path.join(path, adb_cmd)
            if os.path.isfile(full_path):
                return full_path
        except:
            pass
    
    # 2. Buscar en ubicaciones comunes
    if sistema == "Windows":
        common_paths = [
            os.path.expanduser(r"~\Documents\platform-tools\adb.exe"),
            os.path.expanduser(r"~\Downloads\platform-tools\adb.exe"),
            os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
            r"C:\Android\platform-tools\adb.exe",
            r"C:\Program Files\Android\platform-tools\adb.exe",
        ]
        for path in common_paths:
            if os.path.isfile(path):
                return path
    else:
        common_paths = [
            "/opt/homebrew/bin/adb",
            "/usr/local/bin/adb",
            os.path.expanduser("~/Android/sdk/platform-tools/adb"),
        ]
        for path in common_paths:
            if os.path.isfile(path):
                return path
    
    # 3. Último fallback
    adb_path = shutil.which(adb_cmd)
    if adb_path:
        return adb_path
    return adb_cmd


ADB_CMD = find_adb_executable()


# ============== MODELOS ==============
class DeviceStatus(Enum):
    CONNECTED = "device"
    UNAUTHORIZED = "unauthorized"
    OFFLINE = "offline"
    NO_DEVICE = "no device"


@dataclass
class Device:
    serial: str
    status: DeviceStatus
    product: str = ""
    model: str = ""
    device: str = ""


@dataclass
class ForegroundActivity:
    package_id: str
    activity_class: str
    full_name: str
    timestamp: float = 0.0


# ============== HELPERS ==============
def _run(args: list, timeout: int = 10, check: bool = False) -> subprocess.CompletedProcess:
    """Ejecuta comando ADB con stdout/stderr capturados."""
    kwargs = {
        "args": [ADB_CMD] + args,
        "capture_output": True,
        "text": True,
        "timeout": timeout,
    }
    # Solo agregar en Windows para evitar ventanas
    if platform.system() == "Windows":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    return subprocess.run(**kwargs)


# ============== CAPA 1: CONEXIÓN ==============
def get_devices() -> List[Device]:
    """Lista dispositivos conectados."""
    try:
        result = _run(["devices"])
        if result.returncode != 0:
            return []
        
        devices = []
        lines = result.stdout.strip().split("\n")[1:]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) < 2:
                continue
            
            serial = parts[0]
            try:
                status = DeviceStatus(parts[1])
            except ValueError:
                status = DeviceStatus.OFFLINE
            
            devices.append(Device(serial=serial, status=status))
        
        return devices
        
    except Exception:
        return []


def get_connected_device() -> Optional[Device]:
    """Obtiene el primer dispositivo conectado."""
    devices = get_devices()
    for device in devices:
        if device.status == DeviceStatus.CONNECTED:
            return device
    return None


def is_adb_installed() -> bool:
    """Checkea si ADB está disponible."""
    try:
        _run(["version"], timeout=5)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def enable_wireless_debugging(device_serial: str, port: int = 5555) -> Tuple[bool, str]:
    """Habilita debug wireless."""
    try:
        # Reiniciar en modo network
        result = _run(["-s", device_serial, "tcpip", str(port)], timeout=15)
        if result.returncode != 0:
            return False, f"Error: {result.stderr}"
        
        # Conectar
        if ":" in device_serial:
            ip_port = device_serial
        else:
            ip_result = _run(["-s", device_serial, "shell", "ip", "addr", "show", "wlan0"], timeout=10)
            match = re.search(r'inet (\d+\.\d+\.\d+.\d+)', ip_result.stdout)
            if match:
                ip = match.group(1)
                ip_port = f"{ip}:{port}"
            else:
                return True, f"TCPIP enabled on port {port}"
        
        conn_result = _run(["connect", ip_port], timeout=10)
        if "connected" in conn_result.stdout.lower() or "already connected" in conn_result.stdout.lower():
            return True, f"Conectado wireless: {ip_port}"
        else:
            return True, f"TCPIP enabled"
    
    except Exception as e:
        return False, f"Error: {e}"


def disconnect_wireless(device_ip: str) -> Tuple[bool, str]:
    """Desconecta wireless."""
    try:
        result = _run(["disconnect", device_ip])
        if result.returncode == 0:
            return True, f"Desconectado: {device_ip}"
        else:
            return False, result.stderr
    except Exception as e:
        return False, f"Error: {e}"


def scan_wireless_devices() -> List[str]:
    """Escanea devices wireless."""
    try:
        result = _run(["devices"])
        devices = []
        for line in result.stdout.split("\n"):
            if ":5555" in line and "device" in line.lower():
                serial = line.split()[0]
                devices.append(serial)
        return devices
    except Exception:
        return []


def pair_wireless(ip_port: str, pairing_code: str) -> Tuple[bool, str]:
    """Vincula via pairing code."""
    try:
        result = _run(["pair", ip_port, pairing_code], timeout=30)
        if result.returncode == 0 and "successfully" in result.stdout.lower():
            return True, f"Pairing exitoso: {ip_port}"
        else:
            return False, result.stderr or result.stdout
    except Exception as e:
        return False, f"Error: {e}"


# ============== CAPA 2: QUERIES ==============
def get_foreground_activity(device_serial: str) -> Optional[ForegroundActivity]:
    """Obtiene la actividad en foreground."""
    try:
        result = _run(["-s", device_serial, "shell", "dumpsys", "window"], timeout=5)
        if result.returncode != 0:
            return None
        
        for line in result.stdout.split("\n"):
            if "mCurrentFocus=" in line:
                match = re.search(r'u0\s+([a-zA-Z0-9_.]+/[a-zA-Z0-9_.]+)', line)
                if match:
                    full_name = match.group(1)
                    if "/" in full_name:
                        package_id, activity_class = full_name.split("/", 1)
                    else:
                        package_id = full_name
                        activity_class = ""
                    
                    return ForegroundActivity(
                        package_id=package_id,
                        activity_class=activity_class,
                        full_name=full_name
                    )
        return None
    except Exception:
        return None


def get_package_info(device_serial: str, package_id: str) -> dict:
    """Obtiene info de un paquete."""
    try:
        result = _run(["-s", device_serial, "shell", "dumpsys", "package", package_id], timeout=5)
        if result.returncode != 0:
            return {}
        
        info = {}
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if "packageName=" in line:
                key, _, value = line.partition("=")
                info[key] = value
            elif "versionName=" in line:
                key, _, value = line.partition("=")
                info[key] = value
            elif "firstInstallTime=" in line:
                key, _, value = line.partition("=")
                info[key] = value
        return info
    except Exception:
        return {}


def is_package_installed(device_serial: str, package_id: str) -> bool:
    """Checkea si un paquete está instalado."""
    try:
        result = _run(["-s", device_serial, "shell", "pm", "list", "packages", package_id], timeout=5)
        return package_id in result.stdout
    except Exception:
        return False


# ============== CAPA 3: ACCIÓN ==============
def force_stop_package(device_serial: str, package_id: str) -> Tuple[bool, str]:
    """Fuerza el cierre de una app."""
    try:
        result = _run(["-s", device_serial, "shell", "am", "force-stop", package_id], timeout=10)
        success = result.returncode == 0
        message = result.stderr if result.stderr else result.stdout
        return success, message
    except Exception as e:
        return False, str(e)


def uninstall_package(device_serial: str, package_id: str, keep_data: bool = True) -> Tuple[bool, str]:
    """Desinstala una app."""
    cmd = ["-s", device_serial, "shell", "pm", "uninstall"]
    if keep_data:
        cmd.append("-k")
    cmd.extend(["--user", "0", package_id])
    
    try:
        result = _run(cmd, timeout=30)
        output = result.stdout.strip()
        
        if "Success" in output:
            return True, "Package uninstalled"
        elif "Failure" in output:
            return False, f"Uninstall failed: {output}"
        else:
            return False, f"Unknown response: {output}"
    except Exception as e:
        return False, str(e)


# ============== EXCEPCIONES ==============
class ADBError(Exception):
    pass


class ADBNotFoundError(ADBError):
    pass