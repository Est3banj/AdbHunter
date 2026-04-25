"""
AdbHunter - Entry Point
======================

Usage:
    python main.py
    python -m src.main
"""

import sys
import os

# Agregar el directorio src al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import main

if __name__ == "__main__":
    main()