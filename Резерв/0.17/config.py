# config.py

import os
from PyQt5.QtCore import QSize

# --- ОПРЕДЕЛЕНИЕ БАЗОВОГО ПУТИ (перенесено из рабочего main.py) ---
# Для корректного определения путей к эмуляторам и папкам с играми
import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- НАСТРОЙКИ КОНСОЛЕЙ И ПАРАМЕТРОВ (Полностью из рабочего файла) ---
VERSION = "0.17"
CURRENT_CONSOLE = "DENDY" 

CONSOLE_SETTINGS = {
    "DENDY": {
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Dendy"),
        "ROM_EXTENSIONS": ('.nes', '.rar'),
        # ИСПРАВЛЕНО: Убран флаг -f, если ваш эмулятор не поддерживает его
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator/FCE Ultra X Rus/fceux64 rus.exe"),
        "NAME": "Dendy",
        "GRADIENT_END": "#200035",      
        "GRADIENT_START": "#101018",
        # 🌟 ДОБАВЛЕНО: Ключ для запуска игры. Используем "-f" или "--fullscreen"
        "FULLSCREEN_ARG": "", # Установите "" (пустая строка) или "-f", если уверены в нем
    }, # <--- ОБЯЗАТЕЛЬНАЯ ЗАПЯТАЯ
    "SEGA": {
        "ROOT_FOLDER": os.path.join(BASE_DIR, "Sega"),
        "ROM_EXTENSIONS": ('.gen', '.smd', '.bin', '.zip'),
        
        # 🌟 ИСПРАВЛЕНО: Заменил опасные \ на безопасные /
        "EMULATOR_PATH": os.path.join(BASE_DIR, "Emulator/Gens32/Gens32Surreal.exe"), 
        
        "NAME": "Sega",
        "GRADIENT_END": "#350020",      
        "GRADIENT_START": "#181010",
        # 🌟 ДОБАВЛЕНО: Ключ для запуска игры. 
        "FULLSCREEN_ARG": "-f", # Выяснили, что для Gens нужен флаг "-f"
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