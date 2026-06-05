#!/usr/bin/env python3
import argparse
import os
import shutil
import sys

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

def update_ini_file(ini_path, new_config_dict, joystick_index=0):
    """
    Updates the [Joypad] section in the specified desmume.ini file.
    Only replaces keys for the specific Joypad (e.g., Joypad1.*).
    Creates a backup before modifying.
    """
    if not os.path.exists(ini_path):
        print(f"Error: File not found: {ini_path}")
        return False

    prefix = f"Joypad{joystick_index + 1}."

    # Create backup
    backup_path = ini_path + ".bak"
    shutil.copy2(ini_path, backup_path)
    print(f"Backup created at: {backup_path}")

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
                        # Key exists in INI but not in our mapping, keep it?
                        # Actually if it's Joypad1.Something we don't know, maybe we should keep it.
                        new_lines.append(line)
                else:
                    # Key for another Joypad, keep it
                    new_lines.append(line)
            else:
                # Comment or empty line in Joypad section
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
        print("Warning: [Joypad] section not found in INI. Appending to end.")
        new_lines.append("\n[Joypad]\n")
        for k, v in new_config_dict.items():
            new_lines.append(f"{k}={v}\n")

    with open(ini_path, 'w') as f:
        f.writelines(new_lines)

    print(f"Successfully updated {ini_path} (Prefix: {prefix[:-1]})")
    return True

def main():
    parser = argparse.ArgumentParser(description="DeSmuME PS5 DualSense Configuration Generator")
    parser.add_argument("--index", type=int, default=0, help="Joystick index (0 for Player 1, 1 for Player 2, etc.)")
    parser.add_argument("--ini", type=str, help="Path to desmume.ini to update")
    parser.add_argument("--test", action="store_true", help="Run in test mode to identify button IDs")

    args = parser.parse_args()

    if args.test:
        run_test_mode(args.index)
        return

    config_dict = generate_config_dict(DEFAULT_MAPPINGS, args.index)

    if args.ini:
        update_ini_file(args.ini, config_dict, args.index)
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
