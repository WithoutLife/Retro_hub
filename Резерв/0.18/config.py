# config.py

import os
from PyQt5.QtCore import QSize

# --- ОПРЕДЕЛЕНИЕ БАЗОВОГО ПУТИ ---
# BASE_DIR - это путь к папке, где находится main_app.py (или исполняемый файл)
import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- НАСТРОЙКИ КОНСОЛЕЙ И ПАРАМЕТРОВ ---
VERSION = "0.17"
CURRENT_CONSOLE = "DENDY" 

CONSOLE_SETTINGS = {
    "DENDY": {
        # 📂 Папка с играми: [BASE_DIR]/Dendy
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Dendy"),
        "ROM_EXTENSIONS": ('.nes', '.rar'),
        # 🕹️ Путь к эмулятору: [BASE_DIR]/Emulator/FCE Ultra X Rus/fceux64 rus.exe
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator/FCE Ultra X Rus/fceux64 rus.exe"),
        "NAME": "Dendy",
        "GRADIENT_END": "#200035",      
        "GRADIENT_START": "#101018",
        # Для FCEUX, как правило, не нужен аргумент полного экрана
        "FULLSCREEN_ARG": "", 
    }, 
    "SEGA": {
        # 📂 Папка с играми: [BASE_DIR]/Sega
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Sega"),
        "ROM_EXTENSIONS": ('.gen', '.smd', '.bin', '.zip'),
        # 🕹️ Путь к эмулятору: [BASE_DIR]/Emulator/Gens32/Gens32Surreal.exe
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator/Gens32/Gens32Surreal.exe"), 
        "NAME": "Sega",
        "GRADIENT_END": "#350020",      
        "GRADIENT_START": "#181010",
        # Для Gens32 используем аргумент "-f"
        "FULLSCREEN_ARG": "-f", 
    }
}

ALLOWED_COVER_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.tga', '.webp', '.gif')
ICON_FILE_NAME = ":/launcher_icon.ico" 
LOGO_FILE_NAME = ":/retro_hub_logo.png" 
LOGO_HEIGHT = 50 

RESIZE_BORDER_WIDTH = 5 

ICON_SIZE = QSize(180, 150) 
ITEM_WIDTH = ICON_SIZE.width() + 20 
ITEM_HEIGHT = ICON_SIZE.height() + 40

START_WIDTH = 891 
START_HEIGHT = 765