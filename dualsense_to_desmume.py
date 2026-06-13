#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import time
import math

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pygame
except ImportError:
    pygame = None

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    tk = None

# Default mappings for PS5 DualSense (DirectInput)
# Buttons start at 0x4000
# POV/Hats start at 0x4100
DEFAULT_MAPPINGS = {
    "A":      "0x4002", # Circle
    "B":      "0x4001", # Cross
    "X":      "0x4003", # Triangle
    "Y":      "0x4000", # Square
    "L":      "0x4004", # L1
    "R":      "0x4005", # R1
    "Start":  "0x4009", # Options
    "Select": "0x4008", # Create/Share
    "Up":     "0x4100", # D-Pad Up
    "Right":  "0x4101", # D-Pad Right
    "Down":   "0x4102", # D-Pad Down
    "Left":   "0x4103", # D-Pad Left
    "Debug":  "0",
    "Boost":  "0x4007", # R2 (Digital)
    "Lid":    "0x4006", # L2 (Digital)
}

def generate_config_dict(mappings, joystick_index=0):
    """
    Generates a dictionary of DeSmuME config keys and values.
    """
    prefix = f"Joypad{joystick_index + 1}"
    base_button = (joystick_index + 1) << 14
    base_hat = base_button | 0x0100
    
    result = {}
    for key, val in mappings.items():
        config_key = f"{prefix}.{key}"
        if val == "0" or val is None:
            result[config_key] = "0"
            continue

        if isinstance(val, str) and val.startswith("0x"):
            orig_val = int(val, 16)
            if orig_val >= 0x4100:
                new_val = base_hat | (orig_val & 0xFF)
            else:
                new_val = base_button | (orig_val & 0xFF)
            result[config_key] = hex(new_val).upper().replace('X', 'x')
        else:
            result[config_key] = str(val)

    return result

def find_desmume_ini():
    """
    Tries to find the desmume.ini file automatically.
    """
    if psutil:
        for proc in psutil.process_iter(['name', 'exe']):
            try:
                if proc.info['name'] and 'desmume' in proc.info['name'].lower():
                    exe_path = proc.info['exe']
                    if exe_path:
                        ini_path = os.path.join(os.path.dirname(exe_path), "desmume.ini")
                        if os.path.exists(ini_path):
                            return ini_path
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    for d in [".", ".."]:
        p = os.path.join(d, "desmume.ini")
        if os.path.exists(p):
            return os.path.abspath(p)
    return None

def update_ini_file(ini_path, new_config_dict, joystick_index=0):
    """
    Updates the [Joypad] section in the specified desmume.ini file.
    """
    if not ini_path or not os.path.exists(ini_path):
        return False, f"File not found: {ini_path}"

    prefix = f"Joypad{joystick_index + 1}."

    try:
        backup_path = ini_path + ".bak"
        shutil.copy2(ini_path, backup_path)

        with open(ini_path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        joypad_found = False
        in_joypad_section = False
        applied_keys = set()
        
        for line in lines:
            stripped = line.strip()
            if stripped == "[Joypad]":
                joypad_found = True
                in_joypad_section = True
                new_lines.append(line)
                continue

            if in_joypad_section:
                if stripped.startswith("["):
                    for k, v in new_config_dict.items():
                        if k not in applied_keys:
                            new_lines.append(f"{k}={v}\n")
                            applied_keys.add(k)
                    in_joypad_section = False
                    new_lines.append(line)
                elif "=" in stripped:
                    key = stripped.split("=")[0].strip()
                    if key.startswith(prefix):
                        if key in new_config_dict:
                            new_lines.append(f"{key}={new_config_dict[key]}\n")
                            applied_keys.add(key)
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if in_joypad_section:
            for k, v in new_config_dict.items():
                if k not in applied_keys:
                    new_lines.append(f"{k}={v}\n")
                    applied_keys.add(k)
        elif not joypad_found:
            new_lines.append("\n[Joypad]\n")
            for k, v in new_config_dict.items():
                new_lines.append(f"{k}={v}\n")

        with open(ini_path, 'w') as f:
            f.writelines(new_lines)

        return True, f"Successfully updated {ini_path}. Backup created at {backup_path}"
    except Exception as e:
        return False, f"Error updating INI: {str(e)}"

class DualSenseGui:
    def __init__(self, root):
        self.root = root
        self.root.title("D-SCRIBE 1.0 - DeSmuME DualSense Setup")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)

        self.mappings = DEFAULT_MAPPINGS.copy()
        self.listening_for = None
        self.record_sequence = []

        self.setup_ui()
        self.init_pygame()
        self.update_loop()

    def setup_ui(self):
        self.root.configure(bg="#1e1e1e")
        style = ttk.Style()
        style.theme_use('clam')

        # Colors
        bg_color = "#1e1e1e"
        fg_color = "#d4d4d4"
        sidebar_color = "#252526"
        accent_blue = "#007acc"
        accent_red = "#e74c3c"

        style.configure("TFrame", background=bg_color)
        style.configure("Sidebar.TFrame", background=sidebar_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.configure("Sidebar.TLabel", background=sidebar_color, foreground=fg_color, font=("Segoe UI", 10, "bold"))

        style.configure("TButton", background="#333333", foreground=fg_color, borderwidth=0, focuscolor=accent_blue)
        style.map("TButton",
                  background=[('active', '#444444'), ('disabled', '#252526')],
                  foreground=[('disabled', '#555555')])

        style.configure("Record.TButton", background=accent_red, foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Record.TButton", background=[('active', '#c0392b')])

        style.configure("Sync.TButton", background=accent_blue, foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Sync.TButton", background=[('active', '#005a9e')])

        style.configure("TLabelframe", background=bg_color, foreground=accent_blue)
        style.configure("TLabelframe.Label", background=bg_color, foreground=accent_blue, font=("Segoe UI", 10, "bold"))

        # Sidebar
        sidebar = ttk.Frame(self.root, width=180, style="Sidebar.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="D-SCRIBE 1.0", style="Sidebar.TLabel", font=("Segoe UI", 14, "bold"), padding=20).pack()

        self.record_btn = ttk.Button(sidebar, text="RECORD", style="Record.TButton", command=self.start_record_sequence)
        self.record_btn.pack(fill=tk.X, padx=20, pady=5)

        self.sync_btn = ttk.Button(sidebar, text="SYNC", style="Sync.TButton", command=self.apply_config)
        self.sync_btn.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(sidebar, text="DEVICES", style="Sidebar.TLabel", padding=(20, 30, 20, 5)).pack(anchor="w")
        self.joy_idx_var = tk.IntVar(value=0)
        self.joy_spin = tk.Spinbox(sidebar, from_=0, to=10, textvariable=self.joy_idx_var,
                                   command=self.on_joy_change, bg="#333333", fg="white",
                                   insertbackground="white", buttonbackground="#444444", width=5)
        self.joy_spin.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(sidebar, text="CONFIG", style="Sidebar.TLabel", padding=(20, 20, 20, 5)).pack(anchor="w")
        self.ini_path_var = tk.StringVar()
        detected = find_desmume_ini()
        if detected: self.ini_path_var.set(detected)
        ttk.Entry(sidebar, textvariable=self.ini_path_var).pack(fill=tk.X, padx=20, pady=2)
        ttk.Button(sidebar, text="Browse...", command=self.browse_ini).pack(fill=tk.X, padx=20, pady=2)

        # Main Content
        main_content = ttk.Frame(self.root, padding="20")
        main_content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.joy_name_var = tk.StringVar(value="Disconnected")
        ttk.Label(main_content, textvariable=self.joy_name_var, font=("Segoe UI", 12, "bold")).pack(anchor="w")

        grid_frame = ttk.Frame(main_content)
        grid_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        grid_frame.columnconfigure(0, weight=2)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)
        grid_frame.rowconfigure(1, weight=1)

        # Buttons
        btn_section = ttk.LabelFrame(grid_frame, text="BUTTONS", padding=10)
        btn_section.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.buttons = {}
        btn_keys = ["A", "B", "X", "Y", "L", "R", "Boost", "Lid", "Select", "Start", "Debug"]
        for i, key in enumerate(btn_keys):
            btn = ttk.Button(btn_section, text=key, command=lambda k=key: self.start_listening(k))
            btn.grid(row=i//3, column=i%3, sticky="nsew", padx=2, pady=2)
            self.buttons[key] = btn

        # D-Pad
        dpad_section = ttk.LabelFrame(grid_frame, text="D-PAD", padding=10)
        dpad_section.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        dpad_layout = ttk.Frame(dpad_section)
        dpad_layout.pack(expand=True)

        self.buttons["Up"] = ttk.Button(dpad_layout, text="▲", width=5, command=lambda: self.start_listening("Up"))
        self.buttons["Up"].grid(row=0, column=1, pady=2)
        self.buttons["Left"] = ttk.Button(dpad_layout, text="◀", width=5, command=lambda: self.start_listening("Left"))
        self.buttons["Left"].grid(row=1, column=0, padx=2)
        self.buttons["Right"] = ttk.Button(dpad_layout, text="▶", width=5, command=lambda: self.start_listening("Right"))
        self.buttons["Right"].grid(row=1, column=2, padx=2)
        self.buttons["Down"] = ttk.Button(dpad_layout, text="▼", width=5, command=lambda: self.start_listening("Down"))
        self.buttons["Down"].grid(row=2, column=1, pady=2)

        # Sticks
        sticks_section = ttk.LabelFrame(grid_frame, text="STICKS", padding=10)
        sticks_section.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        sticks_container = ttk.Frame(sticks_section)
        sticks_container.pack(expand=True)

        self.lstick_canvas = tk.Canvas(sticks_container, width=120, height=120, bg=bg_color, highlightthickness=0)
        self.lstick_canvas.pack(side=tk.LEFT, padx=40)
        self.draw_octagon(self.lstick_canvas)
        self.lstick_dot = self.lstick_canvas.create_oval(56, 56, 64, 64, fill=accent_red, outline="")
        ttk.Label(sticks_container, text="L-STICK").place(in_=self.lstick_canvas, relx=0.5, rely=0.9, anchor="n")

        self.rstick_canvas = tk.Canvas(sticks_container, width=120, height=120, bg=bg_color, highlightthickness=0)
        self.rstick_canvas.pack(side=tk.LEFT, padx=40)
        self.draw_octagon(self.rstick_canvas)
        self.rstick_dot = self.rstick_canvas.create_oval(56, 56, 64, 64, fill=accent_red, outline="")
        ttk.Label(sticks_container, text="R-STICK").place(in_=self.rstick_canvas, relx=0.5, rely=0.9, anchor="n")

        # Status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_content, textvariable=self.status_var, font=("Segoe UI", 9, "italic")).pack(side=tk.BOTTOM, fill=tk.X)

    def draw_octagon(self, canvas):
        c, r = 60, 50
        points = []
        for i in range(8):
            angle = math.radians(i * 45 + 22.5)
            points.extend([c + r * math.cos(angle), c + r * math.sin(angle)])
        canvas.create_polygon(points, fill="#252526", outline="#444444", width=2)
        canvas.create_line(c-r, c, c+r, c, fill="#333333")
        canvas.create_line(c, c-r, c, c+r, fill="#333333")

    def init_pygame(self):
        if pygame:
            pygame.init()
            pygame.joystick.init()
            self.refresh_joystick()
        else:
            self.joy_name_var.set("Pygame missing")

    def refresh_joystick(self):
        if not pygame: return
        pygame.joystick.quit()
        pygame.joystick.init()
        idx = self.joy_idx_var.get()
        if pygame.joystick.get_count() > idx:
            js = pygame.joystick.Joystick(idx)
            js.init()
            self.joy_name_var.set(f"Connected: {js.get_name()}")
        else:
            self.joy_name_var.set("No controller at this index")

    def on_joy_change(self):
        self.refresh_joystick()

    def browse_ini(self):
        path = filedialog.askopenfilename(filetypes=[("INI files", "*.ini"), ("All files", "*.*")])
        if path: self.ini_path_var.set(path)

    def start_listening(self, key):
        self.listening_for = key
        self.status_var.set(f"RECORDING: Press button for {key}...")
        for k, btn in self.buttons.items():
            btn.configure(state="disabled")

    def stop_listening(self):
        self.listening_for = None
        self.status_var.set("Ready")
        for k, btn in self.buttons.items():
            btn.configure(state="normal")
        if self.record_sequence:
            self.root.after(100, self.next_in_sequence)

    def start_record_sequence(self):
        self.record_sequence = ["B", "A", "Y", "X", "L", "R", "Lid", "Boost", "Select", "Start", "Up", "Down", "Left", "Right"]
        self.next_in_sequence()

    def next_in_sequence(self):
        if self.record_sequence:
            self.start_listening(self.record_sequence.pop(0))
        else:
            self.status_var.set("Recording complete")

    def apply_config(self):
        ini_path = self.ini_path_var.get()
        idx = self.joy_idx_var.get()
        config_dict = generate_config_dict(self.mappings, idx)
        success, msg = update_ini_file(ini_path, config_dict, idx)
        if success: messagebox.showinfo("Sync", msg)
        else: messagebox.showerror("Error", msg)

    def update_loop(self):
        if not pygame: return
        pygame.event.pump()

        idx = self.joy_idx_var.get()
        js = None
        if pygame.joystick.get_count() > idx:
            js = pygame.joystick.Joystick(idx)
            if not js.get_init(): js.init()

        # Input Events
        for event in pygame.event.get():
            if self.listening_for:
                if event.type == pygame.JOYBUTTONDOWN:
                    self.mappings[self.listening_for] = hex(0x4000 | event.button)
                    self.stop_listening()
                elif event.type == pygame.JOYHATMOTION and event.value != (0, 0):
                    v = event.value
                    h = 0x4100 if v == (0, 1) else 0x4101 if v == (1, 0) else 0x4102 if v == (0, -1) else 0x4103
                    self.mappings[self.listening_for] = hex(h)
                    self.stop_listening()

        # Visual Feedback
        if js:
            for key, btn in self.buttons.items():
                val = self.mappings.get(key)
                pressed = False
                if val and val.startswith("0x"):
                    code = int(val, 16)
                    if code >= 0x4100: # Hat
                        hv = js.get_hat(0)
                        d = code & 0xFF
                        if (d==0 and hv[1]==1) or (d==1 and hv[0]==1) or (d==2 and hv[1]==-1) or (d==3 and hv[0]==-1):
                            pressed = True
                    else: # Button
                        bid = code & 0xFF
                        if bid < js.get_numbuttons() and js.get_button(bid):
                            pressed = True

                if pressed: btn.configure(style="Record.TButton")
                elif key == self.listening_for: btn.configure(style="Sync.TButton")
                else: btn.configure(style="TButton")

            if js.get_numaxes() >= 4:
                lx, ly = js.get_axis(0), js.get_axis(1)
                rx, ry = js.get_axis(2), js.get_axis(5) if js.get_numaxes() > 5 else js.get_axis(3)
                self.lstick_canvas.coords(self.lstick_dot, 56 + lx*50, 56 + ly*50, 64 + lx*50, 64 + ly*50)
                self.rstick_canvas.coords(self.rstick_dot, 56 + rx*50, 56 + ry*50, 64 + rx*50, 64 + ry*50)

        self.root.after(16, self.update_loop)

def run_test_mode(joystick_index=0):
    if not pygame:
        print("Error: 'pygame' is required for test mode.")
        return
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() <= joystick_index:
        print(f"Error: No joystick at index {joystick_index}")
        return
    js = pygame.joystick.Joystick(joystick_index)
    js.init()
    print(f"\n--- Test Mode: {js.get_name()} ---")
    base = (joystick_index + 1) << 14
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    print(f"Button {event.button} -> {hex(base | event.button)}")
                elif event.type == pygame.JOYHATMOTION and event.value != (0, 0):
                    v = event.value
                    d = 0 if v == (0, 1) else 1 if v == (1, 0) else 2 if v == (0, -1) else 3
                    print(f"Hat -> {hex(base | 0x0100 | d)}")
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()

def main():
    parser = argparse.ArgumentParser(description="DeSmuME DualSense Configurator")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--ini", type=str)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--cli", action="store_true")
    args = parser.parse_args()

    if not (args.cli or args.test or args.ini) and tk:
        root = tk.Tk()
        DualSenseGui(root)
        root.mainloop()
    elif args.test:
        run_test_mode(args.index)
    else:
        config = generate_config_dict(DEFAULT_MAPPINGS, args.index)
        if args.ini:
            success, msg = update_ini_file(args.ini, config, args.index)
            print(msg)
        else:
            print("[Joypad]")
            for k, v in config.items(): print(f"{k}={v}")

if __name__ == "__main__":
    main()
