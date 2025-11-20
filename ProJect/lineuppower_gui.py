import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ---------------- CONFIG ----------------
DRY_RUN = False

# Wi-Fi adapter name for PowerShell toggle
WIFI_INTERFACE = "Wi-Fi"   # change if needed

# Each action is a PowerShell command
ACTION_WHITELIST = {
    "open_vscode": {
        "label": "Open VS Code",
        "type": "ps",
        "cmd": "Start-Process code",
        "dangerous": False,
    },
    "open_downloads": {
        "label": "Open Downloads",
        "type": "ps",
        "cmd": f"Start-Process '{os.path.expanduser('~/Downloads')}'",
        "dangerous": False,
    },
    "open_spotify": {
        "label": "Open Spotify",
        "type": "ps",
        "cmd": "Start-Process spotify",
        "dangerous": False,
    },
    "wifi_on": {
        "label": "Turn ON Wi-Fi",
        "type": "ps",
        "cmd": f"Set-NetAdapter -Name '{WIFI_INTERFACE}' -Enabled $true",
        "dangerous": True,
    },
    "wifi_off": {
        "label": "Turn OFF Wi-Fi",
        "type": "ps",
        "cmd": f"Set-NetAdapter -Name '{WIFI_INTERFACE}' -Enabled $false",
        "dangerous": True,
    },
    "open_notepad": {
        "label": "Open Notepad",
        "type": "ps",
        "cmd": "Start-Process notepad",
        "dangerous": False,
    },
    "open_taskmgr": {
        "label": "Open Task Manager",
        "type": "ps",
        "cmd": "Start-Process taskmgr",
        "dangerous": False,
    },
}

LINEUPS = {
    "Lineup 1 — Main Squad": ["open_vscode", "open_downloads", "wifi_on", "open_spotify"],
    "Lineup 2 — Team B": ["open_notepad", "open_taskmgr", "wifi_off"],
}

# ----------------------------------------

def append_log(widget, text):
    widget.configure(state="normal")
    widget.insert(tk.END, text)
    widget.see(tk.END)
    widget.configure(state="disabled")


def run_single_action(action_id, log_widget):
    meta = ACTION_WHITELIST.get(action_id)
    if not meta:
        append_log(log_widget, f"[INVALID ACTION] {action_id}\n")
        return

    label = meta["label"]

    if meta["dangerous"]:
        ok = messagebox.askokcancel("Confirm", f"Run dangerous action: {label}?")
        if not ok:
            append_log(log_widget, f"[CANCELLED] {label}\n")
            return

    append_log(log_widget, f"\n[START] {label}\n")

    if DRY_RUN:
        append_log(log_widget, f"[DRY RUN] Would run: {meta['cmd']}\n")
        append_log(log_widget, f"[END] {label}\n")
        return

    # Build PowerShell command
    ps_cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", meta["cmd"]
    ]

    try:
        proc = subprocess.Popen(
            ps_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in proc.stdout:
            append_log(log_widget, line)

        proc.wait()
        append_log(log_widget, f"[EXIT {proc.returncode}] {label}\n")

    except Exception as e:
        append_log(log_widget, f"[ERROR] {label}: {e}\n")


def run_lineup(name, log_widget):
    append_log(log_widget, f"\n=== Running Lineup: {name} ===\n")
    for action in LINEUPS[name]:
        threading.Thread(
            target=run_single_action,
            args=(action, log_widget),
            daemon=True
        ).start()


# ---------------- GUI ----------------
class LineupGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PowerShell Lineup Executor")
        self.geometry("800x500")

        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        ttk.Label(left, text="Available Lineups").pack(anchor="w")

        self.listbox = tk.Listbox(left, width=30, height=10)
        self.listbox.pack(pady=5)

        for name in LINEUPS.keys():
            self.listbox.insert(tk.END, name)

        ttk.Button(left, text="Run Lineup", command=self.execute).pack(pady=5)
        ttk.Button(left, text="Clear Log", command=self.clear_log).pack(pady=5)

        right = ttk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(right, text="Output Log").pack(anchor="w")
        self.log = scrolledtext.ScrolledText(right, wrap=tk.WORD, state="disabled")
        self.log.pack(fill=tk.BOTH, expand=True)

    def execute(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Choose a lineup.")
            return

        name = self.listbox.get(sel[0])
        threading.Thread(target=run_lineup, args=(name, self.log), daemon=True).start()

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="disabled")


if __name__ == "__main__":
    LineupGUI().mainloop()
