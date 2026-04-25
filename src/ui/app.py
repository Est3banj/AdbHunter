"""
App - Interfaz Gráfica CustomTkinter
===================================
GUI principal de AdbHunter.
"""

import customtkinter as ctk
from typing import Optional
from datetime import datetime
import threading

# Importar módulos del proyecto
from core.adb import (
    get_devices,
    get_connected_device,
    is_adb_installed,
    force_stop_package,
    uninstall_package,
    Device,
    DeviceStatus,
    ForegroundActivity,
    ADBNotFoundError
)

from core.watcher import Watcher, ActivityLog
from config.settings import (
    get_full_whitelist,
    is_whitelisted,
    load_config,
    can_uninstall,
    log_uninstall,
    add_to_user_whitelist,
    remove_from_user_whitelist,
    MAX_UNINSTALLS_PER_HOUR
)


# ============== CONSTANTS ==============
CTK_COLORS = {
    "dark": {
        "bg": "#1a1a1a",
        "fg": "#2b2b2b",
        "text": "#ffffff",
        "accent": "#3b8ed0",
        "success": "#2dd36f",
        "warning": "#ffce00",
        "danger": "#ff3b30",
    },
    "light": {
        "bg": "#f0f0f0",
        "fg": "#ffffff",
        "text": "#000000",
        "accent": "#3b8ed0",
        "success": "#28a745",
        "warning": "#ffc107",
        "danger": "#dc3545",
    }
}


# ============== APP PRINCIPAL ==============
class AdbHunterApp(ctk.CTk):
    """
    Ventana principal de AdbHunter.
    
    Layout:
    ┌────────────────────────────────────────────────────────┐
    │ Header: título + status de conexión                   │
    ├────────────────────────────────────────────────────────┤
    │ Panel Izq: Controles (Start/Stop, Poll Interval, etc)   │
    │ Panel Der: Activity Log en tiempo real                  │
    ├────────────────────────────────────────────────────────┤
    │ Footer: Acción (Force Stop, Uninstall) + Info          │
    └────────────────────────────────────────────────────────┘
    """
    
    def __init__(self):
        # Setup ventana
        super().__init__()
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.title("AdbHunter - Virus & Process Tracker")
        self.geometry("900x600")
        
        # State
        self.watcher: Optional[Watcher] = None
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self._selected_package: Optional[str] = None
        
        # Config
        self.config = load_config()
        
        # Layout
        self._setup_ui()
        
        # Auto-start check connection
        self.after(500, self._check_connection)
    
    # ------------ SETUP UI ------------
    def _setup_ui(self):
        """Crea los componentes de la UI"""
        
        # Grid config
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ──────────── HEADER ────────────
        self.header = ctk.CTkFrame(self, height=50, corner_radius=0)
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header.grid_propagate(False)
        
        # Título
        self.title_label = ctk.CTkLabel(
            self.header,
            text="AdbHunter",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(side="left", padx=20, pady=10)
        
        # Status connection
        self.status_label = ctk.CTkLabel(
            self.header,
            text="🔴 No device",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(side="right", padx=20, pady=10)
        
        # ──────────── PANEL IZQUIERDO (CONTROLS) ────────────
        self.left_panel = ctk.CTkFrame(self, width=250)
        self.left_panel.grid(row=1, column=0, sticky="ns", padx=10, pady=10)
        self.left_panel.grid_propagate(False)
        
        # Botón Start/Stop
        self.btn_start = ctk.CTkButton(
            self.left_panel,
            text="▶ Start Watcher",
            command=self._toggle_watcher,
            fg_color="#2dd36f",
            height=40
        )
        self.btn_start.pack(fill="x", padx=10, pady=10)
        
        # Current Package (Display)
        ctk.CTkLabel(
            self.left_panel,
            text="Current Foreground:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(padx=10, pady=(10, 0), anchor="w")
        
        self.current_package_label = ctk.CTkLabel(
            self.left_panel,
            text="--",
            font=ctk.CTkFont(size=16)
        )
        self.current_package_label.pack(padx=10, pady=5, fill="x")
        
        # Activity Class
        self.activity_class_label = ctk.CTkLabel(
            self.left_panel,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.activity_class_label.pack(padx=10, pady=(0, 10), fill="x")
        
        # Separator
        ctk.CTkSeparator(self.left_panel).pack(fill="x", padx=10, pady=10)
        
        # Acciones
        ctk.CTkLabel(
            self.left_panel,
            text="Actions:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(padx=10, pady=(5, 0), anchor="w")
        
        # Force Stop
        self.btn_force_stop = ctk.CTkButton(
            self.left_panel,
            text="⏹ Force Stop",
            command=self._on_force_stop,
            fg_color="#ffce00",
            state="disabled"
        )
        self.btn_force_stop.pack(fill="x", padx=10, pady=5)
        
        # Uninstall
        self.btn_uninstall = ctk.CTkButton(
            self.left_panel,
            text="🗑 Uninstall",
            command=self._on_uninstall,
            fg_color="#ff3b30",
            state="disabled"
        )
        self.btn_uninstall.pack(fill="x", padx=10, pady=5)
        
        # Whitelist toggle
        self.btn_whitelist = ctk.CTkButton(
            self.left_panel,
            text="✓ Add to Whitelist",
            command=self._on_toggle_whitelist,
            state="disabled"
        )
        self.btn_whitelist.pack(fill="x", padx=10, pady=10)
        
        # Separator
        ctk.CTkSeparator(self.left_panel).pack(fill="x", padx=10, pady=10)
        
        # Poll Interval
        ctk.CTkLabel(
            self.left_panel,
            text="Poll Interval:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(padx=10, pady=(5, 0), anchor="w")
        
        self.poll_slider = ctk.CTkSlider(
            self.left_panel,
            from_=0.2,
            to=2.0,
            number_of_steps=18,
            command=self._on_poll_interval_change,
            state="disabled"
        )
        self.poll_slider.set(self.config.poll_interval)
        self.poll_slider.pack(fill="x", padx=10, pady=5)
        
        self.poll_label = ctk.CTkLabel(
            self.left_panel,
            text=f"{self.config.poll_interval}s",
            font=ctk.CTkFont(size=12)
        )
        self.poll_label.pack(padx=10, pady=(0, 10))
        
        # Stats
        self.stats_label = ctk.CTkLabel(
            self.left_panel,
            text="Polls: 0 | Detection rate: --",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.stats_label.pack(padx=10, pady=10)
        
        # ──────────── PANEL DERECHO (LOGS) ────────────
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=10)
        
        # Title
        ctk.CTkLabel(
            self.right_panel,
            text="Activity Log",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(padx=10, pady=10, anchor="w")
        
        # Scrollable frame para logs
        self.log_scroll = ctk.CTkScrollableFrame(
            self.right_panel,
            label_text=""
        )
        self.log_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # ──────────── FOOTER ────────────
        self.footer = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        self.footer_label = ctk.CTkLabel(
            self.footer,
            text=f"Whitelist: {len(get_full_whitelist())} packages protected",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.footer_label.pack(side="right", padx=20, pady=5)
    
    # ------------ CALLBACKS ------------
    def _check_connection(self):
        """Checkea conexión ADB"""
        try:
            if not is_adb_installed():
                self.status_label.configure(text="⚠️ ADB not found")
                self._set_controls_state(False)
                return
            
            devices = get_devices()
            
            if not devices:
                self.status_label.configure(text="🔴 No device")
                self._set_controls_state(False)
            else:
                connected_device = get_connected_device()
                if connected_device:
                    self.status_label.configure(
                        text=f"🟢 {connected_device.serial[:20]}"
                    )
                    self._set_controls_state(True)
                else:
                    # Device pero no autorizado
                    unauthorized = [d for d in devices if d.status == DeviceStatus.UNAUTHORIZED]
                    if unauthorized:
                        self.status_label.configure(
                            text="🟡 Accept RSA on phone"
                        )
                    else:
                        self.status_label.configure(
                            text=f"🔴 {devices[0].status.value}"
                        )
                    self._set_controls_state(False)
                    
        except Exception as e:
            self.status_label.configure(text=f"⚠️ Error: {e}")
            self._set_controls_state(False)
        
        # Re-check cada 5 segundos
        self.after(5000, self._check_connection)
    
    def _set_controls_state(self, enabled: bool):
        """Habilita/deshabilita botones según estado"""
        state = "normal" if enabled else "disabled"
        
        self.btn_start.configure(state=state)
        self.poll_slider.configure(state=state)
    
    def _toggle_watcher(self):
        """Inicia/detiene el watcher"""
        if self.watcher and self.watcher.is_running:
            # Stop
            self.watcher.stop()
            self.watcher = None
            self.btn_start.configure(text="▶ Start Watcher", fg_color="#2dd36f")
        else:
            # Start
            device = get_connected_device()
            if not device:
                return
            
            # Crear watcher
            whitelist = get_full_whitelist()
            self.watcher = Watcher(
                poll_interval=self.config.poll_interval,
                on_change=self._on_activity_change,
                whitelist=whitelist
            )
            self.watcher.start()
            
            self.btn_start.configure(text="⏹ Stop Watcher", fg_color="#ff3b30")
    
    def _on_activity_change(self, activity: ForegroundActivity):
        """Callback cuando cambia la foreground activity"""
        # Update labels (en main thread)
        self.current_package_label.configure(text=activity.package_id)
        self.activity_class_label.configure(text=activity.activity_class)
        
        # Update selected package
        self._selected_package = activity.package_id
        
        # Enable action buttons
        self.btn_force_stop.configure(state="normal")
        self.btn_uninstall.configure(state="normal")
        
        # Check whitelist status
        if is_whitelisted(activity.package_id):
            self.btn_whitelist.configure(text="✓ In Whitelist", state="disabled")
        else:
            self.btn_whitelist.configure(
                text="+ Add to Whitelist",
                command=self._on_toggle_whitelist,
                state="normal"
            )
        
        # Add to log
        self._add_log_entry(activity)
        
        # Update stats
        if self.watcher:
            poll_count = self.watcher.state.poll_count
            self.stats_label.configure(
                text=f"Polls: {poll_count} | Detection rate: --"
            )
    
    def _add_log_entry(self, activity: ForegroundActivity):
        """Agrega entrada al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Frame para cada entry
        entry = ctk.CTkFrame(self.log_scroll, fg_color="transparent")
        entry.pack(fill="x", pady=2)
        
        # Timestamp
        ctk.CTkLabel(
            entry,
            text=f"[{timestamp}]",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            width=80
        ).pack(side="left", padx=(5, 0))
        
        # Package ID
        is_suspicious = not is_whitelisted(activity.package_id)
        text_color = "#ff3b30" if is_suspicious else "#2dd36f"
        
        ctk.CTkLabel(
            entry,
            text=activity.package_id,
            font=ctk.CTkFont(size=11, weight="bold" if is_suspicious else "normal"),
            text_color=text_color,
            anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=5)
        
        # Click para selects
        for widget in entry.winfo_children():
            widget.bind("<Button-1>", lambda e, pkg=activity.package_id: self._select_package(pkg))
    
    def _select_package(self, package_id: str):
        """Selecciona un package del log"""
        self._selected_package = package_id
        self.current_package_label.configure(text=package_id)
        
        self.btn_force_stop.configure(state="normal")
        self.btn_uninstall.configure(state="normal")
        
        if is_whitelisted(package_id):
            self.btn_whitelist.configure(text="✓ In Whitelist", state="disabled")
        else:
            self.btn_whitelist.configure(text="+ Add to Whitelist", state="normal")
    
    def _on_force_stop(self):
        """Force stop de la app seleccionada"""
        if not self._selected_package:
            return
        
        device = get_connected_device()
        if not device:
            return
        
        # Confirmar
        if not self._confirm_action(f"Force Stop {self._selected_package}?"):
            return
        
        success, msg = force_stop_package(device.serial, self._selected_package)
        
        if success:
            self._show_notification(f"Force stopped: {self._selected_package}")
        else:
            self._show_notification(f"Failed: {msg}", error=True)
    
    def _on_uninstall(self):
        """Desinstala la app seleccionada"""
        if not self._selected_package:
            return
        
        # Check whitelist
        if is_whitelisted(self._selected_package):
            self._show_notification("Cannot uninstall whitelisted app!", error=True)
            return
        
        # Check ratelimit
        if not can_uninstall():
            self._show_notification(
                f"Ratelimit reached ({MAX_UNINSTALLS_PER_HOUR}/hour max)",
                error=True
            )
            return
        
        device = get_connected_device()
        if not device:
            return
        
        # Confirmar
        if not self._confirm_action(
            f"UNINSTALL {self._selected_package}?\n\nThis cannot be undone!"
        ):
            return
        
        success, msg = uninstall_package(device.serial, self._selected_package)
        
        if success:
            log_uninstall(self._selected_package, "uninstall", user_confirmed=True)
            self._show_notification(f"Uninstalled: {self._selected_package}")
            
            # Clean selection
            self._selected_package = None
            self.btn_force_stop.configure(state="disabled")
            self.btn_uninstall.configure(state="disabled")
        else:
            log_uninstall(self._selected_package, "fail", user_confirmed=True)
            self._show_notification(f"Failed: {msg}", error=True)
    
    def _on_toggle_whitelist(self):
        """Agrega/remueve de whitelist"""
        if not self._selected_package:
            return
        
        if is_whitelisted(self._selected_package):
            remove_from_user_whitelist(self._selected_package)
            self.btn_whitelist.configure(text="+ Add to Whitelist")
        else:
            add_to_user_whitelist(self._selected_package)
            self.btn_whitelist.configure(text="✓ Added to Whitelist")
            
            # Update watcher whitelist si está corriendo
            if self.watcher:
                self.watcher.update_whitelist(get_full_whitelist())
    
    def _on_poll_interval_change(self, value):
        """Cambia poll interval"""
        value = round(value, 1)
        self.config.poll_interval = value
        self.poll_label.configure(text=f"{value}s")
        
        from config.settings import save_config
        save_config(self.config)
        
        # Update watcher si está corriendo
        if self.watcher:
            self.watcher.poll_interval = value
    
    def _confirm_action(self, message: str) -> bool:
        """Muestra diálogo de confirmación"""
        dialog = ctk.CTkInputDialog(
            self,
            title="Confirm",
            text=f"{message}\n\nType 'yes' to confirm:"
        )
        
        response = dialog.get_input()
        return response and response.lower().strip() == "yes"
    
    def _show_notification(self, message: str, error: bool = False):
        """Muestra notificación"""
        # Simple: actualizar status label temporalmente
        original = self.status_label.cget("text")
        color = "#ff3b30" if error else "#2dd36f"
        
        self.status_label.configure(text=message, text_color=color)
        
        # Restore después de 3 segundos
        self.after(3000, lambda: self.status_label.configure(text=original))


# ============== MAIN ==============
def main():
    """Entry point"""
    app = AdbHunterApp()
    app.mainloop()


if __name__ == "__main__":
    main()