"""Simple launcher entrypoint for packaging and installers.

This module provides a `main()` function that opens the Tkinter GUI.
Used as a stable entry-point for PyInstaller and `pyproject` scripts.
"""
from pathlib import Path
import sys


def main():
    # Import the GUI module and run the main loop. Keep imports local
    # so packaging tools that analyze the file work cleanly.
    try:
        import gui_tk as gui
    except Exception:
        # Try package-style import if running from installed package
        try:
            from . import gui_tk as gui
        except Exception:
            raise

    app = gui.build_ui()
    app.mainloop()


if __name__ == '__main__':
    main()
