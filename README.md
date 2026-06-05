# DeSmuME PS5 DualSense Setup Tool

This tool helps you configure your PS5 DualSense controller for the DeSmuME DS emulator. It generates the correct hex codes for button mappings and can automatically update your `desmume.ini` file.

## Features
- **PS5 DualSense Optimized**: Pre-configured mappings for standard DualSense buttons.
- **Multiple Controllers**: Support for different joystick indices if you have multiple controllers. Automatically maps to `Joypad1`, `Joypad2`, etc.
- **Test Mode**: Real-time feedback of DeSmuME hex codes when you press buttons on your controller (requires `pygame`).
- **Safe Auto-Update**: Automatically updates your `desmume.ini` without wiping out other players' configurations. A backup is created just in case.

## Prerequisites
- Python 3.x
- `pygame` (optional, only needed for **Test Mode**)
  ```bash
  pip install pygame
  ```

## Usage

### 1. Generate Configuration
Run the script to see the recommended `[Joypad]` section:
```bash
python3 dualsense_to_desmume.py
```

### 2. Auto-Update desmume.ini
If you know the path to your `desmume.ini`, the tool can update it for you:
```bash
python3 dualsense_to_desmume.py --ini "C:\Path\To\DeSmuME\desmume.ini"
```
You can also specify which player slot to update (e.g., Player 2):
```bash
python3 dualsense_to_desmume.py --ini "C:\Path\To\DeSmuME\desmume.ini" --index 1
```

### 3. Test Mode (Debugging)
If buttons aren't mapping correctly, use Test Mode to find the exact hex codes for your controller:
```bash
python3 dualsense_to_desmume.py --test
```
Press buttons on your controller, and the script will print the corresponding `0x4XXX` codes to use in the INI.

## Default Button Mappings
| PS5 Button | DeSmuME/DS Button |
|------------|-------------------|
| Circle     | A                 |
| Cross      | B                 |
| Triangle   | X                 |
| Square     | Y                 |
| L1         | L                 |
| R1         | R                 |
| Options    | Start             |
| Share      | Select            |
| D-Pad      | Up/Down/Left/Right|
| L2         | Lid (Close/Open)  |
| R2         | Boost (Fast Forward) |

## Troubleshooting
- **Joystick Index**: If the script doesn't detect the right controller, try `--index 1` or other numbers.
- **Windows vs Linux**: This tool is primarily designed for the Windows version of DeSmuME which uses DirectInput hex codes in its `.ini` file.
- **Permissions**: Ensure you have write access to the `desmume.ini` file.
