# config.py

import os
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QMainWindow 

# --- ОПРЕДЕЛЕНИЕ БАЗОВОГО ПУТИ ---
import sys
# Определяет базовую директорию, независимо от того, запущен ли код из скрипта или как exe
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- НАСТРОЙКИ КОНСОЛЕЙ И ПАРАМЕТРОВ ---
VERSION = "0.24" 
CURRENT_CONSOLE = "DENDY" 

ITEM_WIDTH = 180
ITEM_HEIGHT = 180
ALLOWED_COVER_EXTENSIONS = ('.png', '.jpg', '.jpeg') # Расширения для обложек

CONSOLE_SETTINGS = {
   "DENDY": {
        # 📂 ROOT_FOLDER: Путь к папке Dendy
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Dendy"),
        "ROM_EXTENSIONS": ('.nes', '.rar'),
        # 🕹️ EMULATOR_PATH: Корректное использование os.path.join()
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator", "FCE Ultra X Rus", "fceux64 rus.exe"),
        "NAME": "Dendy",
        # 🎨 НОВЫЙ НЕОНОВО-ФИОЛЕТОВЫЙ ГРАДИЕНТ (Темный старт)
        "GRADIENT_END": "#8A2BE2",      
        "GRADIENT_START": "#0A001A", # Значительно темнее фиолетовый
        "FULLSCREEN_ARG": "", 
    }, 
    "SEGA": {
        # 📂 ROOT_FOLDER: Путь к папке Sega
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Sega"),
        "ROM_EXTENSIONS": ('.gen', '.smd', '.bin', '.zip'),
        # 🕹️ EMULATOR_PATH: Корректное использование os.path.join()
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator", "Gens32", "Gens32Surreal.exe"), 
        "NAME": "Sega",
        # 🎨 НОВЫЙ ТЕМНЫЙ НЕОНОВО-САЛАТОВЫЙ ГРАДИЕНТ (Темный старт)
        "GRADIENT_END": "#7FFF00",      
        "GRADIENT_START": "#000A0A", # Значительно темнее бирюзово-зеленый
        "FULLSCREEN_ARG": "",
    },
    # --- КОНСОЛЬ SONY ---
    "SONY": { 
        # 📂 ROOT_FOLDER: Путь к папке Sony
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Sony"),
        "ROM_EXTENSIONS": ('.iso', '.bin', '.img', '.cue', '.zip'),
        # 🕹️ EMULATOR_PATH: Корректное использование os.path.join()
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator", "DuckStation", "duckstation-qt-x64-ReleaseLTCG.exe"), 
        "NAME": "Sony PlayStation",
        # 🎨 НОВЫЙ НЕОНОВО-ЖЕЛТЫЙ ГРАДИЕНТ (Темный старт)
        "GRADIENT_END": "#FFFF00",      
        "GRADIENT_START": "#1A1A00", # Значительно темнее желтый
        "FULLSCREEN_ARG": "-fullscreen", 
    }
}