"""
AdbHunter - GUI Simple
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.core.adb import is_adb_installed, get_connected_device, force_stop_package, uninstall_package
from src.core.watcher import Watcher
from src.config.settings import get_full_whitelist, is_whitelisted, load_config, add_to_user_whitelist, remove_from_user_whitelist


# Prevenir el FocusIn event en botones (causa el borde blanco)
def block_focus(event):
    return "break"


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AdbHunter - Virus Hunter")
        self.root.geometry("650x480")
        
        # En macOS: forzar que NINGUN widget reciba foco de teclado
        if sys.platform == "darwin":
            # Deshabilitar focus en toda la app
            self.root.option_add("*tearOff", False)
            self.root.bind_class("Button", "<FocusIn>", block_focus)
            self.root.bind_class("Button", "<Key>", block_focus)

        self.watcher = None
        self.history = []
        self.selected = None
        self.last_pkg = None
        self.config = load_config()
        self.max_history = 100

        self._build()

    def _build(self):
        # Title
        tk.Label(self.root, text="AdbHunter", font=("Arial", 22, "bold"), fg="#2979FF").pack(pady=10)

        # Status
        self.status = tk.Label(self.root, text="Verificando...", font=("Arial", 12, "bold"), fg="#424242")
        self.status.pack()

        # Start button
        self.btn = tk.Button(self.root, text="INICIAR", font=("Arial", 12, "bold"),
                         bg="#00C853", fg="white", command=self._start,
                         relief="flat", borderwidth=0)
        self.btn.pack(pady=10)

        # Current app display
        tk.Label(self.root, text="App Actual:").pack()
        self.current = tk.Label(self.root, text="--", font=("Arial", 14, "bold"), fg="#2962FF")
        self.current.pack()

        # Action buttons frame
        btn_frame = tk.Frame(self.root, bg=self.root.cget("bg"))
        btn_frame.pack(pady=10)

        # FORCE STOP
        self.btn_fs = tk.Button(btn_frame, text="FORCE STOP", bg="#FF6D00", fg="white", font=("Arial", 10, "bold"),
                command=self._stop, relief="flat", borderwidth=0)
        self.btn_fs.pack(side="left", padx=5)

        # DESINSTALAR
        self.btn_un = tk.Button(btn_frame, text="DESINSTALAR", bg="#D50000", fg="white", font=("Arial", 10, "bold"),
                command=self._uninstall, relief="flat", borderwidth=0)
        self.btn_un.pack(side="left", padx=5)

        # Whitelist
        self.btn_wl = tk.Button(btn_frame, text="+ Whitelist", bg="#6200EA", fg="white", font=("Arial", 10),
                command=self._wl, relief="flat", borderwidth=0)
        self.btn_wl.pack(side="left", padx=5)
        
        # REFRESH - Recargar lista de apps
        self.btn_refresh = tk.Button(btn_frame, text="REFRESH", bg="#2196F3", fg="white", font=("Arial", 10),
                command=self._refresh, relief="flat", borderwidth=0)
        self.btn_refresh.pack(side="left", padx=5)

        # Info label
        self.info = tk.Label(self.root, text=f"Whitelist: {len(get_full_whitelist())} apps",
                          fg="#6200EA", font=("Arial", 10, "bold"))
        self.info.pack()

        # History list
        tk.Label(self.root, text="Historial de Apps:", font=("Arial", 11, "bold")).pack()

        self.list = tk.Listbox(self.root, height=12, font=("Arial", 10))
        self.list.pack(fill="both", expand=True, padx=20, pady=10)
        self.list.bind('<<ListboxSelect>>', self._select)

        # Instructions
        tk.Label(self.root, text="Click en una app del historial para seleccionarla",
              fg="gray", font=("Arial", 9)).pack(pady=5)

        self._check()

    def _check(self):
        if not is_adb_installed():
            self.status.config(text="ADB no instalado", fg="#D50000")
            self.btn.config(state="disabled", bg="gray")
            return

        d = get_connected_device()
        if d:
            self.status.config(text=f"Conectado: {d.serial[:15]}", fg="#00C853")
            self.btn.config(state="normal", bg="#00C853")
        else:
            self.status.config(text="Sin equipo conectado", fg="#D50000")
            self.btn.config(state="disabled", bg="gray")

        self.root.after(3000, self._check)

    def _start(self):
        d = get_connected_device()
        if not d:
            messagebox.showwarning("Atencion", "No hay equipo conectado")
            return

        if self.watcher and self.watcher.is_running:
            self.watcher.stop()
            self.watcher = None
            self.btn.config(text="INICIAR", bg="#00C853")
            self.status.config(text="Detenido", fg="#424242")
        else:
            self.watcher = Watcher(self.config.poll_interval, self._on_change, get_full_whitelist())
            self.watcher.start()
            self.btn.config(text="DETENER", bg="#D50000")
            self.status.config(text="Monitoreando...", fg="#00C853")

    def _on_change(self, act):
        pkg = act.package_id
        if pkg != self.last_pkg:
            self.last_pkg = pkg
            self._update_list(pkg)

    def _update_list(self, pkg):
        is_wl = is_whitelisted(pkg)

        if not self.history or self.history[-1] != pkg:
            self.history.append(pkg)

            # Limitar historial
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
                while self.list.size() > self.max_history:
                    self.list.delete(0)

            # Color based on whitelist status
            color = "#FF1744" if not is_wl else "#00C853"
            display = f"[!] {pkg}" if not is_wl else f"[OK] {pkg}"

            self.list.insert(tk.END, display)
            self.list.see(tk.END)

            last_idx = self.list.size() - 1
            self.list.itemconfigure(last_idx, fg=color)

        # Update current label
        status = "(whitelist)" if is_wl else ""
        color = "#FF1744" if not is_wl else "#00C853"
        self.current.config(text=f"{pkg} {status}", fg=color, font=("Arial", 14, "bold"))

    def _select(self, e):
        i = self.list.curselection()
        if i:
            text = self.list.get(i[0])
            pkg = text.replace("[!] ", "").replace("[OK] ", "")
            self.selected = pkg

            is_wl = is_whitelisted(pkg)
            color = "#FF1744" if not is_wl else "#00C853"
            self.current.config(text=pkg, fg=color, font=("Arial", 14, "bold"))

    def _stop(self):
        pkg = self.selected or self.last_pkg
        if not pkg:
            messagebox.showwarning("Atencion", "Selecciona una app primero")
            return

        d = get_connected_device()
        if d:
            ok, m = force_stop_package(d.serial, pkg)
            if ok:
                messagebox.showinfo("OK", f"Force stop aplicado:\n{pkg}")
            else:
                messagebox.showerror("Error", m)

    def _uninstall(self):
        pkg = self.selected or self.last_pkg
        if not pkg:
            messagebox.showwarning("Atencion", "Selecciona una app primero")
            return

        if is_whitelisted(pkg):
            messagebox.showerror("Bloqueado", f"No se puede desistalar:\n{pkg}\nEsta en whitelist")
            return

        if messagebox.askyesno("Confirmar", f"Desinstalar {pkg}?\n\nEsto no se puede deshacer!"):
            d = get_connected_device()
            if d:
                ok, m = uninstall_package(d.serial, pkg)
                if ok:
                    messagebox.showinfo("OK", f"Desinstalado:\n{pkg}")
                    self.selected = None
                else:
                    messagebox.showerror("Error", m)

    def _wl(self):
        pkg = self.selected or self.last_pkg
        if not pkg:
            messagebox.showwarning("Atencion", "Selecciona una app primero")
            return

        if is_whitelisted(pkg):
            remove_from_user_whitelist(pkg)
            self.btn_wl.config(text="+ Whitelist", bg="#6200EA")
            msg = f"Removido de whitelist:\n{pkg}"
        else:
            add_to_user_whitelist(pkg)
            self.btn_wl.config(text="PROTEGIDO", bg="#00C853")
            msg = f"Agregado a whitelist:\n{pkg}"

        if self.watcher:
            self.watcher.update_whitelist(get_full_whitelist())

        self.info.config(text=f"Whitelist: {len(get_full_whitelist())} apps", fg="#6200EA")
        messagebox.showinfo("OK", msg)
    
    def _refresh(self):
        """Recargar y comenzar escaneo desde cero"""
        # Detener watcher si está corriendo
        if self.watcher and self.watcher.is_running:
            self.watcher.stop()
            self.watcher = None
            self.btn.config(text="INICIAR", bg="#00C853")
        
        # Limpiar historial
        self.history = []
        self.list.delete(0, tk.END)
        self.last_pkg = None
        self.selected = None
        self.current.config(text="--", fg="#2962FF")
        
        # Recargar config
        self.config = load_config()
        
        if not is_adb_installed():
            self.status.config(text="ADB no instalado", fg="#D50000")
            self.btn.config(state="disabled", bg="gray")
            messagebox.showerror("Error", "ADB no está instalado")
            return

        d = get_connected_device()
        if d:
            self.status.config(text=f"Conectado: {d.serial[:15]}", fg="#00C853")
            self.btn.config(state="normal", bg="#00C853")
            messagebox.showinfo("OK", f"Listo para escanear:\n{d.serial[:20]}")
        else:
            self.status.config(text="Sin equipo conectado", fg="#D50000")
            self.btn.config(state="disabled", bg="gray")
            messagebox.showwarning("Atencion", "No hay equipo conectado")


if __name__ == "__main__":
    App().root.mainloop()