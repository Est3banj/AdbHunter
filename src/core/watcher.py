"""
Watcher - Monitoreo de Foreground Activity
=========================================
Polling loop que detecta cambios en la app visible.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable, List
from datetime import datetime

# Import relativo para módulos del mismo paquete
from .adb import (
    get_connected_device,
    get_foreground_activity,
    Device,
    ForegroundActivity,
    DeviceStatus
)


# ============== MODELOS ==============
@dataclass
class ActivityLog:
    """Registro de una actividad detectada"""
    package_id: str
    activity_class: str
    timestamp: datetime
    is_new: bool  # True si es nuevo respecto al anterior


@dataclass
class WatcherState:
    """Estado actual del watcher"""
    is_running: bool = False
    is_paused: bool = False
    device_serial: Optional[str] = None
    last_package: Optional[str] = None
    current_package: Optional[str] = None
    poll_count: int = 0
    activity_history: List[ActivityLog] = field(default_factory=list)
    last_error: Optional[str] = None


# ============== WATCHER ==============
class Watcher:
    """
    Watcher que monitorea foreground activity.
    
    Usage:
        watcher = Watcher(poll_interval=0.5)
        
        # Callback cuando cambia la activity
        def on_change(activity):
            print(f"Nueva app: {activity.package_id}")
        
        watcher.on_activity_change = on_change
        watcher.start()
    """
    
    def __init__(
        self,
        poll_interval: float = 0.5,
        on_change: Optional[Callable[[ForegroundActivity], None]] = None,
        whitelist: Optional[set] = None
    ):
        """
        Args:
            poll_interval: Segundos entre cada poll (default 0.5s)
            on_change: Callback cuando cambia la foreground activity
            whitelist: Set de packages que se ignoran (opcional)
        """
        self.poll_interval = poll_interval
        self.on_activity_change = on_change
        self.whitelist = whitelist or set()
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._state = WatcherState()
        
        # Locks
        self._lock = threading.Lock()
    
    @property
    def is_running(self) -> bool:
        """Checkea si el watcher está corriendo"""
        return self._running
    
    @property
    def state(self) -> WatcherState:
        """Estado actual (thread-safe)"""
        with self._lock:
            return self._state
    
    @property
    def current_package(self) -> Optional[str]:
        """Package actual en foreground"""
        return self._state.current_package
    
    @property
    def last_package(self) -> Optional[str]:
        """Último package detectado"""
        return self._state.last_package
    
    # ------------ CORRER ------------
    def start(self):
        """Inicia el watcher en un thread separado"""
        if self._running:
            return  # Ya está corriendo
        
        # Verificar que hay device conectado
        device = get_connected_device()
        if not device:
            self._state.last_error = "No device connected"
            return
        
        self._state.device_serial = device.serial
        self._state.is_running = True
        self._state.last_error = None
        
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Detiene el watcher"""
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        
        with self._lock:
            self._state.is_running = False
    
    def pause(self):
        """Pausa el watcher (no para el thread, solo skippea polls)"""
        with self._lock:
            self._state.is_paused = True
    
    def resume(self):
        """Reanuda el watcher"""
        with self._lock:
            self._state.is_paused = False
    
    # ------------ LOOP INTERNO ------------
    def _run_loop(self):
        """Loop principal de polling"""
        self._running = True
        
        while self._running:
            # Check paused
            if self._state.is_paused:
                time.sleep(0.1)
                continue
            
            # Verificar device todavía conectado
            device = get_connected_device()
            if not device:
                self._state.last_error = "Device disconnected"
                time.sleep(1)
                continue
            
            # Query foreground activity
            activity = get_foreground_activity(device.serial)
            
            if activity:
                with self._lock:
                    self._state.poll_count += 1
                    
                    # Si cambió el package
                    if activity.package_id != self._state.last_package:
                        # Ignorar si está en whitelist
                        if activity.package_id in self.whitelist:
                            pass  # Silent ignore
                        else:
                            # Nuevo package - notificar
                            self._state.last_package = self._state.current_package
                            self._state.current_package = activity.package_id
                            
                            # Loggear en historial
                            log_entry = ActivityLog(
                                package_id=activity.package_id,
                                activity_class=activity.activity_class,
                                timestamp=datetime.now(),
                                is_new=True
                            )
                            self._state.activity_history.append(log_entry)
                            
                            # Limpiar historial si crece mucho
                            if len(self._state.activity_history) > 100:
                                self._state.activity_history = (
                                    self._state.activity_history[-50:]
                                )
                            
                            # Callback
                            if self.on_activity_change:
                                try:
                                    self.on_activity_change(activity)
                                except Exception as e:
                                    self._state.last_error = f"Callback error: {e}"
            
            else:
                # Fallo al queryar
                with self._lock:
                    self._state.last_error = "Failed to get foreground activity"
            
            # Sleep
            time.sleep(self.poll_interval)
        
        # Cleanup
        with self._lock:
            self._state.is_running = False
    
    # ------------ HELPERS ------------
    def get_history(self, limit: int = 20) -> List[ActivityLog]:
        """Obtiene el historial de activities"""
        with self._lock:
            return self._state.activity_history[-limit:]
    
    def get_recent_new_packages(self, seconds: float = 2.0) -> List[str]:
        """
        Obtiene packages nuevos en los últimos X segundos.
        Útil para detectar malware que se abre y cierra rápido.
        """
        with self._lock:
            now = datetime.now()
            cutoff = now.timestamp() - seconds
            
            recent = [
                log.package_id 
                for log in self._state.activity_history
                if log.timestamp.timestamp() >= cutoff and log.is_new
            ]
            
            # Dedupe
            return list(dict.fromkeys(recent))
    
    def clear_history(self):
        """Limpia el historial"""
        with self._lock:
            self._state.activity_history.clear()
    
    def update_whitelist(self, whitelist: set):
        """Actualiza la whitelist"""
        self.whitelist = whitelist