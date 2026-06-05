# DeSmuME PS5 DualSense Sync Tool

A robust Graphical User Interface (GUI) and CLI tool to perfectly sync your PS5 DualSense controller with the DeSmuME DS emulator.

## Features
- **Easy GUI**: Browse for your `desmume.ini` and sync with one click.
- **Live Monitor**: See real-time hex codes as you press buttons (requires `pygame`).
- **Safe Sync**: Non-destructive updates that preserve your other Joypad settings.
- **DeSmuME Detection**: Warns you if DeSmuME is running to prevent config overwrites.
- **Multi-Player Support**: Easily map up to 4 controllers to different Joypad slots.

## Installation
1. Install Python 3.x
2. Install dependencies:
   ```bash
   pip install pygame psutil
   ```

## Usage

### Graphical Mode (Default)
Simply run the script:
```bash
python3 dualsense_to_desmume.py
```

### CLI Mode (Advanced)
For automation or when no display is available:
```bash
# Print mappings to console
python3 dualsense_to_desmume.py --cli

# Update INI directly
python3 dualsense_to_desmume.py --ini "C:\Path\To\desmume.ini" --index 0
```

## How it works
DeSmuME uses specific hex codes for DirectInput. This tool calculates the correct offsets based on your joystick's hardware index and the DS button IDs.

- **Joypad 1**: Base `0x4000`
- **Joypad 2**: Base `0x8000`
- **Joypad 3**: Base `0xC000`
- **Joypad 4**: Base `0x10000`

## Troubleshooting
- **No Controller Detected**: Ensure your DualSense is connected via USB or Bluetooth and recognized by Windows/Linux.
- **DeSmuME not Syncing**: Always close DeSmuME **before** clicking SYNC to ensure it reads the new config on next startup.
