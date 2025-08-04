# macOS Display Resolution Switcher

A modern, interactive terminal-based tool for switching display resolutions on macOS with an intuitive interface featuring centered cursor navigation and fast scrolling.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)

## Features

- 🖥️ **Multi-Display Support**: Switch resolutions on multiple displays independently
- 🎯 **Centered Cursor Navigation**: Cursor stays centered while content scrolls smoothly
- ⚡ **Fast Navigation**: Page Up/Down for quick scrolling through resolution lists
- 📱 **HiDPI Support**: Clear identification of HiDPI (Retina) modes
- 🔢 **Mode Numbers**: Shows actual displayplacer mode numbers for reference
- 📏 **Smart Sorting**: HiDPI modes first, then by resolution size and refresh rate
- 💾 **Preserve Settings**: Non-selected displays maintain their current modes
- 📱 **Responsive UI**: Adapts to any terminal size with proper viewport management

## Prerequisites

- **macOS**: This tool is designed specifically for macOS
- **displayplacer**: Install via Homebrew
  ```bash
  brew install displayplacer
  ```
- **Python 3.7+**: Built-in on modern macOS (uses built-in curses library)

## Installation

1. Download the script:
   ```bash
   curl -O https://raw.githubusercontent.com/YOUR_USERNAME/macos-display-switcher/main/display_switcher.py
   ```

2. Make it executable:
   ```bash
   chmod +x display_switcher.py
   ```

3. Run it:
   ```bash
   python3 display_switcher.py
   ```

## Usage

### Basic Usage

Simply run the script to launch the interactive interface:

```bash
python3 display_switcher.py
```

### Interface Overview

```
╔═════════════════════════════════════════════╗
║         Display Resolution Switcher         ║
╚═════════════════════════════════════════════╝

Current:
  29 inch external screen (3) [PRI]: 2560x1080 @60Hz
  24 inch external screen (1): 1920x1080 @60Hz

Displays (←→):
  ► 29 inch external screen (3)
    24 inch external screen (1)

Modes for 29 inch external screen (3) (↑↓):
  ► [ 26] 2560x1080 (HiDPI) @60Hz [CUR]
    [ 27] 1920x1080 (HiDPI) @60Hz
    [ 28] 1680x1050 (HiDPI) @60Hz
    ↓ more modes below ↓

←→ Display | ↑↓ Mode | PgUp/PgDn Fast | Enter Apply | Q Quit
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| `←` `→` | Switch between displays |
| `↑` `↓` | Navigate resolution modes |
| `Page Up` `Page Down` | Fast scroll through modes |
| `Enter` | Apply selected resolution |
| `Q` or `Esc` | Quit |

### Display Elements

- **[PRI]**: Indicates the primary display
- **[CUR]**: Shows the currently active resolution
- **[123]**: Mode number (matches displayplacer's numbering)
- **(HiDPI)**: Indicates high-density/Retina display modes
- **► Cursor**: Shows currently selected item
- **↑/↓ indicators**: Show when more items are available above/below

## How It Works

1. **Discovery**: Calls `displayplacer list` to enumerate all connected displays and their supported resolutions
2. **Parsing**: Extracts display information including mode numbers, resolutions, refresh rates, and HiDPI status
3. **Sorting**: Organizes modes with HiDPI first, then by resolution width (largest first), then by refresh rate
4. **Navigation**: Provides smooth centered-cursor navigation through the mode list
5. **Application**: Constructs and executes `displayplacer` commands to apply the selected resolution

## Resolution Mode Sorting

Modes are intelligently sorted for optimal user experience:

1. **HiDPI modes first** - Most commonly used on Retina displays
2. **By width (descending)** - Larger resolutions appear first
3. **By refresh rate (descending)** - Higher refresh rates preferred

Example order:
```
2560x1600 (HiDPI) @60Hz
1920x1200 (HiDPI) @60Hz
1680x1050 (HiDPI) @60Hz
2560x1600 @60Hz
1920x1200 @60Hz
1680x1050 @60Hz
```

## Examples

### Single Display Setup
Perfect for laptop users who occasionally connect external displays.

### Multi-Display Setup
Ideal for:
- Developers with multiple monitors
- Creative professionals with mixed display types
- Users with different resolution preferences per display

### HiDPI/Retina Displays
The tool clearly identifies and prioritizes HiDPI modes, making it easy to:
- Switch between native and scaled resolutions
- Find the optimal resolution for your workflow
- Understand the relationship between physical and logical resolutions

## Troubleshooting

### displayplacer not found
```bash
Error: displayplacer not found. Install with: brew install displayplacer
```
**Solution**: Install displayplacer using Homebrew: `brew install displayplacer`

### No displays found
This can happen if displayplacer cannot detect displays properly.
**Solution**: Try running `displayplacer list` manually to verify displayplacer is working.

### Terminal too small
The interface adapts to terminal size, but very small terminals may not display properly.
**Solution**: Resize your terminal to at least 80x24 characters.

### Resolution not applying
If a resolution fails to apply, you'll see an error message.
**Common causes**:
- Display doesn't support the selected mode
- Display connection issues
- macOS display restrictions

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup

1. Clone the repository
2. The tool uses only built-in Python libraries, so no additional dependencies are needed
3. Test with multiple display configurations if possible

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Copyright

Copyright © 2024 Rodrigo Polo

## Acknowledgments

- Built on top of the excellent [displayplacer](https://github.com/jakehilborn/displayplacer) utility
- Inspired by the need for a more user-friendly display resolution management tool on macOS