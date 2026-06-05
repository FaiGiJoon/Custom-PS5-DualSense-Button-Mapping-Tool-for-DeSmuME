#!/usr/bin/env python3

def generate_desmume_config():
    """
    Generates a recommended [Joypad] configuration for PS5 DualSense controller on DeSmuME (Windows).
    These values are based on standard DirectInput mappings for the first connected DualSense.
    """
    
    # Mapping of DeSmuME keys to DualSense Button/Hat IDs
    # 0x4000 is typically the base for Joystick 0 Buttons
    # 0x4100 is typically the base for Joystick 0 POV/Hat
    mappings = {
        "Joypad1.A":      "0x4002", # Circle
        "Joypad1.B":      "0x4001", # Cross
        "Joypad1.X":      "0x4003", # Triangle
        "Joypad1.Y":      "0x4000", # Square
        "Joypad1.L":      "0x4004", # L1
        "Joypad1.R":      "0x4005", # R1
        "Joypad1.Start":  "0x4009", # Options
        "Joypad1.Select": "0x4008", # Create/Share
        "Joypad1.Up":     "0x4100", # D-Pad Up
        "Joypad1.Down":   "0x4101", # D-Pad Down
        "Joypad1.Left":   "0x4102", # D-Pad Left
        "Joypad1.Right":  "0x4103", # D-Pad Right
        "Joypad1.Debug":  "0",
        "Joypad1.Boost":  "0x4007", # R2 (Digital)
        "Joypad1.Lid":    "0x4006", # L2 (Digital)
    }

    output = ["[Joypad]"]
    output.append("# PS5 DualSense Recommended Mapping for DeSmuME")
    output.append("# Copy these lines into your desmume.ini file")
    
    for key, val in mappings.items():
        output.append(f"{key}={val}")
        
    return "\n".join(output)

def main():
    print("DeSmuME PS5 DualSense Configuration Generator")
    print("-" * 45)
    print(generate_desmume_config())
    print("-" * 45)
    print("Instructions:")
    print("1. Close DeSmuME if it is running.")
    print("2. Locate your 'desmume.ini' file (usually in the same folder as desmume.exe).")
    print("3. Open 'desmume.ini' in a text editor (like Notepad).")
    print("4. Find the [Joypad] section.")
    print("5. Update or add the 'Joypad1.*' lines with the values shown above.")
    print("   Note: Be careful not to delete Joypad2, Joypad3, etc. if you use them.")
    print("6. Save the file and restart DeSmuME.")

if __name__ == "__main__":
    main()
