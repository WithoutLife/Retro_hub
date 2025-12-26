import os
import time
import subprocess
import logging
import re 

from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget

logger = logging.getLogger(__name__)

# --- КЛАСС МОНИТОРИНГА ЭМУЛЯТОРА (ИСПРАВЛЕН) ---
class EmulatorMonitorThread(QThread):
    """
    Поток для запуска эмулятора как внешнего процесса 
    и мониторинга его закрытия.
    """
    emulator_closed = pyqtSignal()
    
    def __init__(self, emulator_path, rom_path, fullscreen_arg=""):
        super().__init__()
        self.emulator_path = emulator_path
        self.rom_path = rom_path
        self.fullscreen_arg = fullscreen_arg
        self.emulator_dir = os.path.dirname(emulator_path)

    def run(self):
        try:
            # Формируем команду: [эмулятор, аргумент_полного_экрана, путь_к_рому]
            command = [self.emulator_path, self.rom_path]
            # ... (логика добавления fullscreen_arg) ...
            
            logger.info(f"Запуск процесса эмулятора: {' '.join(command)}")
            
            # 🛠️ ИСПРАВЛЕНИЕ 2: Добавьте аргумент cwd
            process = subprocess.Popen(
                command, 
                shell=False, 
                cwd=self.emulator_dir, # <-- КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ
            ) 
            process.wait()
            
            logger.info("Процесс эмулятора завершен.")
            
        except FileNotFoundError:
            logger.error(f"Эмулятор не найден по пути: {self.emulator_path}")
        except Exception as e:
            logger.error(f"Ошибка при запуске эмулятора: {e}", exc_info=True)
            
        finally:
            self.emulator_closed.emit()


# --- КЛАСС ЗАГРУЗКИ ИЗОБРАЖЕНИЙ (БЕЗ ИЗМЕНЕНИЙ) ---
class ImageLoaderThread(QThread):
    """
    Поток для асинхронной загрузки изображений обложек игр.
    """
    image_ready = pyqtSignal(QPixmap, QWidget) # Сигнал: (pixmap, GameItem)

    # ИСПРАВЛЕНО: Добавлен обязательный аргумент item_size 
    def __init__(self, item_widget, game_folder, item_size, allowed_cover_extensions):
        super().__init__()
        self.item_widget = item_widget
        self.game_folder = game_folder
        self.allowed_cover_extensions = allowed_cover_extensions
        
        # ИСПРАВЛЕНИЕ: Теперь используем переданный размер
        self.icon_size = item_size
        
        logger.debug(f"Инициализация потока загрузки для: {os.path.basename(game_folder)}")

    def run(self):
        cover_path = self._find_cover_file()
        pixmap = QPixmap()
        
        if cover_path:
            if not pixmap.load(cover_path):
                 logger.warning(f"Не удалось загрузить изображение: {cover_path}")
            
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                self.icon_size, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.image_ready.emit(scaled_pixmap, self.item_widget)
        else:
             logger.debug(f"Изображение обложки не найдено для: {os.path.basename(self.game_folder)}")
             self.image_ready.emit(QPixmap(), self.item_widget)


    def _find_cover_file(self):
        images_subfolder = os.path.join(self.game_folder, "images")
        if os.path.isdir(images_subfolder):
            for filename in os.listdir(images_subfolder):
                lower_filename = filename.lower()
                if not any(lower_filename.endswith(ext) for ext in self.allowed_cover_extensions):
                    continue
                if "cartridge" in lower_filename or "cover" in lower_filename:
                    return os.path.join(images_subfolder, filename)

        for filename in os.listdir(self.game_folder):
            if any(filename.lower().endswith(ext) for ext in self.allowed_cover_extensions):
                return os.path.join(self.game_folder, filename)

        return None


# --- КЛАСС ЗАГРУЗКИ МЕТАДАННЫХ (НОВЫЙ КЛАСС) ---
class GameLoaderThread(QThread):
    """
    Поток для асинхронной загрузки и парсинга данных игр 
    (сканирование диска и чтение HTML).
    """
    # data_loaded: list[dict] -> ['folder', 'rom', 'title', 'description', 'screenshots']
    data_loaded = pyqtSignal(list) 

    def __init__(self, console_folder, rom_extensions, extract_info_func, parent=None):
        super().__init__(parent)
        self.console_folder = console_folder
        self.rom_extensions = rom_extensions
        # extract_info_func - это extract_short_info из widgets.py
        self.extract_info_func = extract_info_func 
        self._is_running = True
        self.allowed_screenshot_extensions = [".png", ".jpg", ".jpeg", ".webp", ".gif"]


    def run(self):
        game_data_list = []
        
        if not os.path.exists(self.console_folder):
            logger.error(f"Корневая папка не найдена: {self.console_folder}")
            self.data_loaded.emit([])
            return
            
        try:
            # Сканирование папок консоли
            for item_name in os.listdir(self.console_folder):
                if not self._is_running: return # Безопасная остановка
                
                game_folder_path = os.path.join(self.console_folder, item_name)
                
                if os.path.isdir(game_folder_path):
                    
                    # 1. Поиск ROM-файла
                    rom_path = self._find_rom_file(game_folder_path, self.rom_extensions)
                    
                    if rom_path:
                        # 2. Загрузка и парсинг описания/скриншотов
                        html_content, screenshots = self._load_game_info(game_folder_path)
                        
                        # 3. Извлечение краткого описания
                        short_description = self.extract_info_func(html_content)
                        
                        # 4. Добавление данных
                        game_data_list.append({
                            'folder': game_folder_path, # Полный путь к папке игры
                            'rom': rom_path,
                            'title': item_name,
                            'description': short_description,
                            'screenshots': screenshots
                        })

        except Exception as e:
            logger.error(f"Ошибка при загрузке данных игр в потоке: {e}", exc_info=True)
        
        # Сортировка перед отправкой данных
        game_data_list.sort(key=lambda x: x['title'])
        
        self.data_loaded.emit(game_data_list)
        
    def _find_rom_file(self, game_folder_path, allowed_extensions):
        """Ищет ROM-файл в подпапке /rom."""
        rom_dir = os.path.join(game_folder_path, "rom")
        
        if os.path.isdir(rom_dir):
            for filename in os.listdir(rom_dir):
                for ext in allowed_extensions:
                    if filename.lower().endswith(ext):
                        return os.path.join(rom_dir, filename)
        return None

    def _load_game_info(self, game_folder_path):
        """Загрузка HTML-описания и списка скриншотов."""
        
        # 1. Загрузка HTML
        html_path = os.path.join(game_folder_path, "index.html")
        html_content = ""
        if os.path.exists(html_path):
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except Exception:
                # В случае ошибки чтения возвращаем пустой контент
                pass
        
        # 2. Поиск скриншотов
        images_dir = os.path.join(game_folder_path, "images")
        screenshots = []
        
        if os.path.isdir(images_dir):
            for filename in os.listdir(images_dir):
                if "cartridge" not in filename.lower() and any(
                    filename.lower().endswith(ext) for ext in self.allowed_screenshot_extensions
                ):
                    # Сохраняем путь как относительный: images/filename
                    screenshots.append(f"images/{filename}")
                    
        return html_content, screenshots

    def quit(self):
        """Обеспечивает безопасную остановку потока."""
        self._is_running = False
        super().quit()