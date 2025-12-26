import os
import time
import subprocess
import logging
import re
import shlex # 🟢 ДОБАВЛЕНО: для надежного парсинга аргументов
from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget

# ВАЖНО: Убедитесь, что widgets.py существует и содержит эти классы/функции
# (Оставляю заглушки, чтобы избежать сбоя при автономном запуске threads.py)
try:
    from widgets import GameItem, extract_short_info 
except ImportError:
    class GameItem(QWidget): 
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.image_label = QWidget() 
            self.image_label.size = lambda: QSize(100, 100)
            
    def extract_short_info(html): 
        return "Описание недоступно."

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
        
        # Разделяем строку аргументов и добавляем их в команду
        if self.fullscreen_arg:
            # 🟢 ИСПРАВЛЕНИЕ/УЛУЧШЕНИЕ: Используем shlex.split() для надежного парсинга
            try:
                args = shlex.split(self.fullscreen_arg)
                cmd.extend(args) 
            except ValueError as e:
                logger.error(f"Ошибка парсинга аргументов эмулятора '{self.fullscreen_arg}': {e}. Использование простого .split()")
                cmd.extend(self.fullscreen_arg.split())

        
        try:
            logger.info(f"Запуск эмулятора: {' '.join(cmd)}") 
            
            # Установка рабочей директории (cwd)
            emulator_dir = os.path.dirname(self.emulator_path)
            
            self.process = subprocess.Popen(
                cmd, 
                cwd=emulator_dir,
                # Улучшено: Явное указание Shell=False, т.к. команда уже является списком.
                shell=False, 
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
    image_ready = pyqtSignal(GameItem, QPixmap) 

    def __init__(self, game_folder, game_item_widget, allowed_cover_extensions, parent=None):
        super().__init__(parent)
        self.game_folder = game_folder
        self.game_item_widget = game_item_widget
        self.allowed_cover_extensions = tuple(ext.lower() for ext in allowed_cover_extensions) 

    def _find_cover_path(self, game_folder_path):
        """Ищет обложку (cartridge/cover) в папке images или корне папки игры."""
        
        images_dir = os.path.join(game_folder_path, "images")
        
        # 1. Поиск 'cartridge' в папке 'images'
        for ext in self.allowed_cover_extensions:
            cover_filename = f"cartridge{ext}"
            cover_path_in_images = os.path.join(images_dir, cover_filename)
            if os.path.exists(cover_path_in_images):
                return cover_path_in_images
                
        # 2. Поиск 'cover' в корне папки игры
        for ext in self.allowed_cover_extensions:
            cover_path = os.path.join(game_folder_path, f"cover{ext}")
            if os.path.exists(cover_path):
                return cover_path
                
        # 3. Поиск 'cover' в папке 'images'
        for ext in self.allowed_cover_extensions:
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
            # Загрузка пиксмапа
            pixmap.load(cover_path)
            
        if not pixmap.isNull():
            # Получаем целевой размер из виджета
            target_size = self.game_item_widget.image_label.size()
            
            # Проверка на нулевой размер, чтобы избежать ошибок
            if target_size.width() > 0 and target_size.height() > 0:
                 scaled_pixmap = pixmap.scaled(
                     target_size,
                     Qt.KeepAspectRatio, 
                     Qt.SmoothTransformation
                 )
            else:
                 scaled_pixmap = pixmap # Использование оригинального, если размер 0

            self.image_ready.emit(self.game_item_widget, scaled_pixmap) 
        else:
            # Отправляем пустой QPixmap, если обложка не найдена/не загружена
            self.image_ready.emit(self.game_item_widget, QPixmap())


# ----------------------------------------------------------------------
# КЛАСС ЗАГРУЗКИ ИГР (GameLoaderThread)
# ----------------------------------------------------------------------
class GameLoaderThread(QThread):
    """
    Поток для сканирования папок ROM'ов, использующий кэш для оптимизации.
    """
    # 🟢 ИСПРАВЛЕНИЕ: Переименовано для соответствия app_logic.py
    game_found = pyqtSignal(dict)  # Сигнал для передачи данных одной найденной игры
    finished_loading = pyqtSignal(list) # Сигнал для передачи окончательного списка ROM'ов

    def __init__(self, root_folder, rom_extensions, allowed_screenshot_extensions, existing_roms=None, parent=None):
        super().__init__(parent)
        self.root_folder = root_folder
        self.rom_extensions = tuple(ext.lower() for ext in rom_extensions) 
        self.allowed_screenshot_extensions = tuple(ext.lower() for ext in allowed_screenshot_extensions) 
        
        # Кэш существующих игр: ключ = FOLDER_NAME, значение = rom_data
        self.existing_roms_map = {}
        if existing_roms:
            self.existing_roms_map = {rom['FOLDER_NAME']: rom for rom in existing_roms} 
        

    def run(self):
        """Выполняет сканирование диска, используя кэш."""
        full_rom_list = []
        
        try:
              folder_names = os.listdir(self.root_folder)
        except FileNotFoundError:
              logger.error(f"Корневая папка не найдена: {self.root_folder}")
              self.finished_loading.emit([]) # 🟢 ИСПРАВЛЕНИЕ: Используем переименованный сигнал
              return
        
        for folder_name in folder_names:
            # 🟢 Добавлена проверка isInterruptionRequested() вместо isRunning()
            if self.isInterruptionRequested(): return
            
            game_folder_path = os.path.join(self.root_folder, folder_name)
            
            if os.path.isdir(game_folder_path):
                
                # ШАГ 1: ПРОВЕРКА КЭША
                if folder_name in self.existing_roms_map:
                    rom_data = self.existing_roms_map[folder_name]
                    
                    # Обновляем пути, так как папка могла быть перемещена
                    rom_data['FULL_ROM_PATH'] = self._find_rom_file(game_folder_path) or rom_data.get('FULL_ROM_PATH')
                    rom_data['FOLDER_PATH'] = game_folder_path
                    
                    logger.debug(f"Кэш: '{folder_name}' взят из кэша.")
                    full_rom_list.append(rom_data)
                    # КЛЮЧЕВОЙ continue: Предотвращает дублирование сигнала game_loaded.
                    continue 

                # ШАГ 2: НОВАЯ ИГРА (ТРЕБУЕТ ЗАГРУЗКИ)
                rom_path = self._find_rom_file(game_folder_path)
                
                if rom_path:
                    info = self._load_game_info(game_folder_path)
                    
                    rom_data = {
                        'title': folder_name,
                        'FOLDER_NAME': folder_name, 
                        'FOLDER_PATH': game_folder_path, 
                        'FULL_ROM_PATH': rom_path,
                        'description': info['description'],
                        'screenshots': info['screenshots']
                    }
                    
                    logger.info(f"Найдена новая игра: '{folder_name}'. Создание виджета.")
                    
                    # Эмитируем сигнал для создания виджета в основном потоке UI
                    self.game_found.emit(rom_data) # 🟢 ИСПРАВЛЕНИЕ: Используем переименованный сигнал
                    full_rom_list.append(rom_data)
                        
        # ЗАВЕРШЕНИЕ: Эмитируем полный список всех ROM'ов для сохранения или дальнейшей работы
        self.finished_loading.emit(full_rom_list) # 🟢 ИСПРАВЛЕНИЕ: Используем переименованный сигнал
        
    def _find_rom_file(self, rom_dir):
        """
        Ищет ROM-файл с заданными расширениями.
        Сначала ищет в подпапке 'Rom', затем рекурсивно по всей папке.
        """
        rom_subdir = os.path.join(rom_dir, "Rom")
        
        # 1. Поиск в явной подпапке 'Rom'
        if os.path.isdir(rom_subdir):
            for filename in os.listdir(rom_subdir):
                if filename.lower().endswith(self.rom_extensions):
                    return os.path.join(rom_subdir, filename)
        
        # 2. Рекурсивный поиск (как запасной вариант)
        for root, _, files in os.walk(rom_dir):
            for filename in files:
                if filename.lower().endswith(self.rom_extensions):
                    # Добавляем проверку, чтобы не подцепить ROM'ы из папки images
                    if "images" not in root.lower():
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
                # Улучшено: Явный вызов extract_short_info
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
                    # Сохраняем путь относительно папки игры для удобства
                    screenshots.append(os.path.join("images", filename)) 
        
        return {
            'description': description,
            'screenshots': screenshots
        }