"""
App - Interfaz Gráfica CustomTkinter (MINIMAL)
"""

import customtkinter as ctk
import os
import sys

# Fix path - Agregar el directory padre para poder importar src.core
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, script_dir)

from src.core.adb import is_adb_installed, get_devices, get_connected_device, force_stop_package, uninstall_package, DeviceStatus
from src.core.watcher import Watcher
from src.config.settings import get_full_whitelist, is_whitelisted, load_config, can_uninstall, log_uninstall, add_to_user_whitelist, remove_from_user_whitelist


class AdbHunterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AdbHunter")
        self.geometry("800x500")
        
        self.watcher = None
        self.selected_package = None
        self.config = load_config()
        
        self._build_ui()
        self.after(1000, self._check_adb)
    
    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, height=40)
        header.pack(fill="x", side="top")
        
        ctk.CTkLabel(header, text="AdbHunter", font=("Arial", 18, "bold")).pack(side="left", padx=20, pady=5)
        
        self.status = ctk.CTkLabel(header, text="Checking...")
        self.status.pack(side="right", padx=20, pady=5)
        
        # Main
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel
        left = ctk.CTkFrame(main, width=200)
        left.pack(side="left", fill="y", padx=(0, 10))
        
        self.btn_start = ctk.CTkButton(left, text="START", command=self._toggle, fg_color="green", height=35)
        self.btn_start.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(left, text="Current:").pack(padx=10, pady=(10, 0), anchor="w")
        self.current = ctk.CTkLabel(left, text="--", font=("Arial", 14))
        self.current.pack(padx=10, pady=5)
        
        self.btn_stop = ctk.CTkButton(left, text="FORCE STOP", command=self._force_stop, fg_color="orange", state="disabled")
        self.btn_stop.pack(fill="x", padx=10, pady=5)
        
        self.btn_uninstall = ctk.CTkButton(left, text="UNINSTALL", command=self._uninstall, fg_color="red", state="disabled")
        self.btn_uninstall.pack(fill="x", padx=10, pady=5)
        
        self.btn_wl = ctk.CTkButton(left, text="+ WHITELIST", command=self._toggle_wl, state="disabled")
        self.btn_wl.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(left, text="Poll:").pack(padx=10, pady=(10, 0), anchor="w")
        self.poll_val = ctk.CTkLabel(left, text=f"{self.config.poll_interval}s")
        self.poll_val.pack(padx=10)
        
        self.slider = ctk.CTkSlider(left, from_=0.2, to=2.0, command=self._on_slider)
        self.slider.set(self.config.poll_interval)
        self.slider.pack(fill="x", padx=10)
        
        # Log panel
        right = ctk.CTkFrame(main)
        right.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(right, text="Activity Log").pack(padx=10, pady=10)
        
        self.log_frame = ctk.CTkScrollableFrame(right)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _check_adb(self):
        if is_adb_installed():
            devs = get_devices()
            if devs:
                d = get_connected_device()
                if d:
                    self.status.configure(text=f"OK: {d.serial[:12]}")
                    self.btn_start.configure(state="normal")
                    return
            self.status.configure(text="No device")
        else:
            self.status.configure(text="ADB missing")
        self.btn_start.configure(state="disabled")
    
    def _toggle(self):
        if self.watcher and self.watcher.is_running:
            self.watcher.stop()
            self.watcher = None
            self.btn_start.configure(text="START", fg_color="green")
        else:
            d = get_connected_device()
            if not d:
                return
            self.watcher = Watcher(self.config.poll_interval, self._on_change, get_full_whitelist())
            self.watcher.start()
            self.btn_start.configure(text="STOP", fg_color="red")
    
    def _on_change(self, act):
        from datetime import datetime
        self.current.configure(text=act.package_id)
        self.selected_package = act.package_id
        
        self.btn_stop.configure(state="normal")
        self.btn_uninstall.configure(state="normal")
        
        if is_whitelisted(act.package_id):
            self.btn_wl.configure(text="WHITELISTED", state="disabled")
        else:
            self.btn_wl.configure(text="+ WHITELIST", state="normal")
        
        # Log
        ts = datetime.now().strftime("%H:%M:%S")
        color = "red" if not is_whitelisted(act.package_id) else "green"
        
        row = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        row.pack(fill="x", pady=1)
        
        ctk.CTkLabel(row, text=f"[{ts}]", width=8).pack(side="left", padx=5)
        ctk.CTkLabel(row, text=act.package_id, text_color=color).pack(side="left")
        
        if self.watcher:
            self.status.configure(text=f"Polls: {self.watcher.state.poll_count}")
    
    def _force_stop(self):
        if not self.selected_package:
            return
        d = get_connected_device()
        if d:
            force_stop_package(d.serial, self.selected_package)
            self.status.configure(text="Stopped")
    
    def _uninstall(self):
        if not self.selected_package:
            return
        if is_whitelisted(self.selected_package):
            self.status.configure(text="Blocked", text_color="red")
            return
        if not can_uninstall():
            self.status.configure(text="Ratelimit", text_color="red")
            return
        
        d = get_connected_device()
        if d:
            ok, msg = uninstall_package(d.serial, self.selected_package)
            if ok:
                log_uninstall(self.selected_package)
                self.status.configure(text="Uninstalled", text_color="green")
                self.selected_package = None
                self.btn_stop.configure(state="disabled")
                self.btn_uninstall.configure(state="disabled")
            else:
                self.status.configure(text=msg[:30], text_color="red")
    
    def _toggle_wl(self):
        if not self.selected_package:
            return
        if is_whitelisted(self.selected_package):
            remove_from_user_whitelist(self.selected_package)
            self.btn_wl.configure(text="+ WHITELIST")
        else:
            add_to_user_whitelist(self.selected_package)
            self.btn_wl.configure(text="DONE")
            if self.watcher:
                self.watcher.update_whitelist(get_full_whitelist())
    
    def _on_slider(self, v):
        v = round(v, 1)
        self.poll_val.configure(text=f"{v}s")
        self.config.poll_interval = v
        from config.settings import save_config
        save_config(self.config)
        if self.watcher:
            self.watcher.poll_interval = v


def main():
    app = AdbHunterApp()
    app.mainloop()


if __name__ == "__main__":
    main()