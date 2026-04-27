"""
AdbHunter - GUI Simple
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os
from datetime import datetime
import json
import logging

# Silenciar warnings de grpc (ev_poll_posix)
os.environ['GRPC_VERBOSITY'] = 'ERROR'
logging.getLogger('grpc').setLevel(logging.ERROR)

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.core.adb import is_adb_installed, get_connected_device, force_stop_package, uninstall_package, enable_wireless_debugging, disconnect_wireless, scan_wireless_devices, pair_wireless
from src.core.watcher import Watcher
from src.config.settings import get_full_whitelist, is_whitelisted, load_config, add_to_user_whitelist, remove_from_user_whitelist

# ========== LICENCIA SYSTEM ==========
FIREBASE_AVAILABLE = False
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    pass

FIREBASE_CREDS = os.path.join(script_dir, "firebase-creds.json")

def init_firebase():
    if not FIREBASE_AVAILABLE:
        return None
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDS)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except:
        return None

LICENSE_FILE = "license.dat"

def get_license_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), LICENSE_FILE)
    return os.path.join(script_dir, LICENSE_FILE)

def validate_license(key):
    try:
        if not key.startswith("ADH-"):
            return False, "Key inválida"
        
        # Intentar Firebase
        try:
            db = init_firebase()
            if db:
                doc = db.collection("licencias").document(key).get()
                
                if not doc.exists:
                    return False, "Key no registrada"
                
                data = doc.to_dict()
                estado = data.get("estado", "")
                
                if estado != "activo":
                    return False, f"Key {estado}"
                
                expiry_ts = data.get("expiry")
                if expiry_ts:
                    expiry = expiry_ts.replace(tzinfo=None) if hasattr(expiry_ts, 'replace') else expiry_ts
                else:
                    return False, "Sin fecha de expiry"
                
                hoy = datetime.now()
                
                if expiry < hoy:
                    return False, f"Licencia expirada"
                
                dias_restantes = (expiry - hoy).days
                return True, f"Válida. Días restantes: {dias_restantes}"
            else:
                # Firebase no disponible - modo demo
                return True, "Modo demo (sin conexión)"
        except Exception as e:
            # Error cualquier modo demo
            return True, f"Modo demo: {str(e)[:30]}"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def load_saved_license():
    path = get_license_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data.get("key"), data.get("activado")
        except:
            pass
    return None, False

def save_license(key):
    path = get_license_path()
    with open(path, "w") as f:
        json.dump({"key": key, "activado": True}, f)

def check_license():
    key, activado = load_saved_license()
    if not activado or not key:
        return False
    
    valida, msg = validate_license(key)
    if valida:
        return True
    else:
        if os.path.exists(get_license_path()):
            os.remove(get_license_path())
        return False

def block_focus(event):
    return "break"


# ========== APP LICENCIA ==========
class AppLicencia:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AdbHunter - Activar")
        self.root.geometry("400x250")
        
        key_guardada, _ = load_saved_license()
        msg = "Tu licencia expiró. Ingresa nueva." if key_guardada else "Ingresa tu licencia"
        
        tk.Label(self.root, text="AdbHunter", font=("Arial", 24, "bold"), fg="#2979FF").pack(pady=20)
        tk.Label(self.root, text=msg, font=("Arial", 10), fg="#666").pack(pady=10)
        
        self.entry_key = tk.Entry(self.root, font=("Arial", 14), justify="center")
        self.entry_key.pack(pady=10)
        self.entry_key.focus()
        
        tk.Button(self.root, text="ACTIVAR", bg="#00C853", fg="white", font=("Arial", 12, "bold"),
               command=self.activar, relief="flat", borderwidth=0).pack(pady=10)
        
        tk.Label(self.root, text="Formato: ADH-YYMMDD-XXXX", font=("Arial", 8), fg="#999").pack(pady=5)
        
        self.root.mainloop()
    
    def activar(self):
        key = self.entry_key.get().strip().upper()
        valida, msg = validate_license(key)
        
        if valida:
            save_license(key)
            messagebox.showinfo("OK", f"AdbHunter activado!\n{msg}")
            self.root.destroy()
            AppPrincipal().root.mainloop()
        else:
            messagebox.showerror("Error", msg)


# ========== APP PRINCIPAL ==========
class AppPrincipal:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AdbHunter - Virus Hunter")
        self.root.geometry("650x480")
        
        if sys.platform == "darwin":
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
        tk.Label(self.root, text="AdbHunter", font=("Arial", 22, "bold"), fg="#2979FF").pack(pady=10)

        self.status = tk.Label(self.root, text="Verificando...", font=("Arial", 12, "bold"), fg="#424242")
        self.status.pack()

        self.btn = tk.Button(self.root, text="INICIAR", font=("Arial", 12, "bold"),
                         bg="#00C853", fg="white", command=self._start,
                         relief="flat", borderwidth=0)
        self.btn.pack(pady=10)

        tk.Label(self.root, text="App Actual:").pack()
        self.current = tk.Label(self.root, text="--", font=("Arial", 14, "bold"), fg="#2962FF")
        self.current.pack()

        btn_frame = tk.Frame(self.root, bg=self.root.cget("bg"))
        btn_frame.pack(pady=10)

        self.btn_fs = tk.Button(btn_frame, text="FORCE STOP", bg="#FF6D00", fg="white", font=("Arial", 10, "bold"),
                command=self._stop, relief="flat", borderwidth=0)
        self.btn_fs.pack(side="left", padx=5)

        self.btn_un = tk.Button(btn_frame, text="DESINSTALAR", bg="#D50000", fg="white", font=("Arial", 10, "bold"),
                command=self._uninstall, relief="flat", borderwidth=0)
        self.btn_un.pack(side="left", padx=5)

        self.btn_wl = tk.Button(btn_frame, text="+ Whitelist", bg="#6200EA", fg="white", font=("Arial", 10),
                command=self._wl, relief="flat", borderwidth=0)
        self.btn_wl.pack(side="left", padx=5)

        self.btn_refresh = tk.Button(btn_frame, text="REFRESH", bg="#2196F3", fg="white", font=("Arial", 10),
                command=self._refresh, relief="flat", borderwidth=0)
        self.btn_refresh.pack(side="left", padx=5)
        
        self.btn_info = tk.Button(btn_frame, text="ⓘ", bg="#607D8B", fg="white", font=("Arial", 10),
                command=self._show_info, relief="flat", borderwidth=0)
        self.btn_info.pack(side="left", padx=5)
        
        self.btn_wifi = tk.Button(btn_frame, text="WiFi", bg="#FF9800", fg="white", font=("Arial", 10),
                command=self._enable_wifi, relief="flat", borderwidth=0)
        self.btn_wifi.pack(side="left", padx=5)

        self.info = tk.Label(self.root, text=f"Whitelist: {len(get_full_whitelist())} apps",
                          fg="#6200EA", font=("Arial", 10, "bold"))
        self.info.pack()

        tk.Label(self.root, text="Historial de Apps:", font=("Arial", 11, "bold")).pack()

        self.list = tk.Listbox(self.root, height=12, font=("Arial", 10))
        self.list.pack(fill="both", expand=True, padx=20, pady=10)
        self.list.bind('<<ListboxSelect>>', self._select)

        tk.Label(self.root, text="Click en una app para seleccionarla",
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

            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
                while self.list.size() > self.max_history:
                    self.list.delete(0)

            color = "#FF1744" if not is_wl else "#00C853"
            display = f"[!] {pkg}" if not is_wl else f"[OK] {pkg}"

            self.list.insert(tk.END, display)
            self.list.see(tk.END)

            last_idx = self.list.size() - 1
            self.list.itemconfigure(last_idx, fg=color)

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
                messagebox.showinfo("OK", f"Force stop:\n{pkg}")
            else:
                messagebox.showerror("Error", m)

    def _uninstall(self):
        pkg = self.selected or self.last_pkg
        if not pkg:
            messagebox.showwarning("Atencion", "Selecciona una app primero")
            return

        if is_whitelisted(pkg):
            messagebox.showerror("Bloqueado", f"No se puede:\n{pkg} en whitelist")
            return

        if messagebox.askyesno("Confirmar", f"Desinstalar {pkg}?\n\nNo se puede deshacer!"):
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
            msg = f"Removido:\n{pkg}"
        else:
            add_to_user_whitelist(pkg)
            self.btn_wl.config(text="PROTEGIDO", bg="#00C853")
            msg = f"Protegido:\n{pkg}"

        if self.watcher:
            self.watcher.update_whitelist(get_full_whitelist())

        self.info.config(text=f"Whitelist: {len(get_full_whitelist())} apps", fg="#6200EA")
        messagebox.showinfo("OK", msg)
    
    def _refresh(self):
        if self.watcher and self.watcher.is_running:
            self.watcher.stop()
            self.watcher = None
            self.btn.config(text="INICIAR", bg="#00C853")
        
        self.history = []
        self.list.delete(0, tk.END)
        self.last_pkg = None
        self.selected = None
        self.current.config(text="--", fg="#2962FF")
        
        self.config = load_config()
        
        if not is_adb_installed():
            self.status.config(text="ADB no instalado", fg="#D50000")
            self.btn.config(state="disabled", bg="gray")
            messagebox.showerror("Error", "ADB no instalado")
            return
    
    def _show_info(self):
        info = """AdbHunter v1.0

Desarrollado por @Est3banj

GitHub: github.com/Est3banj
Telegram: t.me/Est3banj

Herramienta para detectar y eliminar
apps maliciosas en Android vía ADB.

⚠️ Usar con responsabilidad."""
        messagebox.showinfo("AdbHunter", info)
    
    def _enable_wifi(self):
        """Dialog para conectar via Wireless Debugging"""
        # Ver si ya hay device wireless conectado
        d = get_connected_device()
        
        if d:
            # Ya hay conexión -> ofrecer habilitar más
            ok, msg = enable_wireless_debugging(d.serial)
            if ok:
                messagebox.showinfo("WiFi", msg)
            else:
                messagebox.showerror("Error", msg)
        else:
            # Dialog simple para IP:puerto y código
            dialog = tk.Toplevel(self.root)
            dialog.title("WiFi Pairing")
            dialog.geometry("350x200")
            dialog.transient(self.root)
            
            tk.Label(dialog, text="Wireless Debugging", font=("Arial", 12, "bold")).pack(pady=10)
            
            tk.Label(dialog, text="IP:Puerto (del celu):").pack(anchor="w", padx=20)
            entry_ip = tk.Entry(dialog, width=35)
            entry_ip.pack(padx=20, pady=5)
            
            tk.Label(dialog, text="Código de pairing:").pack(anchor="w", padx=20)
            entry_code = tk.Entry(dialog, width=35)
            entry_code.pack(padx=20, pady=5)
            
            def do_pair():
                ip_port = entry_ip.get().strip()
                code = entry_code.get().strip()
                
                if not ip_port or not code:
                    messagebox.showwarning("Error", "Completá ambos campos")
                    return
                
                ok, msg = pair_wireless(ip_port, code)
                if ok:
                    messagebox.showinfo("Éxito", msg)
                    dialog.destroy()
                    self._check()
                else:
                    messagebox.showerror("Error", msg)
            
            tk.Button(dialog, text="Vincular", command=do_pair, bg="#00C853", fg="white").pack(pady=15)
            tk.Button(dialog, text="Cancelar", command=dialog.destroy).pack()

        d = get_connected_device()
        if d:
            self.status.config(text=f"Conectado: {d.serial[:15]}", fg="#00C853")
            self.btn.config(state="normal", bg="#00C853")
            messagebox.showinfo("OK", f"Listo:\n{d.serial[:20]}")
        else:
            self.status.config(text="Sin equipo conectado", fg="#D50000")
            self.btn.config(state="disabled", bg="gray")
            messagebox.showwarning("Atencion", "No hay equipo")


if __name__ == "__main__":
    if not check_license():
        AppLicencia()
    else:
        app = AppPrincipal()
        app.root.mainloop()