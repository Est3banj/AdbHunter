"""
Módulo de Comunicación ADB
=========================
Gestiona la conexión con dispositivos Android via ADB.
"""

import subprocess
import re
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum


# ============== MODELOS ==============
class DeviceStatus(Enum):
    """Estados posibles de un dispositivo conectado"""
    CONNECTED = "device"
    UNAUTHORIZED = "unauthorized"
    OFFLINE = "offline"
    NO_DEVICE = "no device"


@dataclass
class Device:
    """Representa un dispositivo Android conectado"""
    serial: str
    status: DeviceStatus
    product: str = ""
    model: str = ""
    device: str = ""
    

@dataclass
class ForegroundActivity:
    """Información de la actividad en foreground"""
    package_id: str
    activity_class: str
    full_name: str  # "com.example/.MainActivity"
    timestamp: float = 0.0


# ============== CAPA 1: CONEXIÓN ==============
def get_devices() -> List[Device]:
    """
    Lista dispositivos conectados via 'adb devices'.
    RETURNA: Lista de Device objects
    """
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return []
        
        devices = []
        lines = result.stdout.strip().split("\n")[1:]  # Skip header "List of devices"
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) < 2:
                continue
            
            serial = parts[0]
            status_str = parts[1]
            
            # Parsear status
            try:
                status = DeviceStatus(status_str)
            except ValueError:
                status = DeviceStatus.OFFLINE
            
            devices.append(Device(serial=serial, status=status))
        
        return devices
        
    except FileNotFoundError:
        raise ADBNotFoundError("ADB not found in PATH. Install ADB Platform Tools.")
    except subprocess.TimeoutExpired:
        raise ADBError("ADB command timed out")
    except Exception as e:
        raise ADBError(f"Failed to get devices: {e}")


def get_connected_device() -> Optional[Device]:
    """
    Obtiene el primer dispositivo conectado (status='device').
    RETURNA: Device object o None
    """
    devices = get_devices()
    
    for device in devices:
        if device.status == DeviceStatus.CONNECTED:
            return device
    
    return None


def is_adb_installed() -> bool:
    """Checkea si ADB está disponible en el sistema"""
    try:
        subprocess.run(
            ["adb", "version"],
            capture_output=True,
            timeout=5
        )
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def enable_wireless_debugging(device_serial: str, port: int = 5555) -> Tuple[bool, str]:
    """
    Habilita debug wireless en el dispositivo.
    
    Args:
        device_serial: Serial del device (ej: "R58M..." o "192.168.1.100:5555")
        port: Puerto TCP a usar (default 5555)
    
    Returns:
        (success: bool, message: str)
    """
    try:
        # 1. Reiniciar ADB en modo network
        result = subprocess.run(
            ["adb", "-s", device_serial, "tcpip", str(port)],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode != 0:
            return False, f"Error: {result.stderr}"
        
        # 2. Conectar al IP del device
        # Extraer IP del serial o usar input directo
        if ":" in device_serial:
            # Ya tiene puerto, usar ese IP
            ip_port = device_serial
        else:
            # Obtener IP del device
            ip_result = subprocess.run(
                ["adb", "-s", device_serial, "shell", "ip", "addr", "show", "wlan0"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse IP from output
            match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', ip_result.stdout)
            if match:
                ip = match.group(1)
                ip_port = f"{ip}:{port}"
            else:
                return True, f"TCPIP enabled on port {port}. Connect manually: adb connect <IP>:{port}"
        
        # 3. Intentar conectar
        conn_result = subprocess.run(
            ["adb", "connect", ip_port],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "connected" in conn_result.stdout.lower() or "already connected" in conn_result.stdout.lower():
            return True, f"Conectado wireless: {ip_port}"
        else:
            return True, f"TCPIP enabled. Ejecuta: adb connect <IP>:{port}"
    
    except FileNotFoundError:
        return False, "ADB not found"
    except Exception as e:
        return False, f"Error: {e}"


def disconnect_wireless(device_ip: str) -> Tuple[bool, str]:
    """
    Desconecta una conexión wireless.
    
    Args:
        device_ip: IP del device (ej: "192.168.1.100:5555")
    
    Returns:
        (success: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["adb", "disconnect", device_ip],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return True, f"Desconectado: {device_ip}"
        else:
            return False, result.stderr
    
    except Exception as e:
        return False, f"Error: {e}"


def scan_wireless_devices() -> List[str]:
    """
    Escanea la red local buscando devices Android con wireless debugging.
    
    Returns:
        Lista de serials/IPs de devices encontrados
    """
    try:
        # Primero ver si hay connections wireless existentes
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Buscar devices que terminen en :5555 (wireless)
        for line in result.stdout.split("\n"):
            if ":5555" in line and "device" in line.lower():
                serial = line.split()[0]
                devices.append(serial)
        
        return devices
    
    except Exception:
        return []


def pair_wireless(ip_port: str, pairing_code: str) -> Tuple[bool, str]:
    """
    Vincula un dispositivo via Wireless Debugging pairing code.
    
    Args:
        ip_port: IP:puerto del device (ej: "192.168.1.100:45123")
        pairing_code: Código de pairing (ej: "123456")
    
    Returns:
        (success: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["adb", "pair", ip_port, pairing_code],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and "successfully" in result.stdout.lower():
            return True, f"Pairing exitoso: {ip_port}"
        else:
            return False, result.stderr or result.stdout
    
    except Exception as e:
        return False, f"Error: {e}"


# ============== CAPA 2: QUERIES ==============
def get_foreground_activity(device_serial: str) -> Optional[ForegroundActivity]:
    """
    Obtiene la actividad actual en foreground.
    
    Usa 'dumpsys window windows' que es más reliable que dumpsys activity.
    
    RETURNA: ForegroundActivity o None si falla
    """
    cmd = [
        "adb", "-s", device_serial,
        "shell", "dumpsys", "window"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return None
        
        # Buscar mCurrentFocus - formato nuevo:
        # mCurrentFocus=Window{... u0 com.example.app/.MainActivity}
        for line in result.stdout.split("\n"):
            if "mCurrentFocus=" in line:
                # Extraer después de "u0 " hasta el "}" (fin de la ruta)
                match = re.search(r'u0\s+([a-zA-Z0-9_.]+/[a-zA-Z0-9_.]+)', line)
                if match:
                    full_name = match.group(1)
                    # Parsear "com.package/ClassName" -> package_id, activity_class
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
    """
    Obtiene información de un paquete instalado.
    
    Usa 'dumpsys package package_id' para ver metadata.
    """
    cmd = [
        "adb", "-s", device_serial,
        "shell", "dumpsys", "package", package_id
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return {}
        
        info = {}
        lines = result.stdout.strip().split("\n")
        
        for line in lines:
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
    """Checkea si un paquete está instalado"""
    cmd = [
        "adb", "-s", device_serial,
        "shell", "pm", "list", "packages", package_id
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return package_id in result.stdout
        
    except Exception:
        return False


# ============== CAPA 3: ACCIÓN ==============
def force_stop_package(device_serial: str, package_id: str) -> Tuple[bool, str]:
    """
    Fuerza el cierre de una app (force-stop).
    Útil antes de desinstalar malware que resiste.
    """
    cmd = [
        "adb", "-s", device_serial,
        "shell", "am", "force-stop", package_id
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        success = result.returncode == 0
        message = result.stderr if result.stderr else result.stdout
        
        return success, message
        
    except Exception as e:
        return False, str(e)


def uninstall_package(device_serial: str, package_id: str, keep_data: bool = True) -> Tuple[bool, str]:
    """
    Desinstala una app para el usuario actual (user 0).
    
    Args:
        keep_data: Si True, usa '-k' para mantener datos (default True)
    
    Returns:
        (success, message)
    """
    # Flag -k = keep data, --user 0 = uninstall para usuario actual
    cmd = [
        "adb", "-s", device_serial,
        "shell", "pm", "uninstall",
    ]
    
    if keep_data:
        cmd.append("-k")
    
    cmd.extend(["--user", "0", package_id])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # pm uninstall retorna "Success" o "Failure"
        output = result.stdout.strip()
        
        if "Success" in output:
            return True, "Package uninstalled successfully"
        elif "Failure" in output:
            return False, f"Uninstall failed: {output}"
        else:
            return False, f"Unknown response: {output}"
            
    except Exception as e:
        return False, str(e)


# ============== EXCEPCIONES ==============
class ADBError(Exception):
    """Error genérico de ADB"""
    pass


class ADBNotFoundError(ADBError):
    """ADB no está instalado"""
    pass