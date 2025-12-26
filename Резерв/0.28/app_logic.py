# app_logic.py

import os
import logging
import math
import fnmatch

from PyQt5.QtWidgets import QMessageBox, QLabel
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap

# --- ИМПОРТЫ ИЗ main_app.py (должны быть доступны) ---
from config import (
    CONSOLE_SETTINGS, CURRENT_CONSOLE,  # <--- Теперь используем CURRENT_CONSOLE
    ITEM_WIDTH, ITEM_HEIGHT,  
    ALLOWED_COVER_EXTENSIONS
)
from threads import ImageLoaderThread, GameLoaderThread, EmulatorMonitorThread
from widgets import GameItem, DescriptionWindow 

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# КЛАСС AppLogicMixin (Смешиваемый класс для LauncherApp)
# ----------------------------------------------------------------------

class AppLogicMixin:
    """Содержит всю логику управления данными игр и сеткой."""
    
    # 🚨 ИСПРАВЛЕНИЕ: Добавлены недостающие методы для устранения AttributeError
    def cleanup_threads(self):
        """Останавливает и очищает все активные потоки загрузки изображений и метаданных."""
        logger.info("Очистка потоков...")
        # Останавливаем и ждем завершения потоков загрузки обложек
        if hasattr(self, 'threads'):
            for thread in self.threads:
                if thread.isRunning():
                    thread.quit()
                    thread.wait()
            self.threads = []
        
        # Останавливаем поток загрузки ROM'ов, если он еще активен
        if hasattr(self, 'game_loader_thread') and self.game_loader_thread is not None and self.game_loader_thread.isRunning():
             self.game_loader_thread.quit()
             self.game_loader_thread.wait()

    def clear_grid(self):
        """Полностью очищает QGridLayout от всех виджетов."""
        if hasattr(self, 'grid_layout'):
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
    # ----------------------------------------------------------------------
    
    # 🚨 НОВЫЙ МЕТОД: Переключение консоли
    def switch_console(self, console_key):
        """
        Переключает текущую консоль, обновляет CURRENT_CONSOLE и перезагружает сетку.
        Этот метод вызывается кнопками.
        """
        global CURRENT_CONSOLE # ⚠️ Важно: используем global для изменения импортированной переменной
        
        if console_key == CURRENT_CONSOLE:
            logger.debug(f"Консоль {console_key} уже активна.")
            return
            
        if console_key not in CONSOLE_SETTINGS:
            logger.error(f"Неизвестная консоль: {console_key}")
            return

        # 1. Обновление глобальной переменной
        CURRENT_CONSOLE = console_key
        logger.info(f"Консоль переключена на: {console_key}")
        
        # 2. Обновление UI (фон, кнопки)
        if hasattr(self, 'update_ui_for_console'):
            self.update_ui_for_console(console_key) 
        
        # 3. Перезагрузка игр
        self.load_roms()


    def load_roms(self):
        """
        Запускает GameLoaderThread для асинхронного сканирования диска и парсинга метаданных.
        """ 
        if hasattr(self, 'game_loader_thread') and self.game_loader_thread is not None and self.game_loader_thread.isRunning():
            logger.warning("Отмена предыдущей загрузки метаданных.")
            self.game_loader_thread.quit()
            self.game_loader_thread.wait()
            
        self.cleanup_threads() 
        self.clear_grid() 
        
        settings = CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {}) 
        folder = settings.get("ROOT_FOLDER") 
        extensions = settings.get("ROM_EXTENSIONS")
        
        if not folder or not extensions:
            logger.error(f"Параметры для консоли {CURRENT_CONSOLE} не найдены.")
            return
            
        if not os.path.isdir(folder):
            logger.error(f"Корневая папка не найдена: {folder}")
            QMessageBox.critical(
                self, 
                "Ошибка", 
                f"Корневая папка для {settings.get('NAME', CURRENT_CONSOLE)} не найдена по пути: {folder}"
            )
            self.clear_grid()
            message = QLabel(f"Папка {settings.get('NAME', CURRENT_CONSOLE)} не найдена.")
            message.setObjectName("emptyGridLabel")
            self.grid_layout.addWidget(message, 0, 0, Qt.AlignCenter)
            return


        logger.info(f"Начало загрузки ROM'ов для {CURRENT_CONSOLE} из папки: {folder}")
        
        self.game_loader_thread = GameLoaderThread(folder, extensions, parent=self)
        self.game_loader_thread.data_loaded.connect(self.handle_roms_loaded)
        self.game_loader_thread.start()

    def handle_roms_loaded(self, rom_data):
        """Обрабатывает полученные данные ROM'ов."""
        self.rom_list = rom_data
        
        if not self.rom_list:
            QMessageBox.information(
                self, 
                "Информация", 
                f"Игры для консоли {CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {}).get('NAME', CURRENT_CONSOLE)} не найдены."
            )
            self.clear_grid()
            message = QLabel(f"Игры для {CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {}).get('NAME', CURRENT_CONSOLE)} не найдены.")
            message.setObjectName("emptyGridLabel")
            self.grid_layout.addWidget(message, 0, 0, Qt.AlignCenter)
            return
            
        logger.info(f"Найдено {len(self.rom_list)} игр. Заполнение сетки.")
        self.populate_grid(self.rom_list)

    # 🚨 ИСПРАВЛЕНО: Слот теперь принимает GameItem widget первым аргументом
    def handle_image_ready(self, game_item_widget, pixmap):
        """Обновляет изображение на виджете игры после загрузки."""
        game_item_widget.set_cover_pixmap(pixmap)
        
    def populate_grid(self, roms):
        """Заполняет сетку объектами GameItem на основе списка ROM'ов."""
        self.clear_grid()
        self.cleanup_threads()
        
        if not roms:
            return

        scroll_area_width = self.scroll_area.viewport().width() 
        spacing = self.grid_layout.spacing()
        self.num_cols = max(1, int(scroll_area_width / (ITEM_WIDTH + spacing)))
        
        for index, game_data in enumerate(roms):
            row = index // self.num_cols
            col = index % self.num_cols
            
            item_widget = GameItem(
                game_folder=game_data['folder'], 
                rom_path=game_data['rom'],
                description=game_data['description'], # Краткое описание для тултипа
                item_width=ITEM_WIDTH,      
                item_height=ITEM_HEIGHT,
                screenshots=game_data['screenshots']
            )
            item_widget.game_launched.connect(self.launch_game)
            item_widget.show_description_requested.connect(self.request_game_description)
            
            self.grid_layout.addWidget(item_widget, row, col)
            
            # Запускаем поток для загрузки обложки
            loader = ImageLoaderThread(
                item_widget, # Передаем виджет
                game_data['folder'], 
                item_widget.image_label.size(), 
                allowed_cover_extensions=ALLOWED_COVER_EXTENSIONS
            )
            loader.image_ready.connect(self.handle_image_ready)
            # Убедитесь, что self.threads инициализирован в LauncherApp.__init__()
            if not hasattr(self, 'threads'):
                self.threads = []
            self.threads.append(loader)
            loader.start()
        
        # Настройка растяжения столбцов
        for c in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(c, 0)
        if self.num_cols > 0:
            self.grid_layout.setColumnStretch(self.num_cols - 1, 1)
            
    def request_game_description(self, game_folder):
        """
        Находит полные данные игры по папке и вызывает DescriptionWindow.
        """
        if not hasattr(self, 'rom_list'): return
        
        game_data = next((game for game in self.rom_list if game['folder'] == game_folder), None)
        
        if game_data:
            full_html_content = self.load_full_html_content(game_data['folder'])
            
            self.show_game_description(
                game_data['folder'], 
                full_html_content, # Передаем ПОЛНЫЙ HTML
                game_data['screenshots']
            )
        else:
            logger.error(f"Данные для игры в папке {game_folder} не найдены.")
            QMessageBox.warning(self, "Ошибка", "Не удалось найти описание игры. Пожалуйста, убедитесь, что index.html существует.")

    def load_full_html_content(self, game_folder_path):
        """Читает весь файл index.html."""
        html_path = os.path.join(game_folder_path, "index.html")
        if os.path.exists(html_path):
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Ошибка чтения полного HTML для {game_folder_path}: {e}")
        return "<h1>Ошибка загрузки описания</h1><p>Полный файл index.html не найден или не может быть прочитан.</p>"
            
    def filter_roms(self, text):
        """Фильтрует игры и обновляет сетку."""
        search_text = text.lower()
        if not hasattr(self, 'rom_list') or not self.rom_list: 
            return
        
        if not search_text:
            filtered_list = self.rom_list
        else:
            filtered_list = [
                game for game in self.rom_list 
                if search_text in game['title'].lower()
            ]
        
        self.populate_grid(filtered_list)

    def launch_game(self, rom_path):
        """Запускается по двойному клику."""
        if hasattr(self, 'emulator_thread') and self.emulator_thread and self.emulator_thread.isRunning():
            logger.warning("Эмулятор уже запущен. Игнорирование запроса на запуск.")
            return

        settings = CONSOLE_SETTINGS.get(CURRENT_CONSOLE, {})
        EMULATOR_PATH = settings.get("EMULATOR_PATH") 
        
        if not os.path.exists(EMULATOR_PATH):
            QMessageBox.critical(self, "Ошибка Запуска", f"Эмулятор {settings.get('NAME', 'Консоли')} не найден по пути: {EMULATOR_PATH}")
            logger.error(f"Эмулятор не найден: {EMULATOR_PATH}")
            return
            
        try:
            fullscreen_arg = settings.get('FULLSCREEN_ARG')
            
            # Убедитесь, что show_launcher привязан к LauncherApp
            self.emulator_thread = EmulatorMonitorThread(EMULATOR_PATH, rom_path, fullscreen_arg, parent=self)
            self.emulator_thread.emulator_closed.connect(self.show_launcher) 
            self.emulator_thread.start()
            
            self.showMinimized() 
            logger.info(f"Игра {os.path.basename(os.path.dirname(rom_path))} запущена.")
            
        except Exception:
            logger.error("Не удалось запустить процесс эмулятора:", exc_info=True)
            QMessageBox.critical(self, "Ошибка Запуска", "Не удалось запустить процесс эмулятора.")
            
    def show_game_description(self, game_folder, description, screenshots):
        """Отображает кастомное окно с подробным описанием игры."""
        try:
            desc_window = DescriptionWindow(
                game_folder, 
                description, 
                screenshots, 
                parent=self
            )
            desc_window.exec_()
        except Exception as e:
            logger.error(f"Ошибка при отображении окна описания: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", "Не удалось отобразить подробное описание игры.")