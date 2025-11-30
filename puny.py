#!/usr/bin/env python3
"""
Puny - A minimal terminal-based text editor
Implements Milestones 0-7: file I/O, raw mode, rendering, editing, and status UI
"""

import sys
import termios
import tty
import atexit
import os

# Global state - in a real app you'd use a class, but this is simpler for learning
original_tty = None  # Store original terminal settings
filename = ""  # Current file being edited
buffer = []  # Our text buffer: list of strings, one per line
dirty = False  # Flag: has buffer been modified since last save?


# =============================================================================
# Milestone 1: Terminal Management
# =============================================================================

def save_original_tty():
    """
    Save terminal's original settings so we can restore them on exit.
    This is crucial - otherwise if Puny crashes, user's terminal will be broken.
    """
    global original_tty
    original_tty = termios.tcgetattr(sys.stdin.fileno())


def restore_tty():
    """Restore terminal to its original settings"""
    if original_tty:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, original_tty)


def cleanup():
    """
    Cleanup function registered to run on exit (normal or crash).
    Milestone 1: Always restore terminal to a sane state.
    """
    restore_tty()
    # Clear screen and reset all attributes
    sys.stdout.write("\x1b[2J\x1b[H\x1b[0m")
    sys.stdout.flush()


# =============================================================================
# Milestone 0/2: File Operations & Buffer Management
# =============================================================================

def load_buffer(fname):
    """
    Load file into our buffer data structure.
    Milestone 0: Basic file reading
    Milestone 2: Using list-of-strings buffer
    """
    global buffer
    try:
        with open(fname, 'r') as f:
            # Remove trailing newlines - we'll add them back on save
            buffer = [line.rstrip('\n') for line in f]
    except FileNotFoundError:
        # New file: start with one empty line
        buffer = [""]


def save_buffer(fname):
    """
    Save buffer back to file.
    Milestone 0: Basic file writing
    """
    with open(fname, 'w') as f:
        f.write('\n'.join(buffer))


# =============================================================================
# Milestone 5: Editing Operations
# =============================================================================

def insert_char(line, col, char):
    """
    Insert a character at (line, col) position.
    Milestone 5: Basic text manipulation
    """
    global buffer, dirty
    if 0 <= line < len(buffer):
        buffer[line] = buffer[line][:col] + char + buffer[line][col:]
        dirty = True


def delete_char(line, col):
    """
    Delete character at (line, col).
    If at end of line, merges with next line.
    Milestone 5: Deletion with edge case handling
    """
    global buffer, dirty
    if 0 <= line < len(buffer):
        if col < len(buffer[line]):
            # Delete within line
            buffer[line] = buffer[line][:col] + buffer[line][col + 1:]
            dirty = True
        elif col == len(buffer[line]) and line < len(buffer) - 1:
            # Merge with next line
            buffer[line] += buffer.pop(line + 1)
            dirty = True


# =============================================================================
# Milestone 3/6: Rendering
# =============================================================================

def render(cursor_row, cursor_col):
    """
    Render the entire screen:
    - Clear screen
    - Print buffer content
    - Draw status bar at bottom
    - Position cursor

    Milestone 3: Basic rendering
    Milestone 6: Status bar addition
    """
    # Clear screen and move to top-left
    sys.stdout.write("\x1b[2J\x1b[H")

    # Print each line of the buffer
    for line in buffer:
        sys.stdout.write(line + "\r\n")

    # Get terminal dimensions for status bar
    try:
        height = os.get_terminal_size().lines
        width = os.get_terminal_size().columns
    except OSError:
        height, width = 24, 80  # Fallback

    # Build status bar text
    status = f"{filename} | Line {cursor_row + 1}, Col {cursor_col + 1} | {len(buffer)} lines"
    if dirty:
        status += " | [Modified]"

    # Move to bottom row, use inverse video for status bar
    sys.stdout.write(f"\x1b[{height};1H")  # Set cursor position
    sys.stdout.write("\x1b[7m")  # Enable inverse video
    sys.stdout.write(status[:width].ljust(width))  # Truncate/pad to width
    sys.stdout.write("\x1b[0m")  # Reset all attributes

    # Position cursor in buffer area
    sys.stdout.write(f"\x1b[{cursor_row + 1};{cursor_col + 1}H")
    sys.stdout.flush()  # Ensure all output is written


# =============================================================================
# Milestone 4/5/7: Input Handling
# =============================================================================

def handle_input(cursor_row, cursor_col):
    """
    Process a single keyboard input.
    Returns updated (cursor_row, cursor_col).

    Milestone 4: Cursor movement (arrow keys)
    Milestone 5: Editing (insert/delete)
    Milestone 7: Save/quit UI (Ctrl+S, Ctrl+Q)
    """
    ch = sys.stdin.read(1)

    # Escape sequences (arrow keys, Home, End, etc.)
    if ch == '\x1b':  # ESC
        ch2 = sys.stdin.read(1)
        ch3 = sys.stdin.read(1)
        if ch2 == '[':
            if ch3 == 'A':  # Up arrow
                cursor_row = max(0, cursor_row - 1)
            elif ch3 == 'B':  # Down arrow
                cursor_row = min(len(buffer) - 1, cursor_row + 1)
            elif ch3 == 'C':  # Right arrow
                cursor_col = min(len(buffer[cursor_row]), cursor_col + 1)
            elif ch3 == 'D':  # Left arrow
                cursor_col = max(0, cursor_col - 1)
        return cursor_row, cursor_col

    # Enter key - split line
    if ch == '\r' or ch == '\n':
        line = buffer[cursor_row]
        buffer.insert(cursor_row + 1, line[cursor_col:])
        buffer[cursor_row] = line[:cursor_col]
        cursor_row += 1
        cursor_col = 0
        return cursor_row, cursor_col

    # Backspace (DEL character)
    if ch == '\x7f':
        if cursor_col > 0:
            delete_char(cursor_row, cursor_col - 1)
            cursor_col -= 1
        elif cursor_row > 0:
            # Merge with previous line
            cursor_row -= 1
            cursor_col = len(buffer[cursor_row])
            buffer[cursor_row] += buffer.pop(cursor_row + 1)
        return cursor_row, cursor_col

    # Ctrl+D - delete forward
    if ch == '\x04':
        delete_char(cursor_row, cursor_col)
        return cursor_row, cursor_col

    # Ctrl+S - save
    if ch == '\x13':
        save_buffer(filename)
        global dirty
        dirty = False
        return cursor_row, cursor_col

    # Ctrl+Q - quit with confirmation if dirty
    if ch == '\x11':
        if dirty:
            # Simple prompt interface
            sys.stdout.write("\x1b[2J\x1b[H\x1b[2K")
            sys.stdout.write("Quit without saving? (y/N) ")
            sys.stdout.flush()
            response = sys.stdin.read(1)
            if response.lower() == 'y':
                sys.exit(0)
        else:
            sys.exit(0)
        return cursor_row, cursor_col

    # Printable ASCII characters
    if 32 <= ord(ch) <= 126:
        insert_char(cursor_row, cursor_col, ch)
        cursor_col += 1

    return cursor_row, cursor_col


# =============================================================================
# Milestone 7: Main Loop
# =============================================================================

def main():
    """Main editor loop"""
    global filename

    # Argument parsing (Milestone 0)
    if len(sys.argv) < 2:
        print("Usage: puny <file>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    load_buffer(filename)

    # Terminal setup (Milestone 1)
    save_original_tty()
    atexit.register(cleanup)  # Ensure cleanup on crash
    tty.setraw(sys.stdin.fileno())  # Disable line buffering and echo

    cursor_row, cursor_col = 0, 0

    try:
        while True:
            render(cursor_row, cursor_col)
            cursor_row, cursor_col = handle_input(cursor_row, cursor_col)

            # Ensure cursor stays within line bounds
            cursor_col = min(cursor_col, len(buffer[cursor_row]))
    except KeyboardInterrupt:
        cleanup()
        sys.exit(0)


if __name__ == "__main__":
    main()