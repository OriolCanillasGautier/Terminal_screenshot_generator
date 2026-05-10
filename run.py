#!/usr/bin/env python3
"""Entry point for PyInstaller .exe build."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from termshot.cli import main

if __name__ == '__main__':
    main()
