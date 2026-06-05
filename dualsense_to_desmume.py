#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import time

try:
    import pygame
except ImportError:
    pygame = None

try:
    import psutil
except ImportError:
    psutil = None

import tkinter as tk
from tkinter import filedialog, messagebox

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

def find_desmume_process():
    """
    Attempts to find a running DeSmuME process and returns its executable path.
    """
    if not psutil:
        return None

    for proc in psutil.process_iter(['name', 'exe']):
        try:
            name = proc.info['name'].lower()
            if 'desmume' in name:
                return proc.info['exe']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def find_desmume_ini(exe_path=None):
    """
    Tries to locate desmume.ini. If exe_path is provided, checks that directory.
    Otherwise, checks common locations.
    """
    search_paths = []
    if exe_path:
        search_paths.append(os.path.dirname(exe_path))

    # Common locations (Windows-centric as DeSmuME is primarily Windows)
    search_paths.extend([
        os.getcwd(),
        os.path.expanduser("~"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "DeSmuME"),
    ])

    for path in search_paths:
        if not path: continue
        ini_file = os.path.join(path, "desmume.ini")
        if os.path.exists(ini_file):
            return ini_file
    return None

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

def update_ini_file(ini_path, new_config_dict, joystick_index=0):
    """
    Updates the [Joypad] section in the specified desmume.ini file.
    Only replaces keys for the specific Joypad (e.g., Joypad1.*).
    Creates a backup before modifying.
    """
    if not os.path.exists(ini_path):
        return False, f"Error: File not found: {ini_path}"

    prefix = f"Joypad{joystick_index + 1}."

    # Create backup
    backup_path = ini_path + ".bak"
    try:
        shutil.copy2(ini_path, backup_path)
    except Exception as e:
        return False, f"Failed to create backup: {e}"

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

    if in_joypad_section:
        for k, v in new_config_dict.items():
            if k not in applied_keys:
                new_lines.append(f"{k}={v}\n")
                applied_keys.add(k)
    elif not joypad_found:
        new_lines.append("\n[Joypad]\n")
        for k, v in new_config_dict.items():
            new_lines.append(f"{k}={v}\n")

    try:
        with open(ini_path, 'w') as f:
            f.writelines(new_lines)
    except Exception as e:
        return False, f"Failed to write to INI: {e}"

    return True, f"Successfully updated {ini_path} (Prefix: {prefix[:-1]})"

class DeSmuMEConfigGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DeSmuME PS5 DualSense Configurator")
        self.root.geometry("500x450")

        self.ini_path = tk.StringVar()
        self.joystick_index = tk.IntVar(value=0)
        self.status_msg = tk.StringVar(value="Waiting for input...")
        self.desmume_running = False

        self.setup_ui()
        self.init_pygame()
        self.auto_detect()
        self.update_loop()

    def setup_ui(self):
        # INI Selection
        tk.Label(self.root, text="DeSmuME INI Path:", font=("Arial", 10, "bold")).pack(pady=(10, 0))
        path_frame = tk.Frame(self.root)
        path_frame.pack(fill="x", padx=20)
        tk.Entry(path_frame, textvariable=self.ini_path).pack(side="left", fill="x", expand=True)
        tk.Button(path_frame, text="Browse", command=self.browse_ini).pack(side="right", padx=(5, 0))

        # Joystick Selection
        tk.Label(self.root, text="Controller Slot:", font=("Arial", 10, "bold")).pack(pady=(10, 0))
        joy_frame = tk.Frame(self.root)
        joy_frame.pack()
        for i in range(4):
            tk.Radiobutton(joy_frame, text=f"Player {i+1}", variable=self.joystick_index, value=i).pack(side="left")

        # Feedback Area
        tk.Label(self.root, text="Controller Feedback:", font=("Arial", 10, "bold")).pack(pady=(10, 0))
        self.feedback_canvas = tk.Canvas(self.root, width=400, height=150, bg="#f0f0f0", highlightthickness=1, highlightbackground="#ccc")
        self.feedback_canvas.pack(pady=5)
        self.input_text = self.feedback_canvas.create_text(200, 75, text="Press any button...", font=("Arial", 12))

        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Apply Configuration", command=self.apply_config, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Auto-Detect", command=self.auto_detect).pack(side="left", padx=5)

        # Status
        tk.Label(self.root, textvariable=self.status_msg, fg="blue").pack(pady=5)

    def init_pygame(self):
        if not pygame:
            self.status_msg.set("Pygame not found. Visual feedback disabled.")
            return
        pygame.init()
        pygame.joystick.init()
        self.js = None
        self.refresh_joystick()

    def refresh_joystick(self):
        if not pygame: return
        pygame.joystick.quit()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        if count > self.joystick_index.get():
            self.js = pygame.joystick.Joystick(self.joystick_index.get())
            self.js.init()
            self.status_msg.set(f"Connected: {self.js.get_name()}")
        else:
            self.js = None
            self.status_msg.set(f"No controller detected for Player {self.joystick_index.get()+1}")

    def browse_ini(self):
        path = filedialog.askopenfilename(filetypes=[("INI files", "*.ini"), ("All files", "*.*")])
        if path:
            self.ini_path.set(path)

    def auto_detect(self):
        exe_path = find_desmume_process()
        if exe_path:
            self.desmume_running = True
            self.status_msg.set("DeSmuME is currently running!")
        else:
            self.desmume_running = False

        ini = find_desmume_ini(exe_path)
        if ini:
            self.ini_path.set(ini)
            if not self.desmume_running:
                self.status_msg.set(f"Found INI: {ini}")
        else:
            if not self.ini_path.get():
                self.status_msg.set("Could not find desmume.ini. Please browse manually.")

    def apply_config(self):
        path = self.ini_path.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Error", "Please select a valid desmume.ini file.")
            return

        if self.desmume_running:
            confirm = messagebox.askyesno("DeSmuME Running",
                "DeSmuME is currently running. It may overwrite the INI file when it closes. "
                "It's recommended to close DeSmuME first. Do you want to proceed anyway?")
            if not confirm:
                return

        config_dict = generate_config_dict(DEFAULT_MAPPINGS, self.joystick_index.get())
        success, msg = update_ini_file(path, config_dict, self.joystick_index.get())

        if success:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)

    def update_loop(self):
        # Update Controller Feedback
        if pygame:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    self.feedback_canvas.itemconfig(self.input_text, text=f"Button {event.button} Pressed")
                elif event.type == pygame.JOYHATMOTION:
                    if event.value != (0, 0):
                        self.feedback_canvas.itemconfig(self.input_text, text=f"D-Pad {event.value}")

            # Periodically check if joystick index changed
            if not self.js or self.js.get_id() != self.joystick_index.get():
                self.refresh_joystick()

        # Check DeSmuME process periodically
        exe_path = find_desmume_process()
        was_running = self.desmume_running
        self.desmume_running = (exe_path is not None)
        if self.desmume_running and not was_running:
            self.status_msg.set("DeSmuME is running (Real-time sync active)")
        elif not self.desmume_running and was_running:
             self.status_msg.set("DeSmuME closed.")

        self.root.after(100, self.update_loop)

def run_test_mode(joystick_index=0):
    """
    Initializes pygame and listens for joystick events to display
    the DeSmuME hex codes for buttons and hats.
    """
    if not pygame:
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

def main():
    parser = argparse.ArgumentParser(description="DeSmuME PS5 DualSense Configuration Generator")
    parser.add_argument("--index", type=int, default=0, help="Joystick index (0 for Player 1, 1 for Player 2, etc.)")
    parser.add_argument("--ini", type=str, help="Path to desmume.ini to update")
    parser.add_argument("--test", action="store_true", help="Run in test mode to identify button IDs")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode")

    args = parser.parse_args()

    # If no arguments are provided, or if CLI is not forced, try to start GUI
    if len(sys.argv) == 1 or (not args.cli and not args.ini and not args.test):
        root = tk.Tk()
        app = DeSmuMEConfigGUI(root)
        root.mainloop()
        return

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
