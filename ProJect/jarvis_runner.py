import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ------------------- CONFIG -------------------
# Predefined CMD commands (safe, non-destructive)
COMMANDS = {
    "Show Files (dir)": ["cmd", "/c", "dir"],
    "Show Network Info (ipconfig)": ["cmd", "/c", "ipconfig"],
    "Show Current User (whoami)": ["cmd", "/c", "whoami"],
    "List Tasks (tasklist)": ["cmd", "/c", "tasklist"],
    "Show System Info": ["cmd", "/c", "systeminfo"],
}
# ------------------------------------------------


def run_command(cmd, output_widget):
    """Runs the command in a thread and streams output."""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for line in proc.stdout:
            output_widget.configure(state="normal")
            output_widget.insert(tk.END, line)
            output_widget.see(tk.END)
            output_widget.configure(state="disabled")
        proc.wait()

        output_widget.configure(state="normal")
        output_widget.insert(tk.END, f"\n[Exit code: {proc.returncode}]\n\n")
        output_widget.configure(state="disabled")

    except Exception as e:
        output_widget.configure(state="normal")
        output_widget.insert(tk.END, f"\n[ERROR] {e}\n")
        output_widget.configure(state="disabled")


class CmdUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CMD Command Runner")
        self.geometry("750x450")

        # Left panel (commands)
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        ttk.Label(left, text="Select Command:").pack(anchor="w")

        self.listbox = tk.Listbox(left, width=30, height=20)
        self.listbox.pack(pady=5)

        for name in COMMANDS:
            self.listbox.insert(tk.END, name)

        exec_btn = ttk.Button(left, text="Execute", command=self.execute_command)
        exec_btn.pack(pady=5)

        clear_btn = ttk.Button(left, text="Clear Output", command=self.clear_output)
        clear_btn.pack(pady=5)

        # Right panel (output)
        right = ttk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(right, text="Output:").pack(anchor="w")
        self.output = scrolledtext.ScrolledText(right, wrap=tk.WORD, state="disabled")
        self.output.pack(fill=tk.BOTH, expand=True)

    def clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.configure(state="disabled")

    def execute_command(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("Select Something", "Please pick a command.")
            return

        cmd_name = self.listbox.get(sel[0])
        cmd = COMMANDS.get(cmd_name)

        self.output.configure(state="normal")
        self.output.insert(tk.END, f"\n=== Running: {cmd_name} ===\n")
        self.output.configure(state="disabled")

        threading.Thread(
            target=run_command,
            args=(cmd, self.output),
            daemon=True
        ).start()


if __name__ == "__main__":
    app = CmdUI()
    app.mainloop()
