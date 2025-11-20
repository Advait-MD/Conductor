"""
jarvis_runner.py

Simple Tkinter GUI that lists predefined commands. Selecting a command executes it
safely (no shell=True) and streams stdout/stderr to a text box.

Works on Windows/Linux/macOS (some parts Windows-specific like os.startfile).
Edit COMMAND_WHITELIST to add/remove commands and tune behavior.
"""

import os
import subprocess
import shutil
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

# ------------------ CONFIG ------------------
DRY_RUN = False  # True = show what would run, don't actually execute

# Map friendly command names to execution metadata.
# Each value is a dict:
#  - "type": "exe" | "opener" | "powershell" | "cmd" | "custom"
#  - "cmd": list -> the argument list to pass to subprocess (or function for "custom")
#  - "requires_confirm": bool -> whether to ask before running
#
# Examples below assume Windows paths; change to your paths or use shutil.which.
COMMAND_WHITELIST = {
    "Open VS Code": {
        "type": "exe",
        "cmd": ["code"],  # prefer PATH binary; will try shutil.which
        "requires_confirm": False
    },
    "Open Spotify": {
        "type": "exe",
        "cmd": [r"C:\Users\you\AppData\Roaming\Spotify\Spotify.exe"],  # fallback explicit exe
        "requires_confirm": False
    },
    "List Projects (PowerShell)": {
        "type": "powershell",
        "cmd": ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-ChildItem -Path C:\\Users\\you\\Projects -Directory | Select Name | ConvertTo-Json"],
        "requires_confirm": False
    },
    "Cleanup Temp (DANGEROUS)": {
        "type": "powershell",
        "cmd": ["powershell", "-NoProfile", "-Command",
                "Remove-Item -Path C:\\Temp\\* -Recurse -Force"],
        "requires_confirm": True
    },
    "Open Downloads Folder": {
        "type": "opener",
        "cmd": [os.path.expanduser("~/Downloads")],
        "requires_confirm": False
    }
}
# --------------------------------------------

# Utility to resolve executable (prefer PATH binary when a simple name given)
def resolve_cmd(meta):
    if meta["type"] == "exe":
        first = meta["cmd"][0]
        # if it's a single-name like "code", try shutil.which
        if os.path.sep not in first:
            path = shutil.which(first)
            if path:
                return [path] + meta["cmd"][1:]
            # else fall back to provided (maybe absolute)
        return meta["cmd"]
    return meta["cmd"]

# Executor thread function: runs command and streams output to text widget
def run_command(meta, output_widget):
    if DRY_RUN:
        output_widget_insert(output_widget, f"[DRY RUN] Would run: {meta['cmd']}\n")
        return

    typ = meta["type"]
    cmd = resolve_cmd(meta)

    try:
        if typ == "opener":
            # open folder or file using OS association
            target = cmd[0]
            output_widget_insert(output_widget, f"Opening: {target}\n")
            if os.name == "nt":
                os.startfile(target)
            else:
                # macOS: open <path>, Linux: xdg-open <path>
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, target], close_fds=True)
            return

        # For PowerShell / custom long commands, we capture output
        output_widget_insert(output_widget, f"Executing: {' '.join(cmd)}\n\n")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        # stream output line by line
        for line in proc.stdout:
            output_widget_insert(output_widget, line)
        proc.wait()
        output_widget_insert(output_widget, f"\n[Process exited with code {proc.returncode}]\n\n")
    except FileNotFoundError:
        output_widget_insert(output_widget, f"[ERROR] Executable not found: {cmd[0]}\n")
    except Exception as e:
        output_widget_insert(output_widget, f"[ERROR] {e}\n")

def output_widget_insert(widget, text):
    widget.configure(state="normal")
    widget.insert(tk.END, text)
    widget.see(tk.END)
    widget.configure(state="disabled")

# GUI wiring
class JarvisRunner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jarvis Runner - Predefined Commands")
        self.geometry("800x500")

        # Left pane: list of commands
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        ttk.Label(left, text="Predefined Commands").pack(anchor="nw")
        self.cmd_list = tk.Listbox(left, width=30, height=20)
        self.cmd_list.pack(side=tk.TOP, fill=tk.Y, expand=False, padx=4, pady=4)

        for name in COMMAND_WHITELIST.keys():
            self.cmd_list.insert(tk.END, name)

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=(6,0))
        exec_btn = ttk.Button(btn_frame, text="Execute", command=self.on_execute)
        exec_btn.pack(side=tk.LEFT, padx=2)
        refresh_btn = ttk.Button(btn_frame, text="Refresh", command=self.refresh_list)
        refresh_btn.pack(side=tk.LEFT, padx=2)
        clear_btn = ttk.Button(btn_frame, text="Clear Log", command=self.clear_log)
        clear_btn.pack(side=tk.LEFT, padx=2)

        # Right pane: output log
        right = ttk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        ttk.Label(right, text="Output / Log").pack(anchor="nw")
        self.output = scrolledtext.ScrolledText(right, state="disabled", wrap=tk.WORD)
        self.output.pack(fill=tk.BOTH, expand=True)

        # Bottom: status
        self.status = ttk.Label(self, text="Ready", relief=tk.SUNKEN, anchor="w")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def refresh_list(self):
        # placeholder if you later want to dynamically refresh commands
        self.status.config(text="Command list refreshed")

    def clear_log(self):
        self.output.configure(state="normal")
        self.output.delete(1.0, tk.END)
        self.output.configure(state="disabled")
        self.status.config(text="Log cleared")

    def on_execute(self):
        sel = self.cmd_list.curselection()
        if not sel:
            messagebox.showinfo("No selection", "Please pick a command from the list.")
            return
        name = self.cmd_list.get(sel[0])
        meta = COMMAND_WHITELIST.get(name)
        if not meta:
            messagebox.showerror("Not allowed", "Selected command is not whitelisted.")
            return

        # confirmation for dangerous commands
        if meta.get("requires_confirm"):
            ok = messagebox.askokcancel("Confirm action", f"The command '{name}' is marked dangerous. Proceed?")
            if not ok:
                self.status.config(text="Command cancelled")
                return

        # run in thread
        self.status.config(text=f"Running: {name}")
        t = threading.Thread(target=self._threaded_run, args=(meta, name), daemon=True)
        t.start()

    def _threaded_run(self, meta, name):
        try:
            # attach a small heading
            output_widget_insert(self.output, f"\n=== Running: {name} ===\n")
            run_command(meta, self.output)
            output_widget_insert(self.output, f"=== Finished: {name} ===\n")
            self.status.config(text=f"Finished: {name}")
        except Exception as e:
            output_widget_insert(self.output, f"[ERROR-THREAD] {e}\n")
            self.status.config(text=f"Error running: {name}")

if __name__ == "__main__":
    app = JarvisRunner()
    app.mainloop()
