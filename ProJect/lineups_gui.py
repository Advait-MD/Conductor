"""
lineups_gui.py

Two macro "lineups" that run a set of predefined actions concurrently when clicked.

How it works:
- Each action is whitelisted in ACTION_WHITELIST.
- Clicking a lineup starts all its actions in separate threads/processes.
- Wi-Fi toggles require confirmation and admin privileges on Windows.
- Edit paths / command mappings below to match your system.
"""

import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ---------------- CONFIG ----------------
DRY_RUN = False  # Set True to only simulate what would run

# For Wi-Fi toggles on Windows: name of the network interface (commonly "Wi-Fi")
WIFI_INTERFACE = "Wi-Fi"  # change if your adapter name differs (check `netsh interface show interface`)

# Whitelisted actions: each key is an action id used by lineups
# type: "exe" -> launch executable (list: executable + args)
#       "opener" -> open folder/file via os.startfile (on Windows) or xdg-open/open
#       "cmd" -> run a command (list) via subprocess
# dangerous: if True, ask for confirmation
ACTION_WHITELIST = {
    "open_vscode": {
        "label": "Open VS Code",
        # prefer PATH entry "code" else fallback to explicit exe path (edit the fallback)
        "type": "exe",
        "cmd": ["code"],
        "fallback": r"C:\Users\you\AppData\Local\Programs\Microsoft VS Code\Code.exe",
        "dangerous": False,
    },
    "open_downloads": {
        "label": "Open Downloads folder",
        "type": "opener",
        "cmd": [os.path.expanduser("~/Downloads")],
        "dangerous": False,
    },
    "open_spotify": {
        "label": "Open Spotify",
        "type": "exe",
        # edit fallback to your install location if needed
        "cmd": ["spotify"],
        "fallback": r"C:\Users\hp\AppData\Local\Microsoft\WindowsApps\Spotify.exe",
        "dangerous": False,
    },
    # Wi-Fi enable/disable use netsh (Windows) - marked dangerous because it may require admin
    "wifi_on": {
        "label": "Turn ON Wi-Fi",
        "type": "cmd",
        "cmd": ["netsh", "interface", "set", "interface", WIFI_INTERFACE, "admin=enabled"],
        "dangerous": True,
    },
    "wifi_off": {
        "label": "Turn OFF Wi-Fi",
        "type": "cmd",
        "cmd": ["netsh", "interface", "set", "interface", WIFI_INTERFACE, "admin=disabled"],
        "dangerous": True,
    },
    "open_notepad": {
        "label": "Open Notepad",
        "type": "exe",
        "cmd": ["notepad"],
        "dangerous": False,
    },
    "open_taskmgr": {
        "label": "Open Task Manager",
        "type": "cmd",
        "cmd": ["taskmgr"],
        "dangerous": False,
    },
}

# Define the two lineups: lists of action ids
LINEUPS = {
    "Lineup 1 — Dev Start": ["open_vscode", "open_downloads", "wifi_on", "open_spotify"],
    "Lineup 2 — Quick Tools": ["open_notepad", "open_taskmgr", "wifi_off"],
}
# ----------------------------------------

# ----------------- Helpers -----------------
def resolve_exec_cmd(meta):
    """
    For type 'exe' try shutil.which first, else use fallback or provided cmd.
    Return a list suitable for subprocess or special handling for 'opener'.
    """
    if meta["type"] == "exe":
        base = meta["cmd"][0]
        # if base is a simple command name, try PATH lookup
        if os.path.sep not in base:
            path = shutil.which(base)
            if path:
                return [path] + meta["cmd"][1:]
        # fallback explicit path
        fallback = meta.get("fallback")
        if fallback and os.path.exists(fallback):
            return [fallback] + meta["cmd"][1:]
        # otherwise return original cmd (hoping it's runnable)
        return meta["cmd"]
    else:
        return meta["cmd"]

def run_single_action(action_id, log_widget):
    """
    Validate and execute a single action by id, writing output to log_widget.
    """
    meta = ACTION_WHITELIST.get(action_id)
    if not meta:
        append_log(log_widget, f"[REJECTED] Unknown action id: {action_id}\n")
        return

    label = meta.get("label", action_id)
    if meta.get("dangerous", False):
        # confirm before dangerous actions
        confirmed = messagebox.askokcancel("Confirm action", f"Action '{label}' is marked dangerous. Proceed?")
        if not confirmed:
            append_log(log_widget, f"[CANCELLED] {label}\n")
            return

    append_log(log_widget, f"[START] {label}\n")

    if DRY_RUN:
        append_log(log_widget, f"[DRY RUN] Would run: {meta}\n")
        append_log(log_widget, f"[END] {label}\n\n")
        return

    try:
        if meta["type"] == "opener":
            target = meta["cmd"][0]
            append_log(log_widget, f"Opening: {target}\n")
            if os.name == "nt":
                os.startfile(target)
            else:
                opener = "open" if os.uname().sysname == "Darwin" else "xdg-open"
                subprocess.Popen([opener, target], close_fds=True)
            append_log(log_widget, f"[OK] {label}\n\n")
            return

        cmd = resolve_exec_cmd(meta)

        # For simple GUI programs, Popen without waiting is fine (non-blocking)
        # For commands like netsh or taskmgr we also invoke Popen (they may spawn further processes).
        append_log(log_widget, f"Running command: {' '.join(cmd)}\n")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # stream output if any
        if p.stdout:
            for line in p.stdout:
                append_log(log_widget, line)
        p.wait()
        append_log(log_widget, f"[EXIT {p.returncode}] {label}\n\n")
    except FileNotFoundError:
        append_log(log_widget, f"[ERROR] Executable not found for action {label}\n\n")
    except PermissionError:
        append_log(log_widget, f"[ERROR] Permission denied executing {label}. Try running as admin.\n\n")
    except Exception as e:
        append_log(log_widget, f"[ERROR] {label}: {e}\n\n")

def append_log(widget, text):
    widget.configure(state="normal")
    widget.insert(tk.END, text)
    widget.see(tk.END)
    widget.configure(state="disabled")

def run_lineup(lineup_name, log_widget):
    """
    Run all actions in the lineup concurrently (each in its own thread).
    """
    actions = LINEUPS.get(lineup_name, [])
    append_log(log_widget, f"\n=== Starting lineup: {lineup_name} ===\n")
    threads = []
    for act in actions:
        t = threading.Thread(target=run_single_action, args=(act, log_widget), daemon=True)
        t.start()
        threads.append(t)
    # Optionally we can join if we want to wait; here we don't block UI.
    append_log(log_widget, f"=== Dispatched {len(threads)} actions for {lineup_name} ===\n\n")

# ----------------- GUI -----------------
class LineupsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lineups Executor")
        self.geometry("800x520")

        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        ttk.Label(left, text="Lineups").pack(anchor="nw")
        self.listbox = tk.Listbox(left, width=30, height=10)
        self.listbox.pack(pady=6)
        for name in LINEUPS.keys():
            self.listbox.insert(tk.END, name)

        execute_btn = ttk.Button(left, text="Run Lineup", command=self.on_run_lineup)
        execute_btn.pack(pady=4)

        clear_btn = ttk.Button(left, text="Clear Log", command=self.clear_log)
        clear_btn.pack(pady=4)

        right = ttk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(right, text="Log / Output").pack(anchor="nw")
        self.log = scrolledtext.ScrolledText(right, state="disabled", wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)

        # show action mapping button
        mapping_btn = ttk.Button(left, text="Show Actions", command=self.show_actions)
        mapping_btn.pack(pady=4)

    def on_run_lineup(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Pick a lineup", "Please select a lineup to run.")
            return
        name = self.listbox.get(sel[0])
        # run in separate thread to keep UI responsive
        threading.Thread(target=run_lineup, args=(name, self.log), daemon=True).start()

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="disabled")

    def show_actions(self):
        txt = "Whitelisted actions and commands:\n\n"
        for k, v in ACTION_WHITELIST.items():
            txt += f"{k}: {v.get('label')} -> {v.get('cmd')}\n"
        messagebox.showinfo("Actions", txt)

def main():
    app = LineupsApp()
    app.mainloop()

if __name__ == "__main__":
    main()
