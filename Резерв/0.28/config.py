# config.py

import os
from PyQt5.QtCore import QSize

# --- ОПРЕДЕЛЕНИЕ БАЗОВОГО ПУТИ ---
import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- НАСТРОЙКИ КОНСОЛЕЙ И ПАРАМЕТРОВ ---
VERSION = "0.24" 
CURRENT_CONSOLE = "DENDY" 

CONSOLE_SETTINGS = {
    "DENDY": {
        # 📂 Папка с играми: [BASE_DIR]/Dendy
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Dendy"),
        "ROM_EXTENSIONS": ('.nes', '.rar'),
        # 🕹️ Путь к эмулятору
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator/FCE Ultra X Rus/fceux64 rus.exe"),
        "NAME": "Dendy",
        "GRADIENT_END": "#200035",      
        "GRADIENT_START": "#101018",
        "FULLSCREEN_ARG": "", 
    }, 
    "SEGA": {
        # 📂 Папка с играми: [BASE_DIR]/Sega
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Sega"),
        "ROM_EXTENSIONS": ('.gen', '.smd', '.bin', '.zip'),
        # 🕹️ Путь к эмулятору
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator/Gens32/Gens32Surreal.exe"), 
        "NAME": "Sega",
        "GRADIENT_END": "#350020",      
        "GRADIENT_START": "#181010",
        "FULLSCREEN_ARG": "",
    },
    # --- НОВАЯ КОНСОЛЬ SONY ---
    "SONY": { 
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Sony"),
        "ROM_EXTENSIONS": ('.cue', '.iso', '.chd'), 
        # 🕹️ Пример: ePSXe или RetroArch
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator/ePSXe/ePSXe.exe"), 
        "NAME": "Sony PlayStation",
        "GRADIENT_END": "#002035",      
        "GRADIENT_START": "#101018",
        "FULLSCREEN_ARG": "-fullscreen", 
    },
}

# --- НАСТРОЙКИ ИНТЕРФЕЙСА (Оставить как есть) ---
ITEM_WIDTH = 180
ITEM_HEIGHT = 220
START_WIDTH = 1000
START_HEIGHT = 700
ALLOWED_COVER_EXTENSIONS = ('.png', '.jpg', '.jpeg')
ALLOWED_SCREENSHOT_EXTENSIONS = ('.png', '.jpg', '.jpeg')