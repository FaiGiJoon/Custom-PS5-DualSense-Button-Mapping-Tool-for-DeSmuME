#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import threading
import time

try:
    import psutil
except ImportError:
    psutil = None

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
    joystick_index: The hardware joystick index (0, 1, 2...)
    Joypad prefix is also derived from joystick_index (Joypad1, Joypad2...)
    """
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

def run_test_mode(joystick_index=0):
    """
    Initializes pygame and listens for joystick events to display
    the DeSmuME hex codes for buttons and hats.
    """
    try:
        import pygame
    except ImportError:
        print("Error: 'pygame' is required for test mode.")
        print("Install it with: pip install pygame")
        return

    pygame.init()
    pygame.joystick.init()

    joystick_count = pygame.joystick.get_count()
    if joystick_count == 0:
        print("Error: No joysticks detected.")
        return

    if joystick_index >= joystick_count:
        print(f"Error: Joystick index {joystick_index} out of range. Only {joystick_count} detected.")
        return

    js = pygame.joystick.Joystick(joystick_index)
    js.init()

    print(f"\n--- Test Mode: {js.get_name()} (Index {joystick_index}) ---")
    print("Press buttons on your controller to see their DeSmuME hex codes.")
    print("Press Ctrl+C to exit.\n")

    base_button = (joystick_index + 1) << 14
    base_hat = base_button | 0x0100

    try:
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.JOYBUTTONDOWN:
                    btn_id = event.button
                    hex_code = hex(base_button | btn_id).upper().replace('X', 'x')
                    print(f"Button {btn_id} pressed  -> DeSmuME Code: {hex_code}")
                elif event.type == pygame.JOYHATMOTION:
                    hat_id, value = event.hat, event.value
                    if value != (0, 0):
                        direction = ""
                        hat_hex = 0
                        if value == (0, 1): direction = "Up"; hat_hex = 0
                        elif value == (1, 0): direction = "Right"; hat_hex = 1
                        elif value == (0, -1): direction = "Down"; hat_hex = 2
                        elif value == (-1, 0): direction = "Left"; hat_hex = 3

                        if direction:
                            hex_code = hex(base_hat | hat_hex).upper().replace('X', 'x')
                            print(f"Hat {hat_id} {direction}  -> DeSmuME Code: {hex_code}")

            clock.tick(60)
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()

def find_desmume_ini():
    """
    Tries to find the desmume.ini file automatically.
    """
    # 1. Try to find running DeSmuME process
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

    # 2. Check current and parent directories
    search_dirs = [".", ".."]
    for d in search_dirs:
        p = os.path.join(d, "desmume.ini")
        if os.path.exists(p):
            return os.path.abspath(p)

    return None

class DualSenseGui:
    def __init__(self, root):
        self.root = root
        self.root.title("DeSmuME DualSense Setup")
        self.root.geometry("600x700")

        self.joystick_index = 0
        self.mappings = DEFAULT_MAPPINGS.copy()
        self.listening_for = None # Key we are currently mapping

        self.setup_ui()
        self.init_pygame()
        self.update_loop()

    def setup_ui(self):
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox

        # Main Layout
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # INI Selection
        ini_frame = ttk.LabelFrame(main_frame, text="DeSmuME Configuration", padding="5")
        ini_frame.pack(fill=tk.X, pady=5)

        self.ini_path_var = tk.StringVar()
        detected = find_desmume_ini()
        if detected:
            self.ini_path_var.set(detected)

        ttk.Entry(ini_frame, textvariable=self.ini_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(ini_frame, text="Browse", command=self.browse_ini).pack(side=tk.LEFT, padx=2)
        ttk.Button(ini_frame, text="Auto-Detect", command=self.auto_detect_ini).pack(side=tk.LEFT, padx=2)

        # Joystick Selection
        joy_frame = ttk.Frame(main_frame, padding="5")
        joy_frame.pack(fill=tk.X)
        ttk.Label(joy_frame, text="Joystick Index:").pack(side=tk.LEFT)
        self.joy_idx_var = tk.IntVar(value=0)
        ttk.Spinbox(joy_frame, from_=0, to=10, textvariable=self.joy_idx_var, width=5, command=self.on_joy_change).pack(side=tk.LEFT, padx=5)
        self.joy_name_var = tk.StringVar(value="Checking controllers...")
        ttk.Label(joy_frame, textvariable=self.joy_name_var, foreground="blue").pack(side=tk.LEFT)

        # Mapping Grid
        map_frame = ttk.LabelFrame(main_frame, text="Button Mappings (Click to Re-map)", padding="10")
        map_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.buttons = {}
        row, col = 0, 0
        for key in self.mappings.keys():
            btn = ttk.Button(map_frame, text=f"{key}: {self.mappings[key]}", command=lambda k=key: self.start_listening(k))
            btn.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
            self.buttons[key] = btn
            col += 1
            if col > 2:
                col = 0
                row += 1

        for i in range(3):
            map_frame.columnconfigure(i, weight=1)

        # Troubleshooting
        ts_frame = ttk.LabelFrame(main_frame, text="Troubleshooting", padding="5")
        ts_frame.pack(fill=tk.X, pady=5)
        ts_text = (
            "• If nothing happens: Run DeSmuME as Admin / Reconnect controller.\n"
            "• Use DS4Windows to emulate Xbox controller if DirectInput fails.\n"
            "• Bluetooth can be buggy; USB is more stable on some systems."
        )
        ttk.Label(ts_frame, text=ts_text, justify=tk.LEFT).pack(fill=tk.X)

        # Actions
        btn_frame = ttk.Frame(main_frame, padding="10")
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Apply to desmume.ini", command=self.apply_config).pack(side=tk.RIGHT, padx=5)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(btn_frame, textvariable=self.status_var).pack(side=tk.LEFT)

    def init_pygame(self):
        import pygame
        pygame.init()
        pygame.joystick.init()
        self.refresh_joystick()

    def refresh_joystick(self):
        import pygame
        pygame.joystick.quit()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        idx = self.joy_idx_var.get()
        if count > idx:
            js = pygame.joystick.Joystick(idx)
            js.init()
            self.joy_name_var.set(f"Connected: {js.get_name()}")
        else:
            self.joy_name_var.set("No controller detected at this index")

    def on_joy_change(self):
        self.refresh_joystick()

    def browse_ini(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("INI files", "*.ini"), ("All files", "*.*")])
        if path:
            self.ini_path_var.set(path)

    def auto_detect_ini(self):
        from tkinter import messagebox
        path = find_desmume_ini()
        if path:
            self.ini_path_var.set(path)
        else:
            messagebox.showinfo("Auto-Detect", "Could not find desmume.ini automatically.")

    def start_listening(self, key):
        self.listening_for = key
        self.status_var.set(f"Listening for {key}... Press a button on controller")
        for k, btn in self.buttons.items():
            btn.configure(state="disabled")

    def stop_listening(self):
        self.listening_for = None
        self.status_var.set("Ready")
        for k, btn in self.buttons.items():
            btn.configure(state="normal")
        self.update_button_texts()

    def update_button_texts(self):
        for key, val in self.mappings.items():
            self.buttons[key].configure(text=f"{key}: {val}")

    def apply_config(self):
        from tkinter import messagebox
        ini_path = self.ini_path_var.get()
        idx = self.joy_idx_var.get()
        config_dict = generate_config_dict(self.mappings, idx)
        success, msg = update_ini_file(ini_path, config_dict, idx)
        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)

    def update_loop(self):
        try:
            import pygame
        except ImportError:
            return

        if self.listening_for:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    # Buttons should be 0x4000 + btn_id
                    btn_hex = hex(0x4000 | event.button)
                    self.mappings[self.listening_for] = btn_hex
                    self.stop_listening()
                elif event.type == pygame.JOYHATMOTION:
                    hat_id, value = event.hat, event.value
                    if value != (0, 0):
                        hat_hex = 0
                        if value == (0, 1): hat_hex = 0x4100
                        elif value == (1, 0): hat_hex = 0x4101
                        elif value == (0, -1): hat_hex = 0x4102
                        elif value == (-1, 0): hat_hex = 0x4103

                        if hat_hex:
                            self.mappings[self.listening_for] = hex(hat_hex)
                            self.stop_listening()
        else:
            # Just clear the event queue
            pygame.event.get()

        self.root.after(10, self.update_loop)

def update_ini_file(ini_path, new_config_dict, joystick_index=0):
    """
    Updates the [Joypad] section in the specified desmume.ini file.
    Only replaces keys for the specific Joypad (e.g., Joypad1.*).
    Creates a backup before modifying.
    Returns (success: bool, message: str)
    """
    if not ini_path or not os.path.exists(ini_path):
        return False, f"File not found: {ini_path}"

    prefix = f"Joypad{joystick_index + 1}."

    try:
        # Create backup
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
                    # End of Joypad section. Add any missing keys before leaving.
                    for k, v in new_config_dict.items():
                        if k not in applied_keys:
                            new_lines.append(f"{k}={v}\n")
                            applied_keys.add(k)
                    in_joypad_section = False
                    new_lines.append(line)
                elif "=" in stripped:
                    key = stripped.split("=")[0].strip()
                    if key.startswith(prefix):
                        # Replace existing key if it matches our Joypad prefix
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

        # If we reached EOF while in Joypad section, or section never found
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

def main():
    parser = argparse.ArgumentParser(description="DeSmuME PS5 DualSense Configuration Generator")
    parser.add_argument("--index", type=int, default=0, help="Joystick index (0 for Player 1, 1 for Player 2, etc.)")
    parser.add_argument("--ini", type=str, help="Path to desmume.ini to update")
    parser.add_argument("--test", action="store_true", help="Run in test mode to identify button IDs")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode (default is GUI)")

    args = parser.parse_args()

    # Default to GUI if no CLI-specific args are used, unless --cli is specified
    is_cli = args.cli or args.test or args.ini

    if not is_cli:
        try:
            import tkinter as tk
            root = tk.Tk()
            gui = DualSenseGui(root)
            root.mainloop()
            return
        except ImportError:
            print("Tkinter not available. Falling back to CLI.")
        except Exception as e:
            print(f"Failed to start GUI: {e}. Falling back to CLI.")

    if args.test:
        run_test_mode(args.index)
        return

    config_dict = generate_config_dict(DEFAULT_MAPPINGS, args.index)

    if args.ini:
        success, msg = update_ini_file(args.ini, config_dict, args.index)
        print(msg)
    else:
        print(f"\n[Joypad]  # Mappings for Joypad{args.index + 1}")
        for k, v in config_dict.items():
            print(f"{k}={v}")
        print("\nInstructions:")
        print("1. Copy the lines above.")
        print("2. Paste them into your desmume.ini file under the [Joypad] section.")
        print("   OR run with --ini path/to/desmume.ini to update automatically.")

if __name__ == "__main__":
    main()
