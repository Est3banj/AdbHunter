"""
AdbHunter - GUI Ultra-Minimal
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from src.core.adb import is_adb_installed, get_devices, get_connected_device, force_stop_package, uninstall_package
from src.core.watcher import Watcher
from src.config.settings import get_full_whitelist, is_whitelisted, load_config, add_to_user_whitelist, remove_from_user_whitelist


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AdbHunter")
        self.root.geometry("600x400")
        
        self.watcher = None
        self.history = []
        self.selected = None
        self.last_pkg = None
        self.config = load_config()
        
        self._build()
    
    def _build(self):
        # Title
        tk.Label(self.root, text="AdbHunter", font=("Arial", 20, "bold")).pack(pady=10)
        
        # Status
        self.status = tk.Label(self.root, text="Checking...", font=("Arial", 12))
        self.status.pack()
        
        # Start button
        self.btn = tk.Button(self.root, text="START", font=("Arial", 14), 
                         bg="green", fg="white", command=self._start)
        self.btn.pack(pady=10)
        
        # Current app display
        tk.Label(self.root, text="Current App:").pack()
        self.current = tk.Label(self.root, text="--", font=("Arial", 14), fg="blue")
        self.current.pack()
        
        # Action buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="FORCE STOP", bg="orange", command=self._stop).pack(side="left", padx=5)
        tk.Button(btn_frame, text="UNINSTALL", bg="red", fg="white", command=self._uninstall).pack(side="left", padx=5)
        tk.Button(btn_frame, text="+WHITELIST", command=self._wl).pack(side="left", padx=5)
        
        # History list
        tk.Label(self.root, text="History:").pack()
        self.list = tk.Listbox(self.root, height=10)
        self.list.pack(fill="both", expand=True, padx=20, pady=10)
        self.list.bind('<<ListboxSelect>>', self._select)
        
        self._check()
    
    def _check(self):
        if not is_adb_installed():
            self.status.config(text="ADB missing")
            return
        
        d = get_connected_device()
        if d:
            self.status.config(text="Connected: " + d.serial[:15])
            self.btn.config(state="normal", bg="green")
        else:
            self.status.config(text="No device")
            self.btn.config(state="disabled", bg="gray")
        
        self.root.after(3000, self._check)
    
    def _start(self):
        d = get_connected_device()
        if not d:
            return
        
        if self.watcher and self.watcher.is_running:
            self.watcher.stop()
            self.watcher = None
            self.btn.config(text="START", bg="green")
        else:
            self.watcher = Watcher(self.config.poll_interval, self._on_change, get_full_whitelist())
            self.watcher.start()
            self.btn.config(text="STOP", bg="red")
    
    def _on_change(self, act):
        pkg = act.package_id
        if pkg != self.last_pkg:
            self.last_pkg = pkg
            if not self.history or self.history[-1] != pkg:
                self.history.append(pkg)
                self.list.insert(tk.END, pkg)
                self.list.see(tk.END)
            self.current.config(text=pkg)
    
    def _select(self, e):
        i = self.list.curselection()
        if i:
            self.selected = self.history[i[0]]
            self.current.config(text=self.selected)
    
    def _stop(self):
        pkg = self.selected or self.last_pkg
        if not pkg:
            messagebox.showwarning("?", "Select app first")
            return
        d = get_connected_device()
        if d:
            ok, m = force_stop_package(d.serial, pkg)
            messagebox.showinfo("Result", m)
    
    def _uninstall(self):
        pkg = self.selected or self.last_pkg
        if not pkg:
            messagebox.showwarning("?", "Select app first")
            return
        if is_whitelisted(pkg):
            messagebox.showerror("Blocked", "Whitelisted app")
            return
        if messagebox.askyesno("?", f"Uninstall {pkg}?"):
            d = get_connected_device()
            if d:
                ok, m = uninstall_package(d.serial, pkg)
                messagebox.showinfo("Result", m)
    
    def _wl(self):
        pkg = self.selected or self.last_pkg
        if not pkg:
            return
        if is_whitelisted(pkg):
            remove_from_user_whitelist(pkg)
        else:
            add_to_user_whitelist(pkg)
        if self.watcher:
            self.watcher.update_whitelist(get_full_whitelist())
        messagebox.showinfo("OK", "Whitelist updated")


App().root.mainloop()