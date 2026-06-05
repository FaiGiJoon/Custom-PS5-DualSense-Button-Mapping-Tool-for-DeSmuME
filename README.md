# DeSmuME PS5 DualSense Setup Tool

This tool helps you configure your PS5 DualSense controller for the DeSmuME DS emulator. It provides a user-friendly Graphical User Interface (GUI) to map buttons and can automatically sync with your `desmume.ini` file.

## Features
- **User-Friendly GUI**: Easy-to-use interface for selecting controllers and INI files.
- **Real-Time Visual Feedback**: See your controller inputs live in the tool (requires `pygame`).
- **Process Detection**: Automatically detects if DeSmuME is running and helps locate its configuration file.
- **PS5 DualSense Optimized**: Pre-configured mappings for standard DualSense buttons.
- **Multiple Controllers**: Support for different joystick indices (Player 1, 2, 3, or 4).
- **Safe Auto-Update**: Automatically updates your `desmume.ini` without wiping out other players' configurations. A backup is created just in case.

## Prerequisites
- Python 3.x
- `pygame` (recommended for visual feedback)
- `psutil` (recommended for DeSmuME detection)

Install dependencies:
```bash
pip install pygame psutil
```

## Usage

### 1. Graphical Interface (Default)
Simply run the script without any arguments to launch the GUI:
```bash
python3 dualsense_to_desmume.py
```
- The tool will attempt to auto-detect your `desmume.ini` and any connected controllers.
- Use the **Browse** button if the INI file isn't found automatically.
- Press **Apply Configuration** to save the mappings to DeSmuME.

### 2. Auto-Detect & Sync
If DeSmuME is running when you open the tool, it will notify you and try to use the correct INI file path immediately.

### 3. Command Line Mode (CLI)
For automation or terminal usage, you can still use the CLI:
```bash
python3 dualsense_to_desmume.py --cli --ini "C:\Path\To\DeSmuME\desmume.ini"
```
Other CLI options:
- `--index <0-3>`: Specify player slot (0 for P1, 1 for P2, etc.)
- `--test`: Run in terminal-based test mode.
- `--ini <path>`: Directly update a specific INI file.

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
- **Linux/X11**: If running on Linux, ensure you have a display environment available for the GUI.
- **DeSmuME Overwriting**: If DeSmuME is running, it may overwrite the `desmume.ini` when it closes. The tool will warn you about this. It's best to close DeSmuME, apply the config, and then restart it.
- **Permissions**: Ensure you have write access to the `desmume.ini` file.
