import os
import time
import subprocess
import logging

from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# КЛАСС МОНИТОРИНГА ЭМУЛЯТОРА
# ----------------------------------------------------------------------
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

    def run(self):
        try:
            # Формируем команду: [эмулятор, аргумент_полного_экрана, путь_к_рому]
            command = [self.emulator_path, self.rom_path]
            if self.fullscreen_arg:
                # Вставляем аргумент перед путем к ROM-файлу
                command.insert(1, self.fullscreen_arg)
            
            logger.info(f"Запуск процесса эмулятора: {' '.join(command)}")
            
            # Запускаем процесс и ждем его завершения (блокирующий вызов)
            process = subprocess.Popen(command)
            process.wait() 
            
            logger.info("Процесс эмулятора завершен.")
            
        except FileNotFoundError:
            logger.error(f"Эмулятор не найден по пути: {self.emulator_path}")
        except Exception as e:
            logger.error(f"Ошибка при запуске эмулятора: {e}", exc_info=True)
            
        finally:
            # Сигнал отправляется, даже если возникла ошибка
            self.emulator_closed.emit()

# ----------------------------------------------------------------------
# КЛАСС ЗАГРУЗКИ ИЗОБРАЖЕНИЙ
# ----------------------------------------------------------------------
class ImageLoaderThread(QThread):
    """
    Поток для асинхронной загрузки изображений обложек игр.
    """
    image_ready = pyqtSignal(QPixmap, QWidget) # Сигнал: (pixmap, GameItem)

    def __init__(self, item_widget, game_folder, allowed_cover_extensions):
        super().__init__()
        self.item_widget = item_widget
        self.game_folder = game_folder
        self.allowed_cover_extensions = allowed_cover_extensions
        
        # ИСПРАВЛЕНИЕ: Используем 'image_label', как определено в widgets.py
        self.icon_size = item_widget.image_label.size() 
        
        logger.debug(f"Инициализация потока загрузки для: {os.path.basename(game_folder)}")

    def run(self):
        # 1. Поиск файла обложки
        cover_path = self._find_cover_file()
        
        pixmap = QPixmap()
        
        if cover_path:
            # 2. Загрузка QPixmap
            # Используем .load() для потокобезопасной загрузки
            if not pixmap.load(cover_path):
                 logger.warning(f"Не удалось загрузить изображение: {cover_path}")
            
        if not pixmap.isNull():
            # 3. Масштабирование
            scaled_pixmap = pixmap.scaled(
                self.icon_size, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            # 4. Отправка сигнала с QPixmap и ссылкой на виджет GameItem
            self.image_ready.emit(scaled_pixmap, self.item_widget)
        else:
             # Отправляем пустой Pixmap, чтобы в GameItem сработала логика заглушки
             logger.debug(f"Изображение обложки не найдено для: {os.path.basename(self.game_folder)}")
             self.image_ready.emit(QPixmap(), self.item_widget)


    def _find_cover_file(self):
        """Ищет обложку (cartridge или cover) в папке игры и в подпапке 'images'."""
        
        # 1. Поиск в подпапке "images"
        images_subfolder = os.path.join(self.game_folder, "images")
        if os.path.isdir(images_subfolder):
            
            # Приоритет: ищем 'cartridge' или 'cover' в папке 'images'
            for filename in os.listdir(images_subfolder):
                lower_filename = filename.lower()
                
                # Проверяем расширение
                if not any(lower_filename.endswith(ext) for ext in self.allowed_cover_extensions):
                    continue

                # Проверяем имя (приоритет для 'cartridge' или 'cover')
                if "cartridge" in lower_filename or "cover" in lower_filename:
                    return os.path.join(images_subfolder, filename)

        # 2. Поиск в корневой папке игры (на случай, если обложка лежит там)
        for filename in os.listdir(self.game_folder):
            if any(filename.lower().endswith(ext) for ext in self.allowed_cover_extensions):
                # Находим первый подходящий файл, считаем его обложкой
                return os.path.join(self.game_folder, filename)

        return None