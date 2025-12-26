# threads.py (ФИНАЛЬНЫЙ ИСПРАВЛЕННЫЙ КОД ДЛЯ МНОГОПОТОЧНОСТИ И ЗАПУСКА ЭМУЛЯТОРА)

import os
import time
import subprocess
import logging
import re
from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget

# ВАЖНО: Убедитесь, что widgets.py существует и содержит эти классы/функции
try:
    from widgets import GameItem, extract_short_info 
except ImportError:
    class GameItem(QWidget): pass 
    def extract_short_info(html): return "Описание недоступно."

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# КЛАСС МОНИТОРИНГА ЭМУЛЯТОРА (EmulatorMonitorThread)
# ----------------------------------------------------------------------
class EmulatorMonitorThread(QThread):
    """Мониторит процесс эмулятора и отправляет сигнал при закрытии."""
    emulator_closed = pyqtSignal()

    def __init__(self, emulator_path, rom_path, fullscreen_arg=None, parent=None):
        super().__init__(parent)
        self.emulator_path = emulator_path
        self.rom_path = rom_path
        self.fullscreen_arg = fullscreen_arg
        self.process = None

    def run(self):
        """Запускает эмулятор и ждет его завершения."""
        cmd = [self.emulator_path, self.rom_path]
        
        # ✅ ИСПРАВЛЕНИЕ 1: Разделяем строку аргументов по пробелам и добавляем их в команду
        if self.fullscreen_arg:
            args = self.fullscreen_arg.split() 
            cmd.extend(args) 
        
        try:
            logger.info(f"Запуск эмулятора: {' '.join(cmd)}") 
            
            # ✅ ИСПРАВЛЕНИЕ 2: Установка рабочей директории (cwd)
            # Критически важно для корректного запуска многих старых эмуляторов.
            emulator_dir = os.path.dirname(self.emulator_path)
            
            self.process = subprocess.Popen(
                cmd, 
                cwd=emulator_dir, # <-- Добавляем этот аргумент!
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            self.process.wait() 
            logger.info(f"Эмулятор для {os.path.basename(self.rom_path)} закрыт.")
        except FileNotFoundError:
            logger.error(f"Файл эмулятора не найден: {self.emulator_path}")
        except Exception as e:
            logger.error(f"Ошибка при запуске/мониторинге эмулятора: {e}")
        finally:
            self.emulator_closed.emit() 

# ----------------------------------------------------------------------
# КЛАСС ЗАГРУЗКИ ОБЛОЖЕК (ImageLoaderThread)
# ----------------------------------------------------------------------
class ImageLoaderThread(QThread):
    """
    Поток для асинхронной загрузки изображения обложки.
    """
    # Сигнал передает виджет GameItem для обновления.
    # 🚨 ИСПРАВЛЕНИЕ 3: Сигнал должен возвращать виджет ИЛИ ID и Pixmap. 
    # Так как мы изменили app_logic.py, чтобы найти виджет по ID, сигнал должен быть:
    # image_ready = pyqtSignal(str, QPixmap) 
    # НО: Для упрощения и избежания поиска, если app_logic.py передавал виджет, вернемся к передаче виджета!
    # Проверим app_logic.py: loader.image_ready.connect(self.handle_image_ready)
    # self.handle_image_ready принимает: handle_image_ready(self, game_item_widget, pixmap)
    # ЗНАЧИТ: Сигнал должен передавать GameItem и QPixmap.
    image_ready = pyqtSignal(GameItem, QPixmap) 

    # 🟢 ИСПРАВЛЕНИЕ 4: Синхронизируем с app_logic.py. Принимаем GameItem, НЕ size.
    def __init__(self, game_folder, game_item_widget, allowed_cover_extensions, parent=None):
        super().__init__(parent)
        self.game_folder = game_folder
        self.game_item_widget = game_item_widget # ⬅️ ВОЗВРАЩАЕМ ВИДЖЕТ
        self.allowed_cover_extensions = allowed_cover_extensions
        # self.size удалено

    def _find_cover_path(self, game_folder_path):
        """Ищет обложку (cover.jpg/png ИЛИ cartridge.png/jpg) в папке images."""
        
        images_dir = os.path.join(game_folder_path, "images")
        
        # 1. Поиск 'cartridge' в папке 'images'
        for ext in self.allowed_cover_extensions:
            cover_filename = f"cartridge{ext}"
            cover_path_in_images = os.path.join(images_dir, cover_filename)
            if os.path.exists(cover_path_in_images):
                return cover_path_in_images
                
        # 2. Поиск 'cover'
        for ext in self.allowed_cover_extensions:
            cover_path = os.path.join(game_folder_path, f"cover{ext}")
            if os.path.exists(cover_path):
                return cover_path
                
            cover_filename = f"cover{ext}"
            cover_path_in_images = os.path.join(images_dir, cover_filename)
            if os.path.exists(cover_path_in_images):
                return cover_path_in_images
                
        return None

    def run(self):
        """Загружает обложку и отправляет сигнал."""
        cover_path = self._find_cover_path(self.game_folder)
        
        pixmap = QPixmap()
        if cover_path:
            pixmap.load(cover_path)
            
        if not pixmap.isNull():
            # 🟢 ИСПРАВЛЕНИЕ 5: Получаем размер из виджета GameItem, который теперь хранится в self
            target_size = self.game_item_widget.image_label.size()
            
            scaled_pixmap = pixmap.scaled(
                target_size, # Используем корректный QSize
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            # 🟢 ИСПРАВЛЕНИЕ 6: Передаем виджет и scaled_pixmap
            self.image_ready.emit(self.game_item_widget, scaled_pixmap) 
        else:
            # 🟢 ИСПРАВЛЕНИЕ 7: Передаем виджет и пустой QPixmap
            self.image_ready.emit(self.game_item_widget, QPixmap())


# ----------------------------------------------------------------------
# КЛАСС ЗАГРУЗКИ ИГР (GameLoaderThread)
# ----------------------------------------------------------------------
class GameLoaderThread(QThread):
    """
    Поток для сканирования папок ROM'ов и парсинга метаданных в фоновом режиме.
    """
    data_loaded = pyqtSignal(list) 

    def __init__(self, root_folder, rom_extensions, parent=None):
        super().__init__(parent)
        self.root_folder = root_folder
        self.rom_extensions = rom_extensions
        self.allowed_screenshot_extensions = ('.jpg', '.jpeg', '.png', '.webp') 

    def run(self):
        """Выполняет сканирование диска и сбор метаданных."""
        rom_data = []
        
        for folder_name in os.listdir(self.root_folder):
            if not self.isRunning(): return
            
            game_folder_path = os.path.join(self.root_folder, folder_name)
            
            if os.path.isdir(game_folder_path):
                
                rom_path = self._find_rom_file(game_folder_path)
                
                if rom_path:
                    info = self._load_game_info(game_folder_path)
                    
                    rom_data.append({
                        'title': folder_name,
                        'folder': game_folder_path,
                        'rom': rom_path,
                        'description': info['description'],
                        'screenshots': info['screenshots']
                    })
                    
        self.data_loaded.emit(rom_data)
        
    def _find_rom_file(self, rom_dir):
        """
        Ищет ROM-файл с заданными расширениями. 
        Сначала ищет в подпапке 'Rom', затем рекурсивно по всей папке.
        """
        rom_subdir = os.path.join(rom_dir, "Rom") # <-- ПЕРВЫМ ДЕЛОМ ПРОВЕРЯЕМ ПАПКУ ROM/
        
        # 1. Поиск в явной подпапке 'Rom'
        if os.path.isdir(rom_subdir):
            for filename in os.listdir(rom_subdir):
                if filename.lower().endswith(self.rom_extensions):
                    return os.path.join(rom_subdir, filename)
        
        # 2. Рекурсивный поиск (как запасной вариант)
        for root, _, files in os.walk(rom_dir):
            for filename in files:
                if filename.lower().endswith(self.rom_extensions):
                    return os.path.join(root, filename)
                    
        return None

    def _load_game_info(self, game_folder_path):
        """Читает index.html, извлекает краткое описание и ищет скриншоты."""
        html_content = ""
        html_path = os.path.join(game_folder_path, "index.html")
        description = "Описание недоступно."

        if os.path.exists(html_path):
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                description = extract_short_info(html_content) 
            except Exception:
                logger.warning(f"Ошибка чтения или парсинга HTML для {game_folder_path}")
        
        images_dir = os.path.join(game_folder_path, "images")
        screenshots = []
        if os.path.isdir(images_dir):
            for filename in os.listdir(images_dir):
                # Игнорируем файлы 'cartridge' и 'cover' при сборе скриншотов
                if "cartridge" not in filename.lower() and "cover" not in filename.lower() and any(
                    filename.lower().endswith(ext) for ext in self.allowed_screenshot_extensions
                ):
                    screenshots.append(os.path.join("images", filename)) 
        
        return {
            'description': description,
            'screenshots': screenshots
        }