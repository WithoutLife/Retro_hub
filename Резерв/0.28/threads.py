import os
import time
import subprocess
import logging
import re
from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget

# ВАЖНО: Убедитесь, что widgets.py существует и содержит эти классы/функции
# Используем try/except для предотвращения сбоя импорта при автономном запуске threads.py
try:
    from widgets import GameItem, extract_short_info 
except ImportError:
    class GameItem(QWidget): pass 
    def extract_short_info(html): return "Описание недоступно."

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# КЛАСС МОНИТОРИНГА ЭМУЛЯТОРА
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
        if self.fullscreen_arg:
            cmd.append(self.fullscreen_arg)

        try:
            # Запуск эмулятора
            logger.info(f"Запуск эмулятора: {cmd}")
            self.process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.process.wait() # Ждем завершения процесса
            logger.info(f"Эмулятор для {os.path.basename(self.rom_path)} закрыт.")
        except FileNotFoundError:
            logger.error(f"Файл эмулятора не найден: {self.emulator_path}")
        except Exception as e:
            logger.error(f"Ошибка при запуске/мониторинге эмулятора: {e}")
        finally:
            self.emulator_closed.emit() 

# ----------------------------------------------------------------------
# КЛАСС ЗАГРУЗКИ ОБЛОЖЕК
# ----------------------------------------------------------------------
class ImageLoaderThread(QThread):
    """
    Поток для асинхронной загрузки изображения обложки.
    """
    
    # 🚨 ИСПРАВЛЕНО: Явно объявляем, что сигнал передает GameItem (object) и QPixmap.
    # Это устраняет ошибку 'QPixmap' object has no attribute 'set_cover_pixmap'.
    image_ready = pyqtSignal(object, QPixmap) 

    def __init__(self, game_item_widget, game_folder, size, allowed_cover_extensions, parent=None):
        super().__init__(parent)
        self.game_item_widget = game_item_widget 
        self.game_folder = game_folder
        self.size = size
        self.allowed_cover_extensions = allowed_cover_extensions

    def _find_cover_path(self, game_folder_path):
        """Ищет обложку (cover.jpg/png ИЛИ cartridge.png/jpg) в папке images."""
        
        images_dir = os.path.join(game_folder_path, "images")
        
        # 1. Поиск 'cartridge' в папке 'images' (ваш формат)
        # Проверяем расширения для файла "cartridge"
        for ext in self.allowed_cover_extensions:
            # Ищем: .../images/cartridge.ext
            cover_filename = f"cartridge{ext}"
            cover_path_in_images = os.path.join(images_dir, cover_filename)
            if os.path.exists(cover_path_in_images):
                return cover_path_in_images
                
        # 2. Поиск 'cover' в папке игры или 'images' (старый/альтернативный формат)
        for ext in self.allowed_cover_extensions:
            # Ищем: .../game_folder/cover.ext
            cover_path = os.path.join(game_folder_path, f"cover{ext}")
            if os.path.exists(cover_path):
                return cover_path
                
            # Ищем: .../images/cover.ext
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
            scaled_pixmap = pixmap.scaled(
                self.size, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            # 🚨 ИСПРАВЛЕНО: Передаем GameItem (self.game_item_widget) ПЕРВЫМ
            self.image_ready.emit(self.game_item_widget, scaled_pixmap) 
        else:
            # Отправляем пустой QPixmap, чтобы UI мог отобразить заглушку
            self.image_ready.emit(self.game_item_widget, QPixmap())


# ----------------------------------------------------------------------
# КЛАСС ЗАГРУЗКИ ИГР (GameLoaderThread)
# ----------------------------------------------------------------------
class GameLoaderThread(QThread):
    """
    Поток для сканирования папок ROM'ов и парсинга метаданных в фоновом режиме.
    """
    # Сигнал для отправки списка ROM-данных обратно в главный поток
    data_loaded = pyqtSignal(list) 

    def __init__(self, root_folder, rom_extensions, parent=None):
        super().__init__(parent)
        self.root_folder = root_folder
        self.rom_extensions = rom_extensions
        # Добавляем расширения скриншотов
        self.allowed_screenshot_extensions = ('.jpg', '.jpeg', '.png', '.webp') 

    def run(self):
        """Выполняет сканирование диска и сбор метаданных."""
        rom_data = []
        
        # 1. Сканирование всех подкаталогов в root_folder
        for folder_name in os.listdir(self.root_folder):
            if not self.isRunning(): return # Проверка на остановку
            
            game_folder_path = os.path.join(self.root_folder, folder_name)
            
            if os.path.isdir(game_folder_path):
                
                # 2. Поиск ROM-файла
                rom_path = self._find_rom_file(game_folder_path)
                
                if rom_path:
                    # 3. Загрузка метаданных (описание, скриншоты)
                    info = self._load_game_info(game_folder_path)
                    
                    rom_data.append({
                        'title': folder_name,
                        'folder': game_folder_path,
                        'rom': rom_path,
                        'description': info['description'],
                        'screenshots': info['screenshots']
                    })
                    
        # Отправка собранных данных обратно в главный поток
        self.data_loaded.emit(rom_data)
        
    def _find_rom_file(self, rom_dir):
        """Ищет ROM-файл с заданными расширениями в папке."""
        for filename in os.listdir(rom_dir):
            if filename.lower().endswith(self.rom_extensions):
                return os.path.join(rom_dir, filename)
        
        # Ищем вложенные ROM-файлы (в случае, если папка содержит только один ROM)
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
                # Используется функция extract_short_info из widgets.py для тултипа
                description = extract_short_info(html_content) 
            except Exception:
                logger.warning(f"Ошибка чтения или парсинга HTML для {game_folder_path}")
        
        # 2. Поиск скриншотов
        images_dir = os.path.join(game_folder_path, "images")
        screenshots = []
        if os.path.isdir(images_dir):
            for filename in os.listdir(images_dir):
                if "cartridge" not in filename.lower() and any(
                    filename.lower().endswith(ext) for ext in self.allowed_screenshot_extensions
                ):
                    # Сохраняем путь относительно папки игры
                    screenshots.append(os.path.join("images", filename)) 
        
        return {
            'description': description,
            'screenshots': screenshots
        }