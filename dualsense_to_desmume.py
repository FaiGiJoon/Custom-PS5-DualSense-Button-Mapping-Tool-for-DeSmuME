#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import threading
import time

# Default mappings for PS5 DualSense (DirectInput)
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
    prefix = f"Joypad{joystick_index + 1}"
    base_button = (joystick_index + 1) << 14
    base_hat = base_button | 0x0100
    
    result = {}
    for key, val in mappings.items():
        config_key = f"{prefix}.{key}"
        if val == "0":
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

def update_ini_file(ini_path, new_config_dict, joystick_index=0):
    if not os.path.exists(ini_path):
        return False, f"File not found: {ini_path}"

    prefix = f"Joypad{joystick_index + 1}."
    backup_path = ini_path + ".bak"
    try:
        shutil.copy2(ini_path, backup_path)
    except Exception as e:
        return False, f"Failed to create backup: {e}"

    try:
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
        return True, f"Successfully updated {ini_path}"
    except Exception as e:
        return False, f"Failed to update INI: {e}"

def is_desmume_running():
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'desmume' in proc.info['name'].lower():
                return True
    except ImportError:
        pass # psutil not available
    return False

class DualSenseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DeSmuME DualSense Sync Tool")
        self.root.geometry("500x550")

        import tkinter as tk
        from tkinter import filedialog, messagebox

        self.tk = tk
        self.filedialog = filedialog
        self.messagebox = messagebox

        # Styles
        self.bg_color = "#2c3e50"
        self.fg_color = "#ecf0f1"
        self.accent_color = "#3498db"
        self.root.configure(bg=self.bg_color)

        # UI Components
        title_label = tk.Label(root, text="DualSense ↔ DeSmuME Sync", font=("Helvetica", 18, "bold"),
                               bg=self.bg_color, fg=self.accent_color)
        title_label.pack(pady=20)

        # INI Selection
        ini_frame = tk.Frame(root, bg=self.bg_color)
        ini_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(ini_frame, text="DeSmuME INI Path:", bg=self.bg_color, fg=self.fg_color).pack(side="left")
        self.ini_path_var = tk.StringVar()
        self.ini_entry = tk.Entry(ini_frame, textvariable=self.ini_path_var, width=40)
        self.ini_entry.pack(side="left", padx=5)
        tk.Button(ini_frame, text="Browse", command=self.browse_ini).pack(side="left")

        # Joystick Index
        idx_frame = tk.Frame(root, bg=self.bg_color)
        idx_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(idx_frame, text="Player Slot:", bg=self.bg_color, fg=self.fg_color).pack(side="left")
        self.idx_var = tk.IntVar(value=0)
        tk.OptionMenu(idx_frame, self.idx_var, 0, 1, 2, 3).pack(side="left", padx=5)
        tk.Label(idx_frame, text="(0 = Player 1)", bg=self.bg_color, fg="#95a5a6", font=("Helvetica", 8)).pack(side="left")

        # Live Monitor
        monitor_frame = tk.LabelFrame(root, text="Live Controller Monitor", bg=self.bg_color, fg=self.fg_color, padx=10, pady=10)
        monitor_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.status_var = tk.StringVar(value="Waiting for input...")
        self.status_label = tk.Label(monitor_frame, textvariable=self.status_var, font=("Courier", 12),
                                     bg="#34495e", fg="#2ecc71", height=4, width=40)
        self.status_label.pack(pady=5)
        
        self.js_name_var = tk.StringVar(value="No controller detected")
        tk.Label(monitor_frame, textvariable=self.js_name_var, bg=self.bg_color, fg="#bdc3c7", font=("Helvetica", 9, "italic")).pack()

        # Action Buttons
        btn_frame = tk.Frame(root, bg=self.bg_color)
        btn_frame.pack(pady=20)

        self.sync_btn = tk.Button(btn_frame, text="SYNC TO DESMUME", font=("Helvetica", 12, "bold"),
                                  bg=self.accent_color, fg="white", padx=20, pady=10, command=self.sync)
        self.sync_btn.pack()

        # Pygame Init
        self.pygame_available = False
        try:
            import pygame
            self.pygame = pygame
            pygame.init()
            pygame.joystick.init()
            self.pygame_available = True
            self.poll_joystick()
        except ImportError:
            self.status_var.set("Install 'pygame' for live monitoring.")

    def browse_ini(self):
        filename = self.filedialog.askopenfilename(filetypes=[("INI files", "*.ini"), ("All files", "*.*")])
        if filename:
            self.ini_path_var.set(filename)

    def sync(self):
        ini_path = self.ini_path_var.get()
        if not ini_path:
            self.messagebox.showerror("Error", "Please select your desmume.ini file first.")
            return

        if is_desmume_running():
            if not self.messagebox.askyesno("DeSmuME is Running",
                                            "DeSmuME is currently open. It may overwrite settings on exit. \n\n"
                                            "Do you want to apply settings anyway? (Restart recommended)"):
                return

        config_dict = generate_config_dict(DEFAULT_MAPPINGS, self.idx_var.get())
        success, msg = update_ini_file(ini_path, config_dict, self.idx_var.get())

        if success:
            self.messagebox.showinfo("Success", msg)
        else:
            self.messagebox.showerror("Error", msg)

    def poll_joystick(self):
        if not self.pygame_available: return

        self.pygame.event.pump()
        count = self.pygame.joystick.get_count()

        if count > 0:
            try:
                js = self.pygame.joystick.Joystick(self.idx_var.get())
                if not js.get_init(): js.init()
                self.js_name_var.set(f"Detected: {js.get_name()}")

                base_button = (self.idx_var.get() + 1) << 14
                base_hat = base_button | 0x0100

                # Check buttons
                for i in range(js.get_numbuttons()):
                    if js.get_button(i):
                        hex_code = hex(base_button | i).upper().replace('X', 'x')
                        self.status_var.set(f"Button {i} pressed\nDeSmuME: {hex_code}")

                # Check hats
                for i in range(js.get_numhats()):
                    val = js.get_hat(i)
                    if val != (0, 0):
                        dir_str = ""
                        hat_hex = 0
                        if val == (0, 1): dir_str = "Up"; hat_hex = 0
                        elif val == (1, 0): dir_str = "Right"; hat_hex = 1
                        elif val == (0, -1): dir_str = "Down"; hat_hex = 2
                        elif val == (-1, 0): dir_str = "Left"; hat_hex = 3

                        if dir_str:
                            hex_code = hex(base_hat | hat_hex).upper().replace('X', 'x')
                            self.status_var.set(f"D-Pad {dir_str}\nDeSmuME: {hex_code}")
            except Exception:
                self.js_name_var.set(f"Waiting for Joystick {self.idx_var.get()}...")
        else:
            self.js_name_var.set("No joysticks detected")

        self.root.after(50, self.poll_joystick)

def run_test_mode(joystick_index=0):
    try:
        import pygame
    except ImportError:
        print("Error: 'pygame' is required for test mode.")
        return

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No joysticks detected.")
        return

    js = pygame.joystick.Joystick(joystick_index)
    js.init()
    print(f"Testing: {js.get_name()}")

    base_button = (joystick_index + 1) << 14
    base_hat = base_button | 0x0100

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    print(f"Button {event.button} -> {hex(base_button | event.button).upper().replace('X', 'x')}")
                elif event.type == pygame.JOYHATMOTION:
                    if event.value != (0, 0):
                        print(f"Hat {event.hat} {event.value} -> Mapping...")
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass

def main():
    parser = argparse.ArgumentParser(description="DeSmuME PS5 DualSense Sync Tool")
    parser.add_argument("--index", type=int, default=0, help="Joystick index")
    parser.add_argument("--ini", type=str, help="Path to desmume.ini")
    parser.add_argument("--test", action="store_true", help="CLI Test Mode")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode (no GUI)")

    args = parser.parse_args()

    if args.test:
        run_test_mode(args.index)
    elif args.ini or args.cli:
        # CLI Mode
        config_dict = generate_config_dict(DEFAULT_MAPPINGS, args.index)
        if args.ini:
            success, msg = update_ini_file(args.ini, config_dict, args.index)
            print(msg)
        else:
            for k, v in config_dict.items():
                print(f"{k}={v}")
    else:
        # GUI Mode
        import tkinter as tk
        root = tk.Tk()
        app = DualSenseGUI(root)
        root.mainloop()

if __name__ == "__main__":
    main()
