#!/usr/bin/env python3
"""
Display Resolution Switcher for macOS
A modern, interactive terminal-based tool for switching display resolutions
with centered cursor navigation and fast scrolling capabilities.

Copyright (c) 2024 Rodrigo Polo
Licensed under the MIT License
"""

import subprocess
import sys
import re
import curses
import argparse
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

__version__ = "1.0.0"
__author__ = "Rodrigo Polo"
__license__ = "MIT"

@dataclass
class DisplayMode:
    mode_num: int
    resolution: str
    hertz: int
    color_depth: int
    scaling: bool = False
    
    @property
    def width(self) -> int:
        return int(self.resolution.split('x')[0])
    
    @property
    def height(self) -> int:
        return int(self.resolution.split('x')[1])
    
    def __str__(self):
        suffix = " (HiDPI)" if self.scaling else ""
        return f"{self.resolution}{suffix} @{self.hertz}Hz"

@dataclass
class Display:
    persistent_id: str
    contextual_id: str
    serial_id: str
    display_type: str
    current_resolution: str
    current_hertz: int
    origin: Tuple[int, int]
    current_mode: int
    modes: List[DisplayMode] = None
    
    def __post_init__(self):
        if self.modes is None:
            self.modes = []
    
    def get_short_name(self) -> str:
        return f"{self.display_type} ({self.contextual_id})"
    
    def is_primary(self) -> bool:
        return self.origin == (0, 0)

class Viewport:
    """Manages scrollable viewport for a list"""
    def __init__(self, max_height: int):
        self.max_height = max(1, max_height)
        self.offset = 0
        self.current_index = 0
    
    def update(self, total_items: int, current_index: int):
        """Update viewport to keep cursor centered when possible"""
        self.current_index = current_index
        
        # Try to keep the cursor centered in the viewport
        center_offset = current_index - (self.max_height // 2)
        
        # Adjust offset to keep it within valid bounds
        max_possible_offset = max(0, total_items - self.max_height)
        self.offset = max(0, min(center_offset, max_possible_offset))
    
    def get_visible_range(self, total_items: int) -> Tuple[int, int]:
        """Get the range of items that should be visible"""
        start = self.offset
        end = min(self.offset + self.max_height, total_items)
        return start, end
    
    def has_scroll_up(self) -> bool:
        return self.offset > 0
    
    def has_scroll_down(self, total_items: int) -> bool:
        return self.offset + self.max_height < total_items

class DisplaySwitcher:
    def __init__(self):
        self.displays: List[Display] = []
        self.current_display_index = 0
        self.current_mode_indices = {}
        self.status_message = ""
        self.status_timeout = 0
        self.display_viewport = None
        self.mode_viewports = {}  # Per-display viewports
    
    def run_displayplacer_list(self) -> str:
        """Run displayplacer list and return output"""
        try:
            result = subprocess.run(['displayplacer', 'list'], 
                                  capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise Exception(f"Error running displayplacer: {e}")
        except FileNotFoundError:
            raise Exception("displayplacer not found. Install with: brew install displayplacer")
    
    def parse_displayplacer_output(self, output: str):
        """Parse displayplacer list output"""
        displays_data = output.split('\n\n')
        
        for display_block in displays_data:
            if 'Persistent screen id:' not in display_block:
                continue
            
            lines = display_block.strip().split('\n')
            
            display_data = {
                'persistent_id': "",
                'contextual_id': "",
                'serial_id': "",
                'display_type': "",
                'current_resolution': "",
                'current_hertz': 0,
                'origin': (0, 0),
                'current_mode': -1
            }
            
            for line in lines:
                if line.startswith('Persistent screen id:'):
                    display_data['persistent_id'] = line.split(': ')[1]
                elif line.startswith('Contextual screen id:'):
                    display_data['contextual_id'] = line.split(': ')[1]
                elif line.startswith('Serial screen id:'):
                    display_data['serial_id'] = line.split(': ')[1]
                elif line.startswith('Type:'):
                    display_data['display_type'] = line.split(': ')[1]
                elif line.startswith('Resolution:'):
                    display_data['current_resolution'] = line.split(': ')[1]
                elif line.startswith('Hertz:'):
                    display_data['current_hertz'] = int(line.split(': ')[1])
                elif line.startswith('Origin:'):
                    origin_str = line.split(': ')[1].split(' - ')[0]
                    coords = origin_str.strip('()').split(',')
                    display_data['origin'] = (int(coords[0]), int(coords[1]))
            
            display = Display(**display_data)
            
            # Parse modes
            in_modes_section = False
            for line in lines:
                if line.startswith('Resolutions for rotation'):
                    in_modes_section = True
                    continue
                
                if in_modes_section and line.strip().startswith('mode '):
                    mode_match = re.match(r'\s*mode (\d+): res:(\d+x\d+) hz:(\d+) color_depth:(\d+)(.*)$', line)
                    if mode_match:
                        mode_num = int(mode_match.group(1))
                        resolution = mode_match.group(2)
                        hertz = int(mode_match.group(3))
                        color_depth = int(mode_match.group(4))
                        extra = mode_match.group(5)
                        
                        scaling = 'scaling:on' in extra
                        is_current = '<-- current mode' in extra
                        
                        mode = DisplayMode(mode_num, resolution, hertz, color_depth, scaling)
                        display.modes.append(mode)
                        
                        if is_current:
                            display.current_mode = mode_num
            
            # Sort modes: HiDPI first, then by width (descending), then by refresh rate (descending)
            display.modes.sort(key=lambda m: (not m.scaling, -m.width, -m.hertz))
            
            # Debug: Check if we have the 1280x720 HiDPI mode
            # for mode in display.modes:
            #     if mode.resolution == "1280x720" and mode.scaling:
            #         print(f"Found 1280x720 HiDPI: {mode}")
            
            self.displays.append(display)
            self.current_mode_indices[display.persistent_id] = 0
            # Initialize viewport for this display's modes
            self.mode_viewports[display.persistent_id] = None
    
    def get_current_mode_index(self) -> int:
        """Get the current mode index for the current display"""
        if self.current_display_index < len(self.displays):
            display = self.displays[self.current_display_index]
            return self.current_mode_indices.get(display.persistent_id, 0)
        return 0
    
    def set_current_mode_index(self, index: int):
        """Set the current mode index for the current display"""
        if self.current_display_index < len(self.displays):
            display = self.displays[self.current_display_index]
            self.current_mode_indices[display.persistent_id] = index
    
    def draw_interface(self, stdscr):
        """Draw the interface using curses"""
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(0)   # Wait for input
        
        # Initialize colors if available
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)    # Header
            curses.init_pair(2, curses.COLOR_GREEN, -1)   # Selected
            curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Current mode
            curses.init_pair(4, curses.COLOR_RED, -1)     # Error
            curses.init_pair(5, curses.COLOR_WHITE, -1)   # Scroll indicators
        
        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            # Calculate available space
            current_line = 0
            
            # Header
            header_lines = [
                "╔═════════════════════════════════════════════╗",
                "║         Display Resolution Switcher         ║",
                "╚═════════════════════════════════════════════╝"
            ]
            
            for i, line in enumerate(header_lines):
                if current_line < height:
                    x = max(0, (width - len(line)) // 2)
                    stdscr.addstr(current_line, x, line, curses.color_pair(1))
                    current_line += 1
            
            current_line += 1
            
            # Current configuration (compact)
            if current_line < height - 1:
                stdscr.addstr(current_line, 0, "Current:")
                current_line += 1
            
            for i, display in enumerate(self.displays[:2]):
                if current_line >= height - 1:
                    break
                primary_text = " [PRI]" if display.is_primary() else ""
                current_mode = next((m for m in display.modes if m.mode_num == display.current_mode), None)
                mode_desc = str(current_mode) if current_mode else "Unknown"
                text = f"  {display.get_short_name()}{primary_text}: {mode_desc}"
                if len(text) > width - 2:
                    text = text[:width-5] + "..."
                stdscr.addstr(current_line, 0, text)
                current_line += 1
            
            if len(self.displays) > 2 and current_line < height - 1:
                stdscr.addstr(current_line, 0, f"  + {len(self.displays) - 2} more")
                current_line += 1
            
            current_line += 1
            
            # Calculate viewport sizes
            remaining_height = height - current_line - 4  # Reserve for controls
            display_viewport_height = min(len(self.displays), max(3, remaining_height // 3))
            mode_viewport_height = max(3, remaining_height - display_viewport_height - 2)
            
            # Initialize or update display viewport
            if self.display_viewport is None:
                self.display_viewport = Viewport(display_viewport_height)
            else:
                self.display_viewport.max_height = display_viewport_height
            
            # Get or create mode viewport for current display
            current_display = self.displays[self.current_display_index]
            if self.mode_viewports.get(current_display.persistent_id) is None:
                self.mode_viewports[current_display.persistent_id] = Viewport(mode_viewport_height)
            else:
                self.mode_viewports[current_display.persistent_id].max_height = mode_viewport_height
            
            mode_viewport = self.mode_viewports[current_display.persistent_id]
            
            # Display selection
            if current_line < height - 3:
                stdscr.addstr(current_line, 0, "Displays (←→):", curses.A_BOLD)
                current_line += 1
            
            self.display_viewport.update(len(self.displays), self.current_display_index)
            start, end = self.display_viewport.get_visible_range(len(self.displays))
            
            if self.display_viewport.has_scroll_up() and current_line < height - 3:
                stdscr.addstr(current_line, 2, "↑ more ↑", curses.color_pair(5))
                current_line += 1
            
            for i in range(start, end):
                if current_line >= height - 3:
                    break
                display = self.displays[i]
                prefix = "► " if i == self.current_display_index else "  "
                text = f"{prefix}{display.get_short_name()}"
                if len(text) > width - 4:
                    text = text[:width-7] + "..."
                attr = curses.color_pair(2) if i == self.current_display_index else 0
                stdscr.addstr(current_line, 2, text, attr)
                current_line += 1
            
            if self.display_viewport.has_scroll_down(len(self.displays)) and current_line < height - 3:
                stdscr.addstr(current_line, 2, "↓ more ↓", curses.color_pair(5))
                current_line += 1
            
            current_line += 1
            
            # Mode selection
            if current_line < height - 3:
                current_display = self.displays[self.current_display_index]
                text = f"Modes for {current_display.get_short_name()} (↑↓):"
                if len(text) > width - 2:
                    text = f"Modes (↑↓):"
                stdscr.addstr(current_line, 0, text, curses.A_BOLD)
                current_line += 1
            
            current_mode_idx = self.get_current_mode_index()
            mode_viewport.update(len(current_display.modes), current_mode_idx)
            mode_start, mode_end = mode_viewport.get_visible_range(len(current_display.modes))
            
            # Debug info (remove in production)
            # stdscr.addstr(0, width-30, f"Sel:{current_mode_idx} Off:{mode_viewport.offset}", curses.A_DIM)
            
            if mode_viewport.has_scroll_up() and current_line < height - 3:
                stdscr.addstr(current_line, 2, "↑ more ↑", curses.color_pair(5))
                current_line += 1
            
            for idx in range(mode_start, mode_end):
                if current_line >= height - 3:
                    break
                mode = current_display.modes[idx]
                is_current = mode.mode_num == current_display.current_mode
                is_selected = idx == current_mode_idx
                
                prefix = "► " if is_selected else "  "
                suffix = " [CUR]" if is_current else ""
                text = f"{prefix}[{mode.mode_num:3d}] {mode}{suffix}"
                if len(text) > width - 4:
                    text = text[:width-7] + "..."
                
                attr = 0
                if is_selected:
                    attr = curses.color_pair(2) | curses.A_BOLD
                if is_current and not is_selected:
                    attr = curses.color_pair(3)
                
                stdscr.addstr(current_line, 2, text, attr)
                current_line += 1
            
            if mode_viewport.has_scroll_down(len(current_display.modes)) and current_line < height - 3:
                stdscr.addstr(current_line, 2, "↓ more ↓", curses.color_pair(5))
                current_line += 1
            
            # Controls
            controls = "←→ Display | ↑↓ Mode | PgUp/PgDn Fast | Enter Apply | Q Quit"
            if len(controls) > width - 2:
                controls = "←→ ↑↓ PgUp/Dn Enter Q"
            stdscr.addstr(height - 2, 0, controls)
            
            # Status message
            if self.status_message and self.status_timeout > 0:
                attr = curses.color_pair(4) if "Error" in self.status_message else curses.color_pair(2)
                stdscr.addstr(height - 1, 0, self.status_message[:width-2], attr)
                self.status_timeout -= 1
                if self.status_timeout == 0:
                    self.status_message = ""
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == ord('q') or key == ord('Q') or key == 27:  # q or ESC
                break
            
            elif key == curses.KEY_LEFT and len(self.displays) > 1:
                self.current_display_index = (self.current_display_index - 1) % len(self.displays)
            
            elif key == curses.KEY_RIGHT and len(self.displays) > 1:
                self.current_display_index = (self.current_display_index + 1) % len(self.displays)
            
            elif key == curses.KEY_UP:
                current_display = self.displays[self.current_display_index]
                if current_display.modes:
                    current_idx = self.get_current_mode_index()
                    if current_idx == 0:
                        # Wrap to bottom
                        new_idx = len(current_display.modes) - 1
                    else:
                        new_idx = current_idx - 1
                    self.set_current_mode_index(new_idx)
            
            elif key == curses.KEY_DOWN:
                current_display = self.displays[self.current_display_index]
                if current_display.modes:
                    current_idx = self.get_current_mode_index()
                    if current_idx == len(current_display.modes) - 1:
                        # Wrap to top
                        new_idx = 0
                    else:
                        new_idx = current_idx + 1
                    self.set_current_mode_index(new_idx)
            
            elif key == curses.KEY_PPAGE:  # Page Up
                current_display = self.displays[self.current_display_index]
                if current_display.modes:
                    current_idx = self.get_current_mode_index()
                    # Jump up by half the viewport height
                    jump = max(5, mode_viewport.max_height // 2)
                    new_idx = max(0, current_idx - jump)
                    self.set_current_mode_index(new_idx)
            
            elif key == curses.KEY_NPAGE:  # Page Down
                current_display = self.displays[self.current_display_index]
                if current_display.modes:
                    current_idx = self.get_current_mode_index()
                    # Jump down by half the viewport height
                    jump = max(5, mode_viewport.max_height // 2)
                    new_idx = min(len(current_display.modes) - 1, current_idx + jump)
                    self.set_current_mode_index(new_idx)
            
            elif key == ord('\n') or key == ord('\r'):  # Enter
                self.apply_mode()
    
    def apply_mode(self):
        """Apply the selected mode"""
        current_display = self.displays[self.current_display_index]
        mode_idx = self.get_current_mode_index()
        
        if mode_idx >= len(current_display.modes):
            self.status_message = "Error: Invalid mode"
            self.status_timeout = 30
            return
        
        selected_mode = current_display.modes[mode_idx]
        
        # Build displayplacer command
        # The command should be: displayplacer "id:xxx mode:n origin:(x,y) degree:0" "id:yyy ..."
        cmd_args = []
        
        for display in self.displays:
            if display == current_display:
                mode_num = selected_mode.mode_num
            else:
                mode_num = display.current_mode
            
            # Format origin as (x,y)
            origin_str = f"({display.origin[0]},{display.origin[1]})"
            display_arg = f"id:{display.persistent_id} mode:{mode_num} origin:{origin_str} degree:0"
            cmd_args.append(display_arg)
        
        # Build the full command
        cmd = ["displayplacer"] + cmd_args
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            current_display.current_mode = selected_mode.mode_num
            current_display.current_resolution = selected_mode.resolution
            current_display.current_hertz = selected_mode.hertz
            
            self.status_message = "✓ Applied successfully!"
            self.status_timeout = 30
            
        except subprocess.CalledProcessError as e:
            self.status_message = f"Error: {e.stderr.strip() if e.stderr else 'Failed'}"
            self.status_timeout = 50
    
    def run(self, stdscr):
        """Main run method with curses"""
        try:
            # Load display information
            output = self.run_displayplacer_list()
            self.parse_displayplacer_output(output)
            
            if not self.displays:
                stdscr.addstr(0, 0, "No displays found!")
                stdscr.refresh()
                stdscr.getch()
                return
            
            self.draw_interface(stdscr)
            
        except Exception as e:
            stdscr.addstr(0, 0, f"Error: {str(e)}")
            stdscr.refresh()
            stdscr.getch()

def main():
    """Main entry point with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Interactive display resolution switcher for macOS",
        epilog=f"Copyright (c) 2024 {__author__}. Licensed under the {__license__} License."
    )
    parser.add_argument(
        "--version", "-v", 
        action="version", 
        version=f"Display Resolution Switcher {__version__}"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode (shows additional information)"
    )
    
    args = parser.parse_args()
    
    # Check if we're in a terminal
    if not sys.stdin.isatty():
        print("Error: This tool requires an interactive terminal.", file=sys.stderr)
        sys.exit(1)
    
    try:
        switcher = DisplaySwitcher()
        if args.debug:
            print(f"Starting Display Resolution Switcher v{__version__}")
        curses.wrapper(switcher.run)
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if args.debug:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()